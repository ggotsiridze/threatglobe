import { REPLAY_SPEEDS, type ReplaySpeed, type ReplayState } from "../replay/ReplayController";
import { formatDateTime } from "../utils/format";

interface Props {
  state: ReplayState;
  loading: boolean;
  minutes: number;
  onMinutes: (m: number) => void;
  onPlay: () => void;
  onPause: () => void;
  onRestart: () => void;
  onSpeed: (s: ReplaySpeed) => void;
}

export function ReplayControls({ state, loading, minutes, onMinutes, onPlay, onPause, onRestart, onSpeed }: Props) {
  const pct = state.total ? (state.index / state.total) * 100 : 0;
  const playing = state.status === "playing";
  return (
    <div className="replay" data-testid="replay-controls">
      <div className="replay-row">
        <span className="replay-label">Attack replay</span>
        {playing ? (
          <button className="btn btn-primary" onClick={onPause} data-testid="replay-pause">❚❚ Pause</button>
        ) : (
          <button className="btn btn-primary" onClick={onPlay} disabled={loading || state.total === 0} data-testid="replay-play">
            ▶ Play
          </button>
        )}
        <button className="btn" onClick={onRestart} disabled={loading || state.total === 0} data-testid="replay-restart">
          ↺ Restart
        </button>
        <div className="segmented small" role="group" aria-label="Replay speed">
          {REPLAY_SPEEDS.map((s) => (
            <button key={s} className={state.speed === s ? "active" : ""} aria-pressed={state.speed === s} onClick={() => onSpeed(s)}>
              {s}x
            </button>
          ))}
        </div>
        <select className="select" value={minutes} onChange={(e) => onMinutes(Number(e.target.value))} aria-label="Replay window">
          <option value={5}>Last 5 min</option>
          <option value={15}>Last 15 min</option>
          <option value={60}>Last 60 min</option>
        </select>
      </div>
      <div className="replay-progress">
        <div className="replay-track">
          <div className="replay-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="mono small" data-testid="replay-position">
          {loading ? "Loading history…" : `${state.index}/${state.total}`}
          {state.cursor ? ` · ${formatDateTime(state.cursor)}` : ""}
          {state.status === "finished" ? " · finished" : ""}
        </span>
        <span className="small muted">1x = real time</span>
      </div>
    </div>
  );
}
