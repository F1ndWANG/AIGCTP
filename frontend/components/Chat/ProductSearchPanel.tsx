"use client";

import { useState } from "react";
import { commerce as commerceApi } from "@/lib/api";
import type { ProductListItem } from "@/lib/types";

interface ProductSearchPanelProps {
  onAddToCart: (productId: number) => void;
}

export default function ProductSearchPanel({ onAddToCart }: ProductSearchPanelProps) {
  const [keyword, setKeyword] = useState("");
  const [results, setResults] = useState<ProductListItem[]>([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    if (!keyword.trim()) return;
    setSearching(true);
    try {
      const data = await commerceApi.listProducts({ keyword: keyword.trim(), page_size: 6 });
      setResults(data.items);
    } catch {
      // ignore
    }
    setSearching(false);
  };

  return (
    <div className="border-t dark:border-slate-700 bg-white dark:bg-slate-800 max-h-64 overflow-y-auto">
      <div className="max-w-2xl mx-auto w-full px-4 py-3">
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="搜索商品..."
            className="flex-1 px-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            autoFocus
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {searching ? "..." : "搜索"}
          </button>
          <button
            onClick={() => { setResults([]); setKeyword(""); }}
            className="px-2 py-1.5 text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
          >
            ✕
          </button>
        </div>
        {results.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {results.map((p) => (
              <div key={p.id} className="border dark:border-slate-700 rounded-lg p-2 flex flex-col gap-1">
                <p className="text-xs font-medium truncate">{p.name}</p>
                <p className="text-xs text-red-600 font-bold">¥{p.price}</p>
                <button
                  onClick={() => onAddToCart(p.id)}
                  disabled={p.stock < 1}
                  className="text-xs py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-100 disabled:text-gray-400"
                >
                  {p.stock < 1 ? "缺货" : "加购"}
                </button>
              </div>
            ))}
          </div>
        )}
        {keyword && !searching && results.length === 0 && (
          <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-2">未找到相关商品</p>
        )}
      </div>
    </div>
  );
}
