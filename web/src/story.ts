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
    title: "The first detector",
    body:
      "Bob works out what a sensor has been doing lately, then raises an alarm whenever a reading strays about four times further than normal. It catches most real faults, but it also fires constantly.",
    verdict: "start",
    verdictText: "The baseline version everything else is measured against",
    seconds: 10,
  },
  {
    id: "round1",
    data: "round1",
    baseline: "start",
    eyebrow: "Round 1",
    title: "Ignore very short alarms",
    body:
      "Most false alarms lasted only a few readings, so Bob required alarms to last at least twelve readings before counting. The brief false alarms went away, along with real faults that happened to be short.",
    verdict: "dropped",
    verdictText: "The score fell, so the change was undone",
    seconds: 10,
  },
  {
    id: "round2",
    data: "round2",
    baseline: "start",
    eyebrow: "Round 2",
    title: "Raise the threshold slightly",
    body:
      "Trying another angle, a reading now had to stray four and a half times the usual wander instead of four. That cut false alarms further, though four more real faults slipped past than in the first version.",
    verdict: "dropped",
    verdictText: "The score fell again, and the change was undone",
    seconds: 10,
  },
  {
    id: "quiet",
    data: "start",
    baseline: null,
    unscored: true,
    eyebrow: "Rounds 3 and 4",
    title: "Nothing to grade",
    body:
      "One run timed out before finishing. In the next, someone saved unrelated files into the project folder while the run was going. The grading script assumed Bob had written them and threw away a valid change. Both rounds stay in the record, with a correction note logged under the second.",
    verdict: "none",
    verdictText: "The detector stayed exactly as it was",
    seconds: 9,
  },
  {
    id: "round5",
    data: "round5",
    baseline: "start",
    eyebrow: "Round 5",
    title: "Compare each section to its recent history",
    body:
      "Bob measured variance across a moving window, comparing each stretch to its recent behavior so calm passages were judged against calm baselines. The detector found one more real fault than the first version, but nearly doubled the number of alarms.",
    verdict: "dropped",
    verdictText: "Score fell on evaluation. The change was undone",
    seconds: 10,
  },
  {
    id: "round6",
    data: "round6",
    baseline: "start",
    eyebrow: "Round 6",
    title: "Raise the threshold and merge nearby bursts",
    body:
      "Bob combined two adjustments. Readings had to stray six times the usual wander. Because real faults trigger in intermittent bursts with calm gaps, bursts within 150 readings of each other were merged into a single event. Together, these changes cut total alarms down by a factor of six.",
    verdict: "kept",
    verdictText: "Score rose. This change was kept",
    seconds: 13,
  },
  {
    id: "round7",
    data: "round7",
    baseline: "round6",
    eyebrow: "Round 7",
    title: "Judge by cumulative drift across the window",
    body:
      "Bob adjusted the detector to sum total drift across the entire window. This caught gradual drift, though it missed brief spikes. The approach produced the highest score on the training recordings, but score fell on the hidden test set, so the harness rejected it.",
    verdict: "dropped",
    verdictText: "Score rose on training recordings and fell on the hidden set",
    seconds: 13,
  },
  {
    id: "final",
    data: "round6",
    baseline: "start",
    ghost: "start",
    eyebrow: "Where it ended",
    title: "78 alarms, down from 506",
    body:
      "Out of seven attempts, only one change was kept. Across all 81 recordings the detector raised 78 alarms, down from 506. On this recording it raised a single alarm covering both real faults. The alarm spans most of the recording, which counts as a detection here while offering operators limited precision on where to look.",
    verdict: "final",
    verdictText: "Both faults on this recording fall inside one alarm",
    seconds: 15,
  },
];
