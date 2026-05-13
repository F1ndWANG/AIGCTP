"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { commerce as api } from "@/lib/api";
import { chatHref, withSession } from "@/lib/session";
import { useRecommendationTracking } from "@/lib/useRecommendationTracking";
import ProductCard from "@/components/Commerce/ProductCard";
import { Card, CardContent } from "@/components/UI/card";
import { Badge } from "@/components/UI/badge";
import { Button } from "@/components/UI/button";
import { Input } from "@/components/UI/input";
import { Skeleton } from "@/components/UI/Skeleton";
import { ArrowLeft, Package, Search, X } from "lucide-react";
import { motion } from "motion/react";
import type { Category, ProductListItem } from "@/lib/types";

export default function ProductsPage() {
  const { user, loading: authLoading } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const { track } = useRecommendationTracking("products_page");

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
  const [requestedImageIds, setRequestedImageIds] = useState<Set<number>>(new Set());
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
      const missingGeneratedImages = data.items
        .filter((product) => !product.image_urls?.some((url) => url.startsWith("/generated-products/")))
        .map((product) => product.id)
        .filter((id) => !requestedImageIds.has(id));
      if (missingGeneratedImages.length > 0) {
        setRequestedImageIds((prev) => new Set([...prev, ...missingGeneratedImages]));
        api.generateProductImages(missingGeneratedImages)
          .then((result) => {
            const imageByProductId = new Map(
              result.items
                .filter((item) => item.image_url)
                .map((item) => [item.product_id, item.image_url as string])
            );
            if (imageByProductId.size === 0) return;
            setProducts((prev) => prev.map((product) => {
              const imageUrl = imageByProductId.get(product.id);
              if (!imageUrl) return product;
              const existing = (product.image_urls || []).filter((url) => url !== imageUrl);
              return { ...product, image_urls: [imageUrl, ...existing] };
            }));
          })
          .catch(() => {});
      }
    } catch { toast("加载商品失败", "error"); }
    setLoading(false);
  }, [selectedCategory, keyword, minPrice, maxPrice, page, requestedImageIds, toast]);

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
      track({
        domain: "commerce",
        item_type: "product",
        item_id: productId,
        event_type: "add_cart",
      });
      toast("已加入购物车", "success");
    } catch { toast("加入购物车失败", "error"); }
  };

  const openProduct = (product: ProductListItem) => {
    track({
      domain: "commerce",
      item_type: "product",
      item_id: product.id,
      event_type: "click",
      context: { name: product.name },
    });
    router.push(withSession(`/products/${product.id}`));
  };

  if (authLoading) {
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

  const totalPages = Math.ceil(total / pageSize);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-background"
    >
      {/* Header */}
      <div className="bg-card border-b border-border">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => router.push(chatHref())}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
          >
            <ArrowLeft className="w-4 h-4" />
            返回对话
          </button>
          <h1 className="text-lg font-bold text-foreground">商品列表</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        {/* Search bar */}
        <Card>
          <CardContent className="pt-4 space-y-4">
            <form onSubmit={handleSearch} className="flex gap-2">
              <Input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="搜索商品名称或标签..."
                className="flex-1"
              />
              <Button type="submit" size="sm" className="gap-1">
                <Search className="w-3.5 h-3.5" />
                搜索
              </Button>
              {(keyword || minPrice || maxPrice) && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setKeyword("");
                    setSearchInput("");
                    setMinPrice("");
                    setMaxPrice("");
                    setPage(1);
                  }}
                  className="gap-1"
                >
                  <X className="w-3.5 h-3.5" />
                  清除
                </Button>
              )}
            </form>

            {/* Price filter */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">价格：</span>
              <Input
                type="number"
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
                placeholder="最低"
                className="w-24"
                min="0"
              />
              <span className="text-muted-foreground">—</span>
              <Input
                type="number"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                placeholder="最高"
                className="w-24"
                min="0"
              />
              <Button
                variant="secondary"
                size="sm"
                onClick={() => { setPage(1); loadProducts(); }}
              >
                筛选
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Category pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Badge
            variant={selectedCategory === null ? "default" : "outline"}
            className={`cursor-pointer whitespace-nowrap ${
              selectedCategory === null
                ? "bg-fuchsia-600 hover:bg-fuchsia-700"
                : "hover:bg-muted"
            }`}
            onClick={() => handleCategoryChange(null)}
          >
            全部
          </Badge>
          {categories.map((cat) => (
            <Badge
              key={cat.id}
              variant={selectedCategory === cat.id ? "default" : "outline"}
              className={`cursor-pointer whitespace-nowrap flex items-center gap-1 ${
                selectedCategory === cat.id
                  ? "bg-fuchsia-600 hover:bg-fuchsia-700"
                  : "hover:bg-muted"
              }`}
              onClick={() => handleCategoryChange(cat.id)}
            >
              {cat.icon && <span>{cat.icon}</span>}
              {cat.name}
            </Badge>
          ))}
        </div>

        {/* Product grid */}
        <div className="relative">
          {loading && products.length > 0 && (
            <div className="absolute inset-0 bg-background/60 flex items-center justify-center z-10 rounded-lg">
              <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
            </div>
          )}
          {loading && products.length === 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Card key={i} className="overflow-hidden">
                  <Skeleton className="aspect-square rounded-none" />
                  <CardContent className="p-3 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-5 w-1/2" />
                    <Skeleton className="h-8 w-full" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : products.length === 0 ? (
            <div className="text-center py-16">
              <Package className="w-12 h-12 mx-auto text-muted-foreground/40 mb-4" />
              <p className="text-muted-foreground text-sm">
                {keyword || minPrice || maxPrice ? "没有找到符合条件的商品" : "暂无商品，可在 AI 对话中让助手推荐行程物品或生活好物"}
              </p>
              {(keyword || minPrice || maxPrice) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setKeyword("");
                    setSearchInput("");
                    setMinPrice("");
                    setMaxPrice("");
                    setPage(1);
                  }}
                  className="mt-3"
                >
                  <X className="w-3.5 h-3.5 mr-1" />
                  清除筛选条件
                </Button>
              )}
            </div>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">共 {total} 件商品</p>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {products.map((product) => (
                  <div
                    key={product.id}
                    className="cursor-pointer"
                    onClick={() => openProduct(product)}
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
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                  >
                    上一页
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                  >
                    下一页
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}
