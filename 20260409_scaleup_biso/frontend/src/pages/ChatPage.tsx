import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Sparkles,
  Search,
  ArrowRight,
  Loader2,
  Database,
  BookOpen,
  Building2,
  FileText,
  AlertTriangle,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useApp } from '../App';
import api from '../api/client';
import type {
  ChatMessage,
  ChatResponseData,
  DrugSideEffect,
  DrugTarget,
  DrugTrial,
  Hospital,
} from '../types';

/* ───────────────────── Suggestions ───────────────────── */

const patientSuggestions = [
  { text: '유방암 표준요법 약물 목록 알려줘', icon: Sparkles },
  { text: 'Docetaxel 부작용 알려줘', icon: AlertTriangle },
  { text: '서울 지역 유방암 치료 병원', icon: Building2 },
  { text: 'Paclitaxel 임상시험 정보', icon: FileText },
  { text: '유방암 예방 생활 가이드', icon: BookOpen },
  { text: '유방암 환자 추천 음식', icon: Sparkles },
];

const researcherSuggestions = [
  { text: 'Docetaxel 타겟 유전자 분석', icon: Database },
  { text: '파이프라인 약물 랭킹 보여줘', icon: Sparkles },
  { text: 'Docetaxel pathway 조회', icon: Search },
  { text: 'breast cancer docetaxel PubMed', icon: BookOpen },
  { text: 'Knowledge Graph 통계', icon: Database },
  { text: '신약 재창출 후보 목록', icon: FileText },
];

const thinkingLabels = [
  { text: '질문을 분석하고 있어요', emoji: '🧠' },
  { text: 'Knowledge Graph 검색 중', emoji: '🔍' },
  { text: '결과를 정리하고 있어요', emoji: '✨' },
];

/* ───────────────────── Welcome Screen ───────────────────── */

