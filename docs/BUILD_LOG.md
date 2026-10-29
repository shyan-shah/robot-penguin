# Overnight build log

Everything that happened, in order, including the things that went wrong — which
is most of what is worth reading. Numbers are measured, not estimated; where
something is an assumption it says so.

---

## 0. Where it started

A finished CAD model: 15 printed parts, 26 components, every sketch fully
constrained, every dimension driven by a shared spreadsheet. Interference-free at
the neutral pose. Three things were outstanding — the joints were rigid, there was
no `.ipn` exploded view, and the DF2301Q voice board did not fit in the head.

---

## 1. Articulating the joints

### What the geometry decided

The joints were not designed by me; they were read off the existing model. Every
moving part's pivot was found by looking for cylindrical faces and taking their
axes:

| Joint | Axis | Location | Motion |
|---|---|---|---|
| Hip | Z (vertical) | X ±26, Y 0 | yaw — twists the foot, does **not** swing the leg |
| Ankle | Y (fore-aft) | X ±26, Z −40 | roll — leans the body sideways |
| Flipper | X (lateral) | Y 0, Z 78 | flap, 270° of travel |
| Beak | X (lateral) | Y 31, Z 131 | lower mandible, 0–30° |

Hip yaw plus ankle roll is a genuine waddle mechanism: roll lifts a foot, yaw
steers it. There is **no pitch axis anywhere in the robot**, which is why it can
never bow, lean forward, or take a stride — a fact that shapes everything below.

### How the joints are built

Each moving part got a work axis built as the intersection of two parametric work
planes, so the joint tracks `hip_x` / `Z_ankle` / `Z_flip` instead of sitting at a
typed-in location. All six landed exactly on the cylinder axes of the real horn
bores. The reference axes live in the **parent part** (`base_plate` for hips,
`core_frame` for flippers) because Inventor refuses to offset an assembly's own
origin planes.

Each joint is three constraints chosen so there is no redundancy: an axis mate
(4 DOF), an origin-point-on-plane mate to kill the slide (1 DOF), and an angle
constraint — the joint itself.

### Three bugs found while doing it

**1. The ankle servos got left behind, then flipped.** They were grounded, so
yawing a hip walked the leg out from around them. Attaching them with three flush
constraints matched like-plane to like-plane, which put them in 180° rotated — a
421 mm³ clash. The dummy actually sits rotated 180° about the (0,1,1) diagonal, so
the correct attachment is servo-YZ→leg-YZ as a *mate* and the other two as
flushes to *different* planes.

**2. The angle constraints could flip 180°.** After driving the hips to ±90° to
test recovery, `FOOT_R` came back at Y −37…18 instead of −18…37 — the toes were
pointing backwards, and the ankle ±25° pose that had been clear now showed a
1027 mm³ clash. A plane-to-plane angle constraint has a ±180° ambiguity and the
solver had snapped to the other branch. Fixed by rebuilding all seven joints with
`SolutionType = 78594` (directed angle), which removes the ambiguity. This is a
latent-defect class, not a one-off: an undirected angle constraint can flip at any
time.

**3. `MirrorFeatures.Add` fails for anything sketched on an offset work plane.**
Left-hand geometry had to be built explicitly.

---

## 2. The interference check that had been lying to me

The original report said "no interference". It was wrong, and the reason is worth
recording: the check only compared **moving parts against everything else**. Pairs
of static parts were never tested against each other.

Running a genuine all-pairs check on all 29 components found:

| Clash | Volume | Cause |
|---|---|---|
| HEAD_BACK ~ HEAD_FRONT | **7295 mm³** | The split cutter is a 300 mm square centred on the origin, so it reaches Z 150 — but the head tops out at Z 165.65. **The top 15 mm of the head existed in both halves.** |
| BUCK ~ PROTOBOARD | 96 mm³ | 2 mm of stack overlap |
| BODY_FRONT ~ BODY_BACK | 8.2 mm³ | overlap lip ran up into the neck |

The head one would have printed as two parts that cannot be assembled. Fixed by
setting `cut_big` 300 → 400. It removed 3659 mm³ from the front half and 3644 mm³
from the back.

**Lesson, and it is the main one from the whole CAD phase: an interference check
is only as good as the set of pairs you give it.** Every check since has been
all-pairs.

