import { PracticeTimerState } from "../types";
import { addMessage } from "../ui";

const messagesEl = document.getElementById("messages") as HTMLElement;
const practiceTimers = new Map<string, PracticeTimerState>();

export function addPracticeTimerWidget(
    timerId: string,
    durationMinutes?: number,
    goal?: string,
    breakIntervalMinutes?: number,
    description?: string
): void {
    const widgetEl = document.createElement("div");
    widgetEl.className = "practice-timer-widget";
    widgetEl.id = `timer-${timerId}`;
    widgetEl.innerHTML = `
        <h3>Practice Timer</h3>
        ${description ? `<div class="description">${description}</div>` : ""}
        ${goal ? `<div class="timer-goal">Goal: ${goal}</div>` : ""}
        <div class="practice-timer-display">
            <div class="timer-time" id="time-${timerId}">00:00</div>
            ${durationMinutes ? `<div style="color: #c2185b;">Target: ${durationMinutes} minutes</div>` : ""}
        </div>
        <div class="practice-timer-controls">
            <button class="start-btn" data-timer-id="${timerId}">Start</button>
            <button class="pause-btn" data-timer-id="${timerId}" style="display:none;">Pause</button>
            <button class="stop-btn" data-timer-id="${timerId}">Stop</button>
            <span class="practice-timer-status" id="status-${timerId}">Stopped</span>
        </div>
    `;
    messagesEl.appendChild(widgetEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    const startBtn = widgetEl.querySelector(".start-btn");
    const pauseBtn = widgetEl.querySelector(".pause-btn");
    const stopBtn = widgetEl.querySelector(".stop-btn");
    startBtn?.addEventListener("click", () =>
        startPracticeTimer(timerId, durationMinutes, breakIntervalMinutes)
    );
    pauseBtn?.addEventListener("click", () => pausePracticeTimer(timerId));
    stopBtn?.addEventListener("click", () => stopPracticeTimer(timerId));
    practiceTimers.set(timerId, {
        durationMinutes: durationMinutes || null,
        goal: goal || null,
        breakIntervalMinutes: breakIntervalMinutes || null,
        widgetEl,
        startTime: null,
        pausedTime: 0,
        elapsedSeconds: 0,
        intervalId: null,
        breakIntervalId: null,
        isRunning: false,
    });
}

function startPracticeTimer(
    timerId: string,
    durationMinutes?: number,
    breakIntervalMinutes?: number
): void {
    const timer = practiceTimers.get(timerId);
    if (!timer || timer.isRunning) return;
    const startTime = Date.now() - (timer.pausedTime || 0) * 1000;
    timer.startTime = startTime;
    timer.isRunning = true;
    const widgetEl = timer.widgetEl;
    const startBtn = widgetEl.querySelector(".start-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${timerId}`);
    if (startBtn) startBtn.style.display = "none";
    if (pauseBtn) pauseBtn.style.display = "inline-block";
    if (statusEl) {
        statusEl.textContent = "Running";
        statusEl.className = "practice-timer-status";
    }
    function updateTimer(): void {
        const currentTimer = practiceTimers.get(timerId);
        if (!currentTimer || !currentTimer.isRunning || !currentTimer.startTime) return;
        const elapsed = Math.floor((Date.now() - currentTimer.startTime) / 1000);
        currentTimer.elapsedSeconds = elapsed;
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        const timeEl = document.getElementById(`time-${timerId}`);
        if (timeEl) {
            timeEl.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
        }
        if (durationMinutes && elapsed >= durationMinutes * 60) {
            stopPracticeTimer(timerId);
            if (statusEl) {
                statusEl.textContent = "Complete!";
                statusEl.className = "practice-timer-status";
            }
            addMessage("Practice session complete!", "assistant");
        }
    }
    timer.intervalId = window.setInterval(updateTimer, 1000);
    updateTimer();
    if (breakIntervalMinutes) {
        timer.breakIntervalId = window.setInterval(
            () => {
                addMessage(
                    `Break reminder: You've been practicing for ${breakIntervalMinutes} minutes. Consider taking a short break!`,
                    "assistant"
                );
            },
            breakIntervalMinutes * 60 * 1000
        );
    }
}

function pausePracticeTimer(timerId: string): void {
    const timer = practiceTimers.get(timerId);
    if (!timer || !timer.isRunning) return;
    timer.pausedTime = timer.elapsedSeconds;
    timer.isRunning = false;
    if (timer.intervalId) {
        clearInterval(timer.intervalId);
        timer.intervalId = null;
    }
    if (timer.breakIntervalId) {
        clearInterval(timer.breakIntervalId);
        timer.breakIntervalId = null;
    }
    const widgetEl = timer.widgetEl;
    const startBtn = widgetEl.querySelector(".start-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${timerId}`);
    if (startBtn) startBtn.style.display = "inline-block";
    if (pauseBtn) pauseBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Paused";
        statusEl.className = "practice-timer-status";
    }
}

function stopPracticeTimer(timerId: string): void {
    const timer = practiceTimers.get(timerId);
    if (!timer) return;
    timer.isRunning = false;
    timer.startTime = null;
    timer.pausedTime = 0;
    timer.elapsedSeconds = 0;
    if (timer.intervalId) {
        clearInterval(timer.intervalId);
        timer.intervalId = null;
    }
    if (timer.breakIntervalId) {
        clearInterval(timer.breakIntervalId);
        timer.breakIntervalId = null;
    }
    const widgetEl = timer.widgetEl;
    const startBtn = widgetEl.querySelector(".start-btn") as HTMLButtonElement;
    const pauseBtn = widgetEl.querySelector(".pause-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${timerId}`);
    const timeEl = document.getElementById(`time-${timerId}`);
    if (startBtn) startBtn.style.display = "inline-block";
    if (pauseBtn) pauseBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Stopped";
        statusEl.className = "practice-timer-status";
    }
    if (timeEl) timeEl.textContent = "00:00";
}
