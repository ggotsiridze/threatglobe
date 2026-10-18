import { Suspense, lazy, useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";

import { fetchReplayEvents } from "./api/client";
import type { AttackEvent } from "./api/types";
import { AttackDrawer } from "./components/AttackDrawer";
import { LiveFeed } from "./components/LiveFeed";
import { ReplayControls } from "./components/ReplayControls";
import { StatCards } from "./components/StatCards";
import { TimelineChart } from "./components/TimelineChart";
import { TopBar } from "./components/TopBar";
import { TopList } from "./components/TopList";
import { statusIndicator } from "./hooks/connection";
import { type View, dashboardReducer, initialDashboard } from "./hooks/dashboardState";
import { useArcs } from "./hooks/useArcs";
import { useAttackStream } from "./hooks/useAttackStream";
import { ReplayController, type ReplaySpeed, type ReplayState } from "./replay/ReplayController";
import { SEVERITY_COLORS, formatNumber } from "./utils/format";

const GlobeView = lazy(() => import("./components/GlobeView"));

export default function App() {
  const [state, dispatch] = useReducer(dashboardReducer, initialDashboard);
  const [selected, setSelected] = useState<AttackEvent | null>(null);
  const { arcs, rings, fire, clear } = useArcs(state.sensor);
  const viewRef = useRef<View>(state.view);
  viewRef.current = state.view;
  const fireRef = useRef(fire);
  fireRef.current = fire;

  const { connection, mode } = useAttackStream({
    onHello: (hello) => dispatch({ type: "hello", hello }),
    onAttack: (event) => {
      dispatch({ type: "attack", event });
      if (viewRef.current === "live") fireRef.current(event, SEVERITY_COLORS[event.severity]);
    },
    onSnapshot: (snapshot) => dispatch({ type: "snapshot", snapshot }),
  });

  // --- replay ---------------------------------------------------------------
  const controller = useMemo(
    () =>
      new ReplayController((event) => {
        dispatch({ type: "replayEmit", event });
        fireRef.current(event, SEVERITY_COLORS[event.severity]);
      }),
    [],
  );
  const [replay, setReplay] = useState<ReplayState>(controller.state);
  const [replayMinutes, setReplayMinutes] = useState(15);
  const [replayLoading, setReplayLoading] = useState(false);
  useEffect(() => controller.subscribe(setReplay), [controller]);
  useEffect(() => () => controller.dispose(), [controller]);

  const loadReplay = useCallback(
    async (minutes: number, autoplay: boolean) => {
      controller.pause();
      setReplayLoading(true);
      dispatch({ type: "replayReset" });
      try {
        controller.load(await fetchReplayEvents(minutes));
        if (autoplay) controller.play();
      } catch (err) {
        console.warn("replay load failed", err);
        controller.load([]);
      } finally {
        setReplayLoading(false);
      }
    },
    [controller],
  );

  const changeView = (view: View) => {
    if (view === state.view) return;
    clear();
    dispatch({ type: "setView", view });
    if (view === "replay") void loadReplay(replayMinutes, true);
    else controller.pause();
  };

  const restartReplay = () => {
    clear();
    dispatch({ type: "replayReset" });
    controller.restart();
  };

  const status = statusIndicator(connection, mode);
  const feed = state.view === "live" ? state.liveFeed : state.replayFeed;
  const stats = state.stats;

  return (
    <div className="app">
      <TopBar status={status} isDemo={mode !== "live"} publicMode={state.publicMode} view={state.view} onViewChange={changeView} />

      <main className="layout">
        <aside className="col col-left">
          <StatCards stats={stats} />
          <TopList title="Top Attacking Countries" items={stats?.top_countries} withFlags testId="top-countries" limit={7} />
          <TopList title="Top Honeypots" items={stats?.top_honeypots} testId="top-honeypots" limit={5} />
        </aside>

        <section className="stage">
          <div className="hero">
            <div className="hero-kicker">
              <span className="live-dot" aria-hidden /> {state.view === "live" ? "Monitoring in progress" : "Historical replay"}
            </div>
            <h1 className="hero-title">
              This system is watching
              <br />
              cyber attacks around the world.
            </h1>
            <p className="hero-sub">
              <b className="mono" data-testid="hero-count">{formatNumber(stats?.events_today)}</b> attacks against a honeypot
              sensor in {state.sensor?.city ?? "—"} in the last 24h ·{" "}
              <b className="mono">{formatNumber(stats?.events_last_minute)}</b>/min now
            </p>
            {mode !== "live" && (
              <p className="hero-disclaimer">
                <span className="badge badge-demo">DEMO DATA</span> Synthetic, sanitized telemetry streamed through the real
                pipeline. These are not real attacks.
              </p>
            )}
          </div>

          <Suspense fallback={<div className="globe-wrap globe-loading">Initializing globe…</div>}>
            <GlobeView arcs={arcs} rings={rings} sources={feed.slice(0, 80)} sensor={state.sensor} onSelect={setSelected} />
          </Suspense>

          <div className="severity-legend" aria-label="Arc color legend">
            {Object.entries(SEVERITY_COLORS).map(([sev, color]) => (
              <span key={sev} className="legend-item">
                <span className="legend-line" style={{ background: color }} />
                {sev}
                <span className="mono muted">{formatNumber(stats?.severity_counts[sev as keyof typeof SEVERITY_COLORS])}</span>
              </span>
            ))}
          </div>

          {state.view === "replay" && (
            <ReplayControls
              state={replay}
              loading={replayLoading}
              minutes={replayMinutes}
              onMinutes={(m) => {
                setReplayMinutes(m);
                clear();
                void loadReplay(m, false);
              }}
              onPlay={() => controller.play()}
              onPause={() => controller.pause()}
              onRestart={restartReplay}
              onSpeed={(s: ReplaySpeed) => controller.setSpeed(s)}
            />
          )}
        </section>

        <aside className="col col-right">
          <LiveFeed
            events={feed}
            title={state.view === "live" ? "Live Attack Feed" : "Replay Feed"}
            selectedId={selected?.id ?? null}
            onSelect={setSelected}
          />
        </aside>

        <section className="bottom">
          <TimelineChart timeline={state.timeline} />
          <TopList title="Top Targeted Ports" items={stats?.top_ports} testId="top-ports" limit={6} />
        </section>
      </main>

      <AttackDrawer event={selected} publicMode={state.publicMode} onClose={() => setSelected(null)} />
    </div>
  );
}
