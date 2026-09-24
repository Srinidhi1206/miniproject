"use client";

import "leaflet/dist/leaflet.css";

import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";

import { SCAM_TYPE_LABEL } from "@/features/community/scam-types";
import type { MapLocation, ScamType } from "@/types/api";

/** Circle AREA is proportional to report count (radius ∝ √n), one neutral hue. */
export default function ScamMapView({ locations }: { locations: MapLocation[] }) {
  const max = Math.max(1, ...locations.map((l) => l.total));
  return (
    <MapContainer
      center={[22.6, 79.5]}
      zoom={4.6}
      zoomSnap={0.2}
      minZoom={4}
      maxZoom={9}
      scrollWheelZoom={false}
      className="h-[26rem] w-full sm:h-[32rem]"
      aria-label="Map of reported scams by city"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      {locations.map((l) => {
        const top = (Object.entries(l.by_type) as [ScamType, number][]).sort((a, b) => b[1] - a[1]);
        return (
          <CircleMarker
            key={l.slug}
            center={[l.lat, l.lng]}
            radius={5 + 22 * Math.sqrt(l.total / max)}
            pathOptions={{ color: "#ffffff", weight: 2, fillColor: "#15171b", fillOpacity: 0.72 }}
          >
            <Tooltip direction="top" offset={[0, -6]}>{l.city}: {l.total} report{l.total === 1 ? "" : "s"}</Tooltip>
            <Popup>
              <div className="min-w-44 font-sans">
                <p className="text-sm font-semibold text-ink">{l.city}</p>
                <p className="text-xs text-muted">{l.region} · approximate city area</p>
                <ul className="mt-2 space-y-1">
                  {top.map(([t, n]) => (
                    <li key={t} className="flex justify-between gap-4 text-xs">
                      <span className="text-ink-2">{SCAM_TYPE_LABEL[t]}</span>
                      <span className="font-mono tabular-nums text-ink">{n}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
