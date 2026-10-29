"""Motion library for the penguin: gait, emotes, tricks and fall recovery.

Everything is expressed as keyframes over the seven joints, in degrees, using the
friendly names hip_R/hip_L/ankle_R/ankle_L/flipper_R/flipper_L/beak. The player
interpolates with a cosine ease so the servos are never asked for a step change.

Sign conventions, all taken from the CAD:
  hip_*      + yaws that foot's toe INBOARD
  ankle_*    + rolls the body toward the penguin's LEFT (weight onto the left foot)
  flipper_*  0 = straight forward, 90 = hanging down (rest), 180 = straight back,
             negative = raised. Usable range -95..185.
  beak       0 = closed, 30 = fully open.
"""
import math

REST = {"hip_R": 0.0, "hip_L": 0.0, "ankle_R": 0.0, "ankle_L": 0.0,
        "flipper_R": 90.0, "flipper_L": 90.0, "beak": 0.0}

# Flipper travel is NOT the mechanism's 280 deg - an MG90S only turns 180 deg.
# The window below is the 180 deg that keeps the three poses that matter: 90 is
# hanging down (rest), -45 is raised for waving, 135 is swept back for the bow.
# Anything outside it is a motion the servo physically cannot make.
FLIPPER_LO, FLIPPER_HI = -45.0, 135.0
LIMITS = {"hip_R": (-35, 35), "hip_L": (-35, 35), "ankle_R": (-30, 30),
          "ankle_L": (-30, 30),
          "flipper_R": (FLIPPER_LO, FLIPPER_HI), "flipper_L": (FLIPPER_LO, FLIPPER_HI),
          "beak": (0, 30)}


def clamp(pose):
    return {k: max(LIMITS[k][0], min(LIMITS[k][1], v)) for k, v in pose.items()}


def ease(u):
    """Cosine ease-in-out on [0,1]."""
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, u)))


class Motion:
    """A keyframed pose sequence. keys = [(t_seconds, {joint: deg}), ...]"""

    def __init__(self, keys, loop=False, name="motion"):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.loop = loop
        self.name = name

    @property
    def duration(self):
        return self.keys[-1][0]

    def sample(self, t):
        d = self.duration
        if self.loop and d > 0:
            t = t % d
        if t <= self.keys[0][0]:
            return clamp(dict(REST, **self.keys[0][1]))
        if t >= d:
            return clamp(dict(REST, **self.keys[-1][1]))
        for i in range(len(self.keys) - 1):
            t0, p0 = self.keys[i]
            t1, p1 = self.keys[i + 1]
            if t0 <= t <= t1:
                u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
                a = dict(REST, **p0)
                b = dict(REST, **p1)
                return clamp({k: a[k] + (b[k] - a[k]) * u for k in REST})
        return clamp(dict(REST, **self.keys[-1][1]))


# --------------------------------------------------------------------- gait
def waddle(roll=15.0, yaw=18.0, phase=0.25, period=1.2, toe_out=6.0, lean=0.0):
    """Rocking gait: ankle roll shifts the weight, hip yaw steers the free foot.

    roll     ankle roll amplitude, deg. ~15 centres the CoM over the support foot.
    yaw      hip yaw amplitude, deg
    phase    yaw lead over roll, in cycles
    period   seconds per full left-right cycle
    toe_out  static outward yaw on both feet, deg (negative = toe-in)
    lean     constant ankle bias, deg (steers)
    """
    n = 24
    keys = []
    for i in range(n + 1):
        u = i / n
        r = roll * math.sin(2 * math.pi * u)
        yr = yaw * math.sin(2 * math.pi * (u + phase))
        keys.append((u * period, {
            "ankle_R": r + lean, "ankle_L": r + lean,
            # toe_out is mirrored: + on the right is inboard, so the left takes -toe_out
            "hip_R": yr - toe_out, "hip_L": yr + toe_out,
            "flipper_R": 90 - 12 * math.sin(2 * math.pi * u),
            "flipper_L": 90 + 12 * math.sin(2 * math.pi * u),
        }))
    return Motion(keys, loop=True, name="waddle")


