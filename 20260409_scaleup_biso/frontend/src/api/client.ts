import type {
  ApiResponse,
  Drug,
  DrugTarget,
  DrugSideEffect,
  DrugTrial,
  DrugPathway,
  Hospital,
  KGStats,
  ChatResponseData,
} from '../types';

// Vercel 배포 시: 프록시 경유 (상대 경로) → ngrok 차단 우회
// 로컬 개발 시: Vite proxy 경유 (상대 경로)
// 직접 지정 시: VITE_API_URL 환경변수
const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true',
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export const api = {
  getDrugs: (status?: string) =>
    fetchApi<Drug[]>(`/api/drugs${status ? `?status=${status}` : ''}`),

  getPipelineDrugs: () =>
    fetchApi<Drug[]>('/api/drugs?pipeline=true'),

  getDrugTargets: (drug: string) =>
    fetchApi<DrugTarget[]>(`/api/drug/${encodeURIComponent(drug)}/targets`),

  getDrugPathways: (drug: string) =>
    fetchApi<DrugPathway[]>(`/api/drug/${encodeURIComponent(drug)}/pathways`),

  getDrugSideEffects: (drug: string) =>
    fetchApi<DrugSideEffect[]>(`/api/drug/${encodeURIComponent(drug)}/side_effects`),

  getDrugTrials: (drug: string) =>
    fetchApi<DrugTrial[]>(`/api/drug/${encodeURIComponent(drug)}/trials`),

  getHospitals: (region?: string) =>
    fetchApi<Hospital[]>(`/api/hospitals${region ? `?region=${region}` : ''}`),

  getStats: () =>
    fetchApi<KGStats>('/api/stats'),

  searchPubmed: (query: string) =>
    fetchApi<unknown>(`/api/pubmed?query=${encodeURIComponent(query)}`),

  getNcisGuide: (category: string) =>
    fetchApi<unknown>(`/api/ncis/${encodeURIComponent(category)}`),

  chat: (query: string, userType: string) =>
    fetchApi<ChatResponseData>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ query, user_type: userType }),
    }),
};

export default api;
