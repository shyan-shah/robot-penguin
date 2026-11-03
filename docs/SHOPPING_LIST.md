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

## 0. Exact quantities, and what you may already have

Two different numbers matter, and this page previously blurred them:

- **Used** — what goes into the finished robot.
- **Order** — used, plus spares where a part is easy to lose, strip or damage.

### What the robot actually uses

| Part | Used | Order | Spare rationale |
|---|--:|--:|---|
| ESP32-S3 DevKitC-1 N8R8 | 1 | 1 | |
| MG90S servo | **7** | **9** | Easiest part to burn out or strip. Two spares. |
| 18650 cell, protected | 2 | 2 | |
| 2× 18650 holder | 1 | 1 | |
| Buck converter 6 V ≥3 A | 1 | 1 | |
| MPU6050 IMU | 1 | 1 | |
| INMP441 mic | 1 | 1 | |
| MAX98357A amp | 1 | 1 | |
| Speaker Ø23 × 5 mm, 8 Ω | 1 | 1 | |
| Rocker switch | 1 | 1 | |
| USB-C breakout | 1 | 1 | |
| Protoboard 60 × 38 mm | 1 | 1 | Trim from a 60 × 40. |
| Inline fuse holder + 3 A fuse | 1 | 1 | |
| Silicone wire 26 AWG | ~2 m | 2–3 m | |
| JST-XH / Dupont pairs | ~15 | 20 | |
| **M3 heat-set insert**, Ruthex Ø4.0 × 6 | **23** | 40 (sold in 100s) | You will ruin a few learning the technique. |
| M3 × 10 socket cap | **11** | 15 | 8 frame→columns and shells→base plate, 3 shell top tabs→bridge. |
| M3 × 12 socket cap | 2 | 5 | Neck spigot → bridge. |
| M3 × 16 socket cap | 2 | 5 | Head halves. |
| M3 nylon washer | 8 | 10 | Under the shell flange heads. |
| M2 × 6 self-tapper | 14 | 20 | 2 per servo × 7. |
| M2 × 8 self-tapper | 10 | 15 | Servo horns. |
| Steel rod Ø2 mm | 30 mm | 1 length | Beak hinge pin. |
| Piano wire Ø1.2 mm | ~40 mm | 1 length | Beak pushrod, Z-bend each end. |

Seven servos are used; the eighth and ninth are spares. **23 heat-set inserts**
is the exact count, not an estimate.

### Order these — penguin-specific

Nothing generic substitutes for these, and four of them carry hard dimensions
the CAD is modelled to.

- [ ] **ESP32-S3 DevKitC-1 N8R8** — must be the **S3 with 8 MB PSRAM**. A classic
      ESP32 or an N8R2 will not do: five of the seven servo pins do not exist on
      a classic ESP32, and the PSRAM is the only reason the on-device language
      model is possible later.
- [ ] **MG90S × 9** — one part number for every joint. ⚠ 22.8 × 12.2 × 22.7 mm.
- [ ] **MPU6050** — mandatory. No IMU, no balance loop, no fall detection.
- [ ] **INMP441** and **MAX98357A** — the I²S pair.
- [ ] **Speaker Ø23 × 5 mm, 8 Ω** — ⚠ hard dimension, the seat ring is modelled to it.
- [ ] **18650 × 2 + holder** — ⚠ 65 × 18 mm and 77 × 41 × 21 mm. Buy protected
      cells from a reputable seller; fake 18650s are rampant.
- [ ] **Buck converter 6 V ≥3 A** — ⚠ 30 × 22 mm, holes 24 × 16.
- [ ] **Ruthex M3 Ø4.0 × 6 inserts** — ⚠ the bosses are modelled to the Ruthex
      profile specifically. Another brand's taper may not seat.

### Check your leftovers first — generic maker stock

These are the same parts any project uses, so check what you have before
ordering. If you have all of them, the build drops to **~£75–95**.

- [ ] M3 socket caps — 10 mm ×15, 12 mm ×5, 16 mm ×5
- [ ] M3 nylon washers ×10
- [ ] M2 self-tappers — 6 mm ×20, 8 mm ×15
- [ ] Silicone wire 26 AWG, 2–3 m in a few colours
- [ ] JST-XH or Dupont connector pairs ×20
- [ ] Heat-shrink assortment
- [ ] Ø2 mm steel rod and Ø1.2 mm piano wire — a few cm of each
- [ ] Rocker switch — ⚠ needs a 19 × 13 cutout, so measure before assuming
- [ ] USB-C breakout — ⚠ 15 × 12 flange
- [ ] Protoboard — any 60 × 40 double-sided, trimmed to 38
- [ ] Inline fuse holder + 3 A blade fuse
- [ ] Soldering iron, and a tip you do not mind dedicating to heat-set inserts
- [ ] Digital calipers — for the ⚠ parts
- [ ] Filament — you are printing at 4p/g, so this is £6.40 regardless

### Checked against an existing parts drawer

Worked through one real leftovers list. The verdicts generalise, so they are
kept here.

