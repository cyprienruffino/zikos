const API_URL = window.location.origin;
const WS_URL = API_URL.replace("http", "ws") + "/api/chat/ws";

interface WebSocketMessage {
    type: string;
    message?: string;
    session_id?: string;
    tool_name?: string;
    tool_id?: string;
    arguments?: Record<string, unknown>;
    audio_file_id?: string;
    notation_url?: string;
}

let ws: WebSocket | null = null;
let sessionId: string | null = null;
let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

const statusEl = document.getElementById("status") as HTMLElement;
const messagesEl = document.getElementById("messages") as HTMLElement;
const messageInput = document.getElementById("messageInput") as HTMLInputElement;
const sendButton = document.getElementById("sendButton") as HTMLButtonElement;

function updateStatus(text: string, className: string): void {
    if (statusEl) {
        statusEl.textContent = text;
        statusEl.className = `status ${className}`;
    }
}

function addMessage(
    text: string,
    type: string = "assistant",
    data: Partial<WebSocketMessage> | null = null
): void {
    const messageEl = document.createElement("div");
    messageEl.className = `message ${type}`;

    const textEl = document.createElement("div");
    textEl.textContent = text;
    messageEl.appendChild(textEl);

    if (data?.audio_file_id) {
        const audioEl = document.createElement("div");
        audioEl.className = "audio-player";
        audioEl.innerHTML = `<audio controls src="${API_URL}/api/audio/${data.audio_file_id}"></audio>`;
        messageEl.appendChild(audioEl);
    }

    if (data?.notation_url) {
        const notationEl = document.createElement("div");
        notationEl.className = "notation";
        notationEl.innerHTML = `<img src="${data.notation_url}" alt="Musical notation" />`;
        messageEl.appendChild(notationEl);
    }

    messagesEl.appendChild(messageEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addRecordingWidget(recordingId: string, prompt: string, _maxDuration: number): void {
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

function removeRecordingWidget(recordingId: string): void {
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

    const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
    const formData = new FormData();
    formData.append("file", audioBlob, "recording.wav");
    formData.append("recording_id", recordingId);

    try {
        const response = await fetch(`${API_URL}/api/audio/upload`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        const data = (await response.json()) as { audio_file_id: string };
        removeRecordingWidget(recordingId);

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(
                JSON.stringify({
                    type: "audio_ready",
                    audio_file_id: data.audio_file_id,
                    recording_id: recordingId,
                    session_id: sessionId,
                })
            );
        }

        audioChunks = [];
        mediaRecorder = null;
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        addMessage(`Error uploading audio: ${errorMessage}`, "error");
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

function connect(): void {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        updateStatus("Connected", "connected");
        if (sendButton) {
            sendButton.disabled = false;
        }
    };

    ws.onmessage = (event: MessageEvent) => {
        const data = JSON.parse(event.data as string) as WebSocketMessage;

        if (data.session_id) {
            sessionId = data.session_id;
        }

        if (data.type === "response") {
            addMessage(data.message || "", "assistant", data);
        } else if (data.type === "tool_call" && data.tool_name === "request_audio_recording") {
            const args = (data.arguments || {}) as {
                prompt?: string;
                max_duration?: number;
            };
            addRecordingWidget(
                data.tool_id || `rec_${Date.now()}`,
                args.prompt || "Please record audio",
                args.max_duration || 60.0
            );
        } else if (data.type === "error") {
            addMessage(`Error: ${data.message || "Unknown error"}`, "error");
        }
    };

    ws.onerror = (error: Event) => {
        updateStatus("Connection error", "disconnected");
        console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
        updateStatus("Disconnected", "disconnected");
        if (sendButton) {
            sendButton.disabled = true;
        }
        setTimeout(connect, 3000);
    };
}

if (sendButton) {
    sendButton.addEventListener("click", () => {
        const message = messageInput?.value.trim();
        if (message && ws && ws.readyState === WebSocket.OPEN) {
            addMessage(message, "user");
            ws.send(
                JSON.stringify({
                    type: "message",
                    message: message,
                    session_id: sessionId,
                })
            );
            if (messageInput) {
                messageInput.value = "";
            }
        }
    });
}

if (messageInput) {
    messageInput.addEventListener("keypress", (e: KeyboardEvent) => {
        if (e.key === "Enter") {
            sendButton?.click();
        }
    });
}

connect();
