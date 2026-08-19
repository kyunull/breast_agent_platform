<template>
  <section class="json-pane">
    <div class="json-pane__heading"><strong>{{ title }}</strong><span>{{ subtitle }}</span></div>
    <pre>{{ formatted }}</pre>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ title: string; value: unknown; subtitle?: string }>()
const formatted = computed(() => props.value === null || props.value === undefined ? '暂无数据' : JSON.stringify(props.value, null, 2))
</script>

<style scoped>
.json-pane { min-width: 0; background: #f7f8f4; border: 1px solid var(--line); }.json-pane__heading { display: flex; gap: 8px; align-items: baseline; padding: 11px 13px; border-bottom: 1px solid var(--line); }.json-pane__heading strong { color: var(--ink-950); font-size: 12px; }.json-pane__heading span { color: var(--ink-650); font-size: 10px; }.json-pane pre { min-height: 180px; max-height: 310px; margin: 0; padding: 13px; overflow: auto; color: #48615e; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
@media (max-width: 620px) { .json-pane pre { min-height: 150px; max-height: 260px; } }
</style>
