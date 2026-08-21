import { describe, expect, it } from 'vitest'

import { readJsonDocument } from '@/composables/useJsonFileUpload'

describe('JSON file upload helper', () => {
  it('reads a complete JSON object and preserves the file name', async () => {
    const result = await readJsonDocument(new File(['{"patient_data":{"age":42}}'], 'BC-001.json', { type: 'application/json' }))

    expect(result.name).toBe('BC-001.json')
    expect(result.text).toBe('{"patient_data":{"age":42}}')
    expect(result.value).toEqual({ patient_data: { age: 42 } })
  })

  it('rejects non-json files before reading them', async () => {
    await expect(readJsonDocument(new File(['{}'], 'patient.txt', { type: 'text/plain' }))).rejects.toThrow('仅支持 JSON 文件')
  })

  it('rejects valid JSON arrays because workflow inputs must be objects', async () => {
    await expect(readJsonDocument(new File(['[]'], 'patients.json', { type: 'application/json' }))).rejects.toThrow('JSON 对象')
  })
})
