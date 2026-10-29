"""Tune the penguin's motions against the physics simulation.

This is optimisation against a simulator, not deep RL: the gait is a small
parameterised central-pattern generator and we search its parameters with the
cross-entropy method, scoring real rollouts. Everything is scored under the
MG90S's actual stall torque, so a gait that needs more than the servos can give
scores badly instead of looking fine on paper.

Outputs tuned/gait.json, tuned/getup.json and tuned/report.json.
"""
import json
import math
import os
import sys
import time

import numpy as np

from penguin_env import PenguinSim
from control import Balancer, Gaited
import behaviours as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
os.makedirs(OUT, exist_ok=True)


# ----------------------------------------------------------------- rollouts
def run(sim, motion, seconds, settle=0.4, start=None, tilt=(0.0, 0.0), hz=50,
        balancer=None, lean_scale=1.0):
    """Play a motion and report what happened. Returns a metrics dict."""
    sim.reset(pose=start, tilt=tilt)
    closed = Gaited(motion, balancer, lean_scale) if balancer is not None else None
    for _ in range(int(settle / sim.dt)):
        sim.command(B.REST)
        sim.step()
    p0 = sim.com().copy()
    yaw0 = sim.state()["rpy"][2]
    n = int(seconds / sim.dt)
    every = max(1, int(1.0 / (hz * sim.dt)))
    peak_tau, min_up, fell_at, max_lean = 0.0, 1.0, None, 0.0
    t = 0.0
    for i in range(n):
        if i % every == 0:
            sim.command(closed.sample_closed(t, sim.state()) if closed
                        else motion.sample(t))
        sim.step()
        t += sim.dt
        s = sim.state()
        peak_tau = max(peak_tau, max(abs(v) for v in s["torques"].values()))
        min_up = min(min_up, s["up"])
        max_lean = max(max_lean, abs(s["lean_lat"]))
        if fell_at is None and s["up"] < 0.5:
            fell_at = t
    s = sim.state()
    d = sim.com() - p0
    return {"forward_mm": float(d[1] * 1000), "lateral_mm": float(d[0] * 1000),
            "yaw_deg": math.degrees(s["rpy"][2] - yaw0),
            "upright": float(s["up"]), "min_upright": float(min_up),
            "max_lean_deg": float(max_lean),
            "fell": fell_at is not None, "fell_at": fell_at,
            "peak_torque_pct": float(100 * peak_tau / sim.stall),
            "com_height_mm": float(sim.com()[2] * 1000)}


# --------------------------------------------------------------- gait search
GAIT_KEYS = ["roll", "yaw", "phase", "period", "toe_out", "kp", "kd", "lean_scale"]
GAIT_LO = np.array([2.0, 0.0, -0.5, 0.5, -20.0, 0.10, 0.00, 0.0])
GAIT_HI = np.array([26.0, 34.0, 0.5, 2.4, 20.0, 1.60, 0.25, 1.0])


def gait_score(sim, x, seconds=8.0):
    g = dict(zip(GAIT_KEYS, x))
    gait = {k: g[k] for k in ("roll", "yaw", "phase", "period", "toe_out")}
    m = B.waddle(**gait)
    bal = Balancer(kp=g["kp"], kd=g["kd"], sign=+1.0)
    r = run(sim, m, seconds, balancer=bal, lean_scale=g["lean_scale"])
    # forward travel is the point; punish falling, drifting sideways, spinning,
    # and asking the servos for more than they have.
    s = r["forward_mm"]
    s -= 0.35 * abs(r["lateral_mm"])
    s -= 0.8 * abs(r["yaw_deg"])
    if r["fell"]:
        s -= 400.0
    over = max(0.0, r["peak_torque_pct"] - 70.0)
    s -= 4.0 * over
    r["score"] = float(s)
    r["params"] = g
    return r


