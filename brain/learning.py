"""On-device learning: the penguin remembers what works and gets faster at it.

What this is, honestly
----------------------
A transformer does not fit on an ESP32 - a plain ESP32 has 520 KB of SRAM, and
even a tiny 15M-parameter model needs ~8 MB. So "an LLM on the robot" is not the
right shape for the thing we actually want, which is: *the penguin should learn
how to react to the people around it, and it should keep working when the Wi-Fi
is down.*

That is an associative memory problem, and associative memory fits in flash
comfortably. The design here is:

  tier 1  this file - learned phrase -> response associations, on the robot,
          offline, reinforced by how people actually react. A few hundred
          associations is ~16 KB.
  tier 2  optional tiny character LM on an ESP32-S3 with PSRAM, for offline
          babble when nothing matches. See docs/ONDEVICE_AI.md.
  tier 3  the cloud LLM for real conversation, which is also what *teaches*
          tier 1 - every cloud reply becomes a candidate association.

So the robot genuinely learns over time, it learns specifically from its own
conversations, and the learning survives a power cycle and a dead router.

How matching works
------------------
Each heard phrase becomes a sparse fingerprint: word unigrams and bigrams hashed
into a 1024-bit space. Similarity is Jaccard over the set bits, which is cheap
enough to run against a few hundred stored items on an MCU (a 128-byte AND and
popcount per candidate) and is robust to the word-order noise and dropped words
you get out of a small speech recogniser.
"""
import hashlib
import json
import math
import os
import re
import struct
import time

BITS = 1024
BYTES = BITS // 8
MAX_ITEMS = 384            # ~16 KB of flash at 42 bytes of fingerprint + payload
MATCH_THRESHOLD = 0.40     # Jaccard; swept in test_learning.py (56% coverage, 93% precision)
MERGE_THRESHOLD = 0.48     # above this, a new phrase is the same intent reworded
STRONG = 2.0               # strength at which the robot answers offline without asking the cloud
DECAY_HALFLIFE_DAYS = 21.0

_WORD = re.compile(r"[a-z0-9']+")
_STOP = {"the", "a", "an", "is", "are", "to", "of", "and", "you", "i", "it",
         "that", "this", "do", "does", "did", "can", "will", "would", "me", "my"}

MAX_WORDS = 24      # matches the fixed array in the firmware
MAX_GRAM = 20       # firmware truncates each half of a bigram to 20 chars


def fnv1a64(data):
    """64-bit FNV-1a. Deliberately not a good hash - it is a hash the ESP32 can
    run in a few microseconds, and host and firmware MUST agree bit for bit or a
    memory trained here will not match there. See tools/check_parity.py."""
    h = 0xCBF29CE484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


MAX_TEXT = 127      # firmware normalises into a 128-byte buffer


def normalise(text):
    """Lowercase, punctuation to single spaces, capped at MAX_TEXT.

    Written to match Memory::fingerprint in the firmware character for
    character, including the truncation - tools/check_parity.py enforces it.
    """
    buf = []
    for ch in text:
        c = ch.lower()
        if ("a" <= c <= "z") or ("0" <= c <= "9") or c == " " or c == "'":
            if len(buf) >= MAX_TEXT:
                break
            buf.append(c)
        elif buf and buf[-1] != " ":
            if len(buf) >= MAX_TEXT:
                break
            buf.append(" ")
    return "".join(buf)


def tokens(text):
    w = []
    for t in normalise(text).split(" "):
        if not t:
            continue
        if len(w) >= MAX_WORDS:
            break
        if t in _STOP:
            continue
        w.append(t)
    grams = list(w)
    grams += ["%s_%s" % (w[i][:MAX_GRAM], w[i + 1][:MAX_GRAM])
              for i in range(len(w) - 1)]
    return grams


def fingerprint(text, k=3):
    """Sparse bit fingerprint. k bits per gram, so overlap is meaningful."""
    bits = bytearray(BYTES)
    for g in tokens(text):
        v = fnv1a64(g.encode("utf-8"))
        for j in range(k):
            b = (v >> (j * 10)) % BITS
            bits[b >> 3] |= 1 << (b & 7)
    return bytes(bits)


def popcount(b):
    return sum(bin(x).count("1") for x in b)


def jaccard(a, b):
    inter = sum(bin(a[i] & b[i]).count("1") for i in range(BYTES))
    union = sum(bin(a[i] | b[i]).count("1") for i in range(BYTES))
    return inter / union if union else 0.0


class Association:
    __slots__ = ("fp", "phrase", "say", "emote", "trick", "strength", "hits",
                 "last_s", "created_s")

    def __init__(self, phrase, say, emote, trick=None, strength=1.0):
        self.fp = fingerprint(phrase)
        self.phrase = phrase[:96]
        self.say = say[:160]
        self.emote = emote
        self.trick = trick or ""
        self.strength = strength
        self.hits = 0
        self.last_s = time.time()
        self.created_s = time.time()

    def decayed(self, now=None):
        now = now or time.time()
        dt_days = (now - self.last_s) / 86400.0
        return self.strength * 0.5 ** (dt_days / DECAY_HALFLIFE_DAYS)

    def as_dict(self):
        return {"phrase": self.phrase, "say": self.say, "emote": self.emote,
                "trick": self.trick, "strength": round(self.strength, 3),
                "hits": self.hits}


