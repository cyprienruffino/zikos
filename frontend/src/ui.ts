import { WebSocketMessage } from "./types.js";
import { API_URL } from "./config.js";

function getMessagesEl(): HTMLElement {
    const el = document.getElementById("messages");
    if (!el) {
        throw new Error("Messages element not found");
    }
    return el as HTMLElement;
}

export function addMessage(
    text: string,
    type: string = "assistant",
    data: Partial<WebSocketMessage> | null = null
): void {
    const messageEl = document.createElement("div");
    messageEl.className = `message ${type}`;

    const textEl = document.createElement("div");
    textEl.className = "message-text";
    textEl.innerHTML = text.replace(/\n/g, "<br>");
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

    const messagesEl = getMessagesEl();
    messagesEl.appendChild(messageEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

export function addTypingIndicator(): void {
    const existingIndicator = document.getElementById("typing-indicator");
    if (existingIndicator) {
        return;
    }

    const indicatorEl = document.createElement("div");
    indicatorEl.id = "typing-indicator";
    indicatorEl.className = "message assistant typing-indicator";
    indicatorEl.innerHTML =
        '<div class="typing-dots"><span></span><span></span><span></span></div>';
    const messagesEl = getMessagesEl();
    messagesEl.appendChild(indicatorEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

export function removeTypingIndicator(): void {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) {
        indicator.remove();
    }
}

export function updateStatus(text: string, className: string): void {
    const statusEl = document.getElementById("status");
    if (statusEl) {
        statusEl.textContent = text;
        statusEl.className = `status ${className}`;
    }
}

let streamingMessageEl: HTMLElement | null = null;
let streamingTextEl: HTMLElement | null = null;
let streamingContent: string = "";

export function startStreamingMessage(type: string = "assistant"): void {
    removeTypingIndicator();
    streamingMessageEl = document.createElement("div");
    streamingMessageEl.className = `message ${type}`;

    streamingTextEl = document.createElement("div");
    streamingTextEl.className = "message-text";
    streamingMessageEl.appendChild(streamingTextEl);

    const messagesEl = getMessagesEl();
    messagesEl.appendChild(streamingMessageEl);
    streamingContent = "";
}

export function appendStreamingToken(token: string): void {
    if (streamingTextEl) {
        streamingContent += token;
        streamingTextEl.innerHTML = streamingContent.replace(/\n/g, "<br>");
        const messagesEl = getMessagesEl();
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

export function finishStreamingMessage(data: Partial<WebSocketMessage> | null = null): void {
    if (streamingMessageEl && streamingTextEl) {
        if (data?.audio_file_id) {
            const audioEl = document.createElement("div");
            audioEl.className = "audio-player";
            audioEl.innerHTML = `<audio controls src="${API_URL}/api/audio/${data.audio_file_id}"></audio>`;
            streamingMessageEl.appendChild(audioEl);
        }

        if (data?.notation_url) {
            const notationEl = document.createElement("div");
            notationEl.className = "notation";
            notationEl.innerHTML = `<img src="${data.notation_url}" alt="Musical notation" />`;
            streamingMessageEl.appendChild(notationEl);
        }
    }

    streamingMessageEl = null;
    streamingTextEl = null;
    streamingContent = "";
}
