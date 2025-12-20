import { addMessage, addTypingIndicator } from "../ui.js";

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];
let ws: WebSocket | null = null;
let sessionId: string | null = null;

export function setWebSocket(websocket: WebSocket | null): void {
    ws = websocket;
}

export function setSessionId(id: string | null): void {
    sessionId = id;
}

export function addRecordingWidget(
    recordingId: string,
    prompt: string,
    _maxDuration: number
): void {
    const messagesEl = document.getElementById("messages") as HTMLElement;
    const widgetEl = document.createElement("div");
    widgetEl.className = "recording-widget";
    widgetEl.id = `recording-${recordingId}`;
    widgetEl.innerHTML = `
        <h3>Recording Request</h3>
        <div class="prompt">${prompt}</div>
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

export function removeRecordingWidget(recordingId: string): void {
    const widget = document.getElementById(`recording-${recordingId}`);
    if (widget) {
        widget.remove();
    }
}

async function startRecording(recordingId: string): Promise<void> {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        const widgetEl = document.getElementById(`recording-${recordingId}`);
        if (!widgetEl) return;

        const statusEl = document.getElementById(`status-${recordingId}`) as HTMLElement;
        const recordBtn = widgetEl.querySelector(".record-btn") as HTMLButtonElement;
        const stopBtn = widgetEl.querySelector(".stop-btn") as HTMLButtonElement;

        if (!statusEl || !recordBtn || !stopBtn) return;

        mediaRecorder.ondataavailable = (event: BlobEvent) => {
            if (event.data) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            const audioUrl = URL.createObjectURL(audioBlob);
            const playerEl = document.getElementById(`player-${recordingId}`);
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
        stopBtn.style.display = "inline-block";
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        addMessage(`Error accessing microphone: ${errorMessage}`, "error");
    }
}

function stopRecording(recordingId: string): void {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach((track) => track.stop());

        const widgetEl = document.getElementById(`recording-${recordingId}`);
        if (!widgetEl) return;

        const stopBtn = widgetEl.querySelector(".stop-btn") as HTMLButtonElement;
        const recordBtn = widgetEl.querySelector(".record-btn") as HTMLButtonElement;

        if (recordBtn && stopBtn) {
            recordBtn.style.display = "inline-block";
            stopBtn.style.display = "none";
        }
    }
}

async function sendRecording(recordingId: string): Promise<void> {
    if (audioChunks.length === 0) {
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

    const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
    const formData = new FormData();
    formData.append("file", audioBlob, "recording.wav");
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

        audioChunks = [];
        mediaRecorder = null;
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
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach((track) => track.stop());
    }
    removeRecordingWidget(recordingId);
    audioChunks = [];
    mediaRecorder = null;

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
            JSON.stringify({
                type: "cancel_recording",
                recording_id: recordingId,
            })
        );
    }
}
