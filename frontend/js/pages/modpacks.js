/**
 * Modpacks Browser Page
 */
let modpackState = {
    source: 'modrinth',
    query: '',
    mcVersion: '',
    loader: '',
    offset: 0,
    features: { curseforge_enabled: false },
};

async function renderModpacks() {
    const main = document.getElementById('main-content');
    try {
        modpackState.features = await API.system.features();
    } catch (e) {
        modpackState.features = { curseforge_enabled: false };
    }
    if (!modpackState.features.curseforge_enabled && modpackState.source === 'curseforge') {
        modpackState.source = 'modrinth';
    }

    main.innerHTML = `
        <div class="page-header">
            <div>
                <h2>Modpack Browser</h2>
                <div class="subtitle">Browse modpacks from Modrinth & CurseForge</div>
            </div>
        </div>

        <div class="card" style="margin-bottom:20px">
            <div class="form-row" style="grid-template-columns: 1fr 150px 150px 150px auto;">
                <div class="form-group" style="margin:0">
                    <input class="form-input" id="mp-search" placeholder="Search modpacks..." value="${escapeHtml(modpackState.query)}"
                        onkeydown="if(event.key==='Enter')searchModpacks()">
                </div>
                <div class="form-group" style="margin:0">
                    <select class="form-select" id="mp-source" onchange="modpackState.source=this.value">
                        <option value="modrinth">Modrinth</option>
                        <option value="curseforge" ${modpackState.features.curseforge_enabled ? '' : 'disabled'}>CurseForge${modpackState.features.curseforge_enabled ? '' : ' (API key required)'}</option>
                    </select>
                </div>
                <div class="form-group" style="margin:0">
                    <input class="form-input" id="mp-version" placeholder="MC Version" value="${escapeHtml(modpackState.mcVersion)}">
                </div>
                <div class="form-group" style="margin:0">
                    <select class="form-select" id="mp-loader">
                        <option value="">Any Loader</option>
                        <option value="forge">Forge</option>
                        <option value="fabric">Fabric</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="searchModpacks()">&#128270; Search</button>
            </div>
        </div>

        <div class="card" style="margin-bottom:20px;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <span style="color:var(--text-secondary);font-size:14px;">Install modpacks from each server page to avoid selecting a target server twice.</span>
            <button class="btn btn-secondary btn-sm" onclick="navigate('servers')">Open Servers</button>
        </div>

        <div id="mp-results">
            ${loading('Loading modpacks...')}
        </div>
    `;

    // Preserve filter selections across re-renders.
    const sourceEl = document.getElementById('mp-source');
    const loaderEl = document.getElementById('mp-loader');
    if (sourceEl) sourceEl.value = modpackState.source || 'modrinth';
    if (loaderEl) loaderEl.value = modpackState.loader || '';

    // Populate with initial results so users do not need to search first.
    await searchModpacks();
}

async function searchModpacks() {
    modpackState.query = document.getElementById('mp-search').value;
    modpackState.mcVersion = document.getElementById('mp-version').value;
    modpackState.loader = document.getElementById('mp-loader')?.value || '';
    modpackState.source = document.getElementById('mp-source').value;
    if (modpackState.source === 'curseforge' && !modpackState.features.curseforge_enabled) {
        modpackState.source = 'modrinth';
        const sourceEl = document.getElementById('mp-source');
        if (sourceEl) sourceEl.value = 'modrinth';
        toast('CurseForge search is unavailable until CURSEFORGE_API_KEY is configured', 'warning');
    }
    modpackState.offset = 0;

    const results = document.getElementById('mp-results');
    results.innerHTML = loading('Searching modpacks...');

    try {
        let data;
        if (modpackState.source === 'modrinth') {
            data = await API.modpacks.searchModrinth({
                query: modpackState.query,
                mc_version: modpackState.mcVersion,
                loader: modpackState.loader,
                offset: modpackState.offset,
                limit: 20,
            });
        } else {
            data = await API.modpacks.searchCurseforge({
                query: modpackState.query,
                mc_version: modpackState.mcVersion,
                offset: modpackState.offset,
                limit: 20,
            });
        }

        if (data.results.length === 0) {
            results.innerHTML = emptyState('&#128270;', 'No modpacks found', 'Try different search terms.');
            return;
        }

        results.innerHTML = `
            <p style="color:var(--text-muted);font-size:13px;margin-bottom:12px;">${data.total} results</p>
            <div class="mod-grid">
                ${data.results.map(p => modpackCard(p)).join('')}
            </div>
        `;
    } catch (err) {
        results.innerHTML = emptyState('&#9888;', 'Search failed', err.message);
    }
}

function modpackCard(p) {
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
                    <span class="tag">${escapeHtml(p.source)}</span>
                </div>
            </div>
            <div class="mod-card-actions">
                ${p.source === 'modrinth' ? `<button class="btn btn-secondary btn-sm" onclick="viewModpackDetail('${p.id}')">Details</button>` : ''}
            </div>
        </div>
    `;
}

async function viewModpackDetail(projectId) {
    showModal(`
        <div class="modal-header"><h3>Modpack Details</h3><button class="btn-icon" onclick="closeModalDirect()">&#10005;</button></div>
        <div class="modal-body">${loading('Loading...')}</div>
    `);
    try {
        const detail = await API.modpacks.detail(projectId);
        document.querySelector('#modal-content .modal-body').innerHTML = `
            <div style="display:flex;gap:16px;margin-bottom:16px;">
                ${detail.icon_url ? `<img src="${detail.icon_url}" style="width:80px;height:80px;border-radius:8px;">` : ''}
                <div>
                    <h3>${escapeHtml(detail.name)}</h3>
                    <p style="color:var(--text-secondary)">${escapeHtml(detail.description)}</p>
                    <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">
                        ${(detail.categories || []).map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('')}
                    </div>
                </div>
            </div>
            <div style="font-size:13px;color:var(--text-secondary);">
                <p>&#11015; ${formatNumber(detail.downloads)} downloads</p>
                <p>Minecraft versions: ${(detail.game_versions || []).slice(0, 10).join(', ')}</p>
                <p>Loaders: ${(detail.loaders || []).join(', ')}</p>
            </div>
        `;
    } catch (err) {
        document.querySelector('#modal-content .modal-body').innerHTML = emptyState('&#9888;', 'Error', err.message);
    }
}
