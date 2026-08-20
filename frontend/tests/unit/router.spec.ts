import { canAccessProfiles, canAccessSystemSettings } from '@/router'

describe('role route policy', () => {
  it('allows only administrators to access system settings', () => {
    expect(canAccessSystemSettings('medical_user')).toBe(false)
    expect(canAccessSystemSettings('admin_developer')).toBe(true)
    expect(canAccessProfiles('medical_user')).toBe(false)
    expect(canAccessProfiles('admin_developer')).toBe(true)
  })
})
