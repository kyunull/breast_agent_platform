<template>
  <section class="data-preparation">
    <div class="data-heading"><div><p class="page-eyebrow">数据准备</p><h3>全量 JSON 数据准备</h3><p>用字段路径和分组定义工作流需要的最小资料集。</p></div><el-button :loading="previewLoading" type="primary" @click="runPreview"><Play :size="15" />预览提取结果</el-button></div>
    <div class="data-columns">
      <div class="json-column">
        <div class="column-title"><span>原始 JSON 树</span><small>{{ pathNodes.length }} 个可选路径</small></div>
        <el-input v-model="sampleText" :rows="13" type="textarea" placeholder="粘贴脱敏样例 JSON" @change="refreshPaths" />
        <el-tree v-if="pathNodes.length" :data="pathNodes" :props="{ label: 'label', children: 'children' }" default-expand-all class="json-tree" node-key="path" @node-click="onPathClick" />
      </div>
      <div class="fields-column">
        <div class="column-title"><span>字段与分组</span><button type="button" title="新增分组" @click="addGroup"><Plus :size="15" /><span>新增分组</span></button></div>
        <div v-for="group in groups" :key="group.id" class="group-block">
          <div class="group-heading"><el-input v-model="group.label" size="small" placeholder="业务分组名称" @change="emitConfig" /><span class="group-id">{{ group.id }}</span><button type="button" title="删除分组" @click="removeGroup(group.id)"><Trash2 :size="14" /></button></div>
          <div class="field-table-wrap"><table class="field-table"><thead><tr><th>别名</th><th>路径</th><th>类型</th><th>必填</th><th></th></tr></thead><tbody><tr v-for="field in group.fields" :key="field.alias"><td><el-input v-model="field.alias" size="small" @change="emitConfig" /></td><td><el-input v-model="field.path" size="small" @change="emitConfig" /></td><td><el-select v-model="field.type" size="small" @change="emitConfig"><el-option v-for="type in valueTypes" :key="type" :label="type" :value="type" /></el-select></td><td><el-checkbox v-model="field.required" @change="emitConfig" /></td><td><button type="button" title="删除字段" @click="removeField(group.id, field.alias)"><Trash2 :size="13" /></button></td></tr></tbody></table></div>
          <button class="add-field" type="button" @click="addField(group.id)"><Plus :size="13" />新增字段</button>
        </div>
        <div v-if="groups.length === 0" class="no-groups">先新增一个业务分组，再从左侧路径选择字段。</div>
      </div>
      <div class="preview-column">
        <div class="column-title"><span>提取预览</span><span v-if="preview" class="preview-status" :class="previewOk ? 'is-ok' : 'is-warning'">{{ previewOk ? '资料充分' : '存在缺口' }}</span></div>
        <div v-if="preview" class="preview-content"><div v-for="group in groups" :key="group.id" class="preview-group"><div class="preview-group__title"><strong>{{ group.label }}</strong><span>{{ preview.sufficiency[group.id]?.status === 'sufficient' ? '充分' : '不足' }}</span></div><pre>{{ JSON.stringify(preview.groups[group.id] ?? {}, null, 2) }}</pre><p v-if="preview.missing[group.id]?.length" class="missing">缺失：{{ preview.missing[group.id].join('、') }}</p><p v-for="(message, alias) in preview.errors[group.id]" :key="alias" class="error-line">{{ alias }}：{{ message }}</p></div></div>
        <div v-else class="preview-empty"><ScanSearch :size="22" /><p>填写脱敏样例 JSON 后，点击“预览提取结果”。</p></div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Play, Plus, ScanSearch, Trash2 } from 'lucide-vue-next'

import { previewExtraction, type ExtractionPreviewResponse } from '@/api/extraction'
import { getApiError } from '@/api/client'
import { extractionConfigToForms, serializeExtractionConfig, type ExtractionFieldForm, type ExtractionGroupForm } from '@/composables/useExtractionConfig'
import type { ExtractionConfig } from '@/types/api'