---

## 3. The moving beak

The spec allowed a speaker and a moving beak instead of a buzzer. That meant
splitting the beak and finding room for a seventh servo in a head that was
already full.

**Making room.** The DF2301Q (49 × 32 × 12) was removed. It is an offline
fixed-command recogniser, and with a real LLM and an I²S microphone it is
redundant — removing it freed the entire head and saved 12 g. *Flagged for your
review: if you already own one, it can go in the body with a vent, at the cost of
the beak servo.*

**Splitting the beak.** Copied `beak.ipt` twice and cut each with the same plane
through the beak's own axis. Volumes: 1159.2 + 775.0 = 1934.2 mm³, exactly the
original — a clean split with nothing lost.

**The pivot took three attempts.**

- Pivot at (Y 24, Z 139.5), *inside* the head: clashed from the very first
  degree of opening, 7.3 mm³ at 5°. The mandible's rear face sweeps into the
  head's front surface, because the beak root sits flat against a curved face.
- A cylindrical relief pocket in the head would fix it, but it would have cut
  away the upper beak's Ø8 peg socket.
- **Pivot moved to the beak's rear-bottom corner (Y 31, Z 131) — outside the
  head surface.** Now the rear face swings *forward*, away from the head, and
  nothing needs relieving. Clean 0–30°; 0.65 mm³ appears only at 35°.

**Result:** `beak_upper` (fixed, pegs into the head), `beak_lower` (hinged on a
Ø2 × 30 steel pin through the cheeks), driven by a 1.2 mm wire pushrod from an
MG90S low in the skull. 0.3 mm print clearance between the mandibles.

One subtlety: the first gap cut left an 8.5 mm³ sliver. The trim prism started
exactly at the beak root, and material that is high above the split plane but only
just forward of it has *negative* sketch-y, so it was missed. Fixed with a 1.5 mm
lead-in on the cut.

---

## 4. Building the simulation

The point of the simulator is to be the robot that gets printed, not a cartoon of
it. So:

- **Masses and inertia tensors come out of Inventor**, per link, combined with the
  parallel-axis theorem (`mass_properties.json`). Total 579.7 g.
- **Collision and visual meshes are the exported STLs.**
- **Servos are modelled with the MG90S's real limits** — 0.216 N·m stall,
  600 °/s. A motion that needs more than the hardware has scores badly instead of
  looking fine.

### First bug: it fell over instantly

Spawned at the right height, it face-planted in 3 seconds. Cause: **PyBullet
places the base link's *inertial* frame, not its URDF origin.** The torso's CoM is
54.4 mm above its origin, so the robot was spawned 54 mm into the floor and kicked
out. CoM read 51 mm instead of the expected 104.7 — exactly the 54.4 mm
discrepancy.

With that fixed it stands at 105.9 mm CoM height, matching the CAD's 104.9 mm
prediction, with the foot forces summing to the weight.

---

## 5. Balance: the gait was pumping itself over

Open-loop, the commanded ±15° ankle roll grew to ±30° of body lean over three
cycles and went over. It was driving a pendulum near resonance.

Added a PD controller on body lean, acting on both ankles. Sign had to be
determined empirically — the "obvious" sign made it worse (fell at 28.7° lean);
the other sign held it at 2.9° and it walked.

### Second bug, and a more serious one: lean measured in the wrong frame

The controller read lean from **world Euler angles**. That works until the penguin
turns — then world roll and pitch mix under yaw, the controller sees a lean that
is not there, and it walks itself over. It showed up as 3/3 falls on a *flat
floor* as soon as the test spawned the robot at a non-zero yaw.

Fixed by measuring in the **body frame**, which is also what the IMU bolted to the
frame actually reads:

```
g_body   = R^T · (0, 0, −1)
lean_lat = atan2(−g_body.x, −g_body.z)
```

Standing foot loads went from 4.65 N / 1.46 N (visibly lopsided) to 3.09 N /
2.97 N.

---

## 6. The walking problem you spotted

You watched the walk clip and said he would trip on a carpet. You were right, and
here is the number: **the first optimised gait lifted its feet 4.4 mm.**

