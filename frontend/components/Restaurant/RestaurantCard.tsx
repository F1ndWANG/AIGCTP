"use client";

import type { Restaurant } from "@/lib/types";

interface RestaurantCardProps {
  restaurant: Restaurant;
  onNavigate?: (name: string) => void;
}

export default function RestaurantCard({ restaurant, onNavigate }: RestaurantCardProps) {
  const rating = restaurant.rating ? parseFloat(restaurant.rating) : null;

  return (
    <div className="bg-white rounded-lg border p-4 hover:shadow-md transition">
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
              <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                {restaurant.category}
              </span>
            )}
            {restaurant.distance && (
              <span className="text-xs text-gray-400">
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
        <p className="text-xs text-gray-400 mt-2 truncate">{restaurant.address}</p>
      )}

      {/* Opening Hours */}
      {restaurant.opening_hours && (
        <p className="text-xs text-gray-400 mt-0.5">🕒 {restaurant.opening_hours}</p>
      )}

      {/* Reason */}
      {restaurant.reason && (
        <p className="text-xs text-gray-600 mt-2 bg-gray-50 p-2 rounded">
          {restaurant.reason}
        </p>
      )}

      {/* Recommended Dishes */}
      {restaurant.recommended_dishes && restaurant.recommended_dishes.length > 0 && (
        <div className="mt-2">
          <span className="text-xs text-gray-500">推荐菜: </span>
          {restaurant.recommended_dishes.map((dish: string, i: number) => (
            <span key={i} className="text-xs text-orange-600">
              {dish}{i < restaurant.recommended_dishes!.length - 1 ? " · " : ""}
            </span>
          ))}
        </div>
      )}

      {/* Navigate Button */}
      {onNavigate && (
        <button
          onClick={() => onNavigate(restaurant.name)}
          className="mt-3 w-full py-1.5 text-xs text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition"
        >
          查看路线
        </button>
      )}
    </div>
  );
}
