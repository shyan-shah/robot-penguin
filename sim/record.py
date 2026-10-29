"""Render simulation clips to MP4.

Frames come straight out of PyBullet's camera; ffmpeg does the encoding and burns
a caption into each clip. Run after train.py so the tuned gait and recovery
parameters exist.
"""
import json
import math
import os
import shutil
import subprocess
import sys

import numpy as np

from penguin_env import PenguinSim
from control import Balancer, Gaited
import behaviours as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
TUNED = os.path.join(HERE, "tuned")
os.makedirs(OUT, exist_ok=True)
FONT = "C\\:/Windows/Fonts/arialbd.ttf"
FPS = 30


def _params():
    """Prefer the gait tuned for the current geometry, fall back in order."""
    for name in ("gait_final.json", "gait_v2_hipx22.json", "gait.json"):
        f = os.path.join(TUNED, name)
        if os.path.exists(f):
            return json.load(open(f))["params"], name
    return None, None


def gains():
    g, _ = _params()
    if not g:
        return {"kp": 0.6, "kd": 0.05, "lean_scale": 1.0}
    return {"kp": g["kp"], "kd": g["kd"], "lean_scale": g.get("lean_scale", 1.0)}


def tuned_gait():
    g, name = _params()
    if not g:
        return B.waddle()
    if "dwell" in g:                       # the clearance-aware generator
        import gait_search as G
        return G.gait_motion(*[g[k] for k in ("roll", "yaw", "phase", "period",
                                              "toe_out", "dwell", "flip_amp")])
    return B.waddle(**{k: g[k] for k in ("roll", "yaw", "phase", "period", "toe_out")})


def getup_scale(kind):
    try:
        return json.load(open(os.path.join(TUNED, "getup.json")))[kind]["best_a"]
    except Exception:
        return 1.0


def encode(frames, path, caption=None, fps=FPS):
    """frames: iterable of HxWx3 uint8. Pipes raw video into ffmpeg.

    The caption goes via textfile= rather than text=: drawtext treats ':' as an
    option separator and ',' as a filter separator, so any readable caption
    would otherwise have to be escaped character by character.
    """
    h, w = frames[0].shape[:2]
    cap_path = None
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "%dx%d" % (w, h), "-r", str(fps), "-i", "-"]
    if caption:
        cap_path = os.path.join(OUT, ".caption.txt")
        with open(cap_path, "w", encoding="utf-8") as fh:
            fh.write(caption)
        cmd += ["-vf", ("drawtext=fontfile='%s':textfile='%s':x=24:y=h-56:fontsize=24:"
                        "fontcolor=white:box=1:boxcolor=0x00000099:boxborderw=10"
                        % (FONT, cap_path.replace("\\", "/").replace(":", "\\:")))]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for f in frames:
            pr.stdin.write(f.tobytes())
        pr.stdin.close()
    except BrokenPipeError:
        pass
    err = pr.stderr.read().decode(errors="replace")
    pr.wait()
    if pr.returncode != 0:
        raise RuntimeError("ffmpeg failed for %s:\n%s" % (path, err[-800:]))
    return path


def play(sim, motion, seconds, balancer=None, lean_scale=1.0, yaw_cam=50, dist=0.55,
         track=True, pitch=-18, hz=50, w=640, h=480):
    """Step the sim and grab a frame every 1/FPS of simulated time."""
    closed = Gaited(motion, balancer, lean_scale) if balancer is not None else None
    frames = []
    n = int(seconds / sim.dt)
    every_cmd = max(1, int(1.0 / (hz * sim.dt)))
    every_frame = max(1, int(1.0 / (FPS * sim.dt)))
    t = 0.0
    for i in range(n):
        if i % every_cmd == 0:
            sim.command(closed.sample_closed(t, sim.state()) if closed else motion.sample(t))
        sim.step()
        t += sim.dt
        if i % every_frame == 0:
            target = sim.com() if track else [0, 0, 0.10]
            frames.append(sim.camera(w, h, dist=dist, yaw=yaw_cam, pitch=pitch, target=target))
    return frames


def settle(sim, seconds=0.6, balancer=None):
    for _ in range(int(seconds / sim.dt)):
        sim.command(balancer.correct(sim.state(), B.REST) if balancer else B.REST)
        sim.step()


