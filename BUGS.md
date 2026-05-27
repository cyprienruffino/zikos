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

### BUG-004 — `analyze_timbre` returns physically impossible values
**Priority:** Medium
**Area:** `backend/zikos/mcp/tools/audio/`
**Symptom:** `attack_time: 0.0 ms` and `timbre_consistency: 0.19` reported for real instrument recordings. The LLM itself flagged these as suspicious.
**Suspected cause:** Algorithm bug — likely a boundary condition in onset detection or consistency calculation.

---

### BUG-005 — `detect_pitch` fails silently for low-register instruments
**Priority:** Medium
**Area:** `backend/zikos/mcp/tools/audio/`
**Symptom:** Returns `NO_PITCH_DETECTED` for bass recordings. LLM continues with partial data without flagging the gap.
**Suspected cause:** Pitch detection algorithm (likely `librosa.yin` or `pyin`) has a frequency floor that excludes bass range. Error is returned but not escalated clearly.
