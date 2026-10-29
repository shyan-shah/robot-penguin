# How it works

The robotics and the learning software behind the penguin, explained with this
robot's own numbers rather than in the abstract. Read it in order; each part
depends on the one before.

---

## 1. Why this penguin walks the way it does

### Degrees of freedom decide everything

The robot has seven joints. For walking, only four matter:

```
hip_R, hip_L     rotate about a VERTICAL axis   (yaw)
ankle_R, ankle_L rotate about a FORE-AFT axis   (roll)
```

Notice what is missing. There is **no joint anywhere that pitches** — nothing
rotates about the left-right axis. That single fact decides the robot's entire
character:

- it cannot take a stride, because a stride means swinging a leg forward, which
  is hip *pitch*
- it cannot bow or lean forward
- it cannot lift a foot directly

A human walks by pitching the hip and knee to swing a leg through. This penguin
has to do it a completely different way, and the way it does it is the thing
worth understanding.

### How a waddle actually works

Stand up and try it: keep your knees locked, and walk by rocking side to side.
What you will find is that you rock onto one foot, which unweights the other,
and then you twist the free foot forward and plant it. That is hip yaw plus
ankle roll, and it is exactly what this robot does.

The cycle, one half at a time:

1. **Both ankles roll** the same direction. The body leans. The weight moves off
   one foot.
2. **That foot is now free**, hanging a few millimetres clear.
3. **The hip on that side yaws**, twisting the free foot to a new angle.
4. **The ankles roll back**, planting it. Now the other foot is free.
5. Repeat, mirrored.

Net result: forward shuffle. In simulation, about **13 mm/s**. A penguin's
waddle, not a march, which is correct for the animal.

### Clearance and falling over are the same variable

This is the key insight of the whole walking problem, and it is why the first
gait was wrong.

Because no joint lifts a foot, a foot only leaves the floor when the body rolls
over the *other* foot. Geometrically:

```
clearance ≈ stance_width × sin(body_lean)
```

With the stance at ±26 mm, that is 52 mm × sin(lean). So:

| lean | clearance |
|---|---|
| 5° | 4.5 mm |
| 15° | 13.5 mm |
| 25° | 22.0 mm |

More lean, more clearance. But lean is exactly what tips you over, so the two are
in direct tension, and the ceiling is set by...

### The support polygon

A rigid body on the ground is statically stable as long as the vertical line
through its **centre of mass** lands inside the **support polygon** — the convex
hull of everything touching the floor. Both feet down, that polygon is big. As
the robot rolls onto one foot, the polygon shrinks to just that foot, 38 mm wide.

The robot tips when the CoM leaves the far edge. You can compute exactly when.
The CoM sits 105 mm above the floor and the ankle axis 24 mm above it, so the
lever from the ankle axis to the CoM is:

```
dx = 26 mm (horizontal)   dz = 81 mm (vertical)   R = 85 mm
```

Rotate that lever by angle θ and ask when the CoM crosses the foot's outer edge,
19 mm outboard of the ankle axis:

```
26·cos θ − 81·sin θ = −19     →     θ = 30.7°
```

**That number came out of two completely independent routes** — a closed-form
calculation in MATLAB and a full rigid-body simulation in PyBullet — and they
agree. When two different methods agree on a number, you can build on it.

So the usable band is roughly **15–25° of lean**: below 15° the feet scuff, above
~25° there is not enough margin before falling.

---

## 2. Why balance needs feedback

### The robot is an inverted pendulum

A mass on a stick, balanced above a pivot. Its natural period is:

```
T = 2π √(L/g) = 2π √(0.105 / 9.81) ≈ 0.65 s
```

This matters because **if you drive a pendulum anywhere near its natural
frequency, you pump energy into it.** That is exactly what happened on the first
try: an open-loop command of ±15° ankle roll grew into ±30° of body lean within
three cycles, and the penguin went over. It was not a bug in the code. It was
resonance doing what resonance does.

### The fix: a PD controller

The ankles are the only actuators that act on side-to-side lean, so they carry a
small correction on top of whatever the behaviour is asking for:

```
correction = Kp · (lean − target_lean) + Kd · lean_rate
```

- **Kp** (proportional) pushes back in proportion to how far off you are. Too
  little and it falls; too much and it goes rigid.
- **Kd** (derivative) pushes back against how *fast* you are tipping. This is the
  damping term, and it is what kills the resonance.

A detail that is easy to get wrong: the controller's target is **what the gait
asked for**, not zero. If you servo the lean to zero you suppress exactly the
motion that gives the feet clearance — which is precisely the mistake made in
section 4.

### The bug worth learning from: which frame are you measuring in?

The controller originally read lean from **world Euler angles** (roll, pitch, yaw
relative to the room). That works perfectly — right up until the penguin turns.

Euler angles do not decompose independently once you combine rotations. Yaw the
robot 35° and world "roll" and world "pitch" start mixing into each other. The
controller sees a lean that is not there, corrects for it, and walks itself over.
It showed up as **3 falls out of 3 on a flat floor** as soon as a test spawned the
robot at a non-zero heading.

The fix is to measure in the **body frame**, which is also what the IMU bolted to
the chassis physically reads:

```
g_body   = Rᵀ · (0, 0, −1)        # gravity, expressed in the robot's own axes
lean_lat = atan2(−g_body.x, −g_body.z)
```

An accelerometer measures the gravity vector in its *own* frame. It has no idea
which way the room is. Writing the controller the same way makes it correct and
makes it match the hardware.

Standing foot loads went from 4.65 N / 1.46 N (visibly lopsided) to 3.09 N /
2.97 N just from this change.

---

## 3. How the motions are built

### Keyframes for expression, a CPG for walking

Two different jobs, two different representations.

**Emotes and tricks are keyframed** — a list of (time, pose) and smooth
interpolation between them. This is just animation, and animation is the right
tool for expression because a human is choosing the timing.

**Walking is a central pattern generator (CPG)** — a small set of coupled
oscillators. Biology does this: the rhythm for walking is generated in the spinal
cord, not planned step by step by the brain. For this robot:

```
ankle_R = ankle_L = roll · shaped(t/period, dwell)
hip_R   = yaw · sin(2π(t/period + phase)) − toe_out
hip_L   = yaw · sin(2π(t/period + phase)) + toe_out
```

Seven numbers describe the entire gait. That is what makes it searchable.

The `dwell` parameter is worth a note. A pure sine passes *through* maximum lean
instantly. A trapezoidal wave **holds** it, giving the free leg time to swing
while the foot is actually clear. `shaped()` morphs between the two:

```
shaped(u, dwell) = tanh(k·sin(2πu)) / tanh(k),   k = 0.3 + 6·dwell
```

The optimiser chose dwell ≈ 0.65 — distinctly trapezoidal. It wanted the hold.

### A joint limit is the actuator's, not the linkage's

Worth stating on its own, because it cost a real bug.

The flipper linkage allows 280° of rotation. I took that number from the CAD, put
it in the URDF, and designed behaviours that used 245° of it. The simulation was
happy. An MG90S turns **180°**, so six of those behaviours were commanding angles
no servo on the robot could reach — and nothing would have told me until the
hardware sat at its end stop.

The number that belongs in a model is whichever limit binds first:

```
joint limit = min(what the mechanism allows, what the actuator can do)
```

For the hips it is the mechanism (the feet collide before the servo runs out). For
the flippers it is the servo. Getting that backwards produces a simulation that
validates motions the robot cannot perform, which is worse than no simulation.

### Interpolation with an ease

All blending uses a cosine ease rather than a straight line:

```
ease(u) = 0.5 − 0.5·cos(πu)
```

Linear interpolation means the servo is asked to jump instantly to full speed at
every keyframe, which is both ugly and hard on the gears. A cosine ease starts
and ends at zero velocity.

---

## 4. The "training": how the gait was found

### Cross-entropy method

Not deep reinforcement learning. CEM — simpler, and the right size for a problem
with eight parameters.

```
1. Start with a broad Gaussian over the parameter space.
2. Sample 20 candidate gaits from it.
3. Run each one in the physics simulator. Score it.
4. Keep the best 5.
5. Re-fit the Gaussian to those 5. Narrow it.
6. Go to 2.
```

