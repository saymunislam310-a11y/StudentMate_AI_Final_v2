(function () {
    const KEY = "studentmate-theme";
    const root = document.documentElement;

    function isDark() {
        return root.classList.contains("dark-mode");
    }

    function apply(dark) {
        root.classList.toggle("dark-mode", dark);
        const setting = document.getElementById("darkModeSetting");
        if (setting) setting.checked = dark;
        const btn = document.getElementById("themeToggle");
        if (btn) {
            btn.textContent = dark ? "☀️" : "🌙";
            btn.setAttribute("aria-label", dark ? "Turn on light mode" : "Turn on dark mode");
            btn.title = dark ? "Light mode" : "Dark mode";
        }
    }

    let saved = localStorage.getItem(KEY);
    let dark = saved === "dark";
    if (saved === null) {
        dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    apply(dark);

    document.addEventListener("DOMContentLoaded", function () {
        if (!document.getElementById("themeToggle")) {
            const btn = document.createElement("button");
            btn.id = "themeToggle";
            btn.className = "theme-toggle";
            btn.type = "button";
            btn.addEventListener("click", function () {
                const next = !isDark();
                localStorage.setItem(KEY, next ? "dark" : "light");
                apply(next);
            });
            document.body.appendChild(btn);
        }

        const setting = document.getElementById("darkModeSetting");
        if (setting) {
            setting.checked = isDark();
            setting.addEventListener("change", function () {
                localStorage.setItem(KEY, setting.checked ? "dark" : "light");
                apply(setting.checked);
            });
        }

        apply(isDark());
    });
})();
