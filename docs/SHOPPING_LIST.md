# Shopping list

One page, in buying order. Quantities are **what to order**, not what the robot
uses — spares are built in where a part is easy to damage or lose.

`docs/BOM.md` has the engineering reasoning and the dimensions the CAD depends
on. This page is just the list.

**Hard dimensions** are marked ⚠ — the CAD is modelled to them and a different
size means editing `CAD/penguin_params.xlsx` and rebuilding. Everything else has
clearance around it.

---

## 1. Electronics — the long-lead items, order these first

| Qty | Part | What to search for | Why this one |
|---|---|---|---|
| 1 | **ESP32-S3 DevKitC-1 N8R8** | "ESP32-S3-DevKitC-1 N8R8 8MB PSRAM" | Must be the **S3 with 8 MB PSRAM**, not a classic ESP32. The PSRAM is the only reason the optional on-device language model is possible later. |
| **9** | **MG90S metal-gear servo** | "MG90S metal gear servo 180" | 7 used, 2 spare. One part number for every joint. ⚠ 22.8 × 12.2 × 22.7 mm. |
| 1 | **MPU6050 IMU breakout** | "MPU6050 GY-521" | **Mandatory.** No IMU means no balance loop and no fall detection — he will not stand. |
| 1 | **MAX98357A I²S amp** | "MAX98357A I2S amplifier breakout" | Drives the speaker from the ESP32 over I²S. |
| 1 | **INMP441 I²S MEMS mic** | "INMP441 I2S microphone module" | Hearing. Sits in the head crown. |
| 1 | **Speaker, Ø23 mm, 8 Ω, 1–2 W** | "23mm 8ohm 1W speaker" | ⚠ **Ø23 × 5 mm is a hard dimension** — the seat ring is modelled to it. |
| 1 | **Buck converter 6 V, ≥3 A** | "DC-DC buck 3A adjustable" or a fixed 6 V module | Servo rail only. Seven MG90S can pull over 3 A on a simultaneous move. ⚠ 30 × 22 mm, holes 24 × 16. |
| 2 | **18650 cells, protected** | "18650 protected 3000mAh" | ~2 h of active play. ⚠ 65 × 18 mm. |
| 1 | **2× 18650 holder** | "2x 18650 battery holder" | ⚠ 77 × 41 × 21 mm. 19% of the robot's mass and most of its stability — it sits low at the back on purpose. |
| 1 | **Rocker switch** | "KCD11 rocker switch 19x13" | ⚠ 19 × 13 panel cutout. |
| 1 | **USB-C breakout** | "USB-C breakout board 6-pin" | ⚠ 15 × 12 flange. Charge and flash. |
| 1 | **Protoboard 60 × 40 mm** | "double sided prototype PCB 60x40" | ⚠ **Trim it to 60 × 38** — the stack is 1 mm over otherwise. |
| 1 | **Inline fuse holder + 3 A fuse** | "inline blade fuse holder 3A" | Battery positive, before the switch. Not optional on a lithium pack. |

**Do not buy a DF2301Q offline voice module.** It was in an earlier spec and is
out: it never fitted (49 × 32 × 12 mm into a 70 × 62 × 58 mm head) and the cloud
model plus the learned offline memory replaces what it did.

---

## 2. Fasteners

Order the multipacks — these are pennies and you do not want to stop mid-build.

| Qty | Part | Where it goes |
|---|---|---|
| **40** | **M3 heat-set insert, Ruthex Ø4.0 × 6 mm** | 23 used. ⚠ The bosses are modelled to the Ruthex profile. |
| 10 | M3 × 10 socket cap | Frame to columns, shell flanges to base plate |
| 5 | M3 × 12 socket cap | Neck spigot to bridge |
| 5 | M3 × 16 socket cap | Head halves |
| 10 | M3 nylon washer | Under the shell flange heads |
| 20 | M2 × 6 self-tapper | Servo mounting tabs, 2 per servo |
| 15 | M2 × 8 self-tapper | Servo horns |
| 1 | **Steel rod Ø2 mm** | Cut one 30 mm length — the beak hinge pin |
| 1 | **Piano wire Ø1.2 mm** | Cut ~40 mm — the beak pushrod, Z-bend each end |

## 3. Wire and connectors

| Qty | Part |
|---|---|
| ~2 m | Silicone wire 26 AWG, a few colours — servo extensions up the neck and legs |
| ~15 | JST-XH or Dupont connector pairs — so the head and legs can come off again |
| 1 | Heat-shrink assortment |

## 4. Filament

| Qty | Material | Parts |
|---|---|---|
| 1 kg | **PETG** | base plate, core frame, legs, feet — stiffness and heat resistance near the servos |
| 1 kg | **PLA** — white | body front, head front, beak | 
| (opt) | **PLA** — black and orange | if you want the colours moulded in rather than painted |

Total printed mass is only ~160 g at 20% infill, so one spool of each is far more
than enough. Colour is your call — the renders use white belly, near-black back,
orange beak and feet.

## 5. Tools you may not have

| Part | Note |
|---|---|
| **Soldering iron with a heat-set insert tip** | Or a cheap conical tip you do not mind dedicating to it. 23 inserts is a lot to do badly. |
| Digital calipers | For the ⚠ parts — measure before you trust a listing |

---

## Print settings

Files are in `CAD/exports/stl_print/` — already rotated, sitting on Z=0, centred,
and each verified watertight and within **0.37%** of the CAD volume. Drop them
straight into the slicer.

| | |
|---|---|
| Layer | 0.2 mm |
| Walls | 3 perimeters |
| Infill | 20–25% gyroid |
| PETG | base_plate, core_frame, leg_L, leg_R, foot_L, foot_R |
| PLA | body_front, body_back, head_front, head_back, beak_upper, beak_lower, flipper_L, flipper_R |
| Supports | core_frame, legs, feet, flippers — see BOM.md for why each |
| Largest footprint | body shells, 106 × 115 mm — fits a 180 mm bed |
| Tallest | core_frame, 80 mm |

---

## One thing to get right at assembly

**Fit the flipper horns with the flipper hanging straight down and the servo at
its mid-point.** The linkage allows 280° but an MG90S turns 180°, so the useful
window is −45°…+135°. Out by 45° and half the gestures hit the end stop.

`docs/ASSEMBLY.md` is in build order, because several things become unreachable
once something else is in.
