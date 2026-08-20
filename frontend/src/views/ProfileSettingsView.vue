<template>
  <section class="profiles-page">
    <header class="page-heading">
      <div><p>管理员配置</p><h2>系统配置</h2><span>维护模型服务与知识库服务，连接凭据仅以环境变量引用保存。</span></div>
      <el-button type="primary" @click="openCreate"><Plus :size="15" />{{ kind === 'model' ? '新增模型服务' : '新增知识库服务' }}</el-button>
    </header>
    <p v-if="errorMessage" class="notice">{{ errorMessage }} <button @click="refresh">重试</button></p>
    <div class="profile-tabs"><button :class="{ active: kind === 'model' }" @click="kind = 'model'">模型服务 <span>{{ modelProfiles.length }}</span></button><button :class="{ active: kind === 'knowledge' }" @click="kind = 'knowledge'">知识库服务 <span>{{ knowledgeProfiles.length }}</span></button></div>
    <p v-if="loading">正在读取系统配置...</p>
    <template v-else><table class="profile-table"><thead><tr><th>名称</th><th>模型</th><th>服务地址</th><th>医学用户</th><th>启用状态</th><th></th></tr></thead><tbody><tr v-for="profile in activeProfiles" :key="profile.id"><td><strong>{{ profile.name }}</strong><span>{{ profile.description || '暂无说明' }}</span></td><td>{{ modelName(profile) }}</td><td>{{ serviceAddress(profile) }}</td><td>{{ profile.exposed_to_medical ? '对医学用户开放' : '仅管理员可用' }}</td><td>{{ isActive(profile) ? '启用' : '停用' }}</td><td><button title="编辑服务" @click="openEdit(profile)"><Pencil :size="15" /></button></td></tr></tbody></table><p v-if="!activeProfiles.length" class="empty-state">还没有服务。</p></template>
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑服务' : (kind === 'model' ? '新增模型服务' : '新增知识库服务')" width="min(720px, calc(100vw - 32px))">
      <el-form v-if="kind === 'model'" label-position="top">
        <h3>基本信息</h3><div class="form-grid"><el-form-item label="名称"><el-input v-model="modelForm.name" /></el-form-item><el-form-item label="说明"><el-input v-model="modelForm.description" /></el-form-item></div>
        <div class="switch-row"><el-form-item label="启用服务"><el-switch v-model="modelForm.is_active" /></el-form-item><el-form-item label="对医学用户开放"><el-switch v-model="modelForm.exposed_to_medical" /></el-form-item></div>
        <h3>模型连接</h3><div class="form-grid"><el-form-item label="接口类型"><el-input model-value="OpenAI 兼容接口" readonly /></el-form-item><el-form-item label="服务地址"><el-input v-model="modelForm.base_url" /></el-form-item><el-form-item label="模型"><el-input v-model="modelForm.model" /></el-form-item><el-form-item label="密钥环境变量引用"><el-input v-model="modelForm.api_key_ref" /></el-form-item></div>
        <h3>运行参数</h3><div class="form-grid"><el-form-item label="温度"><el-input v-model="modelForm.temperature" /></el-form-item><el-form-item label="采样概率"><el-input v-model="modelForm.top_p" /></el-form-item><el-form-item label="最大输出长度"><el-input v-model="modelForm.max_tokens" /></el-form-item><el-form-item label="超时（秒）"><el-input v-model="modelForm.timeout" /></el-form-item><el-form-item label="重试次数"><el-input v-model="modelForm.retries" /></el-form-item></div>
        <h3>医学说明</h3><div class="form-grid"><el-form-item label="显示名称"><el-input v-model="modelForm.display_name" /></el-form-item><el-form-item label="临床适用范围"><el-input v-model="modelForm.clinical_scope" /></el-form-item><el-form-item label="支持任务"><el-input v-model="modelForm.supported_tasks" /></el-form-item><el-form-item label="输出风格"><el-input v-model="modelForm.output_style" /></el-form-item></div>
        <el-button :loading="testing" @click="runConnectionTest">测试连接</el-button><span v-if="testMessage">{{ testMessage }}</span>
      </el-form>
      <el-form v-else label-position="top"><el-form-item label="名称"><el-input v-model="knowledgeForm.name" /></el-form-item><el-form-item label="说明"><el-input v-model="knowledgeForm.description" /></el-form-item><el-form-item label="对医学用户开放"><el-switch v-model="knowledgeForm.exposed_to_medical" /></el-form-item><el-form-item label="医学语义选项 JSON"><el-input v-model="knowledgeForm.medical_options" type="textarea" /></el-form-item><el-form-item label="技术配置 JSON"><el-input v-model="knowledgeForm.technical_config" type="textarea" /></el-form-item></el-form>
      <p v-if="formError" class="form-error">{{ formError }}</p><template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Pencil, Plus } from 'lucide-vue-next'
import { getApiError } from '@/api/client'
import { createKnowledgeProfile, createModelProfile, listKnowledgeProfiles, listModelProfiles, patchKnowledgeProfile, patchModelProfile, testModelProfile, type ModelProfileConnectionTestPayload } from '@/api/profiles'
import { modelFormToPayload, modelProfileToForm, type ModelProfileForm } from '@/composables/useModelProfileForm'
import type { Profile, ProfileCreatePayload } from '@/types/api'

const kind = ref<'model' | 'knowledge'>('model')
const modelProfiles = ref<Profile[]>([]); const knowledgeProfiles = ref<Profile[]>([])
const loading = ref(false); const saving = ref(false); const testing = ref(false); const dialogVisible = ref(false)
const editing = ref<Profile | null>(null); const errorMessage = ref(''); const formError = ref(''); const testMessage = ref('')
const modelForm = reactive<ModelProfileForm>(modelProfileToForm())
const knowledgeForm = reactive({ name: '', description: '', exposed_to_medical: true, medical_options: '{}', technical_config: '{}' })
const activeProfiles = computed(() => kind.value === 'model' ? modelProfiles.value : knowledgeProfiles.value)
onMounted(refresh)

