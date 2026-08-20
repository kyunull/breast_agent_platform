<template>
  <section class="test-page">
    <div class="test-heading"><div><p class="page-eyebrow">运行与证据</p><h2>在线测试</h2><p>用一份脱敏样例检查资料提取、节点路径和最终方案。</p></div><div class="run-actions"><el-button :loading="running" type="primary" @click="run"><Play :size="15" />{{ running ? '运行中' : '运行样例' }}</el-button><el-button v-if="polling.active" title="取消运行" @click="cancel"><Square :size="14" />取消</el-button></div></div>
    <div class="run-config"><div><label for="version">工作流版本</label><el-select id="version" v-model="selectedVersion"><el-option label="当前草稿 · v0" :value="0" /><el-option v-for="version in workflow.versions" :key="version.id" :label="`已发布 · v${version.version_number}`" :value="version.version_number" /></el-select></div><div><label for="model">模型配置档案</label><el-select id="model" v-model="selectedModel" clearable placeholder="使用工作流默认"><el-option v-for="profile in modelProfiles" :key="profile.id" :label="profile.name" :value="profile.id" /></el-select></div><div><label>运行方式</label><el-radio-group v-model="mode"><el-radio-button label="sync">同步</el-radio-button><el-radio-button label="async">异步</el-radio-button></el-radio-group></div></div>
    <div v-if="errorMessage" class="notice notice--error"><CircleAlert :size="17" /><span>{{ errorMessage }}</span><button type="button" @click="errorMessage = ''">关闭</button></div>
    <div class="input-panel"><div class="input-panel__heading"><div><strong>脱敏测试输入</strong><span>仅用于当前运行，不写入浏览器持久存储。</span></div><button type="button" title="格式化 JSON" @click="formatInput"><WandSparkles :size="15" />格式化</button></div><el-input v-model="inputText" :rows="8" type="textarea" spellcheck="false" /></div>

    <div class="compare-grid"><JsonComparePane title="原始 JSON" subtitle="测试输入" :value="parsedInput" /><JsonComparePane title="提取结果" subtitle="提取预览" :value="extracted" /><section class="output-pane"><div class="output-pane__heading"><strong>最终输出</strong><span v-if="runStore.run">{{ statusLabel(runStore.run.status) }}</span></div><pre>{{ outputText }}</pre><div v-if="evidenceRefs.length" class="output-evidence"><span>引用证据</span><button v-for="ref in evidenceRefs" :key="ref" type="button" @click="openEvidence(ref)"><BookOpen :size="12" />{{ ref }}</button></div></section></div>
    <TraceTimeline :traces="runStore.traces" :node-labels="nodeLabels" @evidence="openEvidence" />
    <EvidenceDrawer :evidence="runStore.evidence" :error="evidenceError" :loading="evidenceLoading" :visible="runStore.isEvidenceOpen" @close="runStore.closeEvidence" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { BookOpen, CircleAlert, Play, Square, WandSparkles } from 'lucide-vue-next'

import { getApiError } from '@/api/client'
import { listModelProfiles } from '@/api/profiles'
import { cancelRun, createRun, getEvidence, getRun, getTraces } from '@/api/runs'
import { usePolling } from '@/composables/usePolling'
import { collectEvidenceRefs, formatRunError, isRunTerminal } from '@/composables/useRunUtils'
import { useRunStore } from '@/stores/run'
import { useWorkflowStore } from '@/stores/workflow'
import type { MedicalProfile, RunResponse } from '@/types/api'
import JsonComparePane from '@/components/JsonComparePane.vue'
import TraceTimeline from '@/components/TraceTimeline.vue'
import EvidenceDrawer from '@/components/EvidenceDrawer.vue'

const route = useRoute()
const workflow = useWorkflowStore()
const runStore = useRunStore()
const workflowId = String(route.params.id)
const modelProfiles = ref<MedicalProfile[]>([])
const selectedVersion = ref(0)
const selectedModel = ref('')
const mode = ref<'sync' | 'async'>('sync')
const inputText = ref(`{
  "pathology": { "her2": { "score": 3 } },
  "treatment_history": []
}`)
const extracted = ref<Record<string, unknown> | null>(null)
const errorMessage = ref('')
const running = ref(false)
const evidenceLoading = ref(false)
const evidenceError = ref('')
const currentRunId = ref('')
const polling = usePolling<RunResponse>(() => getRun(currentRunId.value), 1500)
const nodeLabels = computed(() => {
  const graph = workflow.draft?.graph as { nodes?: Array<{ id: string; name: string }> } | undefined
  return Object.fromEntries((graph?.nodes ?? []).map((node) => [node.id, node.name]))
})
const parsedInput = computed(() => { try { return JSON.parse(inputText.value) } catch { return null } })
const outputText = computed(() => runStore.run?.output ? JSON.stringify(runStore.run.output, null, 2) : runStore.run?.error ? formatRunError(runStore.run.error) : '运行后显示最终方案。')
const evidenceRefs = computed(() => collectEvidenceRefs(runStore.run?.output ?? null, runStore.traces))
const statusLabels: Record<string, string> = { queued: '排队', running: '运行中', succeeded: '完成', failed: '失败', cancelled: '已取消' }
const statusLabel = (status: string) => statusLabels[status] ?? status

onMounted(async () => {
  try { modelProfiles.value = await listModelProfiles() as MedicalProfile[] } catch (error) { errorMessage.value = getApiError(error).message }
})

watch(polling.latest, async (next) => { if (!next) return; runStore.setRun(next); if (isRunTerminal(next.status)) await loadTraces(next.id) })

function formatInput() { if (parsedInput.value) inputText.value = JSON.stringify(parsedInput.value, null, 2) }

