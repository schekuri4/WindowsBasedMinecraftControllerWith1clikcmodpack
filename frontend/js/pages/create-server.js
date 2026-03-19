/**
 * Create Server Page
 */
let createServerState = {
    network: null,
};

async function renderCreateServer() {
    const main = document.getElementById('main-content');
    try {
        createServerState.network = await API.system.network();
    } catch (e) {
        createServerState.network = null;
    }
    main.innerHTML = `
        <div class="page-header">
            <div>
                <h2>Create New Server</h2>
                <div class="subtitle">Set up a new Minecraft server in one click</div>
            </div>
            <button class="btn btn-secondary" onclick="navigate('servers')">&#8592; Back</button>
        </div>

        <div class="card">
            <div class="tabs" id="create-tabs">
                <div class="tab active" onclick="switchCreateTab('blank')">Blank Server</div>
                <div class="tab" onclick="switchCreateTab('modpack')">From Modpack</div>
            </div>

            <div id="create-tab-content">
                ${renderBlankServerForm()}
            </div>
        </div>
    `;

    updateCreateConnectionPreview('blank');
}

function switchCreateTab(tab) {
    const tabs = document.querySelectorAll('#create-tabs .tab');
    tabs[0].classList.toggle('active', tab === 'blank');
    tabs[1].classList.toggle('active', tab === 'modpack');

    const content = document.getElementById('create-tab-content');
    if (tab === 'blank') {
        content.innerHTML = renderBlankServerForm();
        updateCreateConnectionPreview('blank');
    } else {
        content.innerHTML = renderModpackServerForm();
        updateCreateConnectionPreview('modpack');
    }
}

function getCreateNetworkTarget() {
    return createServerState.network?.public_ip || createServerState.network?.local_ips?.[0] || '<server-ip>';
}

function formatMinecraftAddress(host, port) {
    if (!host) return 'Unavailable';
    return Number(port) === 25565 ? host : `${host}:${port}`;
}

function renderCreateConnectionHelp(mode) {
    const portId = mode === 'blank' ? 'cs-port' : 'csm-port';
    const previewId = mode === 'blank' ? 'cs-connect-preview' : 'csm-connect-preview';
    const target = getCreateNetworkTarget();
    const port = parseInt(document.getElementById(portId)?.value || '25565', 10) || 25565;
    const joinAddress = formatMinecraftAddress(target, port);

    return `
        <div class="card" style="background:var(--bg-input);margin-top:16px;">
            <h4 style="margin-bottom:8px;">How Players Connect</h4>
            <p style="color:var(--text-secondary);font-size:13px;margin-bottom:12px;">
                Open inbound TCP port ${port} on Windows Firewall and your cloud or router firewall for public player access.
            </p>
            <div id="${previewId}" style="display:grid;gap:8px;">
                <div><strong>Join Address:</strong> ${escapeHtml(joinAddress)}</div>
                <div style="color:var(--text-muted);font-size:12px;">Panel-detected public IP: ${escapeHtml(createServerState.network?.public_ip || 'Unavailable')}</div>
            </div>
        </div>
    `;
}

function updateCreateConnectionPreview(mode) {
    const portId = mode === 'blank' ? 'cs-port' : 'csm-port';
    const previewId = mode === 'blank' ? 'cs-connect-preview' : 'csm-connect-preview';
    const preview = document.getElementById(previewId);
    if (!preview) return;
    const target = getCreateNetworkTarget();
    const port = parseInt(document.getElementById(portId)?.value || '25565', 10) || 25565;
    preview.innerHTML = `
        <div><strong>Join Address:</strong> ${escapeHtml(formatMinecraftAddress(target, port))}</div>
        <div style="color:var(--text-muted);font-size:12px;">Panel-detected public IP: ${escapeHtml(createServerState.network?.public_ip || 'Unavailable')}</div>
    `;
}

function renderBlankServerForm() {
    return `
        <div class="form-group">
            <label class="form-label">Server Name</label>
            <input class="form-input" id="cs-name" placeholder="My Minecraft Server" value="My Server">
        </div>
        <div class="form-row">
            <div class="form-group">
                <label class="form-label">Server Type</label>
                <select class="form-select" id="cs-type">
                    <option value="vanilla">Vanilla</option>
                    <option value="fabric">Fabric</option>
                    <option value="forge">Forge</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Minecraft Version</label>
                <input class="form-input" id="cs-version" value="1.20.4" placeholder="1.20.4">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label class="form-label">Min RAM</label>
                <select class="form-select" id="cs-minram">
                    <option value="512M">512 MB</option>
                    <option value="1G" selected>1 GB</option>
                    <option value="2G">2 GB</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Max RAM</label>
                <select class="form-select" id="cs-maxram">
                    <option value="2G">2 GB</option>
                    <option value="4G" selected>4 GB</option>
                    <option value="6G">6 GB</option>
                    <option value="8G">8 GB</option>
                    <option value="10G">10 GB</option>
                    <option value="12G">12 GB</option>
                    <option value="16G">16 GB</option>
                </select>
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Server Port</label>
            <input class="form-input" id="cs-port" type="number" min="1" max="65535" value="25565" oninput="updateCreateConnectionPreview('blank')">
        </div>
        ${renderCreateConnectionHelp('blank')}
        <div style="margin-top: 20px;">
            <button class="btn btn-primary" onclick="doCreateServer()" id="cs-btn">&#10010; Create Server</button>
        </div>
    `;
}