| You have | Verdict | Why |
|---|---|---|
| **Classic ESP32 DevKitC** (spare) | ✅ **Use it** — verified | `pio run -e esp32dev` compiles clean: **RAM 36.2%, Flash 44.0%.** The pin map switches automatically on the build target. Two things had to change to get there, both now in the repo: the learning store drops to 224 slots (it overflowed DRAM by 42,688 bytes at 384), and the partition table becomes `huge_app.csv` (the stock 1.31 MB app partition could not hold a 1.35 MB binary). You only need the S3 if you later build the on-device LM. **Saves £12–19.** |
| **1S 2000 mAh LiPo + TP4056** | ❌ Not usable | 1S is 3.7 V and the servo rail needs 6 V, so you would need a boost, not the specified buck. 18 W from 3.7 V is a 5.5 A draw — 2.75C on a 2000 mAh cell, with heavy sag. Energy is 7.4 Wh against 22 Wh for 2× 18650, so ~40 min not 2 h. And MG90S torque at 4 V falls to ~1.8 kg·cm, putting the ankle at 82% of stall instead of 67%. The TP4056 is a **1S** charger and cannot charge a 2S pack either. |
| **Slide switches** | ❌ Order the rocker | ⚠ **Safety.** This switch breaks battery positive carrying 3 A+. Small multipack slide switches are typically rated 0.3–0.5 A. It is also the wrong shape for the 19 × 13 cutout. £1–2 is not worth a lithium fire. |
| **Prototype PCBs** (multipack) | ✅ Probably — check size | You need one at least **60 × 38 mm** after trimming. A 70 × 90 works; a 40 × 60 or 50 × 70 does not. |
| **M3 heat-set inserts** | ➡️ **Order Ruthex anyway** | The bosses are modelled to **Ruthex Ø4.0 × 6 mm** specifically, and common alternatives (Ø4.6 × 5.8, Ø5.0 × 6) either will not seat or will split the boss. Rather than measure and risk it, buy the Ruthex: £8–10 for 100 when you need 23. Keep whatever you already have for other projects. |
| **M3 screw assortment** | ✅ Use it | Check it has M3 × 10 (you need 11), × 12 (2) and × 16 (2). |
| **M3 nylon standoffs** | — Not needed | Not in the design. Note standoffs are not the 8 **nylon washers** that go under the shell flange heads — check the assortment, or any M3 washer will do. |
| **JST-PH connectors** | ✅ With one caveat | Fine for the head and leg disconnects. **Do not put the 6 V servo-rail trunk through PH** — it is rated ~2 A and that line hits 3 A+. Solder the trunk, or use XH. Individual servos peak under 1 A and are fine. |
| **Silicone hookup wire** | ✅ Check gauge | 26 AWG is specified; 22–28 all work, and thicker is better for the power trunk. |
| **Heatshrink** | ✅ Use it | |
| **ELEGOO kit** — breadboard, jumpers, LEDs, buzzer | ✅ Useful, not required | Not in the BOM, but breadboard the MPU6050 and confirm I²C before soldering anything into the robot. The LEDs are also a cheap way to try "eyes" before committing to round LCDs. |

**One more possible saving:** MG90S servos normally ship with a horn and
mounting screws. Nine servos may cover all 14 off M2 × 6 and 10 off M2 × 8 —
check what arrives before ordering those separately.

### The order, as a basket

Fifteen lines. This is the whole thing, assuming a spare classic ESP32 and a
stocked fastener drawer.

| Part | Qty | Budget | UK stock |
|---|--:|--:|--:|
| MG90S metal-gear servo | 9 | 18.00 | 21.50 |
| 18650 cell, protected | 2 | 12.00 | 18.00 |
| **Ruthex M3 Ø4.0 × 6 insert** | 100 | 8.00 | 10.00 |
| MAX98357A I²S amp | 1 | 2.50 | 5.70 |
| INMP441 I²S mic | 1 | 3.00 | 7.00 |
| MPU6050 IMU | 1 | 2.00 | 4.00 |
| Buck converter 6 V ≥3 A | 1 | 3.00 | 6.00 |
| Speaker Ø23 × 5 mm, 8 Ω | 1 | 2.00 | 4.00 |
| 2× 18650 holder | 1 | 2.00 | 4.00 |
| USB-C breakout | 1 | 2.00 | 4.00 |
| Inline fuse holder + 3 A fuse | 1 | 2.00 | 4.00 |
| Rocker switch, 19 × 13 | 1 | 1.00 | 2.00 |
| Ø2 mm steel rod | 1 | 2.00 | 4.00 |
| Ø1.2 mm piano wire | 1 | 2.00 | 4.00 |
| M3 nylon washer | 10 | 2.00 | 4.00 |
| Filament, 158 g at 4p/g | — | 6.32 | 6.32 |
| **Total** | | **~£70** | **~£109** |

Order the servos and the ESP32-S3 (if you ever want one) first — they are the
long-lead items. Everything else is stocked.

With the spare ESP32 used, Ruthex inserts ordered and filament at 4p/g, the
order comes to **~£70 budget / ~£109 UK stock** — down from ~£105 / ~£171 with
an empty drawer. Drop the Ruthex and it is ~£62 / ~£99, but see the row above.

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
| 15 / 5 / 5 | M3 × 10, × 12, × 16 socket cap | 6 | 12 | Frame to columns, shell flanges, neck spigot, head halves. An M3 assortment box covers all three. |
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

