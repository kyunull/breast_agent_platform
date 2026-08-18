<template>
  <section class="profiles-page">
    <div class="page-heading"><div><p class="page-eyebrow">Admin configuration</p><h2>Profile 管理</h2><p>维护已批准的模型和知识库连接；技术参数只在管理员工作区显示。</p></div><el-button type="primary" @click="openCreate"><Plus :size="15" />新增 Profile</el-button></div>
    <div v-if="errorMessage" class="notice notice--error"><CircleAlert :size="16" />{{ errorMessage }}<button type="button" @click="refresh">重试</button></div>
    <div class="profile-tabs"><button :class="{ active: kind === 'model' }" type="button" @click="kind = 'model'">模型 Profile <span>{{ modelProfiles.length }}</span></button><button :class="{ active: kind === 'knowledge' }" type="button" @click="kind = 'knowledge'">知识库 Profile <span>{{ knowledgeProfiles.length }}</span></button></div>
    <div v-if="loading" class="loading-line">正在读取 Profile...</div>
    <div v-else class="profile-table-wrap"><table class="profile-table"><thead><tr><th>名称</th><th>医学侧选项</th><th>技术配置摘要</th><th>状态</th><th></th></tr></thead><tbody><tr v-for="profile in activeProfiles" :key="profile.id"><td><strong>{{ profile.name }}</strong><span>{{ profile.description || '暂无说明' }}</span></td><td><code>{{ compactJson(profile.medical_options) }}</code></td><td><code>{{ compactJson('technical_config' in profile ? profile.technical_config : {}) }}</code></td><td><span class="active-pill" :class="{ muted: 'is_active' in profile && !profile.is_active }">{{ 'is_active' in profile && !profile.is_active ? '停用' : '启用' }}</span></td><td><button class="icon-action" title="编辑 Profile" type="button" @click="openEdit(profile)"><Pencil :size="15" /><span class="sr-only">编辑</span></button></td></tr></tbody></table><div v-if="!activeProfiles.length" class="empty-state">还没有{{ kind === 'model' ? '模型' : '知识库' }} Profile。</div></div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑 Profile' : '新增 Profile'" width="min(620px, calc(100vw - 32px))"><el-form :model="form" label-position="top"><el-form-item label="类型"><el-radio-group v-model="kind" :disabled="Boolean(editing)"><el-radio-button label="model">模型</el-radio-button><el-radio-button label="knowledge">知识库</el-radio-button></el-radio-group></el-form-item><el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item><el-form-item label="说明"><el-input v-model="form.description" /></el-form-item><el-form-item label="对医学用户开放"><el-switch v-model="form.exposed_to_medical" /></el-form-item><el-form-item label="医学语义选项 JSON"><el-input v-model="form.medical_options" :rows="4" type="textarea" /></el-form-item><el-form-item label="技术配置 JSON"><el-input v-model="form.technical_config" :rows="7" type="textarea" /></el-form-item><p v-if="formError" class="form-error">{{ formError }}</p></el-form><template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button :loading="saving" type="primary" @click="save">保存</el-button></template></el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { CircleAlert, Pencil, Plus } from 'lucide-vue-next'

import { getApiError } from '@/api/client'
import { createKnowledgeProfile, createModelProfile, listKnowledgeProfiles, listModelProfiles, patchKnowledgeProfile, patchModelProfile } from '@/api/profiles'
import type { Profile, ProfileCreatePayload } from '@/types/api'

