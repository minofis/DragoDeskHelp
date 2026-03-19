const API_BASE = '/api/tickets';

function escapeHtml(str) {
  if (!str && str !== 0) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function statusText(status) {
  switch (Number(status)) {
    case 0: return 'Новая';
    case 1: return 'В работе';
    case 2: return 'Выполнено';
    case 3: return 'Закрыто';
    default: return 'Неизвестно';
  }
}

function statusClass(status) {
  switch (Number(status)) {
    case 0: return 'status-новая';
    case 1: return 'status-в-работе';
    case 2: return 'status-выполнено';
    case 3: return 'status-закрыто';
    default: return 'status-неизвестно';
  }
}

async function fetchTickets() {
  try {
    const res = await fetch(API_BASE);
    if (!res.ok) throw new Error('Network response was not ok');
    const data = await res.json();
    const tbody = document.getElementById('ticketsBody');
    if (!tbody) return; // nothing to render into
    tbody.innerHTML = '';
    data.forEach(ticket => {
      const tr = document.createElement('tr');
      const publishedTime = ticket.publishedAt || ticket.createdAt || '';
      tr.innerHTML = `
        <td>${escapeHtml(ticket.id)}</td>
        <td>${escapeHtml(ticket.roomNumber)}</td>
        <td>${escapeHtml(ticket.authorName)}</td>
        <td>${escapeHtml(ticket.description)}</td>
        <td>${escapeHtml(publishedTime)}</td>
        <td><span class="status ${statusClass(ticket.status)}">${statusText(ticket.status)}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to fetch tickets', err);
  }
}

// When this script runs inside the iframe (requests.html)
if (window.self !== window.top) {
  window.refreshTickets = fetchTickets;
  document.addEventListener('DOMContentLoaded', fetchTickets);
} else {
  // Parent window (Index.html) — attach form submit handler
  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('requestForm');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const room = document.getElementById('room')?.value.trim();
      const applicant = document.getElementById('applicant')?.value.trim();
      const description = document.getElementById('description')?.value.trim();

      if (!room || !applicant || !description) {
        alert('Пожалуйста, заполните все поля формы.');
        return;
      }

      const payload = {
        roomNumber: room,
        authorName: applicant,
        description: description
      };

      try {
        const res = await fetch(API_BASE, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    });
        if (!res.ok) throw new Error('POST failed');

        // clear form
        form.reset();
        // close modal if function exists
        if (typeof closeModal === 'function') closeModal();

        // refresh iframe list if possible
        const iframe = document.getElementById('requests-frame');
        if (iframe && iframe.contentWindow) {
          if (typeof iframe.contentWindow.refreshTickets === 'function') {
            iframe.contentWindow.refreshTickets();
          } else {
            // fallback: reload iframe
            iframe.contentWindow.location.reload();
          }
        }
      } catch (err) {
        console.error('Failed to submit ticket', err);
        alert('Ошибка при отправке заявки. Попробуйте ещё раз.');
      }
    });
  });
}
