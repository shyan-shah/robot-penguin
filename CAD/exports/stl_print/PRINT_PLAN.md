# Print plan — all PETG

14 parts, **all in PETG**, ~160 g of filament, about £6.40 at the Bath 4p/g rate.

> **Why there is no separate "PETG print set".** An STL contains triangles and
> nothing else — no material, no colour, no print settings. Re-exporting these
> files against a PETG material assignment produces byte-identical output, so
> there is nothing to re-export. The material decision lives in the slicer and
> in this file. The STLs in this folder are already correct and verified
> watertight to within 0.37% of the CAD.

See `docs/SHOPPING_LIST.md` for why PETG throughout, in short: the robot cannot
self-right, so falling over is part of normal operation, and PETG survives that
where PLA cracks. Switching the eight originally-PLA parts to PETG adds **3.9 g**
(+0.7%), so the tuned gait is unaffected.

---

## Settings

| | |
|---|---|
| Material | PETG throughout |
| Nozzle | 240 °C (PETG) |
| Bed | 80 °C |
| Layer | 0.2 mm |
| Walls | 3 perimeters |
| Infill | 20–25% gyroid |
| Cooling | 30–50%. PETG wants less than PLA — too much and layer adhesion suffers, which is the whole reason for choosing it. |
| Retraction | Tune it. Stringing is PETG's one real vice and the head shells show it most. |
| Largest footprint | 106 × 115 mm (`body_front`, `body_back`) — fits a 180 mm bed one at a time |
| Tallest | 80 mm (`core_frame`) |

Dry the filament if it has been open a while. Wet PETG strings and pops, and the
head shells are the visible parts.

---

## Print order

Deliberately not "biggest first" — this order front-loads the parts whose
dimensional accuracy everything else depends on, and gets a cheap failure in
early rather than six hours in.

| # | Part | Qty | Colour | Infill | Supports | Solid | Printed |
|---|---|--:|---|--:|---|--:|--:|
| 1 | `beak_upper` | 1 | orange | 25% | no | 1.5 g | ~1 g |
| 2 | `core_frame` | 1 | grey | **25%** | **yes** | 55.6 g | ~31 g |
| 3 | `base_plate` | 1 | grey | **25%** | no | 33.3 g | ~18 g |
| 4 | `leg_L`, `leg_R` | 2 | grey | **25%** | **yes** | 17.7 g ea | ~10 g ea |
| 5 | `foot_L`, `foot_R` | 2 | orange | **25%** | **yes** | 14.1 g ea | ~8 g ea |
| 6 | `body_front` | 1 | white | 20% | no | 51.5 g | ~26 g |
| 7 | `body_back` | 1 | black | 20% | no | 53.7 g | ~27 g |
| 8 | `head_front` | 1 | white | 20% | no | 21.5 g | ~11 g |
| 9 | `head_back` | 1 | black | 20% | no | 23.8 g | ~12 g |
| 10 | `flipper_L`, `flipper_R` | 2 | black | 25% | **yes** | 6.5 g ea | ~4 g ea |
| 11 | `beak_lower` | 1 | orange | 25% | no | 2.1 g | ~1 g |
| | **14 parts** | | | | 6 need supports | **319 g** | **~171 g** |

At 4p/g that is **£6.84**.

**Why the order is what it is.** `beak_upper` is a 15-minute test print that
catches a mis-set printer before you commit hours. `core_frame` next because
every servo and board locates off it, and it is where you confirm a Ruthex
Ø4.0 × 6 seats in a boss. Then `base_plate` — check the 60 × 38 protoboard
pocket and the 77 × 41 battery-holder footprint against the real parts. Legs
and feet next, so you can stand the lower half up and see it balance before
printing anything cosmetic. Shells last: `body_front` is the longest print,
and `body_back` is where you verify the USB-C and rocker-switch cutouts.

**Why 25% on the structural parts and 20% on the shells.** The documented
spec is 20–25% gyroid throughout; this splits it by what the part does.
`core_frame`, `base_plate`, the legs and the feet carry load, hold servos and
take landing impacts. The shells are cosmetic and are the largest parts, so
they are where lower infill actually saves anything. The flippers and beak are
small enough that infill barely moves the number — 25% costs nothing there.

Supports are needed on six parts: `core_frame`, both legs, both feet, both
flippers. `docs/BOM.md` says why for each.

---

## Colour grouping

If you are changing filament by colour rather than printing it all in one, these
are the four plates. The two greys in the renders are close enough to share one
spool.

| Plate | Colour | Parts | At 20% |
|---|---|---|--:|
| A | Grey `#5C5C64` | `base_plate`, `core_frame`, `leg_L`, `leg_R` | ~63 g |
| B | White `#EEEEF3` | `body_front`, `head_front` | ~36 g |
| C | Near-black `#1A1A20` | `body_back`, `head_back`, `flipper_L`, `flipper_R` | ~44 g |
| D | Orange `#F2740E` | `foot_L`, `foot_R`, `beak_upper`, `beak_lower` | ~16 g |

**Plate D is only 16 g.** Orange PETG is uncommon and not worth sourcing for
that: print those four in whatever you have and paint them. Do not switch the
feet to PLA to get the colour — they sit against the ankle servo and take the
landing loads.

Printing the whole robot in one colour is entirely fine. It will look like a
grey penguin until you paint it.

---

## Before you start

1. **Check a Ruthex insert fits a test boss** off the `core_frame` print. 23
   inserts is a lot to discover a problem on.
2. **Measure the ⚠ parts** in `docs/SHOPPING_LIST.md` against what arrived —
   speaker Ø23 × 5, battery holder 77 × 41 × 21, buck 30 × 22, switch 19 × 13,
   USB-C flange 15 × 12. The model is parametric, so a wrong dimension is a
   spreadsheet edit and a rebuild, not a redesign.
3. **Trim the protoboard to 60 × 38.** A stock 60 × 40 leaves the stack 1 mm
   over.
