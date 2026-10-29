# Bill of materials

Everything you need to buy, with the dimension the CAD actually assumes. Where a
part's size is load-bearing on the design, it says so — substitute those only
after checking the number.

**(verify)** means the dimension came from a datasheet typical and should be
measured on the part you receive. The model is fully parametric, so a changed
dimension is a spreadsheet edit (`CAD/penguin_params.xlsx`) and a rebuild.

---

## Electronics

| # | Part | Spec the CAD assumes | Qty | Notes |
|---|---|---|---|---|
| 1 | **ESP32-S3 DevKitC-1 (N8R8)** | 52 × 26 mm board, 8 MB PSRAM | 1 | **S3 with PSRAM, not a classic ESP32** — the PSRAM is what makes the optional on-device LM possible. Pin-compatible for everything else. |
| 2 | **MG90S metal-gear servo** | 22.8 × 12.2 × 22.7 mm, 2.2 kg·cm @6 V, **180° travel** (verify) | **7** | Buy 9. One part number for every joint. See the torque and travel notes below. |
| 3 | **18650 cells** | 65 × 18 mm | 2 | Protected cells. ~3000 mAh gives roughly 2 h of active play. |
| 4 | **2× 18650 holder** | 77 × 41 × 21 mm (verify) | 1 | Sits at the very back, low — it is 19 % of the robot's mass and most of its stability. |
| 5 | **Buck converter, 7.4 V → 6 V, ≥3 A** | 30 × 22 × 10 mm, holes 24 × 16 | 1 | Servo rail only. Seven MG90S can pull >3 A on a simultaneous move. |
| 6 | **MPU6050 IMU breakout** | 21 × 16 mm | 1 | Balance and fall detection. Mounts flat on the protoboard. **Mandatory** — without it there is no balance loop. |
| 7 | **INMP441 I²S MEMS mic** | 15 × 13 × 3 mm | 1 | Head crown, behind the forehead holes. |
| 8 | **MAX98357A I²S amp** | 16 × 13 × 3 mm | 1 | On the protoboard, not in the head. |
| 9 | **Speaker, 23 mm, 8 Ω, 1–2 W** | Ø23 × 5 mm | 1 | Seats in the ring behind the head grille. Ø23 is a hard dimension — the seat is modelled to it. |
| 10 | **Rocker switch** | 19 × 13 panel cutout (verify) | 1 | Back panel, left. Breaks battery positive. |
| 11 | **USB-C breakout** | 15 × 12 flange (verify) | 1 | Back panel, right. Charge + flash. |
| 12 | **Protoboard** | 60 × 38 × 1.6 mm | 1 | **Trim a 60 × 40 down to 38** — the stack is 1 mm over otherwise. |
| 13 | Silicone wire, 26 AWG | — | ~2 m | Servo extensions up the neck and legs. |
| 14 | JST-XH / Dupont connectors | — | ~15 | So the head and legs can come off. |
| 15 | Fuse, 3 A, inline | — | 1 | Battery positive, before the switch. |

### Flipper travel — read before mounting the horns

The flipper linkage allows 280° of travel but **an MG90S only turns 180°**, so the
flipper joint is limited by the servo, not the mechanism. The firmware, the
simulation and the motion tables all use **−45° … +135°**, which is the 180°
window that keeps the three poses that matter: 90° hanging down at rest, −45°
raised for waving, 135° swept back for the bow.

**When you fit the flipper horns, do it with the flipper hanging straight down and
the servo at its mid-point.** Get this wrong by 45° and half the gestures hit the
end stop.

If you want the full sweep back (170°) and the flipper raised over the face
(−75°), that needs a 270° servo — a drop-in change, and the limits are one
parameter in three files.

### Servo torque — read before buying

When the penguin stands on one foot, that ankle servo holds the whole 580 g at a
26 mm lever: **1.48 kg·cm, about 67 % of an MG90S's 2.2 kg·cm stall.** It works,
and the simulation never exceeds it, but it is hot for a hobby servo held
statically.

- Fine as specified if it mostly stands, emotes and waddles.
- If you want it walking for long stretches, the **ankles** are what to upgrade
  first. An MG92B is a drop-in with ~3.1 kg·cm.
- The hips, flippers and beak are nowhere near their limits.

---

## Fasteners

| Part | Spec | Qty | Where |
|---|---|---|---|
| M3 × 10 socket cap | | 8 | Frame→columns (4, countersunk), shell flanges→base plate (4) |
| M3 × 10 | | 3 | Shell top tabs → bridge |
| M3 × 16 | | 2 | Head halves |
| M3 × 12 | | 2 | Neck spigot → bridge |
| **M3 heat-set insert** | Ruthex Ø4.0 × 6 mm | **23** | Buy 40 |
| M2 × 6 self-tapper | | 14 | Servo mounting tabs (2 per servo × 7) |
| M2 × 8 self-tapper | | 10 | Servo horns |
| **Steel pin Ø2 × 30 mm** | | 1 | Beak hinge. Cut from 2 mm rod. |
| **Piano wire Ø1.2, ~40 mm** | | 1 | Beak pushrod, Z-bend each end |
| M3 nylon washer | | 8 | Under shell flange heads |

---

## Print settings

| | |
|---|---|
| Material | **PETG** — base plate, core frame, legs, feet (stiffness and heat) |
| | **PLA** — body shells, head, beak, flippers (surface finish) |
| Layer | 0.2 mm |
| Walls | 3 perimeters |
| Infill | 20–25 % gyroid. Solid is 316 g; at 20 % the robot lands near **425 g**. |
| Largest part | body shells, 106 × 115 mm footprint — fits a 180 mm bed |
| Tallest part | core frame, 80 mm |
| Supports | core frame (bridge cantilever, cheek shelves), legs (ankle servo cavity), feet (bracket overhang), flippers (under the hub) |

Print-ready files are in `CAD/exports/stl_print/` — already rotated to the
recommended orientation, sitting on Z=0, centred, and checked watertight. Drop
them straight into the slicer.

`CAD/exports/stl_assembled/` holds the same parts in their as-designed positions
if you want to check fit in a viewer.

---

## Total mass

| Group | Mass |
|---|---|
| Printed, solid | 316 g |
| Printed, 20 % infill | ~160 g |
| Battery + holder | 110 g |
| 7 × MG90S | 94 g |
| Electronics | 61 g |
| **Realistic total** | **~425 g** |

The 400 g target is not reachable with this battery and seven servos — the pack
and the servos alone are 204 g. A single 18650 saves ~45 g if you want to chase it.
