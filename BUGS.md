# Bug Tracker

## Open

### BUG-001 — ~~Same audio file reused across re-recordings~~ CLOSED: not a real bug
**Resolution:** Each upload correctly generates a fresh `uuid4`. The "same file" observation was caused by BUG-002: the `AudioContextEnricher` re-injects the first recording's analysis on every subsequent turn, so the LLM kept seeing and commenting on the old data.

---

### BUG-002 — Audio analysis context re-injected into every subsequent user message
**Priority:** High
**Area:** `AudioContextEnricher`
**Symptom:** API snapshots show the first recording's `[Audio Analysis Results]` block appearing at an ever-increasing message index across turns — it is re-appended as part of every user message that contains an audio keyword ("recording", "sound", etc.). The LLM keeps commenting on the first recording as if no new one arrived.
**Confirmed:** In session `aeb93f4f`, `audio_file_id 12cbcd28` appears at positions [12], [14], [16], [18], [20], [21], [23], [25], [26], [28] across successive snapshots.
**Root cause:** `enrich_message` injects analysis into the user message on every call if audio keywords are present, with no check for whether the same analysis is already in history.

---

### BUG-003 — LLM not proactive with optional tool calls
**Priority:** Medium
**Area:** System prompt / LLM behaviour
**Symptom:** `analyze_timbre`, `detect_chords`, comparison tools etc. are only called after the user explicitly asks. In a multi-recording session, `compare_audio` was never called.
**Suspected cause:** System prompt does not sufficiently motivate proactive tool use; optional tools section is likely too passive.

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
