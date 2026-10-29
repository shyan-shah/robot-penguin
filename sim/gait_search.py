"""Find a gait that actually picks its feet up.

The first optimiser maximised forward distance and found a cheat: hold the body
level with a stiff balance gain and scuff the feet along the floor. It travelled
9.7 mm/s with 4.4 mm of ground clearance, which is a shuffle, not a walk - it
would catch on the first rug it met.

The fix is to make clearance part of the objective, because for this mechanism
clearance is not free. There is no joint that lifts a foot. The only way a foot
leaves the floor is for the body to roll over the other one, so

    lift  ~=  stance_width * sin(body_lean)  =  44 mm * sin(lean)

and the lean is capped by the tip-over angle - 28.3 deg, measured from the CAD
(centre of mass crosses the outer edge of the support foot). Everything this
search does is a negotiation between those two facts.

The roll waveform is shaped rather than sinusoidal: `dwell` morphs it from a sine
towards a square so the body can hold full lean while the free leg swings,
instead of only passing through the lean on the way to the other side.
"""
import json
import math
import os
import time

import numpy as np

from penguin_env import PenguinSim
from control import Balancer, Gaited
import behaviours as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
os.makedirs(OUT, exist_ok=True)

TIP_OVER_DEG = 28.3          # from the CAD: CoM leaves the support foot here
LEAN_CEILING = 23.0          # stay this side of it
CLEAR_FLOOR = 11.0           # mm - below this it is a scuff, not a step
CLEAR_TARGET = 20.0          # mm - no extra reward past this


def shaped(u, dwell):
    """Roll waveform. dwell=0 -> sine, dwell->1 -> trapezoid with a flat hold."""
    s = math.sin(2 * math.pi * u)
    k = 0.3 + 6.0 * dwell
    return math.tanh(k * s) / math.tanh(k)


def gait_motion(roll, yaw, phase, period, toe_out, dwell, flip_amp):
    n = 32
    keys = []
    for i in range(n + 1):
        u = i / n
        r = roll * shaped(u, dwell)
        yr = yaw * math.sin(2 * math.pi * (u + phase))
        keys.append((u * period, {
            "ankle_R": r, "ankle_L": r,
            "hip_R": yr - toe_out, "hip_L": yr + toe_out,
            "flipper_R": 90 - flip_amp * math.sin(2 * math.pi * u),
            "flipper_L": 90 + flip_amp * math.sin(2 * math.pi * u),
        }))
    return B.Motion(keys, loop=True, name="waddle")


KEYS = ["roll", "yaw", "phase", "period", "toe_out", "dwell", "flip_amp", "kp", "kd", "lean_scale"]
LO = np.array([8.0, 0.0, -0.5, 0.7, -16.0, 0.0, 0.0, 0.10, 0.000, 0.4])
HI = np.array([23.0, 34.0, 0.5, 2.2, 16.0, 1.0, 25.0, 1.00, 0.140, 1.2])
# kp had been capped at 0.45, which bounded the answer out of the search:
# with the body-frame lean measurement the controller needs ~0.5 to track the
# gait's commanded lean instead of fighting it, and below ~0.4 it falls.


# Train on more than one floor. A gait tuned only on a perfect plane learns to
# rely on the plane; scoring every candidate on carpet too is what makes the
# result survive a rug.
TRAIN_SURFACES = [
    ("hard", None),
    ("low pile 4 mm", {"pile_mm": 4.0, "cell_mm": 8.0, "friction": 1.1, "seed": 1}),
    ("medium pile 8 mm", {"pile_mm": 8.0, "cell_mm": 9.0, "friction": 1.3, "seed": 2}),
]


def rollout(sim, x, seconds=9.0, settle=0.6, hz=50):
    g = dict(zip(KEYS, x))
    m = gait_motion(*[g[k] for k in ("roll", "yaw", "phase", "period", "toe_out",
                                     "dwell", "flip_amp")])
    bal = Balancer(kp=g["kp"], kd=g["kd"], sign=+1.0)
    closed = Gaited(m, bal, g["lean_scale"])
    sim.reset()
    for _ in range(int(settle / sim.dt)):
        sim.command(B.REST)
        sim.step()
    p0 = sim.com().copy()
    yaw0 = sim.state()["rpy"][2]
    n = int(seconds / sim.dt)
    every = max(1, int(1.0 / (hz * sim.dt)))
    liftR = liftL = 0.0
    lean_max = 0.0
    sat = 0
    samples = 0
    fell = False
    t = 0.0
    for i in range(n):
        if i % every == 0:
            sim.command(closed.sample_closed(t, sim.state()))
        sim.step()
        t += sim.dt
        if i % 4 == 0:
            s = sim.state()
            liftR = max(liftR, sim.clearance("foot_R"))
            liftL = max(liftL, sim.clearance("foot_L"))
            lean_max = max(lean_max, abs(s["lean_lat"]))
            if max(abs(v) for v in s["torques"].values()) > 0.85 * sim.stall:
                sat += 1
            samples += 1
            if s["up"] < 0.5:
                fell = True
    d = sim.com() - p0
    return {"params": g,
            "speed_mms": float(d[1] * 1000 / seconds),
            "forward_mm": float(d[1] * 1000),
            "lateral_mm": float(d[0] * 1000),
            "yaw_deg": float(math.degrees(sim.state()["rpy"][2] - yaw0)),
            "lift_R_mm": float(liftR), "lift_L_mm": float(liftL),
            "clearance_mm": float(min(liftR, liftL)),
            "lean_max_deg": float(lean_max),
            "saturated_pct": float(100.0 * sat / max(1, samples)),
            "fell": bool(fell)}


