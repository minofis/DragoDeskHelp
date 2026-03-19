// Открытие модального окна
function openModal() {
    document.getElementById('requestModal').style.display = 'block';
}

// Закрытие модального окна
function closeModal() {
    const modal = document.getElementById('requestModal');
    const form = document.getElementById('requestForm');
    modal.style.display = 'none';
    if (form) form.reset();
}

// Закрытие по клику на фон
function initModalEvents() {
    window.onclick = function(event) {
        const modal = document.getElementById('requestModal');
        if (event.target === modal) {
            closeModal();
        }
    }
}

// Обработка отправки формы
function initFormSubmit() {
    const form = document.getElementById('requestForm');
    if (form) {
        form.onsubmit = function(e) {
            e.preventDefault();
            const formData = new FormData(form);
            const room = formData.get('room');
            const applicant = formData.get('applicant');
            const desc = formData.get('description');
            
            // TODO: добавить заявку в таблицу во фрейме
            console.log('Новая заявка:', {room, applicant, desc});
            
            alert('Заявка отправлена!\nАудитория: ' + room + '\nЗаявник: ' + applicant + '\nОписание: ' + desc);
            closeModal();
        }
    }
}

// Инициализация всех событий при загрузке страницы
window.addEventListener('load', function() {
    initModalEvents();
    initFormSubmit();
});
 