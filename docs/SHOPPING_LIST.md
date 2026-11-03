# Shopping list

One page, in buying order. Quantities are **what to order**, not what the robot
uses — spares are built in where a part is easy to damage or lose.

`docs/BOM.md` has the engineering reasoning and the dimensions the CAD depends
on. This page is just the list.

**Hard dimensions** are marked ⚠ — the CAD is modelled to them and a different
size means editing `CAD/penguin_params.xlsx` and rebuilding. Everything else has
clearance around it.

### About the prices

Two columns, both in **GBP including VAT**:

- **Budget** — AliExpress / eBay, 2–4 week shipping, clone modules.
- **UK stock** — Pi Hut, Cool Components, Kunkune, Amazon UK. Next-day, genuine
  parts, roughly 1.6× the budget column.

Prices checked **November 2026** and are *indicative* — hobby electronics move
constantly and the cheap end especially. A ✓ marks a price confirmed against a
named UK retailer; everything else is a realistic range from current listings.
**Check before you buy.**

---

## 1. Electronics — the long-lead items, order these first

| Qty | Part | Budget | UK stock | What to search for | Why this one |
|---|---|--:|--:|---|---|
| 1 | **ESP32-S3 DevKitC-1 N8R8** | 12 | 19 ✓ | "ESP32-S3-DevKitC-1 N8R8 8MB PSRAM" | Must be the **S3 with 8 MB PSRAM**, not a classic ESP32. The PSRAM is the only reason the optional on-device language model is possible later. |
| **9** | **MG90S metal-gear servo** | 18 | 21.50 ✓ | "MG90S metal gear servo 180" | 7 used, 2 spare. One part number for every joint. ⚠ 22.8 × 12.2 × 22.7 mm. UK singles are £4.50–5.60, so buy the 10-pack. |
| 1 | **MPU6050 IMU breakout** | 2 | 4 | "MPU6050 GY-521" | **Mandatory.** No IMU means no balance loop and no fall detection — he will not stand. |
| 1 | **MAX98357A I²S amp** | 2.50 | 5.70 ✓ | "MAX98357A I2S amplifier breakout" | Drives the speaker from the ESP32 over I²S. |
| 1 | **INMP441 I²S MEMS mic** | 3 | 7 | "INMP441 I2S microphone module" | Hearing. Sits in the head crown. No clear UK stockist found — Amazon UK or AliExpress. |
| 1 | **Speaker, Ø23 mm, 8 Ω, 1–2 W** | 2 | 4 | "23mm 8ohm 1W speaker" | ⚠ **Ø23 × 5 mm is a hard dimension** — the seat ring is modelled to it. |
| 1 | **Buck converter 6 V, ≥3 A** | 3 | 6 | "DC-DC buck 3A adjustable" or a fixed 6 V module | Servo rail only. Seven MG90S can pull over 3 A on a simultaneous move. ⚠ 30 × 22 mm, holes 24 × 16. |
| 2 | **18650 cells, protected** | 12 | 18 | "18650 protected 3000mAh" | ~2 h of active play. ⚠ 65 × 18 mm. Buy from a reputable seller — fake 18650s are rampant. |
| 1 | **2× 18650 holder** | 2 | 4 | "2x 18650 battery holder" | ⚠ 77 × 41 × 21 mm. 19% of the robot's mass and most of its stability — it sits low at the back on purpose. |
| 1 | **Rocker switch** | 1 | 2 | "KCD11 rocker switch 19x13" | ⚠ 19 × 13 panel cutout. |
| 1 | **USB-C breakout** | 2 | 4 | "USB-C breakout board 6-pin" | ⚠ 15 × 12 flange. Charge and flash. |
| 1 | **Protoboard 60 × 40 mm** | 1.50 | 3 | "double sided prototype PCB 60x40" | ⚠ **Trim it to 60 × 38** — the stack is 1 mm over otherwise. |
| 1 | **Inline fuse holder + 3 A fuse** | 2 | 4 | "inline blade fuse holder 3A" | Battery positive, before the switch. Not optional on a lithium pack. |
| | **Subtotal** | **63** | **102** | | |

**Do not buy a DF2301Q offline voice module.** It was in an earlier spec and is
out: it never fitted (49 × 32 × 12 mm into a 70 × 62 × 58 mm head) and the cloud
model plus the learned offline memory replaces what it did.

---

## 2. Fasteners

Order the multipacks — these are pennies and you do not want to stop mid-build.

| Qty | Part | Budget | UK stock | Where it goes |
|---|---|--:|--:|---|
| **100** | **M3 heat-set insert, Ruthex Ø4.0 × 6 mm** | 8 | 10 | 23 used. ⚠ The bosses are modelled to the Ruthex profile. Sold in 100s, not 50s. |
| 10 / 5 / 5 | M3 × 10, × 12, × 16 socket cap | 6 | 12 | Frame to columns, shell flanges, neck spigot, head halves. An M3 assortment box covers all three. |
| 10 | M3 nylon washer | 2 | 4 | Under the shell flange heads |
| 20 / 15 | M2 × 6 and M2 × 8 self-tapper | 4 | 8 | Servo mounting tabs (2 per servo), servo horns |
| 1 | **Steel rod Ø2 mm** | 2 | 4 | Cut one 30 mm length — the beak hinge pin |
| 1 | **Piano wire Ø1.2 mm** | 2 | 4 | Cut ~40 mm — the beak pushrod, Z-bend each end |
| | **Subtotal** | **24** | **42** | |

