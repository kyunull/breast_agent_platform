<template>
  <div class="semantic-form">
    <div v-if="node.type === 'input'" class="form-intro"><strong>输入资料</strong><span>选择已定义的数据准备分组作为节点输入。</span></div>
    <el-form v-if="node.type === 'input'" label-position="top" size="small">
      <el-form-item label="资料分组"><el-select :model-value="stringConfig('group_id')" placeholder="选择提取分组" @update:model-value="setConfig('group_id', $event)"><el-option v-for="group in extractionGroups" :key="group.id" :label="group.label" :value="group.id" /></el-select></el-form-item>
    </el-form>

    <template v-else-if="node.type === 'condition'">
      <div class="form-intro"><strong>可视化条件</strong><span>把临床问题拆成可解释的分支，缺失值策略会保留在草稿中。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="组合方式"><el-radio-group :model-value="stringConfig('logic', 'AND')" @update:model-value="setConfig('logic', $event)"><el-radio-button label="AND" /><el-radio-button label="OR" /><el-radio-button label="NOT" /></el-radio-group></el-form-item><el-form-item label="判断字段"><el-input :model-value="stringConfig('left_path')" placeholder="例如：$.pathology.her2.score" @update:model-value="setConfig('left_path', $event)" /></el-form-item><el-form-item label="比较方式"><el-select :model-value="stringConfig('operator', 'exists')" @update:model-value="setConfig('operator', $event)"><el-option v-for="option in conditionOperators" :key="option.value" :label="option.label" :value="option.value" /></el-select></el-form-item><el-form-item label="比较值"><el-input :model-value="stringConfig('right_value')" placeholder="按比较方式填写" @update:model-value="setConfig('right_value', $event)" /></el-form-item><el-form-item label="缺失值策略"><el-select :model-value="stringConfig('missing_strategy', 'needs_review')" @update:model-value="setConfig('missing_strategy', $event)"><el-option label="标记待补充" value="needs_review" /><el-option label="按不满足处理" value="false" /><el-option label="终止运行" value="error" /></el-select></el-form-item><el-form-item label="出口标签"><el-input :model-value="stringConfig('branch_label', '满足条件')" @update:model-value="setConfig('branch_label', $event)" /></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'python_rule'">
      <div class="form-intro"><strong>规则处理</strong><span>优先用可视化规则；高级代码仅对管理员/开发人员开放。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="规则动作"><el-select :model-value="stringConfig('rule_kind', 'field_map')" @update:model-value="setConfig('rule_kind', $event)"><el-option label="字段映射" value="field_map" /><el-option label="列表筛选" value="list_filter" /><el-option label="文本清理" value="text_normalize" /></el-select></el-form-item><el-form-item label="输入字段"><el-input :model-value="stringConfig('input_path')" placeholder="例如：$.treatments" @update:model-value="setConfig('input_path', $event)" /></el-form-item><el-form-item label="输出字段"><el-input :model-value="stringConfig('output_alias')" placeholder="例如：latest_treatment" @update:model-value="setConfig('output_alias', $event)" /></el-form-item><el-form-item label="模拟样例"><el-input :model-value="stringConfig('sample_note')" placeholder="只写脱敏样例说明" @update:model-value="setConfig('sample_note', $event)" /></el-form-item><el-form-item v-if="auth.isAdmin" label="高级代码"><el-input :model-value="stringConfig('code')" :rows="5" type="textarea" placeholder="受控 RuleSpec/Python" @update:model-value="setConfig('code', $event)" /></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'rag'">
      <div class="form-intro"><strong>指南检索</strong><span>医学用户只选择已批准知识库和查询语义。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="知识库 Profile"><el-select :model-value="stringConfig('knowledge_profile_ref')" placeholder="选择知识库" @update:model-value="setConfig('knowledge_profile_ref', $event)"><el-option v-for="profile in knowledgeProfiles" :key="profile.id" :label="profile.name" :value="profile.id" /></el-select></el-form-item><el-form-item label="查询模板"><el-input :model-value="stringConfig('query_template')" :rows="3" type="textarea" placeholder="例如：{{her2_status}} 的晚期治疗建议" @update:model-value="setConfig('query_template', $event)" /></el-form-item><el-form-item label="无证据策略"><el-select :model-value="stringConfig('empty_strategy', 'needs_review')" @update:model-value="setConfig('empty_strategy', $event)"><el-option label="标记待核实" value="needs_review" /><el-option label="跳过本节点" value="skip" /><el-option label="终止运行" value="error" /></el-select></el-form-item><el-form-item label="引用要求"><el-switch :model-value="booleanConfig('citation_required', true)" @update:model-value="setConfig('citation_required', $event)" /></el-form-item><el-form-item v-if="auth.isAdmin" label="管理员检索参数"><el-input :model-value="stringConfig('technical_note')" placeholder="由 Profile 控制，不写入医学用户草稿" @update:model-value="setConfig('technical_note', $event)" /></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'llm'">
      <div class="form-intro"><strong>临床判断</strong><span>选择任务模板、提示词变量和语义化详细程度。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="任务模板"><el-select :model-value="stringConfig('task_template', '方案生成')" @update:model-value="setConfig('task_template', $event)"><el-option v-for="label in ['判断', '信息提取', '方案生成', '监测建议', '总结']" :key="label" :label="label" :value="label" /></el-select></el-form-item><el-form-item label="模型 Profile"><el-select :model-value="stringConfig('model_profile_ref')" placeholder="选择已批准模型" @update:model-value="setConfig('model_profile_ref', $event)"><el-option v-for="profile in modelProfiles" :key="profile.id" :label="profile.name" :value="profile.id" /></el-select></el-form-item><el-form-item label="详细程度"><el-radio-group :model-value="stringConfig('detail_level', 'standard')" @update:model-value="setConfig('detail_level', $event)"><el-radio-button label="简洁" value="concise" /><el-radio-button label="标准" value="standard" /><el-radio-button label="详细" value="detailed" /></el-radio-group></el-form-item><el-form-item label="任务提示词"><el-input :model-value="stringConfig('prompt')" :rows="5" type="textarea" placeholder="使用 {{变量名}} 引用提取字段或 RAG 证据" @update:model-value="setConfig('prompt', $event)" /></el-form-item><el-form-item label="引用不足策略"><el-select :model-value="stringConfig('citation_policy', 'required')" @update:model-value="setConfig('citation_policy', $event)"><el-option label="必须有可追溯证据" value="required" /><el-option label="允许标记待核实" value="optional" /></el-select></el-form-item><el-form-item v-if="auth.isAdmin" label="高级模型参数"><el-input :model-value="stringConfig('temperature')" placeholder="temperature / top_p / 超时由管理员维护" @update:model-value="setConfig('temperature', $event)" /></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'parallel_agent'">
      <div class="form-intro"><strong>并行 Agent</strong><span>拆分不同医学视角，完成后使用确定性方式合并。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="子任务（每行一个）"><el-input :model-value="stringConfig('tasks')" :rows="4" type="textarea" placeholder="疗效判断\n安全性监测\n指南差异" @update:model-value="setConfig('tasks', $event)" /></el-form-item><el-form-item label="合并方式"><el-select :model-value="stringConfig('merge_mode', 'deterministic')" @update:model-value="setConfig('merge_mode', $event)"><el-option label="确定性合并" value="deterministic" /><el-option label="汇总 LLM" value="llm_summary" /></el-select></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'output'">
      <div class="form-intro"><strong>方案输出</strong><span>定义最终 JSON 结构，引用会从上游继承。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="终点类型"><el-radio-group :model-value="stringConfig('endpoint', 'recommendation')" @update:model-value="setConfig('endpoint', $event)"><el-radio-button label="给出方案" value="recommendation" /><el-radio-button label="转入工作流" value="handoff" /></el-radio-group></el-form-item><el-form-item label="输出 Schema"><el-input :model-value="stringConfig('schema')" :rows="6" type="textarea" placeholder="填写字段结构和必填项" @update:model-value="setConfig('schema', $event)" /></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'clinical_task'">
      <div class="form-intro"><strong>资料补全任务</strong><span>列出缺口、来源和负责人，不伪造患者数据。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="待补充资料"><el-input :model-value="stringConfig('missing_fields')" :rows="3" type="textarea" @update:model-value="setConfig('missing_fields', $event)" /></el-form-item><el-form-item label="负责科室"><el-input :model-value="stringConfig('owner_department')" @update:model-value="setConfig('owner_department', $event)" /></el-form-item><el-form-item label="优先级"><el-select :model-value="stringConfig('priority', 'routine')" @update:model-value="setConfig('priority', $event)"><el-option label="常规" value="routine" /><el-option label="优先" value="high" /><el-option label="紧急" value="urgent" /></el-select></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'subworkflow'">
      <div class="form-intro"><strong>MDT 子工作流</strong><span>引用固定版本并声明输入输出契约。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="子工作流 ID"><el-input :model-value="stringConfig('workflow_id')" @update:model-value="setConfig('workflow_id', $event)" /></el-form-item><el-form-item label="引用版本"><el-input :model-value="stringConfig('version_number')" placeholder="发布版本号" @update:model-value="setConfig('version_number', $event)" /></el-form-item><el-form-item label="协作说明"><el-input :model-value="stringConfig('handoff_note')" :rows="3" type="textarea" @update:model-value="setConfig('handoff_note', $event)" /></el-form-item></el-form>
    </template>

    <template v-else-if="node.type === 'annotation'">
      <div class="form-intro"><strong>说明与协同</strong><span>承载医学备注、风险、时间、成本和外部文档链接。</span></div>
      <el-form label-position="top" size="small"><el-form-item label="说明内容"><el-input :model-value="stringConfig('note')" :rows="5" type="textarea" @update:model-value="setConfig('note', $event)" /></el-form-item><el-form-item label="外部链接"><el-input :model-value="stringConfig('external_url')" @update:model-value="setConfig('external_url', $event)" /></el-form-item></el-form>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { useAuthStore } from '@/stores/auth'
