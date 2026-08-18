import { ref } from 'vue'

import { parseNodeClipboard, stringifyNodeClipboard } from './useGraphAdapter'
import type { GraphNode } from '@/types/graph'

export function useNodeClipboard() {
  const text = ref('')
  const feedback = ref('')

  async function copy(node: GraphNode) {
    text.value = stringifyNodeClipboard(node)
    try {
      await navigator.clipboard.writeText(text.value)
      feedback.value = '已复制节点结构，可在外部修改后粘贴校验。'
    } catch {
      feedback.value = '已生成节点 JSON，请手动复制。'
    }
  }

  function parse() {
    return parseNodeClipboard(text.value)
  }

  return { text, feedback, copy, parse }
}