async function run() {
  errorMessage.value = ''
  let input: Record<string, unknown>
  try { input = JSON.parse(inputText.value) } catch { errorMessage.value = '测试输入不是有效 JSON。'; return }
  running.value = true
  runStore.setTraces([])
  try {
    const created = await createRun({ workflow_id: workflowId, version_number: selectedVersion.value, input, mode: mode.value, ...(selectedModel.value ? { model_profile_id: selectedModel.value } : {}) })
    currentRunId.value = created.id
    runStore.setRun(created)
    if (created.output && typeof created.output === 'object' && 'extracted' in created.output) extracted.value = created.output.extracted as Record<string, unknown>
    if (isRunTerminal(created.status)) await loadTraces(created.id)
    else await polling.start()
  } catch (error) { errorMessage.value = getApiError(error).message } finally { running.value = false }
}

async function loadTraces(runId: string) { try { runStore.setTraces(await getTraces(runId)) } catch (error) { errorMessage.value = getApiError(error).message } }

async function cancel() { polling.stop(); if (currentRunId.value) { try { await cancelRun(currentRunId.value); const next = await getRun(currentRunId.value); runStore.setRun(next) } catch (error) { errorMessage.value = getApiError(error).message } } }

async function openEvidence(evidenceId: string) {
  if (!currentRunId.value) return
  evidenceLoading.value = true; evidenceError.value = ''; runStore.isEvidenceOpen = true
  try { runStore.openEvidence(await getEvidence(currentRunId.value, evidenceId)) } catch (error) { evidenceError.value = getApiError(error).message } finally { evidenceLoading.value = false }
}
</script>

<style scoped>
.test-page { max-width: 1380px; margin: 0 auto; }.test-heading { display: flex; gap: 20px; align-items: flex-end; justify-content: space-between; margin-bottom: 20px; }.page-eyebrow { margin: 0 0 6px; color: var(--teal-700); font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.test-heading h2 { margin: 0; color: var(--ink-950); font-size: 27px; }.test-heading p:not(.page-eyebrow) { margin: 7px 0 0; color: var(--ink-650); font-size: 13px; }.run-actions { display: flex; gap: 8px; }.run-actions :deep(.el-button--primary) { background: var(--teal-700); border-color: var(--teal-700); }.run-config { display: grid; grid-template-columns: minmax(170px, 1fr) minmax(190px, 1fr) max-content; gap: 14px; align-items: end; margin-bottom: 15px; padding: 14px; background: var(--paper-100); border: 1px solid var(--line); }.run-config label { display: block; margin-bottom: 5px; color: var(--ink-650); font-size: 10px; font-weight: 800; text-transform: uppercase; }.run-config :deep(.el-select) { width: 100%; }.notice { display: flex; gap: 10px; align-items: center; margin-bottom: 15px; padding: 11px 13px; color: var(--red-700); font-size: 12px; background: #fff0ef; border: 1px solid #e7bbb7; border-radius: var(--radius-sm); }.notice button { margin-left: auto; color: inherit; text-decoration: underline; cursor: pointer; background: transparent; border: 0; }.input-panel { margin-bottom: 18px; background: var(--paper-100); border: 1px solid var(--line); }.input-panel__heading { display: flex; gap: 10px; align-items: center; justify-content: space-between; padding: 11px 13px; border-bottom: 1px solid var(--line); }.input-panel__heading strong,.input-panel__heading span { display: block; }.input-panel__heading strong { color: var(--ink-950); font-size: 12px; }.input-panel__heading span { margin-top: 3px; color: var(--ink-650); font-size: 10px; }.input-panel__heading button { display: inline-flex; gap: 5px; align-items: center; color: var(--teal-700); font-size: 11px; cursor: pointer; background: transparent; border: 0; }.input-panel :deep(.el-textarea__inner) { min-height: 140px !important; padding: 12px; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; border: 0; border-radius: 0; }.compare-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }.output-pane { min-width: 0; background: #f7f8f4; border: 1px solid var(--line); }.output-pane__heading { display: flex; gap: 8px; justify-content: space-between; padding: 11px 13px; border-bottom: 1px solid var(--line); }.output-pane__heading strong { color: var(--ink-950); font-size: 12px; }.output-pane__heading span { color: var(--teal-700); font-size: 10px; }.output-pane pre { min-height: 180px; max-height: 310px; margin: 0; padding: 13px; overflow: auto; color: #48615e; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }.output-evidence { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; padding: 9px 13px; border-top: 1px solid var(--line); }.output-evidence > span { width: 100%; color: var(--ink-650); font-size: 10px; }.output-evidence button { display: inline-flex; gap: 4px; align-items: center; padding: 4px 6px; color: var(--teal-700); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; cursor: pointer; background: #e8f3ef; border: 1px solid #b6d8d0; border-radius: var(--radius-sm); }
@media (max-width: 980px) {
  .compare-grid { grid-template-columns: 1fr; }
  .run-config { grid-template-columns: 1fr 1fr; }
  .run-config > :last-child { grid-column: 1 / -1; }
}
.run-config :deep(.el-radio-group) { display: flex; }
.run-config :deep(.el-radio-button__inner) { padding: 8px 12px; }
@media (max-width: 620px) {
  .test-heading { display: block; }
  .test-heading h2 { font-size: 24px; }
  .run-actions { margin-top: 14px; }
  .run-actions :deep(.el-button) { flex: 1; }
  .run-config { grid-template-columns: 1fr; gap: 11px; padding: 12px; }
  .run-config > :last-child { grid-column: auto; }
  .input-panel__heading { align-items: flex-start; }
  .compare-grid { gap: 10px; }
}
</style>
