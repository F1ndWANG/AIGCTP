"use client";

const STATUS_LABELS: Record<string, string> = {
  pending: "待付款",
  paid: "已付款",
  shipped: "已发货",
  completed: "已完成",
  cancelled: "已取消",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-700",
  paid: "bg-blue-100 text-blue-700",
  shipped: "bg-indigo-100 text-indigo-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-500",
};

interface OrderCardProps {
  order: {
    id: number;
    status: string;
    total_amount: number;
    item_count: number;
    first_item_name: string;
    created_at: string;
  };
  onViewDetail: (id: number) => void;
  onReorder?: (id: number) => void;
  onCancel?: (id: number) => void;
}

export default function OrderCard({ order, onViewDetail, onReorder, onCancel }: OrderCardProps) {
  const color = STATUS_COLORS[order.status] || STATUS_COLORS.pending;
  const label = STATUS_LABELS[order.status] || order.status;
  const date = new Date(order.created_at).toLocaleDateString("zh-CN", {
    year: "numeric", month: "2-digit", day: "2-digit",
  });

  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">#{order.id}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded ${color}`}>{label}</span>
        </div>
        <span className="text-xs text-gray-400">{date}</span>
      </div>
      <p className="text-sm text-gray-700 truncate">
        {order.first_item_name}
        {order.item_count > 1 && <span className="text-gray-400"> 等{order.item_count}件商品</span>}
      </p>
      <div className="mt-2 flex items-center justify-between">
        <span className="text-base font-bold text-red-600">¥{order.total_amount.toFixed(2)}</span>
        <div className="flex gap-2">
          <button
            onClick={() => onViewDetail(order.id)}
            className="px-3 py-1 text-xs border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            查看详情
          </button>
          {onReorder && order.status === "completed" && (
            <button
              onClick={() => onReorder(order.id)}
              className="px-3 py-1 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              再来一单
            </button>
          )}
          {onCancel && (order.status === "pending" || order.status === "paid") && (
            <button
              onClick={() => onCancel(order.id)}
              className="px-3 py-1 text-xs border border-red-300 text-red-500 rounded-lg hover:bg-red-50"
            >
              取消
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
