/**
 * Dashboard Page
 */
async function renderDashboard() {
    const main = document.getElementById('main-content');
    main.innerHTML = loading('Loading dashboard...');

    try {
        const [servers, stats] = await Promise.all([
            API.servers.list(),
            API.system.stats(),
        ]);

        const running = servers.filter(s => s.status === 'running').length;
        const stopped = servers.filter(s => s.status === 'stopped').length;

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <h2>Dashboard</h2>
                    <div class="subtitle">System overview and server status</div>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon cpu">&#128187;</div>
                    <div>
                        <div class="stat-value">${stats.cpu.percent}%</div>
                        <div class="stat-label">CPU Usage (${stats.cpu.cores} cores)</div>
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
                        <div class="stat-value">${stats.disk.used_gb}GB</div>
                        <div class="stat-label">Disk ${stats.disk.free_gb}GB free of ${stats.disk.total_gb}GB</div>
                        ${progressBar(stats.disk.percent, stats.disk.percent > 90 ? 'red' : 'green')}
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon net">&#127760;</div>
                    <div>
                        <div class="stat-value">${servers.length}</div>
                        <div class="stat-label">${running} running / ${stopped} stopped</div>
                    </div>
                </div>
            </div>

            <div class="card" style="margin-bottom: 20px">
                <div class="card-header">
                    <span class="card-title">Servers</span>
                    <button class="btn btn-primary btn-sm" onclick="navigate('create-server')">&#10010; New Server</button>
                </div>
                ${servers.length === 0
                    ? emptyState('&#9881;', 'No servers yet', 'Create your first Minecraft server to get started.')
                    : `<div class="server-grid">${servers.map(s => serverCard(s)).join('')}</div>`
                }
            </div>
        `;
    } catch (err) {
        main.innerHTML = `<div class="card">${emptyState('&#9888;', 'Failed to load dashboard', err.message)}</div>`;
    }
}

function serverCard(s) {
    const typeIcons = { vanilla: '&#127795;', forge: '&#128296;', fabric: '&#129526;', paper: '&#128220;', spigot: '&#128311;' };
    const icon = typeIcons[s.server_type] || '&#9881;';
    return `
        <div class="server-card" onclick="navigate('server-detail', { id: ${s.id} })">
            <div class="server-card-header">
                <div class="server-icon">${icon}</div>
                <div>
                    <div class="server-name">${escapeHtml(s.name)}</div>
                    <div class="server-meta">${serverTypeTag(s.server_type)} MC ${escapeHtml(s.minecraft_version || '?')}</div>
                </div>
            </div>
            <div class="server-card-body">
                <div class="server-info">
                    <span>&#128268; :${s.port}</span>
                    <span>&#128190; ${escapeHtml(s.max_ram)}</span>
                </div>
                ${statusBadge(s.status)}
            </div>
        </div>
    `;
}
