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

| # | Part | Supports | Solid | At 20% | Why here |
|---|---|---|--:|--:|---|
| 1 | `beak_upper` | no | 1.5 g | ~1 g | **Test print.** ~15 minutes. Check dimensional accuracy and surface finish before committing hours of PETG. |
| 2 | `core_frame` | **yes** — bridge cantilever, cheek shelves | 55.6 g | ~28 g | The skeleton. Every servo and board locates off it, so if the printer is off, you want to know now. Check the 23 insert bosses accept a Ruthex Ø4.0 × 6. |
| 3 | `base_plate` | no | 33.3 g | ~17 g | Holds the battery, buck and protoboard. Verify the 60 × 38 protoboard pocket and the 77 × 41 holder footprint. |
| 4 | `leg_L`, `leg_R` | **yes** — ankle servo cavity | 17.7 g ea | ~9 g ea | Test-fit an MG90S in the cavity before printing anything cosmetic. |
| 5 | `foot_L`, `foot_R` | **yes** — bracket overhang | 14.1 g ea | ~7 g ea | Then you can stand the lower half up and check it balances. |
| 6 | `body_front` | no | 51.5 g | ~26 g | Longest print. Flange holes must line up with the base plate. |
| 7 | `body_back` | no | 53.7 g | ~27 g | Check the USB-C and rocker-switch cutouts against the real parts. |
| 8 | `head_front` | no | 21.5 g | ~11 g | |
| 9 | `head_back` | no | 23.8 g | ~12 g | Mic holes in the crown. |
| 10 | `flipper_L`, `flipper_R` | **yes** — under the hub | 6.5 g ea | ~3 g ea | |
| 11 | `beak_lower` | no | 2.1 g | ~1 g | Last. Needs the Ø2 mm hinge pin and the Ø1.2 mm pushrod. |
| | **Total** | | **319 g** | **~160 g** | **≈ £6.40** |

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
