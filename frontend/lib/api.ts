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

let token: string | null = null;

export function setToken(t: string | null) {
  token = t;
  if (t) localStorage.setItem("auth_token", t);
  else localStorage.removeItem("auth_token");
}

export function getToken(): string | null {
  if (!token) token = localStorage.getItem("auth_token");
  return token;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const t = getToken();
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const resp = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...options,
    headers,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return resp.json();
}

// Auth
export const auth = {
  register: (username: string, password: string, display_name?: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, display_name }),
    }),
  login: (username: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
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
      onDone: () => void;
      onError: (err: Error) => void;
      onThinking?: (text: string) => void;
    },
    session_id?: string,
    travel_plan_id?: number,
  ): AbortController => {
    const controller = new AbortController();

    fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify({ message, session_id, travel_plan_id }),
      signal: controller.signal,
    })
      .then(async (resp) => {
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ detail: resp.statusText }));
          throw new Error(err.detail || "Request failed");
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
                  case "done":
                    callbacks.onDone();
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
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          callbacks.onError(err);
        }
      });

    return controller;
  },

  listSessions: () => request<ChatSession[]>("/chat/sessions"),
  getSession: (session_id: string) => request<ChatSessionDetail>(`/chat/sessions/${session_id}`),
  deleteSession: (session_id: string) =>
    fetch(`${API_BASE}/chat/sessions/${session_id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    }),
};

// Travel Plans
export const travel = {
  list: () => request<TravelPlanListItem[]>("/travel/plans"),
  get: (id: number) => request<TravelPlanResponse>(`/travel/plans/${id}`),
  delete: (id: number) =>
    fetch(`${API_BASE}/travel/plans/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
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
    fetch(`${API_BASE}/diet/meals/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    }),
  getPlans: () => request<DietPlanListItem[]>("/diet/plans"),
  getPlan: (id: number) => request<DietPlan>(`/diet/plans/${id}`),
  confirmPlan: (id: number) =>
    request<DietPlan>(`/diet/plans/${id}/confirm`, {
      method: "POST",
    }),
  deletePlan: (id: number) =>
    fetch(`${API_BASE}/diet/plans/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    }),
};

// Restaurant
export const restaurant = {
  recommend: (city: string, cuisine?: string) =>
    request<RestaurantRecommendation>("/restaurant/recommend", {
      method: "POST",
      body: JSON.stringify({ city, cuisine }),
    }),
  nearby: (lat: number, lng: number, radius?: number) =>
    request<RestaurantRecommendation>("/restaurant/nearby", {
      method: "POST",
      body: JSON.stringify({ lat, lng, radius }),
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
    fetch(`${API_BASE}/users/me/password`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getToken()}`,
      },
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
    fetch(`${API_BASE}/commerce/cart/items/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    }),
  clearCart: () =>
    fetch(`${API_BASE}/commerce/cart`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
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
