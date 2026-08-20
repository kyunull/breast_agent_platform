<template>
  <DataPreparation
    v-if="draft"
    :workflow-id="workflowId"
    :extraction="draft.extraction"
    @error="errorMessage = $event"
    @update="updateExtraction"
  />
  <div v-if="errorMessage" class="notice notice--error">{{ errorMessage }}</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

import DataPreparation from '@/components/DataPreparation.vue'
import { useWorkflowStore } from '@/stores/workflow'
import type { ExtractionConfig } from '@/types/api'

const route = useRoute()
const store = useWorkflowStore()
const errorMessage = ref('')
const workflowId = computed(() => String(route.params.id))
const draft = computed(() => store.draft)

function updateExtraction(nextExtraction: ExtractionConfig) {
  store.patchLocal({ extraction: nextExtraction as unknown as Record<string, unknown> })
}
</script>

<style scoped>
.notice { margin-top: 14px; padding: 11px 13px; color: var(--red-700); font-size: 12px; background: #fff0ef; border: 1px solid #e7bbb7; border-radius: var(--radius-sm); }
</style>
