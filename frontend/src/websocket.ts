import { WebSocketMessage } from "./types.js";
import { sanitizeToolId } from "./utils/sanitize.js";
import {
    clampBpm,
    validateTimeSignature,
    positiveNumber,
    optionalPositiveNumber,
    validateNoteName,
} from "./utils/validate.js";
import { WS_URL } from "./config.js";
import {
    addMessage,
    addTypingIndicator,
    removeTypingIndicator,
    updateStatus,
    startStreamingMessage,
    appendStreamingToken,
    addThinkingToStreamingMessage,
    finishStreamingMessage,
} from "./ui.js";
import {
    addRecordingWidget,
    removeRecordingWidget,
    setWebSocket,
    setSessionId,
} from "./widgets/recording.js";
import {
    addMetronomeWidget,
    setMetronomeWebSocket,
    setMetronomeSessionId,
} from "./widgets/metronome.js";
import { addTunerWidget } from "./widgets/tuner.js";
import { addChordProgressionWidget } from "./widgets/chordProgression.js";
import { addTempoTrainerWidget } from "./widgets/tempoTrainer.js";
import { addEarTrainerWidget } from "./widgets/earTrainer.js";
import { addPracticeTimerWidget } from "./widgets/practiceTimer.js";

let ws: WebSocket | null = null;
let sessionId: string | null = null;
let isProcessing = false;
let reconnectAttempts = 0;
let reconnectTimeout: number | null = null;

