// Robot penguin - ESP32 firmware.
//
// Responsibilities split: this board owns everything that must happen in
// milliseconds (servo loop, balance, fall detection, reflexes) and the host owns
// everything that can take a second (speech recognition, the LLM, text to speech).
// If Wi-Fi drops the penguin still stands up, balances, and reacts to being
// knocked over - it just stops talking.
//
// Motion tables in motions.h are generated from the simulation; see
// firmware/export_motions.py. Do not hand-edit them.

#include <Arduino.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

#include "motions.h"
#include "learning.h"

// ----------------------------------------------------------------- hardware
// ESP32-S3-DevKitC-1 N8R8 pin map. NOT the classic-ESP32 numbers: on the S3 the
// GPIOs 22-25 do not exist at all, and 26-37 are taken by the SPI flash and the
// octal PSRAM. Five of the seven pins this used to use are unusable on the board
// the BOM specifies. Safe general-purpose pins on N8R8 are 1-18, 21, 38-42, 47
// and 48 (19/20 are native USB, 43/44 are UART0).
// order: hip_R, hip_L, ankle_R, ankle_L, flipper_R, flipper_L, beak
static const int SERVO_PIN[N_JOINTS] = {4, 5, 6, 7, 15, 16, 17};
//                                 hipR hipL ankR ankL flipR flipL beak

// Joint limits. Hips/ankles/beak come from the CAD; the FLIPPER range is set by
// the servo, not the mechanism - the linkage allows 280 deg but an MG90S only
// turns 180. -45..135 is the window that keeps rest (90), wave (-45) and the
// bow (135). The firmware never commands outside these, whatever the host asks.
static const int16_t LIM_LO[N_JOINTS] = {-35, -35, -30, -30, -45, -45, 0};
static const int16_t LIM_HI[N_JOINTS] = {35, 35, 30, 30, 135, 135, 30};

// Per-joint trim (deg) - set these once on the bench so 0 is really 0.
static int16_t TRIM[N_JOINTS] = {0, 0, 0, 0, 0, 0, 0};
// Some horns end up mirrored; flip here rather than re-cutting the motion tables.
static const int8_t DIR[N_JOINTS] = {1, 1, 1, 1, 1, 1, 1};

static const int16_t REST[N_JOINTS] = {0, 0, 0, 0, 90, 90, 0};

Servo servo[N_JOINTS];
static float cmd[N_JOINTS];      // what we are driving, deg
static float goal[N_JOINTS];     // where the player wants us, deg

// MPU6050
static const uint8_t MPU = 0x68;
static float lean = 0.0f, leanRate = 0.0f;   // side-to-side, deg and deg/s
static float pitchFwd = 0.0f;                // fore-aft, deg (no actuator for it)
static float upAxis = 1.0f;                  // 1 = upright, 0 = on its side

// ------------------------------------------------------------------ config
static const char* WIFI_SSID = "CHANGE_ME";
static const char* WIFI_PASS = "CHANGE_ME";
static const char* HOST_IP   = "192.168.1.10";
static const uint16_t HOST_PORT = 8765;

WebSocketsClient ws;

// ------------------------------------------------------------- motion player
struct Player {
  int idx = -1;         // index into MOTIONS, -1 = idle
  uint32_t t0 = 0;
  bool loop = false;
  int queued = -1;
} player;

static int findMotion(const char* name) {
  for (uint8_t i = 0; i < N_MOTIONS; i++)
    if (!strcmp(MOTIONS[i].name, name)) return i;
  return -1;
}

static void play(const char* name, bool loop = false) {
  int i = findMotion(name);
  if (i < 0) return;
  player.idx = i;
  player.t0 = millis();
  player.loop = loop || MOTIONS[i].loop;
}

static void stopMotion() { player.idx = -1; }

// Sample the active motion into goal[]. Linear between frames - the tables are
// already at 50 Hz, so there is nothing to be gained from anything fancier.
static void sampleMotion() {
  for (int j = 0; j < N_JOINTS; j++) goal[j] = REST[j];
  if (player.idx < 0) return;
  const MotionDef& m = MOTIONS[player.idx];
  float t = (millis() - player.t0) / 1000.0f;
  float fpos = t * MOTION_HZ;
  if (fpos >= m.n - 1) {
    if (player.loop) { fpos = fmodf(fpos, (float)(m.n - 1)); }
    else {
      for (int j = 0; j < N_JOINTS; j++) goal[j] = m.frames[m.n - 1][j];
      stopMotion();
      if (player.queued >= 0) { player.idx = player.queued; player.queued = -1; player.t0 = millis(); }
      return;
    }
  }
  int i0 = (int)fpos, i1 = i0 + 1;
  float u = fpos - i0;
  if (i1 > m.n - 1) i1 = m.n - 1;
  for (int j = 0; j < N_JOINTS; j++)
    goal[j] = m.frames[i0][j] + (m.frames[i1][j] - m.frames[i0][j]) * u;
}

