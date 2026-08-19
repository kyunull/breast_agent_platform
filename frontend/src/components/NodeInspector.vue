<template>
  <aside class="node-inspector" :class="{ 'node-inspector--empty': !node }">
    <template v-if="node">
      <div class="node-inspector__heading"><div><p>{{ node.type }}</p><h3>节点属性</h3></div><button title="删除节点" type="button" @click="$emit('delete')"><Trash2 :size="16" aria-hidden="true" /><span class="sr-only">删除节点</span></button></div>
      <el-form label-position="top" size="small">
        <el-form-item label="节点名称"><el-input :model-value="node.name" @update:model-value="updateName" /></el-form-item>
        <el-form-item label="节点标识"><el-input :model-value="node.id" disabled /></el-form-item>
      </el-form>
      <div class="inspector-section"><div class="inspector-section__title"><span>结构复制</span><Copy :size="14" aria-hidden="true" /></div><p>复制内容不包含密钥或真实患者资料。</p><el-button size="small" @click="$emit('copy')"><Copy :size="14" />复制节点 JSON</el-button></div>
      <div class="inspector-section"><div class="inspector-section__title"><span>粘贴校验</span><ClipboardPaste :size="14" aria-hidden="true" /></div><el-input v-model="pasteText" :rows="5" placeholder="粘贴版本化节点 JSON" type="textarea" /><p v-if="issues.length" class="issues">{{ issues.join(' ') }}</p><p v-else-if="preview" class="preview">将导入：{{ preview.name }}（{{ preview.type }}）</p><div class="paste-actions"><el-button size="small" @click="validatePaste">校验</el-button><el-button :disabled="!preview" size="small" type="primary" @click="applyPaste">导入为新节点</el-button></div></div>
      <slot :node="node" />
    </template>
    <div v-else class="inspector-empty"><MousePointer2 :size="22" aria-hidden="true" /><strong>选择一个节点</strong><p>在画布中点击节点后配置其医学语义和输入输出。</p></div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ClipboardPaste, Copy, MousePointer2, Trash2 } from 'lucide-vue-next'

import { parseNodeClipboard } from '@/composables/useGraphAdapter'
import type { GraphNode } from '@/types/graph'

const props = defineProps<{ node: GraphNode | null }>()
const emit = defineEmits<{ update: [node: GraphNode]; delete: []; copy: []; paste: [node: GraphNode] }>()
const pasteText = ref('')
const issues = ref<string[]>([])
const preview = ref<GraphNode | null>(null)

function updateName(name: string) {
  if (props.node) emit('update', { ...props.node, name })
}

function validatePaste() {
  const result = parseNodeClipboard(pasteText.value)
  issues.value = result.issues
  preview.value = result.node
}

function applyPaste() {
  if (preview.value) emit('paste', preview.value)
}
</script>

<style scoped>
.node-inspector { display: flex; flex-direction: column; width: 286px; min-width: 286px; padding: 16px; overflow-y: auto; background: var(--paper-100); border-left: 1px solid var(--line); }
.node-inspector__heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 15px; padding-bottom: 13px; border-bottom: 1px solid var(--line); }
.node-inspector__heading p { margin: 0 0 3px; color: var(--teal-700); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 9px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }.node-inspector__heading h3 { margin: 0; color: var(--ink-950); font-size: 16px; }.node-inspector__heading button { display: grid; width: 28px; height: 28px; color: var(--red-700); place-items: center; cursor: pointer; background: #fff4f3; border: 1px solid #eccbc8; border-radius: var(--radius-sm); }.inspector-section { padding: 15px 0; border-top: 1px solid var(--line); }.inspector-section__title { display: flex; justify-content: space-between; align-items: center; color: var(--ink-950); font-size: 12px; font-weight: 800; }.inspector-section p { color: var(--ink-650); font-size: 11px; line-height: 1.5; }.issues { color: var(--red-700) !important; }.preview { color: var(--teal-700) !important; }.paste-actions { display: flex; gap: 8px; margin-top: 8px; }.inspector-empty { display: grid; align-content: center; justify-items: center; flex: 1; min-height: 260px; color: var(--ink-650); text-align: center; }.inspector-empty strong { margin-top: 12px; color: var(--ink-800); font-size: 13px; }.inspector-empty p { margin: 7px 0 0; font-size: 11px; line-height: 1.6; }.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
@media (max-width: 760px) { .node-inspector { width: 250px; min-width: 250px; padding: 13px; } }
</style>
