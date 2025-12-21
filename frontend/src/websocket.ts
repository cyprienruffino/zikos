import { WebSocketMessage } from "./types.js";
import { WS_URL } from "./config.js";
import { addMessage, addTypingIndicator, removeTypingIndicator, updateStatus } from "./ui.js";
import {
    addRecordingWidget,
    removeRecordingWidget,
    setWebSocket,
    setSessionId,
} from "./widgets/recording.js";
import { addMetronomeWidget } from "./widgets/metronome.js";
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

    ws.onopen = () => {
        reconnectAttempts = 0;
        updateStatus("Connected", "connected");
        const sendButton = document.getElementById("sendButton") as HTMLButtonElement;
        if (sendButton) {
            sendButton.disabled = false;
        }
    };

    ws.onmessage = (event: MessageEvent) => {
        removeTypingIndicator();
        isProcessing = false;

        try {
            const data = JSON.parse(event.data as string) as WebSocketMessage;

            if (data.session_id) {
                sessionId = data.session_id;
                setSessionId(sessionId);
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
            } else if (data.type === "tool_call" && data.tool_name === "create_metronome") {
                const args = (data.arguments || {}) as {
                    bpm?: number;
                    time_signature?: string;
                    description?: string;
                };
                addMetronomeWidget(
                    data.tool_id || `met_${Date.now()}`,
                    args.bpm || 120,
                    args.time_signature || "4/4",
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_tuner") {
                const args = (data.arguments || {}) as {
                    reference_frequency?: number;
                    note?: string;
                    octave?: number;
                    description?: string;
                };
                addTunerWidget(
                    data.tool_id || `tuner_${Date.now()}`,
                    args.reference_frequency || 440,
                    args.note,
                    args.octave,
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_chord_progression") {
                const args = (data.arguments || {}) as {
                    chords?: string[];
                    tempo?: number;
                    time_signature?: string;
                    chords_per_bar?: number;
                    instrument?: string;
                    description?: string;
                };
                addChordProgressionWidget(
                    data.tool_id || `chord_${Date.now()}`,
                    args.chords || [],
                    args.tempo || 120,
                    args.time_signature || "4/4",
                    args.chords_per_bar || 1,
                    args.instrument || "piano",
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_tempo_trainer") {
                const args = (data.arguments || {}) as {
                    start_bpm?: number;
                    end_bpm?: number;
                    duration_minutes?: number;
                    time_signature?: string;
                    ramp_type?: string;
                    description?: string;
                };
                addTempoTrainerWidget(
                    data.tool_id || `tempo_${Date.now()}`,
                    args.start_bpm || 60,
                    args.end_bpm || 120,
                    args.duration_minutes || 5,
                    args.time_signature || "4/4",
                    args.ramp_type || "linear",
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_ear_trainer") {
                const args = (data.arguments || {}) as {
                    mode?: string;
                    difficulty?: string;
                    root_note?: string;
                    description?: string;
                };
                addEarTrainerWidget(
                    data.tool_id || `ear_${Date.now()}`,
                    args.mode || "intervals",
                    args.difficulty || "medium",
                    args.root_note || "C",
                    args.description
                );
            } else if (data.type === "tool_call" && data.tool_name === "create_practice_timer") {
                const args = (data.arguments || {}) as {
                    duration_minutes?: number;
                    goal?: string;
                    break_interval_minutes?: number;
                    description?: string;
                };
                addPracticeTimerWidget(
                    data.tool_id || `timer_${Date.now()}`,
                    args.duration_minutes,
                    args.goal,
                    args.break_interval_minutes,
                    args.description
                );
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

export function sendMessage(message: string): boolean {
    if (ws && ws.readyState === WebSocket.OPEN && !isProcessing) {
        isProcessing = true;
        addTypingIndicator();
        ws.send(
            JSON.stringify({
                type: "message",
                message: message,
                session_id: sessionId,
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