## 3. Wire and connectors

| Qty | Part | Budget | UK stock |
|---|---|--:|--:|
| ~2 m | Silicone wire 26 AWG, a few colours — servo extensions up the neck and legs | 5 | 8 |
| ~15 | JST-XH or Dupont connector pairs — so the head and legs can come off again | 4 | 7 |
| 1 | Heat-shrink assortment | 3 | 6 |
| | **Subtotal** | **12** | **21** |

## 4. Filament

**You only need three spools, not five** — see *Materials and colours* below.
Skip this section entirely if you already have PETG and PLA.

| Qty | Material | Budget | UK stock | Parts |
|---|---|--:|--:|---|
| 1 kg | **PETG** — grey or natural | 15 | 25 | base plate, core frame, legs (**and feet**, see note) |
| 1 kg | **PLA** — white | 12 | 20 | body front, head front |
| 1 kg | **PLA** — black | 12 | 20 | body back, head back, both flippers |
| — | **PLA/PETG — orange** | 0 | 0 | beak and feet need **16 g between them**. Use scrap, or paint. Not worth a spool. |
| | **Subtotal** | **39** | **65** | |

Premium brands run much higher — Prusament PETG is about **£37/kg** in the UK.
At 158 g of total printed material, the spool choice barely affects the build
cost; it affects the other nine prints you will do with what is left.

## 5. Tools you may not have

| Part | Budget | UK stock | Note |
|---|--:|--:|---|
| **Heat-set insert tip for a soldering iron** | 3 | 6 | Or a cheap conical tip you do not mind dedicating to it. 23 inserts is a lot to do badly. |
| Soldering iron, if you have none | 18 | 30 | |
| Digital calipers | 8 | 18 | For the ⚠ parts — measure before you trust a listing |

---

## What it comes to

| Scenario | Total |
|---|--:|
| **Cheapest** — AliExpress throughout, you already have filament and tools | **~£99** |
| **Realistic mix** — UK for the board, battery and audio; budget for the rest | **~£130** |
| **All UK stock**, you already have filament and tools | **~£165** |
| **Everything new** — UK stock, three spools, soldering iron and calipers | **~£285** |

The single biggest saving is the servos: nine MG90S bought as singles from a UK
retailer is £40–50, versus £18–22 for a 10-pack either side of the Channel.

---

## Materials and colours

Fourteen printed parts. **Six PETG, eight PLA**, in five colour groups.

| Part | Material | Colour | RGB | Solid | At 20% |
|---|---|---|---|--:|--:|
| `base_plate` | PETG | frame grey | `#5C5C64` | 33.3 g | ~17 g |
| `core_frame` | PETG | frame grey | `#5C5C64` | 55.6 g | ~28 g |
| `leg_L`, `leg_R` | PETG | leg grey | `#76767E` | 35.5 g | ~18 g |
| `foot_L`, `foot_R` | **PETG** | **orange** | `#F2740E` | 28.1 g | ~14 g |
| `body_front` | PLA | white | `#EEEEF3` | 50.3 g | ~25 g |
| `head_front` | PLA | white | `#EEEEF3` | 21.0 g | ~11 g |
| `body_back` | PLA | near-black | `#1A1A20` | 52.4 g | ~26 g |
| `head_back` | PLA | near-black | `#1A1A20` | 23.2 g | ~12 g |
| `flipper_L`, `flipper_R` | PLA | near-black | `#1A1A20` | 12.6 g | ~6 g |
| `beak_upper`, `beak_lower` | PLA | orange | `#F2740E` | 3.5 g | ~2 g |
| | | | **total** | **316 g** | **~158 g** |

Solid masses are computed from the print STLs (PETG 1.27 g/cm³, PLA 1.24 g/cm³)
and sum to 316 g, matching the CAD. The 20% column assumes 3 perimeters and is
approximate — thin-walled shells come out nearer solid than the chunky frame
does.

**Two things worth knowing:**

1. **The feet are PETG but render orange.** PETG is specified for stiffness and
   heat resistance next to the ankle servos, and the colour comes from the
   render palette. Orange PETG is uncommon and you need 14 g of it, so: print
   them in whatever PETG you have and paint them, or accept grey feet. Do not
   switch them to PLA to get the colour — they sit against the servo and take
   the landing loads.
2. **The built robot weighs ~425 g, not 580 g.** The 579.7 g figure from CAD
   treats every printed part as solid plastic. At 20% infill the printed parts
   come to ~158 g instead of 316 g, so the real robot lands around 425 g with
   electronics. The simulation was tuned on the CAD masses, which is the
   conservative direction — the real one is lighter.

The two greys are close enough that one grey spool covers both.

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
| Supports | core_frame (bridge cantilever, cheek shelves), legs (ankle servo cavity), feet (bracket overhang), flippers (under the hub) |
| Largest footprint | body shells, 106 × 115 mm — fits a 180 mm bed |
| Tallest | core_frame, 80 mm |

---

## One thing to get right at assembly

**Fit the flipper horns with the flipper hanging straight down and the servo at
its mid-point.** The linkage allows 280° but an MG90S turns 180°, so the useful
window is −45°…+135°. Out by 45° and half the gestures hit the end stop.

`docs/ASSEMBLY.md` is in build order, because several things become unreachable
once something else is in.