def optimise_gait(iters=14, pop=18, elite=5, seconds=8.0, seed=1, log=print):
    sim = PenguinSim()
    rng = np.random.default_rng(seed)
    mu = (GAIT_LO + GAIT_HI) / 2.0
    sigma = (GAIT_HI - GAIT_LO) / 4.0
    best = None
    history = []
    for it in range(iters):
        xs = np.clip(rng.normal(mu, sigma, size=(pop, len(mu))), GAIT_LO, GAIT_HI)
        res = [gait_score(sim, x, seconds) for x in xs]
        order = np.argsort([-r["score"] for r in res])
        top = xs[order[:elite]]
        mu = top.mean(axis=0)
        sigma = np.maximum(top.std(axis=0), (GAIT_HI - GAIT_LO) * 0.02)
        cand = res[order[0]]
        if best is None or cand["score"] > best["score"]:
            best = cand
        history.append({"iter": it, "best": float(cand["score"]),
                        "mean": float(np.mean([r["score"] for r in res])),
                        "forward_mm": cand["forward_mm"]})
        log("  iter %2d  best %8.1f  mean %8.1f   fwd %6.1f mm  fell=%s  tau %3.0f%%"
            % (it, cand["score"], history[-1]["mean"], cand["forward_mm"],
               cand["fell"], cand["peak_torque_pct"]))
    sim.close()
    best["history"] = history
    return best


# ------------------------------------------------------------- get-up search
FALLS = {"back": (math.radians(-88), 0.0), "front": (math.radians(88), 0.0),
         "side": (0.0, math.radians(85))}


def tune_getup(log=print, trials=9):
    """For each fall direction, sweep the effort scale and keep what works."""
    sim = PenguinSim()
    out = {}
    for kind, tilt in FALLS.items():
        rows = []
        for a in np.linspace(0.5, 1.5, trials):
            m = B.getup(kind, a=float(a))
            sim.reset(tilt=tilt)
            for _ in range(int(0.6 / sim.dt)):
                sim.command(B.REST)
                sim.step()
            t, n = 0.0, int((m.duration + 1.6) / sim.dt)
            best_up = 0.0
            for i in range(n):
                if i % 5 == 0:
                    sim.command(m.sample(t))
                sim.step()
                t += sim.dt
                best_up = max(best_up, sim.state()["up"])
            up = sim.state()["up"]
            rows.append({"a": float(a), "final_up": float(up), "best_up": float(best_up),
                         "recovered": bool(up > 0.80)})
            log("  %-6s a=%.2f  final_up %.3f  peak %.3f  %s"
                % (kind, a, up, best_up, "RECOVERED" if up > 0.80 else ""))
        ok = [r for r in rows if r["recovered"]]
        out[kind] = {"sweep": rows,
                     "best_a": (max(ok, key=lambda r: r["final_up"])["a"] if ok
                                else max(rows, key=lambda r: r["best_up"])["a"]),
                     "recovers": bool(ok)}
    sim.close()
    return out


# ------------------------------------------------------- behaviour stability
def check_motions(log=print, gains=None):
    """Every emote and trick must leave the penguin standing."""
    sim = PenguinSim()
    gains = gains or {"kp": 0.6, "kd": 0.05}
    mk = lambda: Balancer(kp=gains["kp"], kd=gains["kd"], sign=+1.0)
    rows = []
    for kind, lib in (("emote", B.EMOTES), ("trick", B.TRICKS)):
        for name, m in lib.items():
            r = run(sim, m, m.duration + 1.0, balancer=mk())
            rows.append({"kind": kind, "name": name, "duration": m.duration, **r})
            log("  %-6s %-10s %5.2fs  min_up %.3f  tau %3.0f%%  drift %5.1f mm  %s"
                % (kind, name, m.duration, r["min_upright"], r["peak_torque_pct"],
                   math.hypot(r["forward_mm"], r["lateral_mm"]),
                   "FELL" if r["fell"] else "ok"))
    for name, fn in B.DANCES.items():
        m = fn()
        r = run(sim, m, m.duration + 1.0, balancer=mk())
        rows.append({"kind": "dance", "name": name, "duration": m.duration, **r})
        log("  %-6s %-10s %5.2fs  min_up %.3f  tau %3.0f%%  drift %5.1f mm  %s"
            % ("dance", name, m.duration, r["min_upright"], r["peak_torque_pct"],
               math.hypot(r["forward_mm"], r["lateral_mm"]), "FELL" if r["fell"] else "ok"))
    sim.close()
    return rows


