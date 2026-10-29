"""Round 4: with a real stand-up move, what is the SHORTEST tail that works?

Rounds 2 and 3 searched a controller whose last stage plants the feet and hands
over to the balancer, so the robot finished reclined against the tail at 34
degrees. Verifying that pose (prop_verify.py) showed 96% of its weight already on
its feet, which means the remaining job is not lifting but leaning - so
getup_tail.py adds a stage D that throws the flippers forward and pushes with the
ankles.

Length is the thing to minimise, not maximise. A 150 mm spur is longer than the
body is tall, it would look absurd, and on its back it carries the robot on a
cantilever: 5.7 N at that lever is 0.5 Nm into a 2.4 mm printed shell wall. Every
20 mm off the tail is worth real structural margin. So this sweeps DOWN from the
length round 3 liked and reports the shortest one that still stands up.

The bare robot is searched with the same budget as the control, as before.
"""
import json
import os
import time

import penguin_env
from prop_study import make_variant

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
URDF = os.path.join(HERE, "penguin.urdf")

ATTACH_Y, ATTACH_Z, UP_DEG = -38.0, 55.0, 10.0
LENGTHS = [0.0, 50.0, 70.0, 90.0, 110.0, 130.0]     # 0.0 = bare control


def _eval(job):
    import getup_tail as G
    idx, length = job
    if length <= 0.0:
        path, g = URDF, 0.0
    else:
        path = os.path.join(HERE, "penguin_p4_%d.urdf" % idx)
        g = make_variant(ATTACH_Y, ATTACH_Z, length, -UP_DEG, path)
    sim = penguin_env.PenguinSim(urdf=path)
    best = G.search(sim, "back", iters=14, pop=20, log=lambda s: None)
    sim.close()
    if length > 0.0:
        try:
            os.remove(path)
        except OSError:
            pass
    return dict(best, length_mm=length, prop_g=g)


if __name__ == "__main__":
    import multiprocessing as mp
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    log("=== tail prop, round 4: four-stage recovery, shortest tail that works ===")
    log("    spur off Y %.0f, Z %.0f, %.0f deg above horizontal; length swept"
        % (ATTACH_Y, ATTACH_Z, UP_DEG))
    log("    stage D (flippers forward + ankle push) is the new part")
    log("")
    t0 = time.time()
    with mp.Pool(6) as pool:
        rows = pool.map(_eval, list(enumerate(LENGTHS)))
    log("%7s %7s   %s" % ("len", "mass g", "result"))
    for r in rows:
        tag = "  <- BARE ROBOT (control)" if r["length_mm"] == 0 else ""
        log("%7s %7.1f   final %.3f  peak %.3f  feet %4.2fN tail %4.2fN  %-9s%s"
            % ("bare" if r["length_mm"] == 0 else "%.0f" % r["length_mm"],
               r["prop_g"], r["final_up"], r["peak_up"], r["feet_N"], r["tail_N"],
               "STANDS UP" if r["recovered"] else "", tag))
    ok = [r for r in rows if r["recovered"] and r["length_mm"] > 0]
    log("")
    if ok:
        b = min(ok, key=lambda r: r["length_mm"])
        log("SHORTEST TAIL THAT STANDS UP: %.0f mm (%.1f g), final_up %.3f"
            % (b["length_mm"], b["prop_g"], b["final_up"]))
        json.dump(b, open(os.path.join(OUT, "getup_tail_best.json"), "w"), indent=1)
    else:
        b = max(rows, key=lambda r: r["final_up"])
        log("none stands up; best %s at final_up %.3f"
            % ("bare" if b["length_mm"] == 0 else "%.0f mm" % b["length_mm"],
               b["final_up"]))
    json.dump(rows, open(os.path.join(OUT, "prop_study_r4.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "prop_study_r4_log.txt"), "w").write("\n".join(lines) + "\n")
