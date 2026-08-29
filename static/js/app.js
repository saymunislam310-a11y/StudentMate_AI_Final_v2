let timerSeconds = 25 * 60;
let timerTotalSeconds = 25 * 60;
let timerInterval = null;
let timerRunning = false;

function updateTimerDisplay() {
    const display = document.getElementById("timerDisplay");
    if (!display) return;
    const minutes = Math.floor(timerSeconds / 60);
    const seconds = timerSeconds % 60;
    const mm = String(minutes).padStart(2,"0");
    const ss = String(seconds).padStart(2,"0");
    display.textContent = mm + ":" + ss;

    const percentValue = Math.max(0, Math.round((timerSeconds / Math.max(1, timerTotalSeconds)) * 100));
    const percent = document.getElementById("timerPercent");
    if (percent) {
        percent.textContent = percentValue + "% remaining";
    }

    const ring = document.getElementById("timerRing");
    if (ring) {
        const progress = 360 * (1 - (timerSeconds / Math.max(1, timerTotalSeconds)));
        ring.style.setProperty("--timer-progress", progress + "deg");
        ring.setAttribute("aria-label", `Time left ${mm}:${ss}`);
    }

    const log = document.getElementById("studyMinutes");
    if (log && !timerRunning) {
        log.value = Math.max(1, Math.ceil((timerTotalSeconds - timerSeconds) / 60));
    }
}

function setTimer(minutes) {
    pauseTimer();
    timerTotalSeconds = minutes * 60;
    timerSeconds = timerTotalSeconds;
    const mode = document.getElementById("timerMode");
    if (mode) mode.textContent = minutes >= 60 ? `${minutes/60} hour focus` : `${minutes} minute focus`;

    document.querySelectorAll(".timer-preset").forEach(btn => {
        btn.classList.toggle("active", Number(btn.dataset.minutes) === minutes);
    });
    const status = document.getElementById("timerStatus");
    if (status) status.textContent = "Ready";
    updateTimerDisplay();
}

function setCustomTimer() {
    const input = document.getElementById("customMinutes");
    if (!input) return;
    const minutes = Number(input.value);
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 720) {
        alert("Choose a timer from 1 to 720 minutes.");
        return;
    }
    setTimer(minutes);
    input.value = "";
}

function startTimer() {
    if (timerInterval) return;
    timerRunning = true;
    const status = document.getElementById("timerStatus");
    if (status) status.textContent = "Focusing…";

    timerInterval = setInterval(() => {
        if (timerSeconds <= 0) {
            updateTimerDisplay();
            pauseTimer();
            const status = document.getElementById("timerStatus");
            if (status) status.textContent = "Complete 🎉";
            alert("Study session complete! 🎉 Great work.");
            return;
        }
        timerSeconds--;
        updateTimerDisplay();
    }, 1000);
}

function pauseTimer() {
    clearInterval(timerInterval);
    timerInterval = null;
    timerRunning = false;
    const status = document.getElementById("timerStatus");
    if (status && timerSeconds > 0) status.textContent = "Paused";
    updateTimerDisplay();
}

function resetTimer() {
    pauseTimer();
    timerSeconds = timerTotalSeconds;
    const status = document.getElementById("timerStatus");
    if (status) status.textContent = "Ready";
    updateTimerDisplay();
}

document.addEventListener("DOMContentLoaded", () => {
    // Always paint the default 25-minute session immediately on the study page.
    const display = document.getElementById("timerDisplay");
    if (display) {
        timerTotalSeconds = 25 * 60;
        timerSeconds = 25 * 60;
        timerRunning = false;
        updateTimerDisplay();
    }

    document.querySelectorAll(".timer-preset").forEach(btn => {
        btn.addEventListener("click", () => setTimer(Number(btn.dataset.minutes)));
    });
});
