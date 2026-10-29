# What happened overnight

Start here. Everything else is detail.

---

## The headline

You were right about the walking. The gait I showed you lifted its feet **4.4 mm**
— a scuff, not a step, and it would have caught on the first rug it met. That is
fixed, and fixing it properly meant changing the robot, not just the controller.

Three changes, in order of how much they mattered:

1. **Clearance is now part of what the optimiser is asked for.** It had been told
   "go as far forward as you can", and it discovered that holding the body rigidly
   level and scuffing beats picking the feet up. Same optimiser, same robot,
   better question → **17.9 mm of clearance and faster as well.**
2. **The stance went from ±22 mm to ±26 mm.** Because the only way this mechanism
   lifts a foot is by leaning over the other one, clearance ≈ stance × sin(lean),
   and lean is capped by tipping over. A wider stance buys clearance *and*
   tip-over margin at the same time. The gap between the feet went 6 mm → 14 mm.
3. **The soles are rockered R3**, so a foot edge cannot catch even when clearance
   is marginal.

### About carpet specifically — read this bit

I tried hard to answer "will it trip on a rug" in simulation and **I do not
trust the answer I got, so I am not giving you one.**

Two carpet models. The first, a rigid heightfield at carpet pitch, made the
penguin fall over **standing still** — that is gravel, not carpet. The second,
fine texture plus compliant contact, got standing right (it stands on 4 mm and
8 mm pile with even foot loads, falls on 14 mm shag) but made it tumble the
instant it started walking, in a way that is clearly the contact solver rather
than the robot.

I could have tuned contact stiffness until something looked plausible. That
number would have meant nothing, so there isn't one.

What is solid without the simulator:

- clearance is **18.6 mm**, measured on a hard-floor model I do trust
- carpet pile is typically 3–6 mm low, 6–10 mm medium, 15 mm+ shag
- the soles are rounded R3, so an edge cannot catch a loop
- the gait you saw had **4.4 mm** and would have caught on almost anything

So the geometry is strongly in its favour on low and medium pile, and shag is
probably beyond it. A real rug will settle it in ten seconds, and that is the
first thing worth trying once it is built.

---

## The two things I got wrong, and found

**The interference check had been lying.** It only ever compared *moving* parts
against everything else, so pairs of static parts were never tested. A genuine
all-pairs check found **7295 mm³ of overlap between the two head halves** — the
split cutter was a 300 mm square centred on the origin, reaching Z 150, but the
head tops out at 165.65. The top 15 mm existed in *both* halves. It would have
printed as two parts that cannot be assembled.

**The flipper range was impossible.** The linkage allows 280° and I had designed
the behaviours around all of it. An MG90S turns 180°. Six behaviours were
commanding angles the servo physically cannot reach, and the simulation never
complained because the URDF carried the *mechanism's* limits rather than the
*actuator's*. Now limited to −45°…+135° in all four places that have to agree.

---

## Measured, at the end

| | |
|---|---|
| Mass | 579.7 g solid, **~425 g at 20 % infill** |
| Height | 229.4 mm |
| CoM | 104.8 mm above the floor |
| Stance | ±26 mm, feet 14 mm apart |
| Tip-over | **30.7°** (MATLAB closed form *and* PyBullet, independently) |
| Walking | **9.8 mm/s, 18.6 mm ground clearance**, no falls |
| Standing | hard floor, 4 mm and 8 mm pile all fine; 14 mm shag falls |
| Behaviours | 30 (11 emotes, 16 tricks, 3 dances), **0 unstable** |
| Servo load | median 3.3 % of the time at the limit; ankles 68 % of stall on one foot |
| Shove | 8/8 survived at 1.0 N, 7/8 at 1.4 N, 3/8 at 1.8 N |
| Learning | 55 % answered offline at 95 % precision, 73 memories, 12 KB |
| Print files | 14 parts, watertight, volumes match CAD to **0.37 %** |

## What is ready

**Print now.** `CAD/exports/stl_print/` — 14 parts, already rotated to the right
orientation, sitting on Z=0, centred. All watertight, and each one independently
verified to enclose the same volume as the CAD to within **0.37 %**. Settings in
[docs/BOM.md](docs/BOM.md).

**Order now.** [docs/BOM.md](docs/BOM.md) has everything with the dimension the CAD
assumes. One change worth knowing: it specifies an **ESP32-S3 with 8 MB PSRAM**
rather than a plain ESP32.

