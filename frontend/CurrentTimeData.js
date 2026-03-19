function updateDateTime() {
    const now = new Date();
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    const formatted = now.toLocaleString('ru-RU', options);
    const el = document.getElementById('current-time');
    if (el) {
        el.textContent = formatted;
    }
}

window.addEventListener('load', function () {
    updateDateTime();
    setInterval(updateDateTime, 1000);
});