The optimiser had found a cheat. I had asked it to maximise forward distance, so
it turned the balance gain up to 0.72, held the body flat (2.9° of lean), and
*scuffed* the feet along the floor at 9.7 mm/s. On a hard floor that works. On
anything with a pile it does not.

### Why clearance is not free

There is no joint that lifts a foot. A foot only leaves the floor because the body
rolls over the other one:

```
clearance ≈ stance_width × sin(body_lean)
```

and lean is capped by tip-over. So clearance and falling over are the same
variable seen from two sides. **MATLAB** (closed form) and **PyBullet**
(simulation) independently agree the tip-over angle at the original ±22 mm stance
is **28.3°**.

### Fix 1 — make clearance part of the objective

Rewrote the search to measure the true lowest point of each sole mesh and to
require ≥ 11 mm, rewarding up to 20 mm. Also replaced the sinusoidal roll with a
shaped waveform (`dwell`) that can hold full lean while the free leg swings
instead of only passing through it.

Result at the original stance: **17.9 mm clearance and 12.7 mm/s** — four times
the clearance and faster as well, because a foot that is off the ground is not
fighting friction.

> **Those two numbers predate the body-frame fix in §5**, and the gains that
> produced them were tuned against the buggy measurement. They are a fair record
> of what that run achieved at yaw = 0 (where the bug does not show), but they
> are not valid gains for the corrected controller — seeding a later search from
> them produced a gait that fell over on every surface. The usable numbers are
> the ones measured after the fix, below.
>
> This is the ordinary hazard of tuning against a simulator: **parameters are
> only meaningful together with the model that produced them.** Fix the model and
> the parameters have to be re-found, not carried across.

### Fix 2 — rockered soles

Rounded the entire sole perimeter R3. Even with good clearance, a square edge is
what catches a loop of carpet. Costs 2.8 % of the foot's volume.

### Fix 3 — widen the stance

MATLAB's closed-form map of the tradeoff:

| stance | tip-over | usable lean | clearance |
|---|---|---|---|
| ±22 (original) | 28.3° | 22.3° | 16.7 mm |
| **±26 (now)** | **30.7°** | **24.7°** | **21.7 mm** |
| ±35 | 35.8° | 29.8° | 34.8 mm |

Widening is a triple win: more clearance, *more* tip-over margin, and more hip-yaw
range before the feet collide. Changed `hip_x` 22 → 26 in the shared spreadsheet.

That change rippled, as it should: the hip servos moved outboard into a
frame-mounting column, so the columns moved from X 36 to X 38. Moving them in Y
instead pushed them through the body shell (444 mm³) — reverted. Final state is
all-pairs clear, and the gap between the feet went from 6 mm to **14 mm**, which
also made ±30° hip yaw clash-free for the first time.

### Re-tuning after the frame fix

With the corrected body-frame measurement the controller wants **stiffer** gains,
which makes sense: the error signal is now truthful, so the controller can track
the gait's commanded lean instead of fighting a phantom one. A hand sweep over
roll × kp × lean_scale showed the boundary sharply:

| roll | kp | lean_scale | speed | clearance | result |
|---|---|---|---|---|---|
| 14° | 0.30 | 0.8 | — | — | falls |
| 14° | 0.50 | 0.8 | 12.5 mm/s | 17.2 mm | ok |
| **18°** | **0.50** | **1.0** | **11.3 mm/s** | **18.5 mm** | **ok** |
| 22° | 0.50 | 1.0 | — | — | falls |

It also showed a search-design error worth recording: the optimiser's `kp` range
had been capped at 0.45, and the gain that works is 0.50. **The answer was
bounded out of the search space.** Every candidate it could generate fell over,
which looks exactly like "no solution exists" until you check the bounds against
a hand-found working point.

### Fix 4 — simulating carpet, and why I stopped trusting it

This is the part I could not finish honestly, so here is exactly where it got to.

**First model: a rigid random heightfield** at carpet pitch (8 mm amplitude, 9 mm
cells). The penguin **fell over standing still** on it. That is not carpet
behaviour — it is gravel. With 9 mm cells each foot gets only four or five contact
points, so it perches on rigid peaks and rocks off them.