def main(which=None):
    g = gains()
    mk = lambda: Balancer(kp=g["kp"], kd=g["kd"], sign=+1.0)
    made = []

    def clip(name, caption, build):
        if which and name not in which:
            return
        sim = PenguinSim()
        frames = build(sim)
        sim.close()
        path = os.path.join(OUT, name + ".mp4")
        encode(frames, path, caption)
        made.append((name, len(frames), os.path.getsize(path)))
        print("  %-16s %4d frames  %6.1f s  %7.1f kB" %
              (name, len(frames), len(frames) / FPS, os.path.getsize(path) / 1024), flush=True)

    # 1. the tuned walk
    def _walk(sim):
        sim.reset(); bal = mk(); settle(sim, 0.6, bal)
        return play(sim, tuned_gait(), 12.0, balancer=bal, lean_scale=g["lean_scale"],
                    dist=0.42, yaw_cam=140)
    clip("walk", "Waddle gait - 18.6 mm foot clearance", _walk)

    # 2. emote reel
    def _emotes(sim):
        fr = []
        for name in ("greet", "happy", "excited", "curious", "confused",
                     "scared", "giggle", "angry", "proud", "sad", "sleepy"):
            sim.reset(); bal = mk(); settle(sim, 0.4, bal)
            m = B.EMOTES[name]
            fr += play(sim, m, m.duration + 0.5, balancer=bal, dist=0.36, yaw_cam=150, pitch=-8)
        return fr
    clip("emotes", "11 emotional expressions", _emotes)

    # 3. tricks
    def _tricks(sim):
        fr = []
        for name in ("wave", "bow", "flap", "nod", "peekaboo", "spin",
                     "shiver", "stretch", "sneeze", "hiccup", "point_R",
                     "salute", "bigyawn", "headbang"):
            sim.reset(); bal = mk(); settle(sim, 0.4, bal)
            m = B.TRICKS[name]
            fr += play(sim, m, m.duration + 0.5, balancer=bal, dist=0.36, yaw_cam=130, pitch=-8)
        return fr
    clip("tricks", "15 tricks, all verified stable", _tricks)

    # 4. dances
    def _dance(sim):
        fr = []
        for name, fn in B.DANCES.items():
            sim.reset(); bal = mk(); settle(sim, 0.4, bal)
            m = fn()
            fr += play(sim, m, m.duration + 0.4, balancer=bal, dist=0.40, yaw_cam=145, pitch=-8)
        return fr
    clip("dance", "Beat-locked dances - 92 to 128 bpm", _dance)

    # 5. knocked over and getting up
    def _getup(sim):
        fr = []
        for kind, tilt in (("back", (math.radians(-88), 0.0)),
                           ("front", (math.radians(88), 0.0)),
                           ("side", (0.0, math.radians(85)))):
            sim.reset(tilt=tilt)
            settle(sim, 0.8)
            m = B.getup(kind, a=getup_scale(kind))
            fr += play(sim, m, m.duration + 1.5, dist=0.48, yaw_cam=140, pitch=-10)
        return fr
    clip("getup", "Fall recovery: on its back, face down, on its side", _getup)

    # 6. shoved
    def _push(sim):
        import pybullet as pb
        fr = []
        for ang, f in ((90, 1.4), (270, 1.4), (0, 1.4)):
            sim.reset(); bal = mk(); settle(sim, 0.5, bal)
            vx, vy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            for i in range(int(0.05 / sim.dt)):
                pb.applyExternalForce(sim.rid, -1, [f * vx, f * vy, 0], [0, 0, 0.09],
                                      pb.LINK_FRAME, physicsClientId=sim.cid)
                sim.command(bal.correct(sim.state(), B.REST))
                sim.step()
            stand = B.Motion([(0.0, {}), (3.0, {})])
            fr += play(sim, stand, 3.0, balancer=bal, dist=0.44, yaw_cam=140)
        return fr
    clip("push", "Shoved 1.4 N - balance recovery", _push)

    print("\n%d clips in %s" % (len(made), OUT))
    return made


if __name__ == "__main__":
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found on PATH")
    main(sys.argv[1:] or None)
