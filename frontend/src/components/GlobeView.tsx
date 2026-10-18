import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import { MeshPhongMaterial } from "three";
import { feature } from "topojson-client";
import type { Topology } from "topojson-specification";
import countriesTopo from "world-atlas/countries-110m.json";

import type { AttackEvent, Sensor } from "../api/types";
import { type Arc, FLIGHT_MS, type Ring } from "../hooks/useArcs";
import { SEVERITY_COLORS } from "../utils/format";

interface Props {
  arcs: Arc[];
  rings: Ring[];
  sources: AttackEvent[];
  sensor: Sensor | null;
  onSelect: (event: AttackEvent) => void;
}

function ringArea(ring: GeoJSON.Position[]): number {
  let area = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    area += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1]);
  }
  return Math.abs(area / 2);
}

/** Drop zero-area slivers (e.g. one North Korea ring) that make H3 throw. */
export function cleanCountries(fc: GeoJSON.FeatureCollection): GeoJSON.Feature[] {
  const out: GeoJSON.Feature[] = [];
  for (const f of fc.features) {
    const g = f.geometry;
    if (!g || (g.type !== "Polygon" && g.type !== "MultiPolygon")) continue;
    const polys = (g.type === "Polygon" ? [g.coordinates] : g.coordinates).filter((p) => ringArea(p[0]) > 1e-6);
    if (polys.length) out.push({ ...f, geometry: { type: "MultiPolygon", coordinates: polys } });
  }
  return out;
}

const topo = countriesTopo as unknown as Topology;
const COUNTRIES = cleanCountries(feature(topo, topo.objects.countries) as unknown as GeoJSON.FeatureCollection);

function hexToRgba(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

// Accessors are module-level so their identity is stable across renders;
// a new function identity makes three-globe rebuild the whole layer.
const hexColor = () => "rgba(120, 160, 210, 0.42)";
const arcColor = (d: object) => {
  const c = SEVERITY_COLORS[(d as Arc).event.severity];
  return [hexToRgba(c, 0.35), hexToRgba(c, 1)];
};
const arcStroke = (d: object) => {
  const sev = (d as Arc).event.severity;
  return sev === "CRITICAL" ? 1.5 : sev === "HIGH" ? 1.1 : sev === "MEDIUM" ? 0.8 : 0.6;
};
const arcLabel = (d: object) => {
  const e = (d as Arc).event;
  return `<div class="globe-tip"><b>${e.severity}</b> · ${e.source_country ?? "Unknown"} → ${e.honeypot}</div>`;
};
const ringColor = (d: object) => (t: number) => hexToRgba((d as Ring).color, Math.max(0, 1 - t));
const pointLabel = (d: object) => `<div class="globe-tip">${(d as PointDatum).label}</div>`;
const labelColor = () => "#5eead4";

interface PointDatum {
  lat: number;
  lng: number;
  color: string;
  radius: number;
  altitude: number;
  event: AttackEvent | null;
  label: string;
}

export default function GlobeView({ arcs, rings, sources, sensor, onSelect }: Props) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  const material = useMemo(
    () => new MeshPhongMaterial({ color: "#0a1426", emissive: "#050b16", shininess: 6, transparent: false }),
    [],
  );

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) setSize({ width: Math.round(width), height: Math.round(height) });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const globe = globeRef.current;
    if (!globe) return;
    const controls = globe.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableZoom = true;
    controls.minDistance = 180;
    controls.maxDistance = 600;
    globe.pointOfView({ lat: sensor?.latitude ?? 30, lng: (sensor?.longitude ?? 10) + 25, altitude: 2.3 }, 0);
  }, [sensor]);

  // One point per distinct source location (newest event wins), plus the sensor.
  const points = useMemo<PointDatum[]>(() => {
    const seen = new Map<string, PointDatum>();
    for (const e of sources) {
      if (e.source_latitude == null || e.source_longitude == null) continue;
      const key = `${e.source_latitude.toFixed(1)},${e.source_longitude.toFixed(1)}`;
      if (seen.has(key)) continue;
      seen.set(key, {
        lat: e.source_latitude,
        lng: e.source_longitude,
        color: SEVERITY_COLORS[e.severity] ?? SEVERITY_COLORS.LOW,
        radius: 0.4,
        altitude: 0.01,
        event: e,
        label: `${e.source_city ?? "Unknown"}, ${e.source_country ?? ""} · ${e.severity}`,
      });
    }
    const list = [...seen.values()];
    if (sensor) {
      list.push({
        lat: sensor.latitude,
        lng: sensor.longitude,
        color: "#5eead4",
        radius: 0.7,
        altitude: 0.02,
        event: null,
        label: `Honeypot sensor · ${sensor.city}`,
      });
    }
    return list;
  }, [sources, sensor]);

  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const handleArcClick = useCallback((d: object) => onSelectRef.current((d as Arc).event), []);
  const handlePointClick = useCallback((d: object) => {
    const ev = (d as PointDatum).event;
    if (ev) onSelectRef.current(ev);
  }, []);

  const labels = useMemo(
    () => (sensor ? [{ lat: sensor.latitude, lng: sensor.longitude, text: `HONEYPOT · ${sensor.city.toUpperCase()}` }] : []),
    [sensor],
  );

  return (
    <div className="globe-wrap" ref={wrapRef} data-testid="globe" data-arcs={arcs.length} data-points={points.length}>
      <Globe
        ref={globeRef}
        width={size.width}
        height={size.height}
        backgroundColor="rgba(0,0,0,0)"
        globeMaterial={material}
        showAtmosphere
        atmosphereColor="#3b82f6"
        atmosphereAltitude={0.16}
        hexPolygonsData={COUNTRIES}
        hexPolygonResolution={3}
        hexPolygonMargin={0.42}
        hexPolygonUseDots
        hexPolygonColor={hexColor}
        hexPolygonAltitude={0.004}
        arcsData={arcs}
        arcStartLat="startLat"
        arcStartLng="startLng"
        arcEndLat="endLat"
        arcEndLng="endLng"
        arcColor={arcColor}
        arcStroke={arcStroke}
        arcAltitudeAutoScale={0.42}
        arcDashLength={0.6}
        arcDashGap={2}
        arcDashInitialGap={1}
        arcDashAnimateTime={FLIGHT_MS}
        arcsTransitionDuration={0}
        arcLabel={arcLabel}
        onArcClick={handleArcClick}
        ringsData={rings}
        ringLat="lat"
        ringLng="lng"
        ringColor={ringColor}
        ringMaxRadius={4.5}
        ringPropagationSpeed={3.5}
        ringRepeatPeriod={FLIGHT_MS}
        pointsData={points}
        pointLat="lat"
        pointLng="lng"
        pointColor="color"
        pointRadius="radius"
        pointAltitude="altitude"
        pointsMerge={false}
        pointLabel={pointLabel}
        onPointClick={handlePointClick}
        labelsData={labels}
        labelLat="lat"
        labelLng="lng"
        labelText="text"
        labelSize={0.9}
        labelDotRadius={0}
        labelColor={labelColor}
        labelAltitude={0.02}
        labelResolution={2}
      />
    </div>
  );
}
