# 01 — University CubeSat and ground-station teams

**Subject:** 15 minutes: does an anomaly runbook actually go stale on your mission?

---

Hi <name>,

I'm Hozaifa, a final-semester EEE student at the University of Dhaka. I've built
something for a small-team mission-ops problem and I'd rather find out from you that
I've got the problem wrong than find out from a judge.

The assumption I built on: a CubeSat team writes an anomaly-response runbook around
commissioning, mapping telemetry signatures to corrective actions — and then almost
never revalidates it against real flight data, because doing that means replaying
months of telemetry against the current rules and patching what missed. Unglamorous,
always deferrable, and a four-person team with theses and a semester will defer it.

What I built is a detector that gets re-tuned automatically against labelled NASA
telemetry (SMAP and MSL, from the Telemanom benchmark), with an IBM Granite model
turning each detection into a plain-language brief. An agent proposes one change at a
time, a fixed scorer it cannot edit decides whether the change survives, and every
attempt is logged — including the ones that made it worse, which so far is most of them.

**The ask is one question, and I'd be glad of a one-sentence answer:**
looking at a two-minute recording, would something like this have saved <team> time —
or is the runbook-goes-stale problem just not real on your mission?

A "no, that isn't our problem" is genuinely useful to me and I'll say so publicly.
I'm not asking for data, a meeting, or a partnership.

Recording: <link>
Code and the full log of what the agent tried: <repo link>

Thanks for reading either way.

Hozaifa
Dept. of Electrical & Electronic Engineering, University of Dhaka
<email>

---

## Notes for sending

- Replace `<team>` with the actual mission name, and say something specific about it in
  the first line if you can. A visibly templated email gets the reply rate it deserves.
- Target teams that have actually flown, not ones still in design. The question is
  about operations, and a team that has not operated has nothing to tell you.
- Good hunting grounds: university CubeSat programme pages, the AMSAT and SatNOGS
  communities, IARU frequency-coordination filings (they list a contact per mission),
  and ground-station clubs.
- If the recording is not ready, do not send. The email promises it.
