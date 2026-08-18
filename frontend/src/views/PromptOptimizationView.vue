<template>
  <section class="prompt-page">
    <div class="page-heading"><div><p class="page-eyebrow">Prompt lab</p><h2>提示词优化</h2><p>从一次成功运行中选择 LLM 节点，生成候选并写入草稿。</p></div><span class="draft-note"><FilePenLine :size="15" />只修改 draft</span></div>
    <div class="prompt-grid">
      <section class="control-panel"><div class="panel-title"><strong>选择运行</strong><span>成功运行的 trace 才能生成候选</span></div><el-form label-position="top" size="small"><el-form-item label="运行 ID"><el-input v-model="runId" :placeholder="runStore.run?.id ?? '粘贴一次运行的 ID'" /></el-form-item><el-form-item label="LLM 节点"><el-select v-model="nodeId" placeholder="选择 LLM trace"><el-option v-for="trace in llmTraces" :key="trace.node_id" :label="nodeLabels[trace.node_id] ?? trace.node_id" :value="trace.node_id" /></el-select></el-form-item><el-form-item label="中文优化指令"><el-input v-model="instruction" :rows="7" type="textarea" placeholder="例如：让方案先列出证据缺口，再给出监测建议。" /></el-form-item><p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p><el-button :loading="creating" class="primary-button" type="primary" @click="generate"><Sparkles :size="15" />生成候选</el-button></el-form></section>
      <section class="result-panel"><div class="panel-title"><strong>候选结果</strong><span v-if="optimization">{{ optimization.status }}</span></div><div v-if="!optimization" class="result-empty"><Sparkles :size="22" /><p>提交优化指令后，在这里查看原提示词、候选和差异。</p></div><template v-else><PromptDiff :candidate="optimization.candidate_prompt" :original="optimization.original_prompt" :result-diff="optimization.result_diff" /><div class="apply-row"><span>确认后会刷新当前 draft，不会改动已发布版本。</span><el-button :disabled="!optimization.candidate_prompt || optimization.status === 'applied'" :loading="applying" type="primary" @click="apply"><Check :size="15" />应用到草稿</el-button></div></template></section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { FilePenLine, Sparkles, Check } from 'lucide-vue-next'

import { getApiError } from '@/api/client'
import { createPromptOptimization, applyPromptOptimization } from '@/api/prompts'
import { useRunStore } from '@/stores/run'
import { useWorkflowStore } from '@/stores/workflow'
import PromptDiff from '@/components/PromptDiff.vue'
import type { PromptOptimizationResponse } from '@/types/api'

const workflow = useWorkflowStore()
const runStore = useRunStore()
const workflowId = String(window.location.pathname.split('/')[2] ?? '')
const runId = ref(runStore.run?.id ?? '')
const nodeId = ref('')
const instruction = ref('')
const optimization = ref<PromptOptimizationResponse | null>(null)
const creating = ref(false)
const applying = ref(false)
const errorMessage = ref('')
const nodeLabels = computed(() => Object.fromEntries(((workflow.draft?.graph as { nodes?: Array<{ id: string; name: string }> })?.nodes ?? []).map((node) => [node.id, node.name])))
const llmTraces = computed(() => runStore.traces.filter((trace) => (workflow.draft?.graph as { nodes?: Array<{ id: string; type: string }> })?.nodes?.some((node) => node.id === trace.node_id && node.type === 'llm')))

onMounted(async () => { if (!workflow.draft && workflowId) { try { await workflow.loadDraft(workflowId) } catch (error) { errorMessage.value = getApiError(error).message } } if (!nodeId.value && llmTraces.value[0]) nodeId.value = llmTraces.value[0].node_id })

async function generate() {
  if (!runId.value || !nodeId.value || !instruction.value.trim()) { errorMessage.value = '请先选择运行、LLM 节点并填写优化指令。'; return }
  creating.value = true; errorMessage.value = ''
  try { optimization.value = await createPromptOptimization({ run_id: runId.value, node_id: nodeId.value, instruction: instruction.value.trim() }) } catch (error) { errorMessage.value = getApiError(error).message } finally { creating.value = false }
}

async function apply() {
  if (!optimization.value) return
  applying.value = true; errorMessage.value = ''
  try { optimization.value = await applyPromptOptimization(optimization.value.id); if (workflowId) await workflow.loadDraft(workflowId) } catch (error) { errorMessage.value = getApiError(error).message } finally { applying.value = false }
}
</script>

<style scoped>
.prompt-page { max-width: 1200px; margin: 0 auto; }.page-heading { display: flex; gap: 18px; align-items: flex-end; justify-content: space-between; margin-bottom: 22px; }.page-eyebrow { margin: 0 0 6px; color: var(--teal-700); font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.page-heading h2 { margin: 0; color: var(--ink-950); font-size: 27px; }.page-heading p:not(.page-eyebrow) { margin: 7px 0 0; color: var(--ink-650); font-size: 13px; }.draft-note { display: inline-flex; gap: 6px; align-items: center; padding: 6px 9px; color: var(--teal-700); font-size: 11px; background: #e4f2ee; border: 1px solid #acd1c7; border-radius: 999px; }.prompt-grid { display: grid; grid-template-columns: 310px minmax(0, 1fr); gap: 16px; }.control-panel,.result-panel { min-width: 0; padding: 16px; background: var(--paper-100); border: 1px solid var(--line); box-shadow: var(--shadow-panel); }.panel-title { display: flex; gap: 8px; justify-content: space-between; margin-bottom: 17px; padding-bottom: 12px; border-bottom: 1px solid var(--line); }.panel-title strong { color: var(--ink-950); font-size: 13px; }.panel-title span { color: var(--ink-650); font-size: 10px; }.control-panel :deep(.el-select) { width: 100%; }.primary-button { width: 100%; margin-top: 5px; background: var(--teal-700); border-color: var(--teal-700); }.form-error { margin: 0 0 10px; color: var(--red-700); font-size: 12px; line-height: 1.45; }.result-panel { min-height: 430px; }.result-empty { display: grid; justify-items: center; padding: 115px 20px; color: var(--ink-650); text-align: center; }.result-empty svg { color: var(--teal-700); }.result-empty p { max-width: 260px; font-size: 12px; line-height: 1.6; }.apply-row { display: flex; gap: 14px; align-items: center; justify-content: space-between; margin-top: 14px; padding-top: 13px; color: var(--ink-650); font-size: 11px; border-top: 1px solid var(--line); }.apply-row :deep(.el-button) { flex: 0 0 auto; background: var(--teal-700); border-color: var(--teal-700); }
@media (max-width: 900px) { .prompt-grid { grid-template-columns: 1fr; }.control-panel { max-width: none; } }.page-heading { flex-wrap: wrap; }
</style>
