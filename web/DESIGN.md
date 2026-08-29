# Groundtrack console - design notes

Written after the rebuild. Everything described here is in
[`src/styles.css`](src/styles.css) and the four components beside it; this file
explains why, not what.

## What happened to the first version

A console shipped, was shown to the project owner, and was rejected outright.
The review is written down in [`../docs/console-revamp-brief.md`](../docs/console-revamp-brief.md)
and it is specific: the plot was a black line on white with no colour in it, the
legend named four colours that appeared nowhere near the trace, neither axis said
what it meant, git commit hashes and build-day references were on a public page,
and three competing panels fought for one screen. What the owner asked for
instead was a walkthrough that plays by itself from the first version of the
detector to the last, showing at each step what changed and whether it survived.

None of the old design is preserved. This is a different page.

## What this surface is

A **read** surface first and an **operate** surface second, in that order,
because the reader who matters most arrives knowing nothing about the project and
leaves after a few minutes. So the page opens on a story that runs on its own,
and only then offers the controls for looking around.

One idea per screen, in sequence:

1. What this is, in one paragraph.
2. The walkthrough. Eight steps, self advancing, with the whole benchmark
   reacting underneath each one.
3. Any of the 81 recordings, on demand.
4. What the numbers leave out.

## The world

Deep blue-black stage, warm off-white type, and colour spent only on meaning. The
page is closer to a film than to an instrument: the chart is the largest object
on screen, it changes on its own, and everything around it is quiet enough to let
that read.

### Colour is never decoration

| Token | Value | Means |
|---|---|---|
| `--trace` | `#c3d3e0` | the sensor reading itself, always this colour |
| `--truth` | `#f4b942` | a fault that really happened |
| `--hit` | `#3ad29f` | an alarm with a real fault under it |
| `--miss` | `#ff6b6b` | an alarm with nothing under it |
| `--past` | `#a78bfa` | what an earlier version of the detector flagged |
| `--accent` | `#6cc4ff` | controls, links, the recording being drawn |

Five meanings, five colours, and no sixth. Every one of them appears inside the
plot area rather than only in a legend, which was the first thing the review
asked for.

Two rules follow from it and are worth stating because both were learned the hard
way in this rebuild:

**The trace keeps its own colour, always.** An intermediate version repainted the
line inside each alarm. That reads beautifully for eighty narrow alarms and fails
completely for the one alarm that covers 99% of the recording: the whole trace
turns green, the legend's "the sensor reading" points at nothing, and the picture
quietly flatters the result. Alarms are now drawn as a bar along the top and the
bottom of the plot with a wash between them, and the line is drawn last, over the
top of all of it.

**Red and green are never the only difference between two marks.** A false alarm
is hatched, a true one is solid. The distinction that matters most in the whole
figure survives a reader who cannot tell those two hues apart.

### The legend carries counts

Each legend entry prints how many of that mark are on the chart in front of you,
and an entry with nothing to point at says zero and dims rather than silently
promising a colour that is not there. This is the direct answer to the review's
complaint, and it turns the legend into something a sceptical reader can check
against the picture.

### Axes say what they are

"Sensor reading" and "Reading number, first to last", in words, at every width,
shortened rather than clipped on a phone. No bare unit, no bare number.

## The walkthrough

Eight steps: the first detector, three attempts that were undone, two rounds that
produced nothing to grade, the change that survived, the attempt that scored best
on the recordings the agent could study and lost on the hidden ones, and the
ending.

Three things change at every step, which is what makes it read as motion rather
than as eight screenshots:

- the **chart** of channel T-1, redrawn with that version's alarms;
- the **strip of 81 bars**, one per recording, which is where the rounds that
  barely touch T-1 are visible at all: the whole benchmark reacts to every
  attempt;
- the **counters**, which count up or down to their new values.

Autoplay is the default and starts when the player is actually on screen, so the
story is not half over by the time someone scrolls to it. It never loops; it
stops at the end and offers to play again. Play, pause, back, next and a
segmented bar that jumps to any step are always present, and the bar's segments
are 34px tall so a thumb can hit them. Anyone whose system asks for less motion
gets the player paused, with everything still reachable by hand.

The closing step draws iteration 0's 88 alarms in `--past` along the floor of the
same plot, under the single alarm the shipped engine raises. That comparison on
one axis is the strongest fact in the project, and it is the one frame where the
page shows it rather than saying it.

## Honesty in the visual layer

The kept change makes the detector raise one alarm on T-1 that covers 99% of the
recording. That is a real weakness and the chart makes it look like a triumph, so
the page says so under the chart, on the step where it happens, and again in the
closing text. Same for the bar strip: it uses a square root scale, and the
caption says so and says what that means.

## Type

- **Archivo Variable** for every word, width axis pushed slightly wide at display
  sizes.
- **Azeret Mono Variable** for every number, tabular, so a column of readouts
  aligns without a table.

## Responsive

Structural, not fluid. At 900px the player's two columns dissolve: the chart, the
transport and the words stack in that order, so the controls sit directly under
the chart they drive instead of a full screen below it. At 620px the shell's
padding tightens, the step bar takes its own row, and the picker and comparison
toggle go full width.

## Verified

Real screenshots at 1440px and at 375px, taken from the running dev server
through a headless browser, plus a scripted pass over the controls: autoplay
advances on its own, pause holds, back and next move one step, the segmented bar
jumps, switching recordings loads a different channel's JSON and redraws, and the
console logs no errors on any of it.

Judged against Linear's changelog as a bar for narrated visual reveals, by
separate critics per piece, over four rounds. What that loop fixed: the trace
disappearing under a wide alarm, a legend promising colours the chart did not
have, red being used for two unrelated meanings, controls stranded a screen away
from the chart on a phone, an annotation printed on top of the data, a score
whose rounded delta did not add up to its rounded values, and a panel with a hole
in it. What it did not close: the reference page still wins on pure typographic
restraint, which is easier to achieve on a page carrying one column of prose than
on one carrying a chart, a strip, a legend and a readout column at once.
