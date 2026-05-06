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

export default function ProductCard({ product, onAddToCart }: ProductCardProps) {
  const imgSrc = product.image_urls?.[0];
  const hasDiscount = product.original_price && product.original_price > product.price;
  const outOfStock = product.stock < 1;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 hover:shadow-md transition overflow-hidden">
      <div className="aspect-square bg-gray-50 dark:bg-slate-900 flex items-center justify-center">
        {imgSrc ? (
          <img src={imgSrc} alt={product.name} className="w-full h-full object-cover" />
        ) : (
          <span className="text-gray-300 text-4xl">📦</span>
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
