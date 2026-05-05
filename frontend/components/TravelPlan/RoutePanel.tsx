"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { route as routeApi } from "@/lib/api";
import type { RouteResponse } from "@/lib/types";

const SimpleMap = dynamic(() => import("@/components/Map/SimpleMap"), { ssr: false });

type Mode = "transit" | "driving" | "walking";

const MODE_LABELS: Record<Mode, string> = {
  transit: "公交",
  driving: "驾车",
  walking: "步行",
};

interface RoutePanelProps {
  poiName: string;
  city?: string;
  onClose: () => void;
}

export default function RoutePanel({ poiName, city, onClose }: RoutePanelProps) {
  const [origin, setOrigin] = useState<{ lat: number; lng: number } | null>(null);
  const [mode, setMode] = useState<Mode>("transit");
  const [routeData, setRouteData] = useState<RouteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [geoError, setGeoError] = useState(false);

  // Get user's current location on mount
  useEffect(() => {
    if (!navigator.geolocation) {
      setGeoError(true);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setOrigin({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      () => {
        setGeoError(true);
      },
      { timeout: 8000, enableHighAccuracy: false }
    );
  }, []);

  // Fetch route when origin or mode changes
  const fetchRoute = useCallback(async () => {
    if (!origin) return;
    setLoading(true);
    setError("");
    try {
      const result = await routeApi.get({
        destination_name: poiName,
        origin_lat: origin.lat,
        origin_lng: origin.lng,
        city: city || "",
        mode,
      });
      setRouteData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "路线查询失败");
    } finally {
      setLoading(false);
    }
  }, [origin, mode, poiName, city]);

  useEffect(() => {
    if (origin) fetchRoute();
  }, [origin, mode, fetchRoute]);

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Panel */}
      <div className="relative bg-white rounded-t-2xl sm:rounded-2xl w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-xl sm:m-4">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-5 py-4 flex items-center justify-between rounded-t-2xl">
          <div>
            <h3 className="font-semibold text-gray-900 text-base">路线规划</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              {geoError ? "起点: 默认位置" : origin ? "起点: 我的位置" : "获取定位中..."}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400"
          >
            ✕
          </button>
        </div>

        {/* Destination */}
        <div className="px-5 py-3 bg-blue-50 flex items-center gap-2">
          <span className="text-blue-500 text-lg">📍</span>
          <span className="text-sm font-medium text-gray-800">{poiName}</span>
        </div>

        {/* Mode selector */}
        <div className="px-5 py-3 flex gap-2 border-b">
          {(Object.entries(MODE_LABELS) as [Mode, string][]).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setMode(key)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
                mode === key
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="px-5 py-4 space-y-4">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full" />
              <span className="ml-3 text-sm text-gray-500">查询路线中...</span>
            </div>
          )}

          {error && (
            <div className="text-sm text-red-500 bg-red-50 rounded-lg p-3">{error}</div>
          )}

          {routeData && !loading && (
            <>
              {/* Map */}
              {routeData.origin_lat && routeData.destination_lat && (
                <div className="mb-2">
                  <SimpleMap
                    markers={[
                      {
                        lat: routeData.origin_lat,
                        lng: routeData.origin_lng,
                        title: "起点",
                        color: "#22c55e",
                      },
                      {
                        lat: routeData.destination_lat,
                        lng: routeData.destination_lng,
                        title: routeData.destination_name,
                        popup: routeData.destination_name,
                        color: "#3b82f6",
                      },
                    ]}
                    height="200px"
                  />
                </div>
              )}
              {/* Summary */}
              <div className="flex gap-6 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">📏</span>
                  <span className="text-gray-700">{routeData.distance}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">⏱</span>
                  <span className="text-gray-700">{routeData.duration}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">🚌</span>
                  <span className="text-gray-700">{MODE_LABELS[mode]}</span>
                </div>
              </div>

              {/* Steps */}
              {routeData.steps.length > 0 && (
                <div className="space-y-0">
                  <h4 className="text-xs font-medium text-gray-400 uppercase mb-2">
                    路线步骤
                  </h4>
                  <div className="relative">
                    {/* Vertical line */}
                    <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-blue-200" />

                    {routeData.steps.map((step, i) => (
                      <div key={i} className="flex gap-3 pb-4 relative">
                        <div className="w-4 h-4 rounded-full bg-blue-500 border-2 border-white mt-0.5 shrink-0 z-10" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-700">{step.instruction}</p>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {step.distance} · {step.duration}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Open in Maps */}
              <a
                href={routeData.maps_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full py-2.5 text-center text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition"
              >
                在地图中打开
              </a>
            </>
          )}

          {!origin && !geoError && !loading && (
            <div className="text-sm text-gray-400 text-center py-4">
              正在获取你的位置...
            </div>
          )}

          {geoError && !loading && !routeData && (
            <div className="text-sm text-gray-500 text-center py-4">
              无法获取你的位置，请确保已开启定位权限
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
