"""Studio renders of the penguin, straight out of Inventor's viewport.

Run the body of this through the Inventor MCP's execute_python (it needs the live
`app`, `tg`, `asm`, `v` objects). It is kept here because three things about it
are non-obvious and cost a while to find.

1. `view_image` in the MCP returns a CACHED picture. Every render looked
   identical no matter the camera, which sent me hunting a camera bug that did
   not exist. The files on disk were always correct and different. Check renders
   by decoding the PNG (see the framing check at the bottom), never by eye
   through that helper.

2. `Camera.Fit()` fits the GROUND PLANE as well as the robot, so the penguin
   came out at 58% of frame height instead of ~88%. The framing here instead
   projects the eight corners of the known model bounding box onto the camera's
   own up/right axes and sets the extents from that. It is exact in any aspect
   ratio.

3. Ray tracing (`SaveAsBitmapWithRayTracing`) will not engage through the API in
   this setup - the `RayTracing` flag reads back False after being set. The
   shaded viewport with ground shadows and reflections is what these use, and at
   4K it is more than good enough.

A 229 mm tall robot does not suit 16:9. The shot list is mostly 4:5 and 1:1.

WHICH WAY IS FORWARD. The beak points +Y (BEAK_UPPER sits at Y 23..50), so the
camera has to be on the +Y side to see the face. The first version of this put
az=0 at -Y and quietly rendered the BACK of the robot in every shot, including
the hero. Nothing in the picture says which end you are looking at when the
framing is symmetrical, so check it in pixels: crop the top 40% and count orange
(the beak). Face-on gives thousands of orange pixels and a mostly white head;
from behind it is zero orange and a near-solid black head. The basis is now
fwd = (cos(el)sin(az), cos(el)cos(az), sin(el)), which puts az=0 on the face.

CAUTION: rendering a long frame sequence in one call wedged Inventor at frame 63
of 120 (stuck inside a COM call, unrecoverable without a restart). Render
sequences in chunks of about 30 frames per call - four such chunks completed a
full 120-frame turntable with no trouble.

BACKGROUND. The schemes' colours are read-only, so a custom backdrop is out. For
a pure white studio background, activate the "Presentation" scheme and set
ColorSchemes.BackgroundType = 52737 (one colour); its ScreenColor is white.
52739 is the gradient. The user's own scheme is "Dark" - put it back afterwards.

HIDE THE SKETCHES. Visible sketches render their geometry AND their dimensions
into the picture. Four of them (head_front and head_back) were putting stray
lines over the first set of renders. Walk every occurrence's Sketches, WorkPlanes,
WorkAxes and WorkPoints and set Visible = False before rendering.

THE WALK CYCLE. The assembly grounds the BODY, so driving the ankle constraints
swings the feet instead of rocking the body, and the feet drop about 5.5 mm
through the floor at full roll. For a front-ish view the body roll axis (fore-aft)
lies along the view direction, so rolling the CAMERA's up vector by the ankle
angle converts it exactly into the real thing: feet planted, body rocking. The
ground plane has to be switched off for that shot, or the tilting floor gives it
away. Joint angles come from the tuned gait in sim/tuned/gait_v2.json, sampled
over one period - 45 frames at 30 fps loops seamlessly because the gait is
periodic. Note the flipper convention differs: 90 deg is rest in the simulation,
0 deg in the CAD drive constraints.
"""

SHOTS = [
    # name,      azimuth, elevation, width, height
    ("hero_3q",    35,  12, 3072, 3840),   # 4:5, the main one. az 0 = FACE.
    ("hero_low",   28,  -3, 3072, 3840),   # slightly below eye line, more heroic
    ("front",       0,   6, 2880, 2880),   # 1:1
    ("side",       90,   4, 2880, 2880),
    ("back",      180,  10, 3072, 3840),
    ("three_q_L", -40,  14, 3072, 3840),
    ("story",      30,   8, 2160, 3840),   # 9:16
    ("banner",     35,  10, 3840, 2160),   # 16:9
]