That is the whole algorithm. The distribution walks toward whatever scores well
and tightens around it. For 8 parameters it converges in 15–20 rounds. Deep RL
would need millions of steps to do the same job here, and would be harder to
debug.

### The score function is the entire design

This is the part people underestimate. **The optimiser will do exactly what you
ask, including things you did not mean.**

The first score function was essentially "go as far forward as you can". It
returned a gait that travelled 9.7 mm/s with **4.4 mm of ground clearance** — it
had discovered that holding the body rigidly level (balance gain 0.72, 2.9° of
lean) and *scuffing* the feet along the floor beats picking them up, because
lifting a foot costs energy and risks falling.

On a hard desk, that works. On a rug, it is a faceplant. The optimiser was not
wrong; the question was wrong.

The rewritten score measures the true lowest point of each sole mesh and:

```
score  =  10 × speed
        +  9 × min(clearance, 20 mm)        reward clearance, cap the reward
        − 25 × max(0, 11 mm − clearance)    hard penalty below a step
        − 25 × max(0, lean − 23°)           stay clear of tip-over
        −  4 × max(0, saturated% − 15)      do not live at the servo's limit
        − 900 if it falls over
```

Same optimiser, same robot, different question. Result: **17.9 mm clearance and
12.7 mm/s** — four times the clearance *and* faster, because a foot that is off
the ground is not dragging.

### Domain randomisation

A gait tuned on a perfect plane learns to rely on a perfect plane. So every
candidate is scored on three surfaces at once — hard floor, 4 mm carpet pile,
8 mm pile, modelled as random heightfields at carpet pitch — and the aggregate
weights the **worst** surface at 65 %:

```
score = 0.65 · min(scores) + 0.35 · mean(scores)
```

Optimising the worst case rather than the average is what makes the result
survive contact with a real floor. This is the same principle that gets
simulation-trained robot policies working on real hardware.

### Modelling the actuator honestly

The servos in simulation have the MG90S's real stall torque (0.216 N·m) and real
no-load speed (600 °/s). This is not decoration. Without it, the optimiser happily
finds gaits that need torque the hardware does not have, and they work perfectly
in simulation and fail instantly on the bench.

It also surfaced a real design number: standing on one foot, that ankle servo
holds the whole 580 g at a 26 mm lever — **1.48 kg·cm, 67 % of stall.** That is
the single tightest margin in the robot, and it is why the BOM says the ankles are
what to upgrade first.

---

## 5. Why getting up is hard

Worth understanding, because it is a good example of a problem where no amount of
clever control substitutes for geometry.

Lying on its back, the penguin needs to rotate ~90° and raise its CoM by 55 mm.
Energetically that is 0.31 J, and the flipper servos can deliver 1.36 J over their
travel — so energy is not the constraint.

**Leverage is.** The flipper pivot sits 46.7 mm above the floor and the flipper is
55 mm long, so it reaches the ground with 8 mm to spare. Pushing on 8 mm of lever
cannot right a 5.7 N robot, no matter how the oscillation is timed. A learned
rocking controller — 22 rounds × 28 candidates × 3 fall directions — found
**zero** successes, and that is the honest answer for that actuator.

What changes the picture is the legs. They were limited to ±35° of yaw in the
model because that is all that is useful standing (beyond it the feet collide).
The servo does ±90°, and **lying down the legs can splay to the full range and
push against the floor** — 4.2 N at each foot on a 52 mm lever. That is a
different problem entirely, and it is the one the current search is solving.

The lesson: when a controller search finds nothing, check whether you have
accidentally forbidden the actuator that would have worked.

---

## 6. The learning software

### The problem

A transformer does not fit on an ESP32 — 520 KB of SRAM against 8 MB for even a
tiny model. But "an LLM on the robot" was a means. The end was: *the penguin
learns how to react to the people around it, and it keeps working with the Wi-Fi
down.* That is associative memory, and that fits in flash easily.

### Fingerprints and Jaccard similarity

