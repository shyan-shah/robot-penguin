#include "learning.h"

#include <LittleFS.h>
#include <ctype.h>
#include <math.h>
#include <string.h>

Memory memory_;

// --- the same hash the host uses -------------------------------------------
// BLAKE2b is overkill for an MCU and we only need the low bits, so this is a
// 64-bit FNV-1a. brain/learning.py must use the same function - see
// tools/check_parity.py, which fails the build if the two disagree.
static uint64_t fnv1a(const char* s, size_t n) {
  uint64_t h = 0xcbf29ce484222325ULL;
  for (size_t i = 0; i < n; i++) {
    h ^= (uint8_t)s[i];
    h *= 1099511628211ULL;
  }
  return h;
}

static const char* STOP[] = {"the", "a", "an", "is", "are", "to", "of", "and",
                             "you", "i", "it", "that", "this", "do", "does",
                             "did", "can", "will", "would", "me", "my", nullptr};

static bool isStop(const char* w, size_t n) {
  for (int i = 0; STOP[i]; i++)
    if (strlen(STOP[i]) == n && !strncmp(STOP[i], w, n)) return true;
  return false;
}

static void setBits(uint8_t* out, const char* g, size_t n) {
  uint64_t v = fnv1a(g, n);
  for (int j = 0; j < 3; j++) {                 // 3 bits per gram
    uint16_t b = (uint16_t)((v >> (j * 10)) % PGM_BITS);
    out[b >> 3] |= (uint8_t)(1 << (b & 7));
  }
}

void Memory::fingerprint(const char* text, uint8_t out[PGM_BYTES]) {
  memset(out, 0, PGM_BYTES);
  char buf[128];
  size_t bn = 0;
  // lowercase, strip punctuation
  for (const char* p = text; *p && bn < sizeof(buf) - 1; p++) {
    char c = (char)tolower((unsigned char)*p);
    if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == ' ' || c == '\'')
      buf[bn++] = c;
    else if (bn && buf[bn - 1] != ' ')
      buf[bn++] = ' ';
  }
  buf[bn] = 0;

  // unigrams and bigrams, stopwords dropped
  const char* words[24];
  size_t lens[24];
  int nw = 0;
  const char* p = buf;
  while (*p && nw < 24) {
    while (*p == ' ') p++;
    const char* s = p;
    while (*p && *p != ' ') p++;
    size_t n = (size_t)(p - s);
    if (n && !isStop(s, n)) { words[nw] = s; lens[nw] = n; nw++; }
  }
  for (int i = 0; i < nw; i++) setBits(out, words[i], lens[i]);
  for (int i = 0; i + 1 < nw; i++) {            // bigram "a_b"
    char g[48];
    size_t n = lens[i] < 20 ? lens[i] : 20;
    size_t m = lens[i + 1] < 20 ? lens[i + 1] : 20;
    memcpy(g, words[i], n); g[n] = '_';
    memcpy(g + n + 1, words[i + 1], m);
    setBits(out, g, n + 1 + m);
  }
}

float Memory::jaccard(const uint8_t* a, const uint8_t* b) {
  uint32_t inter = 0, uni = 0;
  for (int i = 0; i < PGM_BYTES; i += 4) {
    uint32_t x, y;
    memcpy(&x, a + i, 4);
    memcpy(&y, b + i, 4);
    inter += __builtin_popcount(x & y);
    uni += __builtin_popcount(x | y);
  }
  return uni ? (float)inter / (float)uni : 0.0f;
}

float Memory::decayed(const Assoc* a, uint32_t now_s) const {
  float days = (float)(now_s - a->last_s) / 86400.0f;
  if (days < 0) days = 0;
  return a->strength * powf(0.5f, days / PGM_HALFLIFE_DAYS);
}

Assoc* Memory::recall(const char* heard, float* sim_out, bool* confident,
                      uint32_t now_s) {
  uint8_t fp[PGM_BYTES];
  fingerprint(heard, fp);
  Assoc* best = nullptr;
  float bs = 0.0f;
  for (uint16_t i = 0; i < n_; i++) {
    float s = jaccard(items_[i].fp, fp);
    if (s > bs) { bs = s; best = &items_[i]; }
  }
  if (sim_out) *sim_out = bs;
  if (confident) *confident = false;
  if (!best || bs < PGM_MATCH_THRESHOLD) return nullptr;
  if (confident)
    *confident = decayed(best, now_s) >= PGM_STRONG &&
                 bs >= PGM_MATCH_THRESHOLD + 0.10f;
  if (best->hits < 65535) best->hits++;
  return best;
}

Assoc* Memory::teach(const char* phrase, const char* say, uint8_t emote,
                     uint8_t trick, uint32_t now_s) {
  uint8_t fp[PGM_BYTES];
  fingerprint(phrase, fp);
  for (uint16_t i = 0; i < n_; i++) {
    if (jaccard(items_[i].fp, fp) > PGM_MERGE_THRESHOLD) {
      // same intent reworded: reinforce and refresh rather than add a duplicate
      Assoc& a = items_[i];
      a.strength = fminf(6.0f, a.strength + 0.5f);
      a.emote = emote;
      a.trick = trick;
      a.say_len = (uint8_t)strnlen(say, PGM_SAY_MAX);
      memcpy(a.say, say, a.say_len);
      a.last_s = now_s;
      dirty_ = true;
      return &a;
    }
  }
  if (n_ >= PGM_MAX_ITEMS) prune(now_s);
  Assoc& a = items_[n_++];
  memcpy(a.fp, fp, PGM_BYTES);
  a.strength = 1.0f;
  a.hits = 0;
  a.emote = emote;
  a.trick = trick;
  a.say_len = (uint8_t)strnlen(say, PGM_SAY_MAX);
  memcpy(a.say, say, a.say_len);
  a.last_s = now_s;
  dirty_ = true;
  return &a;
}

