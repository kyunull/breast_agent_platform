<template>
  <el-drawer :model-value="visible" :size="drawerSize" title="知识库证据" @close="$emit('close')">
    <div v-if="loading" class="drawer-state">正在读取证据原文...</div>
    <div v-else-if="error" class="drawer-state drawer-state--error"><CircleAlert :size="18" /><p>{{ error }}</p></div>
    <article v-else-if="evidence" class="evidence-detail">
      <div class="evidence-detail__tag"><BookOpen :size="14" />{{ evidence.evidence_id }}</div>
      <h2>{{ evidence.source_title }}</h2>
      <div class="evidence-meta"><span v-if="evidence.guideline_id">指南 {{ evidence.guideline_id }}</span><span v-if="evidence.version_id">版本 {{ evidence.version_id }}</span><span v-if="evidence.locator">定位 {{ evidence.locator }}</span><span v-if="evidence.source_level">来源等级 {{ evidence.source_level }}</span></div>
      <blockquote>{{ evidence.text }}</blockquote>
      <div class="evidence-score" v-if="evidence.score !== null">检索相关度 <strong>{{ evidence.score.toFixed(2) }}</strong></div>
      <a v-if="evidence.open_url" class="source-link" :href="evidence.open_url" rel="noreferrer" target="_blank"><ExternalLink :size="14" />打开原始文档</a>
      <p v-else class="no-source">当前部署未提供原始文档地址，仅显示检索证据原文。</p>
    </article>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BookOpen, CircleAlert, ExternalLink } from 'lucide-vue-next'

import type { EvidenceResponse } from '@/types/api'

defineProps<{ visible: boolean; evidence: EvidenceResponse | null; loading?: boolean; error?: string }>()
defineEmits<{ close: [] }>()
const drawerSize = computed(() => window.innerWidth < 620 ? '92%' : '430px')
</script>

<style scoped>
.drawer-state { display: grid; min-height: 160px; color: var(--ink-650); place-items: center; text-align: center; }.drawer-state--error { display: flex; gap: 8px; align-items: flex-start; color: var(--red-700); }.drawer-state--error p { margin: 0; font-size: 13px; line-height: 1.5; }.evidence-detail__tag { display: inline-flex; gap: 5px; align-items: center; color: var(--teal-700); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 10px; font-weight: 800; }.evidence-detail h2 { margin: 10px 0 12px; color: var(--ink-950); font-size: 20px; line-height: 1.35; }.evidence-meta { display: flex; flex-wrap: wrap; gap: 6px; }.evidence-meta span { padding: 4px 6px; color: var(--ink-650); font-size: 10px; background: #edf1ed; border: 1px solid #d5dcd6; border-radius: var(--radius-sm); }.evidence-detail blockquote { margin: 21px 0; padding: 14px 15px; color: var(--ink-800); font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif; font-size: 14px; line-height: 1.8; background: #f3f6f2; border-left: 3px solid var(--teal-600); }.evidence-score { color: var(--ink-650); font-size: 11px; }.evidence-score strong { color: var(--teal-700); }.source-link { display: inline-flex; gap: 7px; align-items: center; margin-top: 21px; color: var(--teal-700); font-size: 13px; font-weight: 700; }.no-source { color: var(--ink-650); font-size: 11px; line-height: 1.5; }
</style>
