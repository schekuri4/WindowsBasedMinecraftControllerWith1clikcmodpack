/**
 * Mods Browser Page  
 */
let modState = {
    query: '',
    mcVersion: '',
    loader: '',
    category: '',
    source: 'modrinth',
    offset: 0,
    queue: [],  // Queued mods for batch install
};

async function renderMods() {
    const main = document.getElementById('main-content');

    let servers = [];
    try { servers = await API.servers.list(); } catch (e) { /* ignore */ }

    main.innerHTML = `
        <div class="page-header">
            <div>
                <h2>Mod Browser</h2>
                <div class="subtitle">Browse, search, and install mods from Modrinth & CurseForge</div>
            </div>
        </div>

        <div class="card" style="margin-bottom:20px">
            <div class="form-row" style="grid-template-columns: 1fr 150px 150px 150px auto;">
                <div class="form-group" style="margin:0">
                    <input class="form-input" id="mod-search" placeholder="Search mods..." value="${escapeHtml(modState.query)}"
                        onkeydown="if(event.key==='Enter')searchMods()">
                </div>
                <div class="form-group" style="margin:0">
                    <select class="form-select" id="mod-source" onchange="modState.source=this.value">
                        <option value="modrinth">Modrinth</option>
                        <option value="curseforge">CurseForge</option>
                    </select>
                </div>
                <div class="form-group" style="margin:0">
                    <input class="form-input" id="mod-version" placeholder="MC Version" value="${escapeHtml(modState.mcVersion)}">
                </div>
                <div class="form-group" style="margin:0">
                    <select class="form-select" id="mod-loader">
                        <option value="">Any Loader</option>
                        <option value="forge">Forge</option>
                        <option value="fabric">Fabric</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="searchMods()">&#128270; Search</button>
            </div>
        </div>

        ${servers.length > 0 ? `
            <div class="card" style="margin-bottom:20px;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="color:var(--text-secondary);font-size:14px;">Install to:</span>
                    <select class="form-select" id="mod-target-server" style="width:auto;min-width:200px;">
                        ${servers.map(s => `<option value="${s.id}">${escapeHtml(s.name)} (${s.server_type} ${s.minecraft_version})</option>`).join('')}
                    </select>
                </div>
                <div style="display:flex;align-items:center;gap:12px;">
                    <span id="mod-queue-count" style="color:var(--text-muted);font-size:13px;">Queue: ${modState.queue.length}</span>
                    <button class="btn btn-success btn-sm" onclick="installModQueue()" ${modState.queue.length === 0 ? 'disabled' : ''} id="mod-queue-btn">
                        &#9889; Install Queue (${modState.queue.length})
                    </button>
                </div>
            </div>
        ` : ''}

        <div id="mod-results">
            ${emptyState('&#128295;', 'Search for mods', 'Type a query and click Search.')}
        </div>
    `;
}

async function searchMods() {
    modState.query = document.getElementById('mod-search').value;
    modState.mcVersion = document.getElementById('mod-version').value;
    modState.loader = document.getElementById('mod-loader')?.value || '';
    modState.source = document.getElementById('mod-source').value;
    modState.offset = 0;

    const results = document.getElementById('mod-results');
    results.innerHTML = loading('Searching mods...');

    try {
        let data;
        if (modState.source === 'modrinth') {
            data = await API.mods.searchModrinth({
                query: modState.query,
                mc_version: modState.mcVersion,
                loader: modState.loader,
                category: modState.category,
                offset: modState.offset,
                limit: 20,
            });
        } else {
            data = await API.mods.searchCurseforge({
                query: modState.query,
                mc_version: modState.mcVersion,
                offset: modState.offset,
                limit: 20,
            });
        }

        if (data.results.length === 0) {
            results.innerHTML = emptyState('&#128270;', 'No mods found', 'Try different search terms.');
            return;
        }

        results.innerHTML = `
            <p style="color:var(--text-muted);font-size:13px;margin-bottom:12px;">${data.total} results</p>
            <div class="mod-grid">
                ${data.results.map(m => modCard(m)).join('')}
            </div>
        `;
    } catch (err) {
        results.innerHTML = emptyState('&#9888;', 'Search failed', err.message);
    }
}

function modCard(m) {
    const queued = modState.queue.some(q => q.project_id === m.id);
    return `
        <div class="mod-card" id="mod-card-${m.id}">
            <img class="mod-icon" src="${m.icon_url || ''}" alt="" onerror="this.style.display='none'">
            <div class="mod-card-info">
                <h4>${escapeHtml(m.name)}</h4>
                <p>${escapeHtml(m.description)}</p>
                <div class="mod-card-meta">
                    <span>&#11015; ${formatNumber(m.downloads)}</span>
                    <span>${escapeHtml(m.author)}</span>
                    ${(m.categories || []).slice(0, 3).map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('')}
                </div>
            </div>
            <div class="mod-card-actions">
                <button class="btn btn-primary btn-sm" onclick="showModInstall('${m.id}', '${escapeHtml(m.name)}', '${m.source}')">Install</button>
                <button class="btn btn-sm ${queued ? 'btn-warning' : 'btn-secondary'}" onclick="toggleModQueue('${m.id}', '${escapeHtml(m.name)}', '${m.source}')" id="queue-btn-${m.id}">
                    ${queued ? '&#10004; Queued' : '+ Queue'}
                </button>
            </div>
        </div>
    `;
}