void Memory::reinforce(Assoc* a, float amount, uint32_t now_s) {
  if (!a) return;
  a->strength += amount;
  if (a->strength > 6.0f) a->strength = 6.0f;
  if (a->strength < 0.0f) a->strength = 0.0f;
  a->last_s = now_s;
  dirty_ = true;
  if (a->strength < 0.2f) {                     // it never works; forget it
    uint16_t idx = (uint16_t)(a - items_);
    if (idx < n_ - 1) items_[idx] = items_[n_ - 1];
    n_--;
  }
}

void Memory::prune(uint32_t now_s) {
  // drop the weakest 10% rather than exactly one, so this is rare
  uint16_t drop = PGM_MAX_ITEMS / 10;
  for (uint16_t d = 0; d < drop && n_; d++) {
    uint16_t worst = 0;
    float wv = 1e9f;
    for (uint16_t i = 0; i < n_; i++) {
      float v = decayed(&items_[i], now_s);
      if (v < wv) { wv = v; worst = i; }
    }
    if (worst < n_ - 1) items_[worst] = items_[n_ - 1];
    n_--;
  }
  dirty_ = true;
}

uint32_t Memory::flashBytes() const {
  uint32_t t = 8;
  for (uint16_t i = 0; i < n_; i++) t += PGM_BYTES + 4 + 2 + 1 + 1 + 1 + items_[i].say_len + 4;
  return t;
}

// ---------------------------------------------------------------- persistence
bool Memory::begin() {
  if (!LittleFS.begin(true)) return false;
  return load();
}

bool Memory::load(const char* path) {
  File f = LittleFS.open(path, "r");
  if (!f) return false;
  char magic[4];
  if (f.read((uint8_t*)magic, 4) != 4 || memcmp(magic, "PGM1", 4)) { f.close(); return false; }
  uint16_t cnt = 0, bits = 0;
  uint8_t n_em = 0, n_tr = 0;
  f.read((uint8_t*)&cnt, 2);
  f.read((uint8_t*)&bits, 2);
  f.read(&n_em, 1);
  f.read(&n_tr, 1);
  // Behaviours are stored as an index into the sorted name list, so adding one
  // behaviour shifts every index after it. Reject a blob written against a
  // different vocabulary rather than quietly playing the wrong trick.
  if (bits != PGM_BITS || n_em != n_em_ || n_tr != n_tr_) {
    f.close();
    return false;
  }
  n_ = 0;
  while (n_ < PGM_MAX_ITEMS && n_ < cnt) {
    Assoc& a = items_[n_];
    if (f.read(a.fp, PGM_BYTES) != PGM_BYTES) break;
    f.read((uint8_t*)&a.strength, 4);
    f.read((uint8_t*)&a.hits, 2);
    f.read(&a.emote, 1);
    f.read(&a.trick, 1);
    f.read(&a.say_len, 1);
    if (a.say_len > PGM_SAY_MAX) break;
    f.read((uint8_t*)a.say, a.say_len);
    f.read((uint8_t*)&a.last_s, 4);
    n_++;
  }
  f.close();
  dirty_ = false;
  return true;
}

bool Memory::save(const char* path) {
  File f = LittleFS.open(path, "w");
  if (!f) return false;
  f.write((const uint8_t*)"PGM1", 4);
  uint16_t bits = PGM_BITS;
  uint8_t n_em = n_em_, n_tr = n_tr_;
  f.write((const uint8_t*)&n_, 2);
  f.write((const uint8_t*)&bits, 2);
  f.write(&n_em, 1);
  f.write(&n_tr, 1);
  for (uint16_t i = 0; i < n_; i++) {
    Assoc& a = items_[i];
    f.write(a.fp, PGM_BYTES);
    f.write((const uint8_t*)&a.strength, 4);
    f.write((const uint8_t*)&a.hits, 2);
    f.write(&a.emote, 1);
    f.write(&a.trick, 1);
    f.write(&a.say_len, 1);
    f.write((const uint8_t*)a.say, a.say_len);
    f.write((const uint8_t*)&a.last_s, 4);
  }
  f.close();
  dirty_ = false;
  return true;
}

float reactionScore(bool laughter, bool touched, bool kept_talking,
                    bool walked_away, bool re_asked) {
  float s = 0.0f;
  if (laughter) s += 0.8f;
  if (touched) s += 0.4f;
  if (kept_talking) s += 0.3f;
  if (walked_away) s -= 0.3f;
  if (re_asked) s -= 0.6f;
  return s > 1.0f ? 1.0f : (s < -1.0f ? -1.0f : s);
}
