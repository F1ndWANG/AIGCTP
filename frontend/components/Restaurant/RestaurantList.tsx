"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import type { Restaurant } from "@/lib/types";
import RestaurantCard from "./RestaurantCard";
import RoutePanel from "@/components/TravelPlan/RoutePanel";

const SimpleMap = dynamic(() => import("@/components/Map/SimpleMap"), { ssr: false });

interface RestaurantListProps {
  restaurants: Restaurant[];
  city?: string;
  title?: string;
  onNavigate?: (name: string) => void;
  onSelect?: (restaurant: Restaurant) => void;
  selectedName?: string;
}

export default function RestaurantList({ restaurants, city, title, onSelect, selectedName }: RestaurantListProps) {
  const [selectedPoi, setSelectedPoi] = useState<string | null>(null);
  const [showMap, setShowMap] = useState(false);

  if (restaurants.length === 0) return null;

  const mapMarkers = restaurants
    .filter((r) => r.latitude && r.longitude)
    .map((r) => ({
      lat: r.latitude!,
      lng: r.longitude!,
      title: r.name,
      popup: r.address,
    }));

  return (
    <div>
      {title && (
        <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">{title}</h3>
      )}

      {/* Map toggle */}
      {mapMarkers.length > 1 && (
        <button
          onClick={() => setShowMap(!showMap)}
          className="mb-3 px-3 py-1.5 text-xs bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition"
        >
          {showMap ? "隐藏地图" : "在地图上查看"}
        </button>
      )}

      {showMap && mapMarkers.length > 0 && (
        <div className="mb-4">
          <SimpleMap markers={mapMarkers} height="250px" />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {restaurants.map((r, i) => (
          <RestaurantCard
            key={i}
            restaurant={r}
            onNavigate={(name) => setSelectedPoi(name)}
            onSelect={onSelect}
            selected={selectedName === r.name}
          />
        ))}
      </div>

      {selectedPoi && (
        <RoutePanel
          poiName={selectedPoi}
          city={city || ""}
          onClose={() => setSelectedPoi(null)}
        />
      )}
    </div>
  );
}
