<template>
  <section class="data-preparation">
    <div class="data-heading"><div><p class="page-eyebrow">数据准备</p><h3>患者入参字段配置</h3><p>按数据类别勾选需要提取的字段，保存时仍使用原始 JSONPath 保证运行时稳定。</p></div><div class="data-heading__actions"><span class="selection-summary"><CheckSquare :size="14" />已选择 {{ selectedFieldCount }} 个字段</span><el-button :loading="previewLoading" type="primary" @click="runPreview"><Play :size="15" />预览提取结果</el-button></div></div>
    <div class="data-columns">
      <div class="json-column">
        <div class="column-title"><span>入参字段目录</span><small>{{ schemaFieldCount }} 个字段</small></div>
        <el-input v-model="schemaFilter" clearable class="schema-search" placeholder="搜索中文字段或原始字段名"><template #prefix><Search :size="14" /></template></el-input>
        <el-tree ref="schemaTree" :data="schemaNodes" :props="{ label: 'label', children: 'children' }" :filter-node-method="filterSchemaNode" default-expand-all show-checkbox check-on-click-node class="json-tree schema-tree" node-key="key" @check="onSchemaCheck">
          <template #default="{ data }">
            <div class="schema-tree-node">
              <div class="schema-tree-node__main"><span>{{ data.label }}</span><small v-if="data.typeLabel">{{ data.typeLabel }}</small></div>
              <code v-if="data.field">{{ data.field.key }}</code>
            </div>
          </template>
        </el-tree>
        <details class="sample-json">
          <summary><FileJson :size="14" />样例 JSON（用于预览）</summary>
          <div class="sample-json__actions">
            <button type="button" title="上传完整 JSON" @click="sampleFileInput?.click()"><Upload :size="14" />上传完整 JSON</button>
            <input ref="sampleFileInput" class="file-input" type="file" accept=".json,application/json" @change="onSampleFileChange" />
            <span v-if="sampleFileName" title="已载入文件">已载入：{{ sampleFileName }}</span>
          </div>
          <p v-if="sampleFileError" class="sample-json__error">{{ sampleFileError }}</p>
          <el-input v-model="sampleText" :rows="8" type="textarea" placeholder="粘贴脱敏样例 JSON，例如 BC-001.json" />
        </details>
      </div>
      <div class="fields-column">
        <div class="column-title"><span>已选字段与分组</span><button type="button" title="新增分组" @click="addGroup"><Plus :size="15" /><span>新增分组</span></button></div>
        <div v-for="group in groups" :key="group.id" class="group-block">
          <div class="group-heading"><el-input v-model="group.label" size="small" placeholder="业务分组名称" @change="emitConfig" /><span class="group-count">{{ group.fields.length }} 个字段</span><span class="group-id">{{ group.id }}</span><button type="button" title="删除分组" @click="removeGroup(group.id)"><Trash2 :size="14" /></button></div>
          <div class="field-table-wrap"><table class="field-table"><thead><tr><th>字段名称</th><th>输出别名</th><th>JSONPath</th><th>类型</th><th>必填</th><th></th></tr></thead><tbody><tr v-for="field in group.fields" :key="`${group.id}-${field.alias}-${field.path}`"><td><div class="field-name-cell"><strong>{{ fieldDisplayName(field) }}</strong><small v-if="fieldDisplayType(field)">{{ fieldDisplayType(field) }}</small></div></td><td><el-input v-model="field.alias" size="small" @change="emitConfig" /></td><td><el-input v-model="field.path" size="small" @change="emitConfig" /></td><td><el-select v-model="field.type" size="small" @change="emitConfig"><el-option v-for="type in valueTypes" :key="type" :label="type.label" :value="type.value" /></el-select></td><td><el-checkbox v-model="field.required" @change="emitConfig" /></td><td><button type="button" title="删除字段" @click="removeField(group.id, field.alias)"><Trash2 :size="13" /></button></td></tr></tbody></table></div>
          <button class="add-field" type="button" @click="addField(group.id)"><Plus :size="13" />新增字段</button>
        </div>
        <div v-if="groups.length === 0" class="no-groups">从左侧字段目录勾选字段，或新增一个自定义分组。</div>
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
import { computed, nextTick, ref, watch } from 'vue'
import { CheckSquare, FileJson, Play, Plus, ScanSearch, Search, Trash2, Upload } from 'lucide-vue-next'
import type { TreeInstance } from 'element-plus'

