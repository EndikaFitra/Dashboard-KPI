import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Loader2, Sparkles, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { postMcpChat } from "@/api/client";

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: 1,
    role: "assistant",
    content:
      "Halo, saya adalah asisten AI untuk membantu menganalisis data KPI. Silahkan ajukan pertanyaan Anda.",
  },
];

const SUGGESTIONS = [
  "Division overview 2025",
  "Underperforming KPIs",
  "Compare all divisions",
  "HR performance trend",
];

const SESSION_KEY = "kpi_chat_messages";

function loadMessages(): Message[] {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (raw) return JSON.parse(raw) as Message[];
  } catch { }
  return INITIAL_MESSAGES;
}

function saveMessages(msgs: Message[]) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(msgs));
}

// Module-level store — survives component unmount/remount within the same tab
const chatStore = {
  loading: false, // true while the AI fetch is in-flight
};

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>(loadMessages);
  // Initialise from module-level store → shows spinner immediately on remount
  const [loading, setLoading] = useState(chatStore.loading);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Sync React state AND module-level store atomically
  const setLoadingSync = useCallback((val: boolean) => {
    chatStore.loading = val;
    setLoading(val);
  }, []);

  // Keep a ref mirror so async handlers always see the latest list
  // even if the component has unmounted (stale closure guard)
  const messagesRef = useRef<Message[]>(messages);
  useEffect(() => { messagesRef.current = messages; }, [messages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // When loading finishes, re-read from sessionStorage.
  // This handles the case where the fetch completed while this component
  // instance was unmounted (e.g. user navigated away and came back).
  useEffect(() => {
    if (!loading) {
      const persisted = loadMessages();
      setMessages(persisted);
      messagesRef.current = persisted;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading]);

  const handleSend = async (question?: string) => {
    const text = (question ?? input).trim();
    if (!text || loading) return;

    const userMsg: Message = { id: Date.now(), role: "user", content: text };
    const withUser = [...messagesRef.current, userMsg];
    messagesRef.current = withUser;
    saveMessages(withUser);
    setMessages(withUser);
    setInput("");
    setLoadingSync(true);

    try {
      const data = await postMcpChat(text);
      const botMsg: Message = { id: Date.now() + 1, role: "assistant", content: data.response };
      // Read from ref (not state) — safe even if component unmounted
      const withBot = [...messagesRef.current, botMsg];
      messagesRef.current = withBot;
      saveMessages(withBot);       // ← always persisted regardless of mount state
      setMessages(withBot);        // no-op if unmounted, but sessionStorage already updated
    } catch {
      const errMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: "Sorry, I couldn't reach the AI backend. Please ensure the MCP server is running.",
      };
      const withErr = [...messagesRef.current, errMsg];
      messagesRef.current = withErr;
      saveMessages(withErr);
      setMessages(withErr);
    } finally {
      setLoadingSync(false);
    }
  };

  const handleClear = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setMessages(INITIAL_MESSAGES);
  }, []);

  return (
    <div className="flex flex-col h-[calc(100svh-3.5rem-2rem)] md:h-[calc(100svh-3.5rem-3rem)] max-w-3xl mx-auto">
      {/* Page header */}
      <div className="mb-4 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">AI Data Analyst</h1>
              <p className="text-xs text-muted-foreground">
                Powered by GroqAI · llama-3.1-8b-instant
              </p>
            </div>
          </div>
          {messages.length > 1 && (
            <button
              onClick={handleClear}
              title="Clear chat"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear chat
            </button>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 min-h-0 bg-card rounded-xl border border-border shadow-sm flex flex-col overflow-hidden">
        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 min-h-0 overflow-y-auto p-5 space-y-4"
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
              )}
              <div
                className={`max-w-[78%] rounded-2xl px-4 py-2.5 ${msg.role === "user"
                  ? "bg-primary text-primary-foreground rounded-tr-sm"
                  : "bg-accent text-foreground rounded-tl-sm"
                  }`}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.content}
                </p>
              </div>
              {msg.role === "user" && (
                <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4 text-muted-foreground" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="bg-accent rounded-2xl rounded-tl-sm px-4 py-2.5 flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                <span className="text-sm text-muted-foreground">
                  Analyzing KPI data...
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Quick suggestions — only when first message */}
        {messages.length === 1 && (
          <div className="px-5 pb-3 flex flex-wrap gap-2 shrink-0">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => handleSend(s)}
                className="text-xs px-3 py-1.5 rounded-full border border-border bg-accent hover:bg-accent/70 text-muted-foreground transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input bar */}
        <div className="p-4 border-t border-border shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your KPI data..."
              className="text-sm h-10 bg-accent/40 border-0 focus-visible:ring-1 flex-1"
              disabled={loading}
            />
            <Button
              type="submit"
              size="icon"
              className="h-10 w-10 shrink-0 rounded-xl"
              disabled={loading || !input.trim()}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
