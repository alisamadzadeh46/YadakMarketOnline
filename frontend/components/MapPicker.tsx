"use client";
// Leaflet map (bundled locally — no CDN script). Tile server is configurable
// via NEXT_PUBLIC_MAP_TILES so an Iranian provider (e.g. map.ir) can be used
// to keep maps working during international-internet cutoffs.
import { useEffect, useRef } from "react";
import "leaflet/dist/leaflet.css";

const TILES =
  process.env.NEXT_PUBLIC_MAP_TILES ||
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TEHRAN: [number, number] = [35.6892, 51.389];

export default function MapPicker({
  lat,
  lng,
  onChange,
  readOnly = false,
  height = 260,
}: {
  lat?: number | string | null;
  lng?: number | string | null;
  onChange?: (lat: number, lng: number) => void;
  readOnly?: boolean;
  height?: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);

  useEffect(() => {
    let disposed = false;
    (async () => {
      const L = (await import("leaflet")).default;
      if (disposed || !box.current || mapRef.current) return;

      const start: [number, number] =
        lat && lng ? [Number(lat), Number(lng)] : TEHRAN;

      const map = L.map(box.current, { attributionControl: false }).setView(start, lat ? 15 : 11);
      L.tileLayer(TILES, { maxZoom: 19 }).addTo(map);
      mapRef.current = map;

      // CSS pin instead of Leaflet's default image assets.
      const icon = L.divIcon({
        className: "",
        html: `<div style="width:30px;height:30px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);
          background:linear-gradient(135deg,#5B2E9E,#7B45C9);border:3px solid #fff;
          display:grid;place-items:center">
          <span style="width:9px;height:9px;border-radius:50%;background:#FF8A3D;transform:rotate(45deg)"></span></div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 30],
      });

      if (lat && lng) {
        markerRef.current = L.marker(start, { icon }).addTo(map);
      }

      if (!readOnly && onChange) {
        map.on("click", (e: any) => {
          const { lat: la, lng: ln } = e.latlng;
          if (markerRef.current) markerRef.current.setLatLng(e.latlng);
          else markerRef.current = L.marker(e.latlng, { icon }).addTo(map);
          onChange(Number(la.toFixed(6)), Number(ln.toFixed(6)));
        });
      }
    })();
    return () => {
      disposed = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      ref={box}
      style={{ height, borderRadius: 14, overflow: "hidden", border: "1.5px solid var(--line)", zIndex: 0 }}
    />
  );
}
