import { API_URL } from "../config.js";
import { escapeHtml, isSafeHttpUrl } from "../utils/sanitize.js";
import {
    SystemStatusResponse,
    ModelRecommendationsResponse,
    ModelRecommendation,
    HardwareInfo,
} from "../types.js";

let setupOverlayEl: HTMLElement | null = null;

// Server-supplied URLs are never interpolated into markup. Render functions
// register them here and emit a data-link-idx placeholder; applySafeLinks()
// then assigns validated http(s) URLs via the element.href property.
let pendingLinkUrls: string[] = [];

function safeLinkPlaceholder(url: string): string {
    pendingLinkUrls.push(url);
    return `data-link-idx="${pendingLinkUrls.length - 1}"`;
}

function applySafeLinks(root: HTMLElement): void {
    root.querySelectorAll<HTMLAnchorElement>("a[data-link-idx]").forEach((anchor) => {
        const idx = Number(anchor.getAttribute("data-link-idx"));
        anchor.removeAttribute("data-link-idx");
        const url = pendingLinkUrls[idx];
        if (typeof url === "string" && isSafeHttpUrl(url)) {
            anchor.href = url;
        }
    });
    pendingLinkUrls = [];
}

export async function checkSystemStatus(): Promise<SystemStatusResponse | null> {
    try {
        const response = await fetch(`${API_URL}/api/system/status`);
        if (!response.ok) {
            console.error("Failed to fetch system status:", response.statusText);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching system status:", error);
        return null;
    }
}

export async function getModelRecommendations(): Promise<ModelRecommendationsResponse | null> {
    try {
        const response = await fetch(`${API_URL}/api/system/model-recommendations`);
        if (!response.ok) {
            console.error("Failed to fetch model recommendations:", response.statusText);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching model recommendations:", error);
        return null;
    }
}

function formatSize(sizeGb: number): string {
    if (sizeGb < 1) {
        return `${Math.round(sizeGb * 1024)} MB`;
    }
    return `${sizeGb.toFixed(1)} GB`;
}

function getTierLabel(tier: string): string {
    const labels: Record<string, string> = {
        cpu: "CPU Only",
        low: "Low VRAM (4-6 GB)",
        medium: "Medium VRAM (8-12 GB)",
        high: "High VRAM (16-24 GB)",
        very_high: "Very High VRAM (24+ GB)",
    };
    return labels[tier] || tier;
}

function renderHardwareInfo(hardware: HardwareInfo): string {
    const gpuSection = hardware.gpu.available
        ? `<div class="hardware-item">
            <span class="label">GPU:</span>
            <span class="value">${escapeHtml(hardware.gpu.name ?? "Unknown")}</span>
            <span class="detail">${escapeHtml(formatSize(hardware.gpu.memory_total_gb || 0))} VRAM (${escapeHtml(formatSize(hardware.gpu.memory_free_gb || 0))} free)</span>
           </div>`
        : `<div class="hardware-item no-gpu">
            <span class="label">GPU:</span>
            <span class="value">Not detected</span>
           </div>`;

    const ramSection = `<div class="hardware-item">
        <span class="label">RAM:</span>
        <span class="value">${escapeHtml(formatSize(hardware.ram.total_gb))}</span>
        <span class="detail">(${escapeHtml(formatSize(hardware.ram.available_gb))} available)</span>
    </div>`;

    const tierSection = `<div class="hardware-item">
        <span class="label">Hardware Tier:</span>
        <span class="value tier-${escapeHtml(hardware.tier)}">${escapeHtml(getTierLabel(hardware.tier))}</span>
    </div>`;

    let hintSection = "";
    if (hardware.gpu_hint) {
        hintSection = `<div class="gpu-hint">
            <p>${escapeHtml(hardware.gpu_hint.message)}</p>
            <a ${safeLinkPlaceholder(hardware.gpu_hint.docs_url)} target="_blank" rel="noopener">View installation guide</a>
        </div>`;
    }

    return `<div class="hardware-info">
        <h3>Detected Hardware</h3>
        ${gpuSection}
        ${ramSection}
        ${tierSection}
        ${hintSection}
    </div>`;
}

function renderModelCard(
    model: ModelRecommendation,
    defaultPath: string,
    isPrimary: boolean
): string {
    const primaryBadge = isPrimary ? '<span class="badge primary">Recommended</span>' : "";
    const tierBadge = `<span class="badge tier-${escapeHtml(model.tier)}">${escapeHtml(getTierLabel(model.tier))}</span>`;

    return `<div class="model-card ${isPrimary ? "primary" : ""}">
        <div class="model-header">
            <h4>${escapeHtml(model.name)}</h4>
            <div class="badges">${primaryBadge}${tierBadge}</div>
        </div>
        <p class="model-description">${escapeHtml(model.description)}</p>
        <div class="model-specs">
            <span>Size: ${escapeHtml(formatSize(model.size_gb))}</span>
            <span>VRAM: ${escapeHtml(formatSize(model.vram_required_gb))}</span>
            <span>Context: ${escapeHtml(model.context_window.toLocaleString())} tokens</span>
        </div>
        <div class="model-actions">
            <a ${safeLinkPlaceholder(model.download_url)} target="_blank" rel="noopener" class="download-btn">
                Download from HuggingFace
            </a>
        </div>
        <div class="model-path">
            <code>Save to: ${escapeHtml(defaultPath)}/${escapeHtml(model.filename)}</code>
        </div>
    </div>`;
}

function renderNoModelsAvailable(): string {
    return `<div class="no-models">
        <p>No compatible models found for your hardware.</p>
        <p>Your system may not have enough memory to run any of the available models.</p>
        <p>Consider upgrading your RAM or GPU, or try a smaller model manually.</p>
    </div>`;
}

function renderCurrentModelInfo(status: SystemStatusResponse): string {
    if (!status.model_loaded || !status.model_path) {
        return "";
    }
    const filename = status.model_path.split("/").pop() || status.model_path;
    return `<div class="current-model-info">
        <h3>Current Model</h3>
        <div class="model-status loaded">
            <span class="status-indicator"></span>
            <span class="status-text">Model loaded</span>
        </div>
        <div class="model-path-display">
            <span class="label">Path:</span>
            <code>${escapeHtml(status.model_path)}</code>
        </div>
        <div class="model-filename">
            <span class="label">File:</span>
            <span class="value">${escapeHtml(filename)}</span>
        </div>
    </div>`;
}

export async function showSetupOverlay(status: SystemStatusResponse): Promise<void> {
    if (setupOverlayEl) {
        return; // Already showing
    }

    const recommendations = await getModelRecommendations();
    const modelLoaded = status.model_loaded;

    setupOverlayEl = document.createElement("div");
    setupOverlayEl.id = "setup-overlay";
    setupOverlayEl.className = "setup-overlay";
    setupOverlayEl.setAttribute("role", "dialog");
    setupOverlayEl.setAttribute("aria-modal", "true");

    let modelsSection: string;
    if (recommendations && recommendations.all_recommendations.length > 0) {
        const primaryModel = recommendations.primary_recommendation;
        const otherModels = recommendations.all_recommendations.filter(
            (m) => !primaryModel || m.name !== primaryModel.name
        );

        const sectionTitle = modelLoaded ? "Alternative Models" : "Recommended Models";
        modelsSection = `<div class="models-section">
            <h3>${sectionTitle}</h3>
            ${primaryModel ? renderModelCard(primaryModel, recommendations.default_model_path, !modelLoaded) : ""}
            ${
                otherModels.length > 0
                    ? `<details class="other-models"${modelLoaded ? "" : ' open=""'}>
                <summary>Other compatible models (${otherModels.length})</summary>
                <div class="other-models-list">
                    ${otherModels.map((m) => renderModelCard(m, recommendations.default_model_path, false)).join("")}
                </div>
            </details>`
                    : ""
            }
        </div>`;
    } else {
        modelsSection = renderNoModelsAvailable();
    }

    let envInstructions = "";
    if (recommendations && !modelLoaded) {
        envInstructions = `<div class="env-instructions">
            <h3>After Downloading</h3>
            <p>Set the model path in your environment:</p>
            <code>export LLM_MODEL_PATH="${escapeHtml(recommendations.default_model_path)}/[model-filename].gguf"</code>
            <p>Then restart the server.</p>
        </div>`;
    }

    const title = modelLoaded ? "System Information" : "Model Setup Required";
    setupOverlayEl.setAttribute("aria-label", title);
    const introMessage = modelLoaded
        ? "View your hardware configuration and available models."
        : status.initialization_error ||
          "No LLM model is configured. Please download a model to use Zikos.";
    const introClass = modelLoaded ? "setup-intro info" : "setup-intro";
    const dismissText = modelLoaded ? "Close" : "I'll set this up later";

    setupOverlayEl.innerHTML = `<div class="setup-content">
        <h2>${title}</h2>
        <p class="${introClass}">${escapeHtml(introMessage)}</p>
        ${renderCurrentModelInfo(status)}
        ${renderHardwareInfo(status.hardware)}
        ${modelsSection}
        ${envInstructions}
        <button class="dismiss-btn" id="dismissSetup">${dismissText}</button>
    </div>`;

    applySafeLinks(setupOverlayEl);

    document.body.appendChild(setupOverlayEl);

    const dismissBtn = document.getElementById("dismissSetup");
    if (dismissBtn) {
        dismissBtn.addEventListener("click", hideSetupOverlay);
        dismissBtn.focus();
    }

    document.addEventListener("keydown", handleOverlayKeydown);
}

function handleOverlayKeydown(e: KeyboardEvent): void {
    if (e.key === "Escape") {
        hideSetupOverlay();
    }
}

export function hideSetupOverlay(): void {
    document.removeEventListener("keydown", handleOverlayKeydown);
    if (setupOverlayEl) {
        setupOverlayEl.remove();
        setupOverlayEl = null;
    }
}

export function isSetupRequired(status: SystemStatusResponse): boolean {
    return !status.model_loaded;
}
