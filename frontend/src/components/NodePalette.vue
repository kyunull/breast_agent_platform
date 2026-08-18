<template>
  <aside class="node-palette" aria-label="节点库">
    <div class="node-palette__heading"><span>节点库</span><small>拖放或点击添加</small></div>
    <div class="node-palette__group">
      <button v-for="item in items" :key="item.type" class="palette-item" type="button" :title="`添加${item.label}`" @click="$emit('add', item.type)">
        <component :is="item.icon" :size="16" aria-hidden="true" />
        <span>{{ item.label }}</span>
        <Plus :size="13" aria-hidden="true" />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { Bot, Braces, DatabaseZap, FileInput, FileOutput, GitBranch, ListTodo, MessageSquareText, Network, Plus, Stethoscope } from 'lucide-vue-next'

import type { GraphNodeType } from '@/types/graph'

defineEmits<{ add: [type: GraphNodeType] }>()

const items: Array<{ type: GraphNodeType; label: string; icon: unknown }> = [
  { type: 'input', label: '输入', icon: FileInput },
  { type: 'condition', label: '条件', icon: GitBranch },
  { type: 'python_rule', label: '规则', icon: Braces },
  { type: 'rag', label: '指南检索', icon: DatabaseZap },
  { type: 'llm', label: 'LLM 判断', icon: Bot },
  { type: 'parallel_agent', label: '并行 Agent', icon: Network },
  { type: 'output', label: '输出', icon: FileOutput },
  { type: 'clinical_task', label: '临床任务', icon: ListTodo },
  { type: 'subworkflow', label: '子工作流', icon: Stethoscope },
  { type: 'annotation', label: '说明', icon: MessageSquareText },
]
</script>

<style scoped>
.node-palette { display: flex; flex-direction: column; min-width: 160px; background: #f5f5f0; border-right: 1px solid var(--line); }
.node-palette__heading { display: flex; flex-direction: column; gap: 3px; padding: 15px 14px 12px; border-bottom: 1px solid var(--line); }
.node-palette__heading span { color: var(--ink-950); font-size: 13px; font-weight: 800; }
.node-palette__heading small { color: var(--ink-650); font-size: 10px; }
.node-palette__group { display: grid; gap: 4px; padding: 10px 8px; overflow-y: auto; }
.palette-item { display: grid; grid-template-columns: 18px 1fr 14px; gap: 7px; align-items: center; min-height: 32px; padding: 0 7px; color: var(--ink-800); font-size: 12px; text-align: left; cursor: pointer; background: transparent; border: 1px solid transparent; border-radius: var(--radius-sm); }
.palette-item svg:last-child { opacity: 0; }
.palette-item:hover { color: var(--teal-700); background: #e4f2ee; border-color: #afd0c8; }
.palette-item:hover svg:last-child { opacity: 1; }
@media (max-width: 760px) { .node-palette { min-width: 145px; } }
</style>
