import { expect, test } from '@playwright/test'

const admin = { id: 'admin-1', username: 'admin', display_name: '管理员', role: 'admin_developer', is_active: true }
const medicalUser = { id: 'medical-1', username: 'doctor', display_name: '医学用户', role: 'medical_user', is_active: true }

test('model service settings let an admin test a referenced credential', async ({ page }) => {
  let testRequestBody: unknown
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: admin })
      return
    }
    if (path === '/api/v1/model-profiles/test') {
      testRequestBody = request.postDataJSON()
      await route.fulfill({ json: { ok: true, model: 'clinical-gpt', latency_ms: 42 } })
      return
    }
    if (path === '/api/v1/model-profiles') {
      await route.fulfill({ json: [{ id: 'model-1', name: '临床模型', description: null, is_active: true, exposed_to_medical: true, technical_config: { base_url: 'https://models.example/v1', model: 'clinical-gpt' }, medical_options: {} }] })
      return
    }
    if (path === '/api/v1/knowledge-profiles' || path === '/api/v1/workflows') {
      await route.fulfill({ json: [] })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/settings/profiles')
  await expect(page.getByRole('heading', { name: '系统配置', level: 2 })).toBeVisible()
  await expect(page.getByRole('link', { name: '系统配置' })).toBeVisible()
  await expect(page.getByText('临床模型')).toBeVisible()
  await page.getByRole('button', { name: '新增模型服务' }).click()

  await page.getByRole('textbox', { name: '名称', exact: true }).fill('测试模型')
  await page.getByRole('textbox', { name: '服务地址' }).fill('https://models.example/v1')
  await page.getByRole('textbox', { name: '模型' }).fill('clinical-gpt')
  await page.getByRole('textbox', { name: '密钥环境变量引用' }).fill('CLINICAL_MODEL_API_KEY_REF')
  const posted = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/model-profiles/test')
  await page.getByRole('button', { name: '测试连接' }).click()
  await posted

  expect(testRequestBody).toEqual({
    technical_config: {
      provider: 'openai_compatible',
      base_url: 'https://models.example/v1',
      model: 'clinical-gpt',
      api_key_ref: 'CLINICAL_MODEL_API_KEY_REF',
    },
  })
  await expect(page.getByText('连接成功：clinical-gpt，耗时 42 毫秒')).toBeVisible()
})

test('model service settings deny medical users', async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem('breast-agent-token', 'e2e-token'))
  await page.route('http://127.0.0.1:8000/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/me') {
      await route.fulfill({ json: medicalUser })
      return
    }
    if (path === '/api/v1/workflows') {
      await route.fulfill({ json: [] })
      return
    }
    await route.fulfill({ json: [] })
  })

  await page.goto('/settings/profiles')
  await expect(page).toHaveURL('/workflows')
  await expect(page.getByRole('link', { name: '系统配置' })).toHaveCount(0)
})
