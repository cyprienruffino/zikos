"""Tests for AudioContextEnricher"""

from typing import Any

import pytest

from zikos.services.llm_orchestration.audio_context_enricher import AudioContextEnricher


class TestAudioContextEnricher:
    """Tests for AudioContextEnricher"""

    @pytest.fixture
    def enricher(self):
        """Create AudioContextEnricher instance"""
        return AudioContextEnricher()

    def test_enrich_message_no_audio_keywords(self, enricher):
        """Test enriching message without audio keywords"""
        message = "What is the weather today?"
        history: list[dict[str, Any]] = []

        enriched, was_enriched = enricher.enrich_message(message, history)

        assert enriched == message
        assert was_enriched is False

    def test_enrich_message_with_audio_keyword_no_analysis(self, enricher):
        """Test enriching message with audio keyword but no analysis in history"""
        message = "Tell me about this audio sample"
        history: list[dict[str, Any]] = []

        enriched, was_enriched = enricher.enrich_message(message, history)

        assert enriched != message
        assert was_enriched is True
        assert "no audio analysis" in enriched.lower() or "not available" in enriched.lower()

    def test_enrich_message_with_audio_keyword_and_analysis(self, enricher):
        """Test enriching message with audio keyword and analysis in history"""
        message = "Tell me about this audio sample"
        history = [
            {
                "role": "user",
                "content": "[Audio Analysis Results]\nAudio File: test.wav\nTempo: 120 BPM",
            }
        ]

        enriched, was_enriched = enricher.enrich_message(message, history)

        assert enriched != message
        assert was_enriched is True
        assert "120" in enriched or "tempo" in enriched.lower()

    def test_enrich_message_already_has_analysis_marker(self, enricher):
        """Test enriching message that already has analysis marker"""
        message = "[Audio Analysis Results]\nTempo: 120"
        history: list[dict[str, Any]] = []

        enriched, was_enriched = enricher.enrich_message(message, history)

        assert enriched == message
        assert was_enriched is False

    def test_find_recent_audio_analysis_with_context_marker(self, enricher):
        """Test finding audio analysis with [Audio Analysis Context] marker"""
        history = [
            {
                "role": "user",
                "content": '[Audio Analysis Results]\n[Audio Analysis Context]{"tempo": 120}[User Question]Tell me about this',
            }
        ]

        analysis = enricher.find_recent_audio_analysis(history)

        assert analysis is not None
        assert "120" in analysis or '"tempo"' in analysis

    def test_find_recent_audio_analysis_without_context_marker(self, enricher):
        """Test finding audio analysis without [Audio Analysis Context] marker"""
        history = [
            {
                "role": "user",
                "content": '[Audio Analysis Results]\nAudio File: test.wav\n{"tempo": 120, "pitch": {"notes": ["A4"]}}',
            }
        ]

        analysis = enricher.find_recent_audio_analysis(history)

        assert analysis is not None
        assert "tempo" in analysis.lower() or "120" in analysis

    def test_find_recent_audio_analysis_no_analysis(self, enricher):
        """Test finding audio analysis when none exists"""
        history = [{"role": "user", "content": "Regular message"}]

        analysis = enricher.find_recent_audio_analysis(history)

        assert analysis is None

    def test_find_recent_audio_analysis_empty_history(self, enricher):
        """Test finding audio analysis with empty history"""
        history: list[dict[str, Any]] = []

        analysis = enricher.find_recent_audio_analysis(history)

        assert analysis is None
