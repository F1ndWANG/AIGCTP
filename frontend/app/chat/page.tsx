"use client";

import { Suspense, useState, useCallback, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import ThemeToggle from "@/components/UI/ThemeToggle";
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
  const [failedMessages, setFailedMessages] = useState<Set<number>>(new Set());
  const lastSentMessageRef = useRef<string>("");
  const abortRef = useRef<AbortController | null>(null);
  const restoredSessionRef = useRef<string | null>(null);
  const searchParams = useSearchParams();

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
      const userMsg: Message = { role: "user", content: message };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      lastSentMessageRef.current = message;
      setFailedMessages(new Set());

      const sid = sessionIdRef.current || generateId();
      if (!sessionIdRef.current) setSessionId(sid);
      setActiveSessionId(sid);

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
          onProducts: (products) => setCurrentProducts(products),
          onRestaurants: (recommendation) => setCurrentRestaurantRec(recommendation),
          onDietPlan: (plan) => setCurrentDietPlan(plan),
          onCartItems: (items) => setCurrentCartItems(items),
          onDone: () => { setSending(false); setThinkingText(""); },
          onError: (err: Error) => {
            toast(err.message, "error");
            setSending(false);
            setThinkingText("");
            setFailedMessages(new Set([messagesRef.current.length - 1]));
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
    setFailedMessages(new Set());
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
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b dark:border-slate-700 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="font-bold text-lg text-gray-900 dark:text-gray-100">AI 生活推荐</h1>
            <button
              onClick={newChat}
              className="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-full hover:bg-blue-100 transition"
            >
              + 新对话
            </button>
            <button
              onClick={loadHistory}
              className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-slate-600 transition"
            >
              历史行程
            </button>
            <button
              onClick={loadChatSessions}
              className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-slate-600 transition"
            >
              历史对话
            </button>
            <ChatSearch messages={messages} />
            <button
              onClick={() => setShowProductSearch(!showProductSearch)}
              className="text-xs px-3 py-1.5 bg-orange-50 text-orange-600 rounded-full hover:bg-orange-100 transition"
            >
              搜商品
            </button>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <span className="text-sm text-gray-500 dark:text-gray-400">{user.display_name}</span>
            <button
              onClick={() => logout()}
              className="text-xs px-3 py-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-full transition"
            >
              退出
            </button>
          </div>
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