**Assemble.** [docs/ASSEMBLY.md](docs/ASSEMBLY.md) is in build order, because a few
things become unreachable once something else is in.

---

## New since you last looked

**A moving beak.** The old beak was one fixed part. It is now `beak_upper` (fixed)
and `beak_lower` (hinged on a Ø2 pin), driven by a seventh MG90S through a 1.2 mm
wire pushrod. It opens 0–30° and tracks the speech envelope, so the beak moves in
time with the voice.

Getting the pivot right took three attempts — inside the head it clashes from the
first degree of opening, because the beak root sits flat against a curved face.
Moved to the beak's rear-bottom corner, outside the head surface, the rear face
swings *forward* and nothing needs relieving.

**A speaker and a microphone in the head**, which meant removing the DF2301Q —
it never fitted (49 × 32 × 12 in a 70 × 62 × 58 shell), and with a proper LLM its
offline fixed-command recognition is redundant.

**Nine more behaviours:** shiver, stretch, sneeze, hiccup, point (left and right),
salute, big yawn, headbang. Plus an always-on breathing idle, because a robot that
is perfectly still reads as switched off.

**Live beat detection** — it finds the tempo of whatever is playing (121 bpm
measured against a 120 bpm track, 7 ms jitter) and picks the dance that suits it.

**It learns.** See below.

---

## The learning, honestly

You asked for an LLM on the ESP32 that learns. A transformer does not fit — 520 KB
of SRAM against 8 MB for even a tiny model. But that was a means, and the end was
*the penguin learns how to react to the people around it and keeps working with
the Wi-Fi down.* That is an associative-memory problem and it fits in flash
easily.

Every phrase becomes a 1024-bit fingerprint; matching is Jaccard overlap, which on
an MCU is a 128-byte AND and a popcount. Every cloud reply becomes a candidate
memory. Strength goes up when a response lands (laughter on the mic, a pat on the
head from the IMU, the conversation continuing) and down when it does not, and
decays with a 21-day half-life.

Measured over a simulated four-week household **with speech-recogniser noise and
deliberately confusable phrases**:

- **55 % of what a regular owner says is answered offline, at 95 % precision**
- 73 associations, **12 KB of flash**

The first version of that test reported 100 % precision at every threshold. That
was a warning, not a success — it meant the test had no hard cases in it.

The optional tier above it is a genuine tiny language model on the S3's PSRAM for
offline babble; that is specified in [docs/ONDEVICE_AI.md](docs/ONDEVICE_AI.md)
but **not built** — it needs the board in hand.

---

## What does not work — and I chased it properly

**It cannot get up off the floor, and longer flippers do not fix it.** You asked
me to design longer ones and verify the length needed, so here is the answer.

Lengthening helps, cleanly and monotonically — but it never finishes:

| flipper | reach past the floor | how far up it gets (1.0 = standing) |
|---|---|---|
| 55 mm (current) | 8.3 mm | 0.31 |
| 71.5 mm | 24.8 mm | 0.45 |
| 88 mm | 41.3 mm | 0.61 |
| 104.5 mm | 57.8 mm | 0.62 |
| 121 mm | 74.3 mm | **0.80** |

It gets to within 40° of standing and falls back, because by then the flipper has
swung past the floor and lost contact while the centre of mass is still outside
the support base. 121 mm is already longer than the body is tall.

I pushed on this hard before concluding: **six controller architectures, five
flipper lengths, both flipper travel ranges, about 5,500 simulated attempts.**
The longest variant was even given zero flipper inertia by the solver — an
advantage no real part has — and still did not make it.

And a longer flipper could not have pushed anyway: the blade tapers to 6 × 2 mm,
which as a PLA cantilever deflects **15.8 mm under the 4 N it would need** at the
current length, and 65 mm at 88 mm. Any self-righting flipper has to be a paddle,
not a taper.

**So I did not change the flipper.** Instead the penguin now has a `helpme`
behaviour — lying on its back it waggles its flippers alternately with its beak
open — and the firmware plays it after one honest recovery attempt. It is a
designed behaviour, not a failure state, and it is rather charming.

**The tail prop was designed and tested, and it does not work either.** Five more
rounds, about 9,000 trials. It looked like a six-fold improvement (0.14 → 0.84)
right up until I dropped the penguin on its back *limp, with no controller at
all* and got the identical numbers. The searches had been measuring the angle
the tail holds the body at, not recovery — scoring absolute uprightness quietly
rewarded a longer tail for reclining less. Rescored on the gain over that free
resting angle, every tail length gains +0.002 to +0.008, and the **bare** robot
gains the most at +0.011.

