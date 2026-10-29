"""Recovery with a tail prop: four stages, because the prop changes the problem.

Without a prop, getting up off its back is a lifting problem the flippers cannot
solve - see docs/SELF_RIGHTING.md. With a spur off the upper back shell, the
sweep in prop_study3.py got final_up 0.826, and verifying that pose showed
something the search was not looking for:

    150 mm tail   up 0.826   pitch +34 deg
    touching: foot_L 3.13 N, foot_R 1.63 N, torso+prop 0.20 N
    -> 4.76 N of 4.96 N on the FEET

It is not lying propped up. It is STANDING, on both feet, reclined 34 degrees
back against the tail like a deckchair, with almost no load on the tail itself.
The hard part - getting the feet under the body - is already done. What is left
is to walk the centre of mass forward over the ankles, and the three-stage
controller never tried: its stage C plants the feet and hands over to the
balancer, and the balancer holds a pose rather than changing one.

So stage D: once the feet are loaded and the body is still reclined, throw the
flippers FORWARD and drive the ankles to pitch the body up off the tail. The
flipper swing is the useful part - 2 x 11 g thrown through 90 degrees at the top
of the body gives a forward pitch reaction, which is the trick a person uses
standing up out of a low chair.

Stage D is entered on a measured condition (feet loaded AND reclined), not on a
timer, so it cannot fire while the robot is still rolling about.
"""
import math
import os

import numpy as np
import pybullet as pb

import behaviours as B
from control import Balancer
from getup_catch import FALLS, FLIP_LO, FLIP_HI, clamp

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
os.makedirs(OUT, exist_ok=True)

KEYS = ["tA", "A_freq", "A_hip", "A_hip_bias", "A_flip",
        "B_freq", "B_flip_amp", "B_flip_centre", "B_phase", "B_hip", "B_ank",
        "trigger", "C_ank", "C_hold",
        "D_flip", "D_ank", "D_hip", "D_rate"]
LO = np.array([0.0, 0.4, 0.0, -90.0, FLIP_LO,
               0.4, 0.0, FLIP_LO, -math.pi, 0.0, 0.0,
               0.45, -25.0, 0.10,
               FLIP_LO, -28.0, -40.0, 0.5])
HI = np.array([3.0, 3.5, 90.0, 90.0, FLIP_HI,
               3.5, 140.0, FLIP_HI, math.pi, 90.0, 28.0,
               0.90, 25.0, 1.20,
               FLIP_HI, 28.0, 40.0, 6.0])


class TailCatcher:
    """A -> roll, B -> push, C -> plant the feet, D -> stand up off the tail."""

    def __init__(self, p):
        self.q = dict(zip(KEYS, p))
        self.caught_at = None
        self.stood_at = None

    def sample(self, t, s, feet_N):
        q = self.q
        if self.caught_at is None and s["up"] >= q["trigger"] and t > 0.4:
            self.caught_at = t
        if self.caught_at is not None:
            held = t - self.caught_at
            # D fires on a measured condition: weight actually on the feet, and
            # still reclined enough that there is something left to do.
            if (self.stood_at is None and held > q["C_hold"]
                    and feet_N > 1.5 and s["up"] < 0.97):
                self.stood_at = t
            if self.stood_at is not None:
                # --- D: throw the flippers forward and push with the ankles
                e = min(1.0, (t - self.stood_at) * q["D_rate"])
                return {"hip_R": clamp(e * q["D_hip"], -90, 90),
                        "hip_L": clamp(-e * q["D_hip"], -90, 90),
                        "ankle_R": clamp(e * q["D_ank"], -30, 30),
                        "ankle_L": clamp(e * q["D_ank"], -30, 30),
                        "flipper_R": clamp(90.0 + e * (q["D_flip"] - 90.0), FLIP_LO, FLIP_HI),
                        "flipper_L": clamp(90.0 + e * (q["D_flip"] - 90.0), FLIP_LO, FLIP_HI),
                        "beak": 0.0}
            # --- C: plant the feet and settle
            return {"hip_R": 0.0, "hip_L": 0.0,
                    "ankle_R": q["C_ank"], "ankle_L": q["C_ank"],
                    "flipper_R": 90.0, "flipper_L": 90.0, "beak": 0.0}
        if t < q["tA"]:
            # --- A: roll onto the side
            w = 2 * math.pi * q["A_freq"] * t
            env = min(1.0, t / 0.3)
            hip = env * (q["A_hip_bias"] + q["A_hip"] * math.sin(w))
            return {"hip_R": clamp(hip, -90, 90), "hip_L": clamp(-hip, -90, 90),
                    "ankle_R": 0.0, "ankle_L": 0.0,
                    "flipper_R": clamp(q["A_flip"], FLIP_LO, FLIP_HI),
                    "flipper_L": clamp(q["A_flip"], FLIP_LO, FLIP_HI), "beak": 0.0}
        # --- B: push
        u = t - q["tA"]
        w = 2 * math.pi * q["B_freq"] * u
        env = min(1.0, u / 0.3)
        return {"hip_R": clamp(env * q["B_hip"], -90, 90),
                "hip_L": clamp(-env * q["B_hip"], -90, 90),
                "ankle_R": clamp(env * q["B_ank"], -30, 30),
                "ankle_L": clamp(env * q["B_ank"], -30, 30),
                "flipper_R": clamp(q["B_flip_centre"] + env * q["B_flip_amp"] * math.sin(w),
                                   FLIP_LO, FLIP_HI),
                "flipper_L": clamp(q["B_flip_centre"] + env * q["B_flip_amp"] * math.sin(w + q["B_phase"]),
                                   FLIP_LO, FLIP_HI),
                "beak": 0.0}