import type { MedicalProfile, ExtractionGroup } from '@/types/api'
import type { GraphNode as WorkflowGraphNode } from '@/types/graph'

const props = defineProps<{ node: WorkflowGraphNode; extractionGroups?: ExtractionGroup[]; modelProfiles?: MedicalProfile[]; knowledgeProfiles?: MedicalProfile[] }>()
const emit = defineEmits<{ update: [node: WorkflowGraphNode] }>()
const auth = useAuthStore()
const node = computed(() => props.node)
const extractionGroups = computed(() => props.extractionGroups ?? [])
const modelProfiles = computed(() => props.modelProfiles ?? [])
const knowledgeProfiles = computed(() => props.knowledgeProfiles ?? [])
const conditionOperators = [{ label: '存在', value: 'exists' }, { label: '为空', value: 'empty' }, { label: '等于', value: 'eq' }, { label: '大于', value: 'gt' }, { label: '包含', value: 'contains' }]

function stringConfig(key: string, fallback = '') {
  const value = node.value.config[key]
  return value === undefined || value === null ? fallback : String(value)
}

function booleanConfig(key: string, fallback = false) {
  const value = node.value.config[key]
  return value === undefined ? fallback : Boolean(value)
}

function setConfig(key: string, value: unknown) {
  emit('update', { ...node.value, config: { ...node.value.config, [key]: value } })
}
</script>

<style scoped>
.semantic-form { padding-top: 3px; }.form-intro { display: grid; gap: 5px; margin: 0 0 14px; padding: 10px; color: var(--ink-650); background: #eef4f0; border-left: 3px solid var(--teal-600); }.form-intro strong { color: var(--ink-950); font-size: 12px; }.form-intro span { font-size: 11px; line-height: 1.45; }.semantic-form :deep(.el-form-item) { margin-bottom: 13px; }.semantic-form :deep(.el-select) { width: 100%; }.semantic-form :deep(.el-radio-group) { display: flex; flex-wrap: wrap; }.semantic-form :deep(.el-radio-button__inner) { padding: 7px 9px; font-size: 11px; }.semantic-form :deep(.el-switch) { --el-switch-on-color: var(--teal-700); }
</style>