def turn(direction=1, roll=15.0, yaw=24.0, period=1.2):
    """Spin on the spot: rock, and yaw both hips the same way while unweighted."""
    n = 24
    keys = []
    for i in range(n + 1):
        u = i / n
        r = roll * math.sin(2 * math.pi * u)
        s = direction * yaw * (1 if math.sin(2 * math.pi * u) > 0 else -1)
        keys.append((u * period, {"ankle_R": r, "ankle_L": r,
                                  "hip_R": s, "hip_L": -s,
                                  "flipper_R": 80, "flipper_L": 80}))
    return Motion(keys, loop=True, name="turn")


# ------------------------------------------------------------------- emotes
def _beakchat(t0, t1, n=4, open_deg=22):
    """Beak chatter keyframes between t0 and t1."""
    keys = []
    for i in range(n * 2 + 1):
        t = t0 + (t1 - t0) * i / (n * 2)
        keys.append((t, {"beak": open_deg if i % 2 else 2}))
    return keys


EMOTES = {}


def _emote(name, keys):
    EMOTES[name] = Motion(keys, name=name)


_emote("happy", [
    (0.0, {}),
    (0.25, {"flipper_R": 35, "flipper_L": 35, "beak": 18, "ankle_R": 6, "ankle_L": 6}),
    (0.50, {"flipper_R": 70, "flipper_L": 70, "beak": 4, "ankle_R": -6, "ankle_L": -6}),
    (0.75, {"flipper_R": 35, "flipper_L": 35, "beak": 18, "ankle_R": 6, "ankle_L": 6}),
    (1.00, {"flipper_R": 70, "flipper_L": 70, "beak": 4, "ankle_R": -6, "ankle_L": -6}),
    (1.35, {}),
])

_emote("excited", [
    (0.0, {}),
    (0.15, {"flipper_R": 10, "flipper_L": 10, "beak": 26}),
    (0.30, {"flipper_R": 95, "flipper_L": 95, "beak": 6}),
    (0.45, {"flipper_R": 10, "flipper_L": 10, "beak": 26}),
    (0.60, {"flipper_R": 95, "flipper_L": 95, "beak": 6}),
    (0.75, {"flipper_R": 10, "flipper_L": 10, "beak": 26}),
    (0.95, {"flipper_R": -40, "flipper_L": -40, "beak": 28}),
    (1.40, {}),
])

_emote("sad", [
    (0.0, {}),
    (0.8, {"flipper_R": 112, "flipper_L": 112, "ankle_R": 0, "ankle_L": 0, "beak": 3}),
    (2.0, {"flipper_R": 115, "flipper_L": 115, "beak": 0}),
    (2.8, {}),
])

_emote("scared", [
    (0.0, {}),
    (0.08, {"flipper_R": -20, "flipper_L": -20, "beak": 30, "ankle_R": 10, "ankle_L": 10}),
    (0.18, {"flipper_R": -10, "flipper_L": -10, "beak": 28, "ankle_R": -10, "ankle_L": -10}),
    (0.32, {"flipper_R": 120, "flipper_L": 120, "beak": 8, "hip_R": 14, "hip_L": -14}),
    (0.70, {"flipper_R": 118, "flipper_L": 118, "beak": 4, "hip_R": 12, "hip_L": -12}),
    (1.60, {}),
])

_emote("curious", [
    (0.0, {}),
    (0.45, {"ankle_R": 11, "ankle_L": 11, "flipper_R": 84, "flipper_L": 96, "beak": 6}),
    (1.10, {"ankle_R": -11, "ankle_L": -11, "flipper_R": 96, "flipper_L": 84, "beak": 9}),
    (1.70, {"ankle_R": 7, "ankle_L": 7, "beak": 3}),
    (2.20, {}),
])

_emote("sleepy", [
    (0.0, {}),
    (1.2, {"flipper_R": 108, "flipper_L": 108, "ankle_R": 4, "ankle_L": 4, "beak": 14}),
    (2.0, {"flipper_R": 110, "flipper_L": 110, "beak": 0}),
    (3.2, {"flipper_R": 112, "flipper_L": 112, "ankle_R": -3, "ankle_L": -3}),
    (4.2, {}),
])

