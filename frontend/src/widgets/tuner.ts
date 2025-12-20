import { TunerState } from "../types.js";
import { addMessage } from "../ui.js";

const messagesEl = document.getElementById("messages") as HTMLElement;
const tuners = new Map<string, TunerState>();

export function addTunerWidget(
    tunerId: string,
    referenceFreq: number,
    note?: string,
    octave?: number,
    description?: string
): void {
    const widgetEl = document.createElement("div");
    widgetEl.className = "tuner-widget";
    widgetEl.id = `tuner-${tunerId}`;
    const noteDisplay = note && octave ? `${note}${octave}` : note || "Any";
    widgetEl.innerHTML = `
        <h3>Tuner</h3>
        ${description ? `<div class="description">${description}</div>` : ""}
        <div class="tuner-display">
            <div class="tuner-frequency" id="freq-${tunerId}">-- Hz</div>
            <div class="tuner-needle">
                <div class="tuner-needle-indicator" id="needle-${tunerId}" style="left: 50%;"></div>
            </div>
            <div class="tuner-cents" id="cents-${tunerId}">0 cents</div>
            <div style="margin-top: 0.5rem; color: #7b1fa2;">Target: ${noteDisplay} (${referenceFreq} Hz)</div>
        </div>
        <div class="tuner-controls">
            <button class="start-btn" data-tuner-id="${tunerId}">Start</button>
            <button class="stop-btn" data-tuner-id="${tunerId}" style="display:none;">Stop</button>
            <span class="tuner-status" id="status-${tunerId}">Stopped</span>
        </div>
    `;
    messagesEl.appendChild(widgetEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    const startBtn = widgetEl.querySelector(".start-btn");
    const stopBtn = widgetEl.querySelector(".stop-btn");
    startBtn?.addEventListener("click", () => startTuner(tunerId, referenceFreq));
    stopBtn?.addEventListener("click", () => stopTuner(tunerId));
    tuners.set(tunerId, {
        referenceFreq,
        widgetEl,
        analyser: null,
        microphone: null,
        audioContext: null,
        isRunning: false,
        animationFrame: null,
    });
}

function startTuner(tunerId: string, referenceFreq: number): void {
    const tuner = tuners.get(tunerId);
    if (!tuner || tuner.isRunning) return;
    navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
            if (!tuner) return;
            tuner.audioContext = new AudioContext();
            tuner.microphone = tuner.audioContext.createMediaStreamSource(stream);
            tuner.analyser = tuner.audioContext.createAnalyser();
            tuner.analyser.fftSize = 4096;
            tuner.microphone.connect(tuner.analyser);
            tuner.isRunning = true;
            const widgetEl = tuner.widgetEl;
            const startBtn = widgetEl.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widgetEl.querySelector(".stop-btn") as HTMLButtonElement;
            const statusEl = document.getElementById(`status-${tunerId}`);
            if (startBtn) startBtn.style.display = "none";
            if (stopBtn) stopBtn.style.display = "inline-block";
            if (statusEl) {
                statusEl.textContent = "Listening...";
                statusEl.className = "tuner-status";
            }
            const bufferLength = tuner.analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            function updateTuner(): void {
                if (!tuner || !tuner.isRunning || !tuner.analyser || !tuner.audioContext) return;
                tuner.analyser.getByteFrequencyData(dataArray);
                let maxIndex = 0;
                let maxValue = 0;
                for (let i = 0; i < bufferLength; i++) {
                    if (dataArray[i] > maxValue) {
                        maxValue = dataArray[i];
                        maxIndex = i;
                    }
                }
                const sampleRate = tuner.audioContext.sampleRate;
                const frequency = (maxIndex * sampleRate) / (2 * bufferLength);
                if (frequency > 80 && frequency < 2000) {
                    const freqEl = document.getElementById(`freq-${tunerId}`);
                    const centsEl = document.getElementById(`cents-${tunerId}`);
                    const needleEl = document.getElementById(`needle-${tunerId}`);
                    if (freqEl) freqEl.textContent = `${frequency.toFixed(1)} Hz`;
                    const cents = 1200 * Math.log2(frequency / referenceFreq);
                    if (centsEl)
                        centsEl.textContent = `${cents > 0 ? "+" : ""}${cents.toFixed(1)} cents`;
                    const needlePosition = Math.max(0, Math.min(100, 50 + (cents / 50) * 25));
                    if (needleEl) {
                        needleEl.style.left = `${needlePosition}%`;
                        needleEl.style.background = Math.abs(cents) < 5 ? "#4caf50" : "#9c27b0";
                    }
                }
                tuner.animationFrame = requestAnimationFrame(updateTuner);
            }
            updateTuner();
        })
        .catch((error) => {
            addMessage(`Error accessing microphone: ${error.message}`, "error");
        });
}

function stopTuner(tunerId: string): void {
    const tuner = tuners.get(tunerId);
    if (!tuner || !tuner.isRunning) return;
    tuner.isRunning = false;
    if (tuner.animationFrame) {
        cancelAnimationFrame(tuner.animationFrame);
    }
    if (tuner.microphone) {
        tuner.microphone.mediaStream.getTracks().forEach((track) => track.stop());
    }
    if (tuner.audioContext) {
        tuner.audioContext.close();
    }
    const widgetEl = tuner.widgetEl;
    const startBtn = widgetEl.querySelector(".start-btn") as HTMLButtonElement;
    const stopBtn = widgetEl.querySelector(".stop-btn") as HTMLButtonElement;
    const statusEl = document.getElementById(`status-${tunerId}`);
    if (startBtn) startBtn.style.display = "inline-block";
    if (stopBtn) stopBtn.style.display = "none";
    if (statusEl) {
        statusEl.textContent = "Stopped";
        statusEl.className = "tuner-status";
    }
    tuner.analyser = null;
    tuner.microphone = null;
    tuner.audioContext = null;
}