// -------------------------------------------------------------------- IMU
static void imuInit() {
  Wire.begin(8, 9);                               // MPU6050 SDA 8, SCL 9 (S3-safe)
  Wire.setClock(400000);
  Wire.beginTransmission(MPU); Wire.write(0x6B); Wire.write(0x00); Wire.endTransmission();
  Wire.beginTransmission(MPU); Wire.write(0x1C); Wire.write(0x08); Wire.endTransmission(); // +-4g
  Wire.beginTransmission(MPU); Wire.write(0x1B); Wire.write(0x08); Wire.endTransmission(); // +-500 dps
}

static void imuRead(float dt) {
  Wire.beginTransmission(MPU); Wire.write(0x3B); Wire.endTransmission(false);
  Wire.requestFrom((int)MPU, 14, 1);
  if (Wire.available() < 14) return;
  int16_t raw[7];
  for (int i = 0; i < 7; i++) raw[i] = (Wire.read() << 8) | Wire.read();
  float ax = raw[0] / 8192.0f, ay = raw[1] / 8192.0f, az = raw[2] / 8192.0f;
  float gy = raw[5] / 65.5f;                       // about the robot's Y axis
  // Accelerometer gives the absolute angle; the gyro gives the fast part.
  float accLean = atan2f(ax, az) * 57.2958f;
  leanRate = gy;
  lean = 0.96f * (lean + gy * dt) + 0.04f * accLean;   // complementary filter
  pitchFwd = atan2f(ay, az) * 57.2958f;
  upAxis = az / sqrtf(ax * ax + ay * ay + az * az + 1e-6f);
}

// ---------------------------------------------------------------- balance
// PD on side-to-side lean, added to both ankles. Gains came out of the
// simulation sweep (sim/tuned/gait.json) - see BAL_KP / BAL_KD in motions.h.
static float balance(float targetLean) {
  float e = lean - targetLean;
  float c = BAL_KP * e + BAL_KD * leanRate;
  if (c > BAL_CLIP_DEG) c = BAL_CLIP_DEG;
  if (c < -BAL_CLIP_DEG) c = -BAL_CLIP_DEG;
  return c;
}

// ---------------------------------------------------------------- reflexes
enum State { ST_IDLE, ST_BUSY, ST_FALLING, ST_DOWN, ST_RECOVER };
static State state = ST_IDLE;
static uint32_t stateAt = 0;
static uint32_t recoverStart = 0;
static const char* downKind = "back";
static uint8_t recoverTries = 0;
static const uint8_t MAX_RECOVER_TRIES = 1;   // see docs/SELF_RIGHTING.md

static void sendEvent(const char* ev, float v = 0) {
  StaticJsonDocument<128> d;
  d["event"] = ev;
  if (v != 0) d["value"] = v;
  char buf[128];
  size_t n = serializeJson(d, buf);
  ws.sendTXT(buf, n);
}

// Which way is it lying? Decided from gravity once it has settled.
static const char* fallKind() {
  if (fabsf(pitchFwd) > 55.0f) return pitchFwd > 0 ? "front" : "back";
  return "side";
}

