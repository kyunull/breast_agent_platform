<template>
  <div class="workflow-node" :class="[`workflow-node--${data.graphNode.type}`, { 'workflow-node--selected': data.selected }]">
    <Handle v-if="data.graphNode.type !== 'input'" id="input" :position="Position.Left" type="target" />
    <div class="workflow-node__topline"><span>{{ typeLabel }}</span><span class="workflow-node__id">{{ id.slice(0, 5) }}</span></div>
    <strong>{{ data.graphNode.name }}</strong>
    <p>{{ summary }}</p>
    <div v-if="data.graphNode.type !== 'output'" class="workflow-node__outputs">
      <div v-for="port in outputPorts" :key="port.id" class="workflow-node__output">
        <span>{{ port.label }}</span><Handle :id="port.id" :position="Position.Right" type="source" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position, type NodeProps } from '@vue-flow/core'

import type { FlowNodeData } from '@/composables/useGraphAdapter'

const props = defineProps<NodeProps<FlowNodeData>>()

const labels: Record<string, string> = {
  input: 'INPUT', condition: 'CONDITION', python_rule: 'RULE', rag: 'EVIDENCE', llm: 'LLM', parallel_agent: 'PARALLEL', output: 'OUTPUT', clinical_task: 'TASK', subworkflow: 'MDT', annotation: 'NOTE',
}
const typeLabel = computed(() => labels[props.data.graphNode.type] ?? props.data.graphNode.type.toUpperCase())
const summary = computed(() => {
  const config = props.data.graphNode.config
  if (typeof config.summary === 'string') return config.summary
  if (typeof config.prompt === 'string') return '已配置任务提示词'
  if (typeof config.query_template === 'string') return '已配置检索查询'
  return '等待配置'
})
const outputPorts = computed(() => {
  if (props.data.graphNode.type !== 'condition') {
    return props.data.graphNode.output_ports.map((port) => typeof port === 'string' ? { id: port, label: port } : { id: port.id, label: port.label ?? port.id })
  }
  const node = props.data.graphNode
  const config = node.config
  const ports = node.output_ports.map((port) => typeof port === 'string' ? { id: port, label: port } : { id: port.id, label: port.label ?? port.id })
  const truePort = String(config.true_port ?? ports[0]?.id ?? 'satisfied')
  const falsePort = String(config.false_port ?? ports[1]?.id ?? 'unsatisfied')
  return [
    { id: truePort, label: String(config.true_label ?? ports.find((port) => port.id === truePort)?.label ?? '满足') },
    { id: falsePort, label: String(config.false_label ?? ports.find((port) => port.id === falsePort)?.label ?? '不满足') },
  ]
})
</script>

<style scoped>
.workflow-node { position: relative; width: 210px; min-height: 104px; padding: 12px 14px; color: var(--ink-950); background: #fffefa; border: 1px solid #9eafa9; border-left: 4px solid var(--ink-650); border-radius: var(--radius-sm); box-shadow: 0 5px 13px rgb(16 38 49 / 11%); transition: border-color .16s ease, box-shadow .16s ease; }
.workflow-node--selected { border-color: var(--teal-600); box-shadow: 0 0 0 3px rgb(39 137 123 / 22%), 0 7px 16px rgb(16 38 49 / 14%); }
.workflow-node__topline { display: flex; justify-content: space-between; margin-bottom: 9px; color: var(--ink-650); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 9px; font-weight: 800; letter-spacing: .08em; }
.workflow-node__id { color: #98a5a0; font-size: 8px; }
.workflow-node strong { display: block; font-size: 14px; }
.workflow-node p { margin: 6px 0 0; color: var(--ink-650); font-size: 11px; line-height: 1.35; }
.workflow-node__outputs { position: absolute; top: 25px; right: -1px; display: grid; gap: 18px; transform: translateY(-50%); }
.workflow-node__output { position: relative; display: flex; align-items: center; justify-content: flex-end; min-height: 16px; padding-right: 7px; color: var(--ink-650); font-size: 9px; white-space: nowrap; }
.workflow-node__output :deep(.vue-flow__handle) { top: 50%; right: -6px; transform: translateY(-50%); }
.workflow-node--input { border-left-color: #387f98; }.workflow-node--condition { border-left-color: #a56c17; }.workflow-node--python_rule { border-left-color: #785c9d; }.workflow-node--rag { border-left-color: var(--teal-700); }.workflow-node--llm { border-left-color: #b04e70; }.workflow-node--parallel_agent { border-left-color: #4e6bb6; }.workflow-node--output { border-left-color: #37835d; }.workflow-node--clinical_task { border-left-color: #b26d32; }.workflow-node--subworkflow { border-left-color: #5b7892; }.workflow-node--annotation { border-left-color: #77817a; }
</style>
