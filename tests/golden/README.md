# Golden-recording regression suite

Real recordings of known material, with committed expected analysis results.
These catch DSP regressions that synthetic sine/harmonic fixtures can't —
real instruments have noise, weak fundamentals, room tone, and human timing.

## Adding a recording

1. Record known material (examples worth having for bass):
   - a scale at 80 BPM played to a click
   - a chromatic run covering the low register (include the low B if 5-string)
   - a deliberately rushed passage
2. Drop the WAV in `tests/golden/recordings/`, e.g. `bass_c_major_80bpm.wav`.
3. Add a sidecar `bass_c_major_80bpm.expected.json` next to it.

## Expectation format

All fields are optional — only the checks you specify run:

```json
{
  "instrument": "bass",
  "tempo_bpm": 80,
  "tempo_tolerance": 3,
  "key": ["C major", "A minor"],
  "lowest_note": "C2",
  "min_notes": 8,
  "min_intonation_accuracy": 0.8
}
```

- `instrument` — passed to detect_pitch (selects the DSP profile)
- `tempo_bpm` / `tempo_tolerance` — detected BPM must be within ±tolerance
  (default 3)
- `key` — detected key must be one of these (list relative-minor/major
  ambiguities explicitly)
- `lowest_note` — this pitch (e.g. "B0") must appear among detected notes
- `min_notes` — at least this many note onsets detected
- `min_intonation_accuracy` — floor for the intonation score

The suite skips itself while `recordings/` is empty, so CI stays green until
recordings are committed.