// The learned recovery is an oscillation, not a keyframe sequence, so it is
// generated here rather than looked up. Constants from getup_search.py.
static void driveRecovery(float t) {
  float freq = GETUP_BACK_FREQ, ampR = GETUP_BACK_AMPR, ampL = GETUP_BACK_AMPL;
  float centre = GETUP_BACK_CENTRE, phase = GETUP_BACK_PHASE;
  float hip = GETUP_BACK_HIP, ank = GETUP_BACK_ANK, ankph = GETUP_BACK_ANKPH;
  float ramp = GETUP_BACK_RAMP;
  if (!strcmp(downKind, "front")) {
    freq = GETUP_FRONT_FREQ; ampR = GETUP_FRONT_AMPR; ampL = GETUP_FRONT_AMPL;
    centre = GETUP_FRONT_CENTRE; phase = GETUP_FRONT_PHASE; hip = GETUP_FRONT_HIP;
    ank = GETUP_FRONT_ANK; ankph = GETUP_FRONT_ANKPH; ramp = GETUP_FRONT_RAMP;
  } else if (!strcmp(downKind, "side")) {
    freq = GETUP_SIDE_FREQ; ampR = GETUP_SIDE_AMPR; ampL = GETUP_SIDE_AMPL;
    centre = GETUP_SIDE_CENTRE; phase = GETUP_SIDE_PHASE; hip = GETUP_SIDE_HIP;
    ank = GETUP_SIDE_ANK; ankph = GETUP_SIDE_ANKPH; ramp = GETUP_SIDE_RAMP;
  }
  float w = 2.0f * PI * freq * t;
  float env = t / ramp; if (env > 1.0f) env = 1.0f;
  goal[0] = env * hip * sinf(w);            // hip_R
  goal[1] = -env * hip * sinf(w);           // hip_L
  goal[2] = env * ank * sinf(w + ankph);    // ankle_R
  goal[3] = goal[2];                        // ankle_L
  goal[4] = centre + env * ampR * sinf(w);          // flipper_R
  goal[5] = centre + env * ampL * sinf(w + phase);  // flipper_L
  goal[6] = 0;
}

// ------------------------------------------------------------- host actions
static void onAction(const JsonDocument& d) {
  const char* emote = d["emote"] | "";
  const char* trick = d["trick"] | "";
  const char* move  = d["move"]  | "";
  const char* dance = d["dance"] | "";
  char key[24];
  if (dance && *dance)      { snprintf(key, sizeof key, "DA_%s", dance); play(key, true); }
  else if (emote && *emote) { snprintf(key, sizeof key, "EM_%s", emote); play(key); }
  if (trick && *trick) {
    snprintf(key, sizeof key, "TR_%s", trick);
    int i = findMotion(key);
    if (i >= 0) { if (player.idx < 0) play(key); else player.queued = i; }
  }
  if (move && *move) {
    if (!strcmp(move, "walk")) play("GAIT_walk", true);
    else if (!strcmp(move, "turn_left")) play("GAIT_turn_L", true);
    else if (!strcmp(move, "turn_right")) play("GAIT_turn_R", true);
    else if (!strcmp(move, "stop")) stopMotion();
  }
  state = ST_BUSY; stateAt = millis();
}

// EMOTE_NAMES / TRICK_NAMES come from motions.h, which is generated from
// brain/actions.py - a hand-written copy here would silently drift.

// Offline fallback. The host normally owns the conversation, but if it is gone
// the penguin answers from what it has learned rather than going silent.
static void answerFromMemory(const char* heard, uint32_t now_s) {
  float sim = 0;
  bool confident = false;
  Assoc* a = memory_.recall(heard, &sim, &confident, now_s);
  if (!a || !confident) {
    play("EM_confused");                        // heard you, do not know that one
    return;
  }
  char key[24];
  if (a->emote < N_EMOTES) {
    snprintf(key, sizeof key, "EM_%s", EMOTE_NAMES[a->emote]);
    play(key);
  }
  if (a->trick < N_TRICKS) {
    snprintf(key, sizeof key, "TR_%s", TRICK_NAMES[a->trick]);
    int i = findMotion(key);
    if (i >= 0) player.queued = i;
  }
  // beak chatter for the length of the remembered line, since there is no TTS
  // here - roughly 190 ms per syllable, approximated as 2.6 chars per syllable
  Serial.printf("[offline] %.*s\n", a->say_len, a->say);
}

static void onWsEvent(WStype_t type, uint8_t* payload, size_t len) {
  if (type != WStype_TEXT) return;
  StaticJsonDocument<512> d;
  if (deserializeJson(d, payload, len)) return;
  if (d.containsKey("beak")) {                 // live beak angle while speaking
    float a = d["beak"];
    goal[6] = constrain(a, 0.0f, 30.0f);
    return;
  }
  if (d.containsKey("learn")) {                // host teaching us a new reflex
    memory_.teach(d["learn"]["phrase"] | "", d["learn"]["say"] | "",
                  d["learn"]["emote"] | 255, d["learn"]["trick"] | 255,
                  millis() / 1000);
    return;
  }
  if (d.containsKey("heard")) {
    // The host has a transcript but could not reach the LLM. Answer from what we
    // have learned rather than standing there silently. (The robot cannot hear
    // for itself - there is no on-device speech recognition - so this path needs
    // the host to be alive even though the network is not.)
    answerFromMemory(d["heard"] | "", millis() / 1000);
    return;
  }
  if (d.containsKey("reward")) {               // how the last answer landed
    float sim; bool conf;
    Assoc* a = memory_.recall(d["reward"]["phrase"] | "", &sim, &conf, millis() / 1000);
    if (a) memory_.reinforce(a, (float)(d["reward"]["amount"] | 0.0), millis() / 1000);
    return;
  }
  if (d.containsKey("emote") || d.containsKey("move") || d.containsKey("dance"))
    onAction(d);
}

