<template>
  <section class="profiles-page">
    <header class="page-heading">
      <div>
        <p class="page-eyebrow">管理员配置</p>
        <h2>系统配置</h2>
        <span>模型连接、知识检索与医学可见性</span>
      </div>
      <el-button type="primary" @click="openCreate">
        <Plus :size="16" />{{ kind === 'model' ? '新增模型服务' : '新增知识库服务' }}
      </el-button>
    </header>

    <p v-if="errorMessage" class="notice notice--error">
      <CircleAlert :size="16" />{{ errorMessage }} <button @click="refresh">重试</button>
    </p>

    <div class="profile-tabs" role="tablist" aria-label="服务类型">
      <button :class="{ active: kind === 'model' }" role="tab" :aria-selected="kind === 'model'" @click="kind = 'model'">
        <BrainCircuit :size="17" />模型服务 <span>{{ modelProfiles.length }}</span>
      </button>
      <button :class="{ active: kind === 'knowledge' }" role="tab" :aria-selected="kind === 'knowledge'" @click="kind = 'knowledge'">
        <Database :size="17" />知识库服务 <span>{{ knowledgeProfiles.length }}</span>
      </button>
    </div>

    <div v-if="loading" class="loading-state">正在读取系统配置...</div>
    <div v-else-if="activeProfiles.length" class="service-list">
      <article v-for="profile in activeProfiles" :key="profile.id" class="service-row">
        <div class="service-mark" :class="`service-mark--${kind}`">
          <BrainCircuit v-if="kind === 'model'" :size="19" />
          <Database v-else :size="19" />
        </div>
        <div class="service-identity">
          <div class="service-title">
            <h3>{{ profile.name }}</h3>
            <span class="provider-badge">{{ providerLabel(profile) }}</span>
          </div>
          <p>{{ profile.description || '暂无说明' }}</p>
        </div>
        <div class="service-facts">
          <div><span>{{ kind === 'model' ? '模型' : '检索设置' }}</span><strong>{{ serviceCapability(profile) }}</strong></div>
          <div class="service-endpoint"><span>服务地址</span><strong>{{ serviceAddress(profile) }}</strong></div>
          <div><span>凭据</span><strong><KeyRound :size="13" />{{ credentialLabel(profile) }}</strong></div>
        </div>
        <div class="service-status">
          <span class="status-pill" :class="{ 'status-pill--off': !isActive(profile) }"><i />{{ isActive(profile) ? '运行中' : '已停用' }}</span>
          <span class="visibility"><Eye v-if="profile.exposed_to_medical" :size="13" /><LockKeyhole v-else :size="13" />{{ profile.exposed_to_medical ? '对医学用户开放' : '仅管理员可用' }}</span>
        </div>
        <button class="icon-button" :title="`编辑${profile.name}`" :aria-label="`编辑${profile.name}`" @click="openEdit(profile)">
          <Pencil :size="15" />
        </button>
      </article>
    </div>
    <div v-else class="empty-state">
      <component :is="kind === 'model' ? BrainCircuit : Database" :size="26" />
      <strong>{{ kind === 'model' ? '还没有模型服务' : '还没有知识库服务' }}</strong>
      <span>创建第一条配置后即可在工作流节点中选择。</span>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="min(800px, calc(100vw - 28px))" class="profile-dialog" destroy-on-close>
      <el-form v-if="kind === 'model'" label-position="top" class="profile-form">
        <section class="form-section">
          <div class="section-heading"><Info :size="16" /><div><h3>基本信息</h3><p>用于在工作流中识别此服务。</p></div></div>
          <div class="form-grid"><el-form-item label="名称"><el-input v-model="modelForm.name" /></el-form-item><el-form-item label="说明"><el-input v-model="modelForm.description" /></el-form-item></div>
          <div class="switch-panel"><label><span><strong>启用服务</strong><small>停用后不可用于新任务</small></span><el-switch v-model="modelForm.is_active" /></label><label><span><strong>医学用户可见</strong><small>可在医学工作流中选择</small></span><el-switch v-model="modelForm.exposed_to_medical" /></label></div>
        </section>
        <section class="form-section">
          <div class="section-heading"><Cable :size="16" /><div><h3>模型连接</h3><p>OpenAI 兼容接口</p></div></div>
          <div class="form-grid"><el-form-item label="服务地址"><el-input v-model="modelForm.base_url" placeholder="https://api.example.com/v1" /></el-form-item><el-form-item label="模型"><el-input v-model="modelForm.model" placeholder="模型标识" /></el-form-item><el-form-item class="span-two" label="API Key"><el-input v-model="modelForm.api_key" type="password" autocomplete="new-password" :placeholder="modelForm.api_key_configured ? '已配置，留空将保留当前密钥' : '请输入服务 API Key'"><template #prefix><KeyRound :size="14" /></template></el-input><p class="field-note">密钥仅以加密形式保存在服务端，页面始终掩码显示。</p></el-form-item></div>
          <div class="test-row"><el-button :loading="testing" @click="runConnectionTest"><PlugZap :size="15" />测试连接</el-button><span v-if="testMessage" class="inline-result"><CircleCheck :size="14" />{{ testMessage }}</span></div>
        </section>
        <section class="form-section">
          <div class="section-heading"><SlidersHorizontal :size="16" /><div><h3>运行参数</h3><p>留空时使用服务默认值</p></div></div>
          <div class="form-grid form-grid--three"><el-form-item label="温度"><el-input v-model="modelForm.temperature" /></el-form-item><el-form-item label="采样概率"><el-input v-model="modelForm.top_p" /></el-form-item><el-form-item label="最大输出长度"><el-input v-model="modelForm.max_tokens" /></el-form-item><el-form-item label="超时（秒）"><el-input v-model="modelForm.timeout" /></el-form-item><el-form-item label="重试次数"><el-input v-model="modelForm.retries" /></el-form-item></div>
        </section>
        <section class="form-section">
          <div class="section-heading"><Stethoscope :size="16" /><div><h3>医学使用范围</h3><p>帮助使用者选择合适的模型。</p></div></div>
          <div class="form-grid"><el-form-item label="显示名称"><el-input v-model="modelForm.display_name" /></el-form-item><el-form-item label="临床适用范围"><el-input v-model="modelForm.clinical_scope" /></el-form-item><el-form-item label="支持任务"><el-input v-model="modelForm.supported_tasks" placeholder="总结, 抽取, 推理" /></el-form-item><el-form-item label="输出风格"><el-input v-model="modelForm.output_style" /></el-form-item></div>
        </section>
      </el-form>

      <el-form v-else label-position="top" class="profile-form">
        <section class="form-section">
          <div class="section-heading"><Info :size="16" /><div><h3>基本信息</h3><p>用于在 RAG 节点中识别此知识库。</p></div></div>
          <div class="form-grid"><el-form-item label="名称"><el-input v-model="knowledgeForm.name" /></el-form-item><el-form-item label="说明"><el-input v-model="knowledgeForm.description" /></el-form-item></div>
          <div class="switch-panel"><label><span><strong>启用服务</strong><small>停用后不可用于新任务</small></span><el-switch v-model="knowledgeForm.is_active" /></label><label><span><strong>医学用户可见</strong><small>可在医学工作流中选择</small></span><el-switch v-model="knowledgeForm.exposed_to_medical" /></label></div>
        </section>
        <section class="form-section">
          <div class="section-heading"><Cable :size="16" /><div><h3>检索连接</h3><p>地址与接口适配方式</p></div></div>
          <div class="form-grid">
            <el-form-item label="提供方"><el-select v-model="knowledgeForm.provider"><el-option label="本地知识库" value="knowledgebase" /><el-option label="通用 HTTP 接口" value="generic_http" /></el-select></el-form-item>
            <el-form-item label="检索路径"><el-input v-model="knowledgeForm.search_path" placeholder="/search" /></el-form-item>
            <el-form-item class="span-two" label="服务地址"><el-input v-model="knowledgeForm.base_url" placeholder="http://127.0.0.1:8101"><template #prefix><Server :size="14" /></template></el-input></el-form-item>
            <el-form-item class="span-two" label="密钥环境变量引用（可选）"><el-input v-model="knowledgeForm.api_key_ref" placeholder="无需鉴权时留空"><template #prefix><KeyRound :size="14" /></template></el-input><p class="field-note">仅保存引用；本地知识库默认无需凭据。</p></el-form-item>
          </div>
        </section>
        <section class="form-section">
          <div class="section-heading"><SlidersHorizontal :size="16" /><div><h3>检索参数</h3><p>控制每次节点检索的范围。</p></div></div>
          <div class="retrieval-grid"><el-form-item label="返回条数"><el-input-number v-model="knowledgeForm.top_k" :min="1" :max="50" controls-position="right" /></el-form-item><el-form-item label="超时（秒）"><el-input-number v-model="knowledgeForm.timeout" :min="1" :max="600" controls-position="right" /></el-form-item><label class="setting-toggle"><span><strong>关键词混合检索</strong><small>结合 BM25 与语义检索</small></span><el-switch v-model="knowledgeForm.bm25" /></label></div>
          <details v-if="knowledgeForm.provider === 'generic_http'" class="advanced-options">
            <summary>高级响应映射</summary>
            <div class="form-grid"><el-form-item label="查询字段"><el-input v-model="knowledgeForm.query_field" /></el-form-item><el-form-item label="结果路径"><el-input v-model="knowledgeForm.result_path" /></el-form-item><el-form-item class="span-two" label="字段映射"><el-input v-model="knowledgeForm.field_mapping" type="textarea" :rows="4" /></el-form-item></div>
          </details>
        </section>
        <section class="form-section preview-section">
          <div class="section-heading"><Search :size="16" /><div><h3>测试检索</h3><p>使用当前已保存配置验证节点检索链路。</p></div></div>
          <div v-if="editing" class="preview-controls"><el-input v-model="previewQuery" placeholder="输入一条医学问题" @keyup.enter="runKnowledgePreview" /><el-button :loading="testingKnowledge" @click="runKnowledgePreview"><Search :size="15" />测试检索</el-button></div>
          <p v-else class="save-first">保存配置后可进行实际检索测试。</p>
          <p v-if="previewMessage" class="preview-message" :class="{ 'preview-message--error': previewFailed }"><CircleCheck v-if="!previewFailed" :size="14" /><CircleAlert v-else :size="14" />{{ previewMessage }}</p>
          <ul v-if="previewEvidence.length" class="evidence-preview">
            <li v-for="evidence in previewEvidence.slice(0, 3)" :key="evidence.evidence_id"><div><strong>{{ evidence.source_title || evidence.guideline_id || '知识库证据' }}</strong><span>{{ evidence.locator || '来源位置未提供' }}</span></div><p>{{ evidence.text }}</p></li>
          </ul>
        </section>
      </el-form>

      <p v-if="formError" class="form-error"><CircleAlert :size="15" />{{ formError }}</p>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存配置</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { BrainCircuit, Cable, CircleAlert, CircleCheck, Database, Eye, Info, KeyRound, LockKeyhole, Pencil, PlugZap, Plus, Search, Server, SlidersHorizontal, Stethoscope } from 'lucide-vue-next'