_emote("angry", [
    (0.0, {}),
    (0.18, {"flipper_R": 55, "flipper_L": 55, "beak": 24, "hip_R": -16, "hip_L": 16}),
    (0.36, {"flipper_R": 105, "flipper_L": 105, "beak": 2}),
    (0.54, {"flipper_R": 55, "flipper_L": 55, "beak": 24}),
    (0.72, {"flipper_R": 105, "flipper_L": 105, "beak": 2}),
    (1.10, {}),
])

_emote("confused", [
    (0.0, {}),
    (0.5, {"ankle_R": 12, "ankle_L": 12, "flipper_R": 70, "flipper_L": 100, "beak": 10}),
    (1.0, {"ankle_R": -12, "ankle_L": -12, "flipper_R": 100, "flipper_L": 70, "beak": 4}),
    (1.5, {"ankle_R": 8, "ankle_L": 8, "beak": 12}),
    (2.1, {}),
])

_emote("proud", [
    (0.0, {}),
    (0.5, {"flipper_R": 45, "flipper_L": 45, "ankle_R": 0, "ankle_L": 0, "beak": 8}),
    (1.6, {"flipper_R": 40, "flipper_L": 40, "beak": 2}),
    (2.3, {}),
])

_emote("giggle", [
    (0.0, {}),
    (0.12, {"ankle_R": 9, "ankle_L": 9, "beak": 20, "flipper_R": 60, "flipper_L": 60}),
    (0.24, {"ankle_R": -9, "ankle_L": -9, "beak": 5, "flipper_R": 100, "flipper_L": 100}),
    (0.36, {"ankle_R": 9, "ankle_L": 9, "beak": 20, "flipper_R": 60, "flipper_L": 60}),
    (0.48, {"ankle_R": -9, "ankle_L": -9, "beak": 5, "flipper_R": 100, "flipper_L": 100}),
    (0.60, {"ankle_R": 9, "ankle_L": 9, "beak": 20, "flipper_R": 60, "flipper_L": 60}),
    (0.95, {}),
])

_emote("greet", [
    (0.0, {}),
    (0.35, {"flipper_R": -55, "flipper_L": 95, "beak": 14}),
    (0.60, {"flipper_R": -20, "flipper_L": 95, "beak": 6}),
    (0.85, {"flipper_R": -55, "flipper_L": 95, "beak": 14}),
    (1.10, {"flipper_R": -20, "flipper_L": 95, "beak": 6}),
    (1.60, {}),
])

# ------------------------------------------------------------------- tricks
TRICKS = {}


def _trick(name, keys, loop=False):
    TRICKS[name] = Motion(keys, loop=loop, name=name)


_trick("bow", [
    (0.0, {}),
    (0.7, {"flipper_R": 150, "flipper_L": 150, "ankle_R": 0, "ankle_L": 0, "beak": 4}),
    (1.6, {"flipper_R": 165, "flipper_L": 165, "beak": 0}),
    (2.4, {}),
])

_trick("wave", [
    (0.0, {}),
    (0.3, {"flipper_R": -60, "flipper_L": 90, "beak": 10}),
    (0.55, {"flipper_R": -25, "flipper_L": 90, "beak": 4}),
    (0.80, {"flipper_R": -60, "flipper_L": 90, "beak": 10}),
    (1.05, {"flipper_R": -25, "flipper_L": 90, "beak": 4}),
    (1.30, {"flipper_R": -60, "flipper_L": 90, "beak": 10}),
    (1.85, {}),
])

_trick("flap", [
    (0.0, {}),
    (0.18, {"flipper_R": 20, "flipper_L": 20}),
    (0.36, {"flipper_R": 140, "flipper_L": 140}),
    (0.54, {"flipper_R": 20, "flipper_L": 20}),
    (0.72, {"flipper_R": 140, "flipper_L": 140}),
    (0.90, {"flipper_R": 20, "flipper_L": 20}),
    (1.30, {}),
])

_trick("nod", [
    (0.0, {}), (0.3, {"beak": 20}), (0.55, {"beak": 2}),
    (0.8, {"beak": 20}), (1.05, {"beak": 2}), (1.4, {}),
])

_trick("peekaboo", [
    (0.0, {}),
    (0.5, {"flipper_R": -75, "flipper_L": -75, "beak": 2}),
    (1.6, {"flipper_R": -75, "flipper_L": -75, "beak": 2}),
    (1.9, {"flipper_R": 20, "flipper_L": 20, "beak": 28}),
    (2.6, {}),
])

