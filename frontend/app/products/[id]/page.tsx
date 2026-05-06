"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { commerce as api } from "@/lib/api";
import { withSession } from "@/lib/session";
import type { Product } from "@/lib/types";

export default function ProductDetailPage() {
  const { user, loading: authLoading } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const params = useParams();
  const productId = Number(params.id);

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [selectedImage, setSelectedImage] = useState(0);
  const [selectedSpecs, setSelectedSpecs] = useState<Record<string, string>>({});
  const [quantity, setQuantity] = useState(1);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (!productId || authLoading) return;
    setLoading(true);
    api.getProduct(productId)
      .then((p) => {
        setProduct(p);
        // Initialize specs with first option
        const initSpecs: Record<string, string> = {};
        p.specs?.forEach((s) => {
          if (s.options?.length > 0) initSpecs[s.name] = s.options[0];
        });
        setSelectedSpecs(initSpecs);
      })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [productId, authLoading]);

  const handleAddToCart = async () => {
    if (!product) return;
    setAdding(true);
    try {
      await api.addCartItem({
        product_id: product.id,
        quantity,
        specs: selectedSpecs,
      });
      toast("已加入购物车", "success");
    } catch { toast("加入购物车失败", "error"); }
    setAdding(false);
  };

  if (authLoading) {
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
        <div className="max-w-4xl mx-auto px-4 py-6 animate-pulse space-y-4">
          <div className="h-4 bg-gray-100 rounded w-24" />
          <div className="aspect-square max-w-md bg-gray-100 rounded-lg" />
          <div className="h-8 bg-gray-100 rounded w-3/4" />
          <div className="h-6 bg-gray-100 rounded w-1/4" />
          <div className="h-20 bg-gray-100 rounded" />
        </div>
      </div>
    );
  }

  if (notFound || !product) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-300 text-5xl mb-4">🔍</p>
          <p className="text-gray-400 dark:text-gray-500 text-sm mb-4">商品不存在或已下架</p>
          <button
            onClick={() => router.push(withSession("/products"))}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            返回商品列表
          </button>
        </div>
      </div>
    );
  }

  const outOfStock = product.stock < 1;
  const hasDiscount = product.original_price && product.original_price > product.price;
  const images = product.image_urls?.length > 0 ? product.image_urls : [""];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Back */}
        <button
          onClick={() => router.push(withSession("/products"))}
          className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 mb-4 block"
        >
          ← 返回商品列表
        </button>

        <div className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 overflow-hidden">
          {/* Image gallery */}
          <div className="md:flex">
            <div className="md:w-1/2 p-4">
              <div className="aspect-square bg-gray-50 dark:bg-slate-900 rounded-lg flex items-center justify-center mb-3">
                {images[0] ? (
                  <img src={images[selectedImage]} alt={product.name} className="w-full h-full object-cover rounded-lg" />
                ) : (
                  <span className="text-gray-300 text-6xl">📦</span>
                )}
              </div>
              {images.length > 1 && (
                <div className="flex gap-2 overflow-x-auto">
                  {images.map((img, i) => (
                    <button
                      key={i}
                      onClick={() => setSelectedImage(i)}
                      className={`w-16 h-16 rounded border-2 flex-shrink-0 overflow-hidden ${
                        selectedImage === i ? "border-blue-500" : "border-transparent"
                      }`}
                    >
                      {img ? (
                        <img src={img} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full bg-gray-100" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Product info */}
            <div className="md:w-1/2 p-6 space-y-4">
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">{product.name}</h1>

              {/* Price */}
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-red-600">¥{product.price}</span>
                {hasDiscount && (
                  <span className="text-lg text-gray-400 dark:text-gray-500 line-through">¥{product.original_price}</span>
                )}
                <span className="text-sm text-gray-400">/{product.unit}</span>
              </div>

              {/* Rating */}
              {product.rating > 0 && (
                <div className="flex items-center gap-1">
                  <span className="text-yellow-400">{'★'.repeat(Math.round(product.rating))}</span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{product.rating} 分</span>
                </div>
              )}

              {/* Tags */}
              {product.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {product.tags.map((tag, i) => (
                    <span key={i} className="text-xs bg-blue-50 text-blue-500 px-2 py-0.5 rounded">{tag}</span>
                  ))}
                </div>
              )}

              {/* Stock */}
              <p className={`text-sm ${outOfStock ? "text-red-500" : "text-gray-500 dark:text-gray-400"}`}>
                {outOfStock ? "暂时缺货" : `库存: ${product.stock} ${product.unit}`}
              </p>

              {/* Specs */}
              {product.specs?.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">规格选择</p>
                  {product.specs.map((spec) => (
                    <div key={spec.name}>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{spec.name}</p>
                      <div className="flex flex-wrap gap-2">
                        {spec.options.map((opt) => {
                          const isSelected = selectedSpecs[spec.name] === opt;
                          return (
                            <button
                              key={opt}
                              onClick={() => setSelectedSpecs((prev) => ({ ...prev, [spec.name]: opt }))}
                              className={`px-3 py-1 text-xs rounded-lg border transition ${
                                isSelected
                                  ? "border-blue-500 bg-blue-50 text-blue-600"
                                  : "border-gray-200 text-gray-600 hover:border-gray-400"
                              }`}
                            >
                              {opt}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Quantity */}
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-700 dark:text-gray-300">数量</span>
                <div className="flex items-center border dark:border-slate-700 rounded-lg">
                  <button
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                    className="px-3 py-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700"
                  >
                    −
                  </button>
                  <span className="px-4 py-1.5 text-sm min-w-[3rem] text-center border-x dark:border-slate-700">{quantity}</span>
                  <button
                    onClick={() => setQuantity((q) => Math.min(product.stock, q + 1))}
                    disabled={quantity >= product.stock}
                    className="px-3 py-1.5 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-30"
                  >
                    +
                  </button>
                </div>
              </div>

              {/* Add to cart */}
              <button
                onClick={handleAddToCart}
                disabled={outOfStock || adding}
                className={`w-full py-3 text-sm font-medium rounded-lg transition ${
                  outOfStock
                    ? "bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
              >
                {adding ? "添加中..." : outOfStock ? "暂时缺货" : "加入购物车"}
              </button>
            </div>
          </div>

          {/* Description */}
          {product.description && (
            <div className="border-t dark:border-slate-700 px-6 py-4">
              <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">商品描述</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 whitespace-pre-wrap">{product.description}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