import { getApiError } from '@/api/client'
import { createKnowledgeProfile, createModelProfile, listKnowledgeProfiles, listModelProfiles, patchKnowledgeProfile, patchModelProfile, previewKnowledge, testModelProfile, type ModelProfileConnectionTestPayload } from '@/api/profiles'
import { knowledgeFormToPayload, knowledgeProfileToForm, type KnowledgeProfileForm } from '@/composables/useKnowledgeProfileForm'
import { modelFormToPayload, modelProfileToForm, type ModelProfileForm } from '@/composables/useModelProfileForm'
import type { EvidenceResponse, Profile, ProfileCreatePayload } from '@/types/api'

const kind = ref<'model' | 'knowledge'>('model')
const modelProfiles = ref<Profile[]>([])
const knowledgeProfiles = ref<Profile[]>([])
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testingKnowledge = ref(false)
const dialogVisible = ref(false)
const editing = ref<Profile | null>(null)
const errorMessage = ref('')
const formError = ref('')
const testMessage = ref('')
const previewQuery = ref('')
const previewMessage = ref('')
const previewFailed = ref(false)
const previewEvidence = ref<EvidenceResponse[]>([])
const modelForm = reactive<ModelProfileForm>(modelProfileToForm())
const knowledgeForm = reactive<KnowledgeProfileForm>(knowledgeProfileToForm())
const activeProfiles = computed(() => kind.value === 'model' ? modelProfiles.value : knowledgeProfiles.value)
const dialogTitle = computed(() => `${editing.value ? '编辑' : '新增'}${kind.value === 'model' ? '模型服务' : '知识库服务'}`)

