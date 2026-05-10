"use client";

interface ProductCardProps {
  product: {
    id: number;
    name: string;
    price: number;
    original_price?: number;
    image_urls: string[];
    stock: number;
    unit: string;
    rating: number;
    tags?: string[];
  };
  onAddToCart?: (productId: number, e: React.MouseEvent) => void;
}

const PRODUCT_IMAGE_FALLBACKS: Record<string, string> = {
  "轻量折叠双肩包": "/product-images/foldable-backpack.svg",
  "便携防晒霜 SPF50+": "/product-images/sunscreen.svg",
  "真空压缩收纳袋套装": "/product-images/compression-bags.svg",
  "便携保温水杯 500ml": "/product-images/thermal-bottle.svg",
  "城市明信片纪念套装": "/product-images/postcards.svg",
  "地方糕点伴手礼盒": "/product-images/pastry-gift-box.svg",
  "龙井茶叶便携装": "/product-images/longjing-tea.svg",
  "每日坚果能量包": "/product-images/nut-pack.svg",
  "高蛋白燕麦杯": "/product-images/oat-cup.svg",
  "低脂鸡胸肉即食装": "/product-images/chicken-meal.svg",
  "蓝牙降噪耳机": "/product-images/noise-cancelling-headphones.svg",
  "桌面小风扇充电式": "/product-images/desk-fan.svg",
};

export default function ProductCard({ product, onAddToCart }: ProductCardProps) {
  const imgSrc = product.image_urls?.[0] || PRODUCT_IMAGE_FALLBACKS[product.name];
  const hasDiscount = product.original_price && product.original_price > product.price;
  const outOfStock = product.stock < 1;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 hover:shadow-md transition overflow-hidden">
      <div className="aspect-square bg-gray-50 dark:bg-slate-900 flex items-center justify-center overflow-hidden">
        {imgSrc ? (
          <img src={imgSrc} alt={product.name} className="w-full h-full object-cover" />
        ) : (
          <div className="h-full w-full bg-[linear-gradient(135deg,#f8fafc,#fdf2f8)]" />
        )}
      </div>
      <div className="p-3">
        <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{product.name}</h3>
        <div className="mt-1 flex items-center gap-2">
          <span className="text-base font-bold text-red-600">¥{product.price}</span>
          {hasDiscount && (
            <span className="text-xs text-gray-400 dark:text-gray-500 line-through">¥{product.original_price}</span>
          )}
          <span className="text-xs text-gray-400 dark:text-gray-500">/{product.unit}</span>
        </div>
        {product.rating > 0 && (
          <div className="mt-1 flex items-center gap-1">
            <span className="text-yellow-400 text-xs">{'★'.repeat(Math.round(product.rating))}</span>
            <span className="text-xs text-gray-400 dark:text-gray-500">{product.rating}</span>
          </div>
        )}
        {product.tags && product.tags.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {product.tags.slice(0, 3).map((tag, i) => (
              <span key={i} className="text-xs bg-blue-50 text-blue-500 px-1 py-0.5 rounded">{tag}</span>
            ))}
          </div>
        )}
        <button
          onClick={(e) => onAddToCart?.(product.id, e)}
          disabled={outOfStock}
          className={`mt-2 w-full py-1.5 text-xs rounded-lg transition ${
            outOfStock
              ? "bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-gray-500 cursor-not-allowed"
              : "bg-blue-600 text-white hover:bg-blue-700"
          }`}
        >
          {outOfStock ? "暂时缺货" : "加入购物车"}
        </button>
      </div>
    </div>
  );
}
