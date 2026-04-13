/* ── 실제 API 응답 기반 타입 정의 (실측 2026-04-13) ── */

export type UserMode = 'patient' | 'researcher';
export type BrcaStatus = 'BRCA_CURRENT' | 'BRCA_RESEARCH' | 'BRCA_CANDIDATE';

/** GET /api/drugs?status=... */
export interface Drug {
  name: string;
  brca_status: BrcaStatus | null;
  overall_score: number | null;
  safety_score: number | null;
  ic50: number | null;
  max_phase: string | null;
  target: string | null;
  rank: number | null;
}

/** GET /api/drug/{name}/targets */
export interface DrugTarget {
  gene_symbol: string;
  protein_name: string | null;
  uniprot_id: string;
  function: string | null;
}

/** GET /api/drug/{name}/side_effects */
export interface DrugSideEffect {
  name: string;
  meddra_term: string;
}

/** GET /api/drug/{name}/trials */
export interface DrugTrial {
  nct_id: string;
  title: string;
  phase: string;
  status: string;
  sponsor: string;
  start_date: string;
  completion_date: string;
}

/** GET /api/drug/{name}/pathways */
export interface DrugPathway {
  name: string;
  source?: string;
}

/** GET /api/hospitals */
export interface Hospital {
  name: string;
  address: string;
  phone: string;
  url: string;
  region: string;
  specialty: string;
  category: string;
  district: string;
}

/** GET /api/stats */
export interface KGStats {
  nodes: Record<string, number>;
  edges: Record<string, number>;
  total_nodes: number;
  total_edges: number;
}

/** POST /api/chat → data */
export interface ChatResponseData {
  answer: string;
  detail?: {
    drug?: string;
    side_effects?: DrugSideEffect[];
    targets?: DrugTarget[];
    trials?: DrugTrial[];
    hospitals?: Hospital[];
    articles?: PubmedArticle[];
    [key: string]: unknown;
  };
  intent?: string;
  drug?: string;
}

export interface PubmedArticle {
  title: string;
  authors?: string;
  pmid?: string;
}

/** Chat message (client-side) */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  source?: string;
  data?: ChatResponseData;
  timestamp: Date;
}

/** Generic API envelope */
export interface ApiResponse<T = unknown> {
  status: string;
  data: T;
  source?: string;
  timestamp: string;
}
