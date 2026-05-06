"use client";

import type { Restaurant } from "@/lib/types";

interface RestaurantCardProps {
  restaurant: Restaurant;
  onNavigate?: (name: string) => void;
  onSelect?: (restaurant: Restaurant) => void;
  selected?: boolean;
}

export default function RestaurantCard({ restaurant, onNavigate, onSelect, selected }: RestaurantCardProps) {
  const rating = restaurant.rating ? parseFloat(restaurant.rating) : null;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-4 hover:shadow-md transition ${selected ? "border-green-300 ring-2 ring-green-100" : ""}`}>
      {/* Header */}
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <button
            onClick={() => onNavigate?.(restaurant.name)}
            className="text-sm font-medium text-blue-700 hover:text-blue-500 hover:underline text-left truncate block"
          >
            {restaurant.name}
          </button>
          <div className="flex items-center gap-2 mt-1">
            {rating && (
              <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">
                {rating.toFixed(1)}
              </span>
            )}
            {restaurant.category && (
              <span className="text-xs bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-gray-400 px-1.5 py-0.5 rounded">
                {restaurant.category}
              </span>
            )}
            {restaurant.distance && (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {restaurant.distance}m
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Tags */}
      {restaurant.tags && restaurant.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {restaurant.tags.slice(0, 4).map((tag: string, i: number) => (
            <span key={i} className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Address */}
      {restaurant.address && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-2 truncate">{restaurant.address}</p>
      )}

      {/* Opening Hours */}
      {restaurant.opening_hours && (
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">🕒 {restaurant.opening_hours}</p>
      )}

      {/* Reason */}
      {restaurant.reason && (
        <p className="text-xs text-gray-600 dark:text-gray-300 mt-2 bg-gray-50 dark:bg-slate-900 p-2 rounded">
          {restaurant.reason}
        </p>
      )}

      {/* Recommended Dishes */}
      {restaurant.recommended_dishes && restaurant.recommended_dishes.length > 0 && (
        <div className="mt-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">推荐菜: </span>
          {restaurant.recommended_dishes.map((dish: string, i: number) => (
            <span key={i} className="text-xs text-orange-600">
              {dish}{i < restaurant.recommended_dishes!.length - 1 ? " · " : ""}
            </span>
          ))}
        </div>
      )}

      {/* Navigate Button */}
      {onNavigate && (
        <div className="mt-3 grid grid-cols-2 gap-2">
          <button
            onClick={() => onNavigate(restaurant.name)}
            className="py-1.5 text-xs text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition"
          >
            查看路线
          </button>
          {onSelect && (
            <button
              onClick={() => onSelect(restaurant)}
              className={`py-1.5 text-xs rounded-lg transition ${
                selected
                  ? "bg-green-100 text-green-700"
                  : "bg-green-600 text-white hover:bg-green-700"
              }`}
            >
              {selected ? "已选择" : "选择餐厅"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
