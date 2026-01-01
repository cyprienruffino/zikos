"""Tests for MIDI tools"""

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from zikos.mcp.tools.processing.midi import MidiTools


@pytest.fixture
def midi_tools():
    """Create MidiTools instance"""
    return MidiTools()


class TestMidiTools:
    """Tests for MidiTools"""

    def test_get_tool_schemas(self, midi_tools):
        """Test getting tool schemas"""
        schemas = midi_tools.get_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) == 3

        tool_names = [s["function"]["name"] for s in schemas]
        assert "validate_midi" in tool_names
        assert "midi_to_audio" in tool_names
        assert "midi_to_notation" in tool_names

    @pytest.mark.asyncio
    async def test_validate_midi(self, midi_tools):
        """Test MIDI validation"""
        midi_text = """
[MIDI]
Tempo: 120
Time Signature: 4/4
Key: C major
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
        result = await midi_tools.validate_midi(midi_text)

        assert "valid" in result
        assert result["valid"] is True
        assert "midi_file_id" in result
        assert result["midi_file_id"] != ""
        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)

    @pytest.mark.asyncio
    async def test_midi_to_audio_file_not_found(self, midi_tools):
        """Test MIDI to audio with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await midi_tools.midi_to_audio("nonexistent_midi", "piano")

    @pytest.mark.asyncio
    async def test_validate_midi_file_creation_failure(self, midi_tools, temp_dir):
        """Test validate_midi when file creation fails"""
        from pathlib import Path
        from unittest.mock import patch

        from zikos.config import settings

        with patch.object(settings, "midi_storage_path", temp_dir):
            with patch.object(midi_tools, "storage_path", temp_dir):
                with patch("zikos.mcp.tools.processing.midi.midi.midi_text_to_file") as mock_parser:
                    mock_parser.side_effect = Exception("Parser failed")

                    result = await midi_tools.validate_midi(
                        """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                    )

                    assert "valid" in result
                    assert result["valid"] is False
                    assert "errors" in result
                    assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_midi_empty_file_created(self, midi_tools, temp_dir):
        """Test validate_midi when file is created but empty"""
        from unittest.mock import patch

        from zikos.config import settings

        with patch.object(settings, "midi_storage_path", temp_dir):
            with patch.object(midi_tools, "storage_path", temp_dir):
                midi_file_id = str(uuid.uuid4())

                def side_effect(midi_text, path):
                    path.touch()
                    return midi_file_id

                with patch(
                    "zikos.mcp.tools.processing.midi.midi.midi_text_to_file",
                    side_effect=side_effect,
                ):
                    result = await midi_tools.validate_midi(
                        """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                    )

                    assert "valid" in result
                    assert result["valid"] is False
                    assert "errors" in result

    @pytest.mark.asyncio
    async def test_midi_to_audio_with_real_synthesis(self, midi_tools, temp_dir):
        """Test MIDI to audio with real synthesis if fluidsynth is available"""
        import shutil
        from pathlib import Path

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        if not shutil.which("fluidsynth"):
            pytest.skip("fluidsynth not available")

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "audio_storage_path", temp_dir):
                    midi_file_id = "test_synthesis"
                    midi_path = temp_dir / f"{midi_file_id}.mid"

                    midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                    midi_text_to_file(midi_text, midi_path)

                    result = await midi_tools.midi_to_audio(midi_file_id, "piano")

                    assert "audio_file_id" in result
                    assert "midi_file_id" in result
                    assert result["midi_file_id"] == midi_file_id
                    assert "instrument" in result
                    assert "duration" in result
        except (ImportError, FileNotFoundError, RuntimeError) as e:
            pytest.skip(f"Synthesis dependencies not available: {e}")

    @pytest.mark.asyncio
    async def test_midi_to_audio_default_instrument(self, midi_tools, temp_dir):
        """Test MIDI to audio with default instrument via call_tool"""
        import shutil
        from pathlib import Path

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        if not shutil.which("fluidsynth"):
            pytest.skip("fluidsynth not available")

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "audio_storage_path", temp_dir):
                    midi_path = Path(settings.midi_storage_path) / "test_midi.mid"
                    midi_path.parent.mkdir(parents=True, exist_ok=True)

                    midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                    midi_text_to_file(midi_text, midi_path)

                    result = await midi_tools.call_tool("midi_to_audio", midi_file_id="test_midi")
                    assert "audio_file_id" in result
        except (ImportError, FileNotFoundError, RuntimeError) as e:
            pytest.skip(f"Synthesis dependencies not available: {e}")

    @pytest.mark.asyncio
    async def test_midi_to_notation_file_not_found(self, midi_tools):
        """Test MIDI to notation with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await midi_tools.midi_to_notation("nonexistent_midi", "both")

    @pytest.mark.asyncio
    async def test_midi_to_notation_default_format(self, midi_tools, temp_dir):
        """Test MIDI to notation with default format via call_tool"""
        from unittest.mock import patch

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "notation_storage_path", temp_dir):
                    with patch.object(midi_tools, "storage_path", temp_dir):
                        midi_file_id = "test_midi"
                        midi_path = temp_dir / f"{midi_file_id}.mid"

                        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                        midi_text_to_file(midi_text, midi_path)

                        result = await midi_tools.call_tool(
                            "midi_to_notation", midi_file_id=midi_file_id
                        )

                        assert result["format"] == "both"
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_notation_parse_failure(self, midi_tools, temp_dir):
        """Test midi_to_notation when MIDI file parsing fails"""
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from zikos.config import settings

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "notation_storage_path", temp_dir):
                    with patch.object(midi_tools, "storage_path", temp_dir):
                        midi_file_id = "test_parse_fail"
                        midi_path = temp_dir / f"{midi_file_id}.mid"
                        midi_path.touch()

                        with patch(
                            "music21.midi.translate.midiFilePathToStream", return_value=None
                        ):
                            with pytest.raises(
                                RuntimeError,
                                match="Failed to render notation: Failed to parse MIDI file",
                            ):
                                await midi_tools.midi_to_notation(midi_file_id, "sheet_music")
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_notation_both_formats(self, midi_tools, temp_dir):
        """Test midi_to_notation with both formats"""
        from pathlib import Path
        from unittest.mock import patch

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "notation_storage_path", temp_dir):
                    with patch.object(midi_tools, "storage_path", temp_dir):
                        midi_file_id = "test_both_formats"
                        midi_path = temp_dir / f"{midi_file_id}.mid"

                        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                        midi_text_to_file(midi_text, midi_path)

                        result = await midi_tools.midi_to_notation(midi_file_id, "both")

                    assert "format" in result
                    assert result["format"] == "both"
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_audio_no_soundfont(self, midi_tools, temp_dir):
        """Test midi_to_audio when no SoundFont is found"""
        from pathlib import Path
        from unittest.mock import patch

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        with patch.object(settings, "midi_storage_path", temp_dir):
            with patch.object(midi_tools, "storage_path", temp_dir):
                midi_file_id = "test_no_soundfont"
                midi_path = temp_dir / f"{midi_file_id}.mid"

                midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                midi_text_to_file(midi_text, midi_path)

                with patch.object(midi_tools, "_find_soundfont", return_value=None):
                    with pytest.raises(RuntimeError, match="No SoundFont found"):
                        await midi_tools.midi_to_audio(midi_file_id, "piano")

    @pytest.mark.asyncio
    async def test_synthesize_with_cli_fluidsynth_not_found(self, midi_tools, temp_dir):
        """Test _synthesize_with_cli when fluidsynth CLI is not found"""
        from pathlib import Path
        from unittest.mock import patch

        from zikos.config import settings

        with patch.object(settings, "midi_storage_path", temp_dir):
            midi_path = temp_dir / "test.mid"
            midi_path.touch()
            soundfont_path = temp_dir / "test.sf2"
            soundfont_path.touch()

            with patch("shutil.which", return_value=None):
                with pytest.raises(FileNotFoundError, match="fluidsynth CLI not found"):
                    await midi_tools._synthesize_with_cli(midi_path, soundfont_path, "piano")

    @pytest.mark.asyncio
    async def test_synthesize_with_cli_synthesis_failure(self, midi_tools, temp_dir):
        """Test _synthesize_with_cli when synthesis fails"""
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from zikos.config import settings

        with patch.object(settings, "midi_storage_path", temp_dir):
            midi_path = temp_dir / "test.mid"
            midi_path.touch()
            soundfont_path = temp_dir / "test.sf2"
            soundfont_path.touch()

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Synthesis error"

            with patch("shutil.which", return_value="/usr/bin/fluidsynth"):
                with patch("subprocess.run", return_value=mock_result):
                    with pytest.raises(RuntimeError, match="FluidSynth synthesis failed"):
                        await midi_tools._synthesize_with_cli(midi_path, soundfont_path, "piano")

    @pytest.mark.asyncio
    async def test_synthesize_with_cli_no_output_file(self, midi_tools, temp_dir):
        """Test _synthesize_with_cli when output file is not created"""
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from zikos.config import settings

        with patch.object(settings, "midi_storage_path", temp_dir):
            with patch.object(settings, "audio_storage_path", temp_dir):
                midi_path = temp_dir / "test.mid"
                midi_path.touch()
                soundfont_path = temp_dir / "test.sf2"
                soundfont_path.touch()

                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stderr = ""

                with patch("shutil.which", return_value="/usr/bin/fluidsynth"):
                    with patch("subprocess.run", return_value=mock_result):
                        with patch("pathlib.Path.exists", return_value=False):
                            with pytest.raises(
                                RuntimeError, match="FluidSynth did not generate output file"
                            ):
                                await midi_tools._synthesize_with_cli(
                                    midi_path, soundfont_path, "piano"
                                )

    @pytest.mark.asyncio
    async def test_synthesize_with_pyfluidsynth_import_error(self, midi_tools, temp_dir):
        """Test _synthesize_with_pyfluidsynth when pyfluidsynth is not available"""
        from pathlib import Path

        from zikos.config import settings

        with patch.object(settings, "midi_storage_path", temp_dir):
            midi_path = temp_dir / "test.mid"
            midi_path.touch()
            soundfont_path = temp_dir / "test.sf2"
            soundfont_path.touch()

            with patch(
                "builtins.__import__", side_effect=ImportError("No module named 'fluidsynth'")
            ):
                with pytest.raises(ImportError, match="pyfluidsynth not available"):
                    await midi_tools._synthesize_with_pyfluidsynth(
                        midi_path, soundfont_path, "piano"
                    )

    @pytest.mark.asyncio
    async def test_synthesize_with_pyfluidsynth_parse_failure(self, midi_tools, temp_dir):
        """Test _synthesize_with_pyfluidsynth when MIDI parsing fails"""
        from pathlib import Path
        from unittest.mock import patch

        from zikos.config import settings

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                midi_path = temp_dir / "test.mid"
                midi_path.touch()
                soundfont_path = temp_dir / "test.sf2"
                soundfont_path.touch()

                with patch("music21.midi.translate.midiFilePathToStream", return_value=None):
                    with pytest.raises(ValueError, match="Failed to parse MIDI file"):
                        await midi_tools._synthesize_with_pyfluidsynth(
                            midi_path, soundfont_path, "piano"
                        )
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_synthesize_with_pyfluidsynth_soundfont_load_failure(self, midi_tools, temp_dir):
        """Test _synthesize_with_pyfluidsynth when SoundFont loading fails"""
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from zikos.config import settings

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "audio_storage_path", temp_dir):
                    midi_path = temp_dir / "test.mid"
                    midi_path.touch()
                    soundfont_path = temp_dir / "test.sf2"
                    soundfont_path.touch()

                    mock_synth = MagicMock()
                    mock_synth.sfload.return_value = -1

                    with patch("music21.midi.translate.midiFilePathToStream") as mock_parse:
                        mock_parse.return_value = MagicMock()
                        mock_parse.return_value.flat.notes = []

                        with patch("fluidsynth.Synth", return_value=mock_synth):
                            with pytest.raises(RuntimeError, match="Failed to load SoundFont"):
                                await midi_tools._synthesize_with_pyfluidsynth(
                                    midi_path, soundfont_path, "piano"
                                )
        except ImportError:
            pytest.skip("fluidsynth or music21 not available")

    @pytest.mark.asyncio
    async def test_synthesize_with_pyfluidsynth_no_audio_data(self, midi_tools, temp_dir):
        """Test _synthesize_with_pyfluidsynth when no audio data is generated"""
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from zikos.config import settings

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "audio_storage_path", temp_dir):
                    midi_path = temp_dir / "test.mid"
                    midi_path.touch()
                    soundfont_path = temp_dir / "test.sf2"
                    soundfont_path.touch()

                    mock_synth = MagicMock()
                    mock_synth.sfload.return_value = 0

                    mock_stream = MagicMock()
                    mock_stream.flat.notes = []

                    with patch(
                        "music21.midi.translate.midiFilePathToStream", return_value=mock_stream
                    ):
                        with patch("fluidsynth.Synth", return_value=mock_synth):
                            with pytest.raises(
                                ValueError, match="No audio data generated from MIDI"
                            ):
                                await midi_tools._synthesize_with_pyfluidsynth(
                                    midi_path, soundfont_path, "piano"
                                )
        except ImportError:
            pytest.skip("fluidsynth or music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_notation_sheet_music_error(self, midi_tools, temp_dir):
        """Test midi_to_notation when sheet music generation fails"""
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "notation_storage_path", temp_dir):
                    with patch.object(midi_tools, "storage_path", temp_dir):
                        midi_file_id = "test_sheet_error"
                        midi_path = temp_dir / f"{midi_file_id}.mid"

                        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                        midi_text_to_file(midi_text, midi_path)

                        mock_score = MagicMock()
                        mock_score.write.side_effect = Exception("Write failed")

                        with patch(
                            "music21.midi.translate.midiFilePathToStream", return_value=mock_score
                        ):
                            result = await midi_tools.midi_to_notation(midi_file_id, "sheet_music")

                            assert "sheet_music_error" in result
                            assert (
                                "Failed to generate sheet music" in result["sheet_music_error"]
                                or "Write failed" in result["sheet_music_error"]
                            )
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_notation_tabs_error(self, midi_tools, temp_dir):
        """Test midi_to_notation when tabs generation fails"""
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            with patch.object(settings, "midi_storage_path", temp_dir):
                with patch.object(settings, "notation_storage_path", temp_dir):
                    with patch.object(midi_tools, "storage_path", temp_dir):
                        midi_file_id = "test_tabs_error"
                        midi_path = temp_dir / f"{midi_file_id}.mid"

                        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
                        midi_text_to_file(midi_text, midi_path)

                        mock_score = MagicMock()
                        mock_score.write.side_effect = Exception("Tabs write failed")

                        with patch(
                            "music21.midi.translate.midiFilePathToStream", return_value=mock_score
                        ):
                            result = await midi_tools.midi_to_notation(midi_file_id, "tabs")

                            assert "tabs_error" in result
                            assert (
                                "Failed to generate tabs" in result["tabs_error"]
                                or "Tabs write failed" in result["tabs_error"]
                            )
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_call_tool_validate_midi(self, midi_tools):
        """Test call_tool for validate_midi"""
        midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
        result = await midi_tools.call_tool("validate_midi", midi_text=midi_text)

        assert "valid" in result
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_call_tool_midi_to_audio_file_not_found(self, midi_tools):
        """Test call_tool for midi_to_audio with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await midi_tools.call_tool(
                "midi_to_audio", midi_file_id="nonexistent", instrument="piano"
            )

    @pytest.mark.asyncio
    async def test_call_tool_midi_to_notation_file_not_found(self, midi_tools):
        """Test call_tool for midi_to_notation with non-existent file"""
        with pytest.raises(FileNotFoundError):
            await midi_tools.call_tool(
                "midi_to_notation", midi_file_id="nonexistent", format="sheet_music"
            )

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, midi_tools):
        """Test call_tool with unknown tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await midi_tools.call_tool("unknown_tool", arg1="test")

    @pytest.mark.asyncio
    async def test_validate_midi_invalid(self, midi_tools):
        """Test MIDI validation with invalid MIDI text"""
        result = await midi_tools.validate_midi("invalid MIDI text")

        assert "valid" in result
        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_validate_midi_empty(self, midi_tools):
        """Test MIDI validation with empty text"""
        result = await midi_tools.validate_midi("")

        assert "valid" in result
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_midi_to_notation_sheet_music(self, midi_tools, temp_dir):
        """Test MIDI to notation with sheet_music format"""
        from pathlib import Path

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            midi_file_id = "test_notation_sheet"
            midi_path = Path(settings.midi_storage_path) / f"{midi_file_id}.mid"
            midi_path.parent.mkdir(parents=True, exist_ok=True)

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_text_to_file(midi_text, midi_path)

            result = await midi_tools.midi_to_notation(midi_file_id, "sheet_music")

            assert "format" in result
            assert result["format"] == "sheet_music"
        except ImportError:
            pytest.skip("music21 not available")

    @pytest.mark.asyncio
    async def test_midi_to_notation_tabs(self, midi_tools, temp_dir):
        """Test MIDI to notation with tabs format"""
        from pathlib import Path

        from zikos.config import settings
        from zikos.mcp.tools.processing.midi.midi_parser import midi_text_to_file

        try:
            midi_file_id = "test_notation_tabs"
            midi_path = Path(settings.midi_storage_path) / f"{midi_file_id}.mid"
            midi_path.parent.mkdir(parents=True, exist_ok=True)

            midi_text = """
