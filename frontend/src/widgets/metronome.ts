import { MetronomeState } from "../types.js";
import { addMessage, addTypingIndicator } from "../ui.js";

function getMessagesEl(): HTMLElement {
    const el = document.getElementById("messages");
    if (!el) {
        throw new Error("Messages element not found");
    }
    return el as HTMLElement;
}

const metronomes = new Map<string, MetronomeState>();

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];
let ws: WebSocket | null = null;
let sessionId: string | null = null;

export function setMetronomeWebSocket(websocket: WebSocket | null): void {
    ws = websocket;
}

export function setMetronomeSessionId(id: string | null): void {
    sessionId = id;
}

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
        <div class="recording-section">
            <label class="keep-metronome-label">
                <input type="checkbox" class="keep-metronome-cb" checked />
                Keep metronome playing during recording
            </label>
            <div class="recording-controls">
                <button class="record-btn" data-metronome-id="${metronomeId}">Record</button>
                <button class="stop-rec-btn" data-metronome-id="${metronomeId}" style="display:none;">Stop</button>
                <button class="send-btn" data-metronome-id="${metronomeId}" disabled>Send</button>
                <button class="cancel-btn" data-metronome-id="${metronomeId}">Cancel</button>
                <span class="recording-status" id="rec-status-${metronomeId}"></span>
            </div>
            <div class="audio-player" id="rec-player-${metronomeId}"></div>
        </div>
    `;
    const messagesEl = getMessagesEl();
    messagesEl.appendChild(widgetEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    const playBtn = widgetEl.querySelector(".play-btn");
    const pauseBtn = widgetEl.querySelector(".pause-btn");
    const stopBtn = widgetEl.querySelector(".stop-btn");
    playBtn?.addEventListener("click", () => startMetronome(metronomeId, bpm, beats));
    pauseBtn?.addEventListener("click", () => pauseMetronome(metronomeId));
    stopBtn?.addEventListener("click", () => stopMetronome(metronomeId));

    widgetEl
        .querySelector(".record-btn")
        ?.addEventListener("click", () => startRecording(metronomeId));
    widgetEl
        .querySelector(".stop-rec-btn")
        ?.addEventListener("click", () => stopRecording(metronomeId));
    widgetEl
        .querySelector(".send-btn")
        ?.addEventListener("click", () => sendRecording(metronomeId));
    widgetEl
        .querySelector(".cancel-btn")
        ?.addEventListener("click", () => cancelRecording(metronomeId));

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

async function startRecording(metronomeId: string): Promise<void> {
    const metronome = metronomes.get(metronomeId);
    const widgetEl = metronome?.widgetEl;
    if (!widgetEl) return;

    const keepPlaying = (widgetEl.querySelector(".keep-metronome-cb") as HTMLInputElement)?.checked;
    if (!keepPlaying && metronome?.isPlaying) {
        pauseMetronome(metronomeId);
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        const statusEl = document.getElementById(`rec-status-${metronomeId}`) as HTMLElement;
        const recordBtn = widgetEl.querySelector(".record-btn") as HTMLButtonElement;
        const stopRecBtn = widgetEl.querySelector(".stop-rec-btn") as HTMLButtonElement;

        if (!statusEl || !recordBtn || !stopRecBtn) return;

        mediaRecorder.ondataavailable = (event: BlobEvent) => {
            if (event.data) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            const audioUrl = URL.createObjectURL(audioBlob);
            const playerEl = document.getElementById(`rec-player-${metronomeId}`);
            if (playerEl) {
                playerEl.innerHTML = `<audio controls src="${audioUrl}"></audio>`;
            }

            const sendBtn = widgetEl.querySelector(".send-btn") as HTMLButtonElement;
            if (sendBtn) {
                sendBtn.disabled = false;
            }
            if (statusEl) {
                statusEl.textContent = "Recording complete";
                statusEl.className = "recording-status";
            }
        };

        mediaRecorder.start();
        statusEl.textContent = "Recording...";
        statusEl.className = "recording-status recording";
        recordBtn.style.display = "none";
        stopRecBtn.style.display = "inline-block";
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        addMessage(`Error accessing microphone: ${errorMessage}`, "error");
    }
}

function stopRecording(metronomeId: string): void {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach((track) => track.stop());

        const metronome = metronomes.get(metronomeId);
        const widgetEl = metronome?.widgetEl;
        if (!widgetEl) return;

        const stopRecBtn = widgetEl.querySelector(".stop-rec-btn") as HTMLButtonElement;
        const recordBtn = widgetEl.querySelector(".record-btn") as HTMLButtonElement;

        if (recordBtn && stopRecBtn) {
            recordBtn.style.display = "inline-block";
            stopRecBtn.style.display = "none";
        }
    }
}

async function sendRecording(metronomeId: string): Promise<void> {
    if (audioChunks.length === 0) {
        addMessage("No audio recorded", "error");
        return;
    }

    const metronome = metronomes.get(metronomeId);
    const widgetEl = metronome?.widgetEl;
    if (!widgetEl) return;

    const sendBtn = widgetEl.querySelector(".send-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`rec-status-${metronomeId}`) as HTMLElement;

    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = "Uploading...";
    }
    if (statusEl) {
        statusEl.textContent = "Uploading audio...";
        statusEl.className = "recording-status";
    }

    const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
    const formData = new FormData();
    formData.append("file", audioBlob, "recording.wav");
    formData.append("recording_id", metronomeId);

    try {
        const response = await fetch(`${window.location.origin}/api/audio/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text().catch(() => response.statusText);
            throw new Error(`Upload failed: ${errorText}`);
        }

        const data = (await response.json()) as { audio_file_id: string };

        if (ws && ws.readyState === WebSocket.OPEN) {
            addTypingIndicator();
            ws.send(
                JSON.stringify({
                    type: "audio_ready",
                    audio_file_id: data.audio_file_id,
                    recording_id: metronomeId,
                    session_id: sessionId,
                })
            );
        } else {
            addMessage("Connection lost. Please reconnect and try again.", "error");
        }

        audioChunks = [];
        mediaRecorder = null;

        // Reset recording UI but keep the metronome widget
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = "Send";
        }
        if (statusEl) {
            statusEl.textContent = "Sent";
            statusEl.className = "recording-status";
        }
        const playerEl = document.getElementById(`rec-player-${metronomeId}`);
        if (playerEl) {
            playerEl.innerHTML = "";
        }
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        addMessage(`Error uploading audio: ${errorMessage}`, "error");

        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = "Send";
        }
        if (statusEl) {
            statusEl.textContent = "Upload failed. Please try again.";
            statusEl.className = "recording-status";
        }
    }
}

function cancelRecording(metronomeId: string): void {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach((track) => track.stop());
    }
    audioChunks = [];
    mediaRecorder = null;

    const metronome = metronomes.get(metronomeId);
    const widgetEl = metronome?.widgetEl;
    if (!widgetEl) return;

    const recordBtn = widgetEl.querySelector(".record-btn") as HTMLButtonElement;
    const stopRecBtn = widgetEl.querySelector(".stop-rec-btn") as HTMLButtonElement;
    const sendBtn = widgetEl.querySelector(".send-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`rec-status-${metronomeId}`) as HTMLElement;
    const playerEl = document.getElementById(`rec-player-${metronomeId}`);

    if (recordBtn) recordBtn.style.display = "inline-block";
    if (stopRecBtn) stopRecBtn.style.display = "none";
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = "Send";
    }
    if (statusEl) {
        statusEl.textContent = "";
        statusEl.className = "recording-status";
    }
    if (playerEl) playerEl.innerHTML = "";
}
