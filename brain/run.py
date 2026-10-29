"""Host-side runner: holds the conversation, talks to the robot over WebSocket.

Split of responsibilities is deliberate. The ESP32 owns the millisecond work -
servo loop, balance, fall detection, getting back up - and keeps doing all of it
if this process dies. This process owns the slow, expensive work: speech
recognition, the LLM, text to speech. The robot is never waiting on the network
to stay upright.

Run with no arguments and type at it; that exercises the whole path without
needing a microphone.
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain import PenguinBrain
import beak_sync

PORT = int(os.environ.get("PENGUIN_PORT", "8765"))


class Robot:
    """One connected penguin."""

    def __init__(self):
        self.ws = None
        self.events = asyncio.Queue()

    async def send(self, **payload):
        if self.ws is None:
            print("   [no robot connected: %s]" % json.dumps(payload))
            return
        await self.ws.send(json.dumps(payload))

    async def act(self, action):
        await self.send(**{k: (v or "") for k, v in action.items() if k != "say"})

    async def speak(self, text, tts=None):
        """Play audio and drive the beak from it.

        With a TTS that streams PCM back, the beak follows the real envelope.
        Without one, it falls back to estimating syllables from the text, which
        is visually convincing enough that most people do not notice.
        """
        if tts is None:
            keys = beak_sync.from_text(text)
            t0 = time.time()
            for t, ang in keys:
                await asyncio.sleep(max(0.0, t - (time.time() - t0)))
                await self.send(beak=round(ang, 1))
            await self.send(beak=0)
            return
        drv = beak_sync.BeakDriver()
        async for block in tts(text):
            await self.send(beak=round(drv.push(block), 1))
        await self.send(beak=round(drv.close(), 1))


async def handle_robot(ws, robot):
    robot.ws = ws
    print("[robot connected]")
    try:
        async for raw in ws:
            try:
                d = json.loads(raw)
            except Exception:
                continue
            if "event" in d:
                await robot.events.put(d["event"])
    finally:
        robot.ws = None
        print("[robot disconnected]")


# Robot events the penguin should say something about, and the persona tag to use.
EVENT_TAG = {"falling": None, "down_back": None, "down_front": None,
             "down_side": None, "recovered": "fell", "stuck": "stuck",
             "righted": "picked_up"}


async def event_loop(robot, brain):
    while True:
        ev = await robot.events.get()
        print("[event] %s" % ev)
        tag = EVENT_TAG.get(ev, None)
        if tag is None:
            continue
        action = await asyncio.to_thread(brain.react, tag)
        print("pingu> %s" % action["say"])
        await robot.act(action)
        await robot.speak(action["say"])


async def console_loop(robot, brain):
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        if line in ("/quit", "/q"):
            break
        tags = []
        if line.startswith("/"):                 # /startled, /tickled, /music ...
            tag = line[1:].split()[0]
            action = await asyncio.to_thread(brain.react, tag)
        else:
            action = await asyncio.to_thread(brain.respond, line, tags)
        lat = brain.last_latency or {}
        print("pingu> %s" % action["say"])
        print("       [%s%s%s%s] first word %.2fs"
              % (action["emote"],
                 " +" + action["trick"] if action["trick"] else "",
                 " +" + action["move"] if action["move"] else "",
                 " +" + action["dance"] if action["dance"] else "",
                 lat.get("first_word_s") or -1))
        await robot.act(action)
        await robot.speak(action["say"])


async def idle_loop(robot, brain, quiet_s=240.0):
    """Say something unprompted when the room has been quiet for a while.

    A desk robot that only ever responds reads as switched off between
    conversations. The interval is deliberately long and jittered - a penguin
    that pipes up every thirty seconds stops being charming very quickly.
    """
    import random
    while True:
        wait = quiet_s * random.uniform(0.7, 1.8)
        await asyncio.sleep(wait)
        if time.time() - brain._last_t < quiet_s:
            continue                       # someone has been talking; leave it
        action = await asyncio.to_thread(brain.react, "idle")
        print("pingu> (unprompted) %s" % action["say"])
        await robot.act(action)
        await robot.speak(action["say"])


async def main():
    robot = Robot()
    brain = PenguinBrain()
    try:
        import websockets
    except ImportError:
        print("websockets not installed - running console only "
              "(pip install websockets to drive a real robot)")
        websockets = None

    tasks = [asyncio.create_task(console_loop(robot, brain)),
             asyncio.create_task(event_loop(robot, brain)),
             asyncio.create_task(idle_loop(robot, brain))]
    if websockets:
        server = await websockets.serve(lambda ws: handle_robot(ws, robot), "0.0.0.0", PORT)
        print("listening for the penguin on ws://0.0.0.0:%d" % PORT)
    print("type to talk to it;  /startled  /tickled  /music  /idle  for events;  /q to quit")
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    if websockets:
        server.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
