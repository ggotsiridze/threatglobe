import type { Severity } from "../api/types";

export function SeverityBadge({ severity, score }: { severity: Severity; score?: number }) {
  return (
    <span className={`sev sev-${severity.toLowerCase()}`} title={`Risk rating ${severity}`}>
      <span className="sev-dot" aria-hidden />
      {severity}
      {score !== undefined && <span className="sev-score">{score}</span>}
    </span>
  );
}
