"""PyBullet environment for the robot penguin.

The robot is the CAD model: masses, inertias and meshes all come out of Inventor.
Servos are simulated with the MG90S's real stall torque and no-load speed, so a
motion that needs more than the hardware can give will visibly fail here instead
of working in simulation and failing on the bench.

Axis convention matches the CAD: +Z up, +Y is the way the penguin faces,
+X is the penguin's right. The floor is at CAD z = -64 mm.
"""
import json
import math
import os

import numpy as np
import pybullet as p
import pybullet_data

HERE = os.path.dirname(os.path.abspath(__file__))
URDF = os.path.join(HERE, "penguin.urdf")
PROPS = os.path.join(os.path.dirname(HERE), "CAD", "exports", "mass_properties.json")

JOINTS = ["leg_R", "leg_L", "foot_R", "foot_L", "flipper_R", "flipper_L", "beak"]
# friendly names used by the behaviour library
ALIAS = {"hip_R": "leg_R", "hip_L": "leg_L", "ankle_R": "foot_R", "ankle_L": "foot_L"}

# Rest pose. Flippers at +90 deg hang down the sides; 0 would point them straight
# forward, which is how the CAD was modelled but not how a penguin stands.
REST = {"hip_R": 0.0, "hip_L": 0.0, "ankle_R": 0.0, "ankle_L": 0.0,
        "flipper_R": 90.0, "flipper_L": 90.0, "beak": 0.0}