// ------------------------------------------------------------------- setup
void setup() {
  Serial.begin(115200);
  for (int j = 0; j < N_JOINTS; j++) {
    servo[j].setPeriodHertz(50);
    servo[j].attach(SERVO_PIN[j], 500, 2500);
    cmd[j] = goal[j] = REST[j];
  }
  imuInit();
  memory_.setVocab(N_EMOTES, N_TRICKS);
  if (memory_.begin())
    Serial.printf("memory: %u learned associations (%lu bytes)\n",
                  memory_.count(), (unsigned long)memory_.flashBytes());
  else
    Serial.println("memory: starting empty");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  ws.begin(HOST_IP, HOST_PORT, "/");
  ws.onEvent(onWsEvent);
  ws.setReconnectInterval(2000);
  Serial.printf("penguin up: %d motions in flash\n", N_MOTIONS);
}

// -------------------------------------------------------------------- loop
void loop() {
  static uint32_t last = 0;
  ws.loop();
  uint32_t now = millis();
  if (now - last < 10) return;                  // 100 Hz control loop
  float dt = (now - last) / 1000.0f;
  last = now;

  imuRead(dt);

  // --- state machine: falling and getting up take priority over everything
  if (upAxis > 0.9f && state != ST_RECOVER) {
    recoverTries = 0;                           // back on its feet
    if (state == ST_DOWN) {                     // somebody picked him up
      state = ST_IDLE; stateAt = now;
      sendEvent("righted"); play("EM_happy");
    }
  }
  if (state != ST_DOWN && state != ST_RECOVER && upAxis < 0.55f) {
    state = ST_FALLING; stateAt = now;
    stopMotion();
    sendEvent("falling");
  }
  if (state == ST_FALLING && now - stateAt > 900) {
    state = ST_DOWN; stateAt = now;
    downKind = fallKind();
    sendEvent(downKind[0] == 'b' ? "down_back" : downKind[0] == 'f' ? "down_front" : "down_side");
  }
  if (state == ST_DOWN && now - stateAt > 600 && recoverTries < MAX_RECOVER_TRIES) {
    state = ST_RECOVER; recoverStart = now; recoverTries++;
  }

  if (state == ST_RECOVER) {
    float t = (now - recoverStart) / 1000.0f;
    driveRecovery(t);
    if (upAxis > 0.88f) {
      state = ST_IDLE; recoverTries = 0;
      sendEvent("recovered"); play("EM_proud");
    } else if (t > 8.0f) {
      // Recovery does not work on this body - see docs/SELF_RIGHTING.md. After
      // one honest attempt it stops heaving and asks to be picked up, which is
      // the designed behaviour rather than a failure state. recoverTries gates
      // the retry so it does not thrash on the floor forever.
      state = ST_DOWN; stateAt = now; sendEvent("stuck");
      play("TR_helpme", true);
    }
  } else if (state == ST_FALLING) {
    for (int j = 0; j < N_JOINTS; j++) goal[j] = REST[j];
    goal[4] = goal[5] = 130;                   // flippers back, inside the -45..135 window
  } else {
    sampleMotion();
    // balance rides on top of whatever is playing, except while recovering
    float targetLean = LEAN_SCALE * 0.5f * (goal[2] + goal[3]);
    float c = balance(targetLean);
    goal[2] += c;
    goal[3] += c;
    if (state == ST_BUSY && player.idx < 0) state = ST_IDLE;
  }

  // --- persist what it has learned, at most once a minute so flash lasts
  static uint32_t last_save = 0;
  if (memory_.dirty() && now - last_save > 60000) {
    memory_.save();
    last_save = now;
  }

  // --- drive servos, rate limited so nothing snaps
  const float MAX_DPS = 420.0f;
  float step = MAX_DPS * dt;
  for (int j = 0; j < N_JOINTS; j++) {
    float g = constrain(goal[j], (float)LIM_LO[j], (float)LIM_HI[j]);
    float d = g - cmd[j];
    cmd[j] += constrain(d, -step, step);
    float out = DIR[j] * cmd[j] + TRIM[j] + 90.0f;
    servo[j].write(constrain(out, 0.0f, 180.0f));
  }
}