const kind = ref<'model' | 'knowledge'>('model')
const modelProfiles = ref<Profile[]>([])
const knowledgeProfiles = ref<Profile[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editing = ref<Profile | null>(null)
const errorMessage = ref('')
const formError = ref('')
const form = reactive({ name: '', description: '', exposed_to_medical: true, medical_options: '{}', technical_config: '{}' })
const activeProfiles = computed(() => kind.value === 'model' ? modelProfiles.value : knowledgeProfiles.value)

onMounted(refresh)

async function refresh() { loading.value = true; errorMessage.value = ''; try { [modelProfiles.value, knowledgeProfiles.value] = await Promise.all([listModelProfiles(), listKnowledgeProfiles()]) } catch (error) { errorMessage.value = getApiError(error).message } finally { loading.value = false } }

function compactJson(value: unknown) { const text = JSON.stringify(value); return text && text.length > 100 ? `${text.slice(0, 100)}…` : text }
function parseObject(value: string, label: string) { try { const parsed = JSON.parse(value); if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(); return parsed as Record<string, unknown> } catch { formError.value = `${label}必须是 JSON 对象。`; return null } }

function openCreate() { editing.value = null; form.name = ''; form.description = ''; form.exposed_to_medical = true; form.medical_options = '{}'; form.technical_config = '{}'; formError.value = ''; dialogVisible.value = true }
function openEdit(profile: Profile) { editing.value = profile; form.name = profile.name; form.description = profile.description ?? ''; form.exposed_to_medical = profile.exposed_to_medical; form.medical_options = JSON.stringify(profile.medical_options, null, 2); form.technical_config = JSON.stringify('technical_config' in profile ? profile.technical_config : {}, null, 2); formError.value = ''; dialogVisible.value = true }

async function save() {
  formError.value = ''
  if (!form.name.trim()) { formError.value = '请输入 Profile 名称。'; return }
  const medicalOptions = parseObject(form.medical_options, '医学语义选项')
  const technicalConfig = parseObject(form.technical_config, '技术配置')
  if (!medicalOptions || !technicalConfig) return
  const payload: ProfileCreatePayload = { name: form.name.trim(), description: form.description.trim() || undefined, exposed_to_medical: form.exposed_to_medical, medical_options: medicalOptions, technical_config: technicalConfig }
  saving.value = true
  try {
    const next = editing.value ? (kind.value === 'model' ? await patchModelProfile(editing.value.id, payload) : await patchKnowledgeProfile(editing.value.id, payload)) : (kind.value === 'model' ? await createModelProfile(payload) : await createKnowledgeProfile(payload))
    const target = kind.value === 'model' ? modelProfiles : knowledgeProfiles
    target.value = editing.value ? target.value.map((item) => item.id === next.id ? next : item) : [next, ...target.value]
    dialogVisible.value = false
  } catch (error) { formError.value = getApiError(error).message } finally { saving.value = false }
}
</script>

<style scoped>
.profiles-page { max-width: 1250px; margin: 0 auto; }.page-heading { display: flex; gap: 20px; align-items: flex-end; justify-content: space-between; margin-bottom: 21px; }.page-eyebrow { margin: 0 0 6px; color: var(--teal-700); font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.page-heading h2 { margin: 0; color: var(--ink-950); font-size: 27px; }.page-heading p:not(.page-eyebrow) { margin: 7px 0 0; color: var(--ink-650); font-size: 13px; }.page-heading :deep(.el-button) { background: var(--teal-700); border-color: var(--teal-700); }.notice { display: flex; gap: 9px; align-items: center; margin-bottom: 14px; padding: 11px 13px; color: var(--red-700); font-size: 12px; background: #fff0ef; border: 1px solid #e7bbb7; border-radius: var(--radius-sm); }.notice button { margin-left: auto; color: inherit; text-decoration: underline; cursor: pointer; background: transparent; border: 0; }.profile-tabs { display: flex; gap: 5px; margin-bottom: 12px; border-bottom: 1px solid var(--line); }.profile-tabs button { display: inline-flex; gap: 7px; align-items: center; padding: 10px 13px; color: var(--ink-650); font-size: 12px; cursor: pointer; background: transparent; border: 0; border-bottom: 2px solid transparent; }.profile-tabs button span { padding: 2px 5px; font-size: 9px; background: #e8ece8; border-radius: 999px; }.profile-tabs button.active { color: var(--teal-700); font-weight: 800; border-bottom-color: var(--teal-700); }.loading-line { padding: 25px 0; color: var(--ink-650); font-size: 12px; }.profile-table-wrap { overflow-x: auto; background: var(--paper-100); border: 1px solid var(--line); box-shadow: var(--shadow-panel); }.profile-table { width: 100%; min-width: 800px; border-collapse: collapse; }.profile-table th { padding: 11px 15px; color: var(--ink-650); font-size: 10px; text-align: left; text-transform: uppercase; background: #e9ece7; border-bottom: 1px solid var(--line); }.profile-table td { padding: 14px 15px; color: var(--ink-800); font-size: 12px; border-bottom: 1px solid #e0e4df; }.profile-table tr:last-child td { border-bottom: 0; }.profile-table strong,.profile-table td span { display: block; }.profile-table strong { color: var(--ink-950); font-size: 13px; }.profile-table td span { margin-top: 4px; color: var(--ink-650); font-size: 10px; }.profile-table code { display: block; max-width: 270px; overflow: hidden; color: #5f706d; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }.active-pill { display: inline-block !important; width: max-content; padding: 3px 6px; color: var(--teal-700) !important; background: #e4f2ee; border: 1px solid #acd1c7; border-radius: 999px; }.active-pill.muted { color: var(--ink-650) !important; background: #edf0ed; border-color: #cbd3cd; }.icon-action { display: grid; width: 29px; height: 29px; color: var(--ink-650); place-items: center; cursor: pointer; background: transparent; border: 1px solid var(--line); border-radius: var(--radius-sm); }.icon-action:hover { color: var(--teal-700); border-color: #acd1c7; }.empty-state { padding: 45px; color: var(--ink-650); text-align: center; }.form-error { margin: 0; color: var(--red-700); font-size: 12px; }.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
@media (max-width: 700px) { .page-heading { display: block; }.page-heading :deep(.el-button) { width: 100%; margin-top: 16px; } }
</style>
