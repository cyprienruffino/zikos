import { WebSocketMessage } from "./types.js";
import { API_URL } from "./config.js";

function getMessagesEl(): HTMLElement {
    const el = document.getElementById("messages");
    if (!el) {
        throw new Error("Messages element not found");
    }
    return el as HTMLElement;
}

/** Build media attachments (audio player, notation images) via DOM APIs so
 *  server-supplied ids/urls are never parsed as HTML. */
function appendMediaElements(container: HTMLElement, data: Partial<WebSocketMessage>): void {
    if (data.audio_file_id) {
        const audioWrap = document.createElement("div");
        audioWrap.className = "audio-player";
        const audio = document.createElement("audio");
        audio.controls = true;
        audio.src = `${API_URL}/api/audio/${encodeURIComponent(data.audio_file_id)}`;
        audioWrap.appendChild(audio);
        container.appendChild(audioWrap);
    }

    if (data.notation_url) {
        const notationEl = document.createElement("div");
        notationEl.className = "notation";
        const img = document.createElement("img");
        img.src = data.notation_url;
        img.alt = "Musical notation";
        notationEl.appendChild(img);
        container.appendChild(notationEl);
    }

    if (data.tabs_url) {
        const tabsEl = document.createElement("div");
        tabsEl.className = "notation";
        const img = document.createElement("img");
        img.src = data.tabs_url;
        img.alt = "Tablature";
        tabsEl.appendChild(img);
        container.appendChild(tabsEl);
    }
}

export function addMessage(
    text: string,
    type: string = "assistant",
    data: Partial<WebSocketMessage> | null = null
): HTMLElement {
    const messageEl = document.createElement("div");
    messageEl.className = `message ${type}`;

    const textEl = document.createElement("div");
    textEl.className = "message-text";
    // Rendered as plain text; newlines are preserved via CSS white-space: pre-wrap.
    textEl.textContent = text;
    messageEl.appendChild(textEl);

    if (data) {
        appendMediaElements(messageEl, data);
    }

    const messagesEl = getMessagesEl();
    messagesEl.appendChild(messageEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return messageEl;
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
        // Append as a text node; newlines are preserved via CSS white-space: pre-wrap.
        streamingTextEl.appendChild(document.createTextNode(token));
        const messagesEl = getMessagesEl();
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
}

export function addThinkingToStreamingMessage(thinking: string): void {
    if (streamingMessageEl) {
        const details = document.createElement("details");
        details.className = "thinking-section";
        const summary = document.createElement("summary");
        summary.textContent = "Thinking";
        details.appendChild(summary);
        const content = document.createElement("div");
        content.className = "thinking-content";
        content.textContent = thinking;
        details.appendChild(content);
        streamingMessageEl.insertBefore(details, streamingTextEl);
    }
}

export function finishStreamingMessage(data: Partial<WebSocketMessage> | null = null): void {
    if (streamingMessageEl && streamingTextEl && data) {
        appendMediaElements(streamingMessageEl, data);
    }

    streamingMessageEl = null;
    streamingTextEl = null;
    streamingContent = "";
}
