<template>
  <section class="workflows-page">
    <div class="page-heading">
      <div>
        <p class="page-eyebrow">决策工作流</p>
        <h2>工作流</h2>
        <p class="page-description">管理临床决策方案的草稿、发布版本和测试入口。</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <Plus :size="16" aria-hidden="true" />
        新建工作流
      </el-button>
    </div>

    <div v-if="store.error" class="notice notice--error" role="alert">
      <CircleAlert :size="17" aria-hidden="true" />
      <span>{{ store.error.message }}</span>
      <button type="button" @click="store.loadWorkflows">重试</button>
    </div>

    <div v-if="loading" class="loading-line">正在读取工作流列表...</div>
    <div v-else-if="store.items.length === 0" class="empty-state">
      <div class="empty-state__mark"><Workflow :size="24" aria-hidden="true" /></div>
      <h3>还没有工作流</h3>
      <p>创建一个决策工作流，从字段准备开始。</p>
      <el-button type="primary" @click="openCreate">创建第一个工作流</el-button>
    </div>
    <div v-else class="workflow-table-wrap">
      <table class="workflow-table">
        <thead><tr><th>名称</th><th>说明</th><th>草稿</th><th>发布</th><th aria-label="操作"></th></tr></thead>
        <tbody>
          <tr v-for="item in store.items" :key="item.id">
            <td><strong>{{ item.name }}</strong><span class="row-id">{{ item.id.slice(0, 8) }}</span></td>
            <td class="muted-cell">{{ item.description || '暂无说明' }}</td>
            <td><span class="status-pill status-pill--draft">v{{ item.draft_version_number }}</span></td>
            <td><span class="status-pill status-pill--muted">未发布</span></td>
            <td class="row-actions">
              <RouterLink :to="`/workflows/${item.id}/edit`" title="编辑工作流"><Pencil :size="16" aria-hidden="true" /><span class="sr-only">编辑</span></RouterLink>
              <RouterLink :to="`/workflows/${item.id}/test`" title="在线测试"><Play :size="16" aria-hidden="true" /><span class="sr-only">测试</span></RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <el-dialog v-model="createVisible" title="创建工作流" width="min(480px, calc(100vw - 32px))">
      <el-form :model="form" label-position="top" @submit.prevent="create">
        <el-form-item label="名称" required><el-input v-model="form.name" placeholder="例如：HER2 阳性晚期乳腺癌决策" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" :rows="3" type="textarea" placeholder="说明适用人群、目标和证据范围" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="createVisible = false">取消</el-button><el-button type="primary" :loading="creating" @click="create">创建并编辑</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CircleAlert, Pencil, Play, Plus, Workflow } from 'lucide-vue-next'

import { useWorkflowStore } from '@/stores/workflow'

const store = useWorkflowStore()
const router = useRouter()
const loading = ref(false)
const creating = ref(false)
const createVisible = ref(false)
const form = reactive({ name: '', description: '' })

onMounted(async () => {
  loading.value = true
  await store.loadWorkflows()
  loading.value = false
})

function openCreate() {
  form.name = ''
  form.description = ''
  createVisible.value = true
}

async function create() {
  if (!form.name.trim()) return
  creating.value = true
  try {
    const created = await store.create(form.name.trim(), form.description.trim() || undefined)
    createVisible.value = false
    await router.push(`/workflows/${created.id}/edit`)
  } finally {
    creating.value = false
  }
}
</script>

<style scoped>
.workflows-page { max-width: 1180px; margin: 0 auto; }
.page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
.page-eyebrow { margin: 0 0 6px; color: var(--teal-700); font-size: 11px; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; }
.page-heading h2 { margin: 0; color: var(--ink-950); font-size: 28px; }
.page-description { margin: 8px 0 0; color: var(--ink-650); font-size: 14px; }
.page-heading :deep(.el-button) { min-height: 40px; background: var(--teal-700); border-color: var(--teal-700); }
.notice { display: flex; gap: 10px; align-items: center; margin-bottom: 18px; padding: 12px 14px; font-size: 13px; border: 1px solid; border-radius: var(--radius-sm); }
.notice--error { color: var(--red-700); background: #fff0ef; border-color: #e7bbb7; }
.notice button { margin-left: auto; color: inherit; text-decoration: underline; cursor: pointer; background: none; border: 0; }
.loading-line { padding: 28px 0; color: var(--ink-650); font-size: 14px; }
.empty-state { display: grid; justify-items: center; padding: 76px 24px; text-align: center; background: var(--paper-100); border: 1px dashed var(--line); }
.empty-state__mark { display: grid; width: 50px; height: 50px; color: var(--teal-700); place-items: center; background: #e1f1ed; border-radius: 50%; }
.empty-state h3 { margin: 18px 0 6px; color: var(--ink-950); font-size: 20px; }
.empty-state p { margin: 0 0 20px; color: var(--ink-650); font-size: 14px; }
.empty-state :deep(.el-button) { background: var(--teal-700); border-color: var(--teal-700); }
.workflow-table-wrap { overflow-x: auto; background: var(--paper-100); border: 1px solid var(--line); box-shadow: var(--shadow-panel); }
.workflow-table { width: 100%; min-width: 760px; border-collapse: collapse; }
.workflow-table th { padding: 13px 18px; color: var(--ink-650); font-size: 11px; font-weight: 800; letter-spacing: 0.08em; text-align: left; text-transform: uppercase; background: #e9ece7; border-bottom: 1px solid var(--line); }
.workflow-table td { padding: 17px 18px; color: var(--ink-800); font-size: 14px; border-bottom: 1px solid #dfe2dd; }
.workflow-table tbody tr:last-child td { border-bottom: 0; }
.workflow-table tbody tr:hover { background: #f1f6f3; }
.workflow-table strong { display: block; color: var(--ink-950); font-size: 14px; }
.row-id { display: block; margin-top: 4px; color: #8a9896; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; }
.muted-cell { max-width: 370px; color: var(--ink-650) !important; }
.status-pill { display: inline-flex; padding: 4px 8px; font-size: 11px; font-weight: 700; border: 1px solid; border-radius: 999px; }
.status-pill--draft { color: #7f4b08; background: #fff4da; border-color: #e8c77e; }
.status-pill--muted { color: #687777; background: #edf0ed; border-color: #cbd3cd; }
.row-actions { display: flex; gap: 7px; justify-content: flex-end; }
.row-actions a { display: grid; width: 30px; height: 30px; color: var(--ink-650); place-items: center; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.row-actions a:hover { color: var(--teal-700); border-color: #90c1b7; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 820px) {
  .page-heading { align-items: flex-start; }
  .workflow-table th,
  .workflow-table td { padding-right: 14px; padding-left: 14px; }
}
@media (max-width: 620px) {
  .page-heading { display: block; margin-bottom: 20px; }
  .page-heading h2 { font-size: 24px; }
  .page-heading :deep(.el-button) { width: 100%; margin-top: 16px; }
  .workflow-table-wrap { box-shadow: none; }
  .workflow-table { min-width: 680px; }
}
</style>
