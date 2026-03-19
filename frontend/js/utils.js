/**
 * MCServerPanel - Utility Functions
 */

function toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    const icons = { success: '&#10004;', error: '&#10006;', warning: '&#9888;', info: '&#8505;' };
    el.innerHTML = `<span>${icons[type] || ''}</span><span>${escapeHtml(message)}</span>`;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 4000);
}

function escapeHtml(text) {
    const el = document.createElement('span');
    el.textContent = text;
    return el.innerHTML;
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

function formatNumber(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
    return String(n);
}

function timeAgo(isoDate) {
    if (!isoDate) return '';
    const diff = Date.now() - new Date(isoDate).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + 'm ago';
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + 'h ago';
    const days = Math.floor(hrs / 24);
    return days + 'd ago';
}

function showModal(html) {
    document.getElementById('modal-content').innerHTML = html;
    document.getElementById('modal-overlay').classList.add('active');
}

function closeModal(event) {
    if (event && event.target !== document.getElementById('modal-overlay')) return;
    document.getElementById('modal-overlay').classList.remove('active');
}

function closeModalDirect() {
    document.getElementById('modal-overlay').classList.remove('active');
}

function loading(text = 'Loading...') {
    return `<div class="loading-overlay"><div class="spinner"></div>${escapeHtml(text)}</div>`;
}

function emptyState(icon, title, subtitle = '') {
    return `<div class="empty-state">
        <div class="icon">${icon}</div>
        <h3>${escapeHtml(title)}</h3>
        ${subtitle ? `<p>${escapeHtml(subtitle)}</p>` : ''}
    </div>`;
}

function statusBadge(status) {
    return `<span class="status-badge ${status}"><span class="status-dot"></span>${status}</span>`;
}

function serverTypeTag(type) {
    const cls = type === 'forge' ? 'forge' : type === 'fabric' ? 'fabric' : 'vanilla';
    return `<span class="tag ${cls}">${escapeHtml(type)}</span>`;
}

function progressBar(percent, color = 'blue') {
    return `<div class="progress-bar"><div class="progress-fill ${color}" style="width:${Math.min(100, percent)}%"></div></div>`;
}
