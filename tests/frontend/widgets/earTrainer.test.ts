import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { addEarTrainerWidget } from "../../../frontend/src/widgets/earTrainer.js";

class MockAudioContext {
    state: string = "running";
    currentTime: number = 0;
    destination: any = {};

    createOscillator(): any {
        return {
            connect: vi.fn(),
            start: vi.fn(),
            stop: vi.fn(),
            frequency: { value: 0 },
            type: "sine",
        };
    }

    createGain(): any {
        return {
            connect: vi.fn(),
            gain: {
                value: 0,
                setValueAtTime: vi.fn(),
                exponentialRampToValueAtTime: vi.fn(),
            },
        };
    }
}

describe("Ear Trainer Widget", () => {
    beforeEach(() => {
        document.body.innerHTML = `<div id="messages"></div>`;

        globalThis.AudioContext = vi.fn(() => new MockAudioContext()) as any;
        vi.spyOn(Math, "floor").mockReturnValue(0);
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe("addEarTrainerWidget()", () => {
        it("should create ear trainer widget in DOM", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            expect(widget).toBeTruthy();
            expect(widget?.className).toBe("ear-trainer-widget");
        });

        it("should display mode (intervals)", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            expect(widget?.textContent).toContain("Intervals");
        });

        it("should display description when provided", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C", "Test trainer");
            const widget = document.getElementById("ear-ear_123");
            expect(widget?.textContent).toContain("Test trainer");
        });

        it("should create play and next buttons", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            expect(widget?.querySelector(".play-btn")).toBeTruthy();
            expect(widget?.querySelector(".next-btn")).toBeTruthy();
        });

        it("should initially hide next button", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            const nextBtn = widget?.querySelector(".next-btn") as HTMLElement;
            expect(nextBtn?.style.display).toBe("none");
        });

        it("should show initial status as Ready", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const statusEl = document.getElementById("status-ear_123");
            expect(statusEl?.textContent).toBe("Ready");
        });

        it("should create option buttons for easy difficulty", () => {
            addEarTrainerWidget("ear_123", "intervals", "easy", "C");
            const widget = document.getElementById("ear-ear_123");
            const options = widget?.querySelectorAll(".ear-trainer-option");
            expect(options?.length).toBe(4);
        });

        it("should create option buttons for medium difficulty", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            const options = widget?.querySelectorAll(".ear-trainer-option");
            expect(options?.length).toBe(11);
        });

        it("should create option buttons for hard difficulty", () => {
            addEarTrainerWidget("ear_123", "intervals", "hard", "C");
            const widget = document.getElementById("ear-ear_123");
            const options = widget?.querySelectorAll(".ear-trainer-option");
            expect(options?.length).toBe(14);
        });
    });

    describe("Play Question", () => {
        it("should play question when play button is clicked", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(globalThis.AudioContext).toHaveBeenCalled();
        });

        it("should show next button after playing", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const nextBtn = widget?.querySelector(".next-btn") as HTMLElement;

            playBtn.click();

            expect(nextBtn.style.display).toBe("inline-block");
            expect(playBtn.style.display).toBe("none");
        });

        it("should enable option buttons after playing", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const options = widget.querySelectorAll(".ear-trainer-option");
            options.forEach((btn) => {
                expect((btn as HTMLButtonElement).disabled).toBe(false);
            });
        });

        it("should play intervals in intervals mode", () => {
            addEarTrainerWidget("ear_123", "intervals", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(globalThis.AudioContext).toHaveBeenCalled();
        });

        it("should play chords in chords mode", () => {
            addEarTrainerWidget("ear_123", "chords", "medium", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            expect(globalThis.AudioContext).toHaveBeenCalled();
        });
    });

    describe("Check Answer", () => {
        it("should show correct result when answer is correct", () => {
            vi.spyOn(Math, "floor").mockReturnValue(0);

            addEarTrainerWidget("ear_123", "intervals", "easy", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const options = widget.querySelectorAll(".ear-trainer-option");
            const firstOption = options[0] as HTMLButtonElement;
            firstOption.click();

            const resultEl = document.getElementById("result-ear_123");
            expect(resultEl?.textContent).toContain("Correct");
        });

        it("should show incorrect result when answer is wrong", () => {
            vi.spyOn(Math, "floor").mockReturnValue(0);

            addEarTrainerWidget("ear_123", "intervals", "easy", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const options = widget.querySelectorAll(".ear-trainer-option");
            const wrongOption = options[1] as HTMLButtonElement;
            wrongOption.click();

            const resultEl = document.getElementById("result-ear_123");
            expect(resultEl?.textContent).toContain("Incorrect");
        });

        it("should highlight correct answer", () => {
            vi.spyOn(Math, "floor").mockReturnValue(0);

            addEarTrainerWidget("ear_123", "intervals", "easy", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const options = widget.querySelectorAll(".ear-trainer-option");
            const firstOption = options[0] as HTMLButtonElement;
            firstOption.click();

            expect(firstOption.style.background).toBe("rgb(76, 175, 80)");
        });

        it("should disable all options after answering", () => {
            vi.spyOn(Math, "floor").mockReturnValue(0);

            addEarTrainerWidget("ear_123", "intervals", "easy", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;

            playBtn.click();

            const options = widget.querySelectorAll(".ear-trainer-option");
            const firstOption = options[0] as HTMLButtonElement;
            firstOption.click();

            options.forEach((btn) => {
                expect((btn as HTMLButtonElement).disabled).toBe(true);
            });
        });
    });

    describe("Next Question", () => {
        it("should play next question when next button is clicked", () => {
            vi.spyOn(Math, "floor").mockReturnValue(0);

            addEarTrainerWidget("ear_123", "intervals", "easy", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const nextBtn = widget?.querySelector(".next-btn") as HTMLButtonElement;

            playBtn.click();
            nextBtn.click();

            expect(playBtn.style.display).toBe("none");
            expect(nextBtn.style.display).toBe("inline-block");
        });

        it("should reset option buttons for next question", () => {
            vi.spyOn(Math, "floor").mockReturnValue(0);

            addEarTrainerWidget("ear_123", "intervals", "easy", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const nextBtn = widget?.querySelector(".next-btn") as HTMLButtonElement;

            playBtn.click();
            const firstOption = widget.querySelectorAll(
                ".ear-trainer-option"
            )[0] as HTMLButtonElement;
            firstOption.click();
            nextBtn.click();

            const options = widget.querySelectorAll(".ear-trainer-option");
            options.forEach((btn) => {
                expect((btn as HTMLButtonElement).disabled).toBe(false);
                expect((btn as HTMLElement).style.opacity).toBe("1");
            });
        });

        it("should hide result when starting next question", () => {
            vi.spyOn(Math, "floor").mockReturnValue(0);

            addEarTrainerWidget("ear_123", "intervals", "easy", "C");
            const widget = document.getElementById("ear-ear_123");
            const playBtn = widget?.querySelector(".play-btn") as HTMLButtonElement;
            const nextBtn = widget?.querySelector(".next-btn") as HTMLButtonElement;

            playBtn.click();
            const firstOption = widget.querySelectorAll(
                ".ear-trainer-option"
            )[0] as HTMLButtonElement;
            firstOption.click();
            nextBtn.click();

            const resultEl = document.getElementById("result-ear_123");
            expect(resultEl?.style.display).toBe("none");
        });
    });

    describe("Edge Cases", () => {
        it("should throw error when messages element is missing", () => {
            document.body.innerHTML = "";
            expect(() => addEarTrainerWidget("ear_123", "intervals", "medium", "C")).toThrow(
                "Messages element not found"
            );
        });
    });
});