export function connect(): void {
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }

    updateStatus("Connecting...", "disconnected");
    ws = new WebSocket(WS_URL);
    setWebSocket(ws);
    setMetronomeWebSocket(ws);

    ws.onopen = () => {
        reconnectAttempts = 0;
        updateStatus("Connected", "connected");
        const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
        if (sendButton) {
            sendButton.disabled = false;
        }
        ws!.send(JSON.stringify({ type: "connect", session_id: sessionId }));
    };

    ws.onmessage = (event: MessageEvent) => {
        try {
            const data = JSON.parse(event.data as string) as WebSocketMessage;

            if (data.session_id) {
                sessionId = data.session_id;
                setSessionId(sessionId);
                setMetronomeSessionId(sessionId);
            }

            if (data.type === "session_id") {
                // Session ID chunk, continue processing
                return;
            }

            if (data.type === "token") {
                // Streaming token
                if (!isProcessing) {
                    startStreamingMessage("assistant");
                    isProcessing = true;
                }
                appendStreamingToken(data.content || "");
                return;
            }

            if (data.type === "thinking") {
                addThinkingToStreamingMessage(data.content || "");
                return;
            }

            // Handle tool calls during streaming
            let justFinishedStreaming = false;
            if (data.type === "tool_call") {
                if (isProcessing) {
                    finishStreamingMessage();
                    isProcessing = false;
                }
                // Continue to tool call handling below
            } else {
                // Non-streaming message or end of stream
                if (isProcessing && (data.type === "response" || data.type === "error")) {
                    finishStreamingMessage(data);
                    isProcessing = false;
                    justFinishedStreaming = true;
                    removeTypingIndicator();
                } else {
                    removeTypingIndicator();
                    isProcessing = false;
                }
            }

            if (data.type === "response" && !justFinishedStreaming) {
                addMessage(data.message || "", "assistant", data);
            } else if (data.type === "tool_call" && data.tool_name === "request_audio_recording") {
                if (data.message) {
                    addMessage(data.message, "assistant", data);
                }
                const args = (data.arguments || {}) as {
                    prompt?: string;
                    max_duration?: number;
                };
                addRecordingWidget(
                    sanitizeToolId(data.tool_id, "rec"),
                    args.prompt || "Please record audio",
                    Math.min(positiveNumber(args.max_duration, 60.0), 600)
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_metronome") {
                if (data.message) {
                    addMessage(data.message, "assistant", data);
                }
                const args = (data.arguments || {}) as {
                    bpm?: number;
                    time_signature?: string;
                    description?: string;
                };
                addMetronomeWidget(
                    sanitizeToolId(data.tool_id, "met"),
                    clampBpm(args.bpm, 120),
                    validateTimeSignature(args.time_signature),
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_tuner") {
                if (data.message) {
                    addMessage(data.message, "assistant", data);
                }
                const args = (data.arguments || {}) as {
                    reference_frequency?: number;
                    note?: string;
                    octave?: number;
                    description?: string;
                };
                addTunerWidget(
                    sanitizeToolId(data.tool_id, "tuner"),
                    positiveNumber(args.reference_frequency, 440),
                    args.note,
                    args.octave,
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_chord_progression") {
                if (data.message) {
                    addMessage(data.message, "assistant", data);
                }
                const args = (data.arguments || {}) as {
                    chords?: string[];
                    tempo?: number;
                    time_signature?: string;
                    chords_per_bar?: number;
                    instrument?: string;
                    description?: string;
                };
                const chords = Array.isArray(args.chords)
                    ? args.chords.filter((chord): chord is string => typeof chord === "string")
                    : [];
                addChordProgressionWidget(
                    sanitizeToolId(data.tool_id, "chord"),
                    chords,
                    clampBpm(args.tempo, 120),
                    validateTimeSignature(args.time_signature),
                    positiveNumber(args.chords_per_bar, 1),
                    args.instrument || "piano",
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_tempo_trainer") {
                if (data.message) {
                    addMessage(data.message, "assistant", data);
                }
                const args = (data.arguments || {}) as {
                    start_bpm?: number;
                    end_bpm?: number;
                    duration_minutes?: number;
                    time_signature?: string;
                    ramp_type?: string;
                    description?: string;
                };
                let startBpm = clampBpm(args.start_bpm, 60);
                let endBpm = clampBpm(args.end_bpm, 120);
                if (startBpm > endBpm) {
                    [startBpm, endBpm] = [endBpm, startBpm];
                }
                addTempoTrainerWidget(
                    sanitizeToolId(data.tool_id, "tempo"),
                    startBpm,
                    endBpm,
                    positiveNumber(args.duration_minutes, 5),
                    validateTimeSignature(args.time_signature),
                    args.ramp_type || "linear",
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_ear_trainer") {
                if (data.message) {
                    addMessage(data.message, "assistant", data);
                }
                const args = (data.arguments || {}) as {
                    mode?: string;
                    difficulty?: string;
                    root_note?: string;
                    description?: string;
                };
                addEarTrainerWidget(
                    sanitizeToolId(data.tool_id, "ear"),
                    args.mode || "intervals",
                    args.difficulty || "medium",
                    validateNoteName(args.root_note),
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_practice_timer") {
                if (data.message) {
                    addMessage(data.message, "assistant", data);
                }
                const args = (data.arguments || {}) as {
                    duration_minutes?: number;
                    goal?: string;
                    break_interval_minutes?: number;
                    description?: string;
                };
                addPracticeTimerWidget(
                    sanitizeToolId(data.tool_id, "timer"),
                    optionalPositiveNumber(args.duration_minutes),
                    args.goal,
                    optionalPositiveNumber(args.break_interval_minutes),
                    args.description
                );
            } else if (data.type === "audio_result" && data.audio_file_id) {
                addMessage("", "assistant", data);
            } else if (data.type === "notation_result" && (data.notation_url || data.tabs_url)) {
                addMessage("", "assistant", data);
            } else if (data.type === "recording_cancelled") {
                const recordingId = data.tool_id || "";
                removeRecordingWidget(recordingId);
                addMessage("Recording cancelled", "assistant");
            } else if (data.type === "error") {
                addMessage(`Error: ${data.message || "Unknown error"}`, "error");
            }
        } catch (error) {
            console.error("Error parsing WebSocket message:", error);
            addMessage("Error processing message from server", "error");
        }
    };

    ws.onerror = (error: Event) => {
        updateStatus("Connection error", "disconnected");
        console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
        // A disconnect mid-stream would otherwise leave isProcessing stuck at
        // true forever, permanently blocking sendMessage after reconnect.
        finishStreamingMessage();
        removeTypingIndicator();
        isProcessing = false;

        updateStatus("Disconnected", "disconnected");
        const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
        if (sendButton) {
            sendButton.disabled = true;
        }

        reconnectAttempts++;
        const delay = Math.min(3000 * reconnectAttempts, 30000);
        updateStatus(`Disconnected. Reconnecting in ${delay / 1000}s...`, "disconnected");

        reconnectTimeout = window.setTimeout(() => {
            connect();
        }, delay);
    };
}

export function sendMessage(message: string, stream: boolean = true): boolean {
    if (ws && ws.readyState === WebSocket.OPEN && !isProcessing) {
        isProcessing = true;
        if (stream) {
            startStreamingMessage("assistant");
        } else {
            addTypingIndicator();
        }
        ws.send(
            JSON.stringify({
                type: "message",
                message: message,
                session_id: sessionId,
                stream: stream,
            })
        );
        return true;
    }
    return false;
}

export function getIsProcessing(): boolean {
    return isProcessing;
}

export function reset(): void {
    ws = null;
    sessionId = null;
    isProcessing = false;
    reconnectAttempts = 0;
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }
}
