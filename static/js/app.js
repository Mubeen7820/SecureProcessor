document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle Logic
    const themeToggle = document.getElementById('theme-toggle');
    const html = document.documentElement;
    const themeIndicatorIcon = document.getElementById('theme-indicator-icon');

    // Light mode: thumb on right (checked=true), sun icon
    // Dark mode: thumb on left (checked=false), moon icon

    const sidebarThemeToggle = document.getElementById('theme-toggle-sidebar');

    const savedTheme = localStorage.getItem('theme') || 'light';
    html.setAttribute('data-theme', savedTheme);

    const syncToggles = (theme) => {
        if (themeToggle) themeToggle.checked = (theme === 'light');
        if (sidebarThemeToggle) sidebarThemeToggle.checked = (theme === 'light');
    };

    syncToggles(savedTheme);
    updateIndicator(savedTheme);

    const handleThemeChange = (e) => {
        const newTheme = e.target.checked ? 'light' : 'dark';
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        syncToggles(newTheme);
        updateIndicator(newTheme);
    };

    if (themeToggle) themeToggle.addEventListener('change', handleThemeChange);
    if (sidebarThemeToggle) sidebarThemeToggle.addEventListener('change', handleThemeChange);

    function updateIndicator(theme) {
        if (!themeIndicatorIcon) return;
        if (theme === 'light') {
            themeIndicatorIcon.className = 'fas fa-sun';
            themeIndicatorIcon.style.color = '#2563eb'; // Deep blue for light mode
        } else {
            themeIndicatorIcon.className = 'fas fa-moon';
            themeIndicatorIcon.style.color = '#00f2ff'; // Cyan for dark mode
        }
    }

    // Live Clock Logic
    const clockElement = document.getElementById('live-clock');
    if (clockElement) {
        const updateClock = () => {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            });
            clockElement.textContent = timeStr;
        };
        setInterval(updateClock, 1000);
        updateClock();
    }

    // Pass-toggle logic (if present on page)
    const togglePass = document.getElementById('toggle-pass');
    if (togglePass) {
        togglePass.onclick = function () {
            const passField = document.getElementById('password-field');
            if (passField.type === 'password') {
                passField.type = 'text';
                this.classList.replace('fa-eye-slash', 'fa-eye');
            } else {
                passField.type = 'password';
                this.classList.replace('fa-eye', 'fa-eye-slash');
            }
        };
    }

    console.log('Secure Processor OS v1.1 Initialized');
});
