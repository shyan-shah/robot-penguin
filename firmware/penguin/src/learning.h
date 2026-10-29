// On-device associative memory - the part of the penguin that learns.
//
// Mirror of brain/learning.py. The fingerprint and the matching rule must stay
// identical in both or a memory trained on the host will not match on the robot;
// test_learning.py on the host is the reference, and tools/check_parity.py
// compares the two implementations on the same strings.
//
// Storage: /learned.bin on LittleFS, written back at most once a minute so flash
// wear stays sane.
#pragma once
#include <Arduino.h>

#define PGM_BITS 1024
#define PGM_BYTES (PGM_BITS / 8)
#define PGM_MAX_ITEMS 384
#define PGM_SAY_MAX 160

// Tuned on the host against a simulated household with speech-recogniser noise
// (brain/test_learning.py). Loose means it answers more and is wrong more.
#define PGM_MATCH_THRESHOLD 0.40f
#define PGM_MERGE_THRESHOLD 0.48f
#define PGM_STRONG 2.0f          // strength needed before it answers offline
#define PGM_HALFLIFE_DAYS 21.0f

struct Assoc {
  uint8_t fp[PGM_BYTES];
  float strength;
  uint16_t hits;
  uint8_t emote;                 // index into the emote table, 255 = none
  uint8_t trick;                 // index into the trick table, 255 = none
  uint8_t say_len;
  char say[PGM_SAY_MAX];
  uint32_t last_s;               // seconds since boot epoch / RTC
};

class Memory {
 public:
  // The behaviour vocabulary this build was compiled against. Set it before
  // load(): behaviours are stored as an index into the sorted name list, so a
  // blob written against a different vocabulary must be rejected, not remapped.
  void setVocab(uint8_t n_emotes, uint8_t n_tricks) { n_em_ = n_emotes; n_tr_ = n_tricks; }

  bool begin();                                   // mount LittleFS, load
  bool load(const char* path = "/learned.bin");
  bool save(const char* path = "/learned.bin");

  // Hash a heard phrase into a sparse bit fingerprint.
  static void fingerprint(const char* text, uint8_t out[PGM_BYTES]);
  static float jaccard(const uint8_t* a, const uint8_t* b);

  // Best learned response, or nullptr. `confident` means strong enough to use
  // without asking the cloud.
  Assoc* recall(const char* heard, float* sim_out, bool* confident, uint32_t now_s);

  // Record what the cloud said so we can say it ourselves next time.
  Assoc* teach(const char* phrase, const char* say, uint8_t emote, uint8_t trick,
               uint32_t now_s);

  void reinforce(Assoc* a, float amount, uint32_t now_s);
  float decayed(const Assoc* a, uint32_t now_s) const;

  uint16_t count() const { return n_; }
  bool dirty() const { return dirty_; }
  void markClean() { dirty_ = false; }
  uint32_t flashBytes() const;

 private:
  Assoc items_[PGM_MAX_ITEMS];
  uint16_t n_ = 0;
  uint8_t n_em_ = 0, n_tr_ = 0;
  bool dirty_ = false;
  void prune(uint32_t now_s);
};

extern Memory memory_;

// How the robot decides a response landed, from the sensors it has.
// laughter   : mic energy burst in the laugh band, shortly after speaking
// touched    : IMU spike while the servos are idle - a pat
// re_asked   : a near-duplicate phrase within 10 s - it got it wrong
float reactionScore(bool laughter, bool touched, bool kept_talking,
                    bool walked_away, bool re_asked);
