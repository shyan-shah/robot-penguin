"""Round two of the tail prop, after round one came back worse than no prop.

Round one put the spur BELOW horizontal, pointing down and back, because that is
what you draw when you think "kickstand". The sweep said every one of those nine
geometries was worse than the bare robot - six of them much worse. The reason is
geometric and obvious in hindsight: lying on its back, the body's -Z now points
roughly UP, so a spur angled below horizontal in the standing frame points up
into the air. It never touches the floor. All it contributes is 50-100 g at a
long lever arm behind the centre of mass, which is exactly the wrong place.

So invert it. A spur that leaves the back shell pointing back and UP in the
standing frame is the one that touches the floor first when the penguin lands on
its back. It then does two useful things:

  1  it holds the body off flat, so the centre of mass starts nearer the tip-over
     line instead of dead centre
  2  it is a fixed pivot well behind the shoulders, so the flipper push rotates
     the body about the tail tip rather than having to lift it

It also cannot foul the floor when standing or walking, whatever its length,
because it points away from the ground. That removes the clearance constraint
that limited round one, so this grid sweeps length and height instead.

Every geometry is searched with the same budget, and the BARE robot is searched
with that same budget too, in the same run. Without that baseline a +0.05 in
peak_up is indistinguishable from search noise.
"""
import json
import math
import os
import time

import numpy as np

import penguin_env
from prop_study import make_variant, PROP_SECTION, PROP_DENSITY, FLOOR_Z

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
URDF = os.path.join(HERE, "penguin.urdf")

# (attach_y, attach_z, length, up_deg)  - up_deg is ABOVE horizontal this time
#
# Round 2 found the shape of the answer: attach HIGH on the shell and point the
# spur nearly straight BACK. Best cell was 90 mm at 10 deg off Z 55, peak 0.708
# against 0.139 for the bare robot on the same budget. It sat on the edge of the
# grid in length and at the bottom of the angle range, so round 3 pushes both.
GRID = [(-38.0, 45.0, 110.0, 10.0),
        (-38.0, 55.0, 110.0, 0.0),
        (-38.0, 55.0, 110.0, 10.0),
        (-38.0, 55.0, 110.0, 20.0),
        (-38.0, 55.0, 130.0, 10.0),
        (-38.0, 55.0, 150.0, 10.0),
        (-38.0, 65.0, 110.0, 10.0),
        (-38.0, 65.0, 130.0, 0.0),
        (-38.0, 55.0, 90.0, 10.0)]      # round 2's best, repeated to show variance


def tip(ay, az, length, up_deg):
    a = math.radians(up_deg)
    return (ay - length * math.cos(a), az + length * math.sin(a))


def _eval(job):
    import getup_catch as G
    idx, spec = job
    path = os.path.join(HERE, "penguin_p3_%d.urdf" % idx)
    if spec is None:                     # the baseline: no prop at all
        g, path = 0.0, URDF
    else:
        ay, az, length, up_deg = spec
        g = make_variant(ay, az, length, -up_deg, path)   # negative = above horizontal
    sim = penguin_env.PenguinSim(urdf=path)
    best = G.search(sim, "back", iters=12, pop=16)
    sim.close()
    if spec is not None:
        try:
            os.remove(path)
        except OSError:
            pass
    row = {"prop_g": g, "peak_up": best["peak_up"], "final_up": best["final_up"],
           "recovered": best["recovered"], "params": best["params"]}
    if spec is None:
        row.update({"length_mm": 0.0, "up_deg": 0.0, "tip_y": 0.0, "tip_z": 0.0})
    else:
        ty, tz = tip(*spec)
        row.update({"length_mm": spec[2], "up_deg": spec[3], "attach_z": spec[1],
                    "tip_y": ty, "tip_z": tz})
    return row


if __name__ == "__main__":
    import multiprocessing as mp
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    log("=== tail prop, round 3: longer, pushing round 2's best corner ===")
    log("    round 2 reached peak 0.708 at 90 mm / 10 deg / Z 55 (bare control 0.139)")
    log("    same search budget for every row, bare robot included as the control")
    log("")
    t0 = time.time()
    jobs = [(0, None)] + [(i + 1, g) for i, g in enumerate(GRID)]
    with mp.Pool(5) as pool:
        rows = pool.map(_eval, jobs)
    base = rows[0]
    log("%6s %6s %6s %8s %8s %7s   %s"
        % ("len", "up", "att Z", "tip Y", "tip Z", "mass g", "result"))
    log("%6s %6s %6s %8s %8s %7.1f   peak %.3f  final %.3f   <- BARE ROBOT (control)"
        % ("-", "-", "-", "-", "-", 0.0, base["peak_up"], base["final_up"]))
    for r in rows[1:]:
        log("%6.0f %6.0f %6.0f %8.1f %8.1f %7.1f   peak %.3f  final %.3f  %s"
            % (r["length_mm"], r["up_deg"], r["attach_z"], r["tip_y"], r["tip_z"],
               r["prop_g"], r["peak_up"], r["final_up"],
               "STANDS UP" if r["recovered"] else ""))
    ok = [r for r in rows[1:] if r["recovered"]]
    log("")
    if ok:
        b = max(ok, key=lambda r: r["final_up"])
        log("WORKS: %.0f mm spur %.0f deg above horizontal at Z %.0f (%.1f g)"
            % (b["length_mm"], b["up_deg"], b["attach_z"], b["prop_g"]))
    else:
        b = max(rows[1:], key=lambda r: r["peak_up"])
        log("none stands up. best %.0f mm at %.0f deg: peak %.3f vs %.3f bare (%+.3f)"
            % (b["length_mm"], b["up_deg"], b["peak_up"], base["peak_up"],
               b["peak_up"] - base["peak_up"]))
    json.dump(rows, open(os.path.join(OUT, "prop_study_r3.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "prop_study_r3_log.txt"), "w").write(chr(10).join(lines) + chr(10))
