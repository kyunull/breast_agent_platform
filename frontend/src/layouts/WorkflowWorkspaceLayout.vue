<template>
  <section class="workflow-workspace">
    <div v-if="loading" class="loading-line">正在读取草稿...</div>
    <div v-else-if="errorMessage" class="notice notice--error">
      <span>{{ errorMessage }}</span>
      <button type="button" @click="load">重试</button>
    </div>
    <template v-else-if="draft">
      <header class="workspace-heading">
        <div>
          <p class="page-eyebrow">工作流草稿</p>
          <div class="title-row">
            <el-input v-model="draft.name" class="title-input" @change="markNameDirty" />
            <span class="draft-badge">草稿 v{{ draft.version_number }}</span>
          </div>
        </div>
        <div class="workspace-actions">
          <el-button :loading="store.saving" @click="save">{{ store.saveLabel }}</el-button>
          <el-button type="primary" @click="publish">发布版本</el-button>
        </div>
      </header>
      <WorkflowWorkspaceTabs :workflow-id="workflowId" />
      <RouterView />
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from 'vue-router'

import { getApiError } from '@/api/client'
import WorkflowWorkspaceTabs from '@/components/WorkflowWorkspaceTabs.vue'
import { useWorkflowStore } from '@/stores/workflow'

const route = useRoute()
const store = useWorkflowStore()
const loading = ref(true)
const errorMessage = ref('')
const workflowId = computed(() => String(route.params.id))
const draft = computed(() => store.draft)

onMounted(load)
watch(workflowId, load)

onBeforeRouteUpdate((to, from) => confirmDiscard(String(to.params.id), String(from.params.id)))
onBeforeRouteLeave(() => confirmDiscard('', workflowId.value))

function confirmDiscard(nextId: string, currentId: string) {
  if (nextId === currentId || !store.dirty) return true
  return window.confirm('当前工作流有未保存的修改，确定离开吗？')
}

async function load() {
  loading.value = true
  errorMessage.value = ''
  try {
    await store.ensureDraft(workflowId.value)
  } catch (error) {
    errorMessage.value = getApiError(error).message
  } finally {
    loading.value = false
  }
}

function markNameDirty() {
  if (draft.value) store.patchLocal({ name: draft.value.name })
}

async function save() {
  try {
    await store.saveDraft()
  } catch (error) {
    errorMessage.value = getApiError(error).message
  }
}

async function publish() {
  try {
    await store.publish()
  } catch (error) {
    errorMessage.value = getApiError(error).message
  }
}
</script>

<style scoped>
.workflow-workspace { max-width: 1480px; margin: 0 auto; }.workspace-heading { display: flex; gap: 18px; align-items: flex-end; justify-content: space-between; margin-bottom: 18px; }.page-eyebrow { margin: 0 0 6px; color: var(--teal-700); font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.title-row { display: flex; gap: 10px; align-items: center; }.title-input { max-width: 430px; }.title-input :deep(.el-input__wrapper) { padding: 2px 10px; background: transparent; box-shadow: none; }.title-input :deep(input) { padding: 0; color: var(--ink-950); font-size: 27px; font-weight: 700; }.draft-badge { padding: 5px 8px; color: #7f4b08; font-size: 10px; font-weight: 800; background: #fff4da; border: 1px solid #e8c77e; border-radius: 999px; }.workspace-actions { display: flex; gap: 8px; align-items: center; }.workspace-actions :deep(.el-button--primary) { background: var(--teal-700); border-color: var(--teal-700); }.loading-line { padding: 26px 0; color: var(--ink-650); font-size: 13px; }.notice { display: flex; gap: 10px; align-items: center; padding: 12px 14px; color: var(--red-700); font-size: 13px; background: #fff0ef; border: 1px solid #e7bbb7; border-radius: var(--radius-sm); }.notice button { margin-left: auto; color: inherit; text-decoration: underline; cursor: pointer; background: none; border: 0; }
@media (max-width: 760px) { .workspace-heading { display: block; }.workspace-actions { margin-top: 14px; }.title-input { max-width: min(100%, 300px); }.title-input :deep(input) { font-size: 23px; } }
</style>