Every phrase becomes a sparse bit vector:

1. Lowercase, strip punctuation, drop stopwords.
2. Take unigrams and bigrams: "good morning" → `good`, `morning`, `good_morning`.
3. Hash each gram and set **3 bits** out of 1024.

Comparison is **Jaccard similarity** — the overlap divided by the union:

```
J(a,b) = popcount(a AND b) / popcount(a OR b)
```

Measured on real phrases:

| | | J |
|---|---|---|
| "good morning" | "good morning penguin" | 0.600 |
| "do a dance" | "can you dance for me" | 0.333 |
| "do a dance" | "what is the capital of peru" | 0.000 |

Why bits and Jaccard rather than embeddings? Because on an MCU this is a 128-byte
AND and a popcount — scanning 384 memories costs well under a millisecond, with no
floating point and no model. And bigrams give it just enough word-order sense to
tell "dance for me" from "dance" without any of the machinery.

The bigrams matter more than they look. Unigrams alone cannot distinguish "do a
dance" from "do a trick" well; the bigram `do_dance` vs `do_trick` does.

### Reinforcement and forgetting

Each association carries a **strength**. It goes up when a response lands and down
when it does not, measured from signals the robot actually has:

| Signal | How it is detected | Δ |
|---|---|---|
| Laughter | mic energy burst after speaking | +0.8 |
| A pat on the head | IMU spike while the servos are idle | +0.4 |
| They kept talking within 6 s | conversation timing | +0.3 |
| They walked away | no further audio | −0.3 |
| They repeated themselves | near-duplicate phrase within 10 s | −0.6 |

And strength **decays with a 21-day half-life**, so things the owner stopped
saying fade out instead of accumulating forever. An association must reach
strength 2.0 before the robot trusts it enough to answer offline — it has to have
seen a response work more than once.

### The two thresholds, and what they trade

- **Match threshold** — how similar before it counts as the same question.
- **Merge threshold** — how similar before a new phrase is the *same intent
  reworded*, and should reinforce the existing memory instead of adding another.

Swept over simulated households with speech-recogniser noise:

| merge | match | coverage | precision | memories |
|---|---|---|---|---|
| 0.72 | 0.34 | 43 % | 95 % | 94 |
| **0.48** | **0.40** | **56 %** | **93 %** | **65** |
| 0.40 | 0.34 | 56 % | 92 % | 62 |

Loose merging keeps the memory small and coverage high, because the noisy
variants of "good morning" reinforce one strong memory instead of creating eight
weak ones. Too loose and distinct intents start merging. 0.48 is the knee.

### Testing something that learns

The first version of the test reported **100 % precision at every threshold**.
That was not a success, it was a warning: a knob that changes nothing means the
test has no hard cases in it. The data was all near-identical catchphrases or
completely unrelated questions, with nothing in between.

Adding speech-recogniser noise (dropped words, homophone swaps, filler words) and
deliberately **confusable pairs** — "do a dance" vs "do a trick", "goodnight" vs
"night" — made the threshold sweep show a real tradeoff, and dropped the honest
precision number to 93 %. That is the number to trust.

### Host and firmware must agree exactly

The memory is trained on the host and shipped to the robot as a flat binary. If
the two `fingerprint()` implementations disagree by **one bit on one gram**, every
learned association silently stops matching once it is on the robot — and nothing
crashes. You would only notice as "it never remembers anything".

So `tools/check_parity.py` holds a deliberately literal transliteration of the C++
and checks it against the Python on 421 strings, including empty strings, pure
punctuation, unicode, and strings past the firmware's 127-character buffer. It
caught a real bug immediately: the FNV-1a offset basis had been typed with digits
missing, so **every fingerprint differed**.

---

## 7. What runs where

```
ESP32-S3                              Host
--------                              ----
servo loop            100 Hz          speech → text
balance PD            100 Hz          the LLM
fall detect/recover   100 Hz          text → speech
learned memory        instant
wake word
```

The split is the design. **If the host dies, the penguin still stands, balances,
and gets itself off the floor.** It just stops talking. Nothing that has to happen
in milliseconds depends on a network.
