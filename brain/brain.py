"""The penguin's brain: speech in, speech and movement out.

Latency is the whole game for something that has to feel alive, so the reply and
the movement come back in one streamed tool call and we start speaking from the
partial JSON rather than waiting for the model to finish. By the time the last
word is generated the penguin has usually been talking for a second already.

The model never commands joint angles — it picks a named behaviour from
actions.py, and the robot plays the version that was tuned and interference-checked
in simulation. That keeps the model from inventing poses the mechanism cannot reach.
"""
import json
import os
import re
import time

import anthropic

from actions import ACTION_TOOL, validate
from persona import CONTEXT, system_prompt

# Opus 5.5 is the default. For a desk toy the latency difference is noticeable —
# set PENGUIN_MODEL=claude-haiku-5-5 if you would rather have snap responses than
# the better comic timing; that is a taste decision, so it is yours to make.
MODEL = os.environ.get("PENGUIN_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("PENGUIN_EFFORT", "low")       # a desk penguin does not need to deliberate
MAX_TURNS = 24                                          # conversation history kept in memory


def _partial_say(buf):
    """Pull the value of "say" out of half-finished tool-input JSON.

    The model emits the fields in schema order and `say` is first, so this sees
    the sentence grow token by token. Returns the text decoded so far.
    """
    m = re.search(r'"say"\s*:\s*"', buf)
    if not m:
        return ""
    out, i = [], m.end()
    while i < len(buf):
        c = buf[i]
        if c == "\\":
            if i + 1 >= len(buf):
                break
            nxt = buf[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/"}.get(nxt, ""))
            i += 2
            continue
        if c == '"':
            break
        out.append(c)
        i += 1
    return "".join(out)


class PenguinBrain:
    def __init__(self, client=None, model=MODEL, on_speech=None, on_action=None,
                 memory=None, offline_ok=True):
        self.client = client or anthropic.Anthropic()
        self.model = model
        self.messages = []
        self.on_speech = on_speech      # called with each new chunk of words
        self.on_action = on_action      # called once with the validated action
        self.last_latency = None
        self.memory = memory            # AssociativeMemory, or None
        self.offline_ok = offline_ok
        self.last_source = None         # "memory" or "cloud"
        self._last_assoc = None
        self._last_heard = None
        self._last_t = 0.0

    # ------------------------------------------------------- learned recall
    def _try_memory(self, heard):
        """Answer from what it has learned, if it is confident enough."""
        if not (self.memory and self.offline_ok):
            return None
        assoc, sim, confident = self.memory.recall(heard)
        if not confident:
            return None
        action = validate({"say": assoc.say, "emote": assoc.emote,
                           "trick": assoc.trick or None})
        self.last_source = "memory"
        self.last_latency = {"first_word_s": 0.0, "total_s": 0.0, "similarity": sim}
        self._last_assoc = assoc
        if self.on_speech:
            self.on_speech(action["say"])
        if self.on_action:
            self.on_action(action)
        return action

    def feedback(self, laughter=False, touched=False, kept_talking=False,
                 walked_away=False, re_asked=False):
        """Tell the memory how the last response landed.

        Call this from whatever is watching the person - the mic for laughter,
        the IMU for a pat on the head, the conversation timing for the rest.
        """
        if not (self.memory and self._last_assoc):
            return 0.0
        from learning import reaction_score
        s = reaction_score(laughter=laughter, touched=touched,
                           spoke_again_s=1.0 if kept_talking else None,
                           walked_away=walked_away, repeated_request=re_asked)
        self.memory.reinforce(self._last_assoc, s)
        return s

    # ------------------------------------------------------------------ input
    def _context_line(self, tags):
        """Turn sensor facts into one short operator note."""
        if not tags:
            return None
        bits = []
        for tag in tags:
            if isinstance(tag, tuple):
                name, fmt = tag
                bits.append(CONTEXT[name].format(**fmt))
            elif tag in CONTEXT:
                bits.append(CONTEXT[tag])
        return " ".join(bits) if bits else None

    def respond(self, heard, tags=None, timeout=20.0):
        """One conversational turn. Returns the validated action dict."""
        # If they just repeated themselves, the last answer was wrong - mark it
        # down and do not serve the same thing again from memory.
        now = time.time()
        re_asked = (self._last_heard and now - self._last_t < 10.0 and
                    heard.strip().lower() == self._last_heard.strip().lower())
        if re_asked:
            self.feedback(re_asked=True)
        self._last_heard, self._last_t = heard, now

        if not tags and not re_asked:
            cached = self._try_memory(heard)
            if cached is not None:
                return cached

        note = self._context_line(tags)
        content = heard if not note else "%s\n\n[%s]" % (heard, note)
        self.messages.append({"role": "user", "content": content})
        self.messages[:] = self.messages[-MAX_TURNS:]

        t0 = time.time()
        spoken = ""
        buf = ""
        first_word_at = None

        tool = dict(ACTION_TOOL, eager_input_streaming=True)
        with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=system_prompt(),
            messages=self.messages,
            tools=[tool],
            # Forced tool choice is rejected on Opus 5.5 / Sonnet 5.5, so the tool is
            # described as mandatory in its own description and we steer with "auto".
            tool_choice={"type": "auto"},
            output_config={"effort": EFFORT},
        ) as stream:
            for event in stream:
                if event.type == "input_json":
                    buf += event.partial_json
                    say = _partial_say(buf)
                    # only emit whole words, so the TTS never splits a syllable
                    if len(say) > len(spoken):
                        cut = say.rfind(" ")
                        if cut > len(spoken):
                            chunk = say[len(spoken):cut + 1]
                            spoken += chunk
                            if first_word_at is None:
                                first_word_at = time.time() - t0
                            if self.on_speech:
                                self.on_speech(chunk)
            msg = stream.get_final_message()

        self.last_latency = {"first_word_s": first_word_at,
                             "total_s": time.time() - t0}

        if msg.stop_reason == "refusal":
            action = {"say": "I'd rather not.", "emote": "confused",
                      "trick": None, "move": None, "dance": None}
            self.messages.append({"role": "assistant", "content": msg.content})
            if self.on_action:
                self.on_action(action)
            return action

        action = None
        for block in msg.content:
            if block.type == "tool_use" and block.name == "act":
                action = validate(block.input)
        if action is None:
            text = "".join(b.text for b in msg.content if b.type == "text").strip()
            action = validate({"say": text or "...", "emote": "curious"})

        # flush whatever the streamed prefix did not cover
        if self.on_speech and len(action["say"]) > len(spoken):
            self.on_speech(action["say"][len(spoken):])

        self.messages.append({"role": "assistant", "content": msg.content})
        # The tool call has to be answered or the next request is rejected.
        self.messages.append({"role": "user", "content": [
            {"type": "tool_result",
             "tool_use_id": next(b.id for b in msg.content if b.type == "tool_use"),
             "content": "done"}]} if any(b.type == "tool_use" for b in msg.content) else
            {"role": "user", "content": "done"})

        # Learn it, so next time this does not need the network. Only phrases
        # worth repeating: a one-off factual question should not become a reflex.
        self.last_source = "cloud"
        self._last_assoc = None
        if self.memory and not tags and self._worth_learning(heard, action):
            self._last_assoc = self.memory.teach(
                heard, action["say"], action["emote"], action["trick"])

        if self.on_action:
            self.on_action(action)
        return action

    @staticmethod
    def _worth_learning(heard, action):
        """A reflex is for things people say repeatedly, not for questions.

        Anything that looks like a request for a fact will have a different right
        answer tomorrow, so caching it would make the penguin confidently stale.
        """
        h = heard.lower().strip()
        if len(h.split()) > 10:
            return False
        for q in ("what is", "what's", "who is", "who's", "when is", "where is",
                  "how many", "how much", "how tall", "how far", "what day",
                  "what time", "remind me", "calculate", "spell "):
            if h.startswith(q) or (" " + q) in h:
                return False
        return len(action["say"]) < 180

    # ------------------------------------------------------- unprompted events
    def react(self, tag, **fmt):
        """Something happened to the penguin and nobody said anything.

        Used for the startle / tickle / music / picked-up cases — the robot has
        already fired its reflex by the time this returns, this is just the
        spoken reaction on top.
        """
        prompts = {
            "startled": "Something just startled you. React.",
            "tickled": "Someone is tickling you. React.",
            "fell": "You fell over and got back up. React.",
            "stuck": "You are on your back and cannot get up on your own. Ask to "
                     "be picked up - keep it light, you are not distressed.",
            "music": "Music just started playing. React.",
            "picked_up": "You have just been picked up. React.",
            "idle": "Say something unprompted.",
            "low_battery": "Mention your battery.",
        }
        return self.respond(prompts.get(tag, "React."),
                            tags=[(tag, fmt)] if fmt else [tag])


if __name__ == "__main__":
    import sys

    said = []
    brain = PenguinBrain(on_speech=lambda c: (said.append(c), print(c, end="", flush=True)))
    line = " ".join(sys.argv[1:]) or "Hello! What are you?"
    print("you  > %s" % line)
    print("pingu> ", end="", flush=True)
    a = brain.respond(line)
    print("\n      emote=%s trick=%s move=%s dance=%s" % (a["emote"], a["trick"], a["move"], a["dance"]))
    print("      first word after %.2f s, full turn %.2f s"
          % (brain.last_latency["first_word_s"] or -1, brain.last_latency["total_s"]))
