import { useCallback, useEffect, useRef, useState } from "react";

import type { AttackEvent, Sensor } from "../api/types";

export const FLIGHT_MS = 1600;
const MAX_ARCS = 60;

export interface Arc {
  key: string;
  event: AttackEvent;
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  born: number;
}

export interface Ring {
  key: string;
  lat: number;
  lng: number;
  color: string;
  born: number;
}

/** Tracks in-flight attack arcs and the impact rings they leave behind. */
export function useArcs(sensor: Sensor | null) {
  const [arcs, setArcs] = useState<Arc[]>([]);
  const [rings, setRings] = useState<Ring[]>([]);
  const timers = useRef(new Set<ReturnType<typeof setTimeout>>());
  const seq = useRef(0);

  const later = (fn: () => void, ms: number) => {
    const t = setTimeout(() => {
      timers.current.delete(t);
      fn();
    }, ms);
    timers.current.add(t);
  };

  const fire = useCallback(
    (event: AttackEvent, color: string) => {
      if (!sensor || event.source_latitude == null || event.source_longitude == null) return;
      const key = `${event.id}-${seq.current++}`;
      const arc: Arc = {
        key,
        event,
        startLat: event.source_latitude,
        startLng: event.source_longitude,
        endLat: sensor.latitude,
        endLng: sensor.longitude,
        born: Date.now(),
      };
      setArcs((prev) => [...prev.slice(-(MAX_ARCS - 1)), arc]);
      later(() => {
        setRings((prev) => [
          ...prev.slice(-20),
          { key, lat: sensor.latitude, lng: sensor.longitude, color, born: Date.now() },
        ]);
      }, FLIGHT_MS);
      later(() => setArcs((prev) => prev.filter((a) => a.key !== key)), FLIGHT_MS * 2);
      later(() => setRings((prev) => prev.filter((r) => r.key !== key)), FLIGHT_MS * 2.5);
    },
    [sensor],
  );

  const clear = useCallback(() => {
    setArcs([]);
    setRings([]);
  }, []);

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach(clearTimeout);
  }, []);

  return { arcs, rings, fire, clear };
}
