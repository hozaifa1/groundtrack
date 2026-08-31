# Groundtrack: 3-Minute Video Presentation Script

**Challenge Theme:** Advance Space Exploration with AI (AI Builders Challenge with IBM Bob)  
**Submission Deadline:** August 31, 2026 at 11:59 PM ET (September 1, 09:59 AM Asia/Dhaka)  
**Live Prototype:** [groundtrack-console.vercel.app](https://groundtrack-console.vercel.app)  
**GitHub Repository:** [github.com/hozaifa1/groundtrack](https://github.com/hozaifa1/groundtrack)  
**Interactive Shoot Sheet / Teleprompter:** [docs/groundtrack-shoot.html](file:///f:/Projects/ibm-bob-challenge/docs/groundtrack-shoot.html)

---

## 3-Minute Script & Shot List

*Target timing: 2m 45s to 2m 55s (approx. 410 spoken words at 140 words/minute).*  
*Slashes (`/`) indicate natural breath pauses. Italic words mark spoken emphasis.*

### Shot 1 [0:00 to 0:14] | Terminal: Git Provenance Proof
- **Visual:** Full screen terminal. Type provenance command live and let the three commit lines settle.
- **Spoken Line:**
  > Here is the git history of a spacecraft fault detector, and of the script that grades it.  
  > / One commit is mine, from *August twenty-second*: the grader. *IBM Bob* wrote every line of the detector after that.  
  > / Bob was *never allowed to read that grader*.
- **Director Note:** Open cold on the terminal. No title cards or logos. Let the three dated lines sit on screen in silence for one beat.

### Shot 2 [0:14 to 0:25] | Browser: Console Hero & Stat Cards
- **Visual:** Alt-Tab to the web console. Show hero headline and four stat cards without scrolling.
- **Spoken Line:**
  > This is *Groundtrack*. I had IBM Bob write the detector. I then made sure *neither of us* could be the one who tells you it worked.
- **Director Note:** This is the central point. Speak steadily through "neither of us" and pause briefly before scrolling.

### Shot 3 [0:25 to 0:41] | Browser: Benchmark Overview
- **Visual:** Scroll down to the 81-recording benchmark overview.
- **Spoken Line:**
  > It runs on NASA's Telemanom benchmark. This consists of *eighty-one telemetry recordings* from the SMAP satellite and the Curiosity rover, with faults labelled by mission engineers.  
  > / It is built for the three or four people running a CubeSat program off a runbook nobody has revalidated since launch.

### Shot 4 [0:41 to 1:00] | Browser: Sealed Grader Architecture
- **Visual:** Display the four-step workflow diagram on the console.
- **Spoken Line:**
  > The grader holds back *twenty-six* of those recordings. Bob never sees them and cannot read the metric.  
  > / Bob proposes a change and commits it. Only then does the sealed grader score it on telemetry Bob has never seen.  
  > / When the score goes up, the change stays. When the score goes down, it reverts automatically.

### Shot 5 [1:00 to 1:32] | Browser: Walkthrough of Iterations
- **Visual:** In the walkthrough section, click Step 1 (baseline), Step 6 (accepted iteration), Step 7 (reverted peak test), then Step 8.
- **Spoken Line:**
  > Eight rounds ran. The grader kept *exactly one*.  
  > / Here is Bob's first detector: five hundred and six alarms across all eighty-one recordings.  
  > / Here is the round the grader kept.  
  > / And here is the round it threw away: Bob's highest score ever on the data it could see, and lower on the data it could not. It reverted automatically. Nobody asked me.
- **Director Note:** Click each step deliberately so charts update alongside your voice.

### Shot 6 [1:32 to 1:54] | Browser: Final Metric Results
- **Visual:** Final step in the walkthrough as counters settle.
- **Spoken Line:**
  > What ships raises *seventy-eight* alarms. On the twenty-six held-out recordings, false alarms fell from a hundred and twenty-eight to *seven*.  
  > / Three in four alarms are real now. It used to be one in six.  
  > / Six real faults traded for a hundred and twenty-one fewer false ones.
- **Director Note:** Deliver the trade plainly as an engineering choice. Do not apologize for the recall shift.

### Shot 7 [1:54 to 2:08] | GitHub / Browser: Generalization Finding *(Optional Cut if Rehearsal > 2:45)*
- **Visual:** Show `docs/generalisation.md` or generalisation stats.
- **Spoken Line:**
  > Tuning against what the agent could see has no benefit. Across four hundred and thirty-two configurations, the two scores are uncorrelated.  
  > / So I stopped, with twenty-eight Bobcoins unspent.
- **Director Note:** Cut this block first if you exceed 2:50 in rehearsal.

### Shot 8 [2:08 to 2:30] | Browser: IBM Granite Operator Briefs
- **Visual:** Scroll to recording explorer, click an alarm (e.g. T-1), and expand the Granite operator brief.
- **Spoken Line:**
  > Finding the alarm is half the job. Telling a tired engineer what to do about it counts for just as much.  
  > / *IBM Granite* runs locally on this laptop's CPU and briefs *every one* of the seventy-eight alarms.  
  > / Nothing is hand-edited. Every number is audited back to the telemetry.
- **Director Note:** Allow the brief panel to open before naming IBM Granite.

### Shot 9 [2:30 to 2:55] | Terminal: Live Verification & Closing
- **Visual:** Alt-Tab back to terminal. Run author check command, then run the scorer.
- **Spoken Line:**
  > The console is static. It has no backend and no API key. You do not have to believe any of it.  
  > / Check git for the engine author: it returns one name.  
  > / Run the scorer: *0.622951*, the number you just watched.  
  > / You can also run the forty-five harness tests, including the one that catches edits to the grader.  
  > / *Other submissions ask you to trust the pitch. This one hands you the commands.*
- **Director Note:** Land the final sentence firmly. Leave the terminal on screen for two seconds in silence, then stop recording.

---

## On-Camera Terminal Commands

```bash
# 1. Opening provenance check (0.2s runtime)
git log --format="%ad  %<(9)%an  %<(34,trunc)%s" --date=short -- tools/score.py engine/*.py | sort

# 2. Author verification (instant)
git log --format='%an' -- 'engine/*.py' | sort -u
# Output: IBM Bob

# 3. Live scorer pass (4s runtime)
.venv/Scripts/python.exe tools/score.py
# Output: GATE METRIC (holdout F1): 0.622951
```

---

## Technical Defense & Q&A Prep

- **Did IBM Bob find the parameters, or did you?**  
  An offline parameter search on the development split identified the two numerical constants. Bob authored the engine code and its internal reasoning. The held-out grader evaluated the final output. This is documented in `README.md` and `docs/parameter-search.md`.
- **Is a held-out split not standard ML practice?**  
  Data splits are standard in model training. In Groundtrack, the split governs an autonomous coding agent's revisions. Bob writes code changes but cannot access the evaluation dataset or metric. Across 432 configurations, visible development scores and holdout scores showed zero correlation. This shows that optimizing on visible data alone degrades generalization.
- **Recall dropped from 25 to 19. Why is this preferable?**  
  On the held-out recordings, 19 of 35 faults are detected while false alarms dropped from 128 to 7. Removing 121 false alarms prevents alarm fatigue for a small operations team triaging alerts manually. Operators needing higher recall can adjust the two constants in `engine/detect.py` using the included search scripts.
- **How do judges verify no human edited Bob's code?**  
  `git log --format='%an' -- 'engine/*.py'` returns only IBM Bob. `git diff 9cc792e -- 'engine/*.py'` is empty.
