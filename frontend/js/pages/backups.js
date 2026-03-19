/**
 * Backups Page (global view)
 */
async function renderBackups() {
    const main = document.getElementById('main-content');
    main.innerHTML = loading('Loading...');

    try {
        const servers = await API.servers.list();
        if (servers.length === 0) {
            main.innerHTML = `
                <div class="page-header"><div><h2>Backups</h2></div></div>
                <div class="card">${emptyState('&#128190;', 'No servers configured', 'Create a server first to manage backups.')}</div>
            `;
            return;
        }

        let allBackups = [];
        for (const s of servers) {
            const backups = await API.backups.list(s.id);
            allBackups.push(...backups.map(b => ({ ...b, serverName: s.name, serverId: s.id })));
        }
        allBackups.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        main.innerHTML = `
            <div class="page-header">
                <div>
                    <h2>Backups</h2>
                    <div class="subtitle">${allBackups.length} backup${allBackups.length !== 1 ? 's' : ''} across ${servers.length} server${servers.length !== 1 ? 's' : ''}</div>
                </div>
            </div>

            <div class="card" style="margin-bottom:20px;padding:12px 20px;display:flex;gap:12px;align-items:center;">
                <span style="color:var(--text-secondary);">Quick backup:</span>
                <select class="form-select" id="backup-server" style="width:auto;min-width:200px;">
                    ${servers.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('')}
                </select>
                <button class="btn btn-primary btn-sm" onclick="quickBackup('full')">&#128190; Full</button>
                <button class="btn btn-secondary btn-sm" onclick="quickBackup('world')">&#127758; World</button>
                <button class="btn btn-secondary btn-sm" onclick="quickBackup('mods')">&#128295; Mods</button>
            </div>

            <div class="card">
                ${allBackups.length === 0
                    ? emptyState('&#128190;', 'No backups yet', 'Create a backup to protect your data.')
                    : `<div class="table-wrap"><table>
                        <thead><tr><th>Server</th><th>Backup</th><th>Type</th><th>Size</th><th>Created</th><th>Actions</th></tr></thead>
                        <tbody>${allBackups.map(b => `
                            <tr>
                                <td>${escapeHtml(b.serverName)}</td>
                                <td>${escapeHtml(b.name)}</td>
                                <td><span class="tag">${escapeHtml(b.backup_type)}</span></td>
                                <td>${b.size_mb} MB</td>
                                <td>${timeAgo(b.created_at)}</td>
                                <td class="btn-group">
                                    <button class="btn btn-sm btn-secondary" onclick="restoreBackup(${b.serverId}, ${b.id}, '${escapeHtml(b.name)}')">Restore</button>
                                    <button class="btn btn-sm btn-danger" onclick="deleteBackupGlobal(${b.id})">&#128465;</button>
                                </td>
                            </tr>
                        `).join('')}</tbody>
                    </table></div>`
                }
            </div>
        `;
    } catch (err) {
        main.innerHTML = `<div class="card">${emptyState('&#9888;', 'Error', err.message)}</div>`;
    }
}

async function quickBackup(type) {
    const serverId = document.getElementById('backup-server').value;
    toast('Creating backup...', 'info');
    try {
        const result = await API.backups.create(serverId, { backup_type: type });
        if (result.success) {
            toast(`Backup created: ${result.size_mb} MB`, 'success');
            renderBackups();
        } else {
            toast(result.error, 'error');
        }
    } catch (err) {
        toast(err.message, 'error');
    }
}

async function deleteBackupGlobal(backupId) {
    if (!confirm('Delete this backup?')) return;
    try {
        await API.backups.delete(backupId);
        toast('Backup deleted', 'info');
        renderBackups();
    } catch (err) {
        toast(err.message, 'error');
    }
}
