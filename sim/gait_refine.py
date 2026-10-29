"""Refine the gait for the widened stance, seeded from the one that already works.

A from-scratch search over three carpet surfaces costs ~90 s of CPU per candidate
and would take most of a night. It is also unnecessary: the clearance-aware gait
found at the ±22 mm stance is a good starting point, and widening the stance to
±26 mm only makes its job easier (the same lean now buys 18 % more clearance).

So this is a local search - a tight Gaussian around the known-good parameters -
which converges in a handful of rounds instead of twenty.
"""
import json
import math
import os
import sys
import time

import numpy as np

from penguin_env import PenguinSim
import gait_search as G

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")

SURFACES = [("hard", None),
            ("carpet 6 mm", {"pile_mm": 6.0, "cell_mm": 9.0, "friction": 1.25, "seed": 5})]

_SIMS = None


def _init():
    global _SIMS
    _SIMS = [PenguinSim(terrain=t) for _, t in SURFACES]


def _eval(args):
    x, seconds = args
    rs = [G.rollout(s, np.asarray(x), seconds) for s in _SIMS]
    ss = [G.score(r) for r in rs]
    agg = 0.6 * min(ss) + 0.4 * (sum(ss) / len(ss))
    summ = dict(rs[0])
    summ["per_surface"] = [{"surface": SURFACES[i][0],
                            "speed_mms": round(rs[i]["speed_mms"], 2),
                            "clearance_mm": round(rs[i]["clearance_mm"], 2),
                            "fell": rs[i]["fell"]} for i in range(len(rs))]
    summ["falls"] = sum(1 for r in rs if r["fell"])
    return agg, summ


def refine(seed_params, iters=8, pop=14, elite=5, seconds=6.5, workers=6,
           spread=0.18, log=print):
    import multiprocessing as mp
    mu = np.array([seed_params[k] for k in G.KEYS], dtype=float)
    sigma = (G.HI - G.LO) * spread
    pool = mp.Pool(workers, initializer=_init)
    rng = np.random.default_rng(23)
    best, best_s = None, -1e9
    hist = []
    try:
        for it in range(iters):
            xs = np.clip(rng.normal(mu, sigma, size=(pop, len(mu))), G.LO, G.HI)
            if it == 0:
                xs[0] = mu                       # always evaluate the seed itself
            out = pool.map(_eval, [(x.tolist(), seconds) for x in xs])
            ss = np.array([o[0] for o in out])
            order = np.argsort(-ss)
            top = xs[order[:elite]]
            mu = top.mean(axis=0)
            sigma = np.maximum(top.std(axis=0), (G.HI - G.LO) * 0.02)
            if ss[order[0]] > best_s:
                best_s, best = float(ss[order[0]]), out[order[0]][1]
            r = out[order[0]][1]
            hist.append({"iter": it, "best": best_s,
                         "speed": r["speed_mms"], "clear": r["clearance_mm"]})
            log("  iter %d  agg %7.1f | hard %5.1f mm/s clr %5.1f | carpet %5.1f mm/s clr %5.1f"
                " | lean %4.1f | falls %d/2"
                % (it, ss[order[0]], r["per_surface"][0]["speed_mms"],
                   r["per_surface"][0]["clearance_mm"],
                   r["per_surface"][1]["speed_mms"], r["per_surface"][1]["clearance_mm"],
                   r["lean_max_deg"], r["falls"]))
    finally:
        pool.close()
        pool.join()
    best["params"] = dict(zip(G.KEYS, [float(v) for v in mu]))
    best["history"] = hist
    best["score"] = best_s
    return best


if __name__ == "__main__":
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    seed = json.load(open(os.path.join(OUT, "gait_seed_v3.json")))["params"]
    log("=== refining for the +/-26 mm stance, seeded from the +/-22 mm result ===")
    log("    seed: %s" % json.dumps({k: round(v, 2) for k, v in seed.items()}))
    t0 = time.time()
    best = refine(seed, log=log)
    log("")
    log("final: %s" % json.dumps({k: round(v, 3) for k, v in best["params"].items()}))
    for d in best["per_surface"]:
        log("   %-12s %5.1f mm/s   clearance %5.1f mm   %s"
            % (d["surface"], d["speed_mms"], d["clearance_mm"], "FELL" if d["fell"] else "ok"))
    log("   lean %.1f deg, saturated %.0f%% of the time"
        % (best["lean_max_deg"], best["saturated_pct"]))
    json.dump(best, open(os.path.join(OUT, "gait_final.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "gait_refine_log.txt"), "w").write("\n".join(lines) + "\n")
