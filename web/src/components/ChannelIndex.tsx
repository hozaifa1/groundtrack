import { useMemo } from "react";
import { MagnifyingGlass } from "@phosphor-icons/react";
import type { ChannelSummary } from "../types";
import { fmtInt } from "../lib/plot";

interface Props {
  channels: ChannelSummary[];
  current: string;
  query: string;
  onQuery: (q: string) => void;
  onPick: (id: string) => void;
}

export function ChannelIndex({ channels, current, query, onQuery, onPick }: Props) {
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return channels;
    return channels.filter(
      (c) =>
        c.id.toLowerCase().includes(q) ||
        c.spacecraft.toLowerCase().includes(q) ||
        c.split.startsWith(q),
    );
  }, [channels, query]);

  const groups = useMemo(() => {
    const by = new Map<string, ChannelSummary[]>();
    for (const c of filtered) {
      const list = by.get(c.spacecraft) ?? [];
      list.push(c);
      by.set(c.spacecraft, list);
    }
    return [...by.entries()];
  }, [filtered]);

  /** Up and down move through the list the operator is actually looking at,
   *  filtered order included, so keyboard and eye stay in agreement. */
  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const i = filtered.findIndex((c) => c.id === current);
    const next =
      filtered[Math.min(filtered.length - 1, Math.max(0, i + (e.key === "ArrowDown" ? 1 : -1)))];
    if (next) onPick(next.id);
  }

  return (
    <nav className="index" aria-label="Telemetry channels" onKeyDown={onKeyDown}>
      <div className="index-head">
        <span className="label">Channel index</span>
        <span className="num" style={{ fontSize: "var(--t-sm)", color: "var(--ink-2)" }}>
          {filtered.length} / {channels.length}
        </span>
      </div>

      <div className="search">
        <MagnifyingGlass size={20} weight="bold" aria-hidden="true" />
        <input
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Filter by id, craft, split"
          aria-label="Filter channels"
          spellCheck={false}
          autoComplete="off"
        />
      </div>

      <div className="index-list">
        {groups.length === 0 && (
          <div className="empty">
            <h3>No channel matches</h3>
            <p>
              Nothing in the benchmark matches that filter. Try a channel prefix such as A, E or T,
              a spacecraft name, or one of the two splits.
            </p>
            <button className="control" onClick={() => onQuery("")}>
              Clear filter
            </button>
          </div>
        )}

        {groups.map(([craft, list]) => (
          <div key={craft}>
            <div className="index-group">
              <span className="label">
                {craft}, {list.length} channels, {list.filter((c) => c.detections > 0).length} firing
              </span>
            </div>
            {list.map((c) => (
              <button
                key={c.id}
                className="chan"
                aria-current={c.id === current}
                onClick={() => onPick(c.id)}
              >
                <span className="chan-id">{c.id}</span>
                <span className="chan-split">
                  {c.split === "holdout" ? "held out" : "dev"}, {fmtInt.format(c.n)}
                </span>
                <span className={c.detections > 0 ? "chan-count fired" : "chan-count"}>
                  {c.detections}
                </span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </nav>
  );
}
