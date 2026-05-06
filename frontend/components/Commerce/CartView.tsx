"use client";

import { useState, useEffect, useCallback } from "react";
import { commerce as api } from "@/lib/api";
import CartItemCard from "@/components/Commerce/CartItemCard";
import { useToast } from "@/components/UI/Toast";
import { CartSkeleton } from "@/components/UI/Skeleton";
import type { Cart } from "@/lib/types";

interface CartViewProps {
  onNavigateChat: () => void;
}

export default function CartView({ onNavigateChat }: CartViewProps) {
  const { toast } = useToast();
  const [cart, setCart] = useState<Cart | null>(null);
  const [cartLoading, setCartLoading] = useState(false);
  const [cartError, setCartError] = useState<string | null>(null);
  const [showCheckout, setShowCheckout] = useState(false);
  const [shippingAddress, setShippingAddress] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [orderNote, setOrderNote] = useState("");

  const loadCart = useCallback(async () => {
    setCartLoading(true);
    try {
      const data = await api.getCart();
      setCart(data);
      setCartError(null);
    } catch { setCartError("加载购物车失败，请重试"); }
    setCartLoading(false);
  }, []);

  useEffect(() => { loadCart(); }, [loadCart]);

  const handleRemoveItem = async (itemId: number) => {
    try {
      await api.removeCartItem(itemId);
      toast("已移除", "success");
      loadCart();
    } catch { toast("移除失败", "error"); }
  };

  const handleUpdateQuantity = async (itemId: number, qty: number) => {
    try {
      await api.updateCartItem(itemId, { quantity: qty });
      loadCart();
    } catch { toast("更新失败", "error"); }
  };

  const handleClearCart = async () => {
    if (!confirm("确定清空购物车？")) return;
    try {
      await api.clearCart();
      toast("已清空", "success");
      loadCart();
    } catch { toast("清空失败", "error"); }
  };

  const handleCheckout = async () => {
    if (!shippingAddress.trim()) {
      toast("请填写收货地址", "error");
      return;
    }
    try {
      await api.createOrder({
        shipping_address: shippingAddress,
        contact_phone: contactPhone,
        notes: orderNote,
      });
      toast("下单成功！", "success");
      setShowCheckout(false);
      setShippingAddress("");
      setContactPhone("");
      setOrderNote("");
      loadCart();
    } catch { toast("下单失败，请重试", "error"); }
  };

  if (cartError && !cartLoading) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-300 text-5xl mb-4">⚠️</p>
        <p className="text-gray-400 dark:text-gray-500 text-sm mb-2">{cartError}</p>
        <button
          onClick={() => { setCartError(null); loadCart(); }}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          重试
        </button>
      </div>
    );
  }

  if (cartLoading && !cart) {
    return <CartSkeleton />;
  }

  const items = cart?.items || [];

  if (items.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-300 text-5xl mb-4">🛒</p>
        <p className="text-gray-400 dark:text-gray-500 text-sm">购物车是空的</p>
        <p className="text-gray-300 text-xs mt-1">去聊天窗口让 AI 帮你推荐商品吧！</p>
        <button
          onClick={onNavigateChat}
          className="mt-4 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          去 AI 对话
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">共 {items.length} 件商品</p>
        <button onClick={handleClearCart} className="text-xs text-red-400 hover:text-red-600">
          清空购物车
        </button>
      </div>

      <div className="space-y-3">
        {items.map((item) => (
          <CartItemCard
            key={item.id}
            item={item}
            onUpdateQuantity={handleUpdateQuantity}
            onRemove={handleRemoveItem}
          />
        ))}
      </div>

      {/* Total & Checkout */}
      <div className="mt-6 bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-500 dark:text-gray-400">合计</span>
          <span className="text-xl font-bold text-red-600">¥{cart?.total_amount.toFixed(2)}</span>
        </div>

        {!showCheckout ? (
          <button
            onClick={() => setShowCheckout(true)}
            className="w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
          >
            去结算
          </button>
        ) : (
          <div className="space-y-3 pt-3 border-t">
            <input
              type="text"
              placeholder="收货地址"
              value={shippingAddress}
              onChange={(e) => setShippingAddress(e.target.value)}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
            <input
              type="text"
              placeholder="联系电话（选填）"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
            <textarea
              placeholder="备注（选填）"
              value={orderNote}
              onChange={(e) => setOrderNote(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowCheckout(false)}
                className="flex-1 py-2 text-sm border border-gray-300 dark:border-slate-700 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                取消
              </button>
              <button
                onClick={handleCheckout}
                className="flex-1 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                提交订单
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
