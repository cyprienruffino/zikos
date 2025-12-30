"""Enrich messages with audio analysis context"""

from typing import Any

from zikos.services.prompt.sections import AudioAnalysisContextFormatter


class AudioContextEnricher:
    """Enriches user messages with audio analysis context when relevant"""

    AUDIO_KEYWORDS = ["sample", "audio", "recording", "sound", "playback", "performance"]

    def enrich_message(self, message: str, history: list[dict[str, Any]]) -> tuple[str, bool]:
        """Enrich message with audio analysis context if relevant

        Args:
            message: Original user message
            history: Conversation history

        Returns:
            tuple: (enriched_message, was_enriched)
        """
        message_lower = message.lower()
        has_analysis_marker = (
            "[audio analysis results]" in message_lower or "audio analysis results" in message_lower
        )

        if has_analysis_marker:
            return message, False

        is_asking_about_audio = any(keyword in message_lower for keyword in self.AUDIO_KEYWORDS)

        if not is_asking_about_audio:
            return message, False

        recent_audio_analysis = self.find_recent_audio_analysis(history)
        if recent_audio_analysis:
            enriched = AudioAnalysisContextFormatter.format_analysis_context(
                recent_audio_analysis, message
            )
            return enriched, True
        else:
            enriched = AudioAnalysisContextFormatter.format_no_analysis_available(message)
            return enriched, True

    def find_recent_audio_analysis(self, history: list[dict[str, Any]]) -> str | None:
        """Find the most recent audio analysis in conversation history

        Args:
            history: Conversation history

        Returns:
            Audio analysis content if found, None otherwise
        """
        for msg in reversed(history):
            content = str(msg.get("content", ""))

            content_lower = content.lower()
            has_analysis_markers = any(
                keyword in content_lower
                for keyword in [
                    "[audio analysis",
                    "audio analysis",
                    "analysis complete",
                    "tempo",
                    "pitch",
                    "rhythm",
                    "bpm",
                    "intonation",
                    "timing accuracy",
                    "audio_file_id",
                ]
            )

            has_structured_data = (
                "{" in content or "[" in content or '"tempo"' in content or '"pitch"' in content
            )

            if has_analysis_markers and has_structured_data:
                if "[Audio Analysis Context]" in content:
                    parts = content.split("[Audio Analysis Context]")
                    if len(parts) > 1:
                        analysis_part = parts[1].split("[User Question]")[0].strip()
                        return analysis_part
                return content
        return None
