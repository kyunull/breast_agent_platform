<template>
  <section class="trace-panel">
    <div class="trace-heading"><div><strong>节点 Trace</strong><span>按执行顺序记录输入摘要、输出和证据</span></div><span>{{ traces.length }} 个节点</span></div>
    <div v-if="!traces.length" class="trace-empty">运行后将在这里显示每个节点的状态和耗时。</div>
    <ol v-else class="trace-list">
      <li v-for="trace in sortedTraces" :key="trace.id" class="trace-item">
        <span class="trace-sequence">{{ trace.sequence }}</span>
        <div class="trace-body"><div class="trace-title"><strong>{{ nodeLabels[trace.node_id] ?? trace.node_id }}</strong><span class="trace-status" :class="`trace-status--${trace.status}`">{{ statusLabel(trace.status) }}</span><span v-if="trace.duration_ms !== null" class="trace-duration">{{ trace.duration_ms }} ms</span></div><p v-if="trace.error" class="trace-error">{{ trace.error.code }}：{{ trace.error.message }}</p><div class="trace-evidence"><button v-for="ref in trace.evidence_refs" :key="ref" type="button" @click="$emit('evidence', ref)"><BookOpen :size="12" />{{ ref }}</button></div></div>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BookOpen } from 'lucide-vue-next'

import type { TraceResponse } from '@/types/api'

const props = defineProps<{ traces: TraceResponse[]; nodeLabels?: Record<string, string> }>()
defineEmits<{ evidence: [evidenceId: string] }>()
const nodeLabels = computed(() => props.nodeLabels ?? {})
const sortedTraces = computed(() => [...props.traces].sort((a, b) => a.sequence - b.sequence))
const statusLabels: Record<string, string> = { succeeded: '完成', running: '运行中', failed: '失败', cancelled: '已取消', queued: '排队' }
const statusLabel = (status: string) => statusLabels[status] ?? status
</script>

<style scoped>
.trace-panel { margin-top: 18px; background: var(--paper-100); border: 1px solid var(--line); }.trace-heading { display: flex; gap: 12px; justify-content: space-between; padding: 13px 15px; border-bottom: 1px solid var(--line); }.trace-heading strong,.trace-heading span { display: block; }.trace-heading strong { color: var(--ink-950); font-size: 13px; }.trace-heading div span { margin-top: 3px; color: var(--ink-650); font-size: 10px; }.trace-heading > span { color: var(--ink-650); font-size: 11px; }.trace-empty { padding: 26px 15px; color: var(--ink-650); font-size: 12px; }.trace-list { margin: 0; padding: 12px 15px 15px; list-style: none; }.trace-item { display: grid; grid-template-columns: 27px 1fr; gap: 11px; padding: 8px 0 12px; border-bottom: 1px solid #e1e4df; }.trace-item:last-child { border-bottom: 0; }.trace-sequence { display: grid; width: 25px; height: 25px; color: var(--ink-650); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; place-items: center; background: #e7eeea; border-radius: 50%; }.trace-title { display: flex; gap: 8px; align-items: center; }.trace-title strong { color: var(--ink-800); font-size: 12px; }.trace-status { padding: 3px 6px; font-size: 9px; font-weight: 700; border: 1px solid; border-radius: 999px; }.trace-status--succeeded { color: var(--teal-700); background: #e3f3ee; border-color: #a6cec5; }.trace-status--failed { color: var(--red-700); background: #fff0ef; border-color: #e7bbb7; }.trace-status--running,.trace-status--queued { color: var(--amber-600); background: #fff5db; border-color: #e8c77e; }.trace-duration { margin-left: auto; color: var(--ink-650); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; }.trace-error { margin: 6px 0 0; color: var(--red-700); font-size: 11px; }.trace-evidence { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 7px; }.trace-evidence button { display: inline-flex; gap: 4px; align-items: center; padding: 3px 6px; color: var(--teal-700); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; cursor: pointer; background: #e8f3ef; border: 1px solid #b6d8d0; border-radius: var(--radius-sm); }.trace-evidence button:hover { background: #d9ece6; }
</style>
