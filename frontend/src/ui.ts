import { WebSocketMessage } from "./types.js";
import { API_URL } from "./config.js";
import { getMessagesEl } from "./dom.js";

const NEAR_BOTTOM_PX = 120;

/** Autoscroll only when the user is already near the bottom, so reading
 *  scrollback is not hijacked by incoming tokens. */
function autoScroll(el: HTMLElement): void {
    if (el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX) {
        el.scrollTop = el.scrollHeight;
    }
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
    autoScroll(messagesEl);
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
let thinkingContentEl: HTMLElement | null = null;
// Thinking frames can arrive before the first token; buffer them until the
// streaming bubble exists.
let pendingThinking: string = "";

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
    thinkingContentEl = null;

    if (pendingThinking) {
        const buffered = pendingThinking;
        pendingThinking = "";
        appendThinking(buffered);
    }
}

export function appendStreamingToken(token: string): void {
    if (streamingTextEl) {
        streamingContent += token;
        // Append as a text node; newlines are preserved via CSS white-space: pre-wrap.
        streamingTextEl.appendChild(document.createTextNode(token));
        autoScroll(getMessagesEl());
    }
}

/** Append thinking text to the bubble's single <details> section. */
function appendThinking(thinking: string): void {
    if (!streamingMessageEl) return;
    if (!thinkingContentEl) {
        const details = document.createElement("details");
        details.className = "thinking-section";
        const summary = document.createElement("summary");
        summary.textContent = "Thinking";
        details.appendChild(summary);
        thinkingContentEl = document.createElement("div");
        thinkingContentEl.className = "thinking-content";
        details.appendChild(thinkingContentEl);
        streamingMessageEl.insertBefore(details, streamingTextEl);
    }
    thinkingContentEl.appendChild(document.createTextNode(thinking));
}

export function addThinkingToStreamingMessage(thinking: string): void {
    if (!streamingMessageEl) {
        pendingThinking += thinking;
        return;
    }
    appendThinking(thinking);
}

export function finishStreamingMessage(data: Partial<WebSocketMessage> | null = null): void {
    if (streamingMessageEl && streamingTextEl) {
        // If the final message differs from the accumulated tokens (e.g. the
        // server post-processed the response), prefer the final message.
        if (data?.message && data.message !== streamingContent) {
            streamingTextEl.textContent = data.message;
        }
        if (data) {
            appendMediaElements(streamingMessageEl, data);
        }
    }

    streamingMessageEl = null;
    streamingTextEl = null;
    streamingContent = "";
    thinkingContentEl = null;
    pendingThinking = "";
}
