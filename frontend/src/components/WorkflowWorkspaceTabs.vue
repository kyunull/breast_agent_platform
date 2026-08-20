<template>
  <nav class="workspace-tabs" aria-label="工作流工作区">
    <RouterLink :to="`/workflows/${workflowId}/data`" :class="{ 'is-active': route.name === 'workflow-data' }">数据准备</RouterLink>
    <RouterLink :to="`/workflows/${workflowId}/edit`" :class="{ 'is-active': route.name === 'workflow-edit' }">流程编辑</RouterLink>
    <RouterLink :to="`/workflows/${workflowId}/test`" :class="{ 'is-active': route.name === 'workflow-test' }">在线测试</RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

defineProps<{ workflowId: string }>()

const route = useRoute()
</script>

<style scoped>
.workspace-tabs { display: flex; gap: 4px; overflow-x: auto; border-bottom: 1px solid var(--line); }
.workspace-tabs a { display: block; padding: 10px 14px; color: var(--ink-650); font-size: 13px; font-weight: 700; text-decoration: none; border-bottom: 2px solid transparent; white-space: nowrap; }
.workspace-tabs a:hover { color: var(--teal-700); }
.workspace-tabs a.is-active { color: var(--teal-700); border-bottom-color: var(--teal-700); }
</style>