onMounted(refresh)

async function refresh() {
  loading.value = true
  errorMessage.value = ''
  try {
    ;[modelProfiles.value, knowledgeProfiles.value] = await Promise.all([listModelProfiles(), listKnowledgeProfiles()])
  } catch (error) {
    errorMessage.value = getApiError(error).message
  } finally {
    loading.value = false
  }
}

function technical(profile: Profile): Record<string, unknown> {
  return 'technical_config' in profile ? profile.technical_config : {}
}

function providerLabel(profile: Profile): string {
  const provider = technical(profile).provider
  if (kind.value === 'model') return provider === 'openai_compatible' ? 'OpenAI 兼容' : '模型接口'
  return provider === 'generic_http' || provider === 'http' ? '通用 HTTP' : '本地知识库'
}

function serviceCapability(profile: Profile): string {
  const config = technical(profile)
  return kind.value === 'model' ? String(config.model ?? config.model_name ?? '-') : `${String(config.top_k ?? 5)} 条 · ${config.bm25 ? '混合检索' : '语义检索'}`
}

function serviceAddress(profile: Profile): string {
  return String(technical(profile).base_url ?? '-')
}

function credentialLabel(profile: Profile): string {
  return 'api_key_configured' in profile && profile.api_key_configured ? '已配置凭据' : '无需凭据'
}