# Appearances are created in the ASSEMBLY document and assigned per occurrence,
# so the parts keep their real PLA material (and therefore their real mass) while
# rendering in penguin colours.
PALETTE = {
    "shell_white": ((238, 238, 243), 0.62, 0.07, 0.60),   # belly, face
    "shell_black": (( 26,  26,  32), 0.70, 0.08, 0.65),   # back, head back, flippers
    "beak_orange": ((242, 116,  14), 0.60, 0.06, 0.55),   # beak, feet
    "leg_grey":    ((118, 118, 126), 0.45, 0.05, 0.45),
    "frame_grey":  (( 92,  92, 100), 0.35, 0.04, 0.35),
}
ASSIGN = {
    "BODY_FRONT": "shell_white", "HEAD_FRONT": "shell_white",
    "BODY_BACK": "shell_black", "HEAD_BACK": "shell_black",
    "FLIPPER_R": "shell_black", "FLIPPER_L": "shell_black",
    "BEAK_UPPER": "beak_orange", "BEAK_LOWER": "beak_orange",
    "FOOT_R": "beak_orange", "FOOT_L": "beak_orange",
    "LEG_R": "leg_grey", "LEG_L": "leg_grey",
    "CORE_FRAME": "frame_grey", "BASE_PLATE": "frame_grey",
}

SETUP = '''
# --- scene, once per session
v.AreTexturesOn = True
for p in ("ShowObjectShadows", "ShowGroundShadows", "ShowAmbientShadows",
          "ShowGroundReflections", "ShowGroundPlane"):
    setattr(v, p, True)
for p in ("ViewCubeEnabled", "NavigationBarEnabled", "SteeringWheelEnabled"):
    setattr(v, p, False)
app.GeneralOptions.Show3DIndicator = False
'''

FRAMING = '''
# Exact model bounds, EXCLUDING the ground plane - this is the fix for Fit().
BB = ((-60.1, 60.1), (-47.0, 55.0), (-64.0, 165.4))
CORNERS = [(x, y, z) for x in BB[0] for y in BB[1] for z in BB[2]]

def shot(name, az, el, w, h, fill=0.88, target=None, zoom=1.0):
    import math, os
    cam = v.Camera
    a, e = math.radians(az), math.radians(el)
    fwd = (math.cos(e)*math.sin(a), -math.cos(e)*math.cos(a), math.sin(e))
    rx = fwd[1]; ry = -fwd[0]; rz = 0.0            # fwd x (0,0,1), before normalising
    rn = math.hypot(rx, ry); rx, ry = rx/rn, ry/rn
    ux = ry*fwd[2]; uy = -rx*fwd[2]; uz = rx*fwd[1]-ry*fwd[0]
    tgt = target or (0.0, 4.0, 50.0)
    us = [(c[0]-tgt[0])*ux + (c[1]-tgt[1])*uy + (c[2]-tgt[2])*uz for c in CORNERS]
    rs = [(c[0]-tgt[0])*rx + (c[1]-tgt[1])*ry for c in CORNERS]
    asp = float(w)/float(h)
    ext_h = max((max(us)-min(us))/fill, (max(rs)-min(rs))/fill/asp) * zoom
    cu, cr = 0.5*(max(us)+min(us)), 0.5*(max(rs)+min(rs))
    tgt = (tgt[0]+cu*ux+cr*rx, tgt[1]+cu*uy+cr*ry, tgt[2]+cu*uz)
    D = 90.0
    cam.Target = tg.CreatePoint(tgt[0]/10.0, tgt[1]/10.0, tgt[2]/10.0)
    cam.Eye = tg.CreatePoint(tgt[0]/10.0+fwd[0]*D, tgt[1]/10.0+fwd[1]*D, tgt[2]/10.0+fwd[2]*D)
    cam.UpVector = tg.CreateUnitVector(0, 0, 1)
    cam.Perspective = True
    cam.Apply()
    cam.SetExtents(ext_h*asp/10.0, ext_h/10.0)
    cam.Apply()
    v.Update()
    opts = app.TransientObjects.CreateNameValueMap(); opts.Add("Resolution", 300)
    p = os.path.join(RENDERS, name + ".png")
    v.Camera.SaveAsBitmapWithOptions(p, w, h, opts)
    return p
'''

# Turntable: render in chunks, then
#   ffmpeg -framerate 30 -i turntable/f%03d.png \
#     -filter_complex "[0]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1,scale=1080:1350" \
#     -c:v libx264 -pix_fmt yuv420p -crf 16 turntable_1080.mp4
# The forward-then-reverse concat makes a seamless loop out of a partial sweep.

if __name__ == "__main__":
    print(__doc__)
    print("Shot list:")
    for s in SHOTS:
        print("   %-11s az %4d  el %3d  %dx%d" % (s[0], s[1], s[2], s[3], s[4]))
