/**
 * MCServerPanel - Main App Router
 */
let currentPage = 'dashboard';
let currentParams = {};

const PAGE_RENDERERS = {
    'dashboard': renderDashboard,
    'servers': renderServers,
    'server-detail': renderServerDetail,
    'create-server': renderCreateServer,
    'modpacks': renderModpacks,
    'mods': renderMods,
    'backups': renderBackups,
    'settings': renderSettings,
};

function navigate(page, params = {}) {
    // Clear any intervals from previous page
    if (typeof consoleInterval !== 'undefined' && consoleInterval) {
        clearInterval(consoleInterval);
        consoleInterval = null;
    }

    currentPage = page;
    currentParams = params;

    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });

    // Render page
    const renderer = PAGE_RENDERERS[page];
    if (renderer) {
        renderer(params);
    } else {
        document.getElementById('main-content').innerHTML =
            `<div class="card">${emptyState('&#9888;', 'Page not found')}</div>`;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    navigate('dashboard');
});
