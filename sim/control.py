"""Closed-loop balance for the penguin.

The ankles are the only actuators that act on side-to-side lean, so they carry a
small PD term on top of whatever the behaviour is asking for. Without it the
rocking gait pumps itself up: an open-loop +/-15 deg command grows to +/-30 deg of
body lean within three cycles and the penguin goes over, because 28.3 deg is where
the centre of mass leaves the support foot (measured from the CAD, see REPORT.md).

There is deliberately no fore-aft term. The robot has no ankle pitch axis, so
nothing can correct a forward or backward lean; it relies on the 55 mm fore-aft
length of the foot for static stability. That is a real limitation of the
mechanism, not an omission here.
"""
import math


class Balancer:
    """PD on body lean, output added to both ankles.

    kp   deg of ankle per deg of lean error
    kd   deg of ankle per (deg/s) of lean rate
    clip maximum correction, deg
    """

    def __init__(self, kp=0.55, kd=0.045, clip=14.0, sign=-1.0):
        self.kp, self.kd, self.clip, self.sign = kp, kd, clip, sign
        self.last = 0.0

    @staticmethod
    def lean(state):
        """Side-to-side lean in degrees, in the BODY frame.

        This is what the IMU on the frame actually measures. Using world Euler
        angles here is a bug that only shows up once the penguin has turned:
        world roll and pitch mix under yaw, the controller reads a lean that is
        not there, and it walks itself over.
        """
        return state["lean_lat"]

    @staticmethod
    def lean_rate(state):
        return math.degrees(state["omega_body"][1])

    def correct(self, state, pose, target_lean=0.0):
        e = self.lean(state) - target_lean
        c = self.sign * (self.kp * e + self.kd * self.lean_rate(state))
        c = max(-self.clip, min(self.clip, c))
        self.last = c
        out = dict(pose)
        for k in ("ankle_R", "ankle_L"):
            out[k] = out.get(k, 0.0) + c
        return out


class Gaited:
    """Plays a motion with the balancer riding on top.

    The motion's own ankle command is treated as the *target* lean rather than a
    raw position, so the controller aims the body where the gait wants it instead
    of fighting it.
    """

    def __init__(self, motion, balancer=None, lean_scale=1.0):
        self.motion = motion
        self.bal = balancer or Balancer()
        self.lean_scale = lean_scale

    def sample_closed(self, t, state):
        pose = self.motion.sample(t)
        target = self.lean_scale * 0.5 * (pose.get("ankle_R", 0.0) + pose.get("ankle_L", 0.0))
        return self.bal.correct(state, pose, target_lean=target)
