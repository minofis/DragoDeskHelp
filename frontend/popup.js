function openModal() {
    document.getElementById('requestModal').style.display = 'block';
}

function closeModal() {
    const modal = document.getElementById('requestModal');
    const form = document.getElementById('requestForm');
    
    if (modal) modal.style.display = 'none';
    if (form) form.reset();
}

window.addEventListener('load', function() {
});