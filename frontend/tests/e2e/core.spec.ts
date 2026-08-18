import { expect, test } from '@playwright/test'

test('shows the local clinical workspace login', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: '登录工作区' })).toBeVisible()
  await expect(page.getByText('账号由本地管理员创建')).toBeVisible()
})

test('keeps login layout readable on a narrow viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: '登录工作区' })).toBeVisible()
  await expect(page.locator('.login-panel')).toBeVisible()
})
