import type {
  AuthResponse,
  ChatResponse,
  ChatSession,
  ChatSessionDetail,
  TravelPlanResponse,
  TravelPlanListItem,
  RouteResponse,
  User,
  HealthProfile,
  MealRecord,
  MealSummary,
  DietPlan,
  DietPlanListItem,
  RestaurantRecommendation,
  SavedRestaurantRecommendation,
  ProductListItem,
  Product,
  Category,
  Cart,
  CartItem,
  Order,
  OrderListItem,
  RecommendationFeedback,
} from "./types";

const API_BASE = "/api";

/** Default request timeout in milliseconds */
const REQUEST_TIMEOUT_MS = 30_000;

/** Maximum retry attempts for retryable errors (5xx, network). */
const MAX_RETRIES = 2;

/** Delay between retries (ms). Doubles each attempt. */
const RETRY_BASE_DELAY = 500;

let refreshPromise: Promise<boolean> | null = null;

function formatApiDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return "";
      })
      .filter(Boolean)
      .join("；") || "请求失败";
  }
  if (detail && typeof detail === "object") {
    if ("message" in detail) return String((detail as { message: unknown }).message);
    if ("detail" in detail) return formatApiDetail((detail as { detail: unknown }).detail);
  }
  return "请求失败";
}

// ── Token management (cookie-based, no localStorage) ──────────

/** Check if user is authenticated by calling the /auth/me endpoint. */
export async function checkAuth(): Promise<User | null> {
  try {
    return await fetch(`${API_BASE}/auth/me`, { credentials: "include" }).then((r) =>
      r.ok ? r.json() : null
    );
  } catch {
    return null;
  }
}

/** Attempt to refresh the access token via cookie-based endpoint. Returns true on success. */
async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = doRefreshAccessToken().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

async function doRefreshAccessToken(): Promise<boolean> {
  try {
    const resp = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    return resp.ok;
  } catch {
    return false;
  }
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  code?: string;

  constructor(message: string, status: number, detail: unknown, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
  }

  get isRetryable(): boolean {
    return this.status >= 500;
  }

  get isAuthExpired(): boolean {
    return this.code === "ERR_AUTH_EXPIRED" || this.status === 401;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let lastError: Error | null = null;
  let refreshedAfterAuthError = false;
  const maxAttempts = MAX_RETRIES + 1;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const { signal: _extSignal, ...restOptions } = options;
      const resp = await fetch(`${API_BASE}${path}`, {
        ...restOptions,
        signal: controller.signal,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(options.headers as Record<string, string>),
        },
      });

      if (!resp.ok) {
        let detail: unknown;
        let code: string | undefined;
        try {
          const body = await resp.json();
          detail = body.detail || body.error || resp.statusText;
          code = body.error;
        } catch {
          const text = await resp.text().catch(() => "");
          detail = text ? text.slice(0, 200) : resp.statusText;
        }
        const err = new ApiError(
          formatApiDetail(detail),
          resp.status,
          detail,
          code,
        );
        if (err.isAuthExpired && !refreshedAfterAuthError) {
          refreshedAfterAuthError = true;
          const refreshed = await refreshAccessToken();
          if (refreshed) continue;
        }
        if (err.isRetryable && attempt < MAX_RETRIES) {
          lastError = err;
          const baseDelay = RETRY_BASE_DELAY * Math.pow(2, attempt);
          await sleep(baseDelay * (0.5 + Math.random() * 0.5));
          continue;
        }
        throw err;
      }

      if (resp.status === 204 || resp.headers.get("content-length") === "0") {
        return undefined as T;
      }

      const text = await resp.text();
      if (!text) return undefined as T;
      return JSON.parse(text) as T;
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      if (err instanceof Error && err.name === "AbortError") {
        throw new ApiError("请求超时", 504, "Request timed out");
      }
      if (attempt < MAX_RETRIES) {
        lastError = err instanceof Error ? err : new Error(String(err));
        const baseDelay = RETRY_BASE_DELAY * Math.pow(2, attempt);
        await sleep(baseDelay * (0.5 + Math.random() * 0.5));
        continue;
      }
      throw lastError || new ApiError("Network error", 0, err);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  throw lastError || new Error("Unexpected error");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Auth
export const auth = {
  login: (username: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  register: (username: string, password: string, display_name?: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, display_name }),
    }),
  logout: () =>
    request<{ message: string }>("/auth/logout", { method: "POST" }),
  me: () => request<User>("/auth/me"),
};