async function refresh() { loading.value = true; errorMessage.value = ''; try { [modelProfiles.value, knowledgeProfiles.value] = await Promise.all([listModelProfiles(), listKnowledgeProfiles()]) } catch (error) { errorMessage.value = getApiError(error).message } finally { loading.value = false } }
function technical(profile: Profile) { return 'technical_config' in profile ? profile.technical_config : {} }
function modelName(profile: Profile) { return String(technical(profile).model ?? '-') }
function serviceAddress(profile: Profile) { return String(technical(profile).base_url ?? '-') }
function isActive(profile: Profile) { return !('is_active' in profile) || profile.is_active }
function openCreate() { editing.value = null; formError.value = ''; testMessage.value = ''; if (kind.value === 'model') Object.assign(modelForm, modelProfileToForm()); else Object.assign(knowledgeForm, { name: '', description: '', exposed_to_medical: true, medical_options: '{}', technical_config: '{}' }); dialogVisible.value = true }
function openEdit(profile: Profile) { editing.value = profile; formError.value = ''; testMessage.value = ''; if (kind.value === 'model') Object.assign(modelForm, modelProfileToForm(profile)); else Object.assign(knowledgeForm, { name: profile.name, description: profile.description ?? '', exposed_to_medical: profile.exposed_to_medical, medical_options: JSON.stringify(profile.medical_options, null, 2), technical_config: JSON.stringify(technical(profile), null, 2) }); dialogVisible.value = true }
function validModel() { const payload = modelFormToPayload(modelForm); if (!payload.name || !payload.technical_config.base_url || !payload.technical_config.model) { formError.value = '请填写名称、服务地址和模型。'; return null }; const ref = modelForm.api_key_ref.trim(); if (ref && !/^[A-Z][A-Z0-9_]*_REF$/.test(ref)) { formError.value = '密钥环境变量引用必须为大写 *_REF 名称'; return null }; return payload }
function testPayload(payload: ProfileCreatePayload): ModelProfileConnectionTestPayload { const config = payload.technical_config; const optional = (key: 'api_key_ref' | 'temperature' | 'top_p' | 'max_tokens' | 'timeout' | 'retries') => typeof config[key] === 'string' || typeof config[key] === 'number' ? { [key]: config[key] } : {}; return { provider: 'openai_compatible', base_url: String(config.base_url), model: String(config.model), ...optional('api_key_ref'), ...optional('temperature'), ...optional('top_p'), ...optional('max_tokens'), ...optional('timeout'), ...optional('retries') } }
async function runConnectionTest() { formError.value = ''; const payload = validModel(); if (!payload) return; testing.value = true; testMessage.value = ''; try { const result = await testModelProfile(testPayload(payload)); testMessage.value = result.ok ? `连接成功：${result.model}，耗时 ${result.latency_ms} 毫秒` : '连接未通过' } catch (error) { testMessage.value = getApiError(error).message } finally { testing.value = false } }
function parseObject(value: string, message: string) { try { const result: unknown = JSON.parse(value); if (!result || typeof result !== 'object' || Array.isArray(result)) throw new Error(); return result as Record<string, unknown> } catch { formError.value = message; return null } }
async function save() { formError.value = ''; if (kind.value === 'model') { const payload = validModel(); if (!payload) return; saving.value = true; try { const next = editing.value ? await patchModelProfile(editing.value.id, payload) : await createModelProfile(payload); modelProfiles.value = editing.value ? modelProfiles.value.map(item => item.id === next.id ? next : item) : [next, ...modelProfiles.value]; dialogVisible.value = false } catch (error) { formError.value = getApiError(error).message } finally { saving.value = false }; return } const medical_options = parseObject(knowledgeForm.medical_options, '医学语义选项必须是 JSON 对象。'); if (!medical_options) return; const technical_config = parseObject(knowledgeForm.technical_config, '技术配置必须是 JSON 对象。'); if (!technical_config) return; const payload: ProfileCreatePayload = { name: knowledgeForm.name.trim(), description: knowledgeForm.description.trim() || undefined, exposed_to_medical: knowledgeForm.exposed_to_medical, medical_options, technical_config }; saving.value = true; try { const next = editing.value ? await patchKnowledgeProfile(editing.value.id, payload) : await createKnowledgeProfile(payload); knowledgeProfiles.value = editing.value ? knowledgeProfiles.value.map(item => item.id === next.id ? next : item) : [next, ...knowledgeProfiles.value]; dialogVisible.value = false } catch (error) { formError.value = getApiError(error).message } finally { saving.value = false } }
</script>

<style scoped>
.profiles-page { max-width: 1250px; margin: 0 auto; }.page-heading { display: flex; justify-content: space-between; gap: 20px; }.page-heading p { color: var(--teal-700); }.page-heading h2 { margin: 4px 0; }.profile-tabs { display: flex; gap: 8px; margin: 20px 0; }.profile-tabs button.active { font-weight: 700; color: var(--teal-700); }.profile-table { width: 100%; border-collapse: collapse; }.profile-table th, .profile-table td { padding: 12px; text-align: left; border-bottom: 1px solid var(--line); }.profile-table span, .profile-table strong { display: block; }.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }.switch-row { display: flex; gap: 24px; }.empty-state { padding: 30px; text-align: center; }.form-error { color: var(--red-700); } h3 { margin: 15px 0 8px; } @media (max-width: 700px) { .form-grid { grid-template-columns: 1fr; }.page-heading { display: block; }.profile-table { min-width: 700px; } }
</style>
