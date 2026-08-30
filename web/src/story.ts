/** The words of the walkthrough. Every number it shows comes from the exported
 *  data instead, so a claim here can never drift away from a measurement. */

export type Verdict = "start" | "kept" | "dropped" | "none" | "final";

export interface Chapter {
  id: string;
  /** Which exported version supplies this chapter's chart and counters. */
  data: string;
  /** The version this attempt was trying to beat, for the arrows. */
  baseline: string | null;
  /** An earlier version whose alarms are drawn under this one for comparison. */
  ghost?: string;
  /** True when the round produced nothing the test could grade. */
  unscored?: boolean;
  eyebrow: string;
  title: string;
  body: string;
  verdict: Verdict;
  verdictText: string;
  /** How long the chapter holds before the player moves on. */
  seconds: number;
}

export const CHAPTERS: Chapter[] = [
  {
    id: "start",
    data: "start",
    baseline: null,
    eyebrow: "Where it started",
    title: "IBM Bob's first detector",
    body:
      "IBM Bob wrote both files in engine/ from scratch: a detector that models recent sensor behavior and triggers an alarm when a reading strays past a four-times cutoff. It catches most real faults. It also produces far more alarms than an operator can manage, and most point to nothing.",
    verdict: "start",
    verdictText: "The baseline every later round is measured against",
    seconds: 10,
  },
  {
    id: "round1",
    data: "round1",
    baseline: "start",
    eyebrow: "Round 1",
    title: "Ignore very short alarms",
    body:
      "Most false alarms lasted ten readings or fewer, while known real faults ran longer. Bob introduced a twelve-reading floor so an alarm required twelve consecutive points to count. Short false alarms disappeared. Several real faults on the hidden recordings also disappeared, because those anomalies were brief too. The training data had not revealed that pattern.",
    verdict: "dropped",
    verdictText: "Ruled out: alarm duration alone does not separate real faults from noise",
    seconds: 10,
  },
  {
    id: "round2",
    data: "round2",
    baseline: "start",
    eyebrow: "Round 2",
    title: "Raise the threshold slightly",
    body:
      "False alarms clustered on specific channels, repeatedly tripping just above the four-times cutoff. Bob raised the threshold to four and a half. Some noise cleared, but real faults sat closer to that boundary than expected. The detector missed four additional real faults compared to the baseline, while filtering less noise than round one.",
    verdict: "dropped",
    verdictText: "Ruled out: a higher cutoff misses real faults without removing enough noise",
    seconds: 10,
  },
  {
    id: "quiet",
    data: "start",
    baseline: null,
    unscored: true,
    eyebrow: "Rounds 3 and 4",
    title: "An audit trail that corrects itself",
    body:
      "Round three timed out before completing a version to grade. Round four ran into a harness issue: the runner detected untracked files in the workspace, attributed them to Bob, and rolled back an earlier change. Those files belonged to the operator, saved during the active run. The ledger documented the error alongside the correction. Bob's actual code change from that round was never scored.",
    verdict: "none",
    verdictText: "No change reached the grader in either round",
    seconds: 9,
  },
  {
    id: "round5",
    data: "round5",
    baseline: "start",
    eyebrow: "Round 5",
    title: "Compare each section to its recent history",
    body:
      "A handful of channels generated most false alarms when evaluated against a single global baseline for the entire recording. Bob adjusted the logic to judge each window against its recent history. Quiet segments received a tighter threshold, catching one more real fault than the baseline. When a channel stayed flat for long intervals, its baseline dropped too low. Total alarms across all recordings nearly doubled.",
    verdict: "dropped",
    verdictText: "Ruled out: local history breaks down when sensor activity stays flat",
    seconds: 10,
  },
  {
    id: "round6",
    data: "round6",
    baseline: "start",
    eyebrow: "Round 6",
    title: "Raise the threshold and merge nearby bursts",
    body:
      "Bob combined two targeted adjustments. He increased the threshold to six times normal wander, high enough that routine fluctuations rarely cross it. Because anomalies fluctuate, that high bar initially split continuous faults into brief fragments. Bob added a merge window so bursts within 150 readings merge into one event. Real faults reassembled into continuous alarms while noise dropped. Total alarms fell from 506 to 78, and the score more than doubled on recordings Bob had never seen.",
    verdict: "kept",
    verdictText: "Kept: the cutoff and merge window solve both sides of the problem",
    seconds: 13,
  },
  {
    id: "round7",
    data: "round7",
    baseline: "round6",
    eyebrow: "Round 7",
    title: "Judge by cumulative drift across the window",
    body:
      "The kept detector still missed gradual drifts that stayed below six times normal wander. Bob tracked cumulative drift across a sliding window to catch sustained low-level deviations. On visible training recordings, this achieved the highest score yet. On the twenty-six unseen recordings, the rule triggered too frequently and degraded performance. The harness retained round six.",
    verdict: "dropped",
    verdictText: "Rejected: strong results on training data failed to generalize to unseen test recordings",
    seconds: 13,
  },
  {
    id: "final",
    data: "round6",
    baseline: "start",
    ghost: "start",
    eyebrow: "Where it ended",
    title: "78 alarms, and most of them real",
    body:
      "Seven rounds followed the baseline, five reached the grader, and one survived. Across all 81 recordings, IBM Bob's final detector reduced total alarms from 506 to 78. On the 26 unseen recordings, false alarms dropped from 128 to 7, and the score rose from 0.266 to 0.623. Roughly three in four alarms now flag genuine issues, up from about one in six at the start. On this recording, both faults fall within one alarm that spans most of the timeline.",
    verdict: "final",
    verdictText: "One round in seven became the detector that shipped",
    seconds: 15,
  },
];
