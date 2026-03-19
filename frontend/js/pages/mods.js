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
    features: { curseforge_enabled: false },
};

async function renderMods() {
    const main = document.getElementById('main-content');
    try {
        modState.features = await API.system.features();
    } catch (e) {
        modState.features = { curseforge_enabled: false };
    }
    if (!modState.features.curseforge_enabled && modState.source === 'curseforge') {
        modState.source = 'modrinth';
    }

    main.innerHTML = `
        <div class="page-header">
            <div>
                <h2>Mod Browser</h2>
                <div class="subtitle">Browse and search mods from Modrinth & CurseForge</div>
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
                        <option value="curseforge" ${modState.features.curseforge_enabled ? '' : 'disabled'}>CurseForge${modState.features.curseforge_enabled ? '' : ' (API key required)'}</option>
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

        <div class="card" style="margin-bottom:20px;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <span style="color:var(--text-secondary);font-size:14px;">Install mods from each server page to keep browsing separate from the target server.</span>
            <button class="btn btn-secondary btn-sm" onclick="navigate('servers')">Open Servers</button>
        </div>

        <div id="mod-results">
            ${loading('Loading mods...')}
        </div>
    `;

    // Preserve filter selections across re-renders.
    const sourceEl = document.getElementById('mod-source');
    const loaderEl = document.getElementById('mod-loader');
    if (sourceEl) sourceEl.value = modState.source || 'modrinth';
    if (loaderEl) loaderEl.value = modState.loader || '';

    // Populate with initial results so users do not need to search first.
    await searchMods();
}

async function searchMods() {
    modState.query = document.getElementById('mod-search').value;
    modState.mcVersion = document.getElementById('mod-version').value;
    modState.loader = document.getElementById('mod-loader')?.value || '';
    modState.source = document.getElementById('mod-source').value;
    if (modState.source === 'curseforge' && !modState.features.curseforge_enabled) {
        modState.source = 'modrinth';
        const sourceEl = document.getElementById('mod-source');
        if (sourceEl) sourceEl.value = 'modrinth';
        toast('CurseForge search is unavailable until CURSEFORGE_API_KEY is configured', 'warning');
    }
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
        </div>
    `;
}