**At the Bath per-gram rate of 4p/g, the entire robot is £6.32 of plastic.**
158 g at 20% infill. Filament is not a meaningful line item in this build, so
choose material on mechanics, not cost.

| | Mass | At 4p/g | Buying spools instead |
|---|--:|--:|--:|
| Whole robot, 20% infill | 158 g | **£6.32** | £39–65 for three spools |
| Whole robot, solid | 316 g | £12.64 | |
| Reprinting the six structural parts | 120 g | £4.80 | |

Spool prices for reference if you print at home: budget PETG/PLA is £12–25/kg,
and premium runs much higher — Prusament PETG is about **£37/kg** in the UK.

### Can it all be one material?

**Yes. Print everything in PETG.** The dual-material split exists for good
reasons, but all of them point at PETG as the single choice, and the cost
argument that favoured PLA disappears at 4p/g.

| | All PETG — recommended | All PLA |
|---|---|---|
| **Impact** | Tough. Survives being dropped. | Brittle. Cracks at the thin ankle and flipper sections. |
| **Heat** | Tg ~80 °C. Fine against a warm servo. | Tg ~60 °C. The legs and frame hold servos that reach 50 °C+ under load, and they carry static weight all day — PLA creeps. |
| **Stiffness** | ~2.1 GPa | ~3.5 GPa — actually *stiffer*, despite what `BOM.md` implies |
| **Surface finish** | Fussier. Stringing, and less crisp on the head shells. | Excellent. The reason PLA was specified for the visible parts. |
| **Mass change** | +3.9 g (+0.7%) | −3.6 g (−0.6%) |

**Why PETG wins for this particular robot: it falls over on purpose.** It cannot
self-right — it detects the fall, tries once, then waggles to be picked up. A
robot whose normal operating mode includes faceplanting onto a desk wants impact
resistance far more than it wants a flawless shell. The feet, ankles and
flippers are exactly the thin sections that take those impacts, and exactly
where PLA is weakest.

The cost of being wrong is small either way: the mass change is under 1%, so the
tuned gait stays valid, and reprinting the six structural parts is **£4.80**.

**If you would rather have the finish**, all PLA is a reasonable choice for a
robot that lives on a desk and gets handled gently. Watch `core_frame`,
`leg_L/R`, `foot_L/R` and `base_plate` — those six are the ones that will creep
or crack first. Do not leave an all-PLA build on a sunny windowsill or in a car.

**Do not mix materials within a part**, and do not switch the feet to PLA just
to get the orange — they sit against the ankle servo and take the landing loads.
Paint them instead.

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
| **Spare classic ESP32 + a stocked parts drawer** (§0) — the realistic case | **~£70** |
| …the same, buying UK stock rather than AliExpress | **~£109** |
| **You have all the generic stock** (§0) — only the penguin-specific parts | **~£75–95** |
| **Cheapest** — AliExpress throughout, uni filament at 4p/g, own tools | **~£105** |
| **Realistic mix** — UK for the board, battery and audio; budget for the rest | **~£136** |
| **All UK stock**, uni filament, own tools | **~£171** |
| **All UK stock** plus a soldering iron and calipers | **~£225** |

Printing at home on retail spools instead of the uni's 4p/g adds £33–59.

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

1. **The feet are PETG but render orange.** PETG is specified for *toughness*
   and heat resistance next to the ankle servos — not stiffness, where PLA
   actually wins — and the colour comes from the render palette. Orange PETG is
   uncommon and you need 14 g of it, so: print them in whatever PETG you have
   and paint them, or accept grey feet. Do not switch them to PLA to get the
   colour — they sit against the servo and take the landing loads.
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

**`CAD/exports/stl_print/PRINT_PLAN.md` has the full plan** — print order, per-part
supports and masses, colour grouping, and the PETG temperatures.

| | |
|---|---|
| Material | **PETG throughout** — recommended, see §4 |
| | *As originally designed:* PETG for base_plate, core_frame, legs, feet; PLA for the shells, head, beak and flippers |
| Nozzle / bed | 240 / 80 °C for PETG |
| Layer | 0.2 mm |
| Walls | 3 perimeters |
| Infill | 20–25% gyroid |
| Supports | core_frame (bridge cantilever, cheek shelves), legs (ankle servo cavity), feet (bracket overhang), flippers (under the hub) |
| Largest footprint | body shells, 106 × 115 mm — fits a 180 mm bed |
| Tallest | core_frame, 80 mm |
| First print | `beak_upper` — 15 minutes, checks accuracy before you commit hours |

---

## One thing to get right at assembly

**Fit the flipper horns with the flipper hanging straight down and the servo at
its mid-point.** The linkage allows 280° but an MG90S turns 180°, so the useful
window is −45°…+135°. Out by 45° and half the gestures hit the end stop.

`docs/ASSEMBLY.md` is in build order, because several things become unreachable
once something else is in.
