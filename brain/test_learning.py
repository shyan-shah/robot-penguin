"""Does the penguin actually learn? Simulated households, measured.

Runs a synthetic owner through weeks of interactions and measures three things
that matter on real hardware:

  offline coverage  - what fraction of what the owner says can be answered from
                      the robot's own memory, with no network
  precision         - of those offline answers, how many were the right one
  flash cost        - how big the learned memory gets

The owner is modelled as a mix of a few catchphrases they repeat (which is what
actually happens with a desk robot), paraphrases of them, and genuinely novel
remarks that should always go to the cloud.
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learning import (AssociativeMemory, MATCH_THRESHOLD, fingerprint, jaccard,
                      reaction_score)

DAY = 86400.0

# What a real owner says to a desk penguin, over and over.
CATCHPHRASES = [
    ("good morning",            "greet",   "Morning! I have been standing here all night."),
    ("good morning penguin",    "greet",   "Morning! I have been standing here all night."),
    ("morning pingu",           "greet",   "Morning! I have been standing here all night."),
    ("how are you",             "happy",   "Upright. That is the main thing."),
    ("how are you doing today", "happy",   "Upright. That is the main thing."),
    ("do a dance",              "excited", "Watch this."),
    ("can you dance for me",    "excited", "Watch this."),
    ("dance",                   "excited", "Watch this."),
    ("tell me a joke",          "giggle",  "Why did the penguin cross the road? He could not, too short."),
    ("say something funny",     "giggle",  "Why did the penguin cross the road? He could not, too short."),
    ("who is a good penguin",   "proud",   "Me. Obviously me."),
    ("goodnight",               "sleepy",  "Night. I will be right here. I cannot go anywhere."),
    ("good night pingu",        "sleepy",  "Night. I will be right here. I cannot go anywhere."),
    ("i am going to work",      "sad",     "Fine. I will guard the desk."),
    ("im home",                 "excited", "You are back! Nothing happened. Nothing at all."),
]

NOVEL = [
    "what is the capital of peru", "explain quantum tunnelling", "what day is it",
    "do you like jazz", "what is my meeting schedule", "how tall is everest",
    "whats the weather like", "remind me to buy milk", "who won the match",
    "can you read this document", "what is 17 times 23", "spell onomatopoeia",
]

# Pairs that share words but must NOT be confused. If the matcher is too loose
# these are where it goes wrong, and they are what makes the threshold matter.
CONFUSABLE = [
    ("do a trick",              "excited", "Which one? I know six."),
    ("do you dance",            "curious", "Constantly. Put music on."),
    ("say something",           "curious", "Something."),
    ("tell me the time",        "confused", "I have no idea. I am a penguin."),
    ("good boy",                "proud",   "I am a bird, but thank you."),
    ("is it morning",           "curious", "Probably. It is always morning to me."),
    ("night",                   "sleepy",  "Already? Fine."),
    ("i am going out",          "sad",     "Take me. No? Fine."),
]

# What a small speech recogniser does to a phrase: drops a word, swaps a
# homophone, tacks on a filler.
_SWAPS = {"you": "ya", "are": "r", "going": "goin", "something": "somethin",
          "penguin": "pengwin", "morning": "mornin", "dance": "dans"}


def asr_noise(phrase, rng, p_drop=0.12, p_swap=0.18, p_filler=0.15):
    w = phrase.split()
    out = []
    for t in w:
        if len(w) > 2 and rng.random() < p_drop:
            continue
        if rng.random() < p_swap and t in _SWAPS:
            t = _SWAPS[t]
        out.append(t)
    if rng.random() < p_filler:
        out.insert(0, rng.choice(["um", "hey", "ok", "so"]))
    return " ".join(out) or phrase


KNOWN = CATCHPHRASES + CONFUSABLE


def cloud_answer(phrase):
    """Stand-in for the cloud LLM: knows the repertoire, improvises otherwise."""
    best, best_s = None, 0.0
    fp = fingerprint(phrase)
    for p, emote, say in KNOWN:
        s = jaccard(fingerprint(p), fp)
        if s > best_s:
            best, best_s = (say, emote, None), s
    return best if best_s > 0.45 else ("Hmm. I will think about that one.", "curious", None)


def run(days=28, per_day=16, seed=7, verbose=True, noise=True):
    rng = random.Random(seed)
    mem = AssociativeMemory()
    t0 = time.time()
    log = []
    for day in range(days):
        now = t0 + day * DAY
        asked = offline = correct = wrong = cloud = 0
        for _ in range(per_day):
            r = rng.random()
            if r < 0.62:
                clean, truth_emote, truth_say = rng.choice(CATCHPHRASES)
                is_novel = False
            elif r < 0.80:
                clean, truth_emote, truth_say = rng.choice(CONFUSABLE)
                is_novel = False
            else:
                clean, truth_emote, truth_say = rng.choice(NOVEL), None, None
                is_novel = True
            heard = asr_noise(clean, rng) if noise else clean
            asked += 1
            assoc, sim, confident = mem.recall(heard, now=now)
            if confident:
                offline += 1
                if not is_novel and assoc.say == truth_say:
                    correct += 1
                    mem.reinforce(assoc, reaction_score(laughter=rng.random() < 0.3,
                                                        spoke_again_s=rng.uniform(1, 8)))
                else:
                    wrong += 1
                    # the owner repeats themselves; the robot learns it got it wrong
                    mem.reinforce(assoc, reaction_score(repeated_request=True))
                    say, emote, _ = cloud_answer(clean)
                    if not is_novel:
                        mem.teach(heard, say, emote, None, now=now)
            else:
                cloud += 1
                say, emote, trick = cloud_answer(clean)
                if not is_novel:
                    mem.teach(heard, say, emote, trick, now=now)
        log.append({"day": day, "asked": asked, "offline": offline,
                    "correct": correct, "wrong": wrong, "cloud": cloud,
                    "items": len(mem.items)})
        if verbose and (day % 4 == 0 or day == days - 1):
            cov = 100.0 * offline / asked
            prec = 100.0 * correct / offline if offline else 0.0
            print("  day %2d  %3d said | offline %3d (%4.0f%%) | precision %4.0f%% | "
                  "cloud %3d | memory %3d" % (day, asked, offline, cov, prec, cloud,
                                              len(mem.items)))
    return mem, log


if __name__ == "__main__":
    print("=== simulated owner, 28 days ===")
    mem, log = run()
    tail = log[-7:]
    cov = 100.0 * sum(d["offline"] for d in tail) / sum(d["asked"] for d in tail)
    off = sum(d["offline"] for d in tail)
    prec = 100.0 * sum(d["correct"] for d in tail) / off if off else 0.0
    print()
    print("last 7 days: %.0f%% answered offline, %.0f%% of those correct" % (cov, prec))
    print("memory: %d associations" % len(mem.items))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learned.bin")
    n = mem.export_bin(out)
    print("flash blob: %d bytes (%.1f KB) for %d associations" % (n, n / 1024.0, len(mem.items)))

    print("\nstrongest learned associations:")
    for a in sorted(mem.items, key=lambda a: -a.decayed())[:8]:
        print('  %-26s -> %-8s "%s"  (strength %.1f, %d hits)'
              % ('"%s"' % a.phrase, a.emote, a.say[:38], a.strength, a.hits))

    print("\nthreshold sweep (does MATCH_THRESHOLD=%.2f sit in the right place?)" % MATCH_THRESHOLD)
    import learning
    for th in (0.22, 0.28, 0.34, 0.40, 0.48):
        learning.MATCH_THRESHOLD = th
        m2, l2 = run(days=21, verbose=False, seed=99)
        t2 = l2[-7:]
        c = 100.0 * sum(d["offline"] for d in t2) / sum(d["asked"] for d in t2)
        o = sum(d["offline"] for d in t2)
        p = 100.0 * sum(d["correct"] for d in t2) / o if o else 0.0
        print("  threshold %.2f -> coverage %4.0f%%  precision %4.0f%%  (%d items)"
              % (th, c, p, len(m2.items)))
    learning.MATCH_THRESHOLD = MATCH_THRESHOLD
