# Console revamp brief

The first console shipped on day 6 was rejected by the project owner. This file is
the correction, written from their review, so the rebuild has one place to work from.

Their words, in substance: *"horrifyingly bad"*, *"no human being will be able to
read any of these"*, *"nobody would get any of this"*, *"the screen is completely
not user friendly at all"*.

Take that at face value. Do not defend the old design or preserve parts of it out
of politeness. Rebuild so that a person who knows nothing about this project
understands what they are looking at within ten seconds.

---

## 1. The charts do not communicate anything

- The plot renders as a black line on a white background and nothing else.
- The legend advertises four colours (labelled, missed, detection, false alarm)
  and none of those colours appear anywhere in the chart the reader is looking
  at. They live in thin 22px "rails" below the plot that nobody connects to the
  graph.
- Put the colour inside the plot area, on and around the trace itself. Shade
  the anomaly regions. Mark the detections where they actually sit on the line.
  If a legend names a colour, that exact colour must be plainly visible in the
  graphic next to it.
- The marks are clickable but nothing signals that. If something is interactive,
  it has to look interactive.

## 2. The axes are unexplained

Nothing explains what the axes mean. Label them in plain language, for
example "Time through the recording" and "Sensor reading". Never leave a bare
number or a bare unit for the reader to decode.

## 3. Delete the jargon

Every one of these has to go or be rewritten in ordinary English:

| Currently on screen | Problem |
|---|---|
| "Operator brief" | Nobody knows what this means. |
| "A fixed benchmark it cannot reach decides whether it was any good." | Unparseable. |
| "held-out F1", "dev / holdout split" | Statistics jargon shown without explanation. |
| "sigma", "7.7 σ" | Never defined for the reader. |
| "commit 27577fe" and any other git hash | A git commit hash has no business on a website. Remove every one. |
| "Day 2", "Day 5", "Day 6 of 9" | The build schedule is not content. Remove every reference. |
| "Bobcoins", "cost cap hit", "guardrail stop", "ledger correction" | Internal vocabulary. |
| "level shift: sustained displacement from baseline" | Write it the way a person would say it. |

Rule of thumb: if a sentence needs the reader to already know the project, rewrite
it or cut it.

## 4. There is far too much on one screen

The current layout packs a left panel, center column, right panel, oversized top stats,
and two stacked graphs into a single view. That overwhelms the viewer. Show one
clear concept at a time, with a single focus per screen.

## 5. What the owner actually asked for instead

> "I think it would be better if you showed like a video kind thing that would
> just automatically move from one to the other to show the steps regarding what
> was done with the graphs and the scores and accuracy and so on. Just it would
> automatically move from step zero all the way to the final step autonomously and
> just show the user what changed and all of that very slowly one after the other
> like a visual flow completely."

Make this the center of the new console: an autoplaying visual walkthrough that
starts at the initial baseline detector and advances step by step to the final version.
At each step it shows:

- what changed, in one plain sentence;
- the telemetry chart redrawn so the change is clearly visible;
- how accuracy shifted, and whether the engine kept or discarded the iteration.

The primary milestone: the first detector fired 506 times across the dataset; the
final version fires 78 times and still catches genuine events. On channel T-1 alone,
the initial version raised 88 alarms, whereas the final version raises 1 alarm that
still catches both anomalies. Present this progression visually on the chart.

One iteration looked like an improvement on the training data but regressed on held-out channels, so the harness discarded it automatically. Include that safeguard in the story.

Provide play, pause, and step controls. Autoplay runs by default, while letting the
user inspect individual steps at their own pace.

## 6. Make it visually appealing

The feedback indicated that the existing interface lacks polish. The revamp must drop the dense telemetry readouts and present a clean layout.

## Constraints that still hold

- Every number on screen must match `results/` and the exported dataset. Simplifying
  the language must not alter any result.
- The page remains static, with no backend services or runtime model calls.
- The runbook text is illustrative and must not be presented as certified NASA doctrine.
- Verify with real screenshots on desktop and mobile viewports before completion.
