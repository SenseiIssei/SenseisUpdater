import { ShieldCheck, ShieldAlert, Cpu, ArrowUpCircle } from "lucide-react";
import { Card } from "./ui";
import type { ScanResult } from "../types";

/**
 * Backend ids that come from the Windows Update Agent.
 *
 * These match `BackendKind::id()` in `odysync-core`. Kept as one object so the
 * order below is the order they render in, security first.
 */
const WINDOWS_UPDATE_BACKENDS = [
  {
    id: "windows-update",
    label: "Security & quality",
    icon: ShieldCheck,
    tone: "text-accent",
  },
  {
    id: "windows-defender-update",
    label: "Defender definitions",
    icon: ShieldAlert,
    tone: "text-accent",
  },
  { id: "windows-drivers", label: "Drivers", icon: Cpu, tone: "text-accent" },
  {
    id: "windows-feature-update",
    label: "Feature upgrades",
    icon: ArrowUpCircle,
    tone: "text-warning",
  },
] as const;

interface Row {
  label: string;
  icon: (typeof WINDOWS_UPDATE_BACKENDS)[number]["icon"];
  tone: string;
  actionable: number;
  blocked: number;
  reasons: string[];
}

/**
 * A summary of what Windows itself is offering.
 *
 * The generic update list is correct but flattens a real distinction: on an
 * unelevated run every Windows update lands in `skipped`, mixed in with
 * everything else the policy engine declined. On the machine this was built
 * against that meant 13 pending security updates sitting inside a list of 49
 * skipped entries, which reads as "nothing to do".
 *
 * Returns `null` when Windows Update contributed nothing to the scan, so the
 * card simply does not exist on macOS and Linux.
 */
export default function WindowsUpdateCard({
  scan,
  elevated,
}: {
  scan: ScanResult;
  elevated: boolean;
}) {
  const rows: Row[] = WINDOWS_UPDATE_BACKENDS.map(({ id, label, icon, tone }) => {
    const actionable = scan.actionable.filter((u) => u.backend === id);
    const blocked = scan.skipped.filter((s) => s.backend === id);
    return {
      label,
      icon,
      tone,
      actionable: actionable.length,
      blocked: blocked.length,
      // Deduplicated: fifteen updates blocked for the same reason should say
      // that reason once.
      reasons: [...new Set(blocked.map((s) => s.reason))],
    };
  }).filter((r) => r.actionable > 0 || r.blocked > 0);

  if (rows.length === 0) return null;

  const total = rows.reduce((n, r) => n + r.actionable + r.blocked, 0);
  const blockedByElevation = rows.some((r) =>
    r.reasons.some((reason) => reason.toLowerCase().includes("administrator")),
  );

  return (
    <Card title={`Windows Update — ${total} pending`}>
      <div className="space-y-2">
        {rows.map((row) => {
          const Icon = row.icon;
          return (
            <div key={row.label} className="flex items-start gap-3 text-xs">
              <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${row.tone}`} />
              <span className="flex-1 text-cyber-text">{row.label}</span>
              <div className="text-right">
                {row.actionable > 0 && (
                  <div className="text-success">{row.actionable} ready</div>
                )}
                {row.blocked > 0 && (
                  // `title` alone would become the accessible name and replace
                  // the visible "N blocked" entirely, so a screen reader would
                  // hear the reason and never the count. aria-label carries
                  // both.
                  <div
                    className="text-cyber-text-dim"
                    title={row.reasons.join("; ")}
                    aria-label={`${row.blocked} blocked: ${row.reasons.join("; ")}`}
                  >
                    {row.blocked} blocked
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* The single most common reason a Windows update cannot be applied, and
          one the user can act on immediately. Shown only when it is actually
          the cause, so it does not become background noise. */}
      {blockedByElevation && !elevated && (
        <p className="mt-3 pt-3 border-t border-cyber-border text-xs text-warning">
          Installing Windows updates needs administrator rights. Scanning does not
          — that is why they are listed here. Restart Odysync as administrator to
          apply them.
        </p>
      )}

      {/* A feature-upgrade row can only appear when the backend is enabled —
          it is off by default, and a disabled backend contributes nothing to a
          scan. So the note explains why they are showing, not how to show
          them. */}
      {rows.some((r) => r.label === "Feature upgrades") && (
        <p className="mt-3 pt-3 border-t border-cyber-border text-xs text-warning">
          Feature upgrades replace the Windows version and take far longer than a
          normal update. They are listed because{" "}
          <code className="text-accent">windows-feature-update</code> is in your{" "}
          <code className="text-accent">enabled-backends</code>.
        </p>
      )}
    </Card>
  );
}