**Second model: fine texture (2.5 mm cells) plus compliant contact**, so the pile
squashes rather than behaving like rock. Much better — it now **stands** on 4 mm
and 8 mm pile with even foot loads, and falls on 14 mm shag, which is believable.
But as soon as it *walks*, the body drops 50 mm in 0.2 s and tumbles, on every
soft setting tried. That failure is too violent and too uniform to be real
behaviour; it is the contact model, not the robot.

I could keep tuning contact stiffness until something looked plausible, but a
number produced that way would mean nothing. **So the carpet claim is withdrawn.**

What can be said without the simulator:

- measured ground clearance is **18.6 mm** on a validated hard-floor model
- typical carpet pile is 3–6 mm (low), 6–10 mm (medium), 15 mm+ (shag)
- the soles are rounded R3, so an edge cannot catch a loop
- the first gait's **4.4 mm** would have caught on almost anything

So the geometry is strongly in its favour on low and medium pile, and shag is
probably beyond it. That is an honest statement of what is known, and the real
robot on a real rug will settle it in ten seconds.

---

## 7. Fall recovery: honest about a hard problem

The hand-animated get-up routines did not work. Neither did a learned oscillating
flipper controller — 22 iterations × 28 candidates × 3 fall directions, zero
successes.

The reason is geometric. Lying on its back, the flipper pivot is 46.7 mm above the
floor and the flipper is 55 mm long, so it reaches the ground with 8 mm to spare
and almost no leverage. Two flippers give 7.8 N of push against a 5.7 N robot, but
the moment arm is wrong.

**What changed:** the hips were capped at ±35° in the model, because that is all
that is useful standing. The servo does ±90°, and *lying down the legs can splay
to the full range and push against the floor* — 4.2 N at each foot on a 52 mm
lever. The URDF limits were opened and the search relaunched with the legs in
play. Status of that run is in the final report.

---

## 8. On-device learning

See `docs/ONDEVICE_AI.md` for the architecture. The honest summary: a transformer
does not fit on an ESP32, but the thing actually wanted — *the penguin learns how
to react to the people around it and keeps working with the Wi-Fi down* — is an
associative-memory problem, and that fits in flash comfortably.

Measured over a simulated 28-day household, with speech-recogniser noise and
deliberately confusable phrases in the test set:

- offline coverage rises from 0 % on day 1 to **86 %** by week four
- **95 % precision** on what it answers itself
- **17 KB** of flash

The first version of that test reported 100 % precision at every threshold, which
was a sign the test was too easy rather than the system being perfect — the data
had no near-misses in it. Adding ASR noise and confusable pairs made the threshold
sweep show a real tradeoff (85 % precision at 0.22, 98 % at 0.48).

---

## 8b. The flipper range was impossible

Caught late, while reading the firmware rather than the CAD, which is why it is
worth recording.

The flipper linkage allows **280° of travel** (−95 to +185), and I had designed
the behaviours around all of it: 90° is hanging down at rest, −75° is raised over
the face for peek-a-boo, 170° is swept back for the bow. Across the whole motion
library the flippers used **245° of span**.

**An MG90S turns 180°.** Six behaviours — greet, wave, excited, scared, salute,
peekaboo — were commanding angles the servo physically cannot reach. In the
simulation it looked fine, because the URDF carried the *mechanism's* limits
rather than the *actuator's*. On the bench the servo would simply have sat at its
end stop.

The fix is to choose which 180° window to mount the horn in. Keeping the three
poses that matter — rest, a raised flipper for waving, and a sweep back for the
bow — gives **−45° … +135°**. Applied in four places that now agree:
`behaviours.py` limits, the URDF joint limits, the firmware's `LIM_LO/LIM_HI`,
and the generated motion tables.

What it costs: peek-a-boo's flippers come up to −45 instead of −75, and the bow
sweeps to 135 instead of 170. Both still read correctly.

**The general lesson:** a joint limit in a simulation should be the *actuator's*
limit, not the linkage's. I had taken the numbers from the CAD, where 280° is
genuinely available, and never asked whether anything could drive it.

---

## 9. Running list of things to check before you print

- The `.ipn` exploded view still needs an interactive insert; not scriptable.
- 3MF export refused; STL and STEP are there.
- `Z_ankle` is duplicated as a local parameter in `leg_*` and `foot_*` rather
  than shared. They must stay equal.
- Speaker dummy mass is 2.1 g; a real 23 mm speaker is 5–8 g.
