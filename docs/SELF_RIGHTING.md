# Can it get itself up? A full investigation

Short answer: **not with flippers.** This is the working-out, because the
negative result is well-measured and it points at what *would* work.

---

## 1. Which joints can even help

Before trying to control anything, measure which joint axes are aligned with the
axis the body must rotate about to stand up. 1.00 means that joint pushes
directly against the fall; 0.00 means it is useless for it.

| fall | hip | ankle | flipper |
|---|---|---|---|
| back shell down | 0.00 | 0.15 | **0.99** |
| face down | 0.00 | 0.04 | **1.00** |
| on its side | 0.00 | **0.68** | **0.74** |

> Re-measured after finding that the fall labels in the code were swapped - a
> roll of −88° about X puts the robot *face down*, not on its back. The numbers
> above are unchanged by it (both orientations give flipper ≈ 1.00), but it
> mattered for the tail prop, which is a feature on one specific side of the
> body: the first prop sweep was propping the back while testing a face-down
> fall. Labels are now asserted against the simulated body orientation rather
> than assumed.

From the back or front, the flippers are the **only** actuator pointing the right
way. That single table reframed the whole problem: no amount of clever hip or
ankle work matters when the robot is on its back.

## 2. Why the flippers struggle

Lying on its back, the flipper pivot sits **46.7 mm above the floor** and the
flipper is **55 mm long**. It reaches the ground with about **8 mm to spare.**

Two flippers at 0.216 N·m give 7.8 N of push against a 5.7 N robot, so force is
not the problem and neither is energy — righting needs 0.34 J and the flippers
can do 1.36 J over their travel. **Leverage is the problem.** You cannot lift a
robot on 8 mm of lever.

## 3. What was tried

| # | Approach | Trials | Result |
|---|---|---|---|
| 1 | Hand-animated keyframe routines (back / front / side) | 27 | none recover |
| 2 | Learned oscillating flipper controller (resonant rocking) | ~1,850 | none recover; best peak uprightness 0.29 |
| 3 | Two-stage: hips roll it onto its side, then ankles + flippers right it | ~1,300 | reaches the side reliably (progress 1.00) but never completes |
| 4 | Flipper-length sweep, 55 → 121 mm | ~630 | monotonic improvement, no completion |
| 5 | Three-stage with a feedback **catch** (stop pushing, plant the feet) | ~1,200 | catch fires, still no completion |
| 6 | All of the above with the flipper's **full 280° linkage travel** (i.e. a 270° servo instead of an MG90S) | ~700 | no change: peak 0.588 at 88 mm, 0.795 at 121 mm, against 0.613 / 0.764 with 180° |

About 5,500 rollouts in total.

## 4. The length sweep — the useful data

Flipper length against how far the body gets (1.0 = standing):

| flipper | reach past the floor | peak uprightness | recovered |
|---|---|---|---|
| 55 mm (current) | 8.3 mm | 0.31 – 0.35 | no |
| 71.5 mm | 24.8 mm | 0.42 – 0.45 | no |
| 88 mm | 41.3 mm | 0.61 | no |
| 104.5 mm | 57.8 mm | 0.62 – 0.70 | no |
| 121 mm | 74.3 mm | 0.76 – 0.81 | no |

The trend is clean and monotonic — every extra millimetre of flipper buys
rotation — but it **asymptotes short of standing**, and 121 mm is already longer
than the body is tall (115 mm).

Two things worth knowing about how hard this was pushed:

- **Flipper travel is not the limit.** Repeating the sweep with the full 280° the
  linkage allows (what a 270° servo would give, instead of the MG90S's 180°)
  changed nothing material: 0.588 at 88 mm and 0.795 at 121 mm.
- **The longest variant was given an unfair advantage and still failed.** At
  121 mm the scaled inertia tensor violated the triangle inequality and PyBullet
  zeroed it, so that flipper swings with *no rotational inertia at all* - easier
  than any real part could be. It still did not get up.

### Why it stalls

The body rotates up to roughly 40–50° short of vertical and falls back. At that
point the flipper has swung past the floor and lost contact, so the push stops
while the centre of mass is still outside the support base. Gravity does the
rest. Making the flipper longer delays that moment but does not remove it.

## 5. And a longer flipper could not push anyway

Worth checking before committing to the idea. The blade tapers to 6 × 2 mm at the
tip. As a PLA cantilever carrying the 4 N it would need to push with:

| flipper | tip section | second moment | deflection under 4 N |
|---|---|---|---|
| 55 mm (current) | 6 × 2 mm | 4 mm⁴ | **15.8 mm** |
| 88 mm, same taper | 6 × 2 mm | 4 mm⁴ | **64.9 mm** |
| 88 mm, paddle tip | 12 × 4 mm | 64 mm⁴ | 4.1 mm |
| 88 mm, wide paddle | 16 × 5 mm | 167 mm⁴ | 1.6 mm |

The current flipper would simply fold. **Any self-righting flipper has to be a
paddle, not a taper** — which is also closer to a real penguin's flipper.

## 6. What would actually work

Ranked by how much they change the robot:

1. **Accept it and ask for help.** A `helpme` behaviour exists: lying on its back
   it waggles its flippers alternately with its beak open, and the firmware fires
   it after a failed recovery attempt. Honestly this is charming, costs nothing,
   and is what most desk robots do.
2. ~~**A tail prop.**~~ **Tried, and it does not work — see section 8.** It was
   designed, simulated over five rounds, and rejected. It reclines the body
   rather than righting it, and the apparent improvement was an artefact of
   scoring absolute uprightness instead of the gain over the free resting angle.
3. **Don't fall over.** Push resistance is already 8/8 at 1.0 N and 7/8 at 1.4 N.
   Widening the stance further (±32 mm gives a 34.2° tip-over against the current
   30.7°) buys more margin than any recovery mechanism.
4. **A fifth limb.** A tail servo, or flippers that can rotate about a second
   axis. This is a real redesign and not worth it for a desk toy.

## 7. Method note

Every number here came from the same simulation that produced the walking
results, with the MG90S's real stall torque and the masses and inertias taken
from the CAD. The flipper variants scale the blade along its length and scale
mass and inertia with it — which makes the long flippers **heavier** in
simulation than a real tapered part would be, so the results are, if anything,
pessimistic about long flippers. That does not change the conclusion.

## 8. The tail prop: designed, simulated, and rejected

Section 6 recommended a tail prop as the cheap route to self-righting. It was
designed in CAD, simulated across five rounds and about 9,000 further trials,
and **it does not work.** Here is the whole trail, including the part where I
nearly reported a false success.

### Round 1 — the obvious shape, which was the wrong sign

A spur angled *below* horizontal, the way you draw a kickstand. Nine geometries,
45–75 mm, 20–50° down. Every one was **worse than no prop at all**, six of them
much worse (peak uprightness as low as −0.53 against the bare robot's 0.14).

The reason is geometric and obvious afterwards: lying on its back, the body's −Z
points roughly *up*, so a spur angled below horizontal in the standing frame
points into the air. It never touches the floor. All it contributes is 50–100 g
at a long lever arm behind the centre of mass, which is exactly the wrong place.

### Rounds 2 and 3 — invert it, and watch the numbers soar

Pointing the spur *back and up* instead, and attaching it high on the shell,
transformed the result:

| geometry | peak uprightness |
|---|---|
| bare robot (same search budget) | 0.139 |
| 90 mm at 10°, Z 55 | 0.709 |
| 110 mm | 0.762 |
| 130 mm | 0.803 |
| 150 mm | **0.835** |

Repeating the 90 mm cell in a separate round returned 0.709 against 0.708 — so
the differences were real, not search noise. This looked like a six-fold
improvement and very nearly went into the report as one.

### The check that killed it

Two things did not smell right. `final_up` equalled `peak_up` in every single
row — the signature of a robot *settling* somewhere rather than rising and
falling back. And round 4, which added a whole new stand-up stage to the
controller, returned numbers **identical to round 3 to three decimal places** at
every length. No controller change should be that invisible.

So I dropped the penguin on its back **limp, with no recovery attempt at all**:

| tail | resting uprightness, no control | what the searches "achieved" |
|---|---|---|
| 90 mm | 0.688 | 0.688 |
| 130 mm | 0.791 | 0.791 |

The searches were not recovering anything. They were measuring **the angle the
tail happens to hold the body at.** Over nine seconds of driving, `up` never
moved by as much as 0.01. Rounds 2–4 had been scoring absolute uprightness,
which quietly rewarded a longer tail for merely reclining less.

### Round 5 — scoring the gain instead

Rescored on the *gain* over the free resting angle, so a tail that just holds the
body higher earns nothing:

| | resting | finishing | gain |
|---|---|---|---|
| bare robot | 0.087 | 0.098 | +0.011 |
| 90 mm tail | 0.695 | 0.696 | +0.002 |
| 110 mm tail | 0.746 | 0.754 | +0.008 |
| 130 mm tail | 0.796 | 0.797 | +0.002 |

Every gain is within noise, and the largest belongs to the *bare* robot. This
included a deliberate "deckchair shuffle" controller — waddling backwards to walk
the feet under the body, the way a person gets out of a low chair — because
tracing the pose showed 96% of the robot's weight already on its feet. It still
could not shift the body off the tail.

### What the tail actually does, and why it still came off

One real benefit: **it makes lying flat on its back impossible.** A backward fall
ends with the penguin reclined at about 40° with its feet on the floor, instead
of flat at 0.09. That is a much better-looking failure, and an easier one to
spot and pick up.

It is not worth what it costs. Crossing the 0.85 "standing" threshold needed
roughly 170 mm of tail — longer than the body is tall, and more than twice the
body depth — for a benefit that is *not* self-righting. At 24 g on a 100 mm
cantilever it also puts about 0.4 N·m into a 2.4 mm printed shell wall, which
needs four M2 screws and a backing plate to carry.

So the tail is **not fitted**. `CAD/tail_prop.ipt` is kept as a fully
parametric, interference-checked part in case it is ever wanted:

- 19,173 mm³, 23.8 g in PLA; spur 16 × 10 mm, 105 mm long
- seat is a vertical cylinder of radius `(bodyW35/2)² / (bodyD35/2)` = 65.326 mm,
  derived from the body's own loft parameters, so it tracks the shell. It
  predicts the measured skin at (0, 38) to **0.011 mm** and fits the real surface
  to within **0.41 mm** across the pad
- four M2 screws; mounts at Z 38, which clears the USB socket at Z 52.6–70.6
- all four sketches fully constrained; zero interference against all 30 parts

**The conclusion of section 6 stands unchanged: accept it, and ask for help.**
The `helpme` behaviour remains the designed response to a fall.
