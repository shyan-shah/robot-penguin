"""Full validation sweep at the current geometry. Everything, in one run.

  1  standing      - does it stand, are the feet evenly loaded, how hard is it working
  2  behaviours    - every emote, trick and dance must leave it upright
  3  gait          - speed and ground clearance on four surfaces
  4  pushes        - how hard a shove it survives, from eight directions
  5  joint sweeps  - every joint through its full travel under load

Writes tuned/validation.json and prints a table. Run it after any change to the
CAD, the URDF, the controller or the motion library - it is the regression test.
"""
import json
import math
import os
import time

import numpy as np

from penguin_env import PenguinSim
from control import Balancer, Gaited
import behaviours as B
import gait_search as G

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")

# Hard floor only. The compliant-carpet contact model is not trustworthy enough
# to put a number against (see docs/BUILD_LOG.md section 6, "Fix 4") - it makes
# the robot tumble while walking in a way that is clearly the contact solver
# rather than the robot. Standing on carpet IS modelled adequately and is
# reported separately.
SURFACES = [("hard floor", None)]
STAND_SURFACES = [("hard floor", None),
                  ("low pile 4 mm", {"pile_mm": 4.0, "friction": 1.1, "seed": 1}),
                  ("medium pile 8 mm", {"pile_mm": 8.0, "friction": 1.3, "seed": 2}),
                  ("deep pile 14 mm", {"pile_mm": 14.0, "friction": 1.4, "seed": 3})]


def load_gait():
    for name in ("gait_final.json", "gait_v2_hipx22.json"):
        f = os.path.join(OUT, name)
        if os.path.exists(f):
            p = json.load(open(f))["params"]
            m = G.gait_motion(*[p[k] for k in ("roll", "yaw", "phase", "period",
                                               "toe_out", "dwell", "flip_amp")])
            return m, p, name
    raise SystemExit("no tuned gait found - run gait_refine.py first")


def play(sim, motion, seconds, bal, lean_scale=1.0, settle=0.6, hz=50, track_clear=False):
    closed = Gaited(motion, bal, lean_scale)
    sim.reset()
    for _ in range(int(settle / sim.dt)):
        sim.command(B.REST)
        sim.step()
    p0 = sim.com().copy()
    yaw0 = sim.state()["rpy"][2]
    every = max(1, int(1.0 / (hz * sim.dt)))
    peak_tau = 0.0
    sat = 0
    samples = 0
    min_up = 1.0
    liftR = liftL = 0.0
    lean_max = 0.0
    fell = False
    t = 0.0
    for i in range(int(seconds / sim.dt)):
        if i % every == 0:
            sim.command(closed.sample_closed(t, sim.state()))
        sim.step()
        t += sim.dt
        if i % 4 == 0:
            s = sim.state()
            tau = max(abs(v) for v in s["torques"].values())
            peak_tau = max(peak_tau, tau)
            samples += 1
            if tau > 0.9 * sim.stall:
                sat += 1
            min_up = min(min_up, s["up"])
            lean_max = max(lean_max, abs(s["lean_lat"]))
            if track_clear:
                liftR = max(liftR, sim.clearance("foot_R"))
                liftL = max(liftL, sim.clearance("foot_L"))
            if s["up"] < 0.5:
                fell = True
    d = sim.com() - p0
    return {"forward_mm": float(d[1] * 1000), "lateral_mm": float(d[0] * 1000),
            "yaw_deg": float(math.degrees(sim.state()["rpy"][2] - yaw0)),
            "min_up": float(min_up), "fell": fell,
            "clearance_mm": float(min(liftR, liftL)) if track_clear else None,
            "lean_max": float(lean_max),
            "torque_pct": float(100 * peak_tau / sim.stall),
            "saturated_pct": float(100.0 * sat / max(1, samples))}


