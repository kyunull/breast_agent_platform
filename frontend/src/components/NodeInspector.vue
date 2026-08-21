<template>
  <aside class="node-inspector" :class="{ 'node-inspector--empty': !node }">
    <template v-if="node">
      <div class="node-inspector__heading">
        <div class="node-inspector__title">
          <p>{{ typeLabel }}</p>
          <el-input v-if="editingName" ref="nameInput" v-model="draftName" class="node-inspector__name-input" size="small" @blur="commitName" @keydown.enter.prevent="commitName" @keydown.esc.prevent="cancelName" />
          <button v-else type="button" class="node-inspector__name" title="编辑节点名称" @click="startNameEdit">{{ typeLabel }} · {{ node.name }}</button>
          <small>{{ node.id }}</small>
        </div>
        <button class="node-inspector__delete" title="删除节点" type="button" @click="$emit('delete')"><Trash2 :size="16" aria-hidden="true" /><span class="sr-only">删除节点</span></button>
      </div>
      <div class="node-inspector__body"><slot :node="node" /></div>
      <section class="structure-tools">
        <button type="button" class="structure-tools__toggle" :aria-expanded="toolsOpen" @click="toolsOpen = !toolsOpen"><span><Braces :size="14" aria-hidden="true" />结构工具</span><ChevronDown :size="15" :class="{ 'is-open': toolsOpen }" aria-hidden="true" /></button>
        <div v-if="toolsOpen" class="structure-tools__body">
          <p>复制内容不包含密钥或真实患者资料。</p>
          <el-button size="small" @click="$emit('copy')"><Copy :size="14" />复制节点 JSON</el-button>
          <div class="paste-block"><div class="inspector-section__title"><span>粘贴校验</span><ClipboardPaste :size="14" aria-hidden="true" /></div><el-input v-model="pasteText" :rows="5" placeholder="粘贴版本化节点 JSON" type="textarea" /><p v-if="issues.length" class="issues">{{ issues.join(' ') }}</p><p v-else-if="preview" class="preview">将导入：{{ preview.name }}（{{ preview.type }}）</p><div class="paste-actions"><el-button size="small" @click="validatePaste">校验</el-button><el-button :disabled="!preview" size="small" type="primary" @click="applyPaste">导入为新节点</el-button></div></div>
        </div>
      </section>
    </template>
    <div v-else class="inspector-empty"><MousePointer2 :size="22" aria-hidden="true" /><strong>选择一个节点</strong><p>在画布中点击节点后配置其医学语义和输入输出。</p></div>
  </aside>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { Braces, ChevronDown, ClipboardPaste, Copy, MousePointer2, Trash2 } from 'lucide-vue-next'
import type { InputInstance } from 'element-plus'

import { parseNodeClipboard } from '@/composables/useGraphAdapter'
import type { GraphNode } from '@/types/graph'

const props = defineProps<{ node: GraphNode | null }>()
const emit = defineEmits<{ update: [node: GraphNode]; delete: []; copy: []; paste: [node: GraphNode] }>()
const pasteText = ref('')
const issues = ref<string[]>([])
const preview = ref<GraphNode | null>(null)
const toolsOpen = ref(false)
const editingName = ref(false)
const draftName = ref('')
const nameInput = ref<InputInstance>()
const typeLabels: Record<GraphNode['type'], string> = { input: '输入', condition: '条件', python_rule: '规则', rag: '指南检索', llm: 'LLM 判断', parallel_agent: '并行 Agent', output: '输出', clinical_task: '临床任务', subworkflow: '子工作流', annotation: '说明' }
const typeLabel = ref('')

watch(() => props.node, (node) => {
  typeLabel.value = node ? typeLabels[node.type] : ''
  draftName.value = node?.name ?? ''
  editingName.value = false
  toolsOpen.value = false
}, { immediate: true })

async function startNameEdit() {
  draftName.value = props.node?.name ?? ''
  editingName.value = true
  await nextTick()
  nameInput.value?.focus()
}

function commitName() {
  const name = draftName.value.trim()
  if (!props.node || !name) return
  editingName.value = false
  if (name !== props.node.name) emit('update', { ...props.node, name })
}

function cancelName() {
  draftName.value = props.node?.name ?? ''
  editingName.value = false
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
.node-inspector { display: flex; flex-direction: column; width: 320px; min-width: 320px; padding: 16px; overflow-y: auto; background: var(--paper-100); border-left: 1px solid var(--line); }
.node-inspector__heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 15px; padding-bottom: 13px; border-bottom: 1px solid var(--line); }.node-inspector__title { min-width: 0; }.node-inspector__title p { margin: 0 0 5px; color: var(--teal-700); font-size: 10px; font-weight: 800; }.node-inspector__title small { display: block; max-width: 220px; margin-top: 5px; overflow: hidden; color: #83918d; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 8px; text-overflow: ellipsis; white-space: nowrap; }.node-inspector__name { max-width: 235px; padding: 0; overflow: hidden; color: var(--ink-950); font-size: 15px; font-weight: 800; text-align: left; text-overflow: ellipsis; white-space: nowrap; cursor: text; background: transparent; border: 0; }.node-inspector__name:hover { color: var(--teal-700); }.node-inspector__name-input { width: 230px; }.node-inspector__delete { display: grid; width: 28px; height: 28px; color: var(--red-700); place-items: center; cursor: pointer; background: #fff4f3; border: 1px solid #eccbc8; border-radius: var(--radius-sm); }.node-inspector__body { flex: 1; }.structure-tools { margin-top: auto; border-top: 1px solid var(--line); }.structure-tools__toggle { display: flex; width: 100%; min-height: 38px; align-items: center; justify-content: space-between; padding: 0; color: var(--ink-800); font-size: 11px; font-weight: 800; cursor: pointer; background: transparent; border: 0; }.structure-tools__toggle span { display: inline-flex; gap: 6px; align-items: center; }.structure-tools__toggle svg:last-child { transition: transform .16s ease; }.structure-tools__toggle svg.is-open { transform: rotate(180deg); }.structure-tools__body { padding: 4px 0 2px; }.structure-tools__body > p { margin: 0 0 9px; color: var(--ink-650); font-size: 10px; line-height: 1.5; }.paste-block { margin-top: 13px; padding-top: 11px; border-top: 1px solid var(--line); }.inspector-section__title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; color: var(--ink-950); font-size: 11px; font-weight: 800; }.issues { color: var(--red-700) !important; }.preview { color: var(--teal-700) !important; }.paste-block p { font-size: 10px; line-height: 1.45; }.paste-actions { display: flex; gap: 8px; margin-top: 8px; }.inspector-empty { display: grid; align-content: center; justify-items: center; flex: 1; min-height: 260px; color: var(--ink-650); text-align: center; }.inspector-empty strong { margin-top: 12px; color: var(--ink-800); font-size: 13px; }.inspector-empty p { margin: 7px 0 0; font-size: 11px; line-height: 1.6; }.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
@media (max-width: 760px) { .node-inspector { width: 250px; min-width: 250px; padding: 13px; } }
</style>
