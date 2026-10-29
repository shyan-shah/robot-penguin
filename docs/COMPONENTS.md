# What every part does

Positions are the CAD coordinates: **Z = 0 is the underside of the base plate, +Z up,
+Y is the way the penguin faces, +X is the penguin's own right.** The floor is at
Z = −64 mm, the top of the head at Z = 165.4 mm.

---

## 1. The seven servos

All seven are MG90S metal-gear micro servos — one part number, one horn type, one
spare in the drawer covers any of them. Each is 22.8 × 12.2 × 22.7 mm, 13.4 g,
roughly 2.2 kg·cm (0.216 N·m) stall at 6 V, and about 600 °/s unloaded.

| # | Servo | Where it lives | Axis | Travel | What it actually does |
|---|---|---|---|---|---|
| 1 | **HIP_R** | base plate, right pocket, X +26 | vertical (Z) | ±30° | Yaws the whole right leg about a vertical line. It does **not** swing the leg forward — it twists the foot toe-in/toe-out. That is the steering. |
| 2 | **HIP_L** | base plate, left pocket, X −26 | vertical (Z) | ±30° | Same, left leg. The two hips working against each other are what make the penguin shuffle forward or spin. |
| 3 | **ANKLE_R** | inside the right leg, X +26, Z −40 | fore-aft (Y) | ±25° | Rolls the body side to side over the right foot. **This is the balance actuator** — it is the only thing that can stop the penguin falling sideways. |
| 4 | **ANKLE_L** | inside the left leg, X −26, Z −40 | fore-aft (Y) | ±25° | Same, left. The two ankles normally move together: rolling both the same way leans the whole robot. |
| 5 | **FLIPPER_R** | core frame, right cheek, Z 78 | lateral (X) | −95…+185° | Flaps the right flipper in a vertical arc. 0° = straight forward, **90° = hanging down (rest)**, 180° = straight back, −90° = straight up. Used for gesture, for waving, and genuinely for pushing itself upright after a fall. |
| 6 | **FLIPPER_L** | core frame, left cheek, Z 78 | lateral (X) | −95…+185° | Same, left. |
| 7 | **BEAK** | inside the head, behind the face, Z 130 | lateral (X) | 0…30° | Opens the lower mandible through a 1.2 mm steel pushrod. 0° = shut, 30° = fully open. Driven from the speech envelope so the beak moves in time with the voice. |

### How the legs actually work

This is the part that surprises people. **The hips yaw; they do not swing.** There
is no fore-aft hip axis anywhere in the robot, so the penguin cannot take a
stride, and it cannot bow or lean forward.

Walking works like this: both ankles roll a few degrees, which tips the body and
unweights one foot; the hip on the unweighted side yaws; the ankles roll back,
planting it. Repeat. The result is a shuffle, and in simulation it is worth about
**13 mm/s with 18 mm of ground clearance** — a penguin's waddle, not a march.

A consequence worth knowing before you build: **the ankles are load-bearing.** When
the robot stands on one foot, that ankle servo holds the entire 580 g at a 26 mm
lever — about 1.48 kg·cm, roughly 67 % of an MG90S's stall torque. That works, but
it is hot for a hobby servo held statically. If the penguin ends up standing on one
foot for long periods, the ankles are the first thing to upgrade.

---

## 2. The boards, and where they are

