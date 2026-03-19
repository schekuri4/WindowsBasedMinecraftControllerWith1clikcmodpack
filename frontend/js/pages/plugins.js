/**
 * Plugin Browser Page
 */
let pluginState = {
    query: '',
    mcVersion: '',
    loader: '',
    offset: 0,
};

async function renderPlugins() {
    const main = document.getElementById('main-content');

    let servers = [];
    try { servers = await API.servers.list(); } catch (e) { /* ignore */ }

    main.innerHTML = `
        <div class="page-header">
            <div>
                <h2>Plugin Browser</h2>
                <div class="subtitle">Browse and install server plugins from Modrinth</div>
            </div>
        </div>

        <div class="card" style="margin-bottom:20px">
            <div class="form-row" style="grid-template-columns: 1fr 150px 150px auto;">
                <div class="form-group" style="margin:0">
                    <input class="form-input" id="plugin-search" placeholder="Search plugins..." value="${escapeHtml(pluginState.query)}"
                        onkeydown="if(event.key==='Enter')searchPlugins()">
                </div>
                <div class="form-group" style="margin:0">
                    <input class="form-input" id="plugin-version" placeholder="MC Version" value="${escapeHtml(pluginState.mcVersion)}">
                </div>
                <div class="form-group" style="margin:0">
                    <select class="form-select" id="plugin-loader">
                        <option value="">Any Loader</option>
                        <option value="paper">Paper</option>
                        <option value="spigot">Spigot</option>
                        <option value="bukkit">Bukkit</option>
                        <option value="velocity">Velocity</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="searchPlugins()">&#128270; Search</button>
            </div>
        </div>

        ${servers.length > 0 ? `
            <div class="card" style="margin-bottom:20px;padding:12px 20px;display:flex;align-items:center;gap:12px;">
                <span style="color:var(--text-secondary);font-size:14px;">Install to server:</span>
                <select class="form-select" id="plugin-target-server" style="width:auto;min-width:240px;">
                    ${servers.map(s => `<option value="${s.id}">${escapeHtml(s.name)} (${escapeHtml(s.server_type)})</option>`).join('')}
                </select>
            </div>
        ` : ''}

        <div id="plugin-results">
            ${loading('Loading plugins...')}
        </div>
    `;

    const loaderEl = document.getElementById('plugin-loader');
    if (loaderEl) loaderEl.value = pluginState.loader || '';

    await searchPlugins();
}

async function searchPlugins() {
    pluginState.query = document.getElementById('plugin-search').value;
    pluginState.mcVersion = document.getElementById('plugin-version').value;
    pluginState.loader = document.getElementById('plugin-loader')?.value || '';
    pluginState.offset = 0;

    const results = document.getElementById('plugin-results');
    results.innerHTML = loading('Searching plugins...');

    try {
        const data = await API.plugins.searchModrinth({
            query: pluginState.query,
            mc_version: pluginState.mcVersion,
            loader: pluginState.loader,
            offset: pluginState.offset,
            limit: 20,
        });

        if (data.results.length === 0) {
            results.innerHTML = emptyState('&#128270;', 'No plugins found', 'Try different search terms.');
            return;
        }

        results.innerHTML = `
            <p style="color:var(--text-muted);font-size:13px;margin-bottom:12px;">${data.total} results</p>
            <div class="mod-grid">
                ${data.results.map(p => pluginCard(p)).join('')}
            </div>
        `;
    } catch (err) {
        results.innerHTML = emptyState('&#9888;', 'Search failed', err.message);
    }
}

function pluginCard(p) {
    const encodedName = encodeURIComponent(p.name || '');
    return `
        <div class="mod-card">
            <img class="mod-icon" src="${p.icon_url || ''}" alt="" onerror="this.style.display='none'">
            <div class="mod-card-info">
                <h4>${escapeHtml(p.name)}</h4>
                <p>${escapeHtml(p.description)}</p>
                <div class="mod-card-meta">
                    <span>&#11015; ${formatNumber(p.downloads)}</span>
                    <span>${escapeHtml(p.author)}</span>
                    ${(p.categories || []).slice(0, 3).map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('')}
                </div>
            </div>
            <div class="mod-card-actions">
                <button class="btn btn-primary btn-sm" onclick="showPluginInstall('${p.id}', '${encodedName}')">Install</button>
            </div>
        </div>
    `;
}

async function showPluginInstall(projectId, encodedName) {
    const name = decodeURIComponent(encodedName || '');
    const serverSelect = document.getElementById('plugin-target-server');
    if (!serverSelect) {
        toast('Create a server first', 'warning');
        return;
    }
    const serverId = serverSelect.value;

    showModal(`
        <div class="modal-header"><h3>Install Plugin: ${escapeHtml(name)}</h3><button class="btn-icon" onclick="closeModalDirect()">&#10005;</button></div>
        <div class="modal-body">${loading('Loading versions...')}</div>
    `);

    try {
        const versions = await API.plugins.versions(projectId, {
            mc_version: document.getElementById('plugin-version')?.value || '',
            loader: document.getElementById('plugin-loader')?.value || '',
        });

        const body = document.querySelector('#modal-content .modal-body');
        if (versions.length === 0) {
            body.innerHTML = emptyState('&#9888;', 'No compatible versions found');
            return;
        }

        body.innerHTML = `
            <div class="form-group">
                <label class="form-label">Select Version</label>
                <select class="form-select" id="plugin-install-version">
                    ${versions.slice(0, 30).map(v => `<option value="${v.id}">${escapeHtml(v.name)} (MC ${v.game_versions.slice(0, 3).join(', ')})</option>`).join('')}
                </select>
            </div>
            <button class="btn btn-success" id="plugin-install-btn" onclick="doInstallPlugin(${serverId}, '${projectId}')">
                &#9889; Install Plugin
            </button>
        `;
    } catch (err) {
        document.querySelector('#modal-content .modal-body').innerHTML = emptyState('&#9888;', 'Error', err.message);
    }
}

async function doInstallPlugin(serverId, projectId) {
    const versionId = document.getElementById('plugin-install-version').value;
    const btn = document.getElementById('plugin-install-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Installing...';

    try {
        const result = await API.plugins.install(serverId, {
            source: 'modrinth',
            project_id: projectId,
            version_id: versionId,
        });
        if (result.success) {
            toast(`Installed ${result.plugin_name}`, 'success');
            closeModalDirect();
        } else {
            toast(result.error, 'error');
            btn.disabled = false;
            btn.innerHTML = '&#9889; Install Plugin';
        }
    } catch (err) {
        toast(err.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '&#9889; Install Plugin';
    }
}
