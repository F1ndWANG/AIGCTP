"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import CartView from "@/components/Commerce/CartView";
import OrdersView from "@/components/Commerce/OrdersView";
import { chatHref } from "@/lib/session";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/UI/tabs";
import { ArrowLeft } from "lucide-react";
import { motion } from "motion/react";

export default function CartPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"cart" | "orders">("cart");

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="min-h-screen flex items-center justify-center"
      >
        <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
      </motion.div>
    );
  }

  if (!user) {
    router.push("/");
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-background"
    >
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as "cart" | "orders")}
      >
        <div className="max-w-4xl mx-auto w-full px-4 py-6">
          <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
            <button
              onClick={() => router.push(chatHref())}
                className="mb-2 -ml-1 text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
            >
              <ArrowLeft className="w-4 h-4" />
              返回对话
            </button>
              <h1 className="text-2xl font-bold text-foreground">购物</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                购物车和订单会在产生数据后展示。
              </p>
          </div>
            <TabsList variant="line" className="self-start sm:self-auto">
              <TabsTrigger value="cart">购物车</TabsTrigger>
              <TabsTrigger value="orders">订单历史</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="cart">
            <CartView onNavigateChat={() => router.push(chatHref())} />
          </TabsContent>
          <TabsContent value="orders">
            <OrdersView />
          </TabsContent>
        </div>
      </Tabs>
    </motion.div>
  );
}