function WelcomeScreen({ onSend }: { onSend: (t: string) => void }) {
  const { mode, reducedMotion } = useApp();
  const suggestions =
    mode === 'patient' ? patientSuggestions : researcherSuggestions;
  const motionProps = reducedMotion
    ? {}
    : { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 } };

  return (
    <motion.div
      {...(reducedMotion ? {} : { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } })}
      className="flex-1 flex flex-col items-center justify-center px-4 relative overflow-hidden"
    >
      <div className="orb w-[500px] h-[500px] bg-violet-600/20 absolute -top-40 left-1/2 -translate-x-1/2" />
      <div className="orb w-[350px] h-[350px] bg-cyan-500/10 absolute top-32 -right-10" style={{ animationDelay: '3s' }} />

      {/* Hero */}
      <motion.div
        {...(reducedMotion ? {} : { initial: { opacity: 0, y: 30 }, animate: { opacity: 1, y: 0 }, transition: { delay: 0.15, duration: 0.7 } })}
        className="text-center mb-12 relative z-10"
      >
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center mx-auto mb-6 shadow-lg shadow-violet-500/25">
          <Sparkles className="w-8 h-8 text-white" aria-hidden="true" />
        </div>
        <h1 className="text-5xl font-bold gradient-text mb-4 leading-tight">BioChat AI</h1>
        <p className="text-zinc-400 text-lg max-w-md mx-auto leading-relaxed">
          {mode === 'patient'
            ? '유방암 약물 정보를 쉽게 알아보세요'
            : '유방암 약물 발견 파이프라인 AI 어시스턴트'}
        </p>
      </motion.div>

      {/* Suggestion Grid */}
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-w-3xl w-full relative z-10"
        role="list"
        aria-label="추천 질문"
      >
        {suggestions.map((s, i) => {
          const Icon = s.icon;
          return (
            <motion.button
              key={s.text}
              role="listitem"
              {...(reducedMotion ? {} : { ...motionProps, transition: { delay: 0.45 + i * 0.07, duration: 0.4 }, whileHover: { scale: 1.02, y: -2 }, whileTap: { scale: 0.98 } })}
              onClick={() => onSend(s.text)}
              className="glass glass-hover rounded-2xl px-4 py-4 text-left flex items-start gap-3 cursor-pointer group"
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                  mode === 'patient'
                    ? 'bg-rose-500/10 text-rose-400 group-hover:bg-rose-500/20'
                    : 'bg-cyan-500/10 text-cyan-400 group-hover:bg-cyan-500/20'
                }`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
              </div>
              <span className="text-sm text-zinc-300 group-hover:text-white transition-colors leading-relaxed flex-1">
                {s.text}
              </span>
              <ArrowRight className="w-4 h-4 text-zinc-700 group-hover:text-zinc-400 mt-0.5 shrink-0 transition-all group-hover:translate-x-0.5" aria-hidden="true" />
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
}

/* ───────────────────── Thinking Indicator ───────────────────── */

function ThinkingIndicator({ step }: { step: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3 mb-4"
      role="status"
      aria-label="AI가 응답을 생성하고 있습니다"
    >
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shrink-0 shadow-lg shadow-violet-500/20">
        <Sparkles className="w-4 h-4 text-white" aria-hidden="true" />
      </div>
      <div className="glass rounded-2xl rounded-tl-md px-4 py-3 max-w-md">
        {thinkingLabels.slice(0, step + 1).map((s, i) => (
          <div
            key={s.text}
            className={`flex items-center gap-2 text-sm text-zinc-300 py-1 ${
              i < step ? 'opacity-40' : ''
            }`}
          >
            <span className="text-xs" aria-hidden="true">{s.emoji}</span>
            <span>{s.text}</span>
            {i === step && (
              <span className="flex gap-0.5 ml-1" aria-hidden="true">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </span>
            )}
          </div>
        ))}
      </div>
    </motion.div>
  );
}

/* ───────────────────── Rich Content — 실제 API 형식 대응 ───────────────────── */

function RichContent({ data }: { data: ChatResponseData }) {
  const detail = data.detail;
  if (!detail) return null;

  const d = detail as Record<string, unknown>;
  const sideEffects = d.side_effects as DrugSideEffect[] | undefined;
  const targets = d.targets as DrugTarget[] | undefined;
  const trials = d.trials as DrugTrial[] | undefined;
  const hospitals = d.hospitals as Hospital[] | undefined;
  const news = d.news as Array<{ title: string; url?: string }> | undefined;
  const drugs = d.drugs as Array<{ name: string; rank?: number | null; overall_score?: number | null; target?: string | null }> | undefined;

  // Disease stats (유방암 통계 등)
  const hasStats = 'code' in d || 'ensemble_spearman' in d;

  return (
    <div className="space-y-3 mt-2">
      {drugs && drugs.length > 0 && <DrugListCards items={drugs} />}
      {sideEffects && sideEffects.length > 0 && <SideEffectCards items={sideEffects} />}
      {targets && targets.length > 0 && <TargetCards items={targets} />}
      {trials && trials.length > 0 && <TrialCards items={trials} />}
      {hospitals && hospitals.length > 0 && <HospitalCards items={hospitals} />}
      {news && news.length > 0 && <NewsCards items={news} />}
      {hasStats && <StatsDetail detail={detail as Record<string, unknown>} />}
    </div>
  );
}

function DrugListCards({ items }: { items: Array<{ name: string; rank?: number | null; overall_score?: number | null; target?: string | null }> }) {
  return (
    <div className="space-y-1.5" role="list" aria-label="약물 목록">
      {items.map((drug, i) => (
        <motion.div
          key={drug.name}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.04 }}
          className="bg-white/[0.04] rounded-xl px-4 py-2.5 flex items-center gap-3 hover:bg-white/[0.06] transition-colors"
          role="listitem"
        >
          <div className="w-7 h-7 rounded-lg bg-violet-500/15 flex items-center justify-center text-violet-400 text-xs font-bold shrink-0">
            {drug.rank ?? i + 1}
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>{drug.name}</span>
            {drug.target && <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>{drug.target}</span>}
          </div>
          {drug.overall_score != null && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-300 tabular-nums">
              {drug.overall_score}
            </span>
          )}
        </motion.div>
      ))}
    </div>
  );
}

function NewsCards({ items }: { items: Array<{ title: string; url?: string }> }) {
  return (
    <div className="space-y-2" role="list" aria-label="뉴스 목록">
      {items.map((item, i) => (
        <div key={item.url ?? i} className="bg-white/[0.04] rounded-xl px-4 py-2.5" role="listitem">
          {item.url ? (
            <a href={item.url} target="_blank" rel="noopener noreferrer"
              className="text-sm text-violet-400 hover:text-violet-300 transition-colors leading-relaxed">
              {item.title}
            </a>
          ) : (
            <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{item.title}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function StatsDetail({ detail }: { detail: Record<string, unknown> }) {
  const displayKeys = Object.entries(detail).filter(
    ([, v]) => typeof v === 'string' || typeof v === 'number',
  );
  if (displayKeys.length === 0) return null;

  const labelMap: Record<string, string> = {
    code: '질병 코드',
    name: '질병명',
    ensemble_spearman: 'Ensemble Spearman',
    ensemble_rmse: 'Ensemble RMSE',
    pipeline_date: '파이프라인 날짜',
  };

  return (
    <div className="grid grid-cols-2 gap-2" role="list" aria-label="통계 정보">
      {displayKeys.map(([key, value]) => (
        <div key={key} className="bg-white/[0.04] rounded-xl px-3 py-2.5 text-center" role="listitem">
          <p className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
            {typeof value === 'number' ? value.toLocaleString() : String(value)}
          </p>
          <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
            {labelMap[key] ?? key}
          </p>
        </div>
      ))}
    </div>
  );
}

function SideEffectCards({ items }: { items: DrugSideEffect[] }) {
  return (
    <div className="space-y-1" role="list" aria-label="부작용 목록">
      {items.map((item) => (
        <div key={item.meddra_term} className="flex items-center gap-2 text-sm py-0.5" role="listitem">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-400/70 shrink-0" aria-hidden="true" />
          <span className="text-zinc-200">{item.name}</span>
          <span className="text-zinc-600 text-xs">({item.meddra_term})</span>
        </div>
      ))}
    </div>
  );
}

function TargetCards({ items }: { items: DrugTarget[] }) {
  return (
    <div className="space-y-1.5" role="list" aria-label="타겟 유전자 목록">
      {items.map((item) => (
        <div
          key={`${item.gene_symbol}-${item.uniprot_id}`}
          className="bg-white/[0.04] rounded-xl px-4 py-2.5 hover:bg-white/[0.06] transition-colors"
          role="listitem"
        >
          <div className="flex items-center gap-2">
            <span className="text-sm text-white font-medium">{item.gene_symbol}</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-300">
              {item.uniprot_id}
            </span>
          </div>
          {item.protein_name && (
            <p className="text-xs text-zinc-500 mt-0.5">{item.protein_name}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function TrialCards({ items }: { items: DrugTrial[] }) {
  return (
    <div className="space-y-2" role="list" aria-label="임상시험 목록">
      {items.map((trial) => (
        <div key={trial.nct_id} className="bg-white/[0.04] rounded-xl px-4 py-2.5" role="listitem">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-medium">
              {trial.status}
            </span>
            <span className="text-zinc-500 text-xs">{trial.phase}</span>
          </div>
          <p className="text-sm text-zinc-200 leading-relaxed">{trial.title}</p>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-zinc-500">
            <span>{trial.nct_id}</span>
            <span>{trial.sponsor}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function HospitalCards({ items }: { items: Hospital[] }) {
  return (
    <div className="space-y-2" role="list" aria-label="병원 목록">
      {items.map((h) => (
        <div
          key={`${h.name}-${h.district}`}
          className="bg-white/[0.04] rounded-xl px-4 py-2.5 flex items-start gap-3"
          role="listitem"
        >
          <Building2 className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="text-sm text-white font-medium">{h.name}</p>
            <p className="text-xs text-zinc-400">{h.region} · {h.specialty}</p>
            <p className="text-xs text-zinc-500 mt-0.5">{h.address}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ───────────────────── Message Bubble ───────────────────── */

function MessageBubble({ message }: { message: ChatMessage }) {
  const { mode, reducedMotion } = useApp();
  const isUser = message.role === 'user';
  const [displayedText, setDisplayedText] = useState(isUser ? message.content : '');
  const [streamDone, setStreamDone] = useState(isUser);

  useEffect(() => {
    if (isUser || !message.content || reducedMotion) {
      setDisplayedText(message.content);
      setStreamDone(true);
      return;
    }
    let i = 0;
    const text = message.content;
    setDisplayedText('');
    setStreamDone(false);

    const interval = setInterval(() => {
      i++;
      if (i <= text.length) {
        setDisplayedText(text.slice(0, i));
      } else {
        setStreamDone(true);
        clearInterval(interval);
      }
    }, 12);

    return () => clearInterval(interval);
  }, [message.content, isUser, reducedMotion]);

  const accentUser =
    mode === 'patient' ? 'bg-rose-500/15 rounded-tr-md' : 'bg-cyan-500/15 rounded-tr-md';

  return (
    <motion.div
      initial={reducedMotion ? undefined : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reducedMotion ? 0 : 0.35 }}
      className={`flex items-start gap-3 mb-5 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-lg ${
          isUser
            ? mode === 'patient'
              ? 'bg-gradient-to-br from-rose-400 to-rose-600 shadow-rose-500/20'
              : 'bg-gradient-to-br from-cyan-400 to-cyan-600 shadow-cyan-500/20'
            : 'bg-gradient-to-br from-violet-500 to-indigo-600 shadow-violet-500/20'
        }`}
        aria-hidden="true"
      >
        {isUser ? (
          <span className="text-white text-xs font-bold">U</span>
        ) : (
          <Sparkles className="w-3.5 h-3.5 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={`max-w-[78%] ${isUser ? 'text-right' : ''}`}>
        <div className={`rounded-2xl px-4 py-3 ${isUser ? accentUser : 'glass rounded-tl-md'}`}>
          {isUser ? (
            <p className="text-sm text-zinc-100 leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div>
              {displayedText && (
                <div className={`text-sm leading-relaxed md-content ${
                  !streamDone ? "after:content-['▌'] after:text-violet-400 after:animate-pulse" : ''
                }`} style={{ color: 'var(--text-secondary)' }}>
                  <ReactMarkdown>{displayedText}</ReactMarkdown>
                </div>
              )}
              {streamDone && message.data != null ? (
                <RichContent data={message.data} />
              ) : null}
            </div>
          )}
        </div>
        {!isUser && message.source && streamDone && (
          <span className="inline-block mt-1.5 text-[10px] text-zinc-500 px-2 py-0.5 rounded-full bg-white/[0.03]">
            via {message.source}
          </span>
        )}
      </div>
    </motion.div>
  );
}

/* ───────────────────── Chat Input ───────────────────── */

function ChatInput({
  onSend,
  isLoading,
}: {
  onSend: (text: string) => void;
  isLoading: boolean;
}) {
  const [input, setInput] = useState('');
  const { mode } = useApp();
  const taRef = useRef<HTMLTextAreaElement>(null);

  const send = useCallback(() => {
    const t = input.trim();
    if (!t || isLoading) return;
    onSend(t);
    setInput('');
    if (taRef.current) taRef.current.style.height = 'auto';
  }, [input, isLoading, onSend]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const autoGrow = () => {
    const el = taRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 150) + 'px';
    }
  };

  const btnColor =
    mode === 'patient'
      ? 'bg-gradient-to-r from-rose-500 to-rose-600 hover:shadow-lg hover:shadow-rose-500/20'
      : 'bg-gradient-to-r from-cyan-500 to-cyan-600 hover:shadow-lg hover:shadow-cyan-500/20';

  return (
    <div className="px-4 pb-4 pt-2 shrink-0">
      <div
        className={`max-w-3xl mx-auto glass rounded-2xl p-1 transition-shadow duration-300 ${input ? 'glow-sm' : ''}`}
      >
        <div className="flex items-end gap-2 px-3 py-2">
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); autoGrow(); }}
            onKeyDown={handleKey}
            placeholder={mode === 'patient' ? '궁금한 것을 물어보세요...' : 'Query drugs, targets, pathways...'}
            rows={1}
            aria-label="메시지 입력"
            className="flex-1 bg-transparent text-zinc-100 text-sm placeholder-zinc-600 outline-none resize-none max-h-[150px] leading-relaxed py-1"
          />
          <button
            onClick={send}
            disabled={!input.trim() || isLoading}
            aria-label="메시지 전송"
            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-all duration-200 ${
              input.trim() && !isLoading
                ? `${btnColor} text-white`
                : 'bg-white/[0.04] text-zinc-600'
            }`}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
            ) : (
              <Send className="w-4 h-4" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
      <p className="text-[10px] text-zinc-600 text-center mt-2" aria-hidden="true">
        Neo4j Knowledge Graph &middot; PubMed &middot; NCIS
      </p>
    </div>
  );
}

