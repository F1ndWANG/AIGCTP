"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { commerce as api } from "@/lib/api";
import { chatHref, withSession } from "@/lib/session";
import ProductCard from "@/components/Commerce/ProductCard";
import type { Category, ProductListItem } from "@/lib/types";

export default function ProductsPage() {
  const { user, loading: authLoading } = useAuth();
  const { toast } = useToast();
  const router = useRouter();

  // Filters
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [keyword, setKeyword] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  // Products
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Load categories once
  useEffect(() => {
    api.listCategories().then(setCategories).catch(() => {});
  }, []);

  // Load products
  const loadProducts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listProducts({
        ...(selectedCategory ? { category_id: selectedCategory } : {}),
        ...(keyword ? { keyword } : {}),
        ...(minPrice ? { min_price: Number(minPrice) } : {}),
        ...(maxPrice ? { max_price: Number(maxPrice) } : {}),
        page,
        page_size: pageSize,
      });
      setProducts(data.items);
      setTotal(data.total);
    } catch { toast("加载商品失败", "error"); }
    setLoading(false);
  }, [selectedCategory, keyword, minPrice, maxPrice, page, toast]);

  useEffect(() => { loadProducts(); }, [loadProducts]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setKeyword(searchInput);
    setPage(1);
  };

  const handleCategoryChange = (id: number | null) => {
    setSelectedCategory(id);
    setPage(1);
  };

  const handleAddToCart = async (productId: number) => {
    try {
      await api.addCartItem({ product_id: productId, quantity: 1 });
      toast("已加入购物车", "success");
    } catch { toast("加入购物车失败", "error"); }
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

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 border-b dark:border-slate-700">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.push(chatHref())} className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
            ← 返回对话
          </button>
          <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">商品列表</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {/* Search bar */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="搜索商品名称或标签..."
            className="flex-1 px-4 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
          />
          <button
            type="submit"
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            搜索
          </button>
          {(keyword || minPrice || maxPrice) && (
            <button
              type="button"
              onClick={() => {
                setKeyword("");
                setSearchInput("");
                setMinPrice("");
                setMaxPrice("");
                setPage(1);
              }}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-700 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
            >
              清除
            </button>
          )}
        </form>

        {/* Price filter */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500 dark:text-gray-400">价格：</span>
          <input
            type="number"
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
            placeholder="最低"
            className="w-24 px-2 py-1.5 border rounded-lg focus:outline-none focus:border-blue-400"
            min="0"
          />
          <span className="text-gray-400 dark:text-gray-500">—</span>
          <input
            type="number"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            placeholder="最高"
            className="w-24 px-2 py-1.5 border rounded-lg focus:outline-none focus:border-blue-400"
            min="0"
          />
          <button
            onClick={() => { setPage(1); loadProducts(); }}
            className="px-3 py-1.5 text-xs bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600"
          >
            筛选
          </button>
        </div>

        {/* Category tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => handleCategoryChange(null)}
            className={`px-3 py-1.5 text-xs rounded-full whitespace-nowrap transition ${
              selectedCategory === null
                ? "bg-blue-600 text-white"
                : "bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600"
            }`}
          >
            全部
          </button>
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => handleCategoryChange(cat.id)}
              className={`px-3 py-1.5 text-xs rounded-full whitespace-nowrap transition ${
                selectedCategory === cat.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-600"
              }`}
            >
              {cat.icon} {cat.name}
            </button>
          ))}
        </div>

        {/* Product grid */}
        <div className="relative">
          {loading && products.length > 0 && (
            <div className="absolute inset-0 bg-white/60 dark:bg-slate-900/60 flex items-center justify-center z-10 rounded-lg">
              <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
            </div>
          )}
          {loading && products.length === 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 overflow-hidden animate-pulse">
                  <div className="aspect-square bg-gray-100 dark:bg-slate-700" />
                  <div className="p-3 space-y-2">
                    <div className="h-4 bg-gray-100 dark:bg-slate-700 rounded w-3/4" />
                    <div className="h-5 bg-gray-100 dark:bg-slate-700 rounded w-1/2" />
                    <div className="h-8 bg-gray-100 dark:bg-slate-700 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : products.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-300 text-5xl mb-4">📦</p>
            <p className="text-gray-400 dark:text-gray-500 text-sm">
              {keyword || minPrice || maxPrice ? "没有找到符合条件的商品" : "暂无商品，可在 AI 对话中让助手推荐行程物品或生活好物"}
            </p>
            {(keyword || minPrice || maxPrice) && (
              <button
                onClick={() => {
                  setKeyword("");
                  setSearchInput("");
                  setMinPrice("");
                  setMaxPrice("");
                  setPage(1);
                }}
                className="mt-3 px-4 py-2 text-sm border border-gray-300 dark:border-slate-700 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                清除筛选条件
              </button>
            )}
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-400 dark:text-gray-500">共 {total} 件商品</p>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {products.map((product) => (
                <div
                  key={product.id}
                  className="cursor-pointer"
                  onClick={() => router.push(withSession(`/products/${product.id}`))}
                >
                  <ProductCard
                    product={product}
                    onAddToCart={(_, e) => {
                      e.stopPropagation();
                      handleAddToCart(product.id);
                    }}
                  />
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-4">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-sm border dark:border-slate-700 rounded-lg disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  上一页
                </button>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 text-sm border dark:border-slate-700 rounded-lg disabled:opacity-30 hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  下一页
                </button>
              </div>
            )}
          </>
        )}
        </div>
      </div>
    </div>
  );
}