# ------------------------------------------------------------- push testing
def push_test(gains=None, log=print, pushes=(0.6, 1.0, 1.4, 1.8, 2.2)):
    """How hard a shove can it take while standing? Impulse applied at the chest."""
    import pybullet as pb
    sim = PenguinSim()
    gains = gains or {"kp": 0.6, "kd": 0.05}
    stand = B.Motion([(0.0, {}), (6.0, {})], name="stand")
    rows = []
    for f in pushes:
        survived = 0
        for ang in range(0, 360, 45):
            sim.reset()
            bal = Balancer(kp=gains["kp"], kd=gains["kd"], sign=+1.0)
            for _ in range(int(0.5 / sim.dt)):
                sim.command(bal.correct(sim.state(), B.REST))
                sim.step()
            vx, vy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            for _ in range(int(0.05 / sim.dt)):      # 50 ms shove
                pb.applyExternalForce(sim.rid, -1, [f * vx, f * vy, 0],
                                      [0, 0, 0.09], pb.LINK_FRAME,
                                      physicsClientId=sim.cid)
                sim.command(bal.correct(sim.state(), B.REST))
                sim.step()
            for _ in range(int(2.5 / sim.dt)):
                sim.command(bal.correct(sim.state(), B.REST))
                sim.step()
            if sim.state()["up"] > 0.8:
                survived += 1
        rows.append({"force_N": f, "survived": survived, "of": 8})
        log("  push %.1f N from 8 directions: %d/8 stayed up" % (f, survived))
    sim.close()
    return rows


# --------------------------------------------------------------------- main
if __name__ == "__main__":
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    t0 = time.time()
    log("=== gait search (cross-entropy over CPG + balance gains) ===")
    best = optimise_gait(log=log)
    log("best gait: %s" % json.dumps({k: round(v, 2) for k, v in best["params"].items()}))
    log("  forward %.1f mm in 8 s  = %.1f mm/s, lateral %.1f, yaw %.1f deg, tau %.0f%%"
        % (best["forward_mm"], best["forward_mm"] / 8.0, best["lateral_mm"],
           best["yaw_deg"], best["peak_torque_pct"]))
    json.dump(best, open(os.path.join(OUT, "gait.json"), "w"), indent=1)

    log("\n=== fall recovery ===")
    gu = tune_getup(log=log)
    json.dump(gu, open(os.path.join(OUT, "getup.json"), "w"), indent=1)
    for k, v in gu.items():
        log("  %-6s %s (best effort scale %.2f)"
            % (k, "recovers" if v["recovers"] else "DOES NOT RECOVER", v["best_a"]))

    gains = {"kp": best["params"]["kp"], "kd": best["params"]["kd"]}
    log("\n=== behaviour stability (balance gains kp=%.2f kd=%.3f) ===" % (gains["kp"], gains["kd"]))
    motions = check_motions(log=log, gains=gains)

    log("\n=== push resistance (standing) ===")
    pushes = push_test(gains=gains, log=log)

    json.dump({"gait": best, "getup": gu, "motions": motions, "pushes": pushes,
               "seconds_elapsed": time.time() - t0},
              open(os.path.join(OUT, "report.json"), "w"), indent=1)
    log("\ndone in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "train_log.txt"), "w").write("\n".join(lines) + "\n")
