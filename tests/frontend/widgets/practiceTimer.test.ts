import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { addPracticeTimerWidget } from "../../../frontend/src/widgets/practiceTimer.js";
import * as ui from "../../../frontend/src/ui.js";

describe("Practice Timer Widget", () => {
    beforeEach(() => {
        document.body.innerHTML = `<div id="messages"></div>`;
        vi.useFakeTimers();
        vi.spyOn(ui, "addMessage").mockImplementation(() => {});
    });

    afterEach(() => {
        vi.clearAllMocks();
        vi.useRealTimers();
    });

    describe("addPracticeTimerWidget()", () => {
        it("should create practice timer widget in DOM", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            expect(widget).toBeTruthy();
            expect(widget?.className).toBe("practice-timer-widget");
        });

        it("should display goal when provided", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            expect(widget?.textContent).toContain("Practice scales");
        });

        it("should display duration when provided", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            expect(widget?.textContent).toContain("30");
        });

        it("should display description when provided", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5, "Test timer");
            const widget = document.getElementById("timer-timer_123");
            expect(widget?.textContent).toContain("Test timer");
        });

        it("should create control buttons", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            expect(widget?.querySelector(".start-btn")).toBeTruthy();
            expect(widget?.querySelector(".pause-btn")).toBeTruthy();
            expect(widget?.querySelector(".stop-btn")).toBeTruthy();
        });

        it("should initially hide pause button", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLElement;
            expect(pauseBtn?.style.display).toBe("none");
        });

        it("should show initial status as Stopped", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const statusEl = document.getElementById("status-timer_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });

        it("should initialize time display as 00:00", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const timeEl = document.getElementById("time-timer_123");
            expect(timeEl?.textContent).toBe("00:00");
        });
    });

    describe("Start Practice Timer", () => {
        it("should start timer when start button is clicked", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();

            const statusEl = document.getElementById("status-timer_123");
            expect(statusEl?.textContent).toBe("Running");
        });

        it("should show pause button when started", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLElement;

            startBtn.click();

            expect(pauseBtn.style.display).toBe("inline-block");
            expect(startBtn.style.display).toBe("none");
        });

        it("should start interval when started", () => {
            const setIntervalSpy = vi.spyOn(window, "setInterval");
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();

            expect(setIntervalSpy).toHaveBeenCalled();
        });

        it("should update time display over time", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            vi.advanceTimersByTime(1000);

            const timeEl = document.getElementById("time-timer_123");
            expect(timeEl?.textContent).not.toBe("00:00");
        });

        it("should not start if already running", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            const firstStatus = document.getElementById("status-timer_123")?.textContent;

            startBtn.click();
            const secondStatus = document.getElementById("status-timer_123")?.textContent;

            expect(firstStatus).toBe(secondStatus);
        });
    });

    describe("Pause Practice Timer", () => {
        it("should pause timer when pause button is clicked", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            startBtn.click();
            pauseBtn.click();

            const statusEl = document.getElementById("status-timer_123");
            expect(statusEl?.textContent).toBe("Paused");
        });

        it("should show start button when paused", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            startBtn.click();
            pauseBtn.click();

            expect(startBtn.style.display).toBe("inline-block");
            expect(pauseBtn.style.display).toBe("none");
        });

        it("should clear interval when paused", () => {
            const clearIntervalSpy = vi.spyOn(window, "clearInterval");
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            startBtn.click();
            pauseBtn.click();

            expect(clearIntervalSpy).toHaveBeenCalled();
        });

        it("should resume from paused time", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            startBtn.click();
            vi.advanceTimersByTime(5000);
            pauseBtn.click();
            startBtn.click();

            const statusEl = document.getElementById("status-timer_123");
            expect(statusEl?.textContent).toBe("Running");
        });

        it("should not pause if not running", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            pauseBtn.click();

            const statusEl = document.getElementById("status-timer_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });
    });

    describe("Stop Practice Timer", () => {
        it("should stop timer when stop button is clicked", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            startBtn.click();
            stopBtn.click();

            const statusEl = document.getElementById("status-timer_123");
            expect(statusEl?.textContent).toBe("Stopped");
        });

        it("should reset time display when stopped", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            startBtn.click();
            vi.advanceTimersByTime(5000);
            stopBtn.click();

            const timeEl = document.getElementById("time-timer_123");
            expect(timeEl?.textContent).toBe("00:00");
        });

        it("should clear interval when stopped", () => {
            const clearIntervalSpy = vi.spyOn(window, "clearInterval");
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            startBtn.click();
            stopBtn.click();

            expect(clearIntervalSpy).toHaveBeenCalled();
        });

        it("should show start button when stopped", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const stopBtn = widget?.querySelector(".stop-btn") as HTMLButtonElement;

            startBtn.click();
            stopBtn.click();

            expect(startBtn.style.display).toBe("inline-block");
        });
    });

    describe("Duration Completion", () => {
        it("should stop when duration is reached", () => {
            addPracticeTimerWidget("timer_123", 0.001, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();

            vi.advanceTimersByTime(1000);

            const statusEl = document.getElementById("status-timer_123");
            expect(statusEl?.textContent).toBe("Complete!");
        });

        it("should show completion message when duration is reached", () => {
            addPracticeTimerWidget("timer_123", 0.001, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();

            vi.advanceTimersByTime(1000);

            expect(ui.addMessage).toHaveBeenCalledWith("Practice session complete!", "assistant");
        });
    });

    describe("Break Intervals", () => {
        it("should set up break interval when provided", () => {
            const setIntervalSpy = vi.spyOn(window, "setInterval");
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();

            expect(setIntervalSpy).toHaveBeenCalledTimes(2);
        });

        it("should show break reminder message", () => {
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 0.001);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;

            startBtn.click();
            vi.advanceTimersByTime(100);

            expect(ui.addMessage).toHaveBeenCalledWith(
                expect.stringContaining("Break reminder"),
                "assistant"
            );
        });

        it("should clear break interval when paused", () => {
            const clearIntervalSpy = vi.spyOn(window, "clearInterval");
            addPracticeTimerWidget("timer_123", 30, "Practice scales", 5);
            const widget = document.getElementById("timer-timer_123");
            const startBtn = widget?.querySelector(".start-btn") as HTMLButtonElement;
            const pauseBtn = widget?.querySelector(".pause-btn") as HTMLButtonElement;

            startBtn.click();
            pauseBtn.click();

            expect(clearIntervalSpy).toHaveBeenCalledTimes(2);
        });
    });

    describe("Edge Cases", () => {
        it("should throw error when messages element is missing", () => {
            document.body.innerHTML = "";
            expect(() => addPracticeTimerWidget("timer_123", 30, "Practice scales", 5)).toThrow(
                "Messages element not found"
            );
        });
    });
});