async function showModInstall(projectId, name, source) {
    const serverSelect = document.getElementById('mod-target-server');
    if (!serverSelect) {
        toast('Create a server first', 'warning');
        return;
    }
    const serverId = serverSelect.value;

    if (source === 'modrinth') {
        showModal(`
            <div class="modal-header"><h3>Install: ${escapeHtml(name)}</h3><button class="btn-icon" onclick="closeModalDirect()">&#10005;</button></div>
            <div class="modal-body">${loading('Loading versions...')}</div>
        `);
        try {
            const mcVersion = document.getElementById('mod-version')?.value || '';
            const loader = document.getElementById('mod-loader')?.value || '';
            const versions = await API.mods.versions(projectId, { mc_version: mcVersion, loader });

            const body = document.querySelector('#modal-content .modal-body');
            if (versions.length === 0) {
                body.innerHTML = emptyState('&#9888;', 'No compatible versions found');
                return;
            }
            body.innerHTML = `
                <div class="form-group">
                    <label class="form-label">Select Version</label>
                    <select class="form-select" id="mod-install-version">
                        ${versions.slice(0, 30).map(v => `<option value="${v.id}">${escapeHtml(v.name)} (MC ${v.game_versions.slice(0, 3).join(', ')})</option>`).join('')}
                    </select>
                </div>
                ${versions[0].dependencies?.some(d => d.dependency_type === 'required') ? `
                    <p style="font-size:13px;color:var(--warning);">&#9888; This mod has required dependencies that will be auto-installed.</p>
                ` : ''}
                <button class="btn btn-success" id="mod-install-btn" onclick="doInstallMod(${serverId}, '${source}', '${projectId}')">
                    &#9889; Install Mod
                </button>
            `;
        } catch (err) {
            document.querySelector('#modal-content .modal-body').innerHTML = emptyState('&#9888;', 'Error', err.message);
        }
    }
}

async function doInstallMod(serverId, source, projectId) {
    const versionId = document.getElementById('mod-install-version').value;
    const btn = document.getElementById('mod-install-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Installing...';

    try {
        const result = await API.mods.install(serverId, {
            source,
            project_id: projectId,
            version_id: versionId,
        });
        if (result.success) {
            let msg = `Installed ${result.mod_name}`;
            if (result.dependencies_installed?.length > 0) {
                msg += ` + ${result.dependencies_installed.length} dependencies`;
            }
            toast(msg, 'success');
            closeModalDirect();
        } else {
            toast(result.error, 'error');
            btn.disabled = false;
            btn.innerHTML = '&#9889; Install Mod';
        }
    } catch (err) {
        toast(err.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '&#9889; Install Mod';
    }
}

// --- Queue system ---
async function toggleModQueue(projectId, name, source) {
    const idx = modState.queue.findIndex(q => q.project_id === projectId);
    if (idx >= 0) {
        modState.queue.splice(idx, 1);
    } else {
        // Need to get latest version
        try {
            const mcVersion = document.getElementById('mod-version')?.value || '';
            const loader = document.getElementById('mod-loader')?.value || '';
            const versions = await API.mods.versions(projectId, { mc_version: mcVersion, loader });
            if (versions.length === 0) {
                toast('No compatible version found', 'warning');
                return;
            }
            modState.queue.push({
                source,
                project_id: projectId,
                version_id: versions[0].id,
                name,
            });
        } catch (err) {
            toast('Failed to fetch version: ' + err.message, 'error');
            return;
        }
    }
    updateQueueUI();
}

function updateQueueUI() {
    const countEl = document.getElementById('mod-queue-count');
    const btnEl = document.getElementById('mod-queue-btn');
    if (countEl) countEl.textContent = `Queue: ${modState.queue.length}`;
    if (btnEl) {
        btnEl.textContent = `⚡ Install Queue (${modState.queue.length})`;
        btnEl.disabled = modState.queue.length === 0;
    }
    // Update individual queue buttons
    modState.queue.forEach(q => {
        const btn = document.getElementById(`queue-btn-${q.project_id}`);
        if (btn) { btn.textContent = '✔ Queued'; btn.className = 'btn btn-sm btn-warning'; }
    });
}

async function installModQueue() {
    const serverSelect = document.getElementById('mod-target-server');
    if (!serverSelect) { toast('No server selected', 'warning'); return; }
    const serverId = serverSelect.value;

    if (modState.queue.length === 0) return;

    toast(`Installing ${modState.queue.length} mods...`, 'info');
    try {
        const mods = modState.queue.map(q => ({
            source: q.source,
            project_id: q.project_id,
            version_id: q.version_id,
        }));
        const results = await API.mods.batchInstall(serverId, mods);
        const success = results.filter(r => r.success).length;
        toast(`Installed ${success}/${results.length} mods`, success === results.length ? 'success' : 'warning');
        modState.queue = [];
        updateQueueUI();
    } catch (err) {
        toast(err.message, 'error');
    }
}
