import { EarTrainerState } from "../types.js";
import { escapeHtml, sanitizeToolId } from "../utils/sanitize.js";
import { getAudioContext } from "./audioEngine.js";
import { getMessagesEl } from "../dom.js";

const earTrainers = new Map<string, EarTrainerState>();

export function addEarTrainerWidget(
    trainerId: string,
    mode: string,
    difficulty: string,
    rootNote: string,
    description?: string
): void {
    trainerId = sanitizeToolId(trainerId, "ear");
    const widgetEl = document.createElement("div");
    widgetEl.className = "ear-trainer-widget";
    widgetEl.id = `ear-${trainerId}`;
    // In chords mode the answers are chord qualities: interval names would
    // all have played the same triad and been unanswerable.
    const intervals =
        mode === "chords"
            ? difficulty === "easy"
                ? ["maj", "min"]
                : difficulty === "medium"
                  ? ["maj", "min", "dim"]
                  : ["maj", "min", "dim", "aug"]
            : difficulty === "easy"
              ? ["P1", "P4", "P5", "P8"]
              : difficulty === "medium"
                ? ["m2", "M2", "m3", "M3", "P4", "P5", "m6", "M6", "m7", "M7", "P8"]
                : [
                      "m2",
                      "M2",
                      "A2",
                      "m3",
                      "M3",
                      "P4",
                      "A4",
                      "P5",
                      "m6",
                      "M6",
                      "A6",
                      "m7",
                      "M7",
                      "P8",
                  ];
    widgetEl.innerHTML = `
        <h3>Ear Trainer - ${mode === "intervals" ? "Intervals" : "Chords"}</h3>
        ${description ? `<div class="description">${escapeHtml(description)}</div>` : ""}
        <div class="ear-trainer-question" id="question-${trainerId}">
            <p>Listen to the ${mode === "intervals" ? "interval" : "chord"} and identify it:</p>
        </div>
        <div class="ear-trainer-controls">
            <button class="play-btn" data-trainer-id="${trainerId}">Play</button>
            <button class="next-btn" data-trainer-id="${trainerId}" style="display:none;">Next</button>
            <span class="ear-trainer-status" id="status-${trainerId}">Ready</span>
        </div>
        <div class="ear-trainer-options" id="options-${trainerId}">
            ${intervals.map((interval) => `<button class="ear-trainer-option" data-interval="${interval}" data-trainer-id="${trainerId}">${interval}</button>`).join("")}
        </div>
        <div class="ear-trainer-result" id="result-${trainerId}" style="display:none;"></div>
    `;
    const messagesEl = getMessagesEl();
    messagesEl.appendChild(widgetEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    const playBtn = widgetEl.querySelector(".play-btn");
    const nextBtn = widgetEl.querySelector(".next-btn");
    playBtn?.addEventListener("click", () =>
        playEarTrainerQuestion(trainerId, mode, rootNote, intervals)
    );
    nextBtn?.addEventListener("click", () =>
        nextEarTrainerQuestion(trainerId, mode, rootNote, intervals)
    );
    const optionBtns = widgetEl.querySelectorAll(".ear-trainer-option");
    optionBtns.forEach((btn) => {
        btn.addEventListener("click", () =>
            checkEarTrainerAnswer(trainerId, btn.getAttribute("data-interval") || "")
        );
    });
    earTrainers.set(trainerId, {
        mode,
        difficulty,
        rootNote,
        intervals,
        widgetEl,
        currentAnswer: null,
    });
}

function playEarTrainerQuestion(
    trainerId: string,
    mode: string,
    rootNote: string,
    intervals: string[]
): void {
    const trainer = earTrainers.get(trainerId);
    if (!trainer) return;
    // Reuse the app-wide AudioContext: creating one per question leaked
    // contexts until the browser refused to create more.
    const audioContext = getAudioContext();
    const randomInterval = intervals[Math.floor(Math.random() * intervals.length)];
    trainer.currentAnswer = randomInterval;
    const rootFreq = getNoteFrequency(rootNote, 4);
    const widgetEl = trainer.widgetEl;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const nextBtn = widgetEl.querySelector(".next-btn") as HTMLButtonElement;
    const resultEl = document.getElementById(`result-${trainerId}`);
    const optionBtns = widgetEl.querySelectorAll(".ear-trainer-option");
    if (resultEl) {
        resultEl.style.display = "none";
        resultEl.className = "ear-trainer-result";
    }
    optionBtns.forEach((btn) => {
        const btnEl = btn as HTMLElement;
        (btnEl as HTMLButtonElement).disabled = false;
        btnEl.style.opacity = "1";
    });
    if (mode === "intervals") {
        playInterval(audioContext, rootFreq, getIntervalFrequency(rootFreq, randomInterval));
    } else {
        playChord(audioContext, rootFreq, randomInterval);
    }
    if (playBtn) playBtn.style.display = "none";
    if (nextBtn) nextBtn.style.display = "inline-block";
}

const INTERVAL_SEMITONES: Record<string, number> = {
    P1: 0,
    m2: 1,
    M2: 2,
    A2: 3,
    m3: 3,
    M3: 4,
    P4: 5,
    A4: 6,
    P5: 7,
    m6: 8,
    M6: 9,
    A6: 10,
    m7: 10,
    M7: 11,
    P8: 12,
};

/** Enharmonically equivalent intervals (e.g. A2 and m3) sound identical. */
function isEnharmonicMatch(a: string, b: string): boolean {
    return INTERVAL_SEMITONES[a] !== undefined && INTERVAL_SEMITONES[a] === INTERVAL_SEMITONES[b];
}

function checkEarTrainerAnswer(trainerId: string, selectedInterval: string): void {
    const trainer = earTrainers.get(trainerId);
    if (!trainer) return;
    const widgetEl = trainer.widgetEl;
    const resultEl = document.getElementById(`result-${trainerId}`);
    const optionBtns = widgetEl.querySelectorAll(".ear-trainer-option");
    const isCorrect =
        selectedInterval === trainer.currentAnswer ||
        (trainer.mode === "intervals" &&
            trainer.currentAnswer !== null &&
            isEnharmonicMatch(selectedInterval, trainer.currentAnswer));
    if (resultEl) {
        resultEl.style.display = "block";
        resultEl.className = `ear-trainer-result ${isCorrect ? "correct" : "incorrect"}`;
        resultEl.textContent = isCorrect
            ? `Correct! It was ${trainer.currentAnswer}`
            : `Incorrect. It was ${trainer.currentAnswer}`;
    }
    optionBtns.forEach((btn) => {
        const btnEl = btn as HTMLElement;
        (btnEl as HTMLButtonElement).disabled = true;
        if (btn.getAttribute("data-interval") === trainer.currentAnswer) {
            btnEl.style.background = "#4caf50";
        } else if (btn.getAttribute("data-interval") === selectedInterval && !isCorrect) {
            btnEl.style.background = "#f44336";
        } else {
            btnEl.style.opacity = "0.5";
        }
    });
}

function nextEarTrainerQuestion(
    trainerId: string,
    mode: string,
    rootNote: string,
    intervals: string[]
): void {
    const trainer = earTrainers.get(trainerId);
    if (!trainer) return;
    const widgetEl = trainer.widgetEl;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const nextBtn = widgetEl.querySelector(".next-btn") as HTMLButtonElement;
    const optionBtns = widgetEl.querySelectorAll(".ear-trainer-option");
    optionBtns.forEach((btn) => {
        const btnEl = btn as HTMLElement;
        (btnEl as HTMLButtonElement).disabled = false;
        btnEl.style.opacity = "1";
        btnEl.style.background = "#00bcd4";
    });
    if (playBtn) playBtn.style.display = "inline-block";
    if (nextBtn) nextBtn.style.display = "none";
    playEarTrainerQuestion(trainerId, mode, rootNote, intervals);
}

function getNoteFrequency(note: string, octave: number): number {
    const notes: Record<string, number> = {
        C: 0,
        "C#": 1,
        D: 2,
        "D#": 3,
        E: 4,
        F: 5,
        "F#": 6,
        G: 7,
        "G#": 8,
        A: 9,
        "A#": 10,
        B: 11,
    };
    // Unknown notes fall back to C rather than producing NaN frequencies.
    const semitones = (notes[note] ?? 0) + (octave - 4) * 12;
    return 440 * Math.pow(2, semitones / 12);
}

function getIntervalFrequency(rootFreq: number, interval: string): number {
    const intervals: Record<string, number> = {
        P1: 0,
        m2: 1,
        M2: 2,
        A2: 3,
        m3: 3,
        M3: 4,
        P4: 5,
        A4: 6,
        P5: 7,
        m6: 8,
        M6: 9,
        A6: 10,
        m7: 10,
        M7: 11,
        P8: 12,
    };
    const semitones = intervals[interval] || 0;
    return rootFreq * Math.pow(2, semitones / 12);
}

function playInterval(audioContext: AudioContext, rootFreq: number, intervalFreq: number): void {
    const duration = 1;
    const rootOsc = audioContext.createOscillator();
    const intervalOsc = audioContext.createOscillator();
    const rootGain = audioContext.createGain();
    const intervalGain = audioContext.createGain();
    rootOsc.frequency.value = rootFreq;
    intervalOsc.frequency.value = intervalFreq;
    rootOsc.type = "sine";
    intervalOsc.type = "sine";
    rootGain.gain.setValueAtTime(0.3, audioContext.currentTime);
    rootGain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
    intervalGain.gain.setValueAtTime(0.3, audioContext.currentTime);
    intervalGain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
    rootOsc.connect(rootGain);
    intervalOsc.connect(intervalGain);
    rootGain.connect(audioContext.destination);
    intervalGain.connect(audioContext.destination);
    rootOsc.start();
    intervalOsc.start();
    rootOsc.stop(audioContext.currentTime + duration);
    intervalOsc.stop(audioContext.currentTime + duration);
}

function playChord(audioContext: AudioContext, rootFreq: number, chordType: string): void {
    const duration = 1.5;
    const chordNotes = getChordNotes(rootFreq, chordType);
    chordNotes.forEach((freq) => {
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.frequency.value = freq;
        osc.type = "sine";
        gain.gain.setValueAtTime(0.2, audioContext.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
        osc.connect(gain);
        gain.connect(audioContext.destination);
        osc.start();
        osc.stop(audioContext.currentTime + duration);
    });
}

const CHORD_QUALITY_SEMITONES: Record<string, number[]> = {
    maj: [0, 4, 7],
    min: [0, 3, 7],
    dim: [0, 3, 6],
    aug: [0, 4, 8],
};

function getChordNotes(rootFreq: number, quality: string): number[] {
    const semitones = CHORD_QUALITY_SEMITONES[quality] ?? CHORD_QUALITY_SEMITONES.maj;
    return semitones.map((semitone) => rootFreq * Math.pow(2, semitone / 12));
}
