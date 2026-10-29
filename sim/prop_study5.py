"""Round 5: the deckchair shuffle, scored on what the controller ADDS.

Rounds 2-4 scored absolute uprightness, which rewarded a longer tail for merely
reclining less - see getup_shuffle.py and prop_diag.py. This one scores the GAIN
over the free resting angle, so a tail that just holds the body higher earns
nothing and only real recovery counts.

It also uses the REAL tail, taken from tail_prop.ipt: 26.1 g, not the 19.6 g of
the 12 mm box the earlier rounds assumed, and the proper 16 x 10 section.
"""
import json
import os
import time

import penguin_env
from prop_study import make_variant

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
URDF = os.path.join(HERE, "penguin.urdf")

ATTACH_Y, ATTACH_Z, UP_DEG = -38.0, 55.0, 0.0     # CAD part is a straight spur
LENGTHS = [0.0, 90.0, 110.0, 130.0]


def _eval(job):
    import getup_shuffle as G
    idx, length = job
    if length <= 0.0:
        path, g = URDF, 0.0
    else:
        path = os.path.join(HERE, "penguin_p5_%d.urdf" % idx)
        g = make_variant(ATTACH_Y, ATTACH_Z, length, -UP_DEG, path)
    sim = penguin_env.PenguinSim(urdf=path)
    best = G.search(sim, iters=16, pop=20, log=lambda s: None)
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

    log("=== tail prop, round 5: shuffle backwards out of the deckchair ===")
    log("    scored on the GAIN over the free resting angle, not absolute up")
    log("")
    t0 = time.time()
    with mp.Pool(4) as pool:
        rows = pool.map(_eval, list(enumerate(LENGTHS)))
    log("%7s %7s   %s" % ("len", "mass g", "result"))
    for r in rows:
        log("%7s %7.1f   rests at %.3f -> finishes %.3f   gain %+.3f   %s%s"
            % ("bare" if r["length_mm"] == 0 else "%.0f" % r["length_mm"],
               r["prop_g"], r["rest_up"], r["final_up"], r["gain"],
               "STANDS UP" if r["recovered"] else "",
               "   <- BARE ROBOT (control)" if r["length_mm"] == 0 else ""))
    ok = [r for r in rows if r["recovered"] and r["length_mm"] > 0]
    log("")
    if ok:
        b = min(ok, key=lambda r: r["length_mm"])
        log("SHORTEST TAIL THAT STANDS UP: %.0f mm, finishing at %.3f (gain %+.3f)"
            % (b["length_mm"], b["final_up"], b["gain"]))
        json.dump(b, open(os.path.join(OUT, "getup_shuffle_best.json"), "w"), indent=1)
    else:
        b = max(rows, key=lambda r: r["gain"])
        log("none stands up. best GAIN from any controller: %+.3f (%s)"
            % (b["gain"], "bare" if b["length_mm"] == 0 else "%.0f mm tail" % b["length_mm"]))
        log("A gain near zero means the shuffle cannot shift the body off the tail,")
        log("and the tail's only real benefit is that it prevents lying flat.")
    json.dump(rows, open(os.path.join(OUT, "prop_study_r5.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "prop_study_r5_log.txt"), "w").write("\n".join(lines) + "\n")
