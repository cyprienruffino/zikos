# Bug Tracker

## Open

### BUG-001 — Same audio file reused across re-recordings
**Priority:** High
**Area:** Frontend / recording widget
**Symptom:** After re-recording, the LLM reports the same `audio_file_id` as the previous session. The user re-recorded but the system served the old file.
**Suspected cause:** Unknown — could be the recording widget not resetting state, the upload endpoint deduplicating by content, or session state leaking the old ID.

---

### BUG-002 — Duplicate audio analysis context messages injected into history
**Priority:** High
**Area:** `AudioContextEnricher` / `ConversationManager`
**Symptom:** API snapshots show multiple consecutive `[Audio Analysis Context]` user messages with identical content. LLM repeats phrases like "Oui, je vois le nouvel enregistrement !" across turns because the context is injected again and again.
**Suspected cause:** `enrich_message` likely called on every turn without checking whether the analysis is already present in history.

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
