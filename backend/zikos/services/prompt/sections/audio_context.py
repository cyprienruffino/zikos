"""Audio analysis context sections for dynamic message injection"""

from zikos.services.prompt.sections.base import PromptSection


class AudioAnalysisReminderSection(PromptSection):
    """Reminder to interpret metrics, not report them (short version)"""

    def render(self) -> str:
        """Render short interpretation reminder"""
        return """CRITICAL: When referencing audio analysis data, NEVER report raw metrics or scores. Always interpret them musically. For example, say "your timing is inconsistent" not "timing_accuracy is 0.44". Use the metrics internally to understand the performance, then explain in musical terms."""


class AudioAnalysisFeedbackReminderSection(PromptSection):
    """Detailed reminder for feedback generation (long version)"""

    def render(self) -> str:
        """Render detailed feedback reminder"""
        return """CRITICAL INSTRUCTIONS FOR PROVIDING FEEDBACK:

- NEVER report raw metrics or scores (e.g., "timing_accuracy: 0.44", "BPM: 86.54", "average_deviation: 52.74 ms")
- NEVER structure feedback as "Tempo Analysis:", "Pitch Analysis:", "Rhythm Analysis:" sections listing metrics
- ALWAYS interpret metrics musically (e.g., "Your timing is inconsistent - you're rushing the beat" instead of "timing accuracy is 0.44")
- Use scores internally to understand what's happening, then explain in musical terms
- Be concise and actionable - get to the point quickly with specific advice

The analysis data below contains scores and metrics FOR YOUR INTERNAL USE ONLY. Use them to understand the performance, then provide musical feedback without mentioning the raw numbers."""


class AudioAnalysisContextFormatter:
    """Helper to format audio analysis context messages"""

    NO_ANALYSIS_AVAILABLE_MESSAGE = (
        "[IMPORTANT: The user is asking about audio analysis, but no audio analysis data is "
        "available in the conversation history. Please inform them that you don't see any audio "
        "analysis available and suggest they record or upload audio first.]"
    )

    @staticmethod
    def format_analysis_context(analysis_data: str, user_question: str | None = None) -> str:
        """Format audio analysis context for user message

        Args:
            analysis_data: The audio analysis data (JSON string or formatted text)
            user_question: Optional user question to append

        Returns:
            Formatted message with analysis context and reminders
        """
        reminder = AudioAnalysisReminderSection().render()

        parts = [
            "[Audio Analysis Context - Use this data to answer the user's question]",
            analysis_data,
            reminder,
        ]

        if user_question:
            parts.extend(
                [
                    "[User Question]",
                    user_question,
                    "IMPORTANT: Answer based ONLY on the audio analysis data provided above. Do not make up or hallucinate information. If the analysis data doesn't contain the information needed, say so explicitly.",
                ]
            )

        return "\n\n".join(parts)

    @staticmethod
    def format_analysis_results(audio_file_id: str, analysis_data: str) -> str:
        """Format audio analysis results for feedback generation

        Args:
            audio_file_id: The audio file identifier
            analysis_data: The audio analysis data (JSON string or formatted text)

        Returns:
            Formatted message with analysis results and feedback reminder
        """
        reminder = AudioAnalysisFeedbackReminderSection().render()

        return f"""[Audio Analysis Results]
Audio File: {audio_file_id}

{analysis_data}

{reminder}

Please provide feedback on this musical performance based on the analysis above."""

    @staticmethod
    def format_no_analysis_available(user_message: str) -> str:
        """Format message when user asks about audio but no analysis is available

        Args:
            user_message: The original user message

        Returns:
            User message with no-analysis-available instruction appended
        """
        return f"{user_message}\n\n{AudioAnalysisContextFormatter.NO_ANALYSIS_AVAILABLE_MESSAGE}"
