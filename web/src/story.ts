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
      "IBM Bob wrote both files in engine/ from scratch: a detector that learns how each sensor has been behaving lately, then raises an alarm whenever a reading strays about four times further than that. It catches most real faults. It also raises far more alarms than an operator could act on, and most of them point at nothing.",
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
      "Most false alarms lasted ten readings or fewer, and every known real fault ran far longer, so Bob set a floor: an alarm needed twelve readings to count. Short false alarms disappeared. So did several real faults on the hidden recordings, which turned out to be short too, a pattern invisible in the data Bob had to train on.",
    verdict: "dropped",
    verdictText: "Ruled out: alarm length alone doesn't separate real faults from noise",
    seconds: 10,
  },
  {
    id: "round2",
    data: "round2",
    baseline: "start",
    eyebrow: "Round 2",
    title: "Raise the threshold slightly",
    body:
      "False alarms clustered on a few channels, all triggering just above the four-times cutoff. Bob raised the cutoff itself, to four and a half. Some noise dropped, but real faults sit closer to that line than the theory predicted. The detector missed four more real faults than the first version, while cutting less noise than round one already had.",
    verdict: "dropped",
    verdictText: "Ruled out: a higher cutoff costs more real faults than it saves in noise",
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
      "Round three ran out of time before it produced anything to grade. Round four looked worse at first: the harness found new files in the project folder and blamed Bob for them, reverting a change it had already paid for. Those files were the operator's, saved into the repo while the run was still going, and had nothing to do with Bob. The ledger records the mistake next to the correction. Bob's actual change from that round was never scored either way.",
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
      "A handful of channels were driving most of the false alarms, each judged against one number for what counts as normal across the whole recording. Bob's fix: judge each stretch against its own recent history instead. Quiet periods got a tighter bar, and the detector caught one more real fault than the first version. But when a channel sat still for a while, its recent history looked calm too, and the bar fell with it. Total alarms across all recordings nearly doubled.",
    verdict: "dropped",
    verdictText: "Ruled out: local history helps until the history itself goes quiet",
    seconds: 10,
  },
  {
    id: "round6",
    data: "round6",
    baseline: "start",
    eyebrow: "Round 6",
    title: "Raise the threshold and merge nearby bursts",
    body:
      "This time two changes moved together. Bob raised the cutoff to six times normal wander, high enough that ordinary variation almost never crosses it. Alone, that would have shattered real faults into scattered fragments, since a real anomaly rarely stays above six the whole way through. So Bob also widened the merge window: bursts within 150 readings of each other now count as one event. Real faults reassemble into a single alarm. Noise mostly disappears. Total alarms fell from 506 to 78, and the score more than doubled on recordings Bob had never seen.",
    verdict: "kept",
    verdictText: "Kept: the cutoff and the merge window solve two halves of one problem",
    seconds: 13,
  },
  {
    id: "round7",
    data: "round7",
    baseline: "round6",
    eyebrow: "Round 7",
    title: "Judge by cumulative drift across the window",
    body:
      "The kept detector still missed slow, moderate drifts that never spike past six times normal wander. Bob tried scoring the total drift added up across a window instead of its single highest point. On the recordings Bob could see, this was the best score yet. On the twenty-six it had never seen, the same rule fired too often and the score fell. The harness kept round six instead.",
    verdict: "dropped",
    verdictText: "Rejected: the best score yet on visible data, but it didn't hold on the hidden set",
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
      "Seven attempts went to the grader. One survived. Across all 81 recordings, IBM Bob's final detector cut alarms from 506 to 78. On the 26 recordings it never trained on, false alarms fell from 128 to 7, and the score rose from 0.266 to 0.623. Roughly three in four alarms now point at something real, up from about one in six at the start. On this recording, both faults sit inside a single alarm, though that alarm spans most of the timeline.",
    verdict: "final",
    verdictText: "One round in seven became the detector that shipped",
    seconds: 15,
  },
];