// Chat
export const chat = {
  send: (message: string, session_id?: string, travel_plan_id?: number) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id, travel_plan_id }),
    }),

  sendStream: (
    message: string,
    callbacks: {
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
    },
    session_id?: string,
    travel_plan_id?: number,
  ): AbortController => {
    const controller = new AbortController();
    let doneCalled = false;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 3;

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
            if (resp.status === 401 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
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
                  // skip malformed SSE lines
                }
              }
            }
          }

          if (!doneCalled && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            startStream();
            return;
          }
          finish();
        })
        .catch((err) => {
          if (err.name === "AbortError") {
            finish();
          } else {
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              reconnectAttempts++;
              const baseDelay = Math.min(1000 * Math.pow(2, reconnectAttempts), 8000);
              const delay = baseDelay * (0.5 + Math.random() * 0.5);
              setTimeout(startStream, delay);
            } else {
              callbacks.onError(err as Error);
            }
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

// Travel Plans
export const travel = {
  list: () => request<TravelPlanListItem[]>("/travel/plans"),
  get: (id: number) => request<TravelPlanResponse>(`/travel/plans/${id}`),
  confirm: (id: number) =>
    request<TravelPlanResponse>(`/travel/plans/${id}/confirm`, {
      method: "POST",
    }),
  delete: (id: number) =>
    request<{ status: string }>(`/travel/plans/${id}`, {
      method: "DELETE",
    }),
};

// Route
export const route = {
  get: (params: {
    destination_name: string;
    destination_lat?: number;
    destination_lng?: number;
    origin_lat: number;
    origin_lng: number;
    city?: string;
    mode?: string;
  }) =>
    request<RouteResponse>("/route", {
      method: "POST",
      body: JSON.stringify({ ...params, mode: params.mode || "transit" }),
    }),
};

// Diet
export const diet = {
  getProfile: () => request<HealthProfile>("/diet/profile"),
  updateProfile: (data: Partial<HealthProfile>) =>
    request<HealthProfile>("/diet/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  getMeals: (meal_date?: string) =>
    request<MealRecord[]>(
      `/diet/meals${meal_date ? `?meal_date=${meal_date}` : ""}`
    ),
  getMealSummary: (meal_date?: string) =>
    request<MealSummary>(
      `/diet/meals/summary${meal_date ? `?meal_date=${meal_date}` : ""}`
    ),
  createMeal: (data: {
    date: string;
    meal_type: string;
    foods: Array<{ name: string; amount: string }>;
    notes?: string;
  }) =>
    request<MealRecord>("/diet/meals", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteMeal: (id: number) =>
    request<{ status: string }>(`/diet/meals/${id}`, {
      method: "DELETE",
    }),
  getPlans: () => request<DietPlanListItem[]>("/diet/plans"),
  getPlan: (id: number) => request<DietPlan>(`/diet/plans/${id}`),
  confirmPlan: (id: number) =>
    request<DietPlan>(`/diet/plans/${id}/confirm`, {
      method: "POST",
    }),
  deletePlan: (id: number) =>
    request<{ status: string }>(`/diet/plans/${id}`, {
      method: "DELETE",
    }),
};

// Restaurant
export const restaurant = {
  recommend: (city: string, cuisine?: string, session_id?: string) =>
    request<RestaurantRecommendation>("/restaurant/recommend", {
      method: "POST",
      body: JSON.stringify({ city, cuisine, session_id }),
    }),
  nearby: (lat: number, lng: number, radius?: number, session_id?: string) =>
    request<RestaurantRecommendation>("/restaurant/nearby", {
      method: "POST",
      body: JSON.stringify({ lat, lng, radius, session_id }),
    }),
  listRecommendations: (session_id?: string) =>
    request<SavedRestaurantRecommendation[]>(
      `/restaurant/recommendations${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`
    ),
  getRecommendation: (id: number) =>
    request<SavedRestaurantRecommendation>(`/restaurant/recommendations/${id}`),
  selectRecommendation: (id: number, restaurant: Record<string, unknown>) =>
    request<SavedRestaurantRecommendation>(`/restaurant/recommendations/${id}/select`, {
      method: "POST",
      body: JSON.stringify({ restaurant }),
    }),
  deleteRecommendation: (id: number) =>
    request<{ status: string }>(`/restaurant/recommendations/${id}`, {
      method: "DELETE",
    }),
};

// User
export const user = {
  me: () => request<User>("/users/me"),
  updateProfile: (data: { display_name?: string; avatar_url?: string }) =>
    request<User>("/users/me", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  updatePreferences: (preferences: Record<string, unknown>) =>
    request<User>("/users/me/preferences", {
      method: "PUT",
      body: JSON.stringify({ preferences }),
    }),
  changePassword: (old_password: string, new_password: string) =>
    request<{ status: string }>("/users/me/password", {
      method: "PUT",
      body: JSON.stringify({ old_password, new_password }),
    }),
};

// Commerce
export const commerce = {
  listProducts: (params?: {
    category_id?: number;
    keyword?: string;
    min_price?: number;
    max_price?: number;
    tags?: string;
    page?: number;
    page_size?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params) {
      (Object.entries(params) as [string, string | number | undefined][]).forEach(([k, v]) => {
        if (v !== undefined && v !== null) qs.set(k, String(v));
      });
    }
    return request<{ items: ProductListItem[]; total: number }>(
      `/commerce/products${qs.toString() ? `?${qs.toString()}` : ""}`
    );
  },
  getProduct: (id: number) => request<Product>(`/commerce/products/${id}`),
  listCategories: () => request<Category[]>("/commerce/categories"),
  getCart: () => request<Cart>("/commerce/cart"),
  addCartItem: (data: { product_id: number; quantity?: number; specs?: Record<string, string> }) =>
    request<CartItem>("/commerce/cart/items", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateCartItem: (id: number, data: { quantity: number }) =>
    request<CartItem>(`/commerce/cart/items/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  removeCartItem: (id: number) =>
    request<{ status: string }>(`/commerce/cart/items/${id}`, {
      method: "DELETE",
    }),
  clearCart: () =>
    request<{ status: string }>("/commerce/cart", {
      method: "DELETE",
    }),
  listOrders: (params?: { status?: string; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params) {
      (Object.entries(params) as [string, string | number | undefined][]).forEach(([k, v]) => {
        if (v !== undefined && v !== null) qs.set(k, String(v));
      });
    }
    return request<OrderListItem[]>(
      `/commerce/orders${qs.toString() ? `?${qs.toString()}` : ""}`
    );
  },
  getOrder: (id: number) => request<Order>(`/commerce/orders/${id}`),
  createOrder: (data: { shipping_address?: string; contact_phone?: string; notes?: string }) =>
    request<Order>("/commerce/orders", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  reorder: (id: number) =>
    request<Cart>(`/commerce/orders/${id}/reorder`, {
      method: "POST",
    }),
  cancelOrder: (id: number) =>
    request<Order>(`/commerce/orders/${id}/cancel`, {
      method: "POST",
    }),
  updateOrderStatus: (id: number, status: string) =>
    request<Order>(`/commerce/orders/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
};

// Feedback
export const feedback = {
  submit: (data: RecommendationFeedback) =>
    request<{ status: string; id: number }>("/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  stats: () =>
    request<Array<{ content_type: string; likes: number; dislikes: number }>>("/feedback/stats"),
  analytics: {
    summary: () =>
      request<{ total_interactions: number; by_content_type: Record<string, { total: number; likes: number; dislikes: number }> }>(
        "/feedback/analytics/summary"
      ),
  },
};
