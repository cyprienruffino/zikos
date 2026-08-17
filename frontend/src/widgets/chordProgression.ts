import { ChordProgressionState } from "../types.js";
import { escapeHtml, sanitizeToolId } from "../utils/sanitize.js";
import { clampBpm, positiveNumber, validateTimeSignature } from "../utils/validate.js";
import { createBeatScheduler } from "./audioEngine.js";
import { getMessagesEl } from "../dom.js";

const chordProgressions = new Map<string, ChordProgressionState>();

export function addChordProgressionWidget(
    progressionId: string,
    chords: string[],
    tempo: number,
    timeSignature: string,
    chordsPerBar: number,
    _instrument: string,
    description?: string
): void {
    progressionId = sanitizeToolId(progressionId, "chord");
    tempo = clampBpm(tempo);
    timeSignature = validateTimeSignature(timeSignature);
    chordsPerBar = positiveNumber(chordsPerBar, 1);
    const widgetEl = document.createElement("div");
    widgetEl.className = "chord-progression-widget";
    widgetEl.id = `chord-${progressionId}`;
    widgetEl.innerHTML = `
        <h3>Chord Progression</h3>
        ${description ? `<div class="description">${escapeHtml(description)}</div>` : ""}
        <div class="chord-progression-display" id="chords-${progressionId}">
            ${chords.map((chord, i) => `<div class="chord-box" data-chord-index="${i}">${escapeHtml(chord)}</div>`).join("")}
        </div>
        <div style="margin: 0.5rem 0; color: #2e7d32;">
            <span>Tempo: <strong>${escapeHtml(tempo)} BPM</strong></span>
            <span style="margin-left: 1rem;">Time: <strong>${escapeHtml(timeSignature)}</strong></span>
        </div>
        <div class="chord-progression-controls">
            <button class="play-btn" data-progression-id="${progressionId}">Play</button>
            <button class="pause-btn" data-progression-id="${progressionId}" style="display:none;">Pause</button>
            <button class="stop-btn" data-progression-id="${progressionId}">Stop</button>
            <span class="chord-progression-status" id="status-${progressionId}">Stopped</span>
        </div>
    `;
    const messagesEl = getMessagesEl();
    messagesEl.appendChild(widgetEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    const playBtn = widgetEl.querySelector(".play-btn");
    const pauseBtn = widgetEl.querySelector(".pause-btn");
    const stopBtn = widgetEl.querySelector(".stop-btn");
    playBtn?.addEventListener("click", () =>
        startChordProgression(progressionId, chords, tempo, timeSignature, chordsPerBar)
    );
    pauseBtn?.addEventListener("click", () => pauseChordProgression(progressionId));
    stopBtn?.addEventListener("click", () => stopChordProgression(progressionId));
    chordProgressions.set(progressionId, {
        chords,
        tempo,
        timeSignature,
        chordsPerBar,
        widgetEl,
        scheduler: null,
        currentChordIndex: 0,
        isPlaying: false,
    });
}

export function parseChordName(chordName: string): number[] {
    const noteToSemitones: Record<string, number> = {
        C: 0,
        "C#": 1,
        Db: 1,
        D: 2,
        "D#": 3,
        Eb: 3,
        E: 4,
        "E#": 5,
        Fb: 4,
        F: 5,
        "F#": 6,
        Gb: 6,
        G: 7,
        "G#": 8,
        Ab: 8,
        A: 9,
        "A#": 10,
        Bb: 10,
        B: 11,
        "B#": 0,
        Cb: 11,
    };

    const match = chordName.match(/^([A-G][#b]?)/);
    const baseNote = match ? match[1] : "C";
    const semitones = noteToSemitones[baseNote] ?? 0;

    const octave = 4;
    const rootFreq = 440 * Math.pow(2, (semitones - 9 + (octave - 4) * 12) / 12);

    const chordType = chordName.slice(baseNote.length).toLowerCase();
    let intervals: number[];

    // Specific qualities first: a naive "includes('m')" check would classify
    // Cmaj7 and Cdim as minor.
    if (chordType.includes("dim")) {
        intervals = [0, 3, 6];
    } else if (chordType.includes("aug")) {
        intervals = [0, 4, 8];
    } else if (chordType.includes("sus4")) {
        intervals = [0, 5, 7];
    } else if (chordType.includes("sus2")) {
        intervals = [0, 2, 7];
    } else if (chordType.includes("sus")) {
        intervals = [0, 5, 7];
    } else if (chordType.includes("maj")) {
        // maj, maj7, maj9... all get a major triad
        intervals = [0, 4, 7];
    } else if (/^(m|min)(?!aj)/.test(chordType)) {
        intervals = [0, 3, 7];
    } else {
        intervals = [0, 4, 7];
    }

    return intervals.map((interval) => rootFreq * Math.pow(2, interval / 12));
}

function playChordAudio(
    audioContext: AudioContext,
    frequencies: number[],
    duration: number,
    startTime: number
): void {
    frequencies.forEach((freq) => {
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.frequency.value = freq;
        osc.type = "sine";
        gain.gain.setValueAtTime(0.15, startTime);
        gain.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
        osc.connect(gain);
        gain.connect(audioContext.destination);
        osc.start(startTime);
        osc.stop(startTime + duration);
    });
}

function startChordProgression(
    progressionId: string,
    chords: string[],
    tempo: number,
    timeSignature: string,
    chordsPerBar: number
): void {
    // Nothing to play; would otherwise crash on chords[chordIndex].
    if (chords.length === 0) return;
    const progression = chordProgressions.get(progressionId);
    if (!progression || progression.isPlaying) return;
    progression.isPlaying = true;
    const [beats, division] = validateTimeSignature(timeSignature).split("/").map(Number);
    const barDuration = (beats / division) * (60 / clampBpm(tempo));
    const chordDuration = barDuration / positiveNumber(chordsPerBar, 1);
    const widgetEl = progression.widgetEl;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${progressionId}`);
    if (playBtn) playBtn.style.display = "none";
    if (pauseBtn) pauseBtn.style.display = "inline-block";
    if (statusEl) {
        statusEl.textContent = "Playing";
        statusEl.className = "chord-progression-status";
    }
    if (!progression.scheduler) {
        progression.scheduler = createBeatScheduler({
            // One scheduler "beat" per chord change: 60 / bpm === chordDuration.
            bpm: 60 / chordDuration,
            beats: chords.length,
            scheduleAudio: (ctx: AudioContext, time: number, chordIndex: number): void => {
                const frequencies = parseChordName(chords[chordIndex]);
                playChordAudio(ctx, frequencies, chordDuration, time);
            },
            onBeat: (chordIndex: number): void => {
                progression.currentChordIndex = chordIndex;
                const chordBoxes = widgetEl.querySelectorAll(".chord-box");
                chordBoxes.forEach((box, idx) => {
                    if (idx === chordIndex) {
                        box.classList.add("active");
                    } else {
                        box.classList.remove("active");
                    }
                });
            },
        });
    }
    progression.scheduler.start();
}

function pauseChordProgression(progressionId: string): void {
    const progression = chordProgressions.get(progressionId);
    if (!progression || !progression.isPlaying) return;
    progression.scheduler?.stop();
    progression.isPlaying = false;
    const widgetEl = progression.widgetEl;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${progressionId}`);
    if (playBtn) playBtn.style.display = "inline-block";
    if (pauseBtn) pauseBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Paused";
        statusEl.className = "chord-progression-status";
    }
}

function stopChordProgression(progressionId: string): void {
    const progression = chordProgressions.get(progressionId);
    if (!progression) return;
    progression.scheduler?.stop();
    progression.scheduler?.resetBeat();
    progression.isPlaying = false;
    progression.currentChordIndex = 0;
    const widgetEl = progression.widgetEl;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${progressionId}`);
    const chordBoxes = widgetEl.querySelectorAll(".chord-box");
    chordBoxes.forEach((box) => box.classList.remove("active"));
    if (playBtn) playBtn.style.display = "inline-block";
    if (pauseBtn) pauseBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Stopped";
        statusEl.className = "chord-progression-status";
    }
}
