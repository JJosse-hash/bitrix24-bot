"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";

export function MiniMap({ lat, lon }: { lat: number; lon: number }) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors"
          }
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }]
      },
      center: [lon, lat],
      zoom: 13
    });
    new maplibregl.Marker({ color: "#0f766e" }).setLngLat([lon, lat]).addTo(map);
    return () => map.remove();
  }, [lat, lon]);

  return <div ref={ref} className="h-64 w-full overflow-hidden rounded border border-line" />;
}
