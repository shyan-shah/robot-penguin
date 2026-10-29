"""Prove the host and the firmware compute the same fingerprint.

A memory trained on the host is shipped to the robot as a flat blob. If the two
implementations of `fingerprint()` disagree by even one bit on one gram, every
learned association silently stops matching once it is on the robot - and nothing
crashes, so you would only notice as "it never remembers anything".

There is no C compiler on this machine, so this cannot run the firmware code
directly. Instead it contains a deliberately literal, line-by-line transliteration
of learning.cpp - including its fixed-size limits and its C tokeniser - and checks
that brain/learning.py agrees with it on a corpus of awkward strings.

Run it after touching either implementation.
"""
import os
import random
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "brain"))

import learning  # noqa: E402

BITS = 1024
BYTES = BITS // 8
STOP = ["the", "a", "an", "is", "are", "to", "of", "and", "you", "i", "it",
        "that", "this", "do", "does", "did", "can", "will", "would", "me", "my"]


# ---------------------------------------------------------------- the C++ port
def c_fnv1a(buf):
    h = 0xCBF29CE484222325
    for b in buf:
        h ^= b
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def c_set_bits(out, g):
    v = c_fnv1a(g)
    for j in range(3):
        b = (v >> (j * 10)) % BITS
        out[b >> 3] |= 1 << (b & 7)


def c_fingerprint(text):
    """Transliteration of Memory::fingerprint in learning.cpp."""
    # lowercase, punctuation -> single spaces, 128-char buffer
    buf = bytearray()
    for ch in text:
        c = ch.lower()
        if ("a" <= c <= "z") or ("0" <= c <= "9") or c == " " or c == "'":
            if len(buf) >= 127:
                break
            buf += c.encode("ascii", "ignore")
        elif buf and buf[-1:] != b" ":
            if len(buf) >= 127:
                break
            buf += b" "

    # split, drop stopwords, cap at 24 words
    words = []
    for tok in bytes(buf).split(b" "):
        if not tok:
            continue
        if len(words) >= 24:
            break
        if tok.decode() in STOP:
            continue
        words.append(tok)

    out = bytearray(BYTES)
    for w in words:
        c_set_bits(out, w)
    for i in range(len(words) - 1):
        n = min(len(words[i]), 20)
        m = min(len(words[i + 1]), 20)
        c_set_bits(out, words[i][:n] + b"_" + words[i + 1][:m])
    return bytes(out)


# ---------------------------------------------------------------------- corpus
CASES = [
    "good morning", "Good Morning, Penguin!", "how are you doing today",
    "do a dance", "DANCE", "tell me a joke...", "who is a good penguin?",
    "um hey can you dance for me", "i'm home!!!", "goodnight   pingu",
    "what is 17 times 23", "spell onomatopoeia", "", "   ", "!!!",
    "a an the is are to of and", "x", "supercalifragilisticexpialidocious penguin",
    "one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty twentyone "
    "twentytwo twentythree twentyfour twentyfive",
    "café naïve", "penguin\tnewline\nhere",
]


def main():
    rng = random.Random(4)
    for _ in range(400):
        n = rng.randint(1, 10)
        CASES.append(" ".join(
            "".join(rng.choice(string.ascii_letters + "0123456789'.,!?")
                    for _ in range(rng.randint(1, 12))) for _ in range(n)))

    bad = []
    for s in CASES:
        a = learning.fingerprint(s)
        b = c_fingerprint(s)
        if a != b:
            diff = sum(bin(a[i] ^ b[i]).count("1") for i in range(BYTES))
            bad.append((s, diff))

    print("checked %d strings" % len(CASES))
    if bad:
        print("MISMATCH on %d:" % len(bad))
        for s, d in bad[:10]:
            print("   %-50r %d bits differ" % (s[:46], d))
        return 1
    print("host learning.py and firmware learning.cpp agree on every case")

    # and the similarity measure, which is what actually gets used
    pairs = [("good morning", "good morning penguin", "high"),
             ("do a dance", "can you dance for me", "medium"),
             ("do a dance", "what is the capital of peru", "low")]
    print("\nJaccard sanity:")
    for p, q, expect in pairs:
        s = learning.jaccard(learning.fingerprint(p), learning.fingerprint(q))
        print("   %-24s vs %-28s %.3f  (%s)" % (p, q, s, expect))
    return 0


if __name__ == "__main__":
    sys.exit(main())
