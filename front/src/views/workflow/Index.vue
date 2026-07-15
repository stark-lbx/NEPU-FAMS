<template>
  <div class="page-container workflow-entry">
    <div class="page-title">
      <el-icon><Document /></el-icon> 流程中心
    </div>

    <el-row :gutter="16" class="entry-row">
      <el-col :xs="24" :sm="12">
        <el-card shadow="hover" class="entry-card" @click="$router.push('/workflows/pending')">
          <div class="entry-icon" style="--c:#E6A23C">
            <el-icon><Bell /></el-icon>
          </div>
          <div class="entry-body">
            <div class="entry-title">待办清单</div>
            <div class="entry-desc">等待我审批 / 派单 / 接单 / 验收 的流程</div>
          </div>
          <el-icon class="entry-arrow"><ArrowRight /></el-icon>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12">
        <el-card shadow="hover" class="entry-card" @click="$router.push('/workflows/done')">
          <div class="entry-icon" style="--c:#67C23A">
            <el-icon><Folder /></el-icon>
          </div>
          <div class="entry-body">
            <div class="entry-title">我的已处理</div>
            <div class="entry-desc">我审批 / 驳回 / 派单 / 接单 过的流程记录</div>
          </div>
          <el-icon class="entry-arrow"><ArrowRight /></el-icon>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷发起：3/4 个按钮 + 弹窗 -->
    <el-card shadow="never" class="quick-card">
      <template #header>
        <div class="card-hd">
          <span><el-icon><Promotion /></el-icon> 快速发起申请</span>
        </div>
      </template>
      <div class="quick-bar">
        <el-button type="primary" :icon="ShoppingCart" @click="openApplyDialog('BORROW')">领用</el-button>
        <el-button type="success" :icon="RefreshRight" @click="openApplyDialog('RETURN')">归还</el-button>
        <el-button type="warning" :icon="Tools" @click="openRepairDialog()">报修</el-button>
        <el-button
          v-if="userStore.hasRole(['admin', 'college_admin'])"
          type="danger" :icon="Delete" @click="openApplyDialog('SCRAP')"
        >报废</el-button>
      </div>
    </el-card>

    <!-- 申请弹窗（复用 composable） -->
    <el-dialog v-model="applyDialog.visible" :title="`发起${APPLY_TYPE_NAME[applyDialog.type]}申请`" width="520px" destroy-on-close>
      <el-form ref="applyFormRef" :model="applyDialog.form" :rules="applyDialogRules" label-width="90px" size="default">
        <el-form-item label="资产编号" prop="asset_code">
          <el-input v-model="applyDialog.form.asset_code" placeholder="请输入资产编号" @blur="onAssetCodeBlur">
            <template #append>
              <el-button @click="onAssetCodeBlur"><el-icon><Search /></el-icon></el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="资产名称">
          <el-input v-model="applyDialog.form.asset_name" disabled />
        </el-form-item>
        <el-form-item v-if="applyDialog.type !== 'RETURN'" label="资产状态">
          <el-tag v-if="applyDialog.form.asset_status_name" :type="ASSET_STATUS_TYPE[applyDialog.form.asset_status] || 'info'" size="small">
            {{ applyDialog.form.asset_status_name }}
          </el-tag>
          <span v-else class="text-muted">-</span>
        </el-form-item>
        <!-- 预计归还时间：仅 BORROW 显示，可选 -->
        <el-form-item v-if="applyDialog.type === 'BORROW'" label="预计归还">
          <el-date-picker
            v-model="applyDialog.form.expect_return_time"
            type="datetime"
            placeholder="可选，例：2026-08-15 18:00"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="applyDialog.form.remark" type="textarea" :rows="3" placeholder="可填写使用目的/归还原因/报废原因等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="applyDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="applyDialog.loading" @click="onSubmitApply">提交</el-button>
      </template>
    </el-dialog>

    <!-- 报修弹窗 -->
    <el-dialog v-model="repairDialog.visible" title="发起报修" width="520px" destroy-on-close>
      <el-form ref="repairFormRef" :model="repairDialog.form" :rules="repairDialogRules" label-width="90px" size="default">
        <el-form-item label="资产编号" prop="asset_code">
          <el-input v-model="repairDialog.form.asset_code" placeholder="请输入资产编号" @blur="onRepairAssetBlur">
            <template #append>
              <el-button @click="onRepairAssetBlur"><el-icon><Search /></el-icon></el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="资产名称">
          <el-input v-model="repairDialog.form.asset_name" disabled />
        </el-form-item>
        <el-form-item label="故障描述" prop="fault_desc">
          <el-input v-model="repairDialog.form.fault_desc" type="textarea" :rows="4" placeholder="请详细描述故障现象" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repairDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="repairDialog.loading" @click="onSubmitRepair">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Bell, Folder, ArrowRight, Promotion, Search,
  Document, ShoppingCart, RefreshRight, Tools, Delete,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { useApplyDialog } from '@/composables/useApplyDialog'
import { APPLY_TYPE_NAME, ASSET_STATUS_TYPE } from '@/types'

const userStore = useUserStore()
const {
  applyFormRef, applyDialog, applyDialogRules,
  repairFormRef, repairDialog, repairDialogRules,
  openApplyDialog, openRepairDialog,
  onAssetCodeBlur, onRepairAssetBlur,
  onSubmitApply, onSubmitRepair,
} = useApplyDialog()
</script>

<style scoped>
.workflow-entry .entry-row { margin-top: 8px; }
.entry-card {
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s;
}
.entry-card:hover { transform: translateY(-2px); }
.entry-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--c) 14%, white);
  color: var(--c);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  flex-shrink: 0;
}
.entry-body { flex: 1; }
.entry-title { font-size: 18px; font-weight: 600; color: #303133; }
.entry-desc { font-size: 12px; color: #909399; margin-top: 4px; }
.entry-arrow { color: #c0c4cc; font-size: 18px; }

.quick-card { margin-top: 16px; }
.card-hd {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}
.quick-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
