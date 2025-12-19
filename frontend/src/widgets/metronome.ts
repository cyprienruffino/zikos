import { MetronomeState } from "../types";

const messagesEl = document.getElementById("messages") as HTMLElement;
const metronomes = new Map<string, MetronomeState>();

export function addMetronomeWidget(
    metronomeId: string,
    bpm: number,
    timeSignature: string,
    description?: string
): void {
    const widgetEl = document.createElement("div");
    widgetEl.className = "metronome-widget";
    widgetEl.id = `metronome-${metronomeId}`;
    const [beats] = timeSignature.split("/").map(Number);
    const beatDots = Array.from(
        { length: beats },
        (_, i) => `<div class="beat-dot ${i === 0 ? "downbeat" : ""}" data-beat="${i}"></div>`
    ).join("");
    widgetEl.innerHTML = `
        <h3>Metronome</h3>
        ${description ? `<div class="description">${description}</div>` : ""}
        <div class="metronome-info">
            <span>BPM: <strong>${bpm}</strong></span>
            <span>Time: <strong>${timeSignature}</strong></span>
        </div>
        <div class="metronome-beat-indicator">
            ${beatDots}
        </div>
        <div class="metronome-controls">
            <button class="play-btn" data-metronome-id="${metronomeId}">Play</button>
            <button class="pause-btn" data-metronome-id="${metronomeId}" style="display:none;">Pause</button>
            <button class="stop-btn" data-metronome-id="${metronomeId}">Stop</button>
            <span class="metronome-status" id="status-${metronomeId}">Stopped</span>
        </div>
    `;
    messagesEl.appendChild(widgetEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    const playBtn = widgetEl.querySelector(".play-btn");
    const pauseBtn = widgetEl.querySelector(".pause-btn");
    const stopBtn = widgetEl.querySelector(".stop-btn");
    playBtn?.addEventListener("click", () => startMetronome(metronomeId, bpm, beats));
    pauseBtn?.addEventListener("click", () => pauseMetronome(metronomeId));
    stopBtn?.addEventListener("click", () => stopMetronome(metronomeId));
    metronomes.set(metronomeId, {
        bpm,
        beats,
        widgetEl,
        intervalId: null,
        audioContext: null,
        currentBeat: 0,
        isPlaying: false,
    });
}

export function removeMetronomeWidget(metronomeId: string): void {
    const metronome = metronomes.get(metronomeId);
    if (metronome) {
        stopMetronome(metronomeId);
        metronomes.delete(metronomeId);
    }
    const widget = document.getElementById(`metronome-${metronomeId}`);
    if (widget) {
        widget.remove();
    }
}

export function startMetronome(metronomeId: string, bpm: number, beats: number): void {
    const metronome = metronomes.get(metronomeId);
    if (!metronome || metronome.isPlaying) return;
    if (!metronome.audioContext) {
        metronome.audioContext = new AudioContext();
    }
    const audioContext = metronome.audioContext;
    if (audioContext.state === "suspended") {
        audioContext.resume();
    }
    metronome.isPlaying = true;
    const intervalMs = (60 / bpm) * 1000;
    const widgetEl = metronome.widgetEl;
    if (!widgetEl) return;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${metronomeId}`);
    if (playBtn) playBtn.style.display = "none";
    if (pauseBtn) pauseBtn.style.display = "inline-block";
    if (statusEl) {
        statusEl.textContent = "Playing";
        statusEl.className = "metronome-status playing";
    }
    function playBeat(beatIndex: number): void {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        const isDownbeat = beatIndex === 0;
        oscillator.frequency.value = isDownbeat ? 800 : 600;
        oscillator.type = "sine";
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.1);
        if (!widgetEl) return;
        const beatDots = widgetEl.querySelectorAll(".beat-dot");
        beatDots.forEach((dot, idx) => {
            if (idx === beatIndex) {
                dot.classList.add("active");
                setTimeout(() => dot.classList.remove("active"), intervalMs * 0.2);
            }
        });
    }
    playBeat(metronome.currentBeat);
    metronome.intervalId = window.setInterval(() => {
        metronome.currentBeat = (metronome.currentBeat + 1) % beats;
        playBeat(metronome.currentBeat);
    }, intervalMs);
}

export function pauseMetronome(metronomeId: string): void {
    const metronome = metronomes.get(metronomeId);
    if (!metronome || !metronome.isPlaying) return;
    if (metronome.intervalId) {
        clearInterval(metronome.intervalId);
        metronome.intervalId = null;
    }
    metronome.isPlaying = false;
    const widgetEl = metronome.widgetEl;
    if (!widgetEl) return;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${metronomeId}`);
    if (playBtn) playBtn.style.display = "inline-block";
    if (pauseBtn) pauseBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Paused";
        statusEl.className = "metronome-status";
    }
}

export function stopMetronome(metronomeId: string): void {
    const metronome = metronomes.get(metronomeId);
    if (!metronome) return;
    if (metronome.intervalId) {
        clearInterval(metronome.intervalId);
        metronome.intervalId = null;
    }
    metronome.isPlaying = false;
    metronome.currentBeat = 0;
    const widgetEl = metronome.widgetEl;
    if (!widgetEl) return;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${metronomeId}`);
    const beatDots = widgetEl.querySelectorAll(".beat-dot");
    beatDots.forEach((dot) => dot.classList.remove("active"));
    if (playBtn) playBtn.style.display = "inline-block";
    if (pauseBtn) pauseBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Stopped";
        statusEl.className = "metronome-status";
    }
}

export function getMetronome(metronomeId: string): MetronomeState | undefined {
    return metronomes.get(metronomeId);
}

export function setMetronome(metronomeId: string, state: MetronomeState): void {
    metronomes.set(metronomeId, state);
}