class PenguinSim:
    def __init__(self, gui=False, timestep=1.0 / 240.0, foot_friction=0.8,
                 shell_friction=0.4, servo_scale=1.0, seed=0, terrain=None,
                 urdf=None):
        self.dt = timestep
        self.terrain = terrain          # None = flat, or a dict (see _ground)
        # A variant study must pass its own file. Rewriting the shared
        # penguin.urdf while another search has it open silently hands that
        # search a different robot - which happened once and cost a run.
        self.urdf = urdf or URDF
        self.meta = json.load(open(PROPS))
        self.stall = self.meta["servo"]["stall_torque_Nm"] * servo_scale
        self.vmax = math.radians(self.meta["servo"]["no_load_speed_dps"])
        self.foot_friction = foot_friction
        self.shell_friction = shell_friction
        self.rng = np.random.default_rng(seed)
        self.cid = p.connect(p.GUI if gui else p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.cid)
        self._load()

    # ------------------------------------------------------------------ setup
    def _load(self):
        p.resetSimulation(physicsClientId=self.cid)
        p.setGravity(0, 0, -9.81, physicsClientId=self.cid)
        p.setTimeStep(self.dt, physicsClientId=self.cid)
        p.setPhysicsEngineParameter(numSolverIterations=80, physicsClientId=self.cid)
        self.plane = self._ground()
        # pybullet places the base link's INERTIAL frame, not its URDF origin, so the
        # spawn height has to include the torso's own centre-of-mass offset.
        self.z0 = -self.meta["floor_z_mm"] / 1000.0 + self.meta["links"]["torso"]["com"][2]
        self.rid = p.loadURDF(self.urdf, [0, 0, self.z0], [0, 0, 0, 1],
                              useFixedBase=False, flags=p.URDF_USE_INERTIA_FROM_FILE,
                              physicsClientId=self.cid)
        self.jid = {}
        for i in range(p.getNumJoints(self.rid, physicsClientId=self.cid)):
            info = p.getJointInfo(self.rid, i, physicsClientId=self.cid)
            self.jid[info[1].decode()] = i
        for name, i in self.jid.items():
            fric = self.foot_friction if name.startswith("foot") else self.shell_friction
            p.changeDynamics(self.rid, i, lateralFriction=fric, spinningFriction=0.005,
                             restitution=0.0, linearDamping=0.02, angularDamping=0.02,
                             physicsClientId=self.cid)
        p.changeDynamics(self.rid, -1, lateralFriction=self.shell_friction,
                         restitution=0.0, physicsClientId=self.cid)
        # cache each foot's mesh vertices so ground clearance is the real lowest
        # point of the sole, not a bounding-box estimate
        self.foot_pts = {}
        for nm in ("foot_R", "foot_L"):
            try:
                self.foot_pts[nm] = np.array(p.getMeshData(
                    self.rid, self.jid[nm], physicsClientId=self.cid)[1])
            except Exception:
                self.foot_pts[nm] = np.zeros((1, 3))
        self.reset()

    def clearance(self, foot):
        """Height of the lowest point of that foot above the floor, in mm.

        This is the number that decides whether the penguin trips on a rug, so it
        is measured from the actual sole mesh.
        """
        st = p.getLinkState(self.rid, self.jid[foot], computeForwardKinematics=1,
                            physicsClientId=self.cid)
        R = np.array(p.getMatrixFromQuaternion(st[5])).reshape(3, 3)
        w = (R @ self.foot_pts[foot].T).T + np.array(st[4])
        return float(w[:, 2].min() * 1000.0)

    def _ground(self):
        """Flat floor, carpet, or carpet with something to trip on.

        Carpet is modelled as a *compliant* flat surface plus fine texture, not
        as a rigid random heightfield. That distinction matters: a first attempt
        used an 8 mm heightfield at 9 mm pitch, which gave each foot only four or
        five contact cells and let the robot perch on sharp rigid peaks. It fell
        over *standing still*, which is a property of the model, not of carpet -
        real pile is dense and squashes.

        So:
          pile_mm   fine texture amplitude (cells default 2.5 mm, ~15x15 per foot)
          soft      contact stiffness/damping, so the pile compresses
          friction  carpet grips better than a desk
          step_mm   a separate rigid obstacle across the path - a rug hem, which
                    is the thing that actually trips a small robot
        """
        t = self.terrain
        if not t:
            pid = p.loadURDF("plane.urdf", physicsClientId=self.cid)
            p.changeDynamics(pid, -1, lateralFriction=1.0, restitution=0.0,
                             physicsClientId=self.cid)
            self.terrain_top = 0.0
            return pid

        cell = t.get("cell_mm", 2.5) / 1000.0
        pile = t.get("pile_mm", 6.0) / 1000.0
        span = t.get("span_mm", 420.0) / 1000.0
        n = max(32, int(span / cell))
        rng = np.random.default_rng(t.get("seed", 0))
        h = rng.random((n, n)).astype(np.float32) * pile
        for _ in range(int(t.get("smooth", 2))):          # tufts, not spikes
            h = (h + np.roll(h, 1, 0) + np.roll(h, 1, 1) +
                 np.roll(h, -1, 0) + np.roll(h, -1, 1)) / 5.0
        self._hfield = h.flatten()
        shape = p.createCollisionShape(
            p.GEOM_HEIGHTFIELD, meshScale=[cell, cell, 1.0],
            heightfieldTextureScaling=(n - 1) / 2,
            heightfieldData=self._hfield.tolist(),
            numHeightfieldRows=n, numHeightfieldColumns=n,
            physicsClientId=self.cid)
        pid = p.createMultiBody(0, shape, physicsClientId=self.cid)
        p.resetBasePositionAndOrientation(pid, [0, 0, -float(h.mean())], [0, 0, 0, 1],
                                          physicsClientId=self.cid)
        dyn = {"lateralFriction": t.get("friction", 1.2), "restitution": 0.0}
        if t.get("soft", True):
            # pile compresses under load instead of behaving like rock
            dyn["contactStiffness"] = t.get("stiffness", 12000.0)
            dyn["contactDamping"] = t.get("damping", 400.0)
        p.changeDynamics(pid, -1, physicsClientId=self.cid, **dyn)
        self.terrain_top = float(h.max() - h.mean())

        # a rug hem / threshold strip the penguin has to walk over
        if t.get("step_mm"):
            s = t["step_mm"] / 1000.0
            box = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.25, 0.004, s / 2],
                                         physicsClientId=self.cid)
            vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.25, 0.004, s / 2],
                                      rgbaColor=[0.6, 0.3, 0.2, 1],
                                      physicsClientId=self.cid)
            self.step_id = p.createMultiBody(0, box, vis,
                                             [0, t.get("step_at_mm", 90.0) / 1000.0, s / 2],
                                             physicsClientId=self.cid)
            p.changeDynamics(self.step_id, -1, lateralFriction=1.0,
                             physicsClientId=self.cid)
        return pid

    def reset(self, pose=None, yaw=0.0, height=None, tilt=(0.0, 0.0)):
        """Drop the penguin standing (or at a given roll/pitch) and let it settle."""
        q = p.getQuaternionFromEuler([tilt[0], tilt[1], yaw])
        # A heightfield is centred on its MEAN height, so its peaks stand above
        # z = 0. Spawning at the flat-floor height buries the feet in the pile and
        # the solver kicks the robot out - which looks exactly like "the gait
        # cannot cope with carpet" and is not.
        z = self.z0 + getattr(self, "terrain_top", 0.0) + (0.001 if self.terrain else 0.0)
        if height is not None:
            z = height
        p.resetBasePositionAndOrientation(self.rid, [0, 0, z], q, physicsClientId=self.cid)
        p.resetBaseVelocity(self.rid, [0, 0, 0], [0, 0, 0], physicsClientId=self.cid)
        pose = dict(REST, **(pose or {}))
        for name, deg in pose.items():
            j = self.jid[ALIAS.get(name, name)]
            p.resetJointState(self.rid, j, math.radians(deg), 0.0, physicsClientId=self.cid)
        self.command(pose)
        self.t = 0.0
        return self.state()

    # ------------------------------------------------------------- servo model
    def command(self, pose):
        """Drive servos to target angles in degrees, clamped by the real torque/speed."""
        for name, deg in pose.items():
            j = self.jid.get(ALIAS.get(name, name))
            if j is None:
                continue
            p.setJointMotorControl2(self.rid, j, p.POSITION_CONTROL,
                                    targetPosition=math.radians(deg),
                                    force=self.stall, maxVelocity=self.vmax,
                                    positionGain=0.6, velocityGain=0.6,
                                    physicsClientId=self.cid)

    def step(self, n=1):
        for _ in range(n):
            p.stepSimulation(physicsClientId=self.cid)
            self.t += self.dt

    # ----------------------------------------------------------------- sensing
    def state(self):
        pos, orn = p.getBasePositionAndOrientation(self.rid, physicsClientId=self.cid)
        roll, pitch, yaw = p.getEulerFromQuaternion(orn)
        lin, ang = p.getBaseVelocity(self.rid, physicsClientId=self.cid)
        R = np.array(p.getMatrixFromQuaternion(orn)).reshape(3, 3)
        up = R[2, 2]                                     # world Z of the body's up axis
        # Body-frame tilt, i.e. exactly what the MPU6050 bolted to the frame reads.
        # World Euler angles are NOT usable here: once the penguin has yawed, world
        # roll and pitch mix together and a controller fed from them destabilises.
        g_body = R.T @ np.array([0.0, 0.0, -1.0])
        lean_lat = math.degrees(math.atan2(-g_body[0], -g_body[2]))   # about body Y
        lean_fwd = math.degrees(math.atan2(-g_body[1], -g_body[2]))   # about body X
        omega_body = R.T @ np.array(ang)
        angles, torques = {}, {}
        for name in JOINTS:
            s = p.getJointState(self.rid, self.jid[name], physicsClientId=self.cid)
            angles[name] = math.degrees(s[0])
            torques[name] = s[3]
        return {"t": self.t, "pos": np.array(pos), "rpy": (roll, pitch, yaw), "up": up,
                "vel": np.array(lin), "omega": np.array(ang),
                "lean_lat": lean_lat, "lean_fwd": lean_fwd,
                "omega_body": omega_body,
                "angles": angles, "torques": torques,
                "contacts": self.contacts(), "com": self.com()}

    def contacts(self):
        """Which feet are touching the ground."""
        out = {}
        for foot in ("foot_R", "foot_L"):
            pts = p.getContactPoints(self.rid, self.plane, self.jid[foot], -1,
                                     physicsClientId=self.cid)
            out[foot] = sum(c[9] for c in pts)          # total normal force, N
        return out

    def com(self):
        tot, acc = 0.0, np.zeros(3)
        for i in [-1] + list(range(p.getNumJoints(self.rid, physicsClientId=self.cid))):
            if i == -1:
                m = p.getDynamicsInfo(self.rid, -1, physicsClientId=self.cid)[0]
                c = p.getBasePositionAndOrientation(self.rid, physicsClientId=self.cid)[0]
            else:
                m = p.getDynamicsInfo(self.rid, i, physicsClientId=self.cid)[0]
                c = p.getLinkState(self.rid, i, physicsClientId=self.cid)[0]
            tot += m
            acc += m * np.array(c)
        return acc / tot

    @property
    def fallen(self):
        """Body axis more than ~60 deg off vertical."""
        return self.state()["up"] < 0.5

    def peak_torque_fraction(self):
        s = self.state()
        return max(abs(v) for v in s["torques"].values()) / self.stall

    # ----------------------------------------------------------------- imagery
    def camera(self, width=640, height=480, dist=0.55, yaw=50, pitch=-18, target=None):
        t = target if target is not None else self.com()
        view = p.computeViewMatrixFromYawPitchRoll(t, dist, yaw, pitch, 0, 2,
                                                   physicsClientId=self.cid)
        proj = p.computeProjectionMatrixFOV(55, width / height, 0.01, 4.0,
                                            physicsClientId=self.cid)
        img = p.getCameraImage(width, height, view, proj,
                               renderer=p.ER_BULLET_HARDWARE_OPENGL,
                               physicsClientId=self.cid)
        return np.reshape(img[2], (height, width, 4))[:, :, :3].astype(np.uint8)

    def close(self):
        p.disconnect(physicsClientId=self.cid)


if __name__ == "__main__":
    sim = PenguinSim()
    s = sim.reset()
    print("spawned: up=%.3f  com z=%.1f mm" % (s["up"], s["com"][2] * 1000))
    for _ in range(480):
        sim.command(REST)
        sim.step()
    s = sim.state()
    print("after 2 s settling:")
    print("  upright       : %.4f (1.0 = perfectly vertical)" % s["up"])
    print("  body tilt     : lateral %.2f / fore-aft %.2f deg" % (s["lean_lat"], s["lean_fwd"]))
    print("  CoM height    : %.1f mm above floor" % (s["com"][2] * 1000))
    print("  foot forces   : R %.2f N   L %.2f N  (weight %.2f N)"
          % (s["contacts"]["foot_R"], s["contacts"]["foot_L"],
             sim.meta["total_mass_kg"] * 9.81))
    print("  peak servo    : %.0f %% of stall" % (sim.peak_torque_fraction() * 100))
    sim.close()
