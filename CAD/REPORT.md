# Robot penguin — CAD report

Built in Autodesk Inventor 2027 through the Inventor MCP. All files under
`…\Year 4\Projects\Penguin\CAD`.

**Status: 14 printed parts, 29 components, every sketch fully constrained, every
dimension parameter-driven. All-pairs interference clear at rest and through the
full travel of all seven joints. Print-ready STLs exported and verified
watertight.**

---

## 1. Files

| File | What |
|---|---|
| `penguin.iam` | Master assembly — 29 components, 54 constraints, 7 live joints |
| `penguin_params.xlsx` | 62 shared parameters, linked into every part |
| `base_plate.ipt` … `flipper_L.ipt` | 14 printed parts |
| `dummies\*.ipt` | 11 purchased-part dummies |
| `exports\stl_print\` | **14 print-ready STLs** — oriented, on Z=0, centred, watertight |
| `exports\stl_assembled\` | The same parts in as-designed positions |
| `exports\penguin.stp` | STEP of the whole assembly |
| `exports\mass_properties.json` | Per-link mass, CoM and inertia — feeds the simulation |
| `renders\` | Build and pose renders |

---

## 2. Overall

| | |
|---|---|
| Total mass | **579.7 g** (solid print; ~425 g at 20 % infill) |
| Printed parts | 315.2 g solid |
| Purchased | 264.5 g |
| CoM | X −0.13, Y 1.08, Z 40.79 mm |
| CoM above floor | **104.8 mm** |
| Overall size | 120.1 × 102.4 × **229.4 mm** tall |
| Stance (hip half-offset) | **±26 mm** |
| Gap between the feet | 14.0 mm |
| Ankle axis above floor | 24.0 mm |
| Tip-over angle | **30.7°** (closed form in MATLAB *and* PyBullet, independently) |

### Per part

| Part | Mass | Features | Sketches | Constraint status |
|---|---|---|---|---|
| base_plate | 33.29 g | 11 | 7 | all FC |
| core_frame | 55.62 g | 30 | 31 | all FC |
| body_front | 50.10 g | 17 | 20 | all FC |
| body_back | 52.26 g | 12 | 14 | all FC |
| head_front | 20.98 g | 14 | 20 | all FC |
| head_back | 23.28 g | 11 | 15 | all FC |
| beak_upper | 1.44 g | 3 | 3 | all FC |
| beak_lower | 2.03 g | 11 | 11 | all FC |
| leg_R / leg_L | 17.74 g each | 8 | 8 | all FC |
| foot_R / foot_L | 14.06 g each | 5 | 4 | all FC |
| flipper_R / flipper_L | 6.33 g each | 4 | 6 | all FC |

Materials: PETG (1.27 g/cc) for base plate, frame, legs and feet; PLA (1.24) for
shells, head, beak and flippers. Both created as document materials since
Inventor ships neither.

---

## 3. The seven joints

| Joint | Axis | Location | Travel | Driven by |
|---|---|---|---|---|
| hip_R / hip_L | Z (vertical) | X ±26, Y 0 | ±30° useful, ±90° mechanical | `hip_ang_R/L` |
| ankle_R / ankle_L | Y (fore-aft) | X ±26, Z −40 | ±25° | `ank_ang_R/L` |
| flipper_R / flipper_L | X (lateral) | Y 0, Z 78 | −95…185° | `flip_ang_R/L` |
| beak | X (lateral) | Y 31, Z 131 | 0…30° | `beak_ang` |

Each joint is a work axis built from two parametric work planes, constrained with
an axis mate + an origin-point-on-plane mate + a **directed** angle constraint.

> **The angle constraints must be directed** (`SolutionType = 78594`). A
> plane-to-plane angle has a ±180° ambiguity, and after driving the hips to ±90°
> the solver snapped the feet round backwards — `FOOT_R` came back at Y −37…18
> instead of −18…37, and a pose that had been clear started showing a 1027 mm³
> clash. Rebuilt directed, it is stable through the full travel.

### Positional representations

`[Primary]`, `Neutral`, `Waddle L`, `Waddle R`, `Wave`, `Bow` — all verified
interference-free. ("Bow" is the nearest the mechanism can do: there is no pitch
axis anywhere in the robot, so it cannot actually lean forward.)

---

## 4. Interference

**All-pairs, all 29 components, at rest: clear.**

Through the joint travel — rest, beak 30°, ankles ±25°, hips ±30° both ways,
flippers up/forward/back, and everything combined: **clear at every pose.**

> The earlier version of this report said "interference-free" on the strength of a
> check that only compared **moving parts against everything else**. Static pairs
> were never tested against each other. A genuine all-pairs check found
> **7295 mm³ of overlap between the two head halves** — the split cutter was a
> 300 mm square centred on the origin, so it reached Z 150 while the head tops out
> at 165.65, and the top 15 mm existed in both halves. It would have printed as
> two parts that cannot be assembled.

Every clash found and fixed, in order:

| # | Clash | Volume | Cause | Fix |
|---|---|---|---|---|
| 1 | HEAD_BACK ~ HEAD_FRONT | **7295 mm³** | split cutter too small for the head's Z range | `cut_big` 300 → 400 |
| 2 | Shells ~ CORE_FRAME | 1284 mm³ | rectangular frame corners outside an elliptical shell | `ShellEnvelope` loft + `TrimToShell` intersect |
| 3 | HEAD ×2 ~ DF2301Q | 1235 mm³ | the board does not fit in a 70 × 62 × 58 head | board removed; see §6 |
| 4 | BUCK ~ BATTERY | 2100 mm³ | only 9.2 mm between the battery lip and the spine wall | `tray_Yc` −2 → −6, buck bosses 5 → 2 mm |
| 5 | LEG ~ SERVO_ANKLE ×2 | 421 mm³ | my own constraint error — servo attached 180° rotated | mate/flush pairing corrected |
| 6 | SPEAKER ~ HEAD_BACK | 434 mm³ | speaker buried in the curved back wall | `spk_Y` −28.5 → −24.0 |
| 7 | BASE_PLATE ~ SERVO_HIP ×2 | 110 mm³ | widened hips pushed the servo into a frame column | `col_x` 36 → 38 |
| 8 | PROTOBOARD ~ BUCK | 96 mm³ | 2 mm of stack overlap | protoboard trimmed 60×40 → 60×38 |
| 9 | BODY_BACK ~ SWITCH / USB | 101 / 884 mm³ | flat flange on a doubly-curved shell | surface-normal mounting pads |
| 10 | FLIPPER ×2 ~ shells | 56 mm³ each | Ø20 hub through a Ø14 notch | `notch_extra` 2 → 8 |
| 11 | BEAK_LOWER ~ HEAD_FRONT | 224 mm³ | beak pivot inside the head | pivot moved outside; see §5 |
| 12 | BODY_FRONT ~ BODY_BACK | 8.2 mm³ | overlap lip ran up into the neck | `LipTrimTop` above Z 95 |

---

## 5. The moving beak

`beak.ipt` became `beak_upper` (fixed, pegs into the head) and `beak_lower`
(hinged). The split was made with one plane through the beak's own axis:
1159.2 + 775.0 = **1934.2 mm³, exactly the original** — nothing lost.

**The pivot had to go outside the head.** At (Y 24, Z 139.5), inside the skull,
the mandible's rear face sweeps into the head's front surface and clashes from
the first degree of opening. Moved to the beak's rear-bottom corner
(**Y 31, Z 131**), the rear face swings *forward*, away from the head, and
nothing needs relieving. Clean 0–30°.

- Hinge: Ø2 × 30 mm steel pin through the cheeks, pushed in from either side
- Drive: MG90S low in the skull, 1.2 mm wire pushrod with a Z-bend each end
- Clearance between the mandibles: 0.3 mm

Also in the head now: a 23 mm speaker seated behind the existing grille, and an
I²S microphone flat against the crown.

---

## 6. Things you need to decide

1. **The DF2301Q was removed.** It does not fit the head (49 × 32 × 12 against a
   70 × 62 × 58 shell), and with an I²S mic and a cloud LLM its offline
   fixed-command recognition is redundant. Saves 12 g and freed the head for the
   beak servo. *If you already own one it can go in the body with a vent, at the
   cost of the moving beak.*
2. **Stance widened `hip_x` 22 → 26.** Buys 21.7 mm of foot clearance instead of
   16.7, a 30.7° tip-over instead of 28.3°, and clash-free ±30° hip yaw. Cost: the
   feet sit 4 mm further out each side and the frame columns moved to X 38.
3. **Protoboard trimmed to 60 × 38.** The buck/board stack is 1 mm over otherwise.
4. **Soles rockered R3** so a foot edge cannot catch on carpet. Costs 2.8 % of the
   foot's volume.
5. **`Z_flip` dropped 85 → 78** (your earlier approval).
6. **Flipper notch widened** Ø14 → Ø20 to pass the stand-off hub.
7. **Panel pads** on the back are built on *fixed* work planes. Everything drawn
   on them is parametric, but they will not re-aim if the body sections change.
8. **`Z_ankle` is a local parameter in both `leg_*` and `foot_*`**, not shared.
   They must stay equal or the ankle axis mate fails — loudly, not silently.
9. **Assumed, not from your spec:** MG90S dome 3.3 / spline Ø4.8; buck holes
   24 × 16; eye holes X ±16 Z 150; mic holes X ±8 Z 159; beak 22 × 14 × 19;
   speaker grille 8 × Ø2 on Ø20 PCD; head screws X ±28.8; leg 20 × 27.5;
   flipper hub Ø20.

---

## 7. Not done

- **`penguin.ipn` exploded view and MP4.** Inventor's presentation API needs an
  interactive insert; `Scenes.Add` opens a modal dialog that blocks every API
  call and has to be closed with a Win32 message. Not scriptable from here.
- **3MF export** refused by Inventor. STEP and STL are both exported.
- Speaker dummy mass is 2.1 g; a real 23 mm speaker is 5–8 g. A ~4 g
  under-estimate on 580 g.
