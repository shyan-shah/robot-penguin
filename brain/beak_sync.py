"""Drive the beak from speech audio.

A beak is not a mouth — it has one degree of freedom, so there is no point trying
to do visemes. What reads as "talking" is the beak tracking the loudness envelope
with a fast attack and a slow release, which is roughly what a real bird's jaw
does. The servo is the limiting factor: an MG90S cannot follow a 50 Hz envelope,
so the envelope is smoothed to something it can actually track.

Also exposes a text-only fallback for when the TTS gives no audio back, which
estimates syllables from the words so the beak still moves in time.
"""
import math
import re

BEAK_MIN = 0.0
BEAK_MAX = 28.0           # mechanism allows 30; leave 2 deg so it never buzzes the stop
RATE_LIMIT_DPS = 420.0    # MG90S does ~600 deg/s unloaded; stay inside that


class BeakDriver:
    """Envelope follower -> beak angle, rate-limited to what the servo can do."""

    def __init__(self, fs=16000, frame=256, attack=0.012, release=0.090,
                 floor_db=-46.0, ceil_db=-12.0):
        self.frame = frame
        self.dt = frame / float(fs)
        self.a_att = math.exp(-self.dt / attack)
        self.a_rel = math.exp(-self.dt / release)
        self.floor_db, self.ceil_db = floor_db, ceil_db
        self.env = 0.0
        self.angle = 0.0

    def push(self, samples):
        """samples: iterable of float PCM in [-1, 1]. Returns the next beak angle."""
        n = 0
        acc = 0.0
        for s in samples:
            acc += s * s
            n += 1
        rms = math.sqrt(acc / n) if n else 0.0
        db = 20.0 * math.log10(max(rms, 1e-6))
        u = (db - self.floor_db) / (self.ceil_db - self.floor_db)
        u = max(0.0, min(1.0, u))
        a = self.a_att if u > self.env else self.a_rel
        self.env = a * self.env + (1.0 - a) * u
        target = BEAK_MIN + (BEAK_MAX - BEAK_MIN) * (self.env ** 0.7)
        return self._slew(target)

    def _slew(self, target):
        max_step = RATE_LIMIT_DPS * self.dt
        d = target - self.angle
        self.angle += max(-max_step, min(max_step, d))
        return self.angle

    def close(self):
        self.env = 0.0
        return self._slew(0.0)


_VOWELS = re.compile(r"[aeiouy]+", re.I)


def syllables(word):
    w = word.lower().strip(".,!?;:'\"")
    if not w:
        return 0
    n = len(_VOWELS.findall(w))
    if w.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


def from_text(text, wpm=150.0, open_deg=20.0):
    """Fallback: (time_s, angle_deg) keyframes estimated from the words alone.

    Used when the TTS hands back only a duration, or when the penguin is speaking
    a canned line from flash with no audio stream to follow.
    """
    words = [w for w in text.split() if w.strip()]
    if not words:
        return [(0.0, 0.0)]
    sec_per_syl = 60.0 / (wpm * 1.4)
    keys, t = [(0.0, 0.0)], 0.0
    for w in words:
        for i in range(syllables(w)):
            keys.append((t + sec_per_syl * 0.35, open_deg * (0.75 if i else 1.0)))
            keys.append((t + sec_per_syl * 0.85, 2.0))
            t += sec_per_syl
        t += sec_per_syl * 0.25          # gap between words
    keys.append((t + 0.12, 0.0))
    return keys


if __name__ == "__main__":
    print("text-driven beak keyframes for 'Hello there, I am a penguin!':")
    for t, a in from_text("Hello there, I am a penguin!")[:14]:
        print("  %5.3f s  %5.1f deg" % (t, a))
    d = BeakDriver()
    print("\nenvelope follower, 1 kHz tone bursts:")
    import random
    for i in range(10):
        loud = (i // 2) % 2 == 0
        block = [(0.5 if loud else 0.01) * math.sin(2 * math.pi * 1000 * k / 16000)
                 for k in range(256)]
        print("  frame %2d %-5s -> %5.1f deg" % (i, "loud" if loud else "quiet", d.push(block)))
