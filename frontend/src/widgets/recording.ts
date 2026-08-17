import { addMessage, addTypingIndicator } from "../ui.js";
import { escapeHtml, sanitizeToolId } from "../utils/sanitize.js";
import { pickRecordingType, extensionForMimeType } from "../utils/media.js";

interface RecordingState {
    mediaRecorder: MediaRecorder | null;
    audioChunks: Blob[];
    /** Synchronous guard so a double-click cannot acquire two streams. */
    starting: boolean;
    maxDurationMs: number;
    autoStopTimeout: number | null;
    objectUrl: string | null;
    mimeType: string;
}

const recordings = new Map<string, RecordingState>();

let ws: WebSocket | null = null;
let sessionId: string | null = null;

export function setWebSocket(websocket: WebSocket | null): void {
    ws = websocket;
}

export function setSessionId(id: string | null): void {
    sessionId = id;
}

export function reset(): void {
    for (const recordingId of [...recordings.keys()]) {
        teardownRecording(recordingId);
    }
    recordings.clear();
}

export function addRecordingWidget(
    recordingId: string,
    prompt: string,
    maxDuration: number
): void {
    recordingId = sanitizeToolId(recordingId, "rec");
    const messagesEl = document.getElementById("messages") as HTMLElement;
    const widgetEl = document.createElement("div");
    widgetEl.className = "recording-widget";
    widgetEl.id = `recording-${recordingId}`;
    widgetEl.innerHTML = `
        <h3>Recording Request</h3>
        <div class="prompt">${escapeHtml(prompt)}</div>
        <div class="recording-controls">
            <button class="record-btn" data-recording-id="${recordingId}">Record</button>
            <button class="stop-btn" data-recording-id="${recordingId}" style="display:none;">Stop</button>
            <button class="send-btn" data-recording-id="${recordingId}" disabled>Send</button>
            <button class="cancel-btn" data-recording-id="${recordingId}">Cancel</button>
            <span class="recording-status" id="status-${recordingId}"></span>
        </div>
        <div class="audio-player" id="player-${recordingId}"></div>
    `;
    messagesEl.appendChild(widgetEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    recordings.set(recordingId, {
        mediaRecorder: null,
        audioChunks: [],
        starting: false,
        maxDurationMs: maxDuration > 0 ? maxDuration * 1000 : 60_000,
        autoStopTimeout: null,
        objectUrl: null,
        mimeType: "",
    });

    widgetEl
        .querySelector(".record-btn")
        ?.addEventListener("click", () => startRecording(recordingId));
    widgetEl
        .querySelector(".stop-btn")
        ?.addEventListener("click", () => stopRecording(recordingId));
    widgetEl
        .querySelector(".send-btn")
        ?.addEventListener("click", () => sendRecording(recordingId));
    widgetEl
        .querySelector(".cancel-btn")
        ?.addEventListener("click", () => cancelRecording(recordingId));
}

/** Stop any active recorder/stream and release resources for this widget. */
function teardownRecording(recordingId: string): void {
    const state = recordings.get(recordingId);
    if (!state) return;
    if (state.autoStopTimeout !== null) {
        clearTimeout(state.autoStopTimeout);
        state.autoStopTimeout = null;
    }
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

export function removeRecordingWidget(recordingId: string): void {
    teardownRecording(recordingId);
    recordings.delete(recordingId);
    const widget = document.getElementById(`recording-${recordingId}`);
    if (widget) {
        widget.remove();
    }
}

async function startRecording(recordingId: string): Promise<void> {
    const state = recordings.get(recordingId);
    if (!state) return;
    // Synchronous guard: a second click before getUserMedia resolves must not
    // acquire a second stream.
    if (state.starting || (state.mediaRecorder && state.mediaRecorder.state !== "inactive")) {
        return;
    }
    state.starting = true;
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
            },
        });

        const current = recordings.get(recordingId);
        if (!current) {
            // Widget was removed (e.g. cancelled) while waiting for permission.
            stream.getTracks().forEach((track) => track.stop());
            return;
        }

        const recordingType = pickRecordingType();
        const mediaRecorder = recordingType.mimeType
            ? new MediaRecorder(stream, { mimeType: recordingType.mimeType })
            : new MediaRecorder(stream);
        current.mediaRecorder = mediaRecorder;
        current.audioChunks = [];
        current.mimeType = mediaRecorder.mimeType || recordingType.mimeType || "audio/webm";

        const widgetEl = document.getElementById(`recording-${recordingId}`);
        if (!widgetEl) {
            teardownRecording(recordingId);
            return;
        }

        const statusEl = document.getElementById(`status-${recordingId}`) as HTMLElement;
        const recordBtn = widgetEl.querySelector(".record-btn") as HTMLButtonElement;
        const stopBtn = widgetEl.querySelector(".stop-btn") as HTMLButtonElement;

        if (!statusEl || !recordBtn || !stopBtn) return;

        mediaRecorder.ondataavailable = (event: BlobEvent) => {
            if (event.data) {
                current.audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            if (current.autoStopTimeout !== null) {
                clearTimeout(current.autoStopTimeout);
                current.autoStopTimeout = null;
            }
            const audioBlob = new Blob(current.audioChunks, { type: current.mimeType });
            const audioUrl = URL.createObjectURL(audioBlob);
            if (current.objectUrl) {
                URL.revokeObjectURL(current.objectUrl);
            }
            current.objectUrl = audioUrl;
            const playerEl = document.getElementById(`player-${recordingId}`);
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
            if (recordBtn && stopBtn) {
                recordBtn.style.display = "inline-block";
                stopBtn.style.display = "none";
            }
        };

        mediaRecorder.start();
        // Honor the max_duration requested by the tool call.
        current.autoStopTimeout = window.setTimeout(() => {
            stopRecording(recordingId);
        }, current.maxDurationMs);
        statusEl.textContent = "Recording...";
        statusEl.className = "recording-status recording";
        recordBtn.style.display = "none";
        stopBtn.style.display = "inline-block";
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        addMessage(`Error accessing microphone: ${errorMessage}`, "error");
    } finally {
        const current = recordings.get(recordingId);
        if (current) {
            current.starting = false;
        }
    }
}

