"""Golden-recording regression suite

Analyzes real committed recordings of known material and checks the results
against sidecar .expected.json files. See README.md in this directory for
the expectation format. Skipped until recordings are added.
"""

import json
from pathlib import Path

import pytest

from zikos.mcp.tools.analysis import AudioAnalysisTools

RECORDINGS_DIR = Path(__file__).parent / "recordings"


def _collect_cases():
    cases = []
    for wav in sorted(RECORDINGS_DIR.glob("*.wav")):
        expected = wav.with_name(wav.stem + ".expected.json")
        if expected.exists():
            cases.append(pytest.param(wav, expected, id=wav.stem))
    if not cases:
        cases.append(
            pytest.param(
                None,
                None,
                id="no-recordings",
                marks=pytest.mark.skip(
                    reason="no golden recordings committed yet (see tests/golden/README.md)"
                ),
            )
        )
    return cases


@pytest.mark.asyncio
@pytest.mark.parametrize(("wav_path", "expected_path"), _collect_cases())
async def test_golden_recording(wav_path: Path, expected_path: Path):
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    tools = AudioAnalysisTools()
    instrument = expected.get("instrument")

    if "tempo_bpm" in expected:
        tempo = await tools.analyze_tempo(audio_path=str(wav_path))
        assert not tempo.get("error"), f"tempo analysis failed: {tempo}"
        tolerance = float(expected.get("tempo_tolerance", 3.0))
        assert (
            abs(tempo["bpm"] - expected["tempo_bpm"]) <= tolerance
        ), f"expected {expected['tempo_bpm']}±{tolerance} BPM, got {tempo['bpm']}"

    if "key" in expected:
        key = await tools.detect_key(audio_path=str(wav_path))
        assert not key.get("error"), f"key detection failed: {key}"
        allowed = expected["key"] if isinstance(expected["key"], list) else [expected["key"]]
        assert key["key"] in allowed, f"expected one of {allowed}, got {key['key']}"

    pitch_checks = {"lowest_note", "min_notes", "min_intonation_accuracy"}
    if pitch_checks & expected.keys():
        pitch = await tools.detect_pitch(audio_path=str(wav_path), instrument=instrument)
        assert not pitch.get("error"), f"pitch detection failed: {pitch}"
        detected = [note["pitch"] for note in pitch["notes"]]

        if "lowest_note" in expected:
            assert (
                expected["lowest_note"] in detected
            ), f"expected {expected['lowest_note']} among detected notes, got {detected}"
        if "min_notes" in expected:
            assert (
                len(detected) >= expected["min_notes"]
            ), f"expected >= {expected['min_notes']} notes, got {len(detected)}: {detected}"
        if "min_intonation_accuracy" in expected:
            assert pitch["intonation_accuracy"] >= expected["min_intonation_accuracy"], (
                f"intonation_accuracy {pitch['intonation_accuracy']} below "
                f"floor {expected['min_intonation_accuracy']}"
            )
