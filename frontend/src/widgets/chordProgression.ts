import { ChordProgressionState } from "../types.js";

const messagesEl = document.getElementById("messages") as HTMLElement;
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