const props = defineProps<{ workflowId: string; extraction: unknown }>()
const emit = defineEmits<{ update: [config: ExtractionConfig]; error: [message: string] }>()
const groups = ref<ExtractionGroupForm[]>([])
const sampleText = ref(`{
  "pathology": { "her2": { "score": 3 } }
}`)
const pathNodes = ref<Array<{ label: string; path: string; children?: unknown[] }>>([])
const preview = ref<ExtractionPreviewResponse | null>(null)
const previewLoading = ref(false)
const valueTypes = ['any', 'string', 'number', 'integer', 'boolean', 'object', 'array'] as const
const previewOk = computed(() => Boolean(preview.value && Object.values(preview.value.sufficiency).every((result) => result.status === 'sufficient')))

watch(() => props.extraction, (value) => { groups.value = extractionConfigToForms(value); if (!groups.value.length) addGroup(); }, { immediate: true, deep: true })

function emitConfig() { emit('update', serializeExtractionConfig(groups.value)) }

function addGroup() {
  const index = groups.value.length + 1
  groups.value.push({ id: `group_${index}`, label: `资料分组 ${index}`, fields: [createField('field_1', '$')] })
  emitConfig()
}

function removeGroup(id: string) { groups.value = groups.value.filter((group) => group.id !== id); emitConfig() }
function createField(alias: string, path: string): ExtractionFieldForm { return { alias, path, type: 'any', required: false, defaultValue: null, filterField: '', filterValue: '', sortBy: '', order: 'asc', take: 'all', timeFrom: '', timeTo: '' } }
function addField(groupId: string) { const group = groups.value.find((item) => item.id === groupId); if (!group) return; group.fields.push(createField(`field_${group.fields.length + 1}`, '$')); emitConfig() }
function removeField(groupId: string, alias: string) { const group = groups.value.find((item) => item.id === groupId); if (!group) return; group.fields = group.fields.filter((field) => field.alias !== alias); emitConfig() }

function refreshPaths() {
  try { pathNodes.value = buildPaths(JSON.parse(sampleText.value)) } catch { pathNodes.value = [] }
}

function buildPaths(value: unknown, base = '$'): Array<{ label: string; path: string; children?: unknown[] }> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return [{ label: base, path: base }]
  return Object.entries(value as Record<string, unknown>).map(([key, child]) => { const path = `${base}.${key}`; return { label: `${key}  ${path}`, path, ...(child && typeof child === 'object' && !Array.isArray(child) ? { children: buildPaths(child, path) } : {}) } })
}

function onPathClick(data: { path: string }) {
  const target = groups.value[0]
  if (!target) return
  const empty = target.fields.find((field) => field.path === '$' || !field.alias)
  if (empty) { empty.path = data.path; empty.alias = data.path.split('.').pop() || 'field'; emitConfig() }
}

async function runPreview() {
  let payload: Record<string, unknown>
  try { payload = JSON.parse(sampleText.value) } catch { emit('error', '样例 JSON 解析失败，请检查格式。'); return }
  previewLoading.value = true
  try { preview.value = await previewExtraction(props.workflowId, payload, serializeExtractionConfig(groups.value)) } catch (error) { emit('error', getApiError(error).message) } finally { previewLoading.value = false }
}

refreshPaths()
</script>

