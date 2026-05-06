"use client";

import { useState, useEffect, useCallback } from "react";
import { commerce as api } from "@/lib/api";
import OrderCard from "@/components/Commerce/OrderCard";
import { useToast } from "@/components/UI/Toast";
import { OrderSkeleton } from "@/components/UI/Skeleton";
import type { OrderListItem, Order } from "@/lib/types";

export default function OrdersView() {
  const { toast } = useToast();
  const [orders, setOrders] = useState<OrderListItem[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(false);

  const loadOrders = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listOrders();
      setOrders(data);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { if (!selectedOrder) loadOrders(); }, [loadOrders, selectedOrder]);

  const handleViewDetail = async (id: number) => {
    try {
      const data = await api.getOrder(id);
      setSelectedOrder(data);
    } catch { toast("加载订单详情失败", "error"); }
  };

  const handleReorder = async (id: number) => {
    try {
      await api.reorder(id);
      toast("已重新加入购物车", "success");
    } catch { toast("复购失败", "error"); }
  };

  const handleCancel = async (id: number) => {
    if (!confirm("确定取消该订单？")) return;
    try {
      await api.cancelOrder(id);
      toast("订单已取消", "success");
      loadOrders();
      setSelectedOrder(null);
    } catch (e: unknown) {
      toast((e instanceof Error ? e.message : "取消失败"), "error");
    }
  };

  if (selectedOrder) {
    return (
      <div>
        <button
          onClick={() => setSelectedOrder(null)}
          className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 mb-4 block"
        >
          ← 返回订单列表
        </button>
        <div className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium">订单 #{selectedOrder.id}</h3>
            <span className={`text-xs font-medium px-2 py-0.5 rounded ${
              selectedOrder.status === "completed" ? "bg-green-100 text-green-700" :
              selectedOrder.status === "paid" ? "bg-blue-100 text-blue-700" :
              selectedOrder.status === "shipped" ? "bg-indigo-100 text-indigo-700" :
              selectedOrder.status === "pending" ? "bg-yellow-100 text-yellow-700" :
              "bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-gray-400"
            }`}>
              {selectedOrder.status === "pending" ? "待付款" :
               selectedOrder.status === "paid" ? "已付款" :
               selectedOrder.status === "shipped" ? "已发货" :
               selectedOrder.status === "completed" ? "已完成" : "已取消"}
            </span>
          </div>

          {/* Status Timeline */}
          {selectedOrder.status !== "cancelled" ? (
            <div className="mb-4 px-1">
              <div className="flex items-center justify-between">
                {[
                  { key: "pending", label: "待付款" },
                  { key: "paid", label: "已付款" },
                  { key: "shipped", label: "已发货" },
                  { key: "completed", label: "已完成" },
                ].map((step, i) => {
                  const statuses = ["pending", "paid", "shipped", "completed"];
                  const currentIdx = statuses.indexOf(selectedOrder.status);
                  const stepIdx = statuses.indexOf(step.key);
                  const isReached = stepIdx <= currentIdx;
                  const isCurrent = step.key === selectedOrder.status;

                  return (
                    <div key={step.key} className="flex-1 flex flex-col items-center relative">
                      {/* Connector line */}
                      {i > 0 && (
                        <div className={`absolute top-3 right-1/2 w-full h-0.5 -z-10 ${
                          isReached ? "bg-blue-500" : "bg-gray-200"
                        }`} />
                      )}
                      {/* Dot */}
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                        isCurrent
                          ? "bg-blue-600 text-white ring-2 ring-blue-200"
                          : isReached
                            ? "bg-blue-500 text-white"
                            : "bg-gray-100 text-gray-400"
                      }`}>
                        {isReached ? "✓" : i + 1}
                      </div>
                      <span className={`text-xs mt-1 ${isReached ? "text-blue-600 font-medium" : "text-gray-400"}`}>
                        {step.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="mb-4 px-1">
              <div className="flex items-center justify-center">
                <div className="flex flex-col items-center">
                  <div className="w-6 h-6 rounded-full bg-red-100 text-red-500 flex items-center justify-center text-xs font-bold">✕</div>
                  <span className="text-xs mt-1 text-red-500 font-medium">已取消</span>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-3">
            {selectedOrder.items.map((item, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <div className="w-12 h-12 bg-gray-50 rounded flex items-center justify-center flex-shrink-0">
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.name} className="w-full h-full object-cover rounded" />
                  ) : (
                    <span>📦</span>
                  )}
                </div>
                <div className="flex-1">
                  <p className="font-medium">{item.name}</p>
                  <p className="text-gray-400 dark:text-gray-500 text-xs">x{item.quantity} ¥{item.price}</p>
                </div>
                <span className="font-medium">¥{(item.price * item.quantity).toFixed(2)}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t dark:border-slate-700 text-sm text-gray-500 dark:text-gray-400 space-y-1">
            {selectedOrder.shipping_address && <p>收货地址: {selectedOrder.shipping_address}</p>}
            {selectedOrder.contact_phone && <p>联系电话: {selectedOrder.contact_phone}</p>}
            {selectedOrder.notes && <p>备注: {selectedOrder.notes}</p>}
          </div>
          <div className="mt-4 pt-4 border-t dark:border-slate-700 flex justify-between items-center">
            <span className="text-sm text-gray-500 dark:text-gray-400">合计</span>
            <span className="text-xl font-bold text-red-600">¥{selectedOrder.total_amount.toFixed(2)}</span>
          </div>
          {selectedOrder.status === "completed" && (
            <button
              onClick={() => handleReorder(selectedOrder.id)}
              className="mt-4 w-full py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              再来一单
            </button>
          )}
          {(selectedOrder.status === "pending" || selectedOrder.status === "paid") && (
            <button
              onClick={() => handleCancel(selectedOrder.id)}
              className="mt-2 w-full py-2 text-sm border border-red-300 text-red-500 rounded-lg hover:bg-red-50"
            >
              取消订单
            </button>
          )}
        </div>
      </div>
    );
  }

  if (loading && orders.length === 0) {
    return <OrderSkeleton />;
  }

  if (orders.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-300 text-5xl mb-4">📋</p>
        <p className="text-gray-400 dark:text-gray-500 text-sm">暂无订单</p>
        <p className="text-gray-300 text-xs mt-1">去购物车下一单吧！</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {orders.map((order) => (
        <OrderCard
          key={order.id}
          order={order}
          onViewDetail={handleViewDetail}
          onReorder={handleReorder}
          onCancel={handleCancel}
        />
      ))}
    </div>
  );
}