function isActive(profile: Profile): boolean {
  return !('is_active' in profile) || profile.is_active
}

function resetFeedback() {
  formError.value = ''
  testMessage.value = ''
  previewQuery.value = ''
  previewMessage.value = ''
  previewFailed.value = false
  previewEvidence.value = []
}

function openCreate() {
  editing.value = null
  resetFeedback()
  if (kind.value === 'model') Object.assign(modelForm, modelProfileToForm())
  else Object.assign(knowledgeForm, knowledgeProfileToForm())
  dialogVisible.value = true
}

function openEdit(profile: Profile) {
  editing.value = profile
  resetFeedback()
  if (kind.value === 'model') Object.assign(modelForm, modelProfileToForm(profile))
  else {
    Object.assign(knowledgeForm, knowledgeProfileToForm(profile))
    previewQuery.value = 'HER2 阳性乳腺癌的治疗建议'
  }
  dialogVisible.value = true
}

function validModel(): ProfileCreatePayload | null {
  const payload = modelFormToPayload(modelForm)
  if (!payload.name || !payload.technical_config.base_url || !payload.technical_config.model) {
    formError.value = '请填写名称、服务地址和模型。'
    return null
  }
  return payload
}

function validKnowledge(): ProfileCreatePayload | null {
  let payload: ProfileCreatePayload
  try {
    payload = knowledgeFormToPayload(knowledgeForm)
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '知识库配置无效。'
    return null
  }
  if (!payload.name || !payload.technical_config.base_url || !payload.technical_config.search_path) {
    formError.value = '请填写名称、服务地址和检索路径。'
    return null
  }
  if (knowledgeForm.api_key_ref.trim() && !/^[A-Z][A-Z0-9_]*_REF$/.test(knowledgeForm.api_key_ref.trim())) {
    formError.value = '密钥环境变量引用必须为大写 *_REF 名称'
    return null
  }
  return payload
}

function modelTestPayload(payload: ProfileCreatePayload): ModelProfileConnectionTestPayload {
  const config = payload.technical_config
  const optional = (key: 'temperature' | 'top_p' | 'max_tokens' | 'timeout' | 'retries') => typeof config[key] === 'string' || typeof config[key] === 'number' ? { [key]: config[key] } : {}
  return { provider: 'openai_compatible', base_url: String(config.base_url), model: String(config.model), ...(payload.api_key ? { api_key: payload.api_key } : {}), ...(editing.value ? { profile_id: editing.value.id } : {}), ...optional('temperature'), ...optional('top_p'), ...optional('max_tokens'), ...optional('timeout'), ...optional('retries') }
}

