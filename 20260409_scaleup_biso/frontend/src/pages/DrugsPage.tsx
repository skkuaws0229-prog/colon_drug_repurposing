import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Pill,
  X,
  Target,
  Route,
  AlertTriangle,
  FileText,
  Search,
  Loader2,
  ChevronRight,
} from 'lucide-react';
import { useApp } from '../App';
import api from '../api/client';
import type { BrcaStatus, Drug, DrugTarget, DrugSideEffect, DrugTrial, DrugPathway } from '../types';

/* ── Tabs ── */
const statusTabs: { status: BrcaStatus; label: string; color: string }[] = [
  { status: 'BRCA_CURRENT', label: '현재 표준요법', color: 'emerald' },
  { status: 'BRCA_RESEARCH', label: '연구/임상시험', color: 'amber' },
  { status: 'BRCA_CANDIDATE', label: '신약 후보', color: 'violet' },
];

const detailTabs = [
  { id: 'targets', label: '타겟', icon: Target },
  { id: 'pathways', label: 'Pathway', icon: Route },
  { id: 'side_effects', label: '부작용', icon: AlertTriangle },
  { id: 'trials', label: '임상시험', icon: FileText },
] as const;

type DetailTabId = (typeof detailTabs)[number]['id'];
type DetailData = DrugTarget[] | DrugSideEffect[] | DrugTrial[] | DrugPathway[];

