/** Shapes emitted by tools/export_console.py. Kept in one file so a change to
 *  the exporter has exactly one place to land on this side. */

export type Split = "dev" | "holdout";
export type Severity = "high" | "medium" | "low";

export interface Brief {
  file: string;
  happened: string;
  matters: string;
  next: string;
  markdown: string;
}

export interface Detection {
  id: string;
  start: number;
  end: number;
  length: number;
  signature: string;
  title: string;
  severity: Severity;
  action: string;
  z_peak: number;
  w_mean: number;
  w_std: number;
  b_mean: number;
  b_std: number;
  cmds: string[];
  brief: Brief | null;
  /** True when this window overlaps a labelled anomaly. False means the
   *  engine raised an alarm nobody had labelled: a false positive. */
  hit: boolean;
}

export interface TruthWindow {
  start: number;
  end: number;
  /** False means no predicted window overlapped this labelled anomaly. */
  caught: boolean;
  class: string;
}

export interface ChannelSummary {
  id: string;
  spacecraft: string;
  split: Split;
  n: number;
  detections: number;
  baseline_detections: number;
  truth: number;
  caught: number;
  severity: Severity | null;
}

export interface ChannelDetail {
  id: string;
  spacecraft: string;
  split: Split;
  n: number;
  values: number[];
  z: number[];
  truth: TruthWindow[];
  detections: Detection[];
  baseline: { start: number; end: number }[];
}

export interface SplitScore {
  tp: number;
  fp: number;
  fn: number;
  channels: number;
  precision: number;
  recall: number;
  f1: number;
}

export interface EngineConstants {
  threshold: number;
  merge_gap: number;
  min_window: number;
  rolling_window: number;
}

/** Nulls here are real and load-bearing. One attempt was killed from outside
 *  before the harness could record anything about it, so cost, task id and
 *  both scores are genuinely absent rather than zero. */
export interface LedgerRow {
  iteration: number;
  attempt: number | null;
  task_id: string | null;
  cost: number | null;
  tool_calls?: number | null;
  f1_before: number | null;
  f1_after: number | null;
  dev_f1?: number | null;
  holdout_f1?: number | null;
  kept: boolean | null;
  outcome: string;
  note?: string;
  files_touched?: string[];
  bob_report?: {
    target_failure?: string;
    hypothesis?: string;
    change?: string;
    generalises?: string;
  };
}

/** One version of the detector, as it scored when it actually ran.
 *  `showcase` is the same numbers narrowed to the one recording the walkthrough
 *  draws, so the chart and the counters cannot drift apart. */
export interface WalkStep {
  key: string;
  iteration: number;
  /** Alarms raised on each recording, in the order of `Walkthrough.channels`. */
  alarms_by_channel: number[];
  alarms: number;
  channels_firing: number;
  flagged_share: number;
  dev: SplitScore;
  holdout: SplitScore;
  showcase: {
    windows: { start: number; end: number; hit: boolean }[];
    caught: number;
  };
  matches_ledger: boolean;
}

export interface Walkthrough {
  showcase: {
    channel: string;
    n: number;
    truth: { start: number; end: number }[];
    /** Where the drawn recording sits in `channels`. */
    index: number;
  };
  channels: string[];
  steps: WalkStep[];
}

export interface Manifest {
  generated: string;
  commit: string;
  channels: ChannelSummary[];
  splits: Record<Split, SplitScore>;
  engine: {
    shipped: EngineConstants;
    baseline: EngineConstants;
    baseline_commit: string;
  };
  totals: {
    channels: number;
    briefs: number;
    severity: Record<string, number>;
    /** Windows that cover more than half, and almost all, of their recording. */
    wide: { over_half: number; almost_all: number };
    signature: Record<string, number>;
    shipped: { windows: number; channels_firing: number; flagged: number; samples: number };
    baseline: { windows: number; channels_firing: number; flagged: number; samples: number };
  };
  ledger: LedgerRow[];
  walkthrough: Walkthrough;
}
