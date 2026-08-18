import { ref } from 'vue'
import { defineStore } from 'pinia'

import type { EvidenceResponse, RunResponse, TraceResponse } from '@/types/api'

export const useRunStore = defineStore('run', () => {
  const run = ref<RunResponse | null>(null)
  const traces = ref<TraceResponse[]>([])
  const evidence = ref<EvidenceResponse | null>(null)
  const isEvidenceOpen = ref(false)

  function setRun(next: RunResponse | null) {
    run.value = next
  }

  function setTraces(next: TraceResponse[]) {
    traces.value = next
  }

  function openEvidence(next: EvidenceResponse) {
    evidence.value = next
    isEvidenceOpen.value = true
  }

  function closeEvidence() {
    isEvidenceOpen.value = false
  }

  return { run, traces, evidence, isEvidenceOpen, setRun, setTraces, openEvidence, closeEvidence }
})