class AssociativeMemory:
    """What the penguin has learned. Lives on the robot."""

    def __init__(self, path=None, max_items=MAX_ITEMS):
        self.items = []
        self.max_items = max_items
        self.path = path
        self.stats = {"queries": 0, "hits": 0, "offline_answers": 0, "taught": 0}
        if path and os.path.exists(path):
            self.load(path)

    # ------------------------------------------------------------- learning
    def teach(self, phrase, say, emote, trick=None, strength=1.0, now=None):
        """Record what the cloud said, so next time we can say it ourselves."""
        fp = fingerprint(phrase)
        for a in self.items:
            if jaccard(a.fp, fp) > MERGE_THRESHOLD:   # same intent reworded: reinforce
                a.strength = min(6.0, a.strength + 0.5)
                a.say, a.emote, a.trick = say[:160], emote, trick or ""
                a.last_s = now or time.time()
                return a
        a = Association(phrase, say, emote, trick, strength)
        if now:
            a.last_s = a.created_s = now
        self.items.append(a)
        self.stats["taught"] += 1
        self._prune()
        return a

    def reinforce(self, assoc, amount):
        """Positive when people react well, negative when they do not."""
        assoc.strength = max(0.0, min(6.0, assoc.strength + amount))
        assoc.last_s = time.time()
        if assoc.strength < 0.2:
            try:
                self.items.remove(assoc)
            except ValueError:
                pass

    def _prune(self):
        if len(self.items) <= self.max_items:
            return
        self.items.sort(key=lambda a: a.decayed(), reverse=True)
        self.items = self.items[:self.max_items]

    # -------------------------------------------------------------- recall
    def recall(self, phrase, now=None):
        """Best learned response, or None. (assoc, similarity, confident)"""
        self.stats["queries"] += 1
        fp = fingerprint(phrase)
        best, best_s = None, 0.0
        for a in self.items:
            s = jaccard(a.fp, fp)
            if s > best_s:
                best, best_s = a, s
        if best is None or best_s < MATCH_THRESHOLD:
            return None, best_s, False
        self.stats["hits"] += 1
        confident = best.decayed(now) >= STRONG and best_s >= MATCH_THRESHOLD + 0.10
        if confident:
            self.stats["offline_answers"] += 1
        best.hits += 1
        return best, best_s, confident

    # ----------------------------------------------------------- persistence
    def save(self, path=None):
        path = path or self.path
        d = {"version": 1, "stats": self.stats,
             "items": [dict(a.as_dict(), last_s=a.last_s, created_s=a.created_s)
                       for a in self.items]}
        with open(path, "w") as f:
            json.dump(d, f, indent=1)
        return path

    def load(self, path):
        d = json.load(open(path))
        self.stats.update(d.get("stats", {}))
        for it in d.get("items", []):
            a = Association(it["phrase"], it["say"], it["emote"], it.get("trick"),
                            it.get("strength", 1.0))
            a.hits = it.get("hits", 0)
            a.last_s = it.get("last_s", time.time())
            a.created_s = it.get("created_s", a.last_s)
            self.items.append(a)

    def export_bin(self, path):
        """Flat little-endian blob for the ESP32 to mmap out of flash.

        header : magic 'PGM1', uint16 count, uint16 bits, uint8 n_emotes,
                 uint8 n_tricks
        record : fp[128] | strength f32 | hits u16 | emote u8 | trick u8 |
                 say_len u8 | say[say_len]

        The emote and trick counts are in the header on purpose. Behaviours are
        stored as an index into the sorted name list, so adding one behaviour
        shifts every index after it. Without this check a blob written before the
        change would keep loading and quietly play the wrong trick.
        """
        self.items.sort(key=lambda a: a.decayed(), reverse=True)
        from actions import EMOTES, TRICKS
        ekeys, tkeys = sorted(EMOTES), sorted(TRICKS)
        blob = bytearray(b"PGM1" + struct.pack("<HHBB", len(self.items), BITS,
                                               len(ekeys), len(tkeys)))
        for a in self.items:
            say = a.say.encode("utf-8")[:160]
            blob += a.fp
            blob += struct.pack("<fHBBB", a.strength, min(a.hits, 65535),
                                ekeys.index(a.emote) if a.emote in ekeys else 255,
                                tkeys.index(a.trick) if a.trick in tkeys else 255,
                                len(say))
            blob += say
        with open(path, "wb") as f:
            f.write(bytes(blob))
        return len(blob)


# ------------------------------------------------------------- reaction read
# How the robot decides whether a response landed. These are the signals it can
# actually measure with the hardware it has.
def reaction_score(laughter=False, spoke_again_s=None, touched=False,
                   walked_away=False, repeated_request=False):
    s = 0.0
    if laughter:
        s += 0.8
    if touched:
        s += 0.4                      # a pat on the head, read by the IMU
    if spoke_again_s is not None and spoke_again_s < 6.0:
        s += 0.3                      # kept the conversation going
    if walked_away:
        s -= 0.3
    if repeated_request:
        s -= 0.6                      # it did not understand the first time
    return max(-1.0, min(1.0, s))