The tail does one real thing: it makes lying flat on its back impossible — he
ends up reclined at about 40° with his feet on the floor. Not worth a 150 mm
spike for, so it is **not fitted**. `CAD/tail_prop.ipt` is kept, fully
parametric and interference-checked, if it is ever wanted.

Full working-out in [docs/SELF_RIGHTING.md](docs/SELF_RIGHTING.md).

## Decisions — made

You asked me to choose. These are settled and the docs reflect them; each one is
reversible if you disagree.

1. **Flipper travel: MG90S, −45°…+135°.** Not the 270° servos. All 30 behaviours
   are already validated inside that window with zero unstable, and the full-sweep
   test showed even 280° of travel does not buy self-righting — so the extra range
   only buys gestures. One part number for all seven joints is worth more at
   assembly time than a wider wave.
2. **The DF2301Q stays out.** Do not buy one.
3. **Self-righting: accept it.** He plays `helpme` after one honest attempt. The
   tail prop was designed, simulated and rejected — see `docs/SELF_RIGHTING.md` §8.
4. **Mass: accept ~425 g.** The 400 g target is not reachable with this battery
   and seven servos — those alone are 204 g. Dropping to one 18650 would save 45 g
   and halve the runtime, which is a bad trade for a desk robot.
5. **Ankle servos: MG90S now.** They run at 67% of stall standing on one foot,
   which is warm but inside spec, and the simulation never exceeds it. An MG92B
   (~3.1 kg·cm) is a drop-in upgrade for the two ankles *if* it ends up walking
   for long stretches — but changing it now would mean re-validating a gait that
   was tuned against MG90S torque, for a problem you may not have.

---

## Firmware — now actually compiled

It had never been built. PlatformIO installed as a pip package (no admin), and
the first real compile found a genuine blocker: `platformio.ini` targeted
`esp32dev`, a **classic ESP32**, while the BOM specifies an **ESP32-S3**. On an
S3-N8R8 the GPIOs 22–25 do not exist at all and 26–37 are taken by the SPI flash
and octal PSRAM — **five of the seven servo pins were unusable on the board you
are told to buy.**

Re-targeted to `esp32-s3-devkitc-1` with PSRAM enabled, and the pins moved into
the S3-safe set (1–18, 21, 38–42, 47, 48):

| Signal | pin |
|---|---|
| hip_R / hip_L | 4 / 5 |
| ankle_R / ankle_L | 6 / 7 |
| flipper_R / flipper_L | 15 / 16 |
| beak | 17 |
| MPU6050 SDA / SCL | 8 / 9 |

**Builds clean** — no warnings from project sources with `-Wall`. RAM 50.9%
(166 KB of 327 KB), flash 40.2% (1.34 MB of 3.34 MB), so there is plenty of room
for the optional on-device model later. `docs/ASSEMBLY.md` carries the new table.

## Renders

`CAD/renders/studio_white/` — 8 stills at 4K on a white studio background, plus
`walk_1080.mp4`, `behaviours_1080.mp4` and `turntable360_1080.mp4`.

One correction worth knowing: the first set were all of his **back**. The beak
points +Y and the camera sat at −Y, and with a symmetrical silhouette nothing
gives it away. Caught by counting beak-orange pixels in the top of the frame.
`CAD/render_shots.py` records that and the other traps.

## Where everything is

| | |
|---|---|
| [README.md](README.md) | Layout, how to run each piece |
| [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) | **The robotics and learning software, taught properly** |
| [docs/BUILD_LOG.md](docs/BUILD_LOG.md) | Everything that happened, including every failure |
| [docs/BOM.md](docs/BOM.md) | What to order |
| [docs/SELF_RIGHTING.md](docs/SELF_RIGHTING.md) | Why it cannot get up, and what would fix it |
| [docs/ASSEMBLY.md](docs/ASSEMBLY.md) | Build order and wiring |
| [CAD/REPORT.md](CAD/REPORT.md) | The CAD model in detail |
| `sim/out/*.mp4` | Simulation videos |
| `CAD/renders/v2_*.png` | Renders of the current model |
| `matlab/out/*.png` | Stability maps and search convergence |
