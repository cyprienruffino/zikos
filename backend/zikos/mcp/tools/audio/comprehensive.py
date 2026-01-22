"""Comprehensive analysis module"""

from typing import Any

from zikos.mcp.tool import Tool, ToolCategory
from zikos.mcp.tools.audio import (
    articulation,
    chords,
    dynamics,
    key,
    phrase_segmentation,
    pitch,
    rhythm,
    tempo,
    timbre,
)
from zikos.mcp.tools.audio.utils import resolve_audio_path


def get_comprehensive_analysis_tool() -> Tool:
    """Get the comprehensive_analysis tool definition"""
    return Tool(
        name="comprehensive_analysis",
        description="Run all analyses and provide structured summary with strengths, weaknesses, and recommendations",
        category=ToolCategory.AUDIO_ANALYSIS,
        parameters={
            "audio_file_id": {"type": "string"},
        },
        required=["audio_file_id"],
        detailed_description="""Run all analyses and provide structured summary with strengths, weaknesses, and recommendations.

Returns: dict with timing (tempo, rhythm), pitch (intonation, stability), dynamics, frequency (timbre), musical_structure (key, chords, phrases), articulation, overall_score (0.0-1.0), strengths (list), weaknesses (list), recommendations (list)

Interpretation Guidelines:
- overall_score: >0.85 excellent, 0.75-0.85 good, 0.65-0.75 needs work, <0.65 poor
- Use this tool for initial assessment or when you need a complete picture of performance
- strengths: Areas where the student excels - acknowledge and build on these
- weaknesses: Areas needing improvement - prioritize these in feedback
- recommendations: Actionable suggestions based on the analysis
- The tool combines results from tempo, pitch, rhythm, dynamics, articulation, timbre, key, chords, and phrase segmentation
- When overall_score is low, check which specific areas (timing, pitch, dynamics) are contributing most
- Use strengths to encourage the student and weaknesses to guide practice focus""",
    )


async def comprehensive_analysis(audio_path: str) -> dict[str, Any]:
    """Run all analyses and provide structured summary"""
    try:
        if audio_path.endswith(".wav") or "/" in audio_path or "\\" in audio_path:
            resolved_path = audio_path
        else:
            resolved_path = str(resolve_audio_path(audio_path))

        tempo_result = await tempo.analyze_tempo(resolved_path)
        pitch_result = await pitch.detect_pitch(resolved_path)
        rhythm_result = await rhythm.analyze_rhythm(resolved_path)
        dynamics_result = await dynamics.analyze_dynamics(resolved_path)
        articulation_result = await articulation.analyze_articulation(resolved_path)
        timbre_result = await timbre.analyze_timbre(resolved_path)
        key_result = await key.detect_key(resolved_path)
        chords_result = await chords.detect_chords(resolved_path)
        phrases_result = await phrase_segmentation.segment_phrases(resolved_path)

        if "error" in tempo_result and tempo_result.get("error_type") == "TOO_SHORT":
            return dict(tempo_result)
        if "error" in pitch_result and pitch_result.get("error_type") == "TOO_SHORT":
            return dict(pitch_result)
        if "error" in rhythm_result and rhythm_result.get("error_type") == "TOO_SHORT":
            return dict(rhythm_result)

        scores = []
        strengths = []
        weaknesses = []

        if "tempo_stability_score" in tempo_result:
            scores.append(tempo_result["tempo_stability_score"])
            if tempo_result["tempo_stability_score"] >= 0.85:
                strengths.append("tempo_stability")
            elif tempo_result["tempo_stability_score"] < 0.70:
                weaknesses.append("tempo_stability")

        if "error" not in pitch_result:
            if "intonation_accuracy" in pitch_result:
                scores.append(pitch_result["intonation_accuracy"])
                if pitch_result["intonation_accuracy"] >= 0.85:
                    strengths.append("intonation")
                elif pitch_result["intonation_accuracy"] < 0.70:
                    weaknesses.append("intonation")

            if "pitch_stability" in pitch_result:
                scores.append(pitch_result["pitch_stability"])
                if pitch_result["pitch_stability"] >= 0.85:
                    strengths.append("pitch_stability")
                elif pitch_result["pitch_stability"] < 0.70:
                    weaknesses.append("pitch_stability")

        if "timing_accuracy" in rhythm_result:
            scores.append(rhythm_result["timing_accuracy"])
            if rhythm_result["timing_accuracy"] >= 0.85:
                strengths.append("timing")
            elif rhythm_result["timing_accuracy"] < 0.70:
                weaknesses.append("timing")

        if "dynamic_consistency" in dynamics_result and "error" not in dynamics_result:
            scores.append(dynamics_result["dynamic_consistency"])
            if dynamics_result["dynamic_consistency"] >= 0.80:
                strengths.append("dynamics")
            elif dynamics_result["dynamic_consistency"] < 0.65:
                weaknesses.append("dynamic_consistency")

        if "articulation_consistency" in articulation_result and "error" not in articulation_result:
            scores.append(articulation_result["articulation_consistency"])
            if articulation_result["articulation_consistency"] >= 0.80:
                strengths.append("articulation")
            elif articulation_result["articulation_consistency"] < 0.65:
                weaknesses.append("articulation_consistency")

        if "timbre_consistency" in timbre_result and "error" not in timbre_result:
            scores.append(timbre_result["timbre_consistency"])
            if timbre_result["timbre_consistency"] >= 0.80:
                strengths.append("timbre")
            elif timbre_result["timbre_consistency"] < 0.65:
                weaknesses.append("timbre_consistency")

        overall_score = float(sum(scores) / len(scores)) if scores else 0.0

        recommendations = []
        if "rushing_detected" in tempo_result and tempo_result.get("rushing_detected"):
            recommendations.append("Practice with metronome to improve tempo consistency")
        if "dragging_detected" in tempo_result and tempo_result.get("dragging_detected"):
            recommendations.append("Focus on maintaining steady tempo")
        if "intonation_accuracy" in pitch_result and pitch_result["intonation_accuracy"] < 0.75:
            recommendations.append("Work on intonation accuracy - consider using a tuner")
        if "timing_accuracy" in rhythm_result and rhythm_result["timing_accuracy"] < 0.75:
            recommendations.append("Practice rhythm and timing exercises")

        return {
            "timing": {
                "tempo": tempo_result,
                "rhythm": rhythm_result,
            },
            "pitch": pitch_result,
            "dynamics": dynamics_result if "error" not in dynamics_result else {},
            "frequency": {
                "timbre": timbre_result if "error" not in timbre_result else {},
            },
            "musical_structure": {
                "key": key_result if "error" not in key_result else {},
                "chords": chords_result if "error" not in chords_result else {},
                "phrases": phrases_result if "error" not in phrases_result else {},
            },
            "articulation": articulation_result if "error" not in articulation_result else {},
            "overall_score": overall_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
        }
    except FileNotFoundError as e:
        return {
            "error": True,
            "error_type": "FILE_NOT_FOUND",
            "message": str(e),
        }
    except Exception as e:
        return {
            "error": True,
            "error_type": "PROCESSING_FAILED",
            "message": f"Failed to run comprehensive analysis: {str(e)}",
        }
