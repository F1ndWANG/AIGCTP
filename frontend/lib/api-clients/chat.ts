import { API_BASE, refreshAccessToken, request } from "../api-client";
import type { ChatResponse, ChatSession, ChatSessionDetail, ProductListItem, SavedRestaurantRecommendation } from "../types";

type StreamCallbacks = {
  onToken: (token: string) => void;
  onResult: (text: string) => void;
  onPlan: (plan: Record<string, unknown>) => void;
  onProducts?: (products: ProductListItem[]) => void;
  onRestaurants?: (recommendation: SavedRestaurantRecommendation) => void;
  onDietPlan?: (plan: Record<string, unknown>) => void;
  onCartItems?: (items: Array<Record<string, unknown>>) => void;
  onDone: () => void;
  onError: (err: Error) => void;
  onThinking?: (text: string) => void;
};

export const chat = {
  send: (message: string, session_id?: string, travel_plan_id?: number) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id, travel_plan_id }),
    }),

  sendStream: (
    message: string,
    callbacks: StreamCallbacks,
    session_id?: string,
    travel_plan_id?: number,
  ): AbortController => {
    const controller = new AbortController();
    let doneCalled = false;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 3;

    const finish = () => {
      if (!doneCalled) {
        doneCalled = true;
        callbacks.onDone();
      }
    };

    const startStream = () => {
      fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message, session_id, travel_plan_id }),
        signal: controller.signal,
      })
        .then(async (resp) => {
          if (!resp.ok) {
            const errBody = await resp.json().catch(() => ({ detail: resp.statusText }));
            if (resp.status === 401 && reconnectAttempts < maxReconnectAttempts) {
              const refreshed = await refreshAccessToken();
              if (refreshed) {
                reconnectAttempts++;
                const baseDelay = Math.min(1000 * Math.pow(2, reconnectAttempts), 8000);
                const delay = baseDelay * (0.5 + Math.random() * 0.5);
                setTimeout(startStream, delay);
                return;
              }
            }
            throw new Error(errBody.detail || "Request failed");
          }

          const reader = resp.body?.getReader();
          if (!reader) throw new Error("Response body is not readable");

          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.slice(6));
                  switch (data.type) {
                    case "token":
                      callbacks.onToken(data.content);
                      break;
                    case "result":
                      callbacks.onResult(data.content);
                      break;
                    case "plan":
                      callbacks.onPlan(data.content);
                      break;
                    case "products":
                      callbacks.onProducts?.(data.content);
                      break;
                    case "restaurants":
                      callbacks.onRestaurants?.(data.content);
                      break;
                    case "diet_plan":
                      callbacks.onDietPlan?.(data.content);
                      break;
                    case "cart_items":
                      callbacks.onCartItems?.(data.content);
                      break;
                    case "done":
                      finish();
                      break;
                    case "error":
                      callbacks.onError(new Error(data.content));
                      finish();
                      break;
                    case "thinking":
                      callbacks.onThinking?.(data.content);
                      break;
                  }
                } catch {
                  // Skip malformed SSE lines.
                }
              }
            }
          }

          if (!doneCalled && reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            startStream();
            return;
          }
          finish();
        })
        .catch((err) => {
          if (err.name === "AbortError") {
            finish();
          } else if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            const baseDelay = Math.min(1000 * Math.pow(2, reconnectAttempts), 8000);
            const delay = baseDelay * (0.5 + Math.random() * 0.5);
            setTimeout(startStream, delay);
          } else {
            callbacks.onError(err as Error);
          }
        });
    };

    startStream();
    return controller;
  },

  listSessions: () => request<ChatSession[]>("/chat/sessions"),
  getSession: (session_id: string) => request<ChatSessionDetail>(`/chat/sessions/${session_id}`),
  deleteSession: (session_id: string) =>
    request<{ status: string }>(`/chat/sessions/${session_id}`, {
      method: "DELETE",
    }),
};
