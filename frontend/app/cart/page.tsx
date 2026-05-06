"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import CartView from "@/components/Commerce/CartView";
import OrdersView from "@/components/Commerce/OrdersView";
import { chatHref } from "@/lib/session";

type Tab = "cart" | "orders";

export default function CartPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"cart" | "orders">("cart");

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
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 border-b dark:border-slate-700">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.push(chatHref())} className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
            ← 返回对话
          </button>
          <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">购物</h1>
        </div>

        {/* Tabs */}
        <div className="max-w-4xl mx-auto flex px-4">
          {([{ key: "cart" as const, label: "购物车" }, { key: "orders" as const, label: "订单历史" }]).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab.key
                  ? "text-blue-600 border-blue-600"
                  : "text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        {activeTab === "cart" && <CartView onNavigateChat={() => router.push(chatHref())} />}
        {activeTab === "orders" && <OrdersView />}
      </div>
    </div>
  );
}
