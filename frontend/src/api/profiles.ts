import { apiClient } from './client'
import type { Profile, ProfileCreatePayload } from '@/types/api'

export async function listModelProfiles(): Promise<Profile[]> {
  return (await apiClient.get<Profile[]>('/api/v1/model-profiles')).data
}

export async function listKnowledgeProfiles(): Promise<Profile[]> {
  return (await apiClient.get<Profile[]>('/api/v1/knowledge-profiles')).data
}

export async function createModelProfile(payload: ProfileCreatePayload): Promise<Profile> {
  return (await apiClient.post<Profile>('/api/v1/model-profiles', payload)).data
}

export async function createKnowledgeProfile(payload: ProfileCreatePayload): Promise<Profile> {
  return (await apiClient.post<Profile>('/api/v1/knowledge-profiles', payload)).data
}

export async function patchModelProfile(id: string, payload: Partial<ProfileCreatePayload>): Promise<Profile> {
  return (await apiClient.patch<Profile>(`/api/v1/model-profiles/${id}`, payload)).data
}

export async function patchKnowledgeProfile(id: string, payload: Partial<ProfileCreatePayload>): Promise<Profile> {
  return (await apiClient.patch<Profile>(`/api/v1/knowledge-profiles/${id}`, payload)).data
}