<style scoped>
.data-preparation { padding: 20px; background: var(--paper-100); border: 1px solid var(--line); box-shadow: var(--shadow-panel); }.data-heading { display: flex; gap: 18px; align-items: flex-end; justify-content: space-between; margin-bottom: 18px; }.page-eyebrow { margin: 0 0 5px; color: var(--teal-700); font-size: 10px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.data-heading h3 { margin: 0; color: var(--ink-950); font-size: 18px; }.data-heading p:not(.page-eyebrow) { margin: 6px 0 0; color: var(--ink-650); font-size: 12px; }.data-heading :deep(.el-button) { background: var(--teal-700); border-color: var(--teal-700); }.data-columns { display: grid; grid-template-columns: minmax(210px, .8fr) minmax(420px, 1.6fr) minmax(220px, .9fr); min-height: 390px; border: 1px solid var(--line); }.json-column,.fields-column,.preview-column { min-width: 0; padding: 13px; }.json-column,.fields-column { border-right: 1px solid var(--line); }.column-title { display: flex; gap: 8px; align-items: center; justify-content: space-between; min-height: 27px; margin-bottom: 10px; color: var(--ink-950); font-size: 12px; font-weight: 800; }.column-title small { color: var(--ink-650); font-size: 10px; font-weight: 500; }.column-title button { display: inline-flex; gap: 4px; align-items: center; color: var(--teal-700); font-size: 11px; cursor: pointer; background: transparent; border: 0; }.json-column :deep(.el-textarea__inner) { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; }.json-tree { max-height: 220px; margin-top: 10px; overflow: auto; font-size: 11px; background: transparent; }.group-block { margin-bottom: 13px; padding: 10px; background: #f7f8f3; border: 1px solid #d5dbd5; }.group-heading { display: grid; grid-template-columns: minmax(100px, 1fr) max-content 24px; gap: 7px; align-items: center; margin-bottom: 8px; }.group-heading :deep(.el-input__wrapper) { padding: 2px 7px; box-shadow: none; }.group-id { color: #82908d; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 9px; }.group-heading button,.field-table button { display: grid; width: 23px; height: 23px; color: var(--red-700); place-items: center; cursor: pointer; background: transparent; border: 0; }.field-table-wrap { overflow-x: auto; }.field-table { width: 100%; min-width: 510px; border-collapse: collapse; }.field-table th { padding: 4px 5px; color: var(--ink-650); font-size: 9px; text-align: left; text-transform: uppercase; }.field-table td { padding: 3px 4px; border-top: 1px solid #e0e4df; }.field-table :deep(.el-select) { width: 100px; }.field-table :deep(input) { font-size: 10px; }.add-field { display: inline-flex; gap: 4px; align-items: center; margin-top: 6px; color: var(--teal-700); font-size: 10px; cursor: pointer; background: transparent; border: 0; }.no-groups { padding: 30px 10px; color: var(--ink-650); font-size: 12px; text-align: center; }.preview-column { background: #f7f8f4; }.preview-status { padding: 3px 6px; font-size: 10px; border: 1px solid; border-radius: 999px; }.is-ok { color: var(--teal-700); background: #e2f2ed; border-color: #9bc8be; }.is-warning { color: var(--amber-600); background: #fff4da; border-color: #e8c77e; }.preview-empty { display: grid; justify-items: center; padding: 75px 12px; color: var(--ink-650); text-align: center; }.preview-empty svg { color: var(--teal-700); }.preview-empty p { max-width: 190px; font-size: 11px; line-height: 1.6; }.preview-group { margin-bottom: 13px; }.preview-group__title { display: flex; justify-content: space-between; color: var(--ink-800); font-size: 11px; }.preview-group__title span { color: var(--teal-700); }.preview-group pre { max-height: 130px; margin: 7px 0; padding: 8px; overflow: auto; color: #49605e; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; line-height: 1.45; background: #edf2ee; border: 1px solid #d7ded8; }.missing,.error-line { margin: 4px 0; color: var(--amber-600); font-size: 10px; line-height: 1.45; }.error-line { color: var(--red-700); }
@media (max-width: 1120px) { .data-columns { grid-template-columns: 220px minmax(520px, 1fr) 250px; overflow-x: auto; } .json-column,.fields-column,.preview-column { width: auto; } }.data-columns { overflow-x: auto; }
@media (max-width: 760px) { .data-preparation { padding: 14px; }.data-heading { display: block; margin-bottom: 14px; }.data-heading :deep(.el-button) { width: 100%; margin-top: 14px; }.data-columns { display: block; overflow: visible; }.json-column,.fields-column,.preview-column { padding: 12px; border-right: 0; }.json-column,.fields-column { border-bottom: 1px solid var(--line); }.preview-column { min-height: 180px; }.field-table-wrap { margin-right: -2px; }.preview-empty { padding: 42px 12px; } }
</style>
