export interface JsonDocumentResult {
  name: string
  text: string
  value: Record<string, unknown>
}

function parseJsonObject(text: string): Record<string, unknown> {
  let value: unknown
  try {
    value = JSON.parse(text)
  } catch {
    throw new Error('文件内容不是有效 JSON。')
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('上传内容必须是 JSON 对象。')
  }
  return value as Record<string, unknown>
}

export async function readJsonDocument(file: File): Promise<JsonDocumentResult> {
  if (!file.name.toLowerCase().endsWith('.json')) {
    throw new Error('仅支持 JSON 文件。')
  }
  const text = await file.text()
  return { name: file.name, text, value: parseJsonObject(text) }
}
