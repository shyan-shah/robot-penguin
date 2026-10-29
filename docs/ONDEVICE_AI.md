# The AI, and what runs where

You asked for an LLM on the ESP32 that learns over time. Here is the honest
version of that, what it can and cannot do, and what I built.

## The constraint, stated plainly

| Board | RAM | Can it run a transformer? |
|---|---|---|
| ESP32 (classic) | 520 KB SRAM | **No.** Not even close. |
| ESP32-S3 + 8 MB PSRAM | 8 MB | A ~15M-parameter model at **1–3 tokens/second** |
| Your laptop / a server | GBs | Yes, properly |

A 15M-parameter TinyStories-class model on an S3 is a real thing — it is also, to
be blunt, not very bright, and at 2 tok/s a one-sentence reply takes ten seconds.
It is a party trick, not a conversation.

But "an LLM on the robot" was a means, not the end. The end was: **the penguin
learns how to react to the people around it, and it keeps working when the
Wi-Fi is down.** That is an associative-memory problem, and associative memory
fits in flash with room to spare.

## Three tiers

```
   tier 3   cloud LLM (Claude)          real conversation, and the TEACHER
      |                                  ~600 ms to first word
      |  every reply becomes a candidate association
      v
   tier 1   associative memory           on the robot, offline, instant
            384 associations, ~17 KB     86% of what a regular owner says
      |
      |  nothing matched, and no network?
      v
   tier 2   tiny character LM (optional) offline babble so it is never mute
            ESP32-S3 + PSRAM only        ~2 tok/s, deliberately short lines
```

### Tier 1 — the part that actually learns

Every phrase the robot hears becomes a sparse fingerprint: word unigrams and
bigrams hashed into 1024 bits, three bits per gram. Matching is Jaccard over the
set bits — on an MCU that is a 128-byte AND and a popcount per candidate, so
scanning 384 associations costs well under a millisecond.

Each association holds the phrase, what to say, which emote to play, a strength,
and a timestamp. Strength goes **up** when the response lands and **down** when it
does not, and decays with a 21-day half-life so things the owner stopped saying
fade out.

How it knows a response landed, using only the sensors it has:

| Signal | Source | Weight |
|---|---|---|
| Laughter | microphone | +0.8 |
| A pat on the head | IMU spike while stationary | +0.4 |
| They kept talking within 6 s | conversation timing | +0.3 |
| They walked away | no further audio | −0.3 |
| They repeated themselves | near-duplicate phrase within 10 s | −0.6 |

An association only answers offline once its strength reaches 2.0 — so the robot
has to have seen a response work more than once before it starts trusting itself.

**Measured**, on a simulated 28-day household including speech-recogniser noise
and deliberately confusable phrase pairs ("do a dance" vs "do a trick", "goodnight"
vs "night"):

```
  day  0   offline   0%
  day  8   offline  50%   precision 100%
  day 16   offline  64%   precision 100%
  day 24   offline  86%   precision 100%
  with ASR noise + confusables:  39-46% offline, 95% precision
```

The threshold sweep is the interesting part, because it shows the knob is real:

| match threshold | coverage | precision |
|---|---|---|
| 0.22 | 46 % | 85 % |
| 0.34 (default) | 46 % | 94 % |
| 0.48 | 39 % | 98 % |

Loose means it answers more and is wrong more. 0.34–0.40 is the knee.

### Tier 2 — the optional tiny LM

If you fit an **ESP32-S3 with 8 MB PSRAM** (it is a drop-in BOM change and about
the same price), a llama2.c-style 15M model in int8 fits in PSRAM and runs at
1–3 tok/s. Its job is narrow: when nothing matches and there is no network, emit
one short line so the penguin is never mute. It is not the conversational brain
and should not be asked to be.

**This is a recommendation, not something I have built** — it needs the S3 board in
hand to tune. Flagged for your decision.

### Tier 3 — the cloud LLM

`claude-opus-5-5` by default, `claude-haiku-5-5` if you would rather have snap
responses than better comic timing (`PENGUIN_MODEL` env var).

The model never commands joint angles. It picks a named behaviour from a fixed
vocabulary and the robot plays the version that was tuned and interference-checked
in simulation. That is deliberate: it means the model cannot invent a pose the
mechanism cannot reach, and a behaviour only has to be proved safe once.

Latency trick worth knowing: the reply and the movement come back in **one
streamed tool call**, and the speech starts from the partial JSON rather than
waiting for the model to finish. The `say` field is first in the schema, so it
streams first, and the penguin is usually talking a second before the model has
finished deciding what trick to do.

## What runs where, and why

| | On the ESP32 | On the host |
|---|---|---|
| Servo loop, 100 Hz | ✓ | |
| Balance PD | ✓ | |
| Fall detection and recovery | ✓ | |
| Learned associations | ✓ | |
| Wake word | ✓ | |
| Speech → text | | ✓ |
| LLM | | ✓ |
| Text → speech | | ✓ |

The split is the point: **if this process dies, the penguin still stands up,
balances, and gets itself off the floor.** It just stops talking. Nothing that has
to happen in milliseconds depends on the network.