/* ───────────────────── Chat Page ───────────────────── */

export default function ChatPage() {
  const { mode, messages, setMessages, reducedMotion } = useApp();
  const [isLoading, setIsLoading] = useState(false);
  const [thinkStep, setThinkStep] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const timersRef = useRef<Set<ReturnType<typeof setTimeout>>>(new Set());

  // Cleanup all timers on unmount (react.dev useEffect cleanup)
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach(clearTimeout);
      timers.clear();
    };
  }, []);

  const safeTimeout = useCallback((fn: () => void, ms: number) => {
    const id = setTimeout(() => {
      timersRef.current.delete(id);
      fn();
    }, ms);
    timersRef.current.add(id);
    return id;
  }, []);

  const scrollBottom = useCallback(() => {
    safeTimeout(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }, 50);
  }, [safeTimeout]);

  /** 프론트엔드 스마트 라우팅 — 백엔드 chat API가 인식 못하는 쿼리를 직접 처리 */
  const smartRoute = useCallback(
    async (text: string): Promise<ChatMessage> => {
      const t = text.toLowerCase();

      // 약물 목록 / 표준요법
      if (t.includes('약물') && (t.includes('목록') || t.includes('표준') || t.includes('리스트'))) {
        const status = t.includes('후보') || t.includes('재창출')
          ? 'BRCA_CANDIDATE'
          : t.includes('연구') || t.includes('임상')
            ? 'BRCA_RESEARCH'
            : 'BRCA_CURRENT';
        const res = await api.getDrugs(status);
        const drugs = Array.isArray(res.data) ? res.data : [];
        const label = status === 'BRCA_CURRENT' ? '현재 표준요법' : status === 'BRCA_RESEARCH' ? '연구/임상시험 중' : '신약 재창출 후보';
        return {
          id: crypto.randomUUID(), role: 'assistant',
          content: `유방암 ${label} 약물 ${drugs.length}개입니다:`,
          data: { answer: `유방암 ${label} 약물 ${drugs.length}개입니다:`, detail: { drugs } } as ChatResponseData,
          source: res.source, timestamp: new Date(),
        };
      }

      // 파이프라인 / 랭킹
      if (t.includes('파이프라인') || t.includes('랭킹') || t.includes('순위')) {
        const res = await api.getPipelineDrugs();
        const drugs = Array.isArray(res.data) ? res.data : [];
        return {
          id: crypto.randomUUID(), role: 'assistant',
          content: `약물 파이프라인 총 ${drugs.length}개 (랭킹순):`,
          data: { answer: `약물 파이프라인 총 ${drugs.length}개:`, detail: { drugs } } as ChatResponseData,
          source: res.source, timestamp: new Date(),
        };
      }

      // KG 통계
      if (t.includes('통계') && (t.includes('kg') || t.includes('knowledge') || t.includes('그래프') || t.includes('노드'))) {
        const res = await api.getStats();
        const s = res.data;
        return {
          id: crypto.randomUUID(), role: 'assistant',
          content: `Knowledge Graph 통계:\n- 전체 노드: ${s.total_nodes.toLocaleString()}\n- 전체 엣지: ${s.total_edges.toLocaleString()}`,
          data: { answer: 'Knowledge Graph 통계', detail: s as unknown as ChatResponseData['detail'] } as ChatResponseData,
          source: res.source, timestamp: new Date(),
        };
      }

      // 병원 (지역 포함)
      if (t.includes('병원') && !t.includes('부작용')) {
        const regionMatch = t.match(/(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)/);
        const res = await api.getHospitals(regionMatch?.[1]);
        const hospitals = Array.isArray(res.data) ? res.data : [];
        const regionLabel = regionMatch ? `${regionMatch[1]} 지역 ` : '';
        return {
          id: crypto.randomUUID(), role: 'assistant',
          content: `${regionLabel}유방암 치료 병원 ${hospitals.length}곳:`,
          data: { answer: `${regionLabel}병원 ${hospitals.length}곳`, detail: { hospitals } } as ChatResponseData,
          source: res.source, timestamp: new Date(),
        };
      }

      // 그 외 → 백엔드 chat API로 전달
      return null as unknown as ChatMessage;
    },
    [],
  );

  const handleSend = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setThinkStep(0);
      scrollBottom();

      const iv = setInterval(() => {
        setThinkStep((p) => Math.min(p + 1, thinkingLabels.length - 1));
      }, 900);

      try {
        // 1. 스마트 라우팅 시도
        const smartResult = await smartRoute(text);
        if (smartResult) {
          clearInterval(iv);
          setMessages((prev) => [...prev, smartResult]);
        } else {
          // 2. 백엔드 chat API 호출
          const res = await api.chat(text, mode);
          clearInterval(iv);

          const d = res.data;
          const content = d.answer || '';
          const aiMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content,
            data: d,
            source: res.source,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, aiMsg]);
        }
      } catch (err: unknown) {
        clearInterval(iv);
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `연결 오류가 발생했습니다.\n\n${msg}\n\n백엔드 서버가 실행 중인지 확인해주세요.`,
            timestamp: new Date(),
          },
        ]);
      } finally {
        setIsLoading(false);
        scrollBottom();
      }
    },
    [mode, setMessages, scrollBottom],
  );

  return (
    <motion.div
      initial={reducedMotion ? undefined : { opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={reducedMotion ? undefined : { opacity: 0 }}
      transition={{ duration: reducedMotion ? 0 : 0.2 }}
      className="h-full flex flex-col"
    >
      <AnimatePresence mode="wait">
        {messages.length === 0 ? (
          <WelcomeScreen key="welcome" onSend={handleSend} />
        ) : (
          <motion.div
            key="messages"
            initial={reducedMotion ? undefined : { opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex-1 overflow-y-auto"
            ref={scrollRef}
            role="log"
            aria-label="대화 내역"
            aria-live="polite"
          >
            <div className="max-w-3xl mx-auto px-4 py-6">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isLoading && <ThinkingIndicator step={thinkStep} />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </motion.div>
  );
}
