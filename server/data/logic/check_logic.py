"""
盘点任务、协同数据同步、差异比对 业务逻辑
不得出现任何SQL语句

设计要点：
  1) 盘点范围 scope_type 三种：ALL（全校）/ DEPT（按学院）/ ASSET（按具体资产）
  2) 创建任务时记录范围，启动任务时按范围从 asset_info 拉账面快照生成 check_detail 行
  3) 保存明细时清洗空行 / null / 无效值
  4) 差异分析 4 类：盘盈 / 盘亏 / 信息不符 / 相符
"""
from typing import Any, Dict, List, Optional, Tuple
import json

from data.basic.check_dao import CheckTaskDAO, CheckDetailDAO, CheckDiffReportDAO
from data.basic.asset_dao import AssetDAO


class CheckLogic:
    """盘点业务逻辑"""

    def __init__(self, db_config: Dict, asset_db_config: Optional[Dict] = None):
        self.task_dao = CheckTaskDAO(db_config)
        self.detail_dao = CheckDetailDAO(db_config)
        self.report_dao = CheckDiffReportDAO(db_config)
        self._asset_db_config = asset_db_config
        self._asset_dao = None

    def _get_asset_dao(self):
        if self._asset_dao is None and self._asset_db_config is not None:
            self._asset_dao = AssetDAO(self._asset_db_config)
        return self._asset_dao

    def create_task(self, data: Dict) -> Dict:
        """创建盘点任务

        :param data: { task_name, scope_type(ALL/DEPT/ASSET),
                       scope_dept_ids/list[int]?, scope_asset_ids/list[int]?,
                       start_time, end_time, checker_ids/list[int]? }
        """
        data["status"] = "PENDING"

        scope_type = (data.get("scope_type") or "DEPT").upper()
        if scope_type not in ("ALL", "DEPT", "ASSET"):
            return {"error": f"不支持的盘点范围: {scope_type}"}
        data["scope_type"] = scope_type

        # 序列化
        if "checker_ids" in data and isinstance(data["checker_ids"], list):
            data["checker_ids"] = ",".join(str(i) for i in data["checker_ids"] if i is not None) or None
        if "scope_dept_ids" in data and isinstance(data["scope_dept_ids"], list):
            data["scope_dept_ids"] = ",".join(str(i) for i in data["scope_dept_ids"] if i is not None) or None
        if "scope_asset_ids" in data and isinstance(data["scope_asset_ids"], list):
            data["scope_asset_ids"] = ",".join(str(i) for i in data["scope_asset_ids"] if i is not None) or None

        # 范围必填校验
        if scope_type == "DEPT" and not data.get("scope_dept_ids"):
            return {"error": "请选择至少一个学院"}
        if scope_type == "ASSET" and not data.get("scope_asset_ids"):
            return {"error": "请选择至少一个资产"}

        task_id = self.task_dao.insert_task(data)
        return self.get_task_detail(task_id) or {}

    def get_task_detail(self, task_id: int) -> Optional[Dict]:
        task = self.task_dao.get_task_by_id(task_id)
        if not task:
            return None
        # 解析 JSON/list 字段为 Python list 方便前端使用
        for f in ("scope_dept_ids", "scope_asset_ids", "checker_ids"):
            v = task.get(f)
            if isinstance(v, str) and v:
                task[f] = [int(x) for x in v.split(",") if x.strip().isdigit()]
            else:
                task[f] = []
        return task

    def list_tasks(self, status: str = "", manager_id: int = 0, dept_id: int = 0,
                   page_num: int = 1, page_size: int = 10, current_user=None) -> Tuple[List, int]:
        items, total = self.task_dao.list_tasks(
            status, manager_id, dept_id, page_num, page_size, current_user
        )
        # 解析 id 列表
        for it in items:
            for f in ("scope_dept_ids", "scope_asset_ids", "checker_ids"):
                v = it.get(f)
                if isinstance(v, str) and v:
                    it[f] = [int(x) for x in v.split(",") if x.strip().isdigit()]
                else:
                    it[f] = []
        return items, total

    def update_task(self, data: Dict) -> Optional[Dict]:
        for f in ("checker_ids", "scope_dept_ids", "scope_asset_ids"):
            if f in data and isinstance(data[f], list):
                data[f] = ",".join(str(i) for i in data[f] if i is not None) or None
        self.task_dao.update_task(data)
        return self.get_task_detail(data["task_id"])

    def delete_task(self, task_id: int) -> bool:
        self.detail_dao.delete_by_task(task_id)
        self.task_dao.delete_task(task_id)
        return True

    def start_task(self, task_id: int) -> Dict:
        """启动盘点任务：按范围生成 check_detail 行（账面快照）"""
        task = self.task_dao.get_task_by_id(task_id)
        if not task:
            return {"error": "任务不存在"}
        if task["status"] != "PENDING":
            return {"error": "当前状态不可开始盘点"}

        # 已有明细则不再生成（避免重复）
        existing = self.detail_dao.list_by_task(task_id)
        if not existing:
            details = self._build_initial_details(task)
            if details:
                self.detail_dao.batch_insert(details)

        self.task_dao.update_task_status(task_id, "IN_PROGRESS")
        return {"message": "盘点任务已开始", "detail_count": len(existing) or 0}

    def _build_initial_details(self, task: Dict) -> List[Dict]:
        """根据 scope_type 从 asset_info 拉账面快照生成盘点明细"""
        asset_dao = self._get_asset_dao()
        if asset_dao is None:
            return []
        scope_type = (task.get("scope_type") or "").upper()
        rows: List[Dict] = []

        if scope_type == "ALL":
            # 全校：分页拉所有（不传 keyword/dept/category 即可）
            assets, _ = asset_dao.list_assets(page_num=1, page_size=100000)
            rows.extend(assets)
        elif scope_type == "DEPT":
            ids = self._parse_id_list(task.get("scope_dept_ids"))
            for d in ids:
                assets, _ = asset_dao.list_assets(dept_id=d, page_num=1, page_size=100000)
                rows.extend(assets)
        elif scope_type == "ASSET":
            ids = self._parse_id_list(task.get("scope_asset_ids"))
            for a in ids:
                one = asset_dao.get_asset_by_id(a)
                if one:
                    rows.append(one)

        details: List[Dict] = []
        for a in rows:
            details.append({
                "task_id": task["task_id"],
                "asset_id": a.get("asset_id"),
                "asset_code": a.get("asset_code") or "",
                "asset_name": a.get("asset_name") or "",
                "asset_spec": a.get("spec") or "",
                "book_location": a.get("location") or "",
                "book_status": self._map_asset_status(a.get("status")),
                "actual_location": None,
                "actual_status": None,
                "diff_type": "",
                "remark": "",
            })
        return details

    @staticmethod
    def _parse_id_list(v: Any) -> List[int]:
        if isinstance(v, list):
            return [int(x) for x in v if str(x).isdigit()]
        if isinstance(v, str) and v:
            return [int(x) for x in v.split(",") if x.strip().isdigit()]
        return []

    @staticmethod
    def _map_asset_status(asset_status_id: Any) -> str:
        """asset_info.status 数字 id → status_code 字符串"""
        if not asset_status_id:
            return "IDLE"
        # asset_status 表约定：1=IDLE, 2=USING, 3=REPAIRING, 4=ABANDON, 5=FLOWING
        return {
            1: "IDLE", 2: "USING", 3: "REPAIRING",
            4: "ABANDON", 5: "FLOWING",
        }.get(int(asset_status_id), "IDLE")

    def get_sheet_data(self, task_id: int) -> Dict:
        """获取盘点表格数据，生成初始表格"""
        task = self.task_dao.get_task_by_id(task_id)
        if not task:
            return {"error": "任务不存在"}

        existing = self.detail_dao.list_by_task(task_id)
        return {
            "task": task,
            "details": existing,
            "headers": [
                "asset_code", "asset_name", "asset_spec",
                "book_location", "book_status",
                "actual_location", "actual_status", "remark"
            ],
            "column_names": [
                "资产编号", "资产名称", "规格型号",
                "账面存放地点", "账面状态",
                "实盘存放地点", "实盘状态", "备注"
            ],
        }

    def save_sheet_data(self, task_id: int, details: List[Dict]) -> Dict:
        """保存盘点明细数据

        关键修复：清洗来自 Luckysheet / 前端的 null/空字符串/全空行
        - 任何字段为 None / "" / 空白 → 视为未录入，存为 None
        - asset_id 缺失 → 跳过该行（不入库）
        - 完全没有任何"实盘"信息（actual_location/actual_status/remark 全空）的行不重复保存
        """
        task = self.task_dao.get_task_by_id(task_id)
        if not task:
            return {"error": "任务不存在"}
        if task["status"] not in ["IN_PROGRESS", "PENDING"]:
            return {"error": "当前任务状态不可编辑"}

        cleaned: List[Dict] = []
        skipped = 0
        for raw in details or []:
            d = self._clean_detail(raw, task_id)
            if d is None:
                skipped += 1
                continue
            cleaned.append(d)

        self.task_dao.update_task_status(task_id, "IN_PROGRESS")
        for d in cleaned:
            self.detail_dao.upsert_detail(d)
        return {
            "message": "保存成功",
            "saved_count": len(cleaned),
            "skipped_count": skipped,
        }

    @staticmethod
    def _clean_detail(raw: Dict, task_id: int) -> Optional[Dict]:
        """清洗单行：None/空串归一为 None，资产 id 缺失则跳过"""
        def norm(v: Any) -> Optional[Any]:
            if v is None:
                return None
            if isinstance(v, str):
                s = v.strip()
                # 兼容 "null"/"None"/"undefined" 字符串
                if s == "" or s.lower() in ("null", "none", "undefined", "nan"):
                    return None
                return s
            return v

        asset_id = raw.get("asset_id")
        # 资产 id 必填：盘点必须基于账面行
        try:
            asset_id_int = int(asset_id) if asset_id is not None and str(asset_id) != "" else 0
        except (TypeError, ValueError):
            asset_id_int = 0
        if not asset_id_int:
            return None

        actual_location = norm(raw.get("actual_location"))
        actual_status = norm(raw.get("actual_status"))
        diff_type = norm(raw.get("diff_type")) or ""
        remark = norm(raw.get("remark"))

        # 全空行不保存（没有意义且会覆盖已有行）
        if not any([actual_location, actual_status, diff_type, remark]):
            return None

        return {
            "task_id": task_id,
            "asset_id": asset_id_int,
            "asset_code": norm(raw.get("asset_code")) or "",
            "asset_name": norm(raw.get("asset_name")) or "",
            "asset_spec": norm(raw.get("asset_spec")) or "",
            "book_location": norm(raw.get("book_location")) or "",
            "book_status": norm(raw.get("book_status")) or "",
            "actual_location": actual_location,
            "actual_status": actual_status,
            "diff_type": diff_type,
            "remark": remark or "",
        }

    def analyze_diff(self, task_id: int, llm_result: Optional[str] = None) -> Dict:
        """差异比对分析
        关键修复：
          1) diff_type 统一使用英文键：MATCHED / MISMATCH / MISSING / EXTRA
          2) 把每行的 diff_type 写回 check_detail 表（前端 Sheet 可直接看到差异标识）
          3) 报告带 diff_items 前端直接渲染
        """
        task = self.task_dao.get_task_by_id(task_id)
        if not task:
            return {"error": "任务不存在"}

        details = self.detail_dao.list_by_task(task_id)
        if not details:
            return {"error": "无盘点明细数据"}

        total = len(details)
        matched = surplus = shortage = mismatch = 0
        diff_items: List[Dict] = []

        for d in details:
            # 已有 diff_type（人工录入）优先
            cur = d.get("diff_type", "")
            # 旧中文值兼容
            cur_map = {"盘盈": "EXTRA", "盘亏": "MISSING", "信息不符": "MISMATCH", "相符": "MATCHED"}
            if cur in cur_map:
                cur = cur_map[cur]

            if not cur:
                # 自动判定
                if not d.get("actual_location") and not d.get("actual_status"):
                    # 关键：完全未录入视为"相符"（视为与账面一致）
                    cur = "MATCHED"
                elif d.get("book_location") != d.get("actual_location") or \
                     str(d.get("book_status") or "") != str(d.get("actual_status") or ""):
                    cur = "MISMATCH"
                else:
                    cur = "MATCHED"
                # 把判定结果写回 detail.diff_type（持久化）
                try:
                    self.detail_dao.update_diff_type(d["detail_id"], cur)
                except Exception:
                    pass

            d["diff_type"] = cur
            if cur == "EXTRA":
                surplus += 1
            elif cur == "MISSING":
                shortage += 1
            elif cur == "MISMATCH":
                mismatch += 1
            else:
                matched += 1
            diff_items.append(d)

        report_data = {
            "task_id": task_id,
            "task_name": task["task_name"],
            "total_items": total,
            "matched_items": matched,
            "surplus_items": surplus,
            "shortage_items": shortage,
            "mismatch_items": mismatch,
            "diff_items": diff_items,
            "llm_analysis": llm_result or "",
        }
        self.report_dao.insert_report(report_data)
        self.task_dao.update_task_status(task_id, "DONE")
        return report_data

    def get_diff_report(self, task_id: int) -> Optional[Dict]:
        """获取差异报告：含 diff_items 明细（从 check_detail 重新计算一次保证最新）"""
        report = self.report_dao.get_by_task(task_id)
        if not report:
            return None
        details = self.detail_dao.list_by_task(task_id)
        # 计算差异只读视图（不写回 DB）
        diff_items: List[Dict] = []
        matched = surplus = shortage = mismatch = 0
        for d in details:
            cur = d.get("diff_type", "") or "MATCHED"
            if cur in ("盘盈",): cur = "EXTRA"
            elif cur in ("盘亏",): cur = "MISSING"
            elif cur in ("信息不符",): cur = "MISMATCH"
            d["diff_type"] = cur
            if cur == "EXTRA": surplus += 1
            elif cur == "MISSING": shortage += 1
            elif cur == "MISMATCH": mismatch += 1
            else: matched += 1
            diff_items.append(d)
        report["diff_items"] = diff_items
        report["matched_items"] = matched
        report["surplus_items"] = surplus
        report["shortage_items"] = shortage
        report["mismatch_items"] = mismatch
        return report

    def confirm_result(self, task_id: int) -> Dict:
        """确认盘点结果"""
        task = self.task_dao.get_task_by_id(task_id)
        if not task:
            return {"error": "任务不存在"}
        self.task_dao.update_task_status(task_id, "CONFIRMED")
        return {"message": "盘点结果已确认"}