def score(r):
    if r["fell"]:
        return -900.0 + r["forward_mm"]
    s = 10.0 * r["speed_mms"]
    c = r["clearance_mm"]
    s += 9.0 * min(c, CLEAR_TARGET)
    if c < CLEAR_FLOOR:                       # a scuff is not a walk
        s -= 25.0 * (CLEAR_FLOOR - c)
    s -= 0.30 * abs(r["lateral_mm"])
    s -= 0.60 * abs(r["yaw_deg"])
    s -= 25.0 * max(0.0, r["lean_max_deg"] - LEAN_CEILING)
    s -= 4.0 * max(0.0, r["saturated_pct"] - 15.0)
    return s


def multi_score(sims, x, seconds=9.0):
    """Score a candidate across every training surface; the worst one counts most."""
    rs = [rollout(s, x, seconds) for s in sims]
    ss = [score(r) for r in rs]
    agg = 0.65 * min(ss) + 0.35 * (sum(ss) / len(ss))     # robustness over average
    summary = dict(rs[0])
    summary["per_surface"] = [
        {"surface": TRAIN_SURFACES[i][0], "score": round(ss[i], 1),
         "speed_mms": round(rs[i]["speed_mms"], 2),
         "clearance_mm": round(rs[i]["clearance_mm"], 2),
         "fell": rs[i]["fell"]} for i in range(len(rs))]
    summary["agg_score"] = agg
    summary["worst_score"] = min(ss)
    summary["falls"] = sum(1 for r in rs if r["fell"])
    return agg, summary


# --- parallel evaluation -----------------------------------------------------
# Heightfield contact is expensive, so one candidate on three surfaces costs
# ~30 s. Each worker builds its own set of sims once and then just evaluates.
_WORKER_SIMS = None


def _init_worker():
    global _WORKER_SIMS
    import pybullet as _p                                  # noqa: F401
    _WORKER_SIMS = [PenguinSim(terrain=t) for _, t in TRAIN_SURFACES]


def _eval_one(args):
    x, seconds = args
    return multi_score(_WORKER_SIMS, np.asarray(x), seconds)


def search(iters=16, pop=20, elite=5, seed=11, log=print, seconds=8.0, workers=4):
    import multiprocessing as mp
    pool = mp.Pool(workers, initializer=_init_worker) if workers > 1 else None
    sims = None if pool else [PenguinSim(terrain=t) for _, t in TRAIN_SURFACES]
    rng = np.random.default_rng(seed)
    mu = (LO + HI) / 2.0
    sigma = (HI - LO) / 4.0
    best, best_s = None, -1e9
    hist = []
    for it in range(iters):
        xs = np.clip(rng.normal(mu, sigma, size=(pop, len(mu))), LO, HI)
        if pool:
            out = pool.map(_eval_one, [(x.tolist(), seconds) for x in xs])
        else:
            out = [multi_score(sims, x, seconds) for x in xs]
        ss = np.array([o[0] for o in out])
        order = np.argsort(-ss)
        top = xs[order[:elite]]
        mu = top.mean(axis=0)
        sigma = np.maximum(top.std(axis=0), (HI - LO) * 0.025)
        if ss[order[0]] > best_s:
            best_s, best = float(ss[order[0]]), out[order[0]][1]
        r = out[order[0]][1]
        hist.append({"iter": it, "best": best_s,
                     "speed": r["speed_mms"], "clear": r["clearance_mm"]})
        log("  iter %2d  agg %7.1f | hard %5.1f mm/s clr %4.1f | carpet %5.1f / %5.1f mm/s"
            " | falls %d/3"
            % (it, ss[order[0]], r["per_surface"][0]["speed_mms"],
               r["per_surface"][0]["clearance_mm"],
               r["per_surface"][1]["speed_mms"], r["per_surface"][2]["speed_mms"],
               r["falls"]))
    if pool:
        pool.close()
        pool.join()
    else:
        for s in sims:
            s.close()
    best["history"] = hist
    best["score"] = best_s
    return best


if __name__ == "__main__":
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    log("=== gait search v2: clearance is part of the objective ===")
    log("    geometry caps lift at stance * sin(lean) = 44 mm * sin(lean);")
    log("    tip-over is %.1f deg, so the ceiling is %.0f deg -> %.1f mm of lift."
        % (TIP_OVER_DEG, LEAN_CEILING, 44.0 * math.sin(math.radians(LEAN_CEILING))))
    t0 = time.time()
    best = search(log=log)
    log("")
    log("best: %s" % json.dumps({k: round(v, 3) for k, v in best["params"].items()}))
    log("  %.1f mm/s forward, clearance %.1f mm (R %.1f / L %.1f), lean %.1f deg, "
        "lateral %.1f mm, yaw %.1f deg, saturated %.0f%% of the time"
        % (best["speed_mms"], best["clearance_mm"], best["lift_R_mm"], best["lift_L_mm"],
           best["lean_max_deg"], best["lateral_mm"], best["yaw_deg"], best["saturated_pct"]))
    json.dump(best, open(os.path.join(OUT, "gait_final.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "gait_final_log.txt"), "w").write("\n".join(lines) + "\n")
