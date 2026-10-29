"""How long would the flippers have to be for the penguin to right itself?

Three independent searches have now failed to find a self-righting motion, and
the reason is not the controller - it is leverage. Lying on its back the flipper
pivot is 46.7 mm above the floor and the flipper is 55 mm long, so it reaches the
ground with about 8 mm to spare. You cannot lift 5.7 N on 8 mm of lever.

"It cannot do it" is a less useful answer than "it needs flippers this long", so
this sweeps the flipper length and finds where recovery becomes possible. The
flipper mesh is stretched along its own length only, and its mass and inertia are
scaled with it, so each variant is a physically consistent robot.

Writes tuned/flipper_study.json.
"""
import json
import math
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
URDF = os.path.join(HERE, "penguin.urdf")          # read only
VARIANT = os.path.join(HERE, "penguin_variant.urdf")  # written per factor


def make_variant(factor):
    """Write penguin_variant.urdf with the flipper links stretched by `factor`.

    Never touches penguin.urdf - other searches read that one.
    """
    src = open(URDF).read()
    out, in_flipper = [], False
    for line in src.splitlines():
        s = line.strip()
        if s.startswith('<link name="flipper'):
            in_flipper = True
        elif s.startswith("</link>"):
            in_flipper = False
        if in_flipper:
            # stretch the mesh along Y (the flipper's length axis in CAD)
            if 'scale="0.001 0.001 0.001"' in line:
                line = line.replace('scale="0.001 0.001 0.001"',
                                    'scale="0.001 %.5f 0.001"' % (0.001 * factor))
            # mass and the inertia about the long axis scale with the extra blade
            elif "<mass value=" in line:
                m = float(line.split('"')[1])
                line = '      <mass value="%.6f"/>' % (m * factor)
            elif "<inertia " in line:
                parts = dict(p.split("=") for p in line.strip()[9:-2].split())
                vals = {k: float(v.strip('"')) for k, v in parts.items()}
                for k in ("ixx", "izz"):
                    vals[k] *= factor ** 3          # length^3 about the transverse axes
                vals["iyy"] *= factor               # mass only about the long axis
                line = ('      <inertia ' +
                        " ".join('%s="%.9f"' % (k, vals[k]) for k in
                                 ("ixx", "iyy", "izz", "ixy", "iyz", "ixz")) + "/>")
        out.append(line)
    open(VARIANT, "w").write("\n".join(out) + "\n")


def restore():
    if os.path.exists(VARIANT):
        os.remove(VARIANT)


def study(factors=(1.0, 1.3, 1.6, 1.9, 2.2), iters=8, pop=18, kind="back", log=print):
    import getup_staged as G
    rows = []
    for f in factors:
        make_variant(f)
        # the module caches nothing, but the sim must be rebuilt per variant
        import importlib
        import penguin_env
        importlib.reload(penguin_env)
        importlib.reload(G)
        sim = penguin_env.PenguinSim(urdf=VARIANT)
        rng = np.random.default_rng(17)
        mu = (G.LO + G.HI) / 2.0
        sigma = (G.HI - G.LO) / 4.0
        best, best_s = None, -1e9
        for it in range(iters):
            xs = np.clip(rng.normal(mu, sigma, size=(pop, len(mu))), G.LO, G.HI)
            rs = [G.trial(sim, x, kind) for x in xs]
            ss = np.array([G.score(r) for r in rs])
            order = np.argsort(-ss)
            top = xs[order[:max(3, pop // 4)]]
            mu = top.mean(axis=0)
            sigma = np.maximum(top.std(axis=0), (G.HI - G.LO) * 0.03)
            if ss[order[0]] > best_s:
                best_s, best = float(ss[order[0]]), rs[order[0]]
        length = 55.0 * f
        reach = length - 46.7
        rows.append({"factor": f, "length_mm": length, "ground_reach_mm": reach,
                     "final_up": best["final_up"], "peak_up": best["peak_up"],
                     "recovered": best["recovered"]})
        log("  flipper %5.1f mm (reach %5.1f mm past the floor) -> peak_up %.3f  final %.3f  %s"
            % (length, reach, best["peak_up"], best["final_up"],
               "RECOVERS" if best["recovered"] else ""))
        sim.close()
    restore()
    return rows


if __name__ == "__main__":
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    log("=== how long do the flippers need to be? (fall: on its back) ===")
    log("    current flipper 55.0 mm, pivot 46.7 mm above the floor when down")
    t0 = time.time()
    try:
        rows = study(log=log)
    finally:
        restore()
    ok = [r for r in rows if r["recovered"]]
    log("")
    if ok:
        log("self-rights from %.0f mm of flipper (%.0f mm longer than now)"
            % (ok[0]["length_mm"], ok[0]["length_mm"] - 55.0))
    else:
        log("no flipper length in this range self-rights it; the limit is not leverage alone")
    json.dump(rows, open(os.path.join(OUT, "flipper_study.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "flipper_study_log.txt"), "w").write("\n".join(lines) + "\n")
