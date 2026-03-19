/**
 * Server Detail Page - Console, Settings, Mods, Backups
 */
let consoleInterval = null;
let consoleAutoScroll = true;
let consoleFilter = '';

function formatServerJoinAddress(host, port) {
    if (!host) return 'Unavailable';
    return Number(port) === 25565 ? host : `${host}:${port}`;
}

function renderServerConnectionCard(server, network) {
    const target = network?.public_ip || network?.local_ips?.[0] || '';
    const joinAddress = formatServerJoinAddress(target, server.port);
    return `
        <div class="card" style="margin-bottom:20px;">
            <h3 style="margin-bottom:12px;">How To Connect</h3>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Join Address</label>
                    <input class="form-input" value="${escapeHtml(joinAddress)}" readonly>
                </div>
                <div class="form-group">
                    <label class="form-label">Server Port</label>
                    <input class="form-input" value="${server.port}" readonly>
                </div>
            </div>
            <p style="color:var(--text-secondary);font-size:13px;">
                Players connect with the join address above. Open inbound TCP port ${server.port} in Windows Firewall and your cloud or router firewall.
            </p>
        </div>
    `;
}

async function renderServerDetail(params) {
    const main = document.getElementById('main-content');
    main.innerHTML = loading('Loading server...');
    clearInterval(consoleInterval);

    try {
        const [server, status, network] = await Promise.all([
            API.servers.get(params.id),
            API.servers.status(params.id),
            API.system.network().catch(() => null),
        ]);

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <h2>${escapeHtml(server.name)}</h2>
                    <div class="subtitle">
                        ${serverTypeTag(server.server_type)} MC ${escapeHtml(server.minecraft_version || '?')}
                        &nbsp;&middot;&nbsp; Port ${server.port}
                        &nbsp;&middot;&nbsp; ${statusBadge(status.status)}
                    </div>
                </div>
                <div class="btn-group">
                    ${status.status === 'running'
                        ? `<button class="btn btn-danger" onclick="stopServer(${server.id})">&#9632; Stop</button>`
                        : `<button class="btn btn-success" onclick="startServer(${server.id})">&#9654; Start</button>`
                    }
                    <button class="btn btn-secondary" onclick="navigate('servers')">&#8592; Back</button>
                </div>
            </div>

            ${renderServerConnectionCard(server, network)}

            <!-- Resource stats -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon cpu">&#128187;</div>
                    <div>
                        <div class="stat-value" id="srv-cpu">${status.cpu_percent}%</div>
                        <div class="stat-label">CPU</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon ram">&#128202;</div>
                    <div>
                        <div class="stat-value" id="srv-ram">${status.memory_mb} MB</div>
                        <div class="stat-label">Memory (${server.max_ram} max)</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon disk">&#128191;</div>
                    <div>
                        <div class="stat-value">${status.disk_mb} MB</div>
                        <div class="stat-label">Disk Usage</div>
                    </div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="tabs">
                <div class="tab active" onclick="switchServerTab('console', ${server.id})">Console</div>
                <div class="tab" onclick="switchServerTab('settings', ${server.id})">Settings</div>
                <div class="tab" onclick="switchServerTab('files', ${server.id})">Files</div>
                <div class="tab" onclick="switchServerTab('mods', ${server.id})">Mods</div>
                <div class="tab" onclick="switchServerTab('srv-backups', ${server.id})">Backups</div>
            </div>

            <div id="server-tab-content">
                ${renderConsoleTab(server.id)}
            </div>
        `;

        // Start polling console
        startConsolePolling(server.id);
    } catch (err) {
        main.innerHTML = `<div class="card">${emptyState('&#9888;', 'Server not found', err.message)}</div>`;
    }
}

function switchServerTab(tab, serverId) {
    document.querySelectorAll('.tabs .tab').forEach((t, i) => {
        t.classList.toggle('active', t.textContent.trim().toLowerCase().replace(/\s+/g, '-') ===
            {console: 'console', settings: 'settings', mods: 'mods', 'srv-backups': 'backups'}[tab]);
    });

    // Simpler approach: activate by index
    const tabs = document.querySelectorAll('.tabs .tab');
    tabs.forEach(t => t.classList.remove('active'));
    const tabIndex = { console: 0, settings: 1, files: 2, mods: 3, 'srv-backups': 4 }[tab];
    if (tabs[tabIndex]) tabs[tabIndex].classList.add('active');

    const content = document.getElementById('server-tab-content');
    clearInterval(consoleInterval);

    if (tab === 'console') {
        content.innerHTML = renderConsoleTab(serverId);
        startConsolePolling(serverId);
    } else if (tab === 'settings') {
        loadServerSettings(serverId);
    } else if (tab === 'files') {
        loadServerFiles(serverId);
    } else if (tab === 'mods') {
        loadServerMods(serverId);
    } else if (tab === 'srv-backups') {
        loadServerBackups(serverId);
    }
}

function renderConsoleTab(serverId) {
    return `
        <div class="card" style="padding:0;overflow:hidden;">
            <div class="console-toolbar">
                <div class="console-toolbar-left">
                    <span class="console-line-count" id="console-line-count">0 lines</span>
                    <input class="console-filter" id="console-filter" placeholder="Filter logs..." oninput="consoleFilter=this.value.toLowerCase()">
                </div>
                <div class="console-toolbar-right">
                    <button class="btn btn-sm console-tool-btn" id="console-scroll-btn" onclick="toggleAutoScroll()" title="Auto-scroll">
                        &#8595; Auto-scroll: ON
                    </button>
                    <button class="btn btn-sm console-tool-btn" onclick="clearConsoleDisplay()" title="Clear display">Clear</button>
                </div>
            </div>
            <div class="console" id="console-output">Connecting to console...</div>
            <div class="console-input-row">
                <input class="form-input" id="console-cmd" placeholder="Type a command..." onkeydown="if(event.key==='Enter')sendCmd(${serverId})">
                <button class="btn btn-primary" onclick="sendCmd(${serverId})">Send</button>
            </div>
        </div>
    `;
}

function toggleAutoScroll() {
    consoleAutoScroll = !consoleAutoScroll;
    const btn = document.getElementById('console-scroll-btn');
    if (btn) {
        btn.innerHTML = consoleAutoScroll ? '&#8595; Auto-scroll: ON' : '&#8645; Auto-scroll: OFF';
        btn.classList.toggle('active', consoleAutoScroll);
    }
    if (consoleAutoScroll) {
        const el = document.getElementById('console-output');
        if (el) el.scrollTop = el.scrollHeight;
    }
}

function clearConsoleDisplay() {
    const el = document.getElementById('console-output');
    if (el) el.innerHTML = '<span class="console-line" style="color:var(--text-muted)">Console cleared.</span>';
}

function startConsolePolling(serverId) {
    fetchConsole(serverId);
    consoleInterval = setInterval(() => fetchConsole(serverId), 2000);
}

async function fetchConsole(serverId) {
    try {
        const data = await API.servers.console(serverId);
        const el = document.getElementById('console-output');
        if (!el) return;

        // Detect if user has scrolled up (not near bottom)
        const wasNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;

        if (data.lines.length === 0) {
            el.innerHTML = '<span class="console-line" style="color:var(--text-muted)">No output yet. Start the server to see console output.</span>';
        } else {
            const filtered = consoleFilter
                ? data.lines.filter(l => l.toLowerCase().includes(consoleFilter))
                : data.lines;
            el.innerHTML = filtered.map(line => {
                let cls = '';
                if (/\berror|exception|fatal/i.test(line)) cls = 'error';
                else if (/\bwarn/i.test(line)) cls = 'warn';
                else if (/\binfo/i.test(line)) cls = 'info';
                return `<div class="console-line ${cls}">${escapeHtml(line)}</div>`;
            }).join('');

            // Only auto-scroll if the toggle is on AND user was already near the bottom
            if (consoleAutoScroll && wasNearBottom) {
                el.scrollTop = el.scrollHeight;
            }
        }

        // Update line count
        const countEl = document.getElementById('console-line-count');
        if (countEl) countEl.textContent = `${data.lines.length} lines`;
    } catch (e) { /* ignore */ }
}

async function sendCmd(serverId) {
    const input = document.getElementById('console-cmd');
    const cmd = input.value.trim();
    if (!cmd) return;
    input.value = '';
    try {
        await API.servers.command(serverId, cmd);
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function startServer(serverId) {
    try {
        const result = await API.servers.start(serverId);
        if (result.success) {
            toast('Server starting...', 'success');
            navigate('server-detail', { id: serverId });
        } else {
            toast(result.error || 'Failed to start', 'error');
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function stopServer(serverId) {
    try {
        const result = await API.servers.stop(serverId);
        if (result.success) {
            toast('Server stopped', 'info');
            navigate('server-detail', { id: serverId });
        } else {
            toast(result.error || 'Failed to stop', 'error');
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}

// --- Settings Tab ---
async function loadServerSettings(serverId) {
    const content = document.getElementById('server-tab-content');
    content.innerHTML = loading('Loading settings...');
    try {
        const server = await API.servers.get(serverId);
        const javas = await API.servers.java();
        content.innerHTML = `
            <div class="card">
                <h3 style="margin-bottom:16px;">Server Settings</h3>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Server Name</label>
                        <input class="form-input" id="set-name" value="${escapeHtml(server.name)}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Port</label>
                        <input class="form-input" id="set-port" type="number" value="${server.port}">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Min RAM</label>
                        <input class="form-input" id="set-minram" value="${escapeHtml(server.min_ram)}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Max RAM</label>
                        <input class="form-input" id="set-maxram" value="${escapeHtml(server.max_ram)}">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">JVM Arguments</label>
                    <input class="form-input" id="set-jvm" value="${escapeHtml(server.jvm_args)}">
                </div>
                <div class="form-group">
                    <label class="form-label">Java Path</label>
                    <select class="form-select" id="set-java">
                        <option value="java" ${server.java_path === 'java' ? 'selected' : ''}>System Default (java)</option>
                        ${javas.map(j => `<option value="${escapeHtml(j.path)}" ${server.java_path === j.path ? 'selected' : ''}>${escapeHtml(j.vendor)} ${escapeHtml(j.version)} (${j.is_64bit ? '64-bit' : '32-bit'})</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Server Jar</label>
                    <input class="form-input" id="set-jar" value="${escapeHtml(server.server_jar)}">
                </div>
                <div class="form-group" style="margin-top:8px">
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="set-autostart" ${server.auto_start ? 'checked' : ''}> Auto-start on panel launch
                    </label>
                </div>
                <div class="form-group">
                    <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                        <input type="checkbox" id="set-autorestart" ${server.auto_restart ? 'checked' : ''}> Auto-restart on crash
                    </label>
                </div>
                <div style="display:flex;gap:8px;margin-top:20px;">
                    <button class="btn btn-primary" onclick="saveServerSettings(${serverId})">Save Settings</button>
                    <button class="btn btn-danger" onclick="confirmDeleteServer(${serverId})">Delete Server</button>
                </div>
                <p style="font-size:12px;color:var(--text-muted);margin-top:12px;">Server path: ${escapeHtml(server.path)}</p>
            </div>
        `;
    } catch (err) {
        content.innerHTML = `<div class="card">${emptyState('&#9888;', 'Error', err.message)}</div>`;
    }
}

async function saveServerSettings(serverId) {
    const data = {
        name: document.getElementById('set-name').value,
        port: parseInt(document.getElementById('set-port').value) || 25565,
        min_ram: document.getElementById('set-minram').value,
        max_ram: document.getElementById('set-maxram').value,
        jvm_args: document.getElementById('set-jvm').value,
        java_path: document.getElementById('set-java').value,
        server_jar: document.getElementById('set-jar').value,
        auto_start: document.getElementById('set-autostart').checked,
        auto_restart: document.getElementById('set-autorestart').checked,
    };
    try {
        await API.servers.update(serverId, data);
        toast('Settings saved', 'success');
    } catch (err) {
        toast(err.message, 'error');
    }
}

function confirmDeleteServer(serverId) {
    showModal(`
        <div class="modal-header"><h3>Delete Server</h3></div>
        <div class="modal-body">
            <p>Are you sure? This action cannot be undone.</p>
            <div class="form-group" style="margin-top:12px">
                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                    <input type="checkbox" id="del-files"> Also delete server files from disk
                </label>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" onclick="closeModalDirect()">Cancel</button>
            <button class="btn btn-danger" onclick="doDeleteServer(${serverId})">Delete</button>
        </div>
    `);
}

async function doDeleteServer(serverId) {
    const deleteFiles = document.getElementById('del-files').checked;
    try {
        await API.servers.delete(serverId, deleteFiles);
        toast('Server deleted', 'info');
        closeModalDirect();
        navigate('servers');
    } catch (err) {
        toast(err.message, 'error');
    }
}

// All server types that support mods (used for compatibility filtering)
const MOD_LOADER_TYPES = ['forge', 'neoforge', 'fabric', 'quilt', 'liteloader', 'rift'];

function getServerLoader(serverType) {
    return MOD_LOADER_TYPES.includes(serverType) ? serverType : '';
}

// --- Mods Tab ---
async function loadServerMods(serverId) {
    const content = document.getElementById('server-tab-content');
    content.innerHTML = loading('Loading installed mods...');
    try {
        const [server, mods, modFiles] = await Promise.all([
            API.servers.get(serverId),
            API.mods.installed(serverId),
            API.mods.files(serverId).catch(() => []),
        ]);
        const contentLoader = getServerLoader(server.server_type);
        const trackedNames = new Set(mods.map(m => m.file_name));
        const untrackedFiles = modFiles.filter(f => !f.tracked);

        content.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Installed Mods (${modFiles.length} files${mods.length ? `, ${mods.length} tracked` : ''})</span>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-secondary" onclick="checkModUpdates(${serverId})">&#128260; Check Updates</button>
                        <button class="btn btn-sm btn-primary" onclick="navigate('mods')">&#10010; Browse Mods</button>
                    </div>
                </div>
                ${modFiles.length === 0
                    ? emptyState('&#128295;', 'No mods installed', 'Browse and install mods from the Mods Browser, or install a modpack.')
                    : `<div class="table-wrap"><table>
                        <thead><tr><th>File Name</th><th>Size</th><th>Source</th><th>Actions</th></tr></thead>
                        <tbody>${modFiles.map(f => {
                            const dbMod = mods.find(m => m.file_name === f.file_name);
                            return `<tr>
                                <td><strong>${escapeHtml(dbMod ? dbMod.mod_name : f.file_name.replace(/\.jar$/, ''))}</strong>
                                    <div style="font-size:11px;color:var(--text-muted)">${escapeHtml(f.file_name)}</div>
                                </td>
                                <td>${f.size_kb > 1024 ? (f.size_kb/1024).toFixed(1)+' MB' : f.size_kb+' KB'}</td>
                                <td>${dbMod ? `<span class="tag">${escapeHtml(dbMod.source)}</span>` : '<span class="tag" style="opacity:0.5">modpack</span>'}</td>
                                <td>${dbMod
                                    ? `<button class="btn btn-sm btn-danger" onclick="uninstallMod(${serverId}, ${dbMod.id}, '${escapeHtml(dbMod.mod_name)}')">Uninstall</button>`
                                    : `<button class="btn btn-sm btn-danger" onclick="deleteModFile(${serverId}, '${encodeURIComponent(f.file_name)}')">Delete</button>`
                                }</td>
                            </tr>`;
                        }).join('')}</tbody>
                    </table></div>`
                }
            </div>

            <div class="card" style="margin-top:20px;">
                <h3 style="margin-bottom:8px;">Compatible Mods For This Server</h3>
                <p style="color:var(--text-secondary);font-size:13px;margin-bottom:12px;">
                    Compatibility locked to MC ${escapeHtml(server.minecraft_version || '?')} ${contentLoader ? `&middot; ${escapeHtml(contentLoader)}` : ''}
                </p>
                <div class="form-row" style="grid-template-columns:1fr auto;">
                    <div class="form-group" style="margin:0;">
                        <input class="form-input" id="srv-mod-search" placeholder="Search compatible mods..." onkeydown="if(event.key==='Enter')searchServerCompatibleMods(${serverId})">
                    </div>
                    <button class="btn btn-primary" onclick="searchServerCompatibleMods(${serverId})">&#128270; Search</button>
                </div>
                <div id="srv-mod-results" style="margin-top:12px;">${emptyState('&#128295;', 'Search for compatible mods', 'Only versions matching this server are used.')}</div>
            </div>

            <div class="card" style="margin-top:20px;">
                <h3 style="margin-bottom:8px;">Compatible Modpacks For This Server</h3>
                <p style="color:var(--text-secondary);font-size:13px;margin-bottom:12px;">
                    Results are filtered by MC ${escapeHtml(server.minecraft_version || '?')} and ${contentLoader || 'loader-agnostic'} compatibility.
                </p>
                <div class="form-row" style="grid-template-columns:1fr auto;">
                    <div class="form-group" style="margin:0;">
                        <input class="form-input" id="srv-modpack-search" placeholder="Search compatible modpacks..." onkeydown="if(event.key==='Enter')searchServerCompatibleModpacks(${serverId})">
                    </div>
                    <button class="btn btn-primary" onclick="searchServerCompatibleModpacks(${serverId})">&#128270; Search</button>
                </div>
                <div id="srv-modpack-results" style="margin-top:12px;">${emptyState('&#128230;', 'Search for compatible modpacks', 'Only compatible versions will be installed.')}</div>
            </div>
        `;
    } catch (err) {
        content.innerHTML = `<div class="card">${emptyState('&#9888;', 'Error', err.message)}</div>`;
    }
}

async function uninstallMod(serverId, modId, modName) {
    if (!confirm(`Uninstall "${modName}"?`)) return;
    try {
        await API.mods.uninstall(serverId, modId);
        toast(`Uninstalled ${modName}`, 'success');
        loadServerMods(serverId);
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function deleteModFile(serverId, encodedFileName) {
    const fileName = decodeURIComponent(encodedFileName);
    if (!confirm(`Delete "${fileName}" from mods folder?`)) return;
    try {
        await API.mods.deleteFile(serverId, encodedFileName);
        toast(`Deleted ${fileName}`, 'success');
        loadServerMods(serverId);
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function checkModUpdates(serverId) {
    toast('Checking for updates...', 'info');
    try {
        const updates = await API.mods.checkUpdates(serverId);
        if (updates.length === 0) {
            toast('All mods are up to date!', 'success');
        } else {
            toast(`${updates.length} update(s) available`, 'warning');
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function searchServerCompatibleMods(serverId) {
    const results = document.getElementById('srv-mod-results');
    if (!results) return;
    results.innerHTML = loading('Searching compatible mods...');

    try {
        const [server] = await Promise.all([API.servers.get(serverId)]);
        const query = document.getElementById('srv-mod-search')?.value || '';
        const loader = getServerLoader(server.server_type);
        const data = await API.mods.searchModrinth({
            query,
            mc_version: server.minecraft_version || '',
            loader,
            offset: 0,
            limit: 20,
        });

        if (!data.results?.length) {
            results.innerHTML = emptyState('&#128270;', 'No compatible mods found', 'Try another search term.');
            return;
        }

        results.innerHTML = `
            <div class="mod-grid">
                ${data.results.map(m => `
                    <div class="mod-card">
                        <img class="mod-icon" src="${m.icon_url || ''}" alt="" onerror="this.style.display='none'">
                        <div class="mod-card-info">
                            <h4>${escapeHtml(m.name)}</h4>
                            <p>${escapeHtml(m.description)}</p>
                            <div class="mod-card-meta">
                                <span>&#11015; ${formatNumber(m.downloads)}</span>
                                <span>${escapeHtml(m.author)}</span>
                            </div>
                        </div>
                        <div class="mod-card-actions">
                            <button class="btn btn-success btn-sm" onclick="installServerCompatibleMod(${serverId}, '${m.id}', '${encodeURIComponent(m.name || '')}')">Install</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        results.innerHTML = emptyState('&#9888;', 'Search failed', err.message);
    }
}

async function installServerCompatibleMod(serverId, projectId, encodedName) {
    const modName = decodeURIComponent(encodedName || '');
    toast(`Installing ${modName}...`, 'info');
    try {
        const server = await API.servers.get(serverId);
        const loader = getServerLoader(server.server_type);
        const versions = await API.mods.versions(projectId, {
            mc_version: server.minecraft_version || '',
            loader,
        });
        if (!versions.length) {
            toast('No compatible version found for this server', 'warning');
            return;
        }
        const result = await API.mods.install(serverId, {
            source: 'modrinth',
            project_id: projectId,
            version_id: versions[0].id,
        });
        if (result.success) {
            toast(`Installed ${result.mod_name}`, 'success');
            loadServerMods(serverId);
        } else {
            toast(result.error || 'Install failed', 'error');
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function searchServerCompatibleModpacks(serverId) {
    const results = document.getElementById('srv-modpack-results');
    if (!results) return;
    results.innerHTML = loading('Searching compatible modpacks...');

    try {
        const server = await API.servers.get(serverId);
        const query = document.getElementById('srv-modpack-search')?.value || '';
        const loader = getServerLoader(server.server_type);
        const data = await API.modpacks.searchModrinth({
            query,
            mc_version: server.minecraft_version || '',
            loader,
            offset: 0,
            limit: 20,
        });

        if (!data.results?.length) {
            results.innerHTML = emptyState('&#128270;', 'No compatible modpacks found', 'Try another search term.');
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
                            <button class="btn btn-success btn-sm" onclick="installServerCompatibleModpack(${serverId}, '${p.id}', '${encodeURIComponent(p.name || '')}')">Install</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (err) {
        results.innerHTML = emptyState('&#9888;', 'Search failed', err.message);
    }
}

async function installServerCompatibleModpack(serverId, projectId, encodedName) {
    const packName = decodeURIComponent(encodedName || '');
    toast(`Installing ${packName}...`, 'info');
    try {
        const server = await API.servers.get(serverId);
        const loader = getServerLoader(server.server_type);
        const versions = await API.modpacks.versions(projectId, {
            mc_version: server.minecraft_version || '',
            loader,
        });
        if (!versions.length) {
            toast('No compatible modpack version found for this server', 'warning');
            return;
        }
        const result = await API.modpacks.install(serverId, {
            source: 'modrinth',
            project_id: projectId,
            version_id: versions[0].id,
        });
        if (result.success) {
            toast(`Installed modpack ${packName}`, 'success');
            loadServerMods(serverId);
        } else {
            toast(result.error || 'Install failed', 'error');
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}

// --- Backups Tab ---
async function loadServerBackups(serverId) {
    const content = document.getElementById('server-tab-content');
    content.innerHTML = loading('Loading backups...');
    try {
        const backups = await API.backups.list(serverId);
        content.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Backups (${backups.length})</span>
                    <div class="btn-group">
                        <button class="btn btn-sm btn-primary" onclick="createServerBackup(${serverId}, 'full')">&#128190; Full Backup</button>
                        <button class="btn btn-sm btn-secondary" onclick="createServerBackup(${serverId}, 'world')">&#127758; World Only</button>
                        <button class="btn btn-sm btn-secondary" onclick="createServerBackup(${serverId}, 'mods')">&#128295; Mods Only</button>
                    </div>
                </div>
                ${backups.length === 0
                    ? emptyState('&#128190;', 'No backups yet', 'Create a backup to protect your server data.')
                    : backups.map(b => `
                        <div class="backup-item">
                            <div>
                                <strong>${escapeHtml(b.name)}</strong>
                                <div style="font-size:12px;color:var(--text-muted)">
                                    ${escapeHtml(b.backup_type)} &middot; ${b.size_mb} MB &middot; ${timeAgo(b.created_at)}
                                </div>
                            </div>
                            <div class="btn-group">
                                <button class="btn btn-sm btn-secondary" onclick="restoreBackup(${serverId}, ${b.id}, '${escapeHtml(b.name)}')">Restore</button>
                                <button class="btn btn-sm btn-danger" onclick="deleteBackup(${serverId}, ${b.id})">&#128465;</button>
                            </div>
                        </div>
                    `).join('')
                }
            </div>
        `;
    } catch (err) {
        content.innerHTML = `<div class="card">${emptyState('&#9888;', 'Error', err.message)}</div>`;
    }
}

async function createServerBackup(serverId, type) {
    toast('Creating backup...', 'info');
    try {
        const result = await API.backups.create(serverId, { backup_type: type });
        if (result.success) {
            toast(`Backup created: ${result.size_mb} MB`, 'success');
            loadServerBackups(serverId);
        } else {
            toast(result.error, 'error');
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function restoreBackup(serverId, backupId, name) {
    if (!confirm(`Restore backup "${name}"? This will overwrite current files.`)) return;
    try {
        const result = await API.backups.restore(serverId, backupId);
        toast(result.success ? 'Backup restored!' : result.error, result.success ? 'success' : 'error');
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function deleteBackup(serverId, backupId) {
    if (!confirm('Delete this backup?')) return;
    try {
        await API.backups.delete(backupId);
        toast('Backup deleted', 'info');
        loadServerBackups(serverId);
    } catch (err) {
        toast(err.message, 'error');
    }
}

// --- Files Tab ---
let currentFilePath = '';

function formatFileSize(bytes) {
    if (bytes === 0) return '—';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

function fileIcon(name, isDir) {
    if (isDir) return '&#128193;';
    const ext = name.split('.').pop().toLowerCase();
    const icons = {
        jar: '&#9749;', zip: '&#128230;', gz: '&#128230;', tar: '&#128230;',
        json: '&#128196;', yml: '&#128196;', yaml: '&#128196;', toml: '&#128196;',
        properties: '&#9881;', txt: '&#128196;', log: '&#128220;', cfg: '&#9881;',
        dat: '&#128190;', dat_old: '&#128190;', mca: '&#127758;',
        png: '&#128248;', jpg: '&#128248;', gif: '&#128248;',
    };
    return icons[ext] || '&#128196;';
}

function buildBreadcrumb(serverId, path) {
    const parts = path ? path.split('/').filter(Boolean) : [];
    let crumbs = `<span class="fm-crumb" onclick="browseFiles(${serverId}, '')">/</span>`;
    let accumulated = '';
    for (const part of parts) {
        accumulated += (accumulated ? '/' : '') + part;
        const p = accumulated;
        crumbs += ` <span style="color:var(--text-muted);">/</span> <span class="fm-crumb" onclick="browseFiles(${serverId}, '${escapeHtml(p)}')">${escapeHtml(part)}</span>`;
    }
    return crumbs;
}

async function loadServerFiles(serverId, path = '') {
    currentFilePath = path;
    const content = document.getElementById('server-tab-content');
    content.innerHTML = loading('Loading files...');
    try {
        const data = await API.servers.files(serverId, path);
        content.innerHTML = `
            <div class="card" style="padding:0;overflow:hidden;">
                <div class="fm-toolbar">
                    <div class="fm-breadcrumb">${buildBreadcrumb(serverId, path)}</div>
                    <div class="fm-actions">
                        <button class="btn btn-sm btn-secondary" onclick="fmNewFolder(${serverId})" title="New Folder">&#128193;+ New Folder</button>
                        <label class="btn btn-sm btn-primary" title="Upload Files" style="margin:0;cursor:pointer;">
                            &#128194; Upload Files
                            <input type="file" multiple style="display:none" onchange="fmUploadFiles(${serverId}, this.files)">
                        </label>
                        <label class="btn btn-sm btn-success" title="Upload Folder" style="margin:0;cursor:pointer;">
                            &#128193; Upload Folder
                            <input type="file" webkitdirectory style="display:none" onchange="fmUploadFiles(${serverId}, this.files)">
                        </label>
                    </div>
                </div>
                <div class="fm-list">
                    ${path ? `<div class="fm-item fm-item-dir" onclick="browseFiles(${serverId}, '${escapeHtml(parentPath(path))}')">
                        <span class="fm-icon">&#128194;</span>
                        <span class="fm-name">..</span>
                        <span class="fm-size"></span>
                        <span class="fm-actions-cell"></span>
                    </div>` : ''}
                    ${data.items.length === 0 && !path ? '<div class="fm-empty">This server has no files yet.</div>' : ''}
                    ${data.items.map(item => {
                        const itemPath = path ? path + '/' + item.name : item.name;
                        return `<div class="fm-item ${item.is_dir ? 'fm-item-dir' : ''}" ${item.is_dir ? `onclick="browseFiles(${serverId}, '${escapeHtml(itemPath)}')"` : ''}>
                            <span class="fm-icon">${fileIcon(item.name, item.is_dir)}</span>
                            <span class="fm-name">${escapeHtml(item.name)}</span>
                            <span class="fm-size">${formatFileSize(item.size)}</span>
                            <span class="fm-actions-cell">
                                ${!item.is_dir ? `<a class="btn btn-sm btn-secondary" href="${API.servers.filesDownload(serverId, itemPath)}" title="Download">&#11015;</a>` : ''}
                                <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); fmDelete(${serverId}, '${escapeHtml(itemPath)}', ${item.is_dir})" title="Delete">&#128465;</button>
                            </span>
                        </div>`;
                    }).join('')}
                </div>
            </div>

            <div class="fm-drop-zone" id="fm-drop-zone"
                ondragover="event.preventDefault(); this.classList.add('active')"
                ondragleave="this.classList.remove('active')"
                ondrop="event.preventDefault(); this.classList.remove('active'); fmUploadFiles(${serverId}, event.dataTransfer.files)">
                &#128194; Drag &amp; drop files or folders here to upload
            </div>
        `;
    } catch (err) {
        content.innerHTML = `<div class="card">${emptyState('&#9888;', 'Error loading files', err.message)}</div>`;
    }
}

function browseFiles(serverId, path) {
    loadServerFiles(serverId, path);
}

function parentPath(path) {
    const parts = path.split('/').filter(Boolean);
    parts.pop();
    return parts.join('/');
}

async function fmUploadFiles(serverId, fileList) {
    if (!fileList || fileList.length === 0) return;
    const formData = new FormData();
    for (const f of fileList) {
        // For folder uploads, webkitRelativePath preserves structure
        const name = f.webkitRelativePath || f.name;
        formData.append('files', f, name);
    }
    toast(`Uploading ${fileList.length} file(s)...`, 'info');
    try {
        await API.servers.filesUpload(serverId, currentFilePath, formData);
        toast(`Uploaded ${fileList.length} file(s)`, 'success');
        loadServerFiles(serverId, currentFilePath);
    } catch (err) {
        toast(err.message, 'error');
    }
}

function fmNewFolder(serverId) {
    const name = prompt('New folder name:');
    if (!name) return;
    API.servers.filesMkdir(serverId, currentFilePath, name).then(() => {
        toast(`Created folder "${name}"`, 'success');
        loadServerFiles(serverId, currentFilePath);
    }).catch(err => toast(err.message, 'error'));
}

async function fmDelete(serverId, path, isDir) {
    const label = isDir ? 'folder' : 'file';
    const name = path.split('/').pop();
    if (!confirm(`Delete ${label} "${name}"?${isDir ? ' This will delete all contents inside.' : ''}`)) return;
    try {
        await API.servers.filesDelete(serverId, path);
        toast(`Deleted ${name}`, 'info');
        loadServerFiles(serverId, currentFilePath);
    } catch (err) {
        toast(err.message, 'error');
    }
}
