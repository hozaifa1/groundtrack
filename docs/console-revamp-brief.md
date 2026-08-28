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

- The plot renders as **a black line on a white background** and nothing else.
- The legend advertises four colours (labelled, missed, detection, false alarm)
  and **none of those colours appear anywhere in the chart the reader is looking
  at**. They live in thin 22px "rails" below the plot that nobody connects to it.
- **Put the colour inside the plot area, on and around the trace itself.** Shade
  the anomaly regions. Mark the detections where they actually sit on the line.
  If a legend names a colour, that exact colour must be plainly visible in the
  graphic next to it.
- The marks are clickable but nothing signals that. If something is interactive,
  it has to look interactive.

## 2. The axes are unexplained

Nothing says what the x-axis or the y-axis mean. Label them in plain language, for
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
| "commit 27577fe" and any other git hash | **A git commit hash has no business on a website.** Remove every one. |
| "Day 2", "Day 5", "Day 6 of 9" | The build schedule is not content. Remove every reference. |
| "Bobcoins", "cost cap hit", "guardrail stop", "ledger correction" | Internal vocabulary. |
| "level shift: sustained displacement from baseline" | Write it the way a person would say it. |

Rule of thumb: if a sentence needs the reader to already know the project, rewrite
it or cut it.

## 4. There is far too much on one screen

Left panel, centre column, right panel, plus oversized figures across the top, plus
two separate graphs stacked. It is overwhelming and none of it is prioritised.
Reduce to one clear thing at a time. One idea per screen.

## 5. What the owner actually asked for instead

> "I think it would be better if you showed like a video kind thing that would
> just automatically move from one to the other to show the steps regarding what
> was done with the graphs and the scores and accuracy and so on. Just it would
> automatically move from step zero all the way to the final step autonomously and
> just show the user what changed and all of that very slowly one after the other
> like a visual flow completely."

**Make this the centrepiece of the new console.** An autoplaying, narrated visual
walkthrough that starts at the very first version of the detector and advances by
itself, slowly, one step at a time, to the final one. At each step it shows:

- what changed, in one plain sentence;
- the same chart redrawn so the change is visible as a change;
- how the accuracy moved, and whether the change was kept or thrown away.

The single most important beat: the first detector fired **506** times across the
data; the final one fires **78** and still catches the real events. On channel T-1
alone the first version raised **88** alarms and the final one raises **1**, and
that 1 still catches both real anomalies. Land that visually, not in prose.

Second beat worth showing: one round *looked* like an improvement on the data the
agent could see and got worse on the data it could not, so it was thrown away
automatically. That is the honest, interesting part of the story.

Give the reader play, pause, and the ability to step back and forth. Autoplay is
the default, but it must never be a prison.

## 6. Make it visually appealing

The owner's assessment was that none of it is. Whatever the new direction is, it
has to look considered and inviting rather than like an instrument readout.

## Constraints that still hold

- Every number on screen must remain true to `results/` and the exported data.
  Simplifying the language must not soften or inflate a result.
- The page stays static: no backend, no model calls at runtime.
- The runbook wording is illustrative, not certified NASA doctrine, and must not
  be presented as official.
- Verify with real screenshots at desktop and mobile before declaring it done.
