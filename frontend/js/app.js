/**
 * MCServerPanel - Main App Router
 */
let currentPage = 'dashboard';
let currentParams = {};
const AUTH_TOKEN_KEY = 'mcsp_token';
const AUTH_USER_KEY = 'mcsp_user';

const PAGE_RENDERERS = {
    'dashboard': renderDashboard,
    'servers': renderServers,
    'server-detail': renderServerDetail,
    'create-server': renderCreateServer,
    'modpacks': renderModpacks,
    'mods': renderMods,
    'plugins': renderPlugins,
    'backups': renderBackups,
    'settings': renderSettings,
};

function isLoggedIn() {
    return !!localStorage.getItem(AUTH_TOKEN_KEY);
}

function renderLogin() {
    const main = document.getElementById('main-content');
    main.innerHTML = `
        <div class="card" style="max-width:480px;margin:60px auto;">
            <h2 style="margin-bottom:8px;">Login</h2>
            <p style="color:var(--text-secondary);margin-bottom:18px;">Use one of the configured local accounts to access this panel.</p>
            <div class="form-group">
                <label class="form-label">Username</label>
                <input class="form-input" id="login-username" placeholder="Username" />
            </div>
            <div class="form-group">
                <label class="form-label">Password</label>
                <input class="form-input" id="login-password" type="password" placeholder="Password" onkeydown="if(event.key==='Enter')doLogin()" />
            </div>
            <button class="btn btn-primary" id="login-btn" onclick="doLogin()">Login</button>
            <p style="margin-top:12px;color:var(--text-muted);font-size:12px;">Configured users: admin / admin and sidd / 1234</p>
        </div>
    `;
}

async function doLogin() {
    const username = document.getElementById('login-username')?.value?.trim() || '';
    const password = document.getElementById('login-password')?.value || '';
    const btn = document.getElementById('login-btn');
    if (!username || !password) {
        toast('Enter username and password', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Signing in...';

    try {
        const resp = await API.auth.login(username, password);
        localStorage.setItem(AUTH_TOKEN_KEY, resp.token);
        localStorage.setItem(AUTH_USER_KEY, resp.username);
        toast(`Welcome ${resp.username}`, 'success');
        navigate('dashboard');
    } catch (err) {
        toast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Login';
    }
}

function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    renderLogin();
}

function navigate(page, params = {}) {
    if (!isLoggedIn()) {
        renderLogin();
        return;
    }

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
    if (isLoggedIn()) {
        navigate('dashboard');
    } else {
        renderLogin();
    }
});
