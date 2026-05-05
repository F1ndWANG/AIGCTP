"use client";

import { Suspense, useState, useCallback, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import MessageList from "@/components/Chat/MessageList";
import ChatInput from "@/components/Chat/ChatInput";
import TravelPlanCard from "@/components/TravelPlan/TravelPlanCard";
import { chat as chatApi, commerce as commerceApi, travel as travelApi } from "@/lib/api";
import type { Message, TravelPlanResponse, TravelPlanListItem, ChatSession, ProductListItem } from "@/lib/types";

function generateId(): string {
  try { return crypto.randomUUID(); } catch { return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`; }
}

function ChatPageContent() {
  const { user, loading, logout } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;
  const [currentPlan, setCurrentPlan] = useState<TravelPlanResponse | null>(null);
  const currentPlanRef = useRef(currentPlan);
  currentPlanRef.current = currentPlan;
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<TravelPlanListItem[]>([]);
  const [thinkingText, setThinkingText] = useState("");
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [showChatHistory, setShowChatHistory] = useState(false);
  const [showProductSearch, setShowProductSearch] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [searchResults, setSearchResults] = useState<ProductListItem[]>([]);
  const [searching, setSearching] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const searchParams = useSearchParams();

  // Restore session from URL query param
  useEffect(() => {
    const sid = searchParams.get("session");
    if (sid) restoreSession(sid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Clean up SSE on unmount
  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  const handleSend = useCallback(
    (message: string) => {
      const userMsg: Message = { role: "user", content: message };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);

      const sid = sessionIdRef.current || generateId();
      if (!sessionIdRef.current) setSessionId(sid);

      // Add placeholder assistant message for streaming
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
      setThinkingText("AI 正在思考...");

      const controller = chatApi.sendStream(
        message,
        {
          onThinking: (text: string) => setThinkingText(text),
          onToken: (token: string) => {
            setThinkingText("");
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (last.role === "assistant") {
                copy[copy.length - 1] = { ...last, content: last.content + token };
              }
              return copy;
            });
          },
          onResult: (text: string) => {
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = { role: "assistant", content: text };
              return copy;
            });
          },
          onPlan: (plan: Record<string, unknown>) => {
            setCurrentPlan(plan as unknown as TravelPlanResponse);
          },
          onDone: () => { setSending(false); setThinkingText(""); },
          onError: (err: Error) => {
            toast(err.message, "error");
            setSending(false);
          },
        },
        sid,
        currentPlanRef.current?.id
      );
      abortRef.current = controller;
    },
    [toast]
  );

  const loadHistory = async () => {
    try {
      const { travel } = await import("@/lib/api");
      const plans = await travel.list();
      setHistory(plans);
      setShowHistory(!showHistory);
    } catch {}
  };

  const loadChatSessions = async () => {
    try {
      const sessions = await chatApi.listSessions();
      setChatSessions(sessions);
      setShowChatHistory(!showChatHistory);
    } catch { toast("加载历史对话失败", "error"); }
  };

  const restoreSession = async (sid: string) => {
    try {
      const detail = await chatApi.getSession(sid);
      setMessages(detail.messages);
      setSessionId(detail.session_id);
      const planContext = (detail.context?.current_travel_plan || null) as {
        id?: number;
        destination?: string;
        days?: number;
        itinerary?: TravelPlanResponse["itinerary"];
      } | null;
      if (planContext?.id) {
        try {
          const fullPlan = await travelApi.get(Number(planContext.id));
          setCurrentPlan(fullPlan);
        } catch {
          setCurrentPlan({
            id: Number(planContext.id),
            destination: planContext.destination || "",
            days: planContext.days || 1,
            itinerary: planContext.itinerary,
            status: "draft",
            created_at: "",
            updated_at: "",
            people_count: 1,
            preferences: {},
          });
        }
      } else {
        setCurrentPlan(null);
      }
      setShowChatHistory(false);
    } catch { toast("加载对话失败", "error"); }
  };

  const deleteSession = async (sid: string) => {
    if (!confirm("确定删除该对话？")) return;
    try {
      await chatApi.deleteSession(sid);
      setChatSessions((prev) => prev.filter((s) => s.session_id !== sid));
      toast("已删除", "success");
    } catch { toast("删除失败", "error"); }
  };

  const newChat = () => {
    setMessages([]);
    setSessionId(undefined);
    setCurrentPlan(null);
  };

  const handleProductSearch = async () => {
    if (!searchKeyword.trim()) return;
    setSearching(true);
    try {
      const data = await commerceApi.listProducts({ keyword: searchKeyword.trim(), page_size: 6 });
      setSearchResults(data.items);
    } catch { toast("搜索失败", "error"); }
    setSearching(false);
  };

  const handleAddToCart = async (productId: number) => {
    try {
      await commerceApi.addCartItem({ product_id: productId, quantity: 1 });
      toast("已加入购物车", "success");
    } catch { toast("加入购物车失败", "error"); }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
    router.push("/");
    return null;
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="font-bold text-lg">AI 生活推荐</h1>
            <button
              onClick={newChat}
              className="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-full hover:bg-blue-100 transition"
            >
              + 新对话
            </button>
            <button
              onClick={loadHistory}
              className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition"
            >
              历史行程
            </button>
            <button
              onClick={loadChatSessions}
              className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition"
            >
              历史对话
            </button>
            <button
              onClick={() => setShowProductSearch(!showProductSearch)}
              className="text-xs px-3 py-1.5 bg-orange-50 text-orange-600 rounded-full hover:bg-orange-100 transition"
            >
              搜商品
            </button>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{user.display_name}</span>
            <button
              onClick={() => logout()}
              className="text-xs px-3 py-1.5 text-red-500 hover:bg-red-50 rounded-full transition"
            >
              退出
            </button>
          </div>
        </div>
      </header>

      {/* History Panel */}
      {showHistory && (
        <div className="bg-white border-b max-h-60 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-4">
            <h3 className="text-sm font-medium text-gray-500 mb-3">
              历史行程 ({history.length})
            </h3>
            {history.length === 0 ? (
              <p className="text-sm text-gray-400">暂无历史行程</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {history.map((plan) => (
                  <button
                    key={plan.id}
                    onClick={() => {
                      const sid = sessionIdRef.current;
                      router.push(sid ? `/travel/${plan.id}?session=${sid}` : `/travel/${plan.id}`);
                      setShowHistory(false);
                    }}
                    className="text-left p-3 border rounded-lg hover:bg-gray-50 transition"
                  >
                    <p className="font-medium text-sm">{plan.destination}</p>
                    <p className="text-xs text-gray-400">
                      {plan.days}天 · {plan.status}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chat History Panel */}
      {showChatHistory && (
        <div className="bg-white border-b max-h-60 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-4">
            <h3 className="text-sm font-medium text-gray-500 mb-3">
              历史对话 ({chatSessions.length})
            </h3>
            {chatSessions.length === 0 ? (
              <p className="text-sm text-gray-400">暂无历史对话</p>
            ) : (
              <div className="space-y-1">
                {chatSessions.map((session) => (
                  <div
                    key={session.session_id}
                    className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 group"
                  >
                    <button
                      onClick={() => restoreSession(session.session_id)}
                      className="flex-1 text-left min-w-0"
                    >
                      <p className="text-sm font-medium truncate">
                        {session.title || "未命名对话"}
                      </p>
                      <p className="text-xs text-gray-400 truncate">
                        {session.last_preview}
                      </p>
                      <p className="text-xs text-gray-300">
                        {new Date(session.updated_at).toLocaleDateString("zh-CN")}
                        · {session.message_count} 条消息
                      </p>
                    </button>
                    <button
                      onClick={() => deleteSession(session.session_id)}
                      className="text-xs text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition flex-shrink-0"
                    >
                      删除
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <MessageList messages={messages} loading={sending} thinkingText={thinkingText} />

      {/* Current Travel Plan */}
      {currentPlan && currentPlan.itinerary && (
        <div className="max-w-2xl mx-auto w-full px-4 pb-4">
          <TravelPlanCard
            plan={currentPlan}
            onView={(id: number) => router.push(`/travel/${id}?session=${sessionId || sessionIdRef.current || ""}`)}
          />
        </div>
      )}

      {/* Product Search Panel */}
      {showProductSearch && (
        <div className="border-t bg-white max-h-64 overflow-y-auto">
          <div className="max-w-2xl mx-auto w-full px-4 py-3">
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleProductSearch()}
                placeholder="搜索商品..."
                className="flex-1 px-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
                autoFocus
              />
              <button
                onClick={handleProductSearch}
                disabled={searching}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {searching ? "..." : "搜索"}
              </button>
              <button
                onClick={() => { setShowProductSearch(false); setSearchResults([]); setSearchKeyword(""); }}
                className="px-2 py-1.5 text-sm text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {searchResults.map((p) => (
                  <div key={p.id} className="border rounded-lg p-2 flex flex-col gap-1">
                    <p className="text-xs font-medium truncate">{p.name}</p>
                    <p className="text-xs text-red-600 font-bold">¥{p.price}</p>
                    <button
                      onClick={() => handleAddToCart(p.id)}
                      disabled={p.stock < 1}
                      className="text-xs py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-100 disabled:text-gray-400"
                    >
                      {p.stock < 1 ? "缺货" : "加购"}
                    </button>
                  </div>
                ))}
              </div>
            )}
            {searchKeyword && !searching && searchResults.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-2">未找到相关商品</p>
            )}
          </div>
        </div>
      )}

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={sending} />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
        </div>
      }
    >
      <ChatPageContent />
    </Suspense>
  );
}