import { previewExtraction, type ExtractionPreviewResponse } from '@/api/extraction'
import { getApiError } from '@/api/client'
import { extractionConfigToForms, serializeExtractionConfig, type ExtractionFieldForm, type ExtractionGroupForm } from '@/composables/useExtractionConfig'
import { readJsonDocument } from '@/composables/useJsonFileUpload'
import { BREAST_CANCER_INPUT_FIELDS, BREAST_CANCER_INPUT_SECTIONS, findBreastCancerInputField, type BreastCancerInputField } from '@/data/breastCancerInputSchema'
import type { ExtractionConfig } from '@/types/api'

const props = defineProps<{ workflowId: string; extraction: unknown }>()
const emit = defineEmits<{ update: [config: ExtractionConfig]; error: [message: string] }>()
const groups = ref<ExtractionGroupForm[]>([])
const sampleText = ref('')
const sampleFileInput = ref<HTMLInputElement>()
const sampleFileName = ref('')
const sampleFileError = ref('')
const schemaFilter = ref('')
const schemaTree = ref<TreeInstance>()
const preview = ref<ExtractionPreviewResponse | null>(null)
const previewLoading = ref(false)
const valueTypes = [{ value: 'any', label: '任意' }, { value: 'string', label: '文本' }, { value: 'number', label: '数值' }, { value: 'integer', label: '整数' }, { value: 'boolean', label: '布尔' }, { value: 'object', label: '对象' }, { value: 'array', label: '数组' }] as const
const previewOk = computed(() => Boolean(preview.value && Object.values(preview.value.sufficiency).every((result) => result.status === 'sufficient')))
const schemaFieldCount = computed(() => BREAST_CANCER_INPUT_FIELDS.length)
const selectedSchemaFields = computed(() => groups.value.flatMap((group) => group.fields).filter((field) => Boolean(findBreastCancerInputField(field.path))))
const selectedFieldCount = computed(() => selectedSchemaFields.value.length)
const schemaNodes = computed(() => BREAST_CANCER_INPUT_SECTIONS.map((section) => ({ key: section.id, label: section.label, typeLabel: section.isArray ? '重复记录' : '单条记录', children: section.fields.map((field) => ({ key: field.path, label: field.label, typeLabel: field.typeLabel, field })) })))

watch(() => props.extraction, (value) => { hydrateGroups(value) }, { immediate: true, deep: true })
watch(schemaFilter, (value) => schemaTree.value?.filter(value))

async function hydrateGroups(value: unknown) {
  const next = extractionConfigToForms(value)
  groups.value = next.length ? next : defaultSelectedGroups()
  if (!next.length) emitConfig()
  await nextTick()
  schemaTree.value?.setCheckedKeys(selectedSchemaFields.value.map((field) => field.path), true)
}

function emitConfig() { emit('update', serializeExtractionConfig(groups.value)) }

function addGroup() {
  const index = groups.value.length + 1
  groups.value.push({ id: `group_${index}`, label: `资料分组 ${index}`, fields: [createField('field_1', '$')] })
  emitConfig()
}

