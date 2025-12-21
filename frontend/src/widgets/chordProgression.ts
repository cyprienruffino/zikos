import { ChordProgressionState } from "../types.js";

function getMessagesEl(): HTMLElement {
    const el = document.getElementById("messages");
    if (!el) {
        throw new Error("Messages element not found");
    }
    return el as HTMLElement;
}

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
    const widgetEl = document.createElement("div");
    widgetEl.className = "chord-progression-widget";
    widgetEl.id = `chord-${progressionId}`;
    widgetEl.innerHTML = `
        <h3>Chord Progression</h3>
        ${description ? `<div class="description">${description}</div>` : ""}
        <div class="chord-progression-display" id="chords-${progressionId}">
            ${chords.map((chord, i) => `<div class="chord-box" data-chord-index="${i}">${chord}</div>`).join("")}
        </div>
        <div style="margin: 0.5rem 0; color: #2e7d32;">
            <span>Tempo: <strong>${tempo} BPM</strong></span>
            <span style="margin-left: 1rem;">Time: <strong>${timeSignature}</strong></span>
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
        audioContext: null,
        intervalId: null,
        currentChordIndex: 0,
        isPlaying: false,
    });
}

function parseChordName(chordName: string): number[] {
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

    const chordType = chordName.replace(baseNote, "").toLowerCase();
    let intervals: number[];

    if (chordType.includes("m") || chordType.includes("min")) {
        intervals = [0, 3, 7];
    } else if (chordType.includes("dim")) {
        intervals = [0, 3, 6];
    } else if (chordType.includes("aug")) {
        intervals = [0, 4, 8];
    } else if (chordType.includes("sus2")) {
        intervals = [0, 2, 7];
    } else if (chordType.includes("sus4") || chordType.includes("sus")) {
        intervals = [0, 5, 7];
    } else {
        intervals = [0, 4, 7];
    }

    return intervals.map((interval) => rootFreq * Math.pow(2, interval / 12));
}

function playChordAudio(audioContext: AudioContext, frequencies: number[], duration: number): void {
    frequencies.forEach((freq) => {
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.frequency.value = freq;
        osc.type = "sine";
        gain.gain.setValueAtTime(0.15, audioContext.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
        osc.connect(gain);
        gain.connect(audioContext.destination);
        osc.start();
        osc.stop(audioContext.currentTime + duration);
    });
}

function startChordProgression(
    progressionId: string,
    chords: string[],
    tempo: number,
    timeSignature: string,
    chordsPerBar: number
): void {
    const progression = chordProgressions.get(progressionId);
    if (!progression || progression.isPlaying) return;
    if (!progression.audioContext) {
        progression.audioContext = new AudioContext();
    }
    const audioContext = progression.audioContext;
    if (audioContext.state === "suspended") {
        audioContext.resume();
    }
    progression.isPlaying = true;
    const [beats, division] = timeSignature.split("/").map(Number);
    const barDuration = (beats / division) * (60 / tempo);
    const chordDuration = barDuration / chordsPerBar;
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
    function playChord(chordIndex: number): void {
        const chordBoxes = widgetEl.querySelectorAll(".chord-box");
        chordBoxes.forEach((box, idx) => {
            if (idx === chordIndex) {
                box.classList.add("active");
            } else {
                box.classList.remove("active");
            }
        });

        const chordName = chords[chordIndex];
        const frequencies = parseChordName(chordName);
        playChordAudio(audioContext, frequencies, chordDuration);
    }
    playChord(progression.currentChordIndex);
    progression.intervalId = window.setInterval(() => {
        progression.currentChordIndex = (progression.currentChordIndex + 1) % chords.length;
        playChord(progression.currentChordIndex);
    }, chordDuration * 1000);
}

function pauseChordProgression(progressionId: string): void {
    const progression = chordProgressions.get(progressionId);
    if (!progression || !progression.isPlaying) return;
    if (progression.intervalId) {
        clearInterval(progression.intervalId);
        progression.intervalId = null;
    }
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
    if (progression.intervalId) {
        clearInterval(progression.intervalId);
        progression.intervalId = null;
    }
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
