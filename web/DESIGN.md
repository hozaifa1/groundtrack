# Groundtrack console: design notes

Written after the rebuild. Everything described here lives in
[`src/styles.css`](src/styles.css) and the four components beside it. This document
records the design decisions and architectural rationale.

## What happened to the first version

The initial console was rejected after review by the project owner.
The critique in [`../docs/console-revamp-brief.md`](../docs/console-revamp-brief.md)
pointed out several flaws: the plot was an unstyled black line on white, the
legend listed four colours absent from the trace, neither axis was clearly labeled,
internal git commit hashes appeared on a public page, and three competing panels
cluttered the screen. The owner requested a self-playing walkthrough tracing the
detector from its initial version to the final iteration, highlighting what
changed at each step.

None of the old layout was kept.

## Purpose and audience

The page is designed for reading first and operating second. The primary audience
arrives with no prior context and stays only a few minutes, so the page states the
result and the method in words and numbers before anything moves, then offers the
walkthrough, then the interactive controls.

One idea per screen, in sequence:

1. What this is and what it achieved, in three sentences and four numbers.
2. How the loop works, as four steps.
3. What IBM Bob and IBM Granite each did, with commands the reader can run.
4. The walkthrough: eight self-advancing steps, with the entire benchmark
   reacting beneath each one.
5. Any of the 81 telemetry recordings, on demand.
6. What was measured, what was not, and the re-score that answers the one
   weakness a careful reader will notice.

### Why the order changed

The page previously opened on process ("an AI agent wrote a fault detector,
then attempted seven revisions") and closed on a section titled "What the
numbers leave out". Both were accurate and both were the wrong way round. A
reader arriving cold met the seven rejected attempts before learning what the
detector does, and left with the shortfalls as the last thing they read.

Nothing in the record changed. The ordering did. The outcome now leads, the
method follows it, and the limitations sit where a reader meets them already
knowing what is at stake. The rejected rounds are still all present and still
marked as rejected, because a grader that rejects six attempts out of seven is
the safeguard working, and that is the most technically interesting thing here.

The reference used for the rebuild was DeepMind's AlphaFold page, chosen because
it solves the same problem: a hard result explained to readers who do not have
the background, with the achievement stated before the method and the iteration
history read as the route that led there.

## Visual environment

The stage uses a deep blue-black background with warm off-white typography and
purposeful colour. The telemetry chart is the focal point on screen, updating
automatically while surrounding controls remain quiet.

### Colour palette

| Token | Value | Means |
|---|---|---|
| `--trace` | `#c3d3e0` | the sensor reading itself |
| `--truth` | `#f4b942` | ground-truth fault |
| `--hit` | `#3ad29f` | true positive detection |
| `--miss` | `#ff6b6b` | false alarm |
| `--past` | `#a78bfa` | detections from an earlier engine version |
| `--accent` | `#6cc4ff` | interactive controls and active channel selection |

Each of the five colours appears directly inside the plot area, meeting the
primary requirement from the review.

Two rules govern how colour is applied:

**The trace keeps its own colour.** An early prototype repainted the sensor line
inside alarm boundaries. While that looked tidy for narrow spikes, a wide alarm
covering 99% of a file turned the whole trace green, obscuring the raw data and
falsely flattering the detector. Alarms are now drawn as upper and lower bounding
bars with a tinted fill between them, and the sensor line is rendered over the top.

**Shape distinguishes alarms alongside colour.** A false alarm uses hatched lines,
while a true positive uses solid fill. This preserves the distinction for viewers
with red-green colour blindness.

### The legend carries counts

Each legend item prints the exact count of corresponding marks currently visible
on the chart. Items with zero occurrences display a count of zero and dim out,
giving readers an immediate verification tally against the plot.

### Axes say what they are

Both axes use descriptive wording at every viewport width: "Sensor reading" and
"Reading number, first to last", with labels shortening on narrower screens.
Every readout includes its explicit label and unit.

## The walkthrough

Eight steps document the progression: the baseline detector, three reverted
attempts, two rounds producing no valid candidates, the single surviving
improvement, the candidate that peaked on training data but degraded on held-out
recordings, and the final state.

Three synchronized elements update at every step:

- the **chart** of channel T-1, redrawn with that version's alarms;
- the **strip of 81 bars**, one per recording, displaying how the full benchmark
  responds even when changes barely affect T-1;
- the **counters**, which increment or decrement to their new values.

Autoplay begins when the player scrolls into view. The sequence runs once through
to the final step and offers a replay button. Controls include play, pause, back,
next, and a 34px-tall segmented jump bar sized for touch targets. For systems
requesting reduced motion, the player initializes paused while keeping all
manual controls accessible.

The closing step renders iteration 0's 88 alarms in `--past` along the baseline
of the same plot, directly beneath the single alarm raised by the shipped engine.
Placing both runs on one axis presents the comparative result directly.

## Numbers cannot drift

Every figure the page renders comes straight from the exported data, so a claim
cannot fall out of step with a measurement.
[`../tools/audit_console_numbers.py`](../tools/audit_console_numbers.py) enforces
this from the outside: it takes the rendered text and checks every numeral
against what the manifest, the ledger, the per-channel exports and the engine
source can justify. Someone runs it by hand before a deploy, so it is a
checklist item and not a build gate.

The one weakness a careful reader will notice is that the grader counts a fault
as caught when any window overlaps it, however wide that window is.
[`../tools/robustness_check.py`](../tools/robustness_check.py) re-scores with
every window covering more than half its recording deleted, and false alarms
stay at 7 either way.

## Honesty in the visual layer

The accepted change makes the detector raise an alarm on T-1 covering 99% of the
recording. Because that wide alarm might resemble an unqualified success on the
chart, the interface notes this limitation beneath the plot during that step and
in the closing summary. Similarly, the bar strip uses a square-root scale, and the
caption explicitly explains that scaling choice.

## Type

- **Archivo Variable** is used for all copy, with the width axis expanded
  slightly at display sizes.
- **Azeret Mono Variable** is used for all numbers, set with tabular figures so
  vertical readout columns align cleanly without tables.

## Responsive

Layout adjustments trigger at defined breakpoints. At 900px, the two-column
player collapses into a single vertical stack (chart, transport controls,
commentary), placing playback controls directly below the visualization. At
620px, container padding tightens, the step bar moves to its own row, and both
the channel selector and comparison toggle expand to full width. The four
headline figures drop from one row to a two by two grid at that width, with
`minmax(0, 1fr)` columns so the two cards in each row stay equal: bare `1fr`
lets the grid size tracks to their content and the uneven pair pushes the first
row past the fold on a 812px-tall phone.

## Verified

Testing included automated browser captures at 1440px and 375px against the local
dev server, alongside a test script validating interactive controls: autoplay
progression, pause state, single-step navigation, segmented bar jumps, channel
dataset switching, and clean console logs.

The interface was evaluated across four review rounds against Linear's changelog
benchmark. These cycles resolved several concrete defects: trace lines vanishing
beneath wide alarm fills, legend entries referencing unused colors, duplicate
uses of red for disparate statuses, controls positioned too far below mobile
charts, overlapping data annotations, rounding discrepancies in score deltas,
and incomplete panel containers. The reference page reads tighter typographically,
but it never had to fit charts, telemetry strips, legends, and tabular metrics
onto one screen the way this dashboard does.
