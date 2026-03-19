/**
 * Plugin Browser Page
 */
let pluginState = {
    source: 'modrinth',
    query: '',
    mcVersion: '',
    loader: '',
    offset: 0,
};

async function renderPlugins() {
    const main = document.getElementById('main-content');

    main.innerHTML = `
        <div class="page-header">
            <div>
                <h2>Plugin Browser</h2>
                <div class="subtitle">Browse server plugins from Modrinth, Hangar, and Spiget</div>
            </div>
        </div>

        <div class="card" style="margin-bottom:20px">
            <div class="form-row" style="grid-template-columns: 1fr 150px 150px 150px auto;">
                <div class="form-group" style="margin:0">
                    <input class="form-input" id="plugin-search" placeholder="Search plugins..." value="${escapeHtml(pluginState.query)}"
                        onkeydown="if(event.key==='Enter')searchPlugins()">
                </div>
                <div class="form-group" style="margin:0">
                    <select class="form-select" id="plugin-source" onchange="pluginState.source=this.value; searchPlugins()">
                        <option value="modrinth">Modrinth</option>
                        <option value="hangar">Hangar</option>
                        <option value="spiget">Spiget</option>
                    </select>
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

        <div class="card" style="margin-bottom:20px;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <span style="color:var(--text-secondary);font-size:14px;">Install plugins from each server page so the target server is chosen once.</span>
            <button class="btn btn-secondary btn-sm" onclick="navigate('servers')">Open Servers</button>
        </div>

        <div id="plugin-results">
            ${loading('Loading plugins...')}
        </div>
    `;

    const sourceEl = document.getElementById('plugin-source');
    const loaderEl = document.getElementById('plugin-loader');
    if (sourceEl) sourceEl.value = pluginState.source || 'modrinth';
    if (loaderEl) loaderEl.value = pluginState.loader || '';

    await searchPlugins();
}

async function searchPlugins() {
    pluginState.query = document.getElementById('plugin-search').value;
    pluginState.source = document.getElementById('plugin-source')?.value || 'modrinth';
    pluginState.mcVersion = document.getElementById('plugin-version').value;
    pluginState.loader = document.getElementById('plugin-loader')?.value || '';
    pluginState.offset = 0;

    const results = document.getElementById('plugin-results');
    results.innerHTML = loading('Searching plugins...');

    try {
        let data;
        const params = {
            query: pluginState.query,
            mc_version: pluginState.mcVersion,
            loader: pluginState.loader,
            offset: pluginState.offset,
            limit: 20,
        };
        if (pluginState.source === 'hangar') {
            data = await API.plugins.searchHangar(params);
        } else if (pluginState.source === 'spiget') {
            data = await API.plugins.searchSpiget(params);
        } else {
            data = await API.plugins.searchModrinth(params);
        }

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
        </div>
    `;
}