function stopRecording(recordingId: string): void {
    const state = recordings.get(recordingId);
    if (!state) return;
    if (state.autoStopTimeout !== null) {
        clearTimeout(state.autoStopTimeout);
        state.autoStopTimeout = null;
    }
    if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
        state.mediaRecorder.stop();
        state.mediaRecorder.stream.getTracks().forEach((track) => track.stop());
    }
}

async function sendRecording(recordingId: string): Promise<void> {
    const state = recordings.get(recordingId);
    if (!state || state.audioChunks.length === 0) {
        addMessage("No audio recorded", "error");
        return;
    }

    const widgetEl = document.getElementById(`recording-${recordingId}`);
    if (!widgetEl) return;

    const sendBtn = widgetEl.querySelector(".send-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${recordingId}`) as HTMLElement;

    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = "Uploading...";
    }
    if (statusEl) {
        statusEl.textContent = "Uploading audio...";
        statusEl.className = "recording-status";
    }

    const mimeType = state.mimeType || "audio/webm";
    const audioBlob = new Blob(state.audioChunks, { type: mimeType });
    const formData = new FormData();
    formData.append("file", audioBlob, `recording.${extensionForMimeType(mimeType)}`);
    formData.append("recording_id", recordingId);

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
        removeRecordingWidget(recordingId);

        if (ws && ws.readyState === WebSocket.OPEN) {
            addTypingIndicator();
            ws.send(
                JSON.stringify({
                    type: "audio_ready",
                    audio_file_id: data.audio_file_id,
                    recording_id: recordingId,
                    session_id: sessionId,
                })
            );
        } else {
            addMessage("Connection lost. Please reconnect and try again.", "error");
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

function cancelRecording(recordingId: string): void {
    removeRecordingWidget(recordingId);

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
            JSON.stringify({
                type: "cancel_recording",
                recording_id: recordingId,
            })
        );
    }
}