function removeGroup(id: string) { groups.value = groups.value.filter((group) => group.id !== id); emitConfig() }
function createField(alias: string, path: string, type: ExtractionFieldForm['type'] = 'any'): ExtractionFieldForm { return { alias, path, type, required: false, defaultValue: null, filterField: '', filterValue: '', sortBy: '', order: 'asc', take: 'all', timeFrom: '', timeTo: '' } }
function defaultSelectedGroups(): ExtractionGroupForm[] {
  return BREAST_CANCER_INPUT_SECTIONS.flatMap((section) => {
    const fields = section.fields.filter((field) => field.defaultSelected)
    return fields.length ? [{ id: section.id, label: section.label, fields: fields.map((field) => createField(field.key, field.path, field.type)) }] : []
  })
}
function addField(groupId: string) { const group = groups.value.find((item) => item.id === groupId); if (!group) return; group.fields.push(createField(`field_${group.fields.length + 1}`, '$')); emitConfig() }
function removeField(groupId: string, alias: string) { const group = groups.value.find((item) => item.id === groupId); if (!group) return; group.fields = group.fields.filter((field) => field.alias !== alias); emitConfig() }

function filterSchemaNode(value: string, data: { label?: string; field?: BreastCancerInputField }) {
  if (!value) return true
  const query = value.trim().toLowerCase()
  return `${data.label ?? ''} ${data.field?.key ?? ''} ${data.field?.path ?? ''}`.toLowerCase().includes(query)
}

function onSchemaCheck(_: unknown, info: { checkedKeys?: unknown[] }) {
  const checkedPaths = new Set((info.checkedKeys ?? []).map(String).filter((key) => key.startsWith('$.patient_data.')))
  const existingGroups = groups.value
  const existingFields = existingGroups.flatMap((group) => group.fields)
  const schemaGroups: ExtractionGroupForm[] = []
  for (const section of BREAST_CANCER_INPUT_SECTIONS) {
    const selected = section.fields.filter((field) => checkedPaths.has(field.path))
    if (!selected.length) continue
    const oldGroup = existingGroups.find((group) => group.id === section.id) ?? existingGroups.find((group) => group.fields.some((field) => findBreastCancerInputField(field.path)?.sectionId === section.id))
    const preservedCustom = oldGroup?.fields.filter((field) => !findBreastCancerInputField(field.path)) ?? []
    const fields = selected.map((field) => existingFields.find((item) => item.path === field.path) ?? createField(field.key, field.path, field.type))
    schemaGroups.push({ id: oldGroup?.id ?? section.id, label: oldGroup?.label ?? section.label, fields: [...fields, ...preservedCustom] })
  }
  const schemaSectionIds = new Set(BREAST_CANCER_INPUT_SECTIONS.map((section) => section.id))
  const customGroups = existingGroups.filter((group) => !schemaSectionIds.has(group.id) && !group.fields.some((field) => Boolean(findBreastCancerInputField(field.path))))
  groups.value = [...customGroups.filter((group) => group.fields.some((field) => field.path !== '$' || field.alias !== 'field_1')), ...schemaGroups]
  emitConfig()
}

function fieldDefinition(field: ExtractionFieldForm) {
  return findBreastCancerInputField(field.path)
}

function fieldDisplayName(field: ExtractionFieldForm) {
  return fieldDefinition(field)?.label ?? field.alias
}

function fieldDisplayType(field: ExtractionFieldForm) {
  return fieldDefinition(field)?.typeLabel ?? valueTypes.find((type) => type.value === field.type)?.label ?? field.type
}

async function onSampleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const result = await readJsonDocument(file)
    sampleText.value = result.text
    sampleFileName.value = result.name
    sampleFileError.value = ''
  } catch (error) {
    sampleFileName.value = ''
    sampleFileError.value = error instanceof Error ? error.message : '文件读取失败。'
    emit('error', sampleFileError.value)
  }
}

async function runPreview() {
  let payload: Record<string, unknown>
  try { payload = JSON.parse(sampleText.value) } catch { emit('error', '样例 JSON 解析失败，请检查格式。'); return }
  previewLoading.value = true
  try { preview.value = await previewExtraction(props.workflowId, payload, serializeExtractionConfig(groups.value)) } catch (error) { emit('error', getApiError(error).message) } finally { previewLoading.value = false }
}

