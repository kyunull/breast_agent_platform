<template>
  <section class="prompt-diff">
    <div class="diff-heading"><div><strong>候选提示词</strong><span>应用后只写入工作流草稿</span></div><span v-if="resultDiff">差异已记录</span></div>
    <div class="diff-grid"><div><p>原提示词</p><pre>{{ original || '暂无原提示词' }}</pre></div><div><p>候选提示词</p><pre class="candidate">{{ candidate || '候选生成后显示' }}</pre></div></div>
    <details v-if="resultDiff" class="diff-details"><summary>查看结构化差异</summary><pre>{{ JSON.stringify(resultDiff, null, 2) }}</pre></details>
  </section>
</template>

<script setup lang="ts">
defineProps<{ original: string; candidate: string | null; resultDiff: Record<string, unknown> | null }>()
</script>

<style scoped>
.prompt-diff { margin-top: 17px; background: var(--paper-100); border: 1px solid var(--line); }.diff-heading { display: flex; gap: 12px; justify-content: space-between; padding: 13px 15px; border-bottom: 1px solid var(--line); }.diff-heading strong,.diff-heading span { display: block; }.diff-heading strong { color: var(--ink-950); font-size: 13px; }.diff-heading div span { margin-top: 3px; color: var(--ink-650); font-size: 10px; }.diff-heading > span { color: var(--teal-700); font-size: 10px; }.diff-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 13px; }.diff-grid p { margin: 0 0 6px; color: var(--ink-650); font-size: 10px; font-weight: 800; text-transform: uppercase; }.diff-grid pre,.diff-details pre { min-height: 170px; margin: 0; padding: 11px; overflow: auto; color: #546562; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; line-height: 1.6; white-space: pre-wrap; background: #f0f3ef; border: 1px solid #d7ddd7; }.diff-grid pre.candidate { color: var(--teal-700); background: #edf7f2; border-color: #b6d8d0; }.diff-details { margin: 0 13px 13px; color: var(--ink-650); font-size: 11px; }.diff-details summary { cursor: pointer; }.diff-details pre { min-height: auto; margin-top: 7px; }
@media (max-width: 720px) { .diff-grid { grid-template-columns: 1fr; } }
</style>
