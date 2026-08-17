import { TempoTrainerState } from "../types.js";
import { escapeHtml, sanitizeToolId } from "../utils/sanitize.js";
import { clampBpm, positiveNumber, validateTimeSignature } from "../utils/validate.js";
import { createBeatScheduler } from "./audioEngine.js";

function getMessagesEl(): HTMLElement {
    const el = document.getElementById("messages");
    if (!el) {
        throw new Error("Messages element not found");
    }
    return el as HTMLElement;
}

const tempoTrainers = new Map<string, TempoTrainerState>();

export function addTempoTrainerWidget(
    trainerId: string,
    startBpm: number,
    endBpm: number,
    durationMinutes: number,
    timeSignature: string,
    rampType: string,
    description?: string
): void {
    trainerId = sanitizeToolId(trainerId, "tempo");
    startBpm = clampBpm(startBpm, 60);
    endBpm = clampBpm(endBpm, 120);
    if (startBpm > endBpm) {
        [startBpm, endBpm] = [endBpm, startBpm];
    }
    durationMinutes = positiveNumber(durationMinutes, 5);
    timeSignature = validateTimeSignature(timeSignature);
    const widgetEl = document.createElement("div");
    widgetEl.className = "tempo-trainer-widget";
    widgetEl.id = `tempo-${trainerId}`;
    widgetEl.innerHTML = `
        <h3>Tempo Trainer</h3>
        ${description ? `<div class="description">${escapeHtml(description)}</div>` : ""}
        <div class="tempo-display" id="tempo-display-${trainerId}">${escapeHtml(startBpm)} BPM</div>
        <div class="tempo-trainer-progress">
            <div class="progress-bar">
                <div class="progress-fill" id="progress-${trainerId}" style="width: 0%;"></div>
            </div>
            <div style="margin-top: 0.5rem; color: #e65100; text-align: center;">
                ${escapeHtml(startBpm)} → ${escapeHtml(endBpm)} BPM over ${escapeHtml(durationMinutes)} minutes
            </div>
        </div>
        <div class="tempo-trainer-controls">
            <button class="play-btn" data-trainer-id="${trainerId}">Start</button>
            <button class="pause-btn" data-trainer-id="${trainerId}" style="display:none;">Pause</button>
            <button class="stop-btn" data-trainer-id="${trainerId}">Stop</button>
            <span class="tempo-trainer-status" id="status-${trainerId}">Stopped</span>
        </div>
    `;
    const messagesEl = getMessagesEl();
    messagesEl.appendChild(widgetEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    const playBtn = widgetEl.querySelector(".play-btn");
    const pauseBtn = widgetEl.querySelector(".pause-btn");
    const stopBtn = widgetEl.querySelector(".stop-btn");
    playBtn?.addEventListener("click", () =>
        startTempoTrainer(trainerId, startBpm, endBpm, durationMinutes, timeSignature, rampType)
    );
    pauseBtn?.addEventListener("click", () => pauseTempoTrainer(trainerId));
    stopBtn?.addEventListener("click", () => stopTempoTrainer(trainerId));
    tempoTrainers.set(trainerId, {
        startBpm,
        endBpm,
        durationMinutes,
        timeSignature,
        rampType,
        widgetEl,
        scheduler: null,
        startTime: null,
        pausedTime: 0,
        isPlaying: false,
    });
}

function startTempoTrainer(
    trainerId: string,
    startBpm: number,
    endBpm: number,
    durationMinutes: number,
    timeSignature: string,
    rampType: string
): void {
    const trainer = tempoTrainers.get(trainerId);
    if (!trainer || trainer.isPlaying) return;
    const startTime = Date.now() - trainer.pausedTime;
    trainer.startTime = startTime;
    trainer.isPlaying = true;
    const widgetEl = trainer.widgetEl;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${trainerId}`);
    if (playBtn) playBtn.style.display = "none";
    if (pauseBtn) pauseBtn.style.display = "inline-block";
    if (statusEl) {
        statusEl.textContent = "Training...";
        statusEl.className = "tempo-trainer-status";
    }
    const [beats] = timeSignature.split("/").map(Number);
    // One scheduler for the whole ramp; the tempo is adjusted in place
    // instead of tearing intervals down per 0.5 BPM step.
    if (!trainer.scheduler) {
        trainer.scheduler = createBeatScheduler({ bpm: startBpm, beats });
    }
    trainer.scheduler.start();
    function updateTempo(): void {
        const currentTrainer = tempoTrainers.get(trainerId);
        if (!currentTrainer || !currentTrainer.isPlaying || !currentTrainer.startTime) return;
        const elapsed = (Date.now() - currentTrainer.startTime) / 1000 / 60;
        const progress = Math.min(1, elapsed / durationMinutes);
        let currentBpm: number;
        if (rampType === "exponential") {
            const ratio = Math.pow(endBpm / startBpm, progress);
            currentBpm = startBpm * ratio;
        } else {
            currentBpm = startBpm + (endBpm - startBpm) * progress;
        }
        const tempoDisplay = document.getElementById(`tempo-display-${trainerId}`);
        const progressFill = document.getElementById(`progress-${trainerId}`);
        if (tempoDisplay) tempoDisplay.textContent = `${currentBpm.toFixed(1)} BPM`;
        if (progressFill) progressFill.style.width = `${progress * 100}%`;
        currentTrainer.scheduler?.setBpm(currentBpm);
        if (progress >= 1) {
            stopTempoTrainer(trainerId);
            if (statusEl) {
                statusEl.textContent = "Complete!";
                statusEl.className = "tempo-trainer-status";
            }
        } else {
            setTimeout(updateTempo, 100);
        }
    }
    updateTempo();
}

function pauseTempoTrainer(trainerId: string): void {
    const trainer = tempoTrainers.get(trainerId);
    if (!trainer || !trainer.isPlaying || !trainer.startTime) return;
    trainer.pausedTime = Date.now() - trainer.startTime;
    trainer.isPlaying = false;
    trainer.scheduler?.stop();
    const widgetEl = trainer.widgetEl;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${trainerId}`);
    if (playBtn) playBtn.style.display = "inline-block";
    if (pauseBtn) pauseBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Paused";
        statusEl.className = "tempo-trainer-status";
    }
}

function stopTempoTrainer(trainerId: string): void {
    const trainer = tempoTrainers.get(trainerId);
    if (!trainer) return;
    trainer.isPlaying = false;
    trainer.startTime = null;
    trainer.pausedTime = 0;
    if (trainer.scheduler) {
        trainer.scheduler.stop();
        trainer.scheduler.resetBeat();
        // The shared AudioContext stays open for other widgets.
        trainer.scheduler = null;
    }
    const widgetEl = trainer.widgetEl;
    const playBtn = widgetEl.querySelector(".play-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${trainerId}`);
    const progressFill = document.getElementById(`progress-${trainerId}`);
    const tempoDisplay = document.getElementById(`tempo-display-${trainerId}`);
    if (playBtn) playBtn.style.display = "inline-block";
    if (pauseBtn) pauseBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Stopped";
        statusEl.className = "tempo-trainer-status";
    }
    if (progressFill) progressFill.style.width = "0%";
    if (tempoDisplay) tempoDisplay.textContent = `${trainer.startBpm} BPM`;
}
