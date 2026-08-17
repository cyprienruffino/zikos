import { MetronomeState } from "../types.js";
import { addMessage, addTypingIndicator } from "../ui.js";
import { escapeHtml, sanitizeToolId } from "../utils/sanitize.js";
import { clampBpm, validateTimeSignature } from "../utils/validate.js";
import { createBeatScheduler } from "./audioEngine.js";
import { pickRecordingType, extensionForMimeType } from "../utils/media.js";

function getMessagesEl(): HTMLElement {
    const el = document.getElementById("messages");
    if (!el) {
        throw new Error("Messages element not found");
    }
    return el as HTMLElement;
}

const metronomes = new Map<string, MetronomeState>();

interface RecordingState {
    mediaRecorder: MediaRecorder | null;
    audioChunks: Blob[];
    /** Synchronous guard so a double-click cannot acquire two streams. */
    starting: boolean;
    objectUrl: string | null;
    mimeType: string;
}

const recordings = new Map<string, RecordingState>();

function getRecordingState(metronomeId: string): RecordingState {
    let state = recordings.get(metronomeId);
    if (!state) {
        state = {
            mediaRecorder: null,
            audioChunks: [],
            starting: false,
            objectUrl: null,
            mimeType: "",
        };
        recordings.set(metronomeId, state);
    }
    return state;
}

/** Stop any active recorder/stream and release resources for this widget. */
function teardownRecording(metronomeId: string): void {
    const state = recordings.get(metronomeId);
    if (!state) return;
    if (state.mediaRecorder) {
        if (state.mediaRecorder.state !== "inactive") {
            state.mediaRecorder.stop();
        }
        state.mediaRecorder.stream.getTracks().forEach((track) => track.stop());
        state.mediaRecorder = null;
    }
    if (state.objectUrl) {
        URL.revokeObjectURL(state.objectUrl);
        state.objectUrl = null;
    }
    state.audioChunks = [];
    state.starting = false;
}

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
    metronomeId = sanitizeToolId(metronomeId, "met");
    bpm = clampBpm(bpm);
    timeSignature = validateTimeSignature(timeSignature);
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
        ${description ? `<div class="description">${escapeHtml(description)}</div>` : ""}
        <div class="metronome-info">
            <span>BPM: <strong>${escapeHtml(bpm)}</strong></span>
            <span>Time: <strong>${escapeHtml(timeSignature)}</strong></span>
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
        scheduler: null,
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
    teardownRecording(metronomeId);
    recordings.delete(metronomeId);
    const widget = document.getElementById(`metronome-${metronomeId}`);
    if (widget) {
        widget.remove();
    }
}

export function startMetronome(metronomeId: string, bpm: number, beats: number): void {
    bpm = clampBpm(bpm);
    const metronome = metronomes.get(metronomeId);
    if (!metronome || metronome.isPlaying) return;
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
    if (!metronome.scheduler) {
        metronome.scheduler = createBeatScheduler({
            bpm,
            beats,
            onBeat: (beatIndex: number): void => {
                metronome.currentBeat = beatIndex;
                if (!widgetEl) return;
                const beatDots = widgetEl.querySelectorAll(".beat-dot");
                beatDots.forEach((dot, idx) => {
                    if (idx === beatIndex) {
                        dot.classList.add("active");
                        setTimeout(() => dot.classList.remove("active"), intervalMs * 0.2);
                    }
                });
            },
        });
    }
    metronome.scheduler.setBpm(bpm);
    metronome.scheduler.start();
}

export function pauseMetronome(metronomeId: string): void {
    const metronome = metronomes.get(metronomeId);
    if (!metronome || !metronome.isPlaying) return;
    metronome.scheduler?.stop();
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
    metronome.scheduler?.stop();
    metronome.scheduler?.resetBeat();
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

    const recState = getRecordingState(metronomeId);
    // Synchronous guard: a second click before getUserMedia resolves must not
    // acquire a second stream.
    if (
        recState.starting ||
        (recState.mediaRecorder && recState.mediaRecorder.state !== "inactive")
    ) {
        return;
    }
    recState.starting = true;

    const keepPlaying = (widgetEl.querySelector(".keep-metronome-cb") as HTMLInputElement)?.checked;
    if (!keepPlaying && metronome?.isPlaying) {
        pauseMetronome(metronomeId);
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
            },
        });

        if (!recordings.has(metronomeId)) {
            // Widget was removed while waiting for permission.
            stream.getTracks().forEach((track) => track.stop());
            return;
        }

        const recordingType = pickRecordingType();
        const mediaRecorder = recordingType.mimeType
            ? new MediaRecorder(stream, { mimeType: recordingType.mimeType })
            : new MediaRecorder(stream);
        recState.mediaRecorder = mediaRecorder;
        recState.audioChunks = [];
        recState.mimeType = mediaRecorder.mimeType || recordingType.mimeType || "audio/webm";

        const statusEl = document.getElementById(`rec-status-${metronomeId}`) as HTMLElement;
        const recordBtn = widgetEl.querySelector(".record-btn") as HTMLButtonElement;
        const stopRecBtn = widgetEl.querySelector(".stop-rec-btn") as HTMLButtonElement;

        if (!statusEl || !recordBtn || !stopRecBtn) return;

        mediaRecorder.ondataavailable = (event: BlobEvent) => {
            if (event.data) {
                recState.audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(recState.audioChunks, { type: recState.mimeType });
            const audioUrl = URL.createObjectURL(audioBlob);
            if (recState.objectUrl) {
                URL.revokeObjectURL(recState.objectUrl);
            }
            recState.objectUrl = audioUrl;
            const playerEl = document.getElementById(`rec-player-${metronomeId}`);
            if (playerEl) {
                playerEl.innerHTML = "";
                const audio = document.createElement("audio");
                audio.controls = true;
                audio.src = audioUrl;
                playerEl.appendChild(audio);
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
    } finally {
        recState.starting = false;
    }
}

function stopRecording(metronomeId: string): void {
    const recState = recordings.get(metronomeId);
    const mediaRecorder = recState?.mediaRecorder;
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
    const recState = recordings.get(metronomeId);
    if (!recState || recState.audioChunks.length === 0) {
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

    const mimeType = recState.mimeType || "audio/webm";
    const audioBlob = new Blob(recState.audioChunks, { type: mimeType });
    const formData = new FormData();
    formData.append("file", audioBlob, `recording.${extensionForMimeType(mimeType)}`);
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

        teardownRecording(metronomeId);

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
    teardownRecording(metronomeId);

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
