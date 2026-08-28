# Groundtrack console - design system

Written after the build, from the built world. Everything here is in
[`src/styles.css`](src/styles.css); this file explains why, not what.

## What this surface is

An **Operate** surface. Someone is doing a task: find a channel, see what the
engine called, decide whether it matters. It is also the artifact a competition
judge opens cold with three minutes to spend, so the first viewport has to make
the argument legible before anyone learns the controls.

Those two readers want the same thing, which is why there is no separate
marketing shell: the fastest way to convince the judge is to let them operate
the real console over real data.

## The world

**Diazo whiteprint.** Spacecraft engineering drawings were reproduced on a cool
grey-blue stock in blue-black ink. That is the ground here, and it is
deliberately *not* cream. "Light technical broadsheet" drifts toward warm paper,
a high-contrast display serif and a terracotta accent, which is the single most
common look for a generated page in this register. The width axis of a
grotesque, cool stock and a functional palette get to the same place without
arriving where every other page arrives.

### Colour is never decoration

Three voices, and no fourth. Nothing on this page is coloured to be interesting.

| Token | Value | Means | On paper |
|---|---|---|---|
| `--ink` | `#10161c` | text, and the telemetry trace itself | 15.8:1 |
| `--ink-2` | `#46525c` | every piece of secondary text | 6.9:1 |
| `--signal` | `#16436e` | **the engine said so** | 8.8:1 |
| `--truth` | `#2b3238` | **the label file said so** | 12.6:1 |
| `--alarm` | `#a32b1d` | a missed anomaly, or high severity | 6.3:1 |
| `--caution` | `#8a5b12` | medium severity | 5.0:1 |

Low severity gets no colour at all. Colour is spent on the things that change
what an operator does.

Strategy is **Restrained**, which is the floor for Operate and the right ceiling
here: the plot is the only large field of ink on the page, and it earns that by
being the content.

Light is locked, and there is no dark mode. That is a real cost for a
mission-ops tool and it was a decision, not an oversight: the world is a printed
engineering plate, and half of a printed plate is the paper.

### Type

Two families, both self-hosted, no system stack anywhere.

- **Archivo Variable** carries every word. Its width axis is doing the work:
  display sizes run at `font-stretch: 108-118%`, which reads as a technical
  publication rather than a magazine. The axis is driven through `font-stretch`
  rather than `font-variation-settings` so the CSS font-matching algorithm picks
  the face instead of being bypassed. Only `wdth.css` is imported, because that
  file carries both axes and adding `wght.css` ships a second copy of the font.
- **Azeret Mono Variable** carries every number, always `tabular-nums`, so a
  column of readouts aligns on the decimal without a table.

**The smallest type anywhere in this interface is 16px**, including SVG axis
ticks and field labels, which conventionally get 10 to 12. Every step above them
moved up to match. The reference this was benchmarked against sets body at 17px,
chart titles at 15px and labels at 14px; density here is bought with rules and
space instead.

| Token | px | Role |
|---|---|---|
| `--t-xs` | 16 | axis ticks, rail labels, the floor |
| `--t-sm` | 17 | field labels, captions |
| `--t-base` | 19 | index rows, controls, brief prose |
| `--t-md` | 21 | lead paragraph |
| `--t-lg` | 24 | readouts, detection titles |
| `--t-xl` | 30 | plate headings |
| `--t-2xl` | 44 | masthead figures |
| `--t-3xl` | 72 | channel identifier |

Fixed rem steps, never `clamp()`. Users view a tool at a consistent DPI, and a
heading that shrinks inside a narrow column looks worse, not more responsive.

### Structure is rules and space

There is **no `border-radius` and no `box-shadow` in the stylesheet**, and no
card. An engineering plate does not have them, and the moment one appears the
page becomes a dashboard. Grouping is done with hairlines (`--rule-faint`,
`--rule`, `--rule-strong`), a two-step paper tone, and space.

Explicitly refused, and worth naming because they are what the category ships by
default: pills and tinted capsules (severity is carried by the word's own colour
and weight), eyebrow labels above headings, section numbering, decorative status
dots, gradient text, glass, and any em dash.

### Browser surfaces

Selection, focus ring, scrollbars and numerals are themed from the palette
rather than left at browser defaults. This is the cheapest signal that a page was
built rather than assembled, and the one most reliably skipped.

## Composition

A three-column application shell at full viewport height, each column scrolling
alone.

```
masthead 96px          wordmark left, the three numbers that matter right
--------------------------------------------------------------------------
channel index  |  plate column               |  brief
264-312px      |  flexible                   |  384-472px
scrolls        |  scrolls                    |  scrolls
```

Selecting a channel is the leftmost thing on screen and never scrolls away.

### The rails, which are the whole argument

Under each plot, aligned to the same x-scale, sit stacked 22px rails. Each rail
is one source's assertion about the same timeline:

- **Labelled** - graphite where the benchmark says an anomaly is, oxide red
  where one was missed.
- **Engine** - solid Prussian blue where a detection landed on a labelled
  anomaly, hollow where it did not. Hollow reads as "asserted, unsupported",
  which is exactly what a false positive is.
- **Iteration 0** - optional third rail, the engine as IBM Bob first wrote it,
  executed out of git rather than reimplemented.

Shading the plot area in two overlapping colours would have been the obvious
move and would have gone muddy. Separate rails on a shared axis stay readable at
any density, and they are why turning on the comparison is legible instantly:
on channel T-1 the engine's rail holds **1** mark and iteration 0's holds **88**,
above a Labelled rail of 2 that both of them catch.

### Motion

One authored moment: opening a detection eases the plot's x-domain from the
whole pass down to that window plus context, 420ms on an exponential ease-out.
It conveys a state transition and preserves the window's position in the
channel, which a cut would destroy. Everything else is 120-160ms on colour.
`prefers-reduced-motion` collapses all of it.

## Responsive

Structural, never fluid. Type sizes do not shrink; columns stack.

- **1400px** - index and brief narrow.
- **1180px** - brief moves below the plate column, full width.
- **860px** - single column; the masthead wraps and the index caps at 18rem.
- **Plot below 500px** - rail labels move above their rails and the axis gutter
  drops from 124px to 54px, because a 124px gutter is a third of a phone.

## Verified, and not

Measured in the live DOM: no element renders below 16px; no `border-radius`
anywhere; no em dash in any rendered string; no horizontal overflow at 1280 or
540; every text/background pair passes WCAG AA; no tap target under 40px; the
impeccable mechanical detector returns clean, though in degraded mode, which is
an undercount.

**Not verified in this session**: the browser pane could not composite, so there
are no screenshots and the sub-500px plot layout was never exercised live. Those
need a human eye before this is called finished.