/* ── Page ── */
export default function DrugsPage() {
  const { mode, reducedMotion } = useApp();
  const [activeTab, setActiveTab] = useState<BrcaStatus>('BRCA_CURRENT');
  const [drugs, setDrugs] = useState<Drug[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedDrug, setSelectedDrug] = useState<string | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTabId>('targets');
  const [detailData, setDetailData] = useState<DetailData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  /* Fetch drugs */
  useEffect(() => {
    setLoading(true);
    setDrugs([]);
    api.getDrugs(activeTab)
      .then((r) => setDrugs(Array.isArray(r.data) ? r.data : []))
      .catch(() => setDrugs([]))
      .finally(() => setLoading(false));
  }, [activeTab]);

  /* Fetch detail */
  useEffect(() => {
    if (!selectedDrug) return;
    setDetailLoading(true);
    setDetailData(null);

    const fetchers: Record<DetailTabId, (n: string) => Promise<{ data: DetailData }>> = {
      targets: (n) => api.getDrugTargets(n) as Promise<{ data: DrugTarget[] }>,
      pathways: (n) => api.getDrugPathways(n) as Promise<{ data: DrugPathway[] }>,
      side_effects: (n) => api.getDrugSideEffects(n) as Promise<{ data: DrugSideEffect[] }>,
      trials: (n) => api.getDrugTrials(n) as Promise<{ data: DrugTrial[] }>,
    };

    fetchers[detailTab](selectedDrug)
      .then((r) => setDetailData(Array.isArray(r.data) ? r.data : []))
      .catch(() => setDetailData([]))
      .finally(() => setDetailLoading(false));
  }, [selectedDrug, detailTab]);

  const filtered = drugs.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase()),
  );

  const tabMeta = statusTabs.find((t) => t.status === activeTab)!;

  const colorBg = (c: string) =>
    c === 'emerald' ? 'bg-emerald-500/15 text-emerald-400'
      : c === 'amber' ? 'bg-amber-500/15 text-amber-400'
      : 'bg-violet-500/15 text-violet-400';

  const tabBg = (c: string) =>
    c === 'emerald' ? 'bg-emerald-500/15' : c === 'amber' ? 'bg-amber-500/15' : 'bg-violet-500/15';

  return (
    <motion.div
      initial={reducedMotion ? undefined : { opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={reducedMotion ? undefined : { opacity: 0 }}
      transition={{ duration: reducedMotion ? 0 : 0.2 }}
      className="h-full flex"
    >
      {/* ── Main list ── */}
      <div className={`flex-1 overflow-y-auto transition-all duration-300 ${selectedDrug ? 'lg:mr-[400px]' : ''}`}>
        <div className="max-w-4xl mx-auto px-6 py-8">
          <motion.div
            initial={reducedMotion ? undefined : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <h1 className="text-3xl font-bold text-white">
              {mode === 'patient' ? '약물 정보' : '약물 파이프라인'}
            </h1>
            <p className="text-zinc-400 mt-1">
              {mode === 'patient'
                ? '유방암 치료에 사용되는 약물을 확인하세요'
                : 'Drug Discovery Pipeline — Ranked by Overall Score'}
            </p>
          </motion.div>

          {/* Search */}
          <div className="mb-5">
            <label htmlFor="drug-search" className="sr-only">약물 검색</label>
            <div className="glass rounded-xl px-4 py-2.5 flex items-center gap-3">
              <Search className="w-4 h-4 text-zinc-500" aria-hidden="true" />
              <input
                id="drug-search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="약물 검색..."
                className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-600 outline-none"
              />
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-6" role="tablist" aria-label="BRCA 상태 필터">
            {statusTabs.map((tab) => (
              <button
                key={tab.status}
                role="tab"
                aria-selected={activeTab === tab.status}
                aria-controls="drug-grid"
                onClick={() => { setActiveTab(tab.status); setSelectedDrug(null); }}
                className={`relative px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  activeTab === tab.status ? 'text-white' : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]'
                }`}
              >
                {activeTab === tab.status && (
                  <motion.div
                    layoutId="drugTab"
                    className={`absolute inset-0 rounded-xl ${tabBg(tab.color)}`}
                    transition={reducedMotion ? { duration: 0 } : { type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Drug Grid */}
          <div id="drug-grid" role="tabpanel">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-6 h-6 text-violet-400 animate-spin" aria-label="로딩 중" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-20 text-zinc-500">
                <Pill className="w-10 h-10 mx-auto mb-3 opacity-30" aria-hidden="true" />
                <p className="text-sm">약물을 찾을 수 없습니다</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3" role="list">
                <AnimatePresence mode="popLayout">
                  {filtered.map((drug, i) => {
                    const selected = selectedDrug === drug.name;
                    return (
                      <motion.button
                        key={drug.name}
                        layout={!reducedMotion}
                        initial={reducedMotion ? undefined : { opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={reducedMotion ? undefined : { opacity: 0, scale: 0.95 }}
                        transition={{ delay: i * 0.03, duration: reducedMotion ? 0 : 0.3 }}
                        whileHover={reducedMotion ? undefined : { scale: 1.01, y: -1 }}
                        onClick={() => { setSelectedDrug(selected ? null : drug.name); setDetailTab('targets'); }}
                        role="listitem"
                        aria-label={`${drug.name} — Score: ${drug.overall_score ?? 'N/A'}`}
                        className={`glass rounded-2xl p-5 text-left transition-all duration-200 group w-full ${
                          selected ? 'ring-1 ring-violet-500/30 bg-white/[0.05]' : 'hover:bg-white/[0.04]'
                        }`}
                      >
                        <div className="flex items-center gap-4">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold shrink-0 ${colorBg(tabMeta.color)}`}>
                            {drug.rank ?? i + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="text-white font-medium text-sm truncate">{drug.name}</h3>
                            <div className="flex items-center gap-2 mt-0.5">
                              {drug.target && <span className="text-xs text-zinc-500 truncate">{drug.target}</span>}
                              {drug.overall_score != null && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-300 tabular-nums">
                                  Score {drug.overall_score}
                                </span>
                              )}
                            </div>
                          </div>
                          <ChevronRight className={`w-4 h-4 shrink-0 transition-all ${
                            selected ? 'text-violet-400 rotate-90' : 'text-zinc-600 group-hover:text-zinc-400'
                          }`} aria-hidden="true" />
                        </div>
                      </motion.button>
                    );
                  })}
                </AnimatePresence>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Detail slide-over ── */}
      <AnimatePresence>
        {selectedDrug && (
          <motion.aside
            initial={reducedMotion ? undefined : { x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={reducedMotion ? undefined : { x: 400, opacity: 0 }}
            transition={reducedMotion ? { duration: 0 } : { type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed right-0 top-0 h-full w-full max-w-[400px] bg-zinc-900/95 backdrop-blur-xl border-l border-white/[0.06] z-40 flex flex-col"
            role="dialog"
            aria-label={`${selectedDrug} 상세 정보`}
          >
            {/* Header */}
            <div className="shrink-0 border-b border-white/[0.06] px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">{selectedDrug}</h2>
                <p className="text-xs text-zinc-500 mt-0.5">{activeTab.replace('BRCA_', '')}</p>
              </div>
              <button
                onClick={() => setSelectedDrug(null)}
                aria-label="패널 닫기"
                className="w-8 h-8 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] flex items-center justify-center text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>

            {/* Detail tabs */}
            <div className="shrink-0 px-5 py-3 flex gap-1 border-b border-white/[0.06] overflow-x-auto" role="tablist">
              {detailTabs.map((t) => (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={detailTab === t.id}
                  onClick={() => setDetailTab(t.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                    detailTab === t.id ? 'bg-violet-500/15 text-violet-300' : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]'
                  }`}
                >
                  <t.icon className="w-3 h-3" aria-hidden="true" />
                  {t.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-5 py-4" role="tabpanel">
              <AnimatePresence mode="wait">
                {detailLoading ? (
                  <motion.div key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center justify-center py-16">
                    <Loader2 className="w-5 h-5 text-violet-400 animate-spin" aria-label="로딩 중" />
                  </motion.div>
                ) : !detailData || detailData.length === 0 ? (
                  <motion.p key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-zinc-500 text-sm text-center py-16">
                    데이터 없음
                  </motion.p>
                ) : (
                  <motion.div
                    key={detailTab}
                    initial={reducedMotion ? undefined : { opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={reducedMotion ? undefined : { opacity: 0, y: -8 }}
                    className="space-y-2"
                    role="list"
                  >
                    {detailTab === 'targets' && (detailData as DrugTarget[]).map((t) => (
                      <div key={`${t.gene_symbol}-${t.uniprot_id}`} className="bg-white/[0.03] rounded-xl px-4 py-3 hover:bg-white/[0.05] transition-colors" role="listitem">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-white font-medium">{t.gene_symbol}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300">{t.uniprot_id}</span>
                        </div>
                        {t.protein_name && <p className="text-xs text-zinc-500 mt-1">{t.protein_name}</p>}
                      </div>
                    ))}
                    {detailTab === 'side_effects' && (detailData as DrugSideEffect[]).map((se) => (
                      <div key={se.meddra_term} className="bg-white/[0.03] rounded-xl px-4 py-3 flex items-center gap-2" role="listitem">
                        <div className="w-1.5 h-1.5 rounded-full bg-amber-400/70 shrink-0" aria-hidden="true" />
                        <span className="text-sm text-zinc-200">{se.name}</span>
                        <span className="text-xs text-zinc-500">({se.meddra_term})</span>
                      </div>
                    ))}
                    {detailTab === 'trials' && (detailData as DrugTrial[]).map((tr) => (
                      <div key={tr.nct_id} className="bg-white/[0.03] rounded-xl px-4 py-3" role="listitem">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium">{tr.status}</span>
                          <span className="text-xs text-zinc-500">{tr.phase}</span>
                        </div>
                        <p className="text-sm text-zinc-200 leading-relaxed">{tr.title}</p>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-zinc-500">
                          <span>{tr.nct_id}</span>
                          <span>{tr.sponsor}</span>
                          <span>{tr.start_date} ~ {tr.completion_date}</span>
                        </div>
                      </div>
                    ))}
                    {detailTab === 'pathways' && (detailData as DrugPathway[]).map((pw, i) => (
                      <div key={pw.name ?? i} className="bg-white/[0.03] rounded-xl px-4 py-3" role="listitem">
                        <span className="text-sm text-zinc-200">{pw.name}</span>
                        {pw.source && <p className="text-xs text-zinc-500 mt-1">Source: {pw.source}</p>}
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