# Slower and shallower than the first version, which flipped the penguin over at
# the wider stance - 25 deg of hip yaw reversed every 0.4 s is more angular
# momentum than 38 mm of foot can absorb.
_trick("spin", [
    (0.0, {}),
    (0.6, {"ankle_R": 11, "ankle_L": 11, "hip_R": 17, "hip_L": -17, "flipper_R": 55, "flipper_L": 55}),
    (1.2, {"ankle_R": -11, "ankle_L": -11, "hip_R": -17, "hip_L": 17, "flipper_R": 55, "flipper_L": 55}),
    (1.8, {"ankle_R": 11, "ankle_L": 11, "hip_R": 17, "hip_L": -17}),
    (2.4, {"ankle_R": -11, "ankle_L": -11, "hip_R": -17, "hip_L": 17}),
    (3.0, {}),
])

_trick("shiver", [                      # cold, or nervous
    (0.00, {}),
    (0.08, {"ankle_R": 5, "ankle_L": 5, "flipper_R": 104, "flipper_L": 104}),
    (0.16, {"ankle_R": -5, "ankle_L": -5, "flipper_R": 112, "flipper_L": 112}),
    (0.24, {"ankle_R": 5, "ankle_L": 5, "flipper_R": 104, "flipper_L": 104}),
    (0.32, {"ankle_R": -5, "ankle_L": -5, "flipper_R": 112, "flipper_L": 112}),
    (0.40, {"ankle_R": 5, "ankle_L": 5, "flipper_R": 104, "flipper_L": 104}),
    (0.48, {"ankle_R": -5, "ankle_L": -5, "flipper_R": 112, "flipper_L": 112}),
    (0.56, {"ankle_R": 4, "ankle_L": 4, "flipper_R": 106, "flipper_L": 106}),
    (0.90, {}),
])

_trick("stretch", [                     # the wake-up: flippers back, long yawn
    (0.0, {}),
    (0.9, {"flipper_R": 165, "flipper_L": 165, "beak": 26, "ankle_R": -4, "ankle_L": -4}),
    (1.8, {"flipper_R": 170, "flipper_L": 170, "beak": 28}),
    (2.4, {"flipper_R": 40, "flipper_L": 40, "beak": 4}),
    (3.0, {}),
])

_trick("sneeze", [                      # wind up, then a sharp snap forward
    (0.0, {}),
    (0.35, {"flipper_R": 60, "flipper_L": 60, "beak": 10, "ankle_R": -6, "ankle_L": -6}),
    (0.60, {"flipper_R": 45, "flipper_L": 45, "beak": 22, "ankle_R": -9, "ankle_L": -9}),
    (0.68, {"flipper_R": 130, "flipper_L": 130, "beak": 30, "ankle_R": 10, "ankle_L": 10}),
    (0.90, {"flipper_R": 100, "flipper_L": 100, "beak": 2, "ankle_R": 2, "ankle_L": 2}),
    (1.40, {}),
])

_trick("hiccup", [
    (0.0, {}),
    (0.10, {"ankle_R": 8, "ankle_L": 8, "beak": 20, "flipper_R": 72, "flipper_L": 72}),
    (0.28, {"ankle_R": -3, "ankle_L": -3, "beak": 2}),
    (0.75, {}),
    (0.85, {"ankle_R": 8, "ankle_L": 8, "beak": 20, "flipper_R": 72, "flipper_L": 72}),
    (1.03, {"ankle_R": -3, "ankle_L": -3, "beak": 2}),
    (1.50, {}),
])

_trick("point_R", [                     # "that one, over there"
    (0.0, {}),
    (0.45, {"flipper_R": 10, "flipper_L": 95, "beak": 8, "hip_R": -12}),
    (1.40, {"flipper_R": 8, "flipper_L": 95, "hip_R": -12, "beak": 2}),
    (1.90, {}),
])

_trick("point_L", [
    (0.0, {}),
    (0.45, {"flipper_R": 95, "flipper_L": 10, "beak": 8, "hip_L": 12}),
    (1.40, {"flipper_R": 95, "flipper_L": 8, "hip_L": 12, "beak": 2}),
    (1.90, {}),
])

