const API_BASE = '/api/tickets';

// Защита от XSS-атак
function escapeHtml(str) {
  if (!str && str !== 0) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Генерация CSS-класса на основе статуса
function statusClassFromText(statusText) {
  if (!statusText && statusText !== 0) return 'status-невідомо';

  const slug = String(statusText)
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\-а-яёА-ЯЁіІїЇєЄґҐ\-]/g, '')
    .replace(/-+/g, '-');
  return `status-${slug}`;
}

// Получение и отрисовка заявок
async function fetchTickets() {
  try {
    const res = await fetch(API_BASE);
    if (!res.ok) throw new Error('Network response was not ok');
    
    const data = await res.json();
    const tbody = document.getElementById('ticketsBody');
    if (!tbody) return; 
    
    tbody.innerHTML = '';
    
    if (data.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 60px 20px; color: #666; font-size: 1.1em; font-style: italic; background: #fff; border: none !important;">
            Заявок поки що немає
          </td>
        </tr>
      `;
      return; 
    }
    
    data.forEach(ticket => {
      const tr = document.createElement('tr');
      const publishedTime = ticket.publishedAt || ticket.createdAt || '';
      
      tr.innerHTML = `
        <td>${escapeHtml(ticket.displayId ?? ticket.id ?? ticket.Id ?? '')}</td>
        <td>${escapeHtml(ticket.roomNumber)}</td>
        <td>${escapeHtml(ticket.authorName)}</td>
        <td>${escapeHtml(ticket.description)}</td>
        <td>${escapeHtml(publishedTime)}</td>
        <td><span class="status ${statusClassFromText(ticket.statusText ?? ticket.StatusText ?? '')}">${escapeHtml(ticket.statusText ?? ticket.StatusText ?? '')}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to fetch tickets', err);
    const tbody = document.getElementById('ticketsBody');
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 30px; color: #dc3545; border: none !important;">
            Помилка завантаження даних. Перевірте з'єднання з сервером.
          </td>
        </tr>
      `;
    }
  }
}

if (window.self !== window.top) {

  window.refreshTickets = fetchTickets;
  document.addEventListener('DOMContentLoaded', fetchTickets);
} else {
  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('requestForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const room = document.getElementById('room')?.value.trim();
      const applicant = document.getElementById('applicant')?.value.trim();
      const description = document.getElementById('description')?.value.trim();

      // 1. Проверка на пустые поля
      if (!room || !applicant || !description) {
        alert('Будь ласка, заповніть усі поля форми.');
        return;
      }

      // 2. Валидация номера аудитории
      const roomRegex = /^[0-9]{1,4}[а-яА-Яa-zA-ZіІїЇєЄґҐ]?$/;
      if (!roomRegex.test(room)) {
        alert('Некоректний номер аудиторії! Введіть число (наприклад: 305 або 101а).');
        return; 
      }

      const payload = {
        roomNumber: room,
        authorName: applicant,
        description: description
      };

      // 3. Отправка на сервер
      try {
        const res = await fetch(API_BASE, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error('POST failed');

        alert('Заявка успішно відправлена!');

        // Очищаем форму и закрываем модалку
        form.reset();
        if (typeof closeModal === 'function') closeModal();

        // Обновляем таблицу во фрейме
        const iframe = document.getElementById('requests-frame');
        if (iframe && iframe.contentWindow) {
          if (typeof iframe.contentWindow.refreshTickets === 'function') {
            iframe.contentWindow.refreshTickets();
          } else {
            iframe.contentWindow.location.reload();
          }
        }
      } catch (err) {
        console.error('Failed to submit ticket', err);
        alert('Помилка при відправці заявки. Перевірте дані та спробуйте ще раз.');
      }
    });
  });
}