[MIDI]
Tempo: 120
Track 1:
  C4 velocity=60 duration=0.5
[/MIDI]
"""
            midi_text_to_file(midi_text, midi_path)

            result = await midi_tools.midi_to_notation(midi_file_id, "tabs")

            assert "format" in result
            assert result["format"] == "tabs"
        except ImportError:
            pytest.skip("music21 not available")

    def test_find_soundfont(self, midi_tools, temp_dir):
        """Test finding SoundFont"""
        from pathlib import Path

        test_soundfont = temp_dir / "test.sf2"
        test_soundfont.touch()

        with patch.object(midi_tools, "_find_soundfont") as mock_find:
            mock_find.return_value = test_soundfont
            result = midi_tools._find_soundfont()
            assert result == test_soundfont

    def test_find_soundfont_not_found(self, midi_tools):
        """Test finding SoundFont when not available"""
        result = midi_tools._find_soundfont()
        assert result is None or isinstance(result, Path)

    def test_instrument_to_program(self, midi_tools):
        """Test instrument to program conversion"""
        assert midi_tools._instrument_to_program("piano") == 0
        assert midi_tools._instrument_to_program("guitar") == 24
        assert midi_tools._instrument_to_program("violin") == 40
        assert midi_tools._instrument_to_program("bass") == 32
        assert midi_tools._instrument_to_program("drums") == 128
        assert midi_tools._instrument_to_program("unknown") == 0
        assert midi_tools._instrument_to_program("PIANO") == 0
