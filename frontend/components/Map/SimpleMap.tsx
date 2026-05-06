"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix Leaflet default icon path issue with bundlers
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export interface MapMarker {
  lat: number;
  lng: number;
  title: string;
  popup?: string;
  color?: string;
}

interface SimpleMapProps {
  markers: MapMarker[];
  center?: { lat: number; lng: number };
  zoom?: number;
  className?: string;
  height?: string;
}

export default function SimpleMap({
  markers,
  center,
  zoom = 14,
  className = "",
  height = "300px",
}: SimpleMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<L.Map | null>(null);
  const resizeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return;

    const map = L.map(mapRef.current, {
      zoomControl: true,
      attributionControl: false,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
    }).addTo(map);

    leafletMap.current = map;

    return () => {
      if (resizeTimerRef.current) {
        clearTimeout(resizeTimerRef.current);
        resizeTimerRef.current = null;
      }
      map.remove();
      leafletMap.current = null;
    };
  }, []);

  useEffect(() => {
    const map = leafletMap.current;
    if (!map) return;

    // Clear existing markers
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker) map.removeLayer(layer);
    });

    // Add markers
    const bounds = L.latLngBounds([]);
    let hasBounds = false;

    markers.forEach((m) => {
      const markerColor = m.color || "#3b82f6";
      const markerHtml = `<div style="background:${markerColor};width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3)"></div>`;
      const icon = L.divIcon({ html: markerHtml, className: "", iconSize: [16, 16], iconAnchor: [8, 8] });

      const marker = L.marker([m.lat, m.lng], { icon }).addTo(map);

      if (m.popup || m.title) {
        marker.bindPopup(`<strong>${m.title}</strong>${m.popup ? `<br/>${m.popup}` : ""}`);
      }

      bounds.extend([m.lat, m.lng]);
      hasBounds = true;
    });

    // Set view
    if (markers.length > 1 && hasBounds) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    } else if (center) {
      map.setView([center.lat, center.lng], zoom);
    } else if (markers.length === 1) {
      map.setView([markers[0].lat, markers[0].lng], zoom);
    }

    // Fix map rendering in modals/dialogs. Leaflet may throw if the
    // component unmounts before the delayed resize runs.
    if (resizeTimerRef.current) clearTimeout(resizeTimerRef.current);
    resizeTimerRef.current = setTimeout(() => {
      if (leafletMap.current !== map || !mapRef.current) return;
      try {
        map.invalidateSize();
      } catch {
        // Ignore stale Leaflet instances during React remounts.
      }
    }, 200);
  }, [markers, center, zoom]);

  return (
    <div
      ref={mapRef}
      className={`rounded-lg overflow-hidden ${className}`}
      style={{ height, width: "100%" }}
    />
  );
}
