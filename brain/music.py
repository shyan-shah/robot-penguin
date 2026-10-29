"""Hear music, find the beat, and tell the robot when to move.

Deliberately simple: a spectral-flux onset function, autocorrelation for tempo,
and a phase lock so the penguin lands on the beat rather than near it. All of it
runs on a 16 kHz mono stream in small frames, which is what the I2S microphone
gives, and the whole thing costs a few hundred microseconds per frame - it can
run on the ESP32 if you want the dancing to survive a network drop.

What matters for a dancing robot is not tempo accuracy, it is *phase*. An MG90S
takes about 120 ms to swing a flipper, so the command has to go out ahead of the
beat. `next_beat_in()` exists for exactly that.
"""
import math

import numpy as np

FS = 16000
FRAME = 512
HOP = 256
MIN_BPM, MAX_BPM = 60.0, 180.0


class BeatTracker:
    def __init__(self, fs=FS, frame=FRAME, hop=HOP, history_s=8.0):
        self.fs, self.frame, self.hop = fs, frame, hop
        self.win = np.hanning(frame).astype(np.float32)
        self.prev_mag = None
        self.flux = []
        self.max_frames = int(history_s * fs / hop)
        self.frame_dt = hop / float(fs)
        self.bpm = None
        self.confidence = 0.0
        self.phase_s = 0.0          # time since the last predicted beat
        self.t = 0.0
        self._last_beat_t = 0.0

    # ------------------------------------------------------------- onsets
    def push(self, samples):
        """Feed one hop of mono float PCM. Returns True if a beat just landed."""
        x = np.asarray(samples, dtype=np.float32)
        if len(x) < self.frame:
            x = np.pad(x, (0, self.frame - len(x)))
        mag = np.abs(np.fft.rfft(x[:self.frame] * self.win))
        if self.prev_mag is None:
            self.prev_mag = mag
            return False
        # spectral flux: only increases count, which is what an onset is
        d = mag - self.prev_mag
        self.prev_mag = mag
        self.flux.append(float(np.sum(d[d > 0])))
        if len(self.flux) > self.max_frames:
            self.flux.pop(0)
        self.t += self.frame_dt
        if len(self.flux) >= 64 and len(self.flux) % 16 == 0:
            self._estimate()
        return self._beat_now()

    # -------------------------------------------------------------- tempo
    def _estimate(self):
        f = np.asarray(self.flux, dtype=np.float32)
        f = f - f.mean()
        if f.std() < 1e-6:
            self.confidence = 0.0
            return
        f = f / f.std()
        ac = np.correlate(f, f, mode="full")[len(f) - 1:]
        lo = max(1, int(60.0 / MAX_BPM / self.frame_dt))
        hi = min(len(ac) - 1, int(60.0 / MIN_BPM / self.frame_dt))
        if hi <= lo:
            return
        seg = ac[lo:hi]
        k = int(np.argmax(seg)) + lo
        peak = float(seg[k - lo])
        self.confidence = max(0.0, min(1.0, peak / (abs(ac[0]) + 1e-6) * 3.0))
        bpm = 60.0 / (k * self.frame_dt)
        # snap octave errors into the range people actually dance at
        while bpm < 85.0:
            bpm *= 2.0
        while bpm > 170.0:
            bpm /= 2.0
        self.bpm = bpm if self.bpm is None else 0.75 * self.bpm + 0.25 * bpm
        # phase: align to the strongest recent onset
        tail = f[-k:] if k <= len(f) else f
        if len(tail):
            off = int(np.argmax(tail))
            self._last_beat_t = self.t - (len(tail) - 1 - off) * self.frame_dt

    def _beat_now(self):
        if not self.bpm or self.confidence < 0.25:
            return False
        period = 60.0 / self.bpm
        since = self.t - self._last_beat_t
        if since >= period:
            self._last_beat_t += period * math.floor(since / period)
            return True
        return False

    # ------------------------------------------------------------ for the robot
    def next_beat_in(self, lead_s=0.12):
        """Seconds until the next beat, minus the servo's travel time.

        Returns None if there is no confident tempo. `lead_s` defaults to the
        ~120 ms an MG90S needs to throw a flipper, so a command issued now lands
        on the beat rather than after it.
        """
        if not self.bpm or self.confidence < 0.25:
            return None
        period = 60.0 / self.bpm
        since = self.t - self._last_beat_t
        return max(0.0, period - (since % period) - lead_s)

    def style(self):
        """Which of the tuned dances suits this tempo."""
        if not self.bpm:
            return None
        if self.bpm < 100:
            return "sway"
        if self.bpm < 124:
            return "bob"
        return "flap"


if __name__ == "__main__":
    # synthetic 120 bpm click track with noise, to show it locks on
    bpm = 120.0
    dur = 10.0
    n = int(FS * dur)
    sig = (np.random.randn(n) * 0.01).astype(np.float32)
    period = int(FS * 60.0 / bpm)
    for i in range(0, n - 800, period):
        k = np.arange(800)
        sig[i:i + 800] += (np.exp(-k / 90.0) * np.sin(2 * np.pi * 180 * k / FS) * 0.7).astype(np.float32)
    bt = BeatTracker()
    beats = []
    for i in range(0, n - FRAME, HOP):
        if bt.push(sig[i:i + FRAME]):
            beats.append(bt.t)
    print("true tempo      120.0 bpm")
    print("estimated       %.1f bpm   confidence %.2f   style '%s'"
          % (bt.bpm or 0, bt.confidence, bt.style()))
    if len(beats) > 3:
        iv = np.diff(beats)
        print("beats detected  %d, mean interval %.3f s (= %.1f bpm), jitter %.0f ms"
              % (len(beats), iv.mean(), 60.0 / iv.mean(), iv.std() * 1000))
    nb = bt.next_beat_in()
    print("next beat in    %s (servo lead already applied)"
          % ("%.3f s" % nb if nb is not None else "no confident tempo"))
