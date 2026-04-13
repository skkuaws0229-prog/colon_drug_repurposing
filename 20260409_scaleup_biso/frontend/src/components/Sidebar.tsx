import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare,
  LayoutDashboard,
  Pill,
  FlaskConical,
  Users,
  Plus,
  Trash2,
  Sun,
  Moon,
  Monitor,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import { useApp } from '../App';

const navItems = [
  { path: '/', icon: MessageSquare, label: 'AI Chat' },
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/drugs', icon: Pill, label: '약물 탐색' },
];

const themeOptions = [
  { value: 'dark' as const, icon: Moon, label: 'Dark' },
  { value: 'light' as const, icon: Sun, label: 'Light' },
  { value: 'system' as const, icon: Monitor, label: 'System' },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    mode,
    setMode,
    theme,
    setTheme,
    reducedMotion,
    conversations,
    activeConvId,
    newConversation,
    switchConversation,
    deleteConversation,
    sidebarOpen,
    setSidebarOpen,
  } = useApp();

  const spring = reducedMotion
    ? { duration: 0 }
    : { type: 'spring' as const, stiffness: 400, damping: 30 };

  return (
    <motion.aside
      animate={{ width: sidebarOpen ? 280 : 72 }}
      transition={reducedMotion ? { duration: 0 } : { duration: 0.25 }}
      className="h-screen flex flex-col border-r shrink-0 z-50 overflow-hidden"
      style={{ background: 'var(--sidebar-bg)', borderColor: 'var(--border)', backdropFilter: 'blur(20px)' }}
      role="navigation"
      aria-label="메인 내비게이션"
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-4 shrink-0">
        <button
          onClick={() => navigate('/')}
          aria-label="BioChat AI 홈"
          className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shrink-0 hover:shadow-lg hover:shadow-violet-500/20 transition-shadow"
        >
          <FlaskConical className="w-5 h-5 text-white" aria-hidden="true" />
        </button>
        <AnimatePresence>
          {sidebarOpen && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-sm font-semibold gradient-text whitespace-nowrap"
            >
              BioChat AI
            </motion.span>
          )}
        </AnimatePresence>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label={sidebarOpen ? '사이드바 접기' : '사이드바 펼치기'}
          className="ml-auto w-8 h-8 rounded-lg flex items-center justify-center t-muted hover:t-primary transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-3 mb-2 shrink-0">
        <button
          onClick={() => { newConversation(); navigate('/'); }}
          aria-label="새 대화"
          className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors"
          style={{ background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)' }}
        >
          <Plus className="w-4 h-4 shrink-0" />
          {sidebarOpen && <span>새 대화</span>}
        </button>
      </div>

      {/* Conversation History */}
      {sidebarOpen && (
        <div className="flex-1 overflow-y-auto px-3 min-h-0">
          {conversations.length > 0 && (
            <div className="mb-3">
              <p className="text-[10px] font-semibold uppercase tracking-widest px-2 mb-1.5" style={{ color: 'var(--text-muted)' }}>
                대화 이력
              </p>
              <div className="space-y-0.5">
                {conversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors text-sm ${
                      activeConvId === conv.id ? '' : ''
                    }`}
                    style={{
                      background: activeConvId === conv.id ? 'var(--surface-hover)' : 'transparent',
                      color: activeConvId === conv.id ? 'var(--text)' : 'var(--text-secondary)',
                    }}
                    onClick={() => { switchConversation(conv.id); navigate('/'); }}
                  >
                    <MessageSquare className="w-3.5 h-3.5 shrink-0 opacity-50" />
                    <span className="truncate flex-1">{conv.title}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id); }}
                      aria-label={`${conv.title} 삭제`}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:text-red-400"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className="px-3 py-2 shrink-0 space-y-0.5" aria-label="페이지 이동">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              aria-label={item.label}
              aria-current={isActive ? 'page' : undefined}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-all relative ${
                sidebarOpen ? '' : 'justify-center'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNav"
                  className="absolute inset-0 rounded-xl"
                  style={{ background: 'var(--surface-hover)' }}
                  transition={spring}
                />
              )}
              <Icon
                className={`w-[18px] h-[18px] relative z-10 shrink-0 transition-colors ${
                  isActive ? '' : ''
                }`}
                style={{ color: isActive ? 'var(--text)' : 'var(--text-muted)' }}
                aria-hidden="true"
              />
              {sidebarOpen && (
                <span className="relative z-10" style={{ color: isActive ? 'var(--text)' : 'var(--text-secondary)' }}>
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Controls */}
      <div className="px-3 py-3 shrink-0 space-y-2" style={{ borderTop: '1px solid var(--border)' }}>
        {/* Theme Toggle */}
        {sidebarOpen ? (
          <div className="flex items-center rounded-xl p-1" style={{ background: 'var(--surface)' }}>
            {themeOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTheme(opt.value)}
                aria-label={`${opt.label} 테마`}
                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  theme === opt.value ? '' : ''
                }`}
                style={{
                  background: theme === opt.value ? 'var(--surface-hover)' : 'transparent',
                  color: theme === opt.value ? 'var(--text)' : 'var(--text-muted)',
                  boxShadow: theme === opt.value ? 'var(--shadow)' : 'none',
                }}
              >
                <opt.icon className="w-3.5 h-3.5" aria-hidden="true" />
                {opt.label}
              </button>
            ))}
          </div>
        ) : (
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label="테마 전환"
            className="w-full flex justify-center py-2 rounded-xl transition-colors"
            style={{ color: 'var(--text-muted)' }}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        )}

        {/* Mode Toggle */}
        <button
          onClick={() => setMode(mode === 'patient' ? 'researcher' : 'patient')}
          aria-label={`현재: ${mode === 'patient' ? '환자/보호자' : '연구자'} 모드`}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl transition-all ${sidebarOpen ? '' : 'justify-center'}`}
        >
          <motion.div
            animate={{
              background: mode === 'patient'
                ? 'linear-gradient(135deg, #fb7185, #e11d48)'
                : 'linear-gradient(135deg, #22d3ee, #0891b2)',
            }}
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            transition={{ duration: reducedMotion ? 0 : 0.3 }}
          >
            <Users className="w-4 h-4 text-white" aria-hidden="true" />
          </motion.div>
          {sidebarOpen && (
            <div className="text-left">
              <p className="text-xs font-medium" style={{ color: 'var(--text)' }}>
                {mode === 'patient' ? '환자/보호자' : '연구자'}
              </p>
              <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                모드 전환
              </p>
            </div>
          )}
        </button>
      </div>
    </motion.aside>
  );
}
