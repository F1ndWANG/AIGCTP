import { request } from "../api-client";
import type { Cart, CartItem, Category, Order, OrderListItem, Product, ProductListItem } from "../types";

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
  addRecommendedCartItem: (data: {
    product_id?: number;
    product_name: string;
    price?: number;
    reason?: string;
    quantity?: number;
    specs?: Record<string, string>;
  }) =>
    request<CartItem>("/commerce/cart/recommended-item", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  generateProductImages: (product_ids: number[]) =>
    request<{ items: Array<{ product_id: number; image_url?: string; generated: boolean; error?: string }> }>(
      "/commerce/products/images/generate",
      {
        method: "POST",
        body: JSON.stringify({ product_ids }),
      }
    ),
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
    return request<OrderListItem[]>(`/commerce/orders${qs.toString() ? `?${qs.toString()}` : ""}`);
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
