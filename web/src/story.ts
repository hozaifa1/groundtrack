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
      "Bob works out what a sensor has been doing lately, then raises an alarm whenever a reading strays about four times further from that than the sensor normally wanders. It finds most of the real faults. It also fires constantly.",
    verdict: "start",
    verdictText: "The version everything else is measured against",
    seconds: 10,
  },
  {
    id: "round1",
    data: "round1",
    baseline: "start",
    eyebrow: "Round 1",
    title: "Ignore the very short alarms",
    body:
      "Most of the false alarms lasted only a handful of readings, so Bob made an alarm last at least twelve readings before it counted. The short false alarms went away, and so did real faults that happen to be short.",
    verdict: "dropped",
    verdictText: "Score fell. The change was undone",
    seconds: 10,
  },
  {
    id: "round2",
    data: "round2",
    baseline: "start",
    eyebrow: "Round 2",
    title: "Ask for a slightly bigger stray",
    body:
      "Same idea from the other side: a reading now had to stray four and a half times the usual wander instead of four. Fewer false alarms again, and four more real faults slipped past than the first version had missed.",
    verdict: "dropped",
    verdictText: "Score fell again, and again it was undone",
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
      "One run was cut off by a timeout before it finished. In the next one, a person saved unrelated files into the project folder while the run was going, the script that checks the work assumed Bob had written them, and it threw away a change that was fine. Both rounds are in the record, and the second one has a correction underneath it.",
    verdict: "none",
    verdictText: "The detector stayed exactly as it was",
    seconds: 9,
  },
  {
    id: "round5",
    data: "round5",
    baseline: "start",
    eyebrow: "Round 5",
    title: "Judge each stretch against its own neighbourhood",
    body:
      "A different idea. Bob measured how jumpy a recording is using a moving window, comparing each stretch only to its own recent history, so a calm passage would be judged against calm. It found one more real fault than the first version and nearly doubled the number of alarms.",
    verdict: "dropped",
    verdictText: "Third attempt, third time the score fell. Undone",
    seconds: 10,
  },
  {
    id: "round6",
    data: "round6",
    baseline: "start",
    eyebrow: "Round 6",
    title: "Raise the bar, and stop cutting one fault into many",
    body:
      "Two changes at once, and neither works alone. A reading now has to stray six times the usual wander, which on its own would throw away real faults, because a real fault crosses that line in bursts with calm gaps in between. So bursts within 150 readings of each other are now treated as one event. Together they take the alarm count down by a factor of six.",
    verdict: "kept",
    verdictText: "Score rose. This is the change that stayed",
    seconds: 13,
  },
  {
    id: "round7",
    data: "round7",
    baseline: "round6",
    eyebrow: "Round 7",
    title: "Judge by total drift instead of the worst moment",
    body:
      "Bob swapped the test itself: a stretch now qualifies by how far it strays added up over its whole length, so it catches long gentle drift but misses a brief, sharp blip. On the recordings Bob was allowed to study, this was the best result of the entire run. On the hidden ones it was worse, so the test threw it out.",
    verdict: "dropped",
    verdictText: "The score rose on the recordings Bob could study and fell on the hidden ones",
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
      "Seven attempts, one kept. Across all 81 recordings the detector now raises 78 alarms, down from 506, and on this recording it raises a single one that covers both real faults. That single alarm also stretches across almost the whole recording, which is the honest weakness of it: an alarm that wide counts as correct here while telling an operator very little about where to look.",
    verdict: "final",
    verdictText: "Both faults on this recording are inside one alarm",
    seconds: 15,
  },
];
