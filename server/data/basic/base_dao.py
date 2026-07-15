"""
DAO基类：数据库连接、SQL执行封装
所有DAO层类继承此基类，统一数据库操作入口
"""
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool


class BaseDAO:
    """数据访问基类，封装SQLAlchemy引擎与通用执行方法"""

    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化数据库连接
        :param db_config: 数据库配置字典，包含 host/port/user/password/database/pool_size/max_overflow
        """
        url = (
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            f"?charset=utf8mb4"
        )
        self._engine: Engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=db_config.get("pool_size", 10),
            max_overflow=db_config.get("max_overflow", 20),
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

    def _execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行查询SQL，返回字典列表
        """
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            rows = result.fetchall()
            if rows:
                return [dict(row._mapping) for row in rows]
            return []

    def _execute_one(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """执行查询SQL，返回第一条记录"""
        rows = self._execute(sql, params)
        return rows[0] if rows else None

    def _execute_update(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行更新SQL（INSERT/UPDATE/DELETE），返回影响行数
        """
        with self._engine.connect() as conn:
            with conn.begin():
                result = conn.execute(text(sql), params or {})
                return result.rowcount

    def _execute_insert(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行INSERT并返回自增ID
        """
        with self._engine.connect() as conn:
            with conn.begin():
                result = conn.execute(text(sql), params or {})
                return result.lastrowid

    def _execute_batch(self, sql: str, params_list: List[Dict[str, Any]]) -> int:
        """批量执行更新"""
        count = 0
        with self._engine.connect() as conn:
            with conn.begin():
                for params in params_list:
                    result = conn.execute(text(sql), params)
                    count += result.rowcount
        return count

    def _execute_scalar(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行查询，返回第一行第一列标量值"""
        with self._engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            row = result.fetchone()
            return row[0] if row else None

    @property
    def conn(self):
        """获取原始连接（用于事务控制）"""
        return self._engine.connect()
