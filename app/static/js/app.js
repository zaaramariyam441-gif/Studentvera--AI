document.addEventListener('DOMContentLoaded', function () {
    const globalSearch = document.getElementById('global-search');
    if (globalSearch) {
        globalSearch.addEventListener('input', function () {
            const term = this.value.trim().toLowerCase();
            const rows = document.querySelectorAll('table tbody tr');
            rows.forEach((row) => {
                if (!row.dataset.searchText) {
                    row.dataset.searchText = Array.from(row.querySelectorAll('td')).map(cell => cell.textContent.toLowerCase()).join(' ');
                }
                row.style.display = row.dataset.searchText.includes(term) || !term ? '' : 'none';
            });
        });
    }

    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const applyTheme = (darkMode) => {
            document.body.classList.toggle('dark-mode', darkMode);
            const icon = themeToggle.querySelector('.theme-toggle-icon');
            if (icon) icon.textContent = darkMode ? '🌙' : '☀️';
            localStorage.setItem('studentvera-theme', darkMode ? 'dark' : 'light');
        };

        const savedTheme = localStorage.getItem('studentvera-theme');
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        applyTheme(savedTheme ? savedTheme === 'dark' : prefersDark);

        themeToggle.addEventListener('click', function () {
            applyTheme(!document.body.classList.contains('dark-mode'));
        });
    }
});