def foot_load(sim):
    names = {v: k for k, v in sim.jid.items()}
    tot = 0.0
    for c in pb.getContactPoints(bodyA=sim.rid, bodyB=sim.plane,
                                 physicsClientId=sim.cid):
        if c[3] >= 0 and "foot" in names.get(c[3], ""):
            tot += c[9]
    return tot


def tail_load(sim):
    tot = 0.0
    for c in pb.getContactPoints(bodyA=sim.rid, bodyB=sim.plane,
                                 physicsClientId=sim.cid):
        if c[3] < 0:
            tot += c[9]
    return tot


def trial(sim, p, kind, drive=9.0, settle=2.5, hz=50):
    sim.reset(tilt=FALLS[kind])
    for _ in range(int(0.7 / sim.dt)):
        sim.command(B.REST)
        sim.step()
    rc = TailCatcher(p)
    bal = Balancer(kp=0.5, kd=0.05, sign=+1.0)
    peak = sim.state()["up"]
    every = max(1, int(1.0 / (hz * sim.dt)))
    t = 0.0
    for i in range(int(drive / sim.dt)):
        s = sim.state()
        if i % every == 0:
            pose = rc.sample(t, s, foot_load(sim))
            if rc.caught_at is not None:
                pose = bal.correct(s, pose)
            sim.command(pose)
        sim.step()
        t += sim.dt
        peak = max(peak, sim.state()["up"])
    for i in range(int(settle / sim.dt)):
        s = sim.state()
        if i % every == 0:
            sim.command(bal.correct(s, B.REST))
        sim.step()
        peak = max(peak, sim.state()["up"])
    s = sim.state()
    return {"final_up": float(s["up"]), "peak_up": float(peak),
            "caught": rc.caught_at is not None,
            "stood": rc.stood_at is not None,
            "feet_N": float(foot_load(sim)), "tail_N": float(tail_load(sim)),
            "recovered": bool(s["up"] > 0.85)}


def score(r):
    return (r["final_up"] * 200.0 + r["peak_up"] * 50.0
            + (20.0 if r["caught"] else 0.0) + (30.0 if r["stood"] else 0.0)
            + (250.0 if r["recovered"] else 0.0))


def search(sim, kind, iters=14, pop=20, elite=5, seed=7, log=print):
    rng = np.random.default_rng(seed)
    mu = (LO + HI) / 2.0
    sigma = (HI - LO) / 4.0
    best, best_s = None, -1e9
    for it in range(iters):
        xs = np.clip(rng.normal(mu, sigma, size=(pop, len(mu))), LO, HI)
        rs = [trial(sim, x, kind) for x in xs]
        ss = np.array([score(r) for r in rs])
        order = np.argsort(-ss)
        top = xs[order[:elite]]
        mu = top.mean(axis=0)
        sigma = np.maximum(top.std(axis=0), (HI - LO) * 0.03)
        if ss[order[0]] > best_s:
            best_s = float(ss[order[0]])
            best = {"params": dict(zip(KEYS, [float(v) for v in xs[order[0]]])),
                    **rs[order[0]]}
        log("  iter %2d  best %6.1f | final %.3f peak %.3f feet %.2fN tail %.2fN %s"
            % (it, best_s, best["final_up"], best["peak_up"], best["feet_N"],
               best["tail_N"], "STANDS UP" if best["recovered"] else ""))
    return best