function renderModpackServerForm() {
    return `
        <p style="color:var(--text-secondary);margin-bottom:16px;">
            Search for a modpack, then create a server pre-configured with it.
        </p>
        <div class="form-group">
            <label class="form-label">Server Name</label>
            <input class="form-input" id="csm-name" placeholder="My Modpack Server">
        </div>
        <div class="form-row">
            <div class="form-group">
                <label class="form-label">Search Modpacks</label>
                <input class="form-input" id="csm-search" placeholder="Search modpacks..." onkeydown="if(event.key==='Enter')searchModpacksForCreate()">
            </div>
            <div class="form-group" style="display:flex;align-items:flex-end;">
                <button class="btn btn-primary" onclick="searchModpacksForCreate()">Search</button>
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label class="form-label">Max RAM</label>
                <select class="form-select" id="csm-maxram">
                    <option value="4G">4 GB</option>
                    <option value="6G" selected>6 GB</option>
                    <option value="8G">8 GB</option>
                    <option value="10G">10 GB</option>
                    <option value="12G">12 GB</option>
                    <option value="16G">16 GB</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Server Port</label>
                <input class="form-input" id="csm-port" type="number" min="1" max="65535" value="25565" oninput="updateCreateConnectionPreview('modpack')">
            </div>
        </div>
        ${renderCreateConnectionHelp('modpack')}
        <div id="csm-results" style="margin-top:16px;"></div>
    `;
}

async function doCreateServer() {
    const btn = document.getElementById('cs-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Creating...';

    const data = {
        name: document.getElementById('cs-name').value || 'My Server',
        server_type: document.getElementById('cs-type').value,
        minecraft_version: document.getElementById('cs-version').value,
        min_ram: document.getElementById('cs-minram').value,
        max_ram: document.getElementById('cs-maxram').value,
        port: parseInt(document.getElementById('cs-port').value) || 25565,
    };

    try {
        const result = await API.servers.create(data);
        if (result.warning) {
            toast(result.warning, 'warning');
        }
        toast(`Server "${data.name}" created!`, 'success');
        navigate('server-detail', { id: result.server_id });
    } catch (err) {
        toast(err.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '&#10010; Create Server';
    }
}

async function searchModpacksForCreate() {
    const query = document.getElementById('csm-search').value;
    const results = document.getElementById('csm-results');
    results.innerHTML = loading('Searching...');

    try {
        const data = await API.modpacks.searchModrinth({ query, limit: 10 });
        if (data.results.length === 0) {
            results.innerHTML = emptyState('&#128270;', 'No modpacks found');
            return;
        }
        results.innerHTML = `
            <div class="mod-grid">
                ${data.results.map(p => `
                    <div class="mod-card">
                        <img class="mod-icon" src="${p.icon_url || ''}" alt="" onerror="this.style.display='none'">
                        <div class="mod-card-info">
                            <h4>${escapeHtml(p.name)}</h4>
                            <p>${escapeHtml(p.description)}</p>
                            <div class="mod-card-meta">
                                <span>&#11015; ${formatNumber(p.downloads)}</span>
                                <span>${escapeHtml(p.author)}</span>
                            </div>
                        </div>
                        <div class="mod-card-actions">
                            <button class="btn btn-primary btn-sm" onclick="selectModpackForCreate('${p.id}', '${encodeURIComponent(p.name || '')}')">Select</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        results.innerHTML = emptyState('&#9888;', 'Search failed', err.message);
    }
}

async function selectModpackForCreate(projectId, encodedName) {
    const name = decodeURIComponent(encodedName || '');
    const serverName = document.getElementById('csm-name').value || name + ' Server';
    const maxRam = document.getElementById('csm-maxram').value;
    const port = parseInt(document.getElementById('csm-port').value || '25565', 10) || 25565;
    const results = document.getElementById('csm-results');
    results.innerHTML = loading('Fetching modpack versions...');

    try {
        const versions = await API.modpacks.versions(projectId);
        if (versions.length === 0) {
            results.innerHTML = emptyState('&#9888;', 'No server versions found for this modpack');
            return;
        }

        const v = versions[0]; // Latest version
        results.innerHTML = `
            <div class="card" style="background:var(--bg-input)">
                <h4>Selected: ${escapeHtml(name)} - ${escapeHtml(v.name)}</h4>
                <p style="color:var(--text-secondary);font-size:13px;margin:8px 0;">
                    MC: ${v.game_versions.join(', ')} &middot; Loaders: ${v.loaders.join(', ')} &middot; Port: ${port}
                </p>
                <button class="btn btn-success" id="csm-install-btn" onclick="createServerFromModpack('${encodeURIComponent(serverName)}', '${maxRam}', ${port}, '${projectId}', '${v.id}')">
                    &#9889; Create Server with this Modpack
                </button>
            </div>
        `;
    } catch (err) {
        results.innerHTML = emptyState('&#9888;', 'Error', err.message);
    }
}

async function createServerFromModpack(encodedName, maxRam, port, projectId, versionId) {
    const name = decodeURIComponent(encodedName || '');
    const btn = document.getElementById('csm-install-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Creating server & installing modpack...';

    try {
        // Create blank server first
        const server = await API.servers.create({
            name,
            server_type: 'vanilla',
            minecraft_version: '1.20.4',
            min_ram: '2G',
            max_ram: maxRam,
            port,
        });

        // Install modpack onto it
        const result = await API.modpacks.install(server.server_id, {
            source: 'modrinth',
            project_id: projectId,
            version_id: versionId,
        });

        if (result.success) {
            toast(`Modpack installed! ${result.files_installed} files`, 'success');
            navigate('server-detail', { id: server.server_id });
        } else {
            toast(result.error || 'Modpack installation failed', 'error');
            navigate('server-detail', { id: server.server_id });
        }
    } catch (err) {
        toast(err.message, 'error');
        btn.disabled = false;
        btn.innerHTML = '&#9889; Create Server with this Modpack';
    }
}
