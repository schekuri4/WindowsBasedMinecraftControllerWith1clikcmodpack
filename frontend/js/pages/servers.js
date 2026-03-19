/**
 * Servers List Page
 */
async function renderServers() {
    const main = document.getElementById('main-content');
    main.innerHTML = loading('Loading servers...');

    try {
        const servers = await API.servers.list();
        main.innerHTML = `
            <div class="page-header">
                <div>
                    <h2>My Servers</h2>
                    <div class="subtitle">${servers.length} server${servers.length !== 1 ? 's' : ''} configured</div>
                </div>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="showImportModal()">&#128194; Import Existing</button>
                    <button class="btn btn-primary" onclick="navigate('create-server')">&#10010; New Server</button>
                </div>
            </div>

            ${servers.length === 0
                ? `<div class="card">${emptyState('&#9881;', 'No servers yet', 'Create a new server or import an existing one.')}</div>`
                : `<div class="server-grid">${servers.map(s => serverCard(s)).join('')}</div>`
            }
        `;
    } catch (err) {
        main.innerHTML = `<div class="card">${emptyState('&#9888;', 'Failed to load servers', err.message)}</div>`;
    }
}

function showImportModal() {
    showModal(`
        <div class="modal-header">
            <h3>Import Existing Server</h3>
            <button class="btn-icon" onclick="closeModalDirect()">&#10005;</button>
        </div>
        <div class="modal-body">
            <p style="color: var(--text-secondary); margin-bottom:16px;">
                Point to an existing Minecraft server folder. The panel will auto-detect the server type and jar file.
            </p>
            <div class="form-group">
                <label class="form-label">Server Name</label>
                <input class="form-input" id="import-name" placeholder="My Existing Server">
            </div>
            <div class="form-group">
                <label class="form-label">Server Folder Path</label>
                <input class="form-input" id="import-path" placeholder="C:\\path\\to\\server">
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary" onclick="closeModalDirect()">Cancel</button>
            <button class="btn btn-primary" onclick="doImportServer()">Import</button>
        </div>
    `);
}

async function doImportServer() {
    const name = document.getElementById('import-name').value.trim();
    const path = document.getElementById('import-path').value.trim();
    if (!name || !path) { toast('Please fill in all fields', 'warning'); return; }

    try {
        const result = await API.servers.import({ name, path });
        toast(`Imported "${result.name}" (${result.server_type} ${result.minecraft_version})`, 'success');
        closeModalDirect();
        navigate('servers');
    } catch (err) {
        toast(err.message, 'error');
    }
}