_trick("salute", [
    (0.0, {}),
    (0.35, {"flipper_R": -45, "flipper_L": 95, "beak": 4}),
    (1.10, {"flipper_R": -45, "flipper_L": 95, "beak": 0}),
    (1.60, {}),
])

_trick("bigyawn", [
    (0.0, {}),
    (0.6, {"beak": 30, "flipper_R": 60, "flipper_L": 60, "ankle_R": -5, "ankle_L": -5}),
    (1.5, {"beak": 30, "flipper_R": 55, "flipper_L": 55}),
    (2.1, {"beak": 3, "flipper_R": 100, "flipper_L": 100}),
    (2.6, {}),
])

_trick("headbang", [                    # for when the music is actually good
    (0.00, {}),
    (0.18, {"ankle_R": 13, "ankle_L": 13, "beak": 18, "flipper_R": 35, "flipper_L": 35}),
    (0.36, {"ankle_R": -13, "ankle_L": -13, "beak": 2, "flipper_R": 120, "flipper_L": 120}),
    (0.54, {"ankle_R": 13, "ankle_L": 13, "beak": 18, "flipper_R": 35, "flipper_L": 35}),
    (0.72, {"ankle_R": -13, "ankle_L": -13, "beak": 2, "flipper_R": 120, "flipper_L": 120}),
    (0.90, {"ankle_R": 13, "ankle_L": 13, "beak": 18, "flipper_R": 35, "flipper_L": 35}),
    (1.30, {}),
])


_trick("helpme", [                      # played while it is lying on the floor
    (0.0, {}),
    (0.4, {"flipper_R": -40, "flipper_L": 130, "beak": 26}),
    (0.8, {"flipper_R": 130, "flipper_L": -40, "beak": 6}),
    (1.2, {"flipper_R": -40, "flipper_L": 130, "beak": 26}),
    (1.6, {"flipper_R": 130, "flipper_L": -40, "beak": 6}),
    (2.0, {"flipper_R": 20, "flipper_L": 20, "beak": 22}),
    (2.6, {}),
])


# ------------------------------------------------------------------- idle life
def breathing(period=4.2, depth=2.2, flip=3.0):
    """Always-on idle layer. A robot that is perfectly still reads as switched
    off; a 2 deg sway at breathing rate reads as alive, and it costs almost
    nothing in current because the servos barely move."""
    n = 16
    keys = []
    for i in range(n + 1):
        u = i / n
        s = math.sin(2 * math.pi * u)
        keys.append((u * period, {
            "ankle_R": depth * s, "ankle_L": depth * s,
            "flipper_R": 90 + flip * s, "flipper_L": 90 + flip * s,
        }))
    return Motion(keys, loop=True, name="breathing")


def look_around(period=6.0):
    """Idle curiosity: slow sweeps as if watching the room."""
    return Motion([
        (0.0, {}),
        (1.2, {"ankle_R": 9, "ankle_L": 9, "hip_R": -8, "hip_L": -8, "beak": 3}),
        (2.6, {"ankle_R": 9, "ankle_L": 9, "hip_R": -8, "hip_L": -8}),
        (4.0, {"ankle_R": -9, "ankle_L": -9, "hip_R": 8, "hip_L": 8, "beak": 3}),
        (5.4, {"ankle_R": -9, "ankle_L": -9, "hip_R": 8, "hip_L": 8}),
        (period, {}),
    ], name="look_around")


# --------------------------------------------------------------------- dances
def dance_bob(bpm=110, bars=4):
    """Weight-shift bob locked to the beat, flippers on the off-beat."""
    beat = 60.0 / bpm
    keys = [(0.0, {})]
    for i in range(bars * 4):
        t = (i + 1) * beat
        s = 1 if i % 2 == 0 else -1
        keys.append((t, {"ankle_R": 12 * s, "ankle_L": 12 * s,
                         "flipper_R": 70 if s > 0 else 105,
                         "flipper_L": 105 if s > 0 else 70,
                         "beak": 16 if i % 4 == 0 else 2}))
    keys.append((keys[-1][0] + beat, {}))
    return Motion(keys, name="dance_bob")