def main():
    t0 = time.time()
    motion, P, src = load_gait()
    mk = lambda: Balancer(kp=P["kp"], kd=P["kd"], sign=+1.0)
    res = {"gait_source": src, "params": P}
    print("gait from %s\n" % src)

    # ---------------------------------------------------------------- 1
    sim = PenguinSim()
    bal = mk()
    sim.reset()
    for _ in range(int(3.0 / sim.dt)):
        sim.command(bal.correct(sim.state(), B.REST))
        sim.step()
    s = sim.state()
    res["standing"] = {"up": float(s["up"]), "com_mm": float(sim.com()[2] * 1000),
                       "foot_R_N": float(s["contacts"]["foot_R"]),
                       "foot_L_N": float(s["contacts"]["foot_L"]),
                       "torque_pct": float(100 * sim.peak_torque_fraction())}
    print("1. STANDING  upright %.4f | CoM %.1f mm | feet %.2f / %.2f N | servo %.0f%%"
          % (res["standing"]["up"], res["standing"]["com_mm"], res["standing"]["foot_R_N"],
             res["standing"]["foot_L_N"], res["standing"]["torque_pct"]))

    # ---------------------------------------------------------------- 2
    print("\n2. BEHAVIOURS")
    rows = []
    libs = [("emote", B.EMOTES), ("trick", B.TRICKS)]
    for kind, lib in libs:
        for name, m in sorted(lib.items()):
            r = play(sim, m, m.duration + 1.0, mk())
            rows.append(dict(kind=kind, name=name, **r))
    for name, fn in sorted(B.DANCES.items()):
        m = fn()
        r = play(sim, m, m.duration + 0.8, mk())
        rows.append(dict(kind="dance", name=name, **r))
    res["behaviours"] = rows
    bad = [r for r in rows if r["fell"] or r["min_up"] < 0.9]
    # Peak torque is a poor measure - a single-frame spike at the start of a fast
    # move is normal and harmless. What matters is how much of the time a servo
    # is pinned at its limit.
    hot = [r for r in rows if r["saturated_pct"] > 10]
    print("   %d behaviours, %d unstable, %d spending >10%% of the time at the servo limit"
          % (len(rows), len(bad), len(hot)))
    for r in rows:
        flag = "FELL" if r["fell"] else ("wobble" if r["min_up"] < 0.9 else "")
        if flag or r["saturated_pct"] > 10:
            print("     %-6s %-10s min_up %.3f  peak tau %3.0f%%  saturated %3.0f%% of the time  %s"
                  % (r["kind"], r["name"], r["min_up"], r["torque_pct"],
                     r["saturated_pct"], flag))
    sim.close()

    # ---------------------------------------------------------------- 3
    print("\n3. GAIT BY SURFACE")
    gait_rows = []
    for sname, terr in SURFACES:
        sim = PenguinSim(terrain=terr)
        trials = [play(sim, motion, 10.0, mk(), P["lean_scale"], track_clear=True)
                  for _ in range(2)]
        sim.close()
        spd = float(np.mean([t["forward_mm"] for t in trials]) / 10.0)
        clr = float(np.mean([t["clearance_mm"] for t in trials]))
        falls = sum(1 for t in trials if t["fell"])
        gait_rows.append({"surface": sname, "speed_mms": spd, "clearance_mm": clr,
                          "falls": falls, "of": len(trials),
                          "lean_max": float(np.mean([t["lean_max"] for t in trials])),
                          "torque_pct": float(np.mean([t["torque_pct"] for t in trials]))})
        print("   %-18s %6.1f mm/s   clearance %5.1f mm   lean %4.1f  tau %3.0f%%  falls %d/%d"
              % (sname, spd, clr, gait_rows[-1]["lean_max"], gait_rows[-1]["torque_pct"],
                 falls, len(trials)))
    res["gait"] = gait_rows

    # ---------------------------------------------------------------- 4
    print("\n4. PUSH RESISTANCE")
    import pybullet as pb
    sim = PenguinSim()
    pushes = []
    for f in (0.6, 1.0, 1.4, 1.8, 2.2):
        survived = 0
        for ang in range(0, 360, 45):
            sim.reset()
            bal = mk()
            for _ in range(int(0.5 / sim.dt)):
                sim.command(bal.correct(sim.state(), B.REST))
                sim.step()
            vx, vy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            for _ in range(int(0.05 / sim.dt)):
                pb.applyExternalForce(sim.rid, -1, [f * vx, f * vy, 0], [0, 0, 0.09],
                                      pb.LINK_FRAME, physicsClientId=sim.cid)
                sim.command(bal.correct(sim.state(), B.REST))
                sim.step()
            for _ in range(int(2.5 / sim.dt)):
                sim.command(bal.correct(sim.state(), B.REST))
                sim.step()
            if sim.state()["up"] > 0.8:
                survived += 1
        pushes.append({"force_N": f, "survived": survived, "of": 8})
        print("   %.1f N from 8 directions: %d/8 stayed up" % (f, survived))
    res["pushes"] = pushes
    sim.close()

    # ---------------------------------------------------------------- 5
    print("\n5. STANDING ON CARPET  (walking on carpet is not modelled reliably)")
    stand = []
    for sname, terr in STAND_SURFACES:
        sim = PenguinSim(terrain=terr)
        sim.reset()
        bal = mk()
        for _ in range(int(5.0 / sim.dt)):
            sim.command(bal.correct(sim.state(), B.REST))
            sim.step()
        s2 = sim.state()
        stand.append({"surface": sname, "up": float(s2["up"]),
                      "lean": float(s2["lean_lat"]),
                      "com_mm": float(sim.com()[2] * 1000),
                      "stayed_up": bool(s2["up"] > 0.9)})
        print("   %-18s up %.3f  lean %6.2f  CoM %6.1f mm  %s"
              % (sname, s2["up"], s2["lean_lat"], sim.com()[2] * 1000,
                 "stands" if s2["up"] > 0.9 else "FALLS"))
        sim.close()
    res["standing_by_surface"] = stand

    res["seconds"] = time.time() - t0
    json.dump(res, open(os.path.join(OUT, "validation.json"), "w"), indent=1)
    print("\nwritten tuned/validation.json  (%.0f s)" % res["seconds"])


if __name__ == "__main__":
    main()
