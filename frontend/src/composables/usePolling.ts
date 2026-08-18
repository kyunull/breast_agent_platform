import { onBeforeUnmount, ref } from 'vue'

import { isRunTerminal } from './useRunUtils'
import type { RunStatus } from '@/types/api'

export function usePolling<T extends { status: RunStatus | string }>(fetcher: () => Promise<T>, interval = 1500) {
  const active = ref(false)
  const error = ref<unknown>(null)
  const latest = ref<T | null>(null)
  let timer: ReturnType<typeof setTimeout> | undefined

  const stop = () => {
    active.value = false
    if (timer) clearTimeout(timer)
    timer = undefined
  }

  const tick = async (): Promise<T | null> => {
    if (!active.value) return null
    try {
      const result = await fetcher()
      latest.value = result
      if (isRunTerminal(result.status)) { stop(); return result }
      timer = setTimeout(() => { void tick() }, interval)
      return result
    } catch (reason) {
      error.value = reason
      stop()
      return null
    }
  }

  const start = async () => {
    stop()
    error.value = null
    latest.value = null
    active.value = true
    return tick()
  }

  onBeforeUnmount(stop)
  return { active, error, latest, start, stop }
}