</script>

<style scoped>
.data-preparation { padding: 20px; background: var(--paper-100); border: 1px solid var(--line); box-shadow: var(--shadow-panel); }.data-heading { display: flex; gap: 18px; align-items: flex-end; justify-content: space-between; margin-bottom: 18px; }.data-heading__actions { display: flex; gap: 12px; align-items: center; }.selection-summary { display: inline-flex; gap: 5px; align-items: center; color: var(--teal-700); font-size: 11px; font-weight: 700; white-space: nowrap; }.page-eyebrow { margin: 0 0 5px; color: var(--teal-700); font-size: 10px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.data-heading h3 { margin: 0; color: var(--ink-950); font-size: 18px; }.data-heading p:not(.page-eyebrow) { margin: 6px 0 0; color: var(--ink-650); font-size: 12px; }.data-heading :deep(.el-button) { background: var(--teal-700); border-color: var(--teal-700); }.data-columns { display: grid; grid-template-columns: minmax(260px, .9fr) minmax(560px, 1.8fr) minmax(220px, .8fr); min-height: 480px; border: 1px solid var(--line); }.json-column,.fields-column,.preview-column { min-width: 0; padding: 13px; }.json-column,.fields-column { border-right: 1px solid var(--line); }.column-title { display: flex; gap: 8px; align-items: center; justify-content: space-between; min-height: 27px; margin-bottom: 10px; color: var(--ink-950); font-size: 12px; font-weight: 800; }.column-title small { color: var(--ink-650); font-size: 10px; font-weight: 500; }.column-title button { display: inline-flex; gap: 4px; align-items: center; color: var(--teal-700); font-size: 11px; cursor: pointer; background: transparent; border: 0; }.schema-search :deep(.el-input__wrapper) { box-shadow: 0 0 0 1px #d4ded7 inset; }.json-column :deep(.el-textarea__inner) { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; }.json-tree { max-height: 390px; margin-top: 10px; overflow: auto; font-size: 11px; background: transparent; }.schema-tree :deep(.el-tree-node__content) { min-height: 30px; height: auto; padding: 3px 0; }.schema-tree-node { display: flex; width: 100%; min-width: 0; gap: 8px; align-items: center; justify-content: space-between; padding-right: 7px; }.schema-tree-node__main { display: inline-flex; min-width: 0; gap: 7px; align-items: center; }.schema-tree-node__main > span { overflow: hidden; color: var(--ink-850); text-overflow: ellipsis; white-space: nowrap; }.schema-tree-node__main small { flex: 0 0 auto; padding: 2px 5px; color: var(--teal-700); font-size: 9px; background: #e6f1ec; border-radius: 3px; }.schema-tree-node code { flex: 0 0 auto; max-width: 130px; overflow: hidden; color: #84908d; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }.sample-json { margin-top: 11px; padding-top: 10px; border-top: 1px solid var(--line); }.sample-json summary { display: flex; gap: 6px; align-items: center; color: var(--ink-800); font-size: 11px; font-weight: 700; cursor: pointer; list-style: none; }.sample-json summary::-webkit-details-marker { display: none; }.sample-json summary::after { margin-left: auto; color: var(--ink-650); content: '展开'; font-size: 10px; font-weight: 500; }.sample-json[open] summary::after { content: '收起'; }.sample-json :deep(.el-textarea) { margin-top: 9px; }.group-block { margin-bottom: 13px; padding: 10px; background: #f7f8f3; border: 1px solid #d5dbd5; }.group-heading { display: grid; grid-template-columns: minmax(120px, 1fr) max-content max-content 24px; gap: 7px; align-items: center; margin-bottom: 8px; }.group-heading :deep(.el-input__wrapper) { padding: 2px 7px; box-shadow: none; }.group-count { color: var(--teal-700); font-size: 10px; white-space: nowrap; }.group-id { color: #82908d; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 9px; }.group-heading button,.field-table button { display: grid; width: 23px; height: 23px; color: var(--red-700); place-items: center; cursor: pointer; background: transparent; border: 0; }.field-table-wrap { overflow-x: auto; }.field-table { width: 100%; min-width: 700px; border-collapse: collapse; }.field-table th { padding: 4px 5px; color: var(--ink-650); font-size: 9px; text-align: left; text-transform: uppercase; }.field-table td { padding: 5px 4px; vertical-align: middle; border-top: 1px solid #e0e4df; }.field-name-cell { display: grid; gap: 2px; min-width: 106px; }.field-name-cell strong { overflow: hidden; color: var(--ink-850); font-size: 10px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }.field-name-cell small { color: var(--teal-700); font-size: 9px; }.field-table :deep(.el-select) { width: 78px; }.field-table :deep(input) { font-size: 10px; }.add-field { display: inline-flex; gap: 4px; align-items: center; margin-top: 6px; color: var(--teal-700); font-size: 10px; cursor: pointer; background: transparent; border: 0; }.no-groups { padding: 30px 10px; color: var(--ink-650); font-size: 12px; text-align: center; }.preview-column { background: #f7f8f4; }.preview-status { padding: 3px 6px; font-size: 10px; border: 1px solid; border-radius: 999px; }.is-ok { color: var(--teal-700); background: #e2f2ed; border-color: #9bc8be; }.is-warning { color: var(--amber-600); background: #fff4da; border-color: #e8c77e; }.preview-empty { display: grid; justify-items: center; padding: 75px 12px; color: var(--ink-650); text-align: center; }.preview-empty svg { color: var(--teal-700); }.preview-empty p { max-width: 190px; font-size: 11px; line-height: 1.6; }.preview-group { margin-bottom: 13px; }.preview-group__title { display: flex; justify-content: space-between; color: var(--ink-800); font-size: 11px; }.preview-group__title span { color: var(--teal-700); }.preview-group pre { max-height: 130px; margin: 7px 0; padding: 8px; overflow: auto; color: #49605e; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; line-height: 1.45; background: #edf2ee; border: 1px solid #d7ded8; }.missing,.error-line { margin: 4px 0; color: var(--amber-600); font-size: 10px; line-height: 1.45; }.error-line { color: var(--red-700); }
@media (max-width: 1120px) { .data-columns { grid-template-columns: 220px minmax(520px, 1fr) 250px; overflow-x: auto; } .json-column,.fields-column,.preview-column { width: auto; } }.data-columns { overflow-x: auto; }
.file-input { display: none; }
.sample-json__actions { display: flex; min-width: 0; gap: 8px; align-items: center; margin-top: 10px; }
.sample-json__actions button { display: inline-flex; flex: 0 0 auto; gap: 5px; align-items: center; padding: 6px 8px; color: var(--teal-700); font-size: 10px; font-weight: 700; cursor: pointer; background: #e8f3ef; border: 1px solid #b6d8d0; border-radius: var(--radius-sm); }
.sample-json__actions button:active { transform: translateY(1px); }
.sample-json__actions span { min-width: 0; overflow: hidden; color: var(--ink-650); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.sample-json__error { margin: 7px 0 0; color: var(--red-700); font-size: 10px; line-height: 1.5; }
@media (max-width: 760px) { .data-preparation { padding: 14px; overflow-x: hidden; }.data-heading { display: block; margin-bottom: 14px; }.data-heading :deep(.el-button) { width: 100%; margin-top: 14px; }.data-columns { display: block; overflow-x: hidden; }.json-column,.fields-column,.preview-column { padding: 12px; border-right: 0; }.json-column,.fields-column { border-bottom: 1px solid var(--line); }.preview-column { min-height: 180px; }.field-table-wrap { margin-right: -2px; }.preview-empty { padding: 42px 12px; } }
</style>
