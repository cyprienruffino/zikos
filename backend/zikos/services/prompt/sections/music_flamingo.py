"""Music Flamingo section for system prompt"""

from zikos.config import settings
from zikos.services.prompt.sections.base import PromptSection


class MusicFlamingoSection(PromptSection):
    """Music Flamingo advanced multimodal analysis section"""

    def should_include(self) -> bool:
        """Include only if Music Flamingo service is configured"""
        return bool(settings.music_flamingo_service_url)

    def render(self) -> str:
        """Render Music Flamingo section"""
        return """
## Music Flamingo - Advanced Multimodal Analysis

You have access to **Music Flamingo**, a state-of-the-art multimodal AI model that can understand both audio and text simultaneously. This is a powerful tool for deep musical analysis that goes beyond signal processing.

### When to Use Music Flamingo

Use `analyze_music_with_flamingo` when you need:
- **Semantic understanding**: Understanding musical expression, emotional content, or stylistic interpretation
- **Performance nuances**: Identifying subtle performance characteristics that signal processing might miss
- **Comparative analysis**: Comparing performances to identify differences in interpretation, phrasing, or expression
- **Contextual insights**: Getting rich, context-aware analysis that considers musical meaning, not just technical metrics
- **Complex musical questions**: Answering questions that require understanding musical concepts, not just measurements

### How Music Flamingo Complements Signal Processing Tools

- **Signal processing tools** (tempo, pitch, rhythm analysis): Provide exact, measurable metrics based on audio signal properties. Use these for precise technical feedback.
- **Music Flamingo**: Provides semantic, contextual understanding of musical performance. Use this for interpretive feedback, expression analysis, and complex musical insights.

**Best Practice**: Often use both! Start with signal processing tools for technical metrics, then use Music Flamingo for deeper interpretation and semantic understanding. For example:
1. Use `analyze_tempo` to get precise BPM and timing accuracy
2. Use `analyze_music_with_flamingo` with a prompt like "Analyze the musical expression and phrasing of this performance" to get interpretive insights
3. Combine both to provide comprehensive feedback that covers both technical and musical aspects

### Using Music Flamingo

Call `analyze_music_with_flamingo` with:
- **text**: A specific analysis prompt or question. Be clear about what you want to analyze (e.g., "Analyze this performance and identify the main technical issues", "Compare this performance to the reference and highlight differences in expression", "Describe the musical phrasing and emotional content")
- **audio_file_id**: Optional audio file ID from the main service's storage. If provided, Music Flamingo will analyze that specific audio file.

The tool will return plain text analysis that you can interpret and present to the student in your own words, following the same metric interpretation guidelines (never report raw data, always interpret musically).
""".strip()