| Component | Position (mm) | Mass | What it does |
|---|---|---|---|
| **ESP32-S3 dev board** | X ±27.5, Y 10.4–23.4, Z 51–79 | 10 g | The brain on the robot. Runs the servo loop, reads the IMU, streams audio, talks to the LLM over Wi-Fi. Mounted on the protoboard, facing into the body. |
| **Protoboard + wiring** | X ±30, Y 23.4–25, Z 46.9–84.9 | 20 g | 60 × 38 mm board on four M3 standoffs off the spine wall. Carries the ESP32, the I²S amplifier, the servo power rail and the fuse. |
| **Battery holder + 2× 18650** | X ±38.5, Y −26.5–14.5, Z 24–45 | 110 g | 7.4 V pack, right at the back and as low as it will go. **This is 19 % of the robot's entire mass and the single biggest thing keeping it upright** — moving it up or forward would cost you stability directly. |
| **Buck converter** | X ±15, Y 18–28, Z 24–46 | 15 g | 7.4 V → 6 V for the servo rail, sat on the tray in front of the battery. Servos are the only thing that needs 6 V; the ESP32 takes its own 5 V/3.3 V. |
| **Speaker, 23 mm 8 Ω** | X ±11.5, Y −24…−19, Z 123.5–146.5 | ~6 g | In the **head**, firing backward out of the 8-hole grille in the skull. In the head rather than the body so the voice comes from the face, which matters more than you would think for something with a moving beak. |
| **I²S MEMS microphone** | X ±7.5, Y ±6.5, Z 155–158 | ~1 g | Flat against the crown, behind the two 2 mm holes in the forehead. Away from the servos so it picks up less gear noise. |
| **I²S amplifier (MAX98357A)** | on the protoboard | ~2 g | Drives the speaker. Lives in the body, not the head — there is no room in the skull once the beak servo and the speaker are in, and it only needs two wires up the neck. |

---

## 3. The back panel — the two things you asked about

Looking at the penguin from behind, there are two rectangular pads moulded into the
black back shell, each sitting on its own flat **surface-normal pad** so a flat-flanged
part can bolt to a doubly-curved shell without rocking.

### The left one: **power switch**
- Position X −36.4…−5.9, Y −42.7…−9.6, Z 51.9–69.9 — roughly between the shoulder blades, on the penguin's left.
- A rocker/toggle that breaks the **battery positive** line before anything else.
- It is up at Z ~60 rather than near the floor on purpose: you can reach it without turning the robot over, and it is too high for it to get knocked on when the penguin falls on its back.

### The right one: **USB-C socket**
- Position X 4.3…43.1, Y −47.4…−15.8, Z 52.7–70.6 — mirrored, on the penguin's right.
- Two jobs: **charging the 18650 pack in place**, and **flashing / serial-debugging the ESP32** without opening the shell.
- The flange sits proud of its pad by exactly the flange thickness, so the socket face is flush with the outside of the shell rather than buried in it.

Both pads are built on *fixed* work planes computed from the body's loft sections.
Everything drawn on them is parametric, but if the body profile itself changes the
pads will not re-aim themselves — that is a known limitation, noted in the CAD report.

---

## 4. What a build costs you, in grams

| Group | Mass |
|---|---|
| Printed parts (solid) | 316 g |
| Battery + holder | 110 g |
| 7 × MG90S | 94 g |
| Electronics (ESP32, protoboard, buck, switch, USB, speaker, mic) | 61 g |
| **Total** | **~581 g** |

The 400 g target is not reachable with this battery and this many servos: the pack
and the servos alone are 204 g, and the shells have to be thick enough to take the
screw bosses. At 20–25 % infill the printed parts drop to roughly 160 g, which
brings the robot to about **425 g**. If you want to go lower, the honest levers are a
smaller battery (a single 18650 saves ~45 g) or dropping to five servos by fixing
the beak.

---

## 5. Fasteners

| Fastener | Qty | Where |
|---|---|---|
| M3 × 10 socket/csk | 11 | Frame → base-plate columns (4), shell flanges → base plate (4), shell top tabs → bridge (3) |
| M3 × 16 | 2 | Head halves |
| M3 × 12 | 2 | Neck spigot → bridge |
| M3 heat-set insert (Ø4 × 6) | 23 | Column tops, base-plate bosses, protoboard, buck, bridge, head join |
| M2 × 6 self-tapper | 14 | Servo mounting tabs — 2 each for hip, flipper, ankle, beak |
| M2 × 8 self-tapper | 10 | Servo horns |
| **Ø2 × 30 steel pin** | 1 | Beak hinge — pushed in from either cheek, retained with a drop of CA |
| **Ø1.2 steel wire, ~40 mm** | 1 | Beak pushrod, Z-bend at each end |
