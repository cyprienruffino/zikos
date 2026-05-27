"""Audio analysis context sections for dynamic message injection"""

from zikos.services.prompt.sections.base import PromptSection


class AudioAnalysisFeedbackReminderSection(PromptSection):
    """Detailed reminder for feedback generation"""

    def render(self) -> str:
        return """CRITICAL INSTRUCTIONS FOR PROVIDING FEEDBACK:

- NEVER report raw metrics or scores (e.g., "timing_accuracy: 0.44", "BPM: 86.54", "average_deviation: 52.74 ms")
- NEVER structure feedback as "Tempo Analysis:", "Pitch Analysis:", "Rhythm Analysis:" sections listing metrics
- ALWAYS interpret metrics musically (e.g., "Your timing is inconsistent - you're rushing the beat" instead of "timing accuracy is 0.44")
- Use scores internally to understand what's happening, then explain in musical terms
- Be concise and actionable - get to the point quickly with specific advice

The analysis data below contains scores and metrics FOR YOUR INTERNAL USE ONLY. Use them to understand the performance, then provide musical feedback without mentioning the raw numbers."""


class AudioAnalysisContextFormatter:
    """Helper to format audio analysis results injected on recording upload"""

    @staticmethod
    def format_analysis_results(audio_file_id: str, analysis_data: str) -> str:
        reminder = AudioAnalysisFeedbackReminderSection().render()
        return f"""[Audio Analysis Results]
Audio File: {audio_file_id}

{analysis_data}

{reminder}

Please provide feedback on this musical performance based on the analysis above."""
