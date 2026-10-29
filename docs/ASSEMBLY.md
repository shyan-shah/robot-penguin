# Assembly

Build order matters here — a few things become unreachable once something else is
in. Do it in this order and nothing has to come back apart.

Set aside an evening. The fiddly parts are the beak pushrod and getting the servo
horns on at the right angle.

---

## Before you start: centre every servo

**Do this first, before anything is screwed to anything.** Plug each MG90S into
the ESP32 one at a time and command it to 90° (the firmware's `cmd` zero). Mark
the horn position. A servo assembled off-centre costs you half its travel and you
will not find out until the robot is together.

Flash the firmware with all `TRIM` values at 0 for this.

---

## 1. Base plate and hips (do this first — it gets buried)

1. Press **4 heat-set inserts** into the column tops and **4** into the shell
   bosses. Use a soldering iron at 200 °C, press until flush, let it cool before
   releasing.
2. Drop **SERVO_HIP_R** and **SERVO_HIP_L** into their pockets at X ±26, output
   shaft **pointing down**. 2× M2 × 6 self-tappers each.
3. Route both servo leads up through the cable slots.

> The hip servos cannot be fitted or removed once the core frame is bolted on.
> If you are unsure about a servo, replace it now.

## 2. Legs and feet

4. Press the ankle servos into the leg cavities, shaft pointing **outboard**
   (+Y in the leg's own frame). 2× M2 × 6 each.
5. Fit the foot bracket over the ankle servo horn. The foot's toe points
   **forward**; it is easy to get this 180° out — check before screwing.
   M2 × 8 through the horn.
6. Bolt each leg onto its hip servo horn. **Set the hip to 0° first**, and have
   the leg pointing straight forward when you tighten it.

At this point stand it on a table. It should balance on its own feet with the
servos unpowered. If it leans, check the horn angles before going further.

## 3. Core frame and electronics

7. Press **5 inserts** into the bridge and **4** into the protoboard bosses,
   **4** into the buck bosses.
8. Bolt the frame onto the base-plate columns — 4× M3 × 10, **countersunk**, they
   must sit flush in the 3 mm tray.
9. Fit the **buck converter** on its bosses. Set it to **6.0 V before wiring
   anything to it.** Check with a meter.
10. Fit the **protoboard**, then the ESP32-S3, the I²S amp and the MPU6050 onto it.
    The IMU must be rigid with the frame — tape or a loose mount will ruin the
    balance loop.
11. Fit the **battery holder** right at the back, as low as it goes. Fuse in the
    battery positive line, then the switch.

## 4. Flippers

12. Press the flipper servos into the frame cheeks, shafts pointing **outboard**.
13. Fit each flipper onto its horn with the flipper **hanging straight down**
    (that is 90° in the firmware's convention, which is the rest pose).

## 5. Head — the beak is the fiddly bit

14. Press **2 inserts** for the head join screws.
15. Fit the **beak servo** low in the skull on its two bosses.
16. Thread the **1.2 mm pushrod** through the head-front slot and hook its Z-bend
    into the lower beak's lever hole.
17. Lay `beak_lower` between the hinge bosses and push the **Ø2 × 30 pin** in from
    one cheek, through boss → arm → arm → boss. A drop of CA on the last 2 mm.
18. Peg `beak_upper` into its Ø8 socket.
19. Connect the pushrod's other Z-bend to the servo horn **with the beak closed
    and the servo at 0°**. Adjust the Z-bend until closed-is-closed; this is the
    one adjustment worth getting right.
20. Fit the **speaker** into its ring behind the grille, and the **mic** flat
    against the crown. Foam tape for both.
21. Join the head halves — 2× M3 × 16.

> The pushrod crosses the head's split plane, so the two halves cannot be fully
> separated once it is connected. Attach the servo end last, and disconnect it
> first if you ever open the head.

## 6. Shells and closing up

22. Run the head cable down the neck spigot before bolting the head to the bridge
    (2× M3 × 12).
23. Offer up `body_back`, then `body_front` — the front has the overlap lip and
    goes on second.
24. 4× M3 × 10 up through the bottom flanges into the base-plate bosses, 3× M3 × 10
    through the top tabs into the bridge.
25. Fit the switch and the USB-C breakout into their back-panel pads.

---

## Wiring

```
2× 18650 (7.4 V)
   └─ 3 A fuse ─ rocker switch ─┬─ buck converter ─ 6.0 V ─ servo rail (7 servos)
                                └─ ESP32-S3 VIN
```

| Signal | ESP32-S3 pin |
|---|---|
| hip_R / hip_L | 4 / 5 |
| ankle_R / ankle_L | 6 / 7 |
| flipper_R / flipper_L | 15 / 16 |
| beak | 17 |
| MPU6050 SDA / SCL | 8 / 9 |
| I²S mic BCLK / WS / DATA | 10 / 11 / 12 |
| I²S amp BCLK / LRC / DIN | 13 / 14 / 18 |

> **These numbers changed.** The table used to carry classic-ESP32 pins, which do
> not work on the S3 this build specifies: GPIO 22–25 do not exist on an S3 at
> all, and 26–37 are taken by the SPI flash and the octal PSRAM on an N8R8. Five
> of the seven servo pins were unusable. Safe general-purpose pins on this board
> are **1–18, 21, 38–42, 47, 48** (19/20 are native USB, 43/44 are UART0), and
> everything above is inside that set with room to spare.

**Give the servos their own ground path back to the buck**, not through the
ESP32's ground pin. Seven MG90S starting together will brown out a dev board that
is sharing a thin ground.

Add a **1000 µF capacitor across the servo rail** at the protoboard. It is the
difference between a robot that works and one that resets every time it waves.

---

## First power-on

1. Servos **unplugged**. Power up, check 6.0 V at the rail and that the ESP32
   boots.
2. Plug in **one** servo. Check it centres rather than slamming to an end stop.
3. Add the rest one at a time.
4. Set `TRIM[]` in `main.cpp` so that every joint reads true zero when commanded
   zero. This is the step people skip and then wonder why it walks in a curve.
5. Stand it up and let the balance loop settle. The ankles should make small
   continuous corrections — if they buzz or oscillate, halve `BAL_KP`.

## If it walks in a circle

Almost always servo trim, not the gait. Check the hips read true zero. If one hip
is 5° off, the penguin turns a few degrees every step and you get a slow circle.