async function runConnectionTest() {
  formError.value = ''
  const payload = validModel()
  if (!payload) return
  testing.value = true
  testMessage.value = ''
  try {
    const result = await testModelProfile(modelTestPayload(payload))
    testMessage.value = result.ok ? `连接成功：${result.model}，耗时 ${result.latency_ms} 毫秒` : '连接未通过'
  } catch (error) {
    testMessage.value = getApiError(error).message
  } finally {
    testing.value = false
  }
}

async function runKnowledgePreview() {
  previewMessage.value = ''
  previewFailed.value = false
  previewEvidence.value = []
  if (!editing.value) return
  if (!previewQuery.value.trim()) {
    previewMessage.value = '请输入测试问题。'
    previewFailed.value = true
    return
  }
  testingKnowledge.value = true
  try {
    const result = await previewKnowledge({ knowledge_profile_id: editing.value.id, query: previewQuery.value.trim(), guideline_ids: [], version_ids: [], language: 'zh' })
    previewEvidence.value = result.evidence
    previewMessage.value = `找到 ${result.evidence.length} 条证据`
  } catch (error) {
    previewMessage.value = getApiError(error).message
    previewFailed.value = true
  } finally {
    testingKnowledge.value = false
  }
}

async function save() {
  formError.value = ''
  const payload = kind.value === 'model' ? validModel() : validKnowledge()
  if (!payload) return
  saving.value = true
  try {
    if (kind.value === 'model') {
      const next = editing.value ? await patchModelProfile(editing.value.id, payload) : await createModelProfile(payload)
      modelProfiles.value = editing.value ? modelProfiles.value.map(item => item.id === next.id ? next : item) : [next, ...modelProfiles.value]
    } else {
      const next = editing.value ? await patchKnowledgeProfile(editing.value.id, payload) : await createKnowledgeProfile(payload)
      knowledgeProfiles.value = editing.value ? knowledgeProfiles.value.map(item => item.id === next.id ? next : item) : [next, ...knowledgeProfiles.value]
    }
    dialogVisible.value = false
  } catch (error) {
    formError.value = getApiError(error).message
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profiles-page { max-width: 1250px; margin: 0 auto; }
.page-heading { display: flex; gap: 20px; align-items: flex-end; justify-content: space-between; }
.page-eyebrow { margin: 0 0 6px; color: var(--teal-700); font-size: 11px; font-weight: 800; text-transform: uppercase; }
.page-heading h2 { margin: 0; color: var(--ink-950); font-size: 27px; }
.page-heading div > span { display: block; margin-top: 7px; color: var(--ink-650); font-size: 13px; }
.page-heading :deep(.el-button) { min-height: 40px; }
.page-heading :deep(.el-button span), .test-row :deep(.el-button span), .preview-controls :deep(.el-button span) { gap: 7px; }
.notice { display: flex; gap: 9px; align-items: center; margin: 16px 0 0; padding: 11px 13px; font-size: 12px; border: 1px solid; border-radius: var(--radius-sm); }
.notice--error { color: var(--red-700); background: #fff0ef; border-color: #e7bbb7; }
.notice button { margin-left: auto; color: inherit; cursor: pointer; background: transparent; border: 0; }
.profile-tabs { display: flex; gap: 22px; margin-top: 25px; border-bottom: 1px solid var(--line); }
.profile-tabs button { display: inline-flex; gap: 7px; align-items: center; min-height: 43px; padding: 0 2px; color: var(--ink-650); font-size: 13px; font-weight: 700; cursor: pointer; background: transparent; border: 0; border-bottom: 2px solid transparent; }
.profile-tabs button:hover, .profile-tabs button.active { color: var(--teal-700); border-bottom-color: var(--teal-700); }
.profile-tabs button span { display: grid; min-width: 21px; height: 18px; padding: 0 5px; color: var(--ink-650); font-size: 10px; place-items: center; background: #e2e6e2; border: 1px solid #d1d7d2; border-radius: 999px; }
.loading-state { padding: 45px 0; color: var(--ink-650); font-size: 13px; }
.service-list { margin-top: 16px; background: var(--paper-100); border: 1px solid var(--line); box-shadow: var(--shadow-panel); }
.service-row { display: grid; grid-template-columns: 38px minmax(180px, 1.15fr) minmax(430px, 2fr) minmax(130px, .7fr) 32px; gap: 14px; align-items: center; min-height: 92px; padding: 16px 17px; border-bottom: 1px solid var(--line); }
.service-row:last-child { border-bottom: 0; }
.service-row:hover { background: #f6f8f5; }
.service-mark { display: grid; width: 38px; height: 38px; color: var(--teal-700); place-items: center; background: #e4f2ee; border: 1px solid #bdd8d1; border-radius: 6px; }
.service-mark--model { color: #3f658c; background: #e9eef4; border-color: #c4d0dd; }
.service-identity { min-width: 0; }
.service-title { display: flex; gap: 7px; align-items: center; min-width: 0; }
.service-title h3 { min-width: 0; margin: 0; overflow: hidden; color: var(--ink-950); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.provider-badge { flex: 0 0 auto; padding: 3px 5px; color: var(--ink-650); font-size: 9px; font-weight: 700; background: #e9ece8; border: 1px solid #d3d9d4; border-radius: 3px; }
.service-identity p { margin: 6px 0 0; overflow: hidden; color: var(--ink-650); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.service-facts { display: grid; grid-template-columns: minmax(90px, .7fr) minmax(170px, 1.4fr) minmax(95px, .7fr); gap: 16px; min-width: 0; }
.service-facts div { min-width: 0; }
.service-facts span { display: block; margin-bottom: 5px; color: #75857f; font-size: 9px; font-weight: 700; text-transform: uppercase; }
.service-facts strong { display: flex; gap: 5px; align-items: center; overflow: hidden; color: var(--ink-800); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.service-status { display: grid; gap: 8px; justify-items: start; }
.status-pill { display: inline-flex; gap: 6px; align-items: center; color: var(--teal-700); font-size: 10px; font-weight: 800; }
.status-pill i { width: 7px; height: 7px; background: #2b9d77; border-radius: 50%; box-shadow: 0 0 0 3px #dcefe8; }
.status-pill--off { color: var(--ink-650); }
.status-pill--off i { background: #87928e; box-shadow: 0 0 0 3px #e5e8e5; }
.visibility { display: inline-flex; gap: 5px; align-items: center; color: var(--ink-650); font-size: 10px; }
.icon-button { display: grid; width: 30px; height: 30px; color: var(--ink-650); place-items: center; cursor: pointer; background: #fff; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.icon-button:hover { color: var(--teal-700); border-color: #90c1b7; }
.empty-state { display: grid; justify-items: center; margin-top: 16px; padding: 68px 24px; color: var(--ink-650); text-align: center; background: var(--paper-100); border: 1px dashed var(--line); }
.empty-state svg { margin-bottom: 10px; color: var(--teal-700); }
.empty-state strong { color: var(--ink-800); font-size: 13px; }
.empty-state span { margin-top: 6px; font-size: 11px; }
.profile-form { display: grid; gap: 14px; }
.form-section { padding: 15px 16px 4px; background: #f7f8f5; border: 1px solid #d7ddd8; border-radius: 6px; }
.section-heading { display: flex; gap: 9px; align-items: flex-start; margin-bottom: 15px; padding-bottom: 11px; color: var(--teal-700); border-bottom: 1px solid #dde2de; }
.section-heading svg { flex: 0 0 auto; margin-top: 1px; }
.section-heading h3 { margin: 0; color: var(--ink-950); font-size: 13px; }
.section-heading p { margin: 4px 0 0; color: var(--ink-650); font-size: 10px; }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 14px; }
.form-grid--three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.span-two { grid-column: 1 / -1; }
.profile-form :deep(.el-form-item) { min-width: 0; margin-bottom: 14px; }
.profile-form :deep(.el-form-item__label) { color: var(--ink-650); font-size: 11px; font-weight: 700; }
.profile-form :deep(.el-select), .retrieval-grid :deep(.el-input-number) { width: 100%; }
.profile-form :deep(.el-switch) { --el-switch-on-color: var(--teal-700); }
.field-note { width: 100%; margin: 5px 0 0; color: #7b8984; font-size: 9px; }
.switch-panel { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
.switch-panel label, .setting-toggle { display: flex; gap: 12px; align-items: center; justify-content: space-between; min-height: 54px; padding: 10px 12px; background: #fff; border: 1px solid #d7ddd8; border-radius: var(--radius-sm); }
.switch-panel strong, .switch-panel small, .setting-toggle strong, .setting-toggle small { display: block; }
.switch-panel strong, .setting-toggle strong { color: var(--ink-800); font-size: 11px; }
.switch-panel small, .setting-toggle small { margin-top: 3px; color: var(--ink-650); font-size: 9px; }
.test-row { display: flex; gap: 10px; align-items: center; margin: 0 0 12px; }
.inline-result { display: inline-flex; gap: 6px; align-items: center; color: var(--teal-700); font-size: 11px; }
.retrieval-grid { display: grid; grid-template-columns: minmax(110px, .7fr) minmax(110px, .7fr) minmax(200px, 1.3fr); gap: 14px; align-items: start; }
.setting-toggle { margin-top: 1px; }
.advanced-options { margin: 0 0 12px; padding-top: 10px; border-top: 1px solid #dde2de; }
.advanced-options summary { margin-bottom: 12px; color: var(--ink-800); font-size: 11px; font-weight: 700; cursor: pointer; }
.preview-section { padding-bottom: 15px; }
.preview-controls { display: grid; grid-template-columns: 1fr max-content; gap: 9px; }
.save-first { margin: 0; color: var(--ink-650); font-size: 11px; }
.preview-message { display: flex; gap: 6px; align-items: center; margin: 11px 0 0; color: var(--teal-700); font-size: 11px; font-weight: 700; }
.preview-message--error { color: var(--red-700); }
.evidence-preview { display: grid; gap: 8px; margin: 12px 0 0; padding: 0; list-style: none; }
.evidence-preview li { min-width: 0; padding: 10px 11px; background: #fff; border: 1px solid #d7ddd8; border-left: 3px solid var(--teal-600); }
.evidence-preview li div { display: flex; gap: 10px; align-items: center; justify-content: space-between; }
.evidence-preview li strong { color: var(--ink-800); font-size: 10px; }
.evidence-preview li span { flex: 0 0 auto; color: var(--ink-650); font-size: 9px; }
.evidence-preview li p { display: -webkit-box; margin: 7px 0 0; overflow: hidden; color: var(--ink-650); font-size: 10px; line-height: 1.55; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.form-error { display: flex; gap: 7px; align-items: center; margin: 13px 0 0; color: var(--red-700); font-size: 12px; }

@media (max-width: 1020px) {
  .service-row { grid-template-columns: 38px minmax(180px, 1fr) minmax(300px, 1.5fr) 32px; }
  .service-status { grid-column: 2 / 4; display: flex; gap: 18px; }
  .icon-button { grid-column: 4; grid-row: 1 / 3; }
}

@media (max-width: 700px) {
  .page-heading { display: block; }
  .page-heading :deep(.el-button) { width: 100%; margin-top: 16px; }
  .profile-tabs { gap: 14px; }
  .profile-tabs button { flex: 1; justify-content: center; }
  .service-row { grid-template-columns: 38px minmax(0, 1fr) 30px; gap: 11px; padding: 14px; }
  .service-identity { grid-column: 2; }
  .service-title { align-items: flex-start; flex-direction: column; }
  .service-identity p { white-space: normal; }
  .service-facts { grid-column: 1 / -1; grid-template-columns: 1fr 1fr; gap: 12px; padding-top: 12px; border-top: 1px solid #e0e4e1; }
  .service-facts .service-endpoint { grid-column: 1 / -1; grid-row: 2; }
  .service-status { grid-column: 1 / -1; display: flex; gap: 15px; align-items: center; }
  .icon-button { grid-column: 3; grid-row: 1; }
  .form-grid, .form-grid--three, .switch-panel, .retrieval-grid { grid-template-columns: 1fr; }
  .span-two { grid-column: auto; }
  .profile-dialog :deep(.el-dialog__body) { padding: 12px; overflow-x: hidden; }
  .form-section { padding: 13px 12px 3px; }
  .preview-controls { grid-template-columns: 1fr; }
  .preview-controls :deep(.el-button) { width: 100%; }
  .evidence-preview li div { align-items: flex-start; flex-direction: column; gap: 3px; }
}
</style>
