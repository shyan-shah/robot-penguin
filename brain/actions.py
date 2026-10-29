"""The action vocabulary — the contract between the brain and the robot.

The LLM never commands servo angles. It picks a named behaviour from this list and
the robot plays the tuned, interference-checked motion for it. That keeps the model
from inventing poses the mechanism cannot reach, and means a behaviour only has to
be proved safe once, in simulation.
"""

EMOTES = {
    "greet":    "flipper raise and a short wave, beak chatter",
    "happy":    "both flippers lift and drop twice with a small body bob",
    "excited":  "fast double flap, flippers thrown up, beak wide",
    "curious":  "head tilt one way then the other, beak slightly open",
    "confused": "slow tilt both ways, flippers at odd heights",
    "scared":   "sharp recoil, flippers snap up then clamp to the body, beak wide",
    "giggle":   "quick small body shakes with beak chatter",
    "angry":    "flippers slap down twice, feet turned out, beak snaps",
    "proud":    "chest out, flippers held high and still",
    "sad":      "flippers droop, body settles, beak closed",
    "sleepy":   "slow droop, long beak yawn, gentle sway",
}

TRICKS = {
    "wave":     "one flipper raised and waved",
    "bow":      "flippers swept back, body settles - the closest thing to a bow",
    "flap":     "both flippers beat fast, three times",
    "nod":      "beak nods yes",
    "peekaboo": "flippers up over the face, pause, then thrown open with beak wide",
    "spin":     "rocks and yaws to turn roughly 60 degrees on the spot",
    "shiver":   "fast small shakes - cold, or nervous",
    "stretch":  "flippers swept right back and a long yawn - the wake-up",
    "sneeze":   "winds up, then snaps forward with the beak wide",
    "hiccup":   "two sharp involuntary bobs",
    "point_R":  "points with the right flipper and leans that way",
    "point_L":  "points with the left flipper and leans that way",
    "salute":   "one flipper up to the brow, held",
    "bigyawn":  "beak wide open for a long second, flippers drooping",
    "headbang": "hard rhythmic rocking - for when the music is actually good",
    "helpme":   "lying on its back, waggling its flippers - asks to be picked up",
}

MOVES = {
    "walk":     "waddle forward",
    "back":     "waddle backward",
    "turn_left":  "spin left on the spot",
    "turn_right": "spin right on the spot",
    "stop":     "stand still",
}

DANCES = {
    "bob":  "weight-shift bob, best 95-120 bpm",
    "flap": "fast flipper dance, best 120-140 bpm",
    "sway": "slow sway, best 80-100 bpm",
}

# Reflexes run on the robot itself, never via the LLM - they need to be immediate.
REFLEXES = {
    "getup_back":  "recover from lying on its back",
    "getup_front": "recover from lying face down",
    "getup_side":  "recover from lying on its side",
    "brace":       "feet flat, flippers in, hold - triggered when a fall starts",
    "startle":     "the scared emote, fired by the IMU before the LLM has said anything",
    "stuck":       "after a failed recovery - plays helpme and asks out loud",
}

ALL_BEHAVIOURS = {}
for group, d in (("emote", EMOTES), ("trick", TRICKS), ("move", MOVES),
                 ("dance", DANCES), ("reflex", REFLEXES)):
    for k, v in d.items():
        ALL_BEHAVIOURS[k] = {"group": group, "description": v}


def catalogue(exclude_reflexes=True):
    """One line per behaviour, for dropping into the system prompt."""
    rows = []
    for name, meta in ALL_BEHAVIOURS.items():
        if exclude_reflexes and meta["group"] == "reflex":
            continue
        rows.append("  %-11s (%-5s) %s" % (name, meta["group"], meta["description"]))
    return "\n".join(rows)


ACTION_TOOL = {
    "name": "act",
    "description": (
        "Say something and move at the same time. Call this exactly once per turn. "
        "The body language carries as much as the words, so pick a behaviour that "
        "matches the mood even when the reply is short."),
    "input_schema": {
        "type": "object",
        "properties": {
            "say": {"type": "string",
                    "description": "What the penguin says out loud. Keep it to one or "
                                   "two short sentences - it is a small robot, not a "
                                   "narrator. Plain text, no emoji, no stage directions."},
            "emote": {"type": "string", "enum": sorted(EMOTES),
                      "description": "The emotional expression to play while speaking."},
            "trick": {"type": "string", "enum": sorted(TRICKS) + [""],
                      "description": "An optional trick to play after speaking. Empty if none."},
            "move": {"type": "string", "enum": sorted(MOVES) + [""],
                     "description": "Optional locomotion. Empty to stay put."},
            "dance": {"type": "string", "enum": sorted(DANCES) + [""],
                      "description": "Start dancing. Only when there is music, or when asked."},
        },
        "required": ["say", "emote"],
    },
}


def validate(action):
    """Clamp whatever came back to something the robot can actually do."""
    out = {"say": str(action.get("say", ""))[:400],
           "emote": action.get("emote") if action.get("emote") in EMOTES else "happy",
           "trick": action.get("trick") if action.get("trick") in TRICKS else None,
           "move": action.get("move") if action.get("move") in MOVES else None,
           "dance": action.get("dance") if action.get("dance") in DANCES else None}
    return out
