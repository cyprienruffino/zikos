import { TempoTrainerState } from "../types.js";

const messagesEl = document.getElementById("messages") as HTMLElement;
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
    const widgetEl = document.createElement("div");
    widgetEl.className = "tempo-trainer-widget";
    widgetEl.id = `tempo-${trainerId}`;
    widgetEl.innerHTML = `
        <h3>Tempo Trainer</h3>
        ${description ? `<div class="description">${description}</div>` : ""}
        <div class="tempo-display" id="tempo-display-${trainerId}">${startBpm} BPM</div>
        <div class="tempo-trainer-progress">
            <div class="progress-bar">
                <div class="progress-fill" id="progress-${trainerId}" style="width: 0%;"></div>
            </div>
            <div style="margin-top: 0.5rem; color: #e65100; text-align: center;">
                ${startBpm} → ${endBpm} BPM over ${durationMinutes} minutes
            </div>
        </div>
        <div class="tempo-trainer-controls">
            <button class="play-btn" data-trainer-id="${trainerId}">Start</button>
            <button class="pause-btn" data-trainer-id="${trainerId}" style="display:none;">Pause</button>
            <button class="stop-btn" data-trainer-id="${trainerId}">Stop</button>
            <span class="tempo-trainer-status" id="status-${trainerId}">Stopped</span>
        </div>
    `;
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
        metronome: null,
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
        if (
            !currentTrainer.metronome ||
            Math.abs(currentTrainer.metronome.bpm - currentBpm) > 0.5
        ) {
            if (currentTrainer.metronome && currentTrainer.metronome.intervalId) {
                clearInterval(currentTrainer.metronome.intervalId);
            }
            if (!currentTrainer.metronome || !currentTrainer.metronome.audioContext) {
                currentTrainer.metronome = {
                    bpm: currentBpm,
                    beats,
                    audioContext: new AudioContext(),
                    intervalId: null,
                    currentBeat: 0,
                };
            }
            currentTrainer.metronome.bpm = currentBpm;
            const audioContext = currentTrainer.metronome.audioContext;
            if (audioContext.state === "suspended") {
                audioContext.resume();
            }
            const intervalMs = (60 / currentBpm) * 1000;
            const playBeat = (beatIndex: number): void => {
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                const isDownbeat = beatIndex === 0;
                oscillator.frequency.value = isDownbeat ? 800 : 600;
                oscillator.type = "sine";
                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.1);
            };
            if (currentTrainer.metronome.intervalId) {
                clearInterval(currentTrainer.metronome.intervalId);
            }
            playBeat(currentTrainer.metronome.currentBeat);
            currentTrainer.metronome.intervalId = window.setInterval(() => {
                const trainerState = tempoTrainers.get(trainerId);
                if (trainerState?.metronome) {
                    trainerState.metronome.currentBeat =
                        (trainerState.metronome.currentBeat + 1) % beats;
                    playBeat(trainerState.metronome.currentBeat);
                }
            }, intervalMs);
        }
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
    if (trainer.metronome && trainer.metronome.intervalId) {
        clearInterval(trainer.metronome.intervalId);
        trainer.metronome.intervalId = null;
    }
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
    if (trainer.metronome) {
        if (trainer.metronome.intervalId) {
            clearInterval(trainer.metronome.intervalId);
        }
        if (trainer.metronome.audioContext) {
            trainer.metronome.audioContext.close();
        }
        trainer.metronome = null;
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
