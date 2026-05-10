"use client";

import { Suspense, useState, useCallback, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import ThemeToggle from "@/components/UI/ThemeToggle";
import { MessageCircle, Plus, Map, History, Search, LogOut, Package } from "lucide-react";
import MessageList from "@/components/Chat/MessageList";
import ChatInput from "@/components/Chat/ChatInput";
import SuggestionChips from "@/components/Chat/SuggestionChips";
import ChatResultCards from "@/components/Chat/ChatResultCards";
import ProductSearchPanel from "@/components/Chat/ProductSearchPanel";
import HistoryPanels from "@/components/Chat/HistoryPanels";
import ChatSearch from "@/components/Chat/ChatSearch";
import { ApiError, chat as chatApi, commerce as commerceApi, travel as travelApi } from "@/lib/api";
import { setActiveSessionId } from "@/lib/session";
import type {
  Message,
  TravelPlanResponse,
  TravelPlanListItem,
  ChatSession,
  ProductListItem,
  SavedRestaurantRecommendation,
} from "@/lib/types";

function generateId(): string {
  try { return crypto.randomUUID(); } catch { return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`; }
}

function ChatPageContent() {
  const { user, loading, logout } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
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
  const [currentProducts, setCurrentProducts] = useState<ProductListItem[]>([]);
  const [currentRestaurantRec, setCurrentRestaurantRec] = useState<SavedRestaurantRecommendation | null>(null);
  const [currentDietPlan, setCurrentDietPlan] = useState<Record<string, unknown> | null>(null);
  const [currentCartItems, setCurrentCartItems] = useState<Array<Record<string, unknown>>>([]);
  const [confirmingPlan, setConfirmingPlan] = useState(false);
  const [failedMessages, setFailedMessages] = useState<Set<string>>(new Set());
  const [llmStatus, setLlmStatus] = useState<"checking" | "ok" | "error">("checking");
  const lastSentMessageRef = useRef<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const restoredSessionRef = useRef<string | null>(null);
  const searchParams = useSearchParams();

  // Check DeepSeek connectivity on mount
  useEffect(() => {
    fetch("/api/health/llm", { signal: AbortSignal.timeout(8000) })
      .then((r) => r.json())
      .then((d) => setLlmStatus(d.status === "ok" ? "ok" : "error"))
      .catch(() => setLlmStatus("error"));
  }, []);

  // Restore session from URL query param
  useEffect(() => {
    const sid = searchParams.get("session");
    if (!sid || restoredSessionRef.current === sid) return;
    restoredSessionRef.current = sid;
    restoreSession(sid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Clean up SSE on unmount
  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  const handleSend = useCallback(
    (message: string) => {
      const assistantMessageId = generateId();
      const userMsg: Message = { role: "user", content: message };
      const assistantMsg: Message = { id: assistantMessageId, role: "assistant", content: "" };
      let assistantHasContent = false;
      let streamCompleted = false;

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setSending(true);
      lastSentMessageRef.current = message;
      setFailedMessages(new Set());

      const sid = sessionIdRef.current || generateId();
      if (!sessionIdRef.current) setSessionId(sid);
      setActiveSessionId(sid);

      setThinkingText("AI 正在思考...");

      const controller = chatApi.sendStream(
        message,
        {
          onThinking: (text: string) => setThinkingText(text),
          onToken: (token: string) => {
            assistantHasContent = true;
            setThinkingText("");
            setMessages((prev) => {
              return prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: msg.content + token }
                  : msg
              );
            });
          },
          onResult: (text: string) => {
            assistantHasContent = Boolean(text);
            setMessages((prev) => {
              return prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: text }
                  : msg
              );
            });
          },
          onPlan: (plan: Record<string, unknown>) => {
            setCurrentPlan(plan as unknown as TravelPlanResponse);
          },
          onProducts: (products) => setCurrentProducts(products),
          onRestaurants: (recommendation) => setCurrentRestaurantRec(recommendation),
          onDietPlan: (plan) => setCurrentDietPlan(plan),
          onCartItems: (items) => setCurrentCartItems(items),
          onDone: () => {
            streamCompleted = true;
            setSending(false);
            setThinkingText("");
            if (assistantHasContent) {
              setFailedMessages((prev) => {
                const next = new Set(prev);
                next.delete(assistantMessageId);
                return next;
              });
            }
          },
          onError: (err: Error) => {
            if (streamCompleted || assistantHasContent) {
              setSending(false);
              setThinkingText("");
              return;
            }
            toast(err.message, "error");
            setSending(false);
            setThinkingText("");
            setFailedMessages(new Set([assistantMessageId]));
          },
        },
        sid,
        currentPlanRef.current?.id
      );
      abortRef.current = controller;
    },
    [toast]
  );

  const handleRetry = useCallback(() => {
    const lastMsg = lastSentMessageRef.current;
    if (!lastMsg) return;
    // Remove the last user + assistant pair
    setMessages((prev) => {
      const copy = [...prev];
      if (copy.length >= 2) {
        copy.splice(copy.length - 2, 2);
      }
      return copy;
    });
    setFailedMessages(new Set<string>());
    // Re-send immediately
    setTimeout(() => handleSend(lastMsg), 0);
  }, [handleSend]);

  const handleConfirmPlan = async (id: number) => {
    if (confirmingPlan) return;
    setConfirmingPlan(true);
    try {
      const confirmed = await travelApi.confirm(id);
      setCurrentPlan(confirmed);
      toast("最终行程已确认", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "未知错误";
      toast("确认失败: " + msg, "error");
    } finally {
      setConfirmingPlan(false);
    }
  };

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

  const resetConversationState = () => {
    setMessages([]);
    setSessionId(undefined);
    setCurrentPlan(null);
    setCurrentProducts([]);
    setCurrentRestaurantRec(null);
    setCurrentDietPlan(null);
    setCurrentCartItems([]);
  };

  const restoreSession = async (sid: string) => {
    try {
      const detail = await chatApi.getSession(sid);
      setMessages(detail.messages);
      setSessionId(detail.session_id);
      setActiveSessionId(detail.session_id);
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
      const products = detail.context?.current_products as ProductListItem[] | undefined;
      const restaurantRec = detail.context?.current_restaurant_recommendation as SavedRestaurantRecommendation | undefined;
      const dietPlan = detail.context?.current_diet_plan as Record<string, unknown> | undefined;
      const cartItems = detail.context?.current_cart_items as Array<Record<string, unknown>> | undefined;
      setCurrentProducts(products || []);
      setCurrentRestaurantRec(restaurantRec || null);
      setCurrentDietPlan(dietPlan || null);
      setCurrentCartItems(cartItems || []);
      setShowChatHistory(false);
    } catch (err) {
      const staleSession = err instanceof ApiError && [403, 404].includes(err.status);
      if (staleSession) {
        resetConversationState();
        setActiveSessionId(null);
        setShowChatHistory(false);
        router.replace("/chat");
        const marker = `stale_chat_session_notified:${sid}`;
        const alreadyNotified = window.sessionStorage.getItem(marker) === "1";
        if (!alreadyNotified) {
          window.sessionStorage.setItem(marker, "1");
          toast("历史对话不存在，已开启新对话", "info");
        }
        return;
      }
      toast("加载对话失败，请稍后重试", "error");
    }
  };

  const deleteSession = async (sid: string) => {
    try {
      await chatApi.deleteSession(sid);
      setChatSessions((prev) => prev.filter((s) => s.session_id !== sid));
      if (sid === sessionIdRef.current) {
        resetConversationState();
        setActiveSessionId(null);
        router.replace("/chat");
      }
      toast("对话已删除", "info", {
        label: "撤销",
        onClick: async () => {
          // Re-create by restoring: refresh sessions list
          try {
            const sessions = await chatApi.listSessions();
            setChatSessions(sessions);
          } catch { /* ignore */ }
        },
      });
    } catch { toast("删除失败", "error"); }
  };

  const newChat = () => {
    resetConversationState();
    setActiveSessionId(null);
    router.replace("/chat");
  };

  const handleAddToCart = async (productId: number) => {
    try {
      await commerceApi.addCartItem({ product_id: productId, quantity: 1 });
      toast("已加入购物车", "success");
    } catch { toast("加入购物车失败", "error"); }
  };

  // Derived state for SuggestionChips
  const lastAssistantMessage = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].content) return messages[i].content;
    }
    return "";
  })();

  const chipContext = {
    show: !sending && messages.some((m) => m.role === "assistant" && m.content),
    lastResponse: lastAssistantMessage,
    hasTravelPlan: !!currentPlan,
    hasProducts: currentProducts.length > 0,
    hasRestaurants: !!currentRestaurantRec,
    hasDietPlan: !!currentDietPlan,
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
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-border/50 bg-background/80 backdrop-blur-lg supports-[backdrop-filter]:bg-background/60 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-lg bg-gradient-to-r from-fuchsia-500 to-pink-500 bg-clip-text text-transparent">AI 生活推荐</h1>
            <div className="hidden sm:flex items-center gap-1.5 ml-3">
              <button
                onClick={newChat}
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-primary/10 text-primary rounded-full hover:bg-primary/20 transition-colors"
              >
                <Plus className="h-3 w-3" /> 新对话
              </button>
              <button
                onClick={loadHistory}
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-muted text-muted-foreground rounded-full hover:bg-muted/80 transition-colors"
              >
                <Map className="h-3 w-3" /> 历史行程
              </button>
              <button
                onClick={loadChatSessions}
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-muted text-muted-foreground rounded-full hover:bg-muted/80 transition-colors"
              >
                <History className="h-3 w-3" /> 历史对话
              </button>
              <ChatSearch messages={messages} />
              <button
                onClick={() => setShowProductSearch(!showProductSearch)}
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 rounded-full hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors"
              >
                <Package className="h-3 w-3" /> 搜商品
              </button>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <span className="text-sm text-muted-foreground hidden sm:inline">{user.display_name}</span>
            <button
              onClick={() => logout()}
              className="inline-flex items-center gap-1 text-xs px-3 py-1.5 text-destructive hover:bg-destructive/10 rounded-full transition-colors"
            >
              <LogOut className="h-3 w-3" /> 退出
            </button>
          </div>
        </div>
        {/* Mobile action row */}
        <div className="sm:hidden flex items-center gap-1.5 mt-2 overflow-x-auto pb-0.5">
          <button
            onClick={newChat}
            className="shrink-0 inline-flex items-center gap-1 text-xs px-3 py-1.5 bg-primary/10 text-primary rounded-full"
          >
            <Plus className="h-3 w-3" /> 新对话
          </button>
          <button
            onClick={loadHistory}
            className="shrink-0 inline-flex items-center gap-1 text-xs px-3 py-1.5 bg-muted text-muted-foreground rounded-full"
          >
            <Map className="h-3 w-3" /> 行程
          </button>
          <button
            onClick={loadChatSessions}
            className="shrink-0 inline-flex items-center gap-1 text-xs px-3 py-1.5 bg-muted text-muted-foreground rounded-full"
          >
            <History className="h-3 w-3" /> 对话
          </button>
          <button
            onClick={() => setShowProductSearch(!showProductSearch)}
            className="shrink-0 inline-flex items-center gap-1 text-xs px-3 py-1.5 bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400 rounded-full"
          >
            <Package className="h-3 w-3" /> 商品
          </button>
        </div>
      </header>

      {/* History Panels */}
      <HistoryPanels
        showHistory={showHistory}
        history={history}
        showChatHistory={showChatHistory}
        chatSessions={chatSessions}
        sessionId={sessionIdRef.current}
        onViewTravelPlan={(id) => {
          router.push(`/travel/${id}${sessionIdRef.current ? `?session=${sessionIdRef.current}` : ""}`);
          setShowHistory(false);
        }}
        onRestoreSession={restoreSession}
        onDeleteSession={deleteSession}
      />

      {/* Messages */}
      <MessageList
        messages={messages}
        loading={sending}
        thinkingText={thinkingText}
        onRetry={handleRetry}
        failedMessages={failedMessages}
      />

      {/* Result Cards */}
      <ChatResultCards
        currentPlan={currentPlan}
        currentProducts={currentProducts}
        currentRestaurantRec={currentRestaurantRec}
        currentDietPlan={currentDietPlan}
        currentCartItems={currentCartItems}
        sessionId={sessionIdRef.current}
        onConfirmPlan={handleConfirmPlan}
        confirmingPlan={confirmingPlan}
        onAddToCart={handleAddToCart}
      />

      {/* Product Search Panel */}
      {showProductSearch && (
        <ProductSearchPanel onAddToCart={handleAddToCart} />
      )}

      {/* Suggestion Chips */}
      <SuggestionChips
        onSelect={handleSend}
        show={chipContext.show}
        lastResponse={chipContext.lastResponse}
        hasTravelPlan={chipContext.hasTravelPlan}
        hasProducts={chipContext.hasProducts}
        hasRestaurants={chipContext.hasRestaurants}
        hasDietPlan={chipContext.hasDietPlan}
      />

      {/* LLM status indicator */}
      <div className="flex justify-center">
        <span className={`text-[10px] px-2 py-0.5 rounded-full ${
          llmStatus === "ok" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
          llmStatus === "error" ? "bg-destructive/10 text-destructive" :
          "bg-muted text-muted-foreground"
        }`}>
          {llmStatus === "ok" ? "DeepSeek 已连接" : llmStatus === "error" ? "DeepSeek 连接异常" : "检查连接中..."}
        </span>
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={sending || llmStatus === "error"} />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      }
    >
      <ChatPageContent />
    </Suspense>
  );
}
