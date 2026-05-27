# Bug Tracker

## Open

### BUG-001 — ~~Same audio file reused across re-recordings~~ CLOSED: not a real bug
**Resolution:** Each upload correctly generates a fresh `uuid4`. The "same file" observation was caused by BUG-002: the `AudioContextEnricher` re-injects the first recording's analysis on every subsequent turn, so the LLM kept seeing and commenting on the old data.

---

### ~~BUG-002 — Audio analysis context re-injected into every subsequent user message~~ CLOSED
**Resolution:** `AudioContextEnricher` removed entirely. Analysis is now injected exactly once (in `handle_audio_ready`); the LLM calls its own tools for any further context it needs.

---

### ~~BUG-003 — LLM not proactive with optional tool calls~~ CLOSED
**Resolution:** System prompt updated with explicit rules: "AUDIO ANALYSIS = GO DEEPER" (call key/chords/timbre/dynamics before giving feedback when useful) and "FOLLOW-UP QUESTIONS = USE TOOLS" (use `segment_audio` + re-analysis rather than guessing from history).

---

### ~~BUG-004 — `analyze_timbre` returns physically impossible values~~ CLOSED
**Resolution:**
- `attack_time=0`: `onset_frame` (librosa frames) was used as a sample index — off by 512×. Fixed to `int(onset_time * sr)`.
- `timbre_consistency=0.19`: `TIMBRE_CONSISTENCY_DIVISOR` was 500, too tight for real music. Spectral centroid std easily reaches 2000 Hz, saturating the formula. Raised to 1500.

---

### ~~BUG-005 — `detect_pitch` fails silently for low-register instruments~~ CLOSED
**Resolution:** `pyin` prefers to report sub-octaves; with `fmin=C2 (65.4 Hz)`, any note whose sub-octave fell below C2 returned `NO_PITCH_DETECTED`. Lowered to `fmin=C1 (32.7 Hz)` and `frame_length=4096`. Now detects bass notes from ~D2 (73 Hz) upward — note names are correct, octave may be off by one for the lowest register. E1/A1 remain undetectable (pyin fundamental limitation below ~50 Hz).