def dance_flap(bpm=128, bars=4):
    """Faster: full flipper flaps on every beat with a hip twist every bar."""
    beat = 60.0 / bpm
    keys = [(0.0, {})]
    for i in range(bars * 4):
        t = (i + 1) * beat
        up = i % 2 == 0
        twist = 18 if (i // 4) % 2 == 0 else -18
        keys.append((t, {"flipper_R": 15 if up else 130,
                         "flipper_L": 15 if up else 130,
                         "hip_R": twist, "hip_L": -twist,
                         "ankle_R": 8 if up else -8, "ankle_L": 8 if up else -8,
                         "beak": 20 if up else 2}))
    keys.append((keys[-1][0] + beat, {}))
    return Motion(keys, name="dance_flap")


def dance_sway(bpm=92, bars=4):
    """Slow ballad sway, flippers out wide."""
    beat = 60.0 / bpm
    keys = [(0.0, {})]
    for i in range(bars * 2):
        t = (i + 1) * beat * 2
        s = 1 if i % 2 == 0 else -1
        keys.append((t, {"ankle_R": 16 * s, "ankle_L": 16 * s,
                         "hip_R": 10 * s, "hip_L": 10 * s,
                         "flipper_R": 45, "flipper_L": 45,
                         "beak": 10 if i % 2 == 0 else 3}))
    keys.append((keys[-1][0] + beat, {}))
    return Motion(keys, name="dance_sway")


DANCES = {"bob": dance_bob, "flap": dance_flap, "sway": dance_sway}


# ---------------------------------------------------------------- recovery
def getup(kind="back", a=1.0):
    """Fall recovery. `a` scales the effort, tuned per fall direction by train.py.

    back  : on its back  -> flippers sweep under, rock, push up
    front : face down    -> flippers push the chest up, tuck feet, rock back
    side  : on its side  -> push off the down-side flipper, then the back routine
    """
    if kind == "back":
        return Motion([
            (0.0, {"flipper_R": 90, "flipper_L": 90}),
            (0.4, {"flipper_R": 185, "flipper_L": 185, "beak": 10}),
            (0.9, {"flipper_R": 185, "flipper_L": 185, "hip_R": -30 * a, "hip_L": 30 * a}),
            (1.3, {"flipper_R": 120 * a, "flipper_L": 120 * a,
                   "ankle_R": 25 * a, "ankle_L": 25 * a}),
            (1.7, {"flipper_R": 20, "flipper_L": 20,
                   "ankle_R": -25 * a, "ankle_L": -25 * a, "beak": 24}),
            (2.1, {"flipper_R": 150, "flipper_L": 150, "ankle_R": 0, "ankle_L": 0}),
            (2.6, {}),
        ], name="getup_back")
    if kind == "front":
        return Motion([
            (0.0, {"flipper_R": 90, "flipper_L": 90}),
            (0.4, {"flipper_R": -60, "flipper_L": -60, "beak": 12}),
            (0.9, {"flipper_R": 25 * a, "flipper_L": 25 * a,
                   "hip_R": 30 * a, "hip_L": -30 * a}),
            (1.4, {"flipper_R": 150 * a, "flipper_L": 150 * a,
                   "ankle_R": 20 * a, "ankle_L": 20 * a}),
            (1.9, {"flipper_R": 170, "flipper_L": 170,
                   "ankle_R": -20 * a, "ankle_L": -20 * a, "beak": 20}),
            (2.4, {"flipper_R": 100, "flipper_L": 100, "ankle_R": 0, "ankle_L": 0}),
            (2.9, {}),
        ], name="getup_front")
    return Motion([                                            # side
        (0.0, {"flipper_R": 90, "flipper_L": 90}),
        (0.4, {"flipper_R": 10, "flipper_L": 170, "beak": 14}),
        (0.9, {"flipper_R": 170 * a, "flipper_L": 10,
               "ankle_R": 28 * a, "ankle_L": 28 * a}),
        (1.4, {"flipper_R": 90, "flipper_L": 90,
               "ankle_R": -28 * a, "ankle_L": -28 * a}),
        (1.9, {"flipper_R": 140, "flipper_L": 140, "ankle_R": 0, "ankle_L": 0, "beak": 22}),
        (2.5, {}),
    ], name="getup_side")


ALL = {}
ALL.update({("emote", k): v for k, v in EMOTES.items()})
ALL.update({("trick", k): v for k, v in TRICKS.items()})
