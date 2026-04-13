import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  Database, GitBranch, Pill, Beaker, Target,
  MessageSquare, Search, BookOpen, TrendingUp, Layers,
} from 'lucide-react';
import { useApp } from '../App';
import api from '../api/client';
import type { KGStats } from '../types';

/* ── Animated counter ── */
function useCounter(target: number, duration = 2000) {
  const [count, setCount] = useState(0);
  const { reducedMotion } = useApp();
  useEffect(() => {
    if (!target) return;
    if (reducedMotion) { setCount(target); return; }
    const t0 = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const p = Math.min((now - t0) / duration, 1);
      setCount(Math.floor(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, reducedMotion]);
  return count;
}

function StatCard({ icon: Icon, label, value, color, delay }: {
  icon: React.ElementType; label: string; value: number; color: string; delay: number;
}) {
  const count = useCounter(value);
  const { reducedMotion } = useApp();
  return (
    <motion.div
      initial={reducedMotion ? undefined : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: reducedMotion ? 0 : delay }}
      whileHover={reducedMotion ? undefined : { scale: 1.02, y: -2 }}
      className="glass rounded-2xl p-6 flex flex-col items-center text-center"
    >
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${color}`}>
        <Icon className="w-6 h-6" aria-hidden="true" />
      </div>
      <p className="text-3xl font-bold tabular-nums tracking-tight" style={{ color: 'var(--text)' }}>
        {count.toLocaleString()}
      </p>
      <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>{label}</p>
    </motion.div>
  );
}

/* ── Chart colors ── */
const NODE_COLORS = ['#8b5cf6', '#6366f1', '#22d3ee', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#f97316'];
const PIPE_COLORS = ['#10b981', '#f59e0b', '#8b5cf6'];

const pipelineCards = [
  { status: 'BRCA_CURRENT', label: '현재 표준요법', count: 6, gradient: 'from-emerald-500 to-emerald-600', icon: Pill },
  { status: 'BRCA_RESEARCH', label: '연구/임상시험 중', count: 5, gradient: 'from-amber-500 to-amber-600', icon: Beaker },
  { status: 'BRCA_CANDIDATE', label: '신약 재창출 후보', count: 4, gradient: 'from-violet-500 to-violet-600', icon: Target },
];

/* ── Custom tooltip ── */
function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs shadow-xl" style={{ color: 'var(--text)' }}>
      <p className="font-medium">{label}</p>
      <p style={{ color: 'var(--text-secondary)' }}>{payload[0].value.toLocaleString()}</p>
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { mode, reducedMotion, effectiveTheme } = useApp();
  const [stats, setStats] = useState<KGStats | null>(null);

  useEffect(() => {
    api.getStats().then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const totalNodes = stats?.total_nodes ?? 30558;
  const totalEdges = stats?.total_edges ?? 137465;
  const drugCount = stats?.nodes?.Drug ?? 19844;
  const pathwayCount = stats?.nodes?.Pathway ?? 686;

  // Chart data
  const nodeChartData = stats?.nodes
    ? Object.entries(stats.nodes).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
    : [];

  const pipeChartData = pipelineCards.map((c) => ({ name: c.label, value: c.count }));

  const quickActions = mode === 'patient'
    ? [
        { label: 'AI 상담', icon: MessageSquare, path: '/' },
        { label: '약물 정보', icon: Pill, path: '/drugs' },
        { label: '생활 가이드', icon: BookOpen, path: '/' },
      ]
    : [
        { label: 'AI 분석', icon: MessageSquare, path: '/' },
        { label: '약물 파이프라인', icon: Pill, path: '/drugs' },
        { label: '논문 검색', icon: Search, path: '/' },
      ];

  const axisColor = effectiveTheme === 'dark' ? '#52525b' : '#94a3b8';

  return (
    <motion.div
      initial={reducedMotion ? undefined : { opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={reducedMotion ? undefined : { opacity: 0 }}
      className="h-full overflow-y-auto"
    >
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <motion.div initial={reducedMotion ? undefined : { opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10 relative">
          <div className="orb w-[500px] h-[300px] bg-violet-600/10 -top-48 -left-32" />
          <h1 className="text-3xl font-bold relative z-10" style={{ color: 'var(--text)' }}>Dashboard</h1>
          <p className="mt-1 relative z-10" style={{ color: 'var(--text-secondary)' }}>
            {mode === 'patient' ? '유방암 약물 정보를 한눈에 확인하세요' : 'Breast Cancer Drug Discovery Pipeline Overview'}
          </p>
        </motion.div>

        {/* Stats */}
        <section aria-label="Knowledge Graph 통계" className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          <StatCard icon={Database} label="KG 전체 노드" value={totalNodes} color="bg-violet-500/15 text-violet-400" delay={0.1} />
          <StatCard icon={GitBranch} label="KG 전체 엣지" value={totalEdges} color="bg-indigo-500/15 text-indigo-400" delay={0.2} />
          <StatCard icon={Pill} label="Drug 노드" value={drugCount} color="bg-cyan-500/15 text-cyan-400" delay={0.3} />
          <StatCard icon={Layers} label="Pathway 노드" value={pathwayCount} color="bg-emerald-500/15 text-emerald-400" delay={0.4} />
        </section>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
          {/* Bar Chart - Node Distribution */}
          {nodeChartData.length > 0 && (
            <motion.section
              initial={reducedMotion ? undefined : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: reducedMotion ? 0 : 0.3 }}
              className="glass rounded-2xl p-5"
              aria-label="노드 타입 분포 차트"
            >
              <h2 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text)' }}>
                <Database className="w-4 h-4 text-violet-400" aria-hidden="true" />
                노드 타입 분포
              </h2>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={nodeChartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: axisColor }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: axisColor }} axisLine={false} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : `${v}`} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface)' }} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {nodeChartData.map((_, i) => (
                      <Cell key={i} fill={NODE_COLORS[i % NODE_COLORS.length]} fillOpacity={0.8} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </motion.section>
          )}

          {/* Pie Chart - Drug Pipeline */}
          <motion.section
            initial={reducedMotion ? undefined : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: reducedMotion ? 0 : 0.4 }}
            className="glass rounded-2xl p-5"
            aria-label="약물 파이프라인 차트"
          >
            <h2 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: 'var(--text)' }}>
              <TrendingUp className="w-4 h-4 text-violet-400" aria-hidden="true" />
              약물 파이프라인 분포
            </h2>
            <div className="flex items-center gap-6">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie
                    data={pipeChartData}
                    cx="50%" cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {pipeChartData.map((_, i) => (
                      <Cell key={i} fill={PIPE_COLORS[i]} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-3 flex-1">
                {pipelineCards.map((card, i) => (
                  <div key={card.status} className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full shrink-0" style={{ background: PIPE_COLORS[i] }} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate" style={{ color: 'var(--text)' }}>{card.label}</p>
                    </div>
                    <span className="text-sm font-bold tabular-nums" style={{ color: 'var(--text)' }}>{card.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.section>
        </div>

        {/* Pipeline Cards */}
        <motion.section
          initial={reducedMotion ? undefined : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: reducedMotion ? 0 : 0.5 }}
          className="mb-10"
          aria-label="약물 파이프라인"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {pipelineCards.map((card, i) => (
              <motion.button
                key={card.status}
                whileHover={reducedMotion ? undefined : { scale: 1.02, y: -2 }}
                whileTap={reducedMotion ? undefined : { scale: 0.98 }}
                onClick={() => navigate('/drugs')}
                aria-label={`${card.label} ${card.count}개`}
                className="glass rounded-2xl p-5 text-left cursor-pointer"
              >
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center mb-3 shadow-lg`}>
                  <card.icon className="w-5 h-5 text-white" aria-hidden="true" />
                </div>
                <p className="text-2xl font-bold" style={{ color: 'var(--text)' }}>{card.count}</p>
                <p className="text-sm mt-0.5" style={{ color: 'var(--text-secondary)' }}>{card.label}</p>
                <div className="mt-3 h-1 rounded-full overflow-hidden" style={{ background: 'var(--surface)' }}
                  role="progressbar" aria-valuenow={card.count} aria-valuemax={15}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(card.count / 15) * 100}%` }}
                    transition={{ delay: reducedMotion ? 0 : 0.8 + i * 0.1, duration: reducedMotion ? 0 : 0.8 }}
                    className={`h-full rounded-full bg-gradient-to-r ${card.gradient}`}
                  />
                </div>
              </motion.button>
            ))}
          </div>
        </motion.section>

        {/* Quick Actions */}
        <motion.section
          initial={reducedMotion ? undefined : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: reducedMotion ? 0 : 0.7 }}
          aria-label="빠른 실행"
        >
          <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--text)' }}>빠른 실행</h2>
          <div className="grid grid-cols-3 gap-4">
            {quickActions.map((a) => (
              <motion.button
                key={a.label}
                whileHover={reducedMotion ? undefined : { scale: 1.02, y: -2 }}
                onClick={() => navigate(a.path)}
                aria-label={a.label}
                className="glass rounded-2xl p-5 text-center"
              >
                <div className={`w-12 h-12 rounded-xl mx-auto mb-3 flex items-center justify-center ${
                  mode === 'patient' ? 'bg-rose-500/10 text-rose-400' : 'bg-cyan-500/10 text-cyan-400'
                }`}>
                  <a.icon className="w-5 h-5" aria-hidden="true" />
                </div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{a.label}</p>
              </motion.button>
            ))}
          </div>
        </motion.section>
      </div>
    </motion.div>
  );
}
