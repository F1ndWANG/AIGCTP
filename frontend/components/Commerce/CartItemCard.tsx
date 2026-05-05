"use client";

interface CartItemCardProps {
  item: {
    id: number;
    product_name: string;
    product_image: string;
    price: number;
    unit: string;
    quantity: number;
    specs: Record<string, string>;
  };
  onUpdateQuantity: (id: number, quantity: number) => void;
  onRemove: (id: number) => void;
}

export default function CartItemCard({ item, onUpdateQuantity, onRemove }: CartItemCardProps) {
  const subtotal = item.price * item.quantity;

  return (
    <div className="bg-white rounded-lg border p-4 flex items-center gap-4">
      <div className="w-16 h-16 bg-gray-50 rounded-lg flex items-center justify-center flex-shrink-0">
        {item.product_image ? (
          <img src={item.product_image} alt={item.product_name} className="w-full h-full object-cover rounded-lg" />
        ) : (
          <span className="text-2xl">📦</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-gray-900 truncate">{item.product_name}</h4>
        {Object.keys(item.specs).length > 0 && (
          <p className="text-xs text-gray-400 mt-0.5">
            {Object.entries(item.specs).map(([k, v]) => `${k}: ${v}`).join(", ")}
          </p>
        )}
        <p className="text-xs text-gray-400 mt-0.5">¥{item.price}/{item.unit}</p>
        <div className="mt-2 flex items-center gap-3">
          <div className="flex items-center border rounded-lg">
            <button
              onClick={() => item.quantity > 1 && onUpdateQuantity(item.id, item.quantity - 1)}
              className="px-2 py-1 text-sm text-gray-500 hover:text-gray-700"
            >
              −
            </button>
            <span className="px-3 py-1 text-sm font-medium text-gray-900 min-w-[2rem] text-center">
              {item.quantity}
            </span>
            <button
              onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
              className="px-2 py-1 text-sm text-gray-500 hover:text-gray-700"
            >
              +
            </button>
          </div>
          <span className="text-sm font-medium text-red-600">¥{subtotal.toFixed(2)}</span>
        </div>
      </div>
      <button
        onClick={() => onRemove(item.id)}
        className="text-xs text-red-400 hover:text-red-600 flex-shrink-0"
      >
        删除
      </button>
    </div>
  );
}
