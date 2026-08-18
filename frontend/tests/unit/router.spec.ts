import { canAccessProfiles } from '@/router'

describe('role route policy', () => {
  it('blocks profile management for medical users', () => {
    expect(canAccessProfiles('medical_user')).toBe(false)
    expect(canAccessProfiles('admin_developer')).toBe(true)
  })
})
