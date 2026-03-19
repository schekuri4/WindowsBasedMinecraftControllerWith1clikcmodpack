/**
 * Settings Page
 */
async function renderSettings() {
    const main = document.getElementById('main-content');

    let javas = [];
    try { javas = await API.servers.java(); } catch (e) { /* ignore */ }

    main.innerHTML = `
        <div class="page-header">
            <div>
                <h2>Settings</h2>
                <div class="subtitle">Panel configuration and system info</div>
            </div>
        </div>

        <div class="card" style="margin-bottom:20px">
            <h3 style="margin-bottom:16px;">Java Installations</h3>
            ${javas.length === 0
                ? `<p style="color:var(--text-secondary);">No Java installations detected. Please install Java to run Minecraft servers.</p>`
                : `<div class="table-wrap"><table>
                    <thead><tr><th>Vendor</th><th>Version</th><th>Architecture</th><th>Path</th></tr></thead>
                    <tbody>${javas.map(j => `
                        <tr>
                            <td><strong>${escapeHtml(j.vendor)}</strong></td>
                            <td>${escapeHtml(j.version)}</td>
                            <td>${j.is_64bit ? '64-bit' : '32-bit'}</td>
                            <td style="font-size:12px;color:var(--text-muted);word-break:break-all;">${escapeHtml(j.path)}</td>
                        </tr>
                    `).join('')}</tbody>
                </table></div>`
            }
            <button class="btn btn-secondary btn-sm" style="margin-top:12px" onclick="renderSettings()">&#128260; Refresh</button>
        </div>

        <div class="card" style="margin-bottom:20px">
            <h3 style="margin-bottom:16px;">System Resources</h3>
            <div id="settings-stats">${loading('Loading system stats...')}</div>
        </div>

        <div class="card" style="margin-bottom:20px">
            <h3 style="margin-bottom:16px;">Export / Import Setup</h3>
            <p style="color:var(--text-secondary);font-size:14px;margin-bottom:12px;">
                Export your server's modpack and mod configuration to share or back it up.
            </p>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">Server to Export</label>
                    <select class="form-select" id="export-server"></select>
                </div>
                <div class="form-group">
                    <label class="form-label">Export Name</label>
                    <input class="form-input" id="export-name" placeholder="my-setup">
                </div>
            </div>
            <button class="btn btn-primary btn-sm" onclick="doExport()">&#128194; Export</button>
        </div>

        <div class="card">
            <h3 style="margin-bottom:16px;">About</h3>
            <p style="color:var(--text-secondary);">MCServerPanel v1.0.0</p>
            <p style="color:var(--text-muted);font-size:13px;">
                A Windows-compatible Minecraft server management panel with integrated modpack and mod installation.
            </p>
        </div>
    `;

    // Load system stats
    try {
        const stats = await API.system.stats();
        document.getElementById('settings-stats').innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon cpu">&#128187;</div>
                    <div>
                        <div class="stat-value">${stats.cpu.percent}%</div>
                        <div class="stat-label">CPU (${stats.cpu.cores} cores)</div>
                        ${progressBar(stats.cpu.percent, 'blue')}
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon ram">&#128202;</div>
                    <div>
                        <div class="stat-value">${stats.memory.percent}%</div>
                        <div class="stat-label">RAM ${stats.memory.used_mb}MB / ${stats.memory.total_mb}MB</div>
                        ${progressBar(stats.memory.percent, 'purple')}
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon disk">&#128191;</div>
                    <div>
                        <div class="stat-value">${stats.disk.percent}%</div>
                        <div class="stat-label">Disk ${stats.disk.used_gb}GB / ${stats.disk.total_gb}GB</div>
                        ${progressBar(stats.disk.percent, stats.disk.percent > 90 ? 'red' : 'green')}
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon net">&#127760;</div>
                    <div>
                        <div class="stat-value">${formatBytes(stats.network.bytes_sent)}</div>
                        <div class="stat-label">Sent / ${formatBytes(stats.network.bytes_recv)} Recv</div>
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        document.getElementById('settings-stats').innerHTML = '<p style="color:var(--text-muted)">Could not load stats</p>';
    }

    // Populate export server dropdown
    try {
        const servers = await API.servers.list();
        const select = document.getElementById('export-server');
        if (select) {
            select.innerHTML = servers.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('');
        }
    } catch (e) { /* ignore */ }
}

async function doExport() {
    const serverId = document.getElementById('export-server')?.value;
    const name = document.getElementById('export-name')?.value || 'export';
    if (!serverId) { toast('Select a server', 'warning'); return; }
    try {
        const result = await API.modpacks.export(serverId, name);
        if (result.success) {
            toast(`Exported to ${result.path}`, 'success');
        } else {
            toast(result.error, 'error');
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}
