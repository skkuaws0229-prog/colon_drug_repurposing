import {
  createContext,
  useContext,
  useState,
  useMemo,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence, useReducedMotion } from 'framer-motion';
import type { UserMode, ChatMessage } from './types';
import Layout from './components/Layout';
import ChatPage from './pages/ChatPage';
import DashboardPage from './pages/DashboardPage';
import DrugsPage from './pages/DrugsPage';

/* ════════════════════════════════════════
   Types
   ════════════════════════════════════════ */

type Theme = 'dark' | 'light' | 'system';

interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
}

interface AppContextType {
  // Theme
  theme: Theme;
  setTheme: (t: Theme) => void;
  effectiveTheme: 'dark' | 'light';
  // Mode
  mode: UserMode;
  setMode: (m: UserMode) => void;
  // Chat & conversations
  messages: ChatMessage[];
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  conversations: Conversation[];
  activeConvId: string | null;
  newConversation: () => void;
  switchConversation: (id: string) => void;
  deleteConversation: (id: string) => void;
  // Accessibility
  reducedMotion: boolean;
  // Sidebar
  sidebarOpen: boolean;
  setSidebarOpen: (v: boolean) => void;
}

const AppContext = createContext<AppContextType>(null!);
export const useApp = () => useContext(AppContext);

/* ════════════════════════════════════════
   LocalStorage helpers
   ════════════════════════════════════════ */

const CONV_KEY = 'biochat_conversations';
const ACTIVE_KEY = 'biochat_active';
const THEME_KEY = 'biochat_theme';

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(CONV_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations(convs: Conversation[]) {
  localStorage.setItem(CONV_KEY, JSON.stringify(convs));
}

/* ════════════════════════════════════════
   Provider
   ════════════════════════════════════════ */

function AppProvider({ children }: { children: ReactNode }) {
  // Theme
  const [theme, setThemeState] = useState<Theme>(
    () => (localStorage.getItem(THEME_KEY) as Theme) || 'dark',
  );
  const prefersDark =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches;
  const effectiveTheme: 'dark' | 'light' =
    theme === 'system' ? (prefersDark ? 'dark' : 'light') : theme;

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    localStorage.setItem(THEME_KEY, t);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', effectiveTheme);
  }, [effectiveTheme]);

  // Mode
  const [mode, setMode] = useState<UserMode>('patient');

  // Conversations
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeConvId, setActiveConvId] = useState<string | null>(
    () => localStorage.getItem(ACTIVE_KEY),
  );
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const active = loadConversations().find(
      (c) => c.id === localStorage.getItem(ACTIVE_KEY),
    );
    return active?.messages ?? [];
  });

  // Sync messages → active conversation
  useEffect(() => {
    if (!activeConvId && messages.length > 0) {
      // Create new conversation
      const id = crypto.randomUUID();
      const title =
        messages[0]?.content.slice(0, 40) || 'New conversation';
      const conv: Conversation = {
        id,
        title,
        messages,
        createdAt: Date.now(),
      };
      setConversations((prev) => {
        const updated = [conv, ...prev];
        saveConversations(updated);
        return updated;
      });
      setActiveConvId(id);
      localStorage.setItem(ACTIVE_KEY, id);
    } else if (activeConvId && messages.length > 0) {
      setConversations((prev) => {
        const updated = prev.map((c) =>
          c.id === activeConvId
            ? {
                ...c,
                messages,
                title:
                  messages[0]?.content.slice(0, 40) || c.title,
              }
            : c,
        );
        saveConversations(updated);
        return updated;
      });
    }
  }, [messages, activeConvId]);

  const newConversation = useCallback(() => {
    setMessages([]);
    setActiveConvId(null);
    localStorage.removeItem(ACTIVE_KEY);
  }, []);

  const switchConversation = useCallback(
    (id: string) => {
      const conv = conversations.find((c) => c.id === id);
      if (conv) {
        setMessages(conv.messages);
        setActiveConvId(id);
        localStorage.setItem(ACTIVE_KEY, id);
      }
    },
    [conversations],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const updated = prev.filter((c) => c.id !== id);
        saveConversations(updated);
        return updated;
      });
      if (activeConvId === id) {
        setMessages([]);
        setActiveConvId(null);
        localStorage.removeItem(ACTIVE_KEY);
      }
    },
    [activeConvId],
  );

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Accessibility
  const prefersReducedMotion = useReducedMotion() ?? false;

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      effectiveTheme,
      mode,
      setMode,
      messages,
      setMessages,
      conversations,
      activeConvId,
      newConversation,
      switchConversation,
      deleteConversation,
      reducedMotion: prefersReducedMotion,
      sidebarOpen,
      setSidebarOpen,
    }),
    [
      theme,
      setTheme,
      effectiveTheme,
      mode,
      messages,
      conversations,
      activeConvId,
      newConversation,
      switchConversation,
      deleteConversation,
      prefersReducedMotion,
      sidebarOpen,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

/* ════════════════════════════════════════
   Routes
   ════════════════════════════════════════ */

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<ChatPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/drugs" element={<DrugsPage />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Layout>
          <AnimatedRoutes />
        </Layout>
      </AppProvider>
    </BrowserRouter>
  );
}
