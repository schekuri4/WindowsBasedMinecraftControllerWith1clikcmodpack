/**
 * MCServerPanel - API Client
 */
const API = {
    base: '/api',

    async request(method, path, body = null) {
        const token = localStorage.getItem('mcsp_token');
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (token) {
            opts.headers.Authorization = `Bearer ${token}`;
        }
        if (body) opts.body = JSON.stringify(body);
        const resp = await fetch(this.base + path, opts);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: resp.statusText }));
            throw new Error(err.detail || 'Request failed');
        }
        return resp.json();
    },

    get(path) { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },
    put(path, body) { return this.request('PUT', path, body); },
    del(path) { return this.request('DELETE', path); },

    // Auth
    auth: {
        login: (username, password) => API.post('/auth/login', { username, password }),
    },

    // Servers
    servers: {
        list: () => API.get('/servers'),
        get: (id) => API.get(`/servers/${id}`),
        create: (data) => API.post('/servers', data),
        import: (data) => API.post('/servers/import', data),
        update: (id, data) => API.put(`/servers/${id}`, data),
        delete: (id, deleteFiles = false) => API.del(`/servers/${id}?delete_files=${deleteFiles}`),
        start: (id) => API.post(`/servers/${id}/start`),
        stop: (id) => API.post(`/servers/${id}/stop`),
        command: (id, cmd) => API.post(`/servers/${id}/command`, { command: cmd }),
        console: (id, lines = 100) => API.get(`/servers/${id}/console?lines=${lines}`),
        status: (id) => API.get(`/servers/${id}/status`),
        versions: () => API.get('/servers/versions'),
        java: () => API.get('/servers/java'),
        files: (id, path = '') => API.get(`/servers/${id}/files?path=${encodeURIComponent(path)}`),
        filesDownload: (id, path) => {
            const token = localStorage.getItem('mcsp_token');
            return `${API.base}/servers/${id}/files/download?path=${encodeURIComponent(path)}&token=${token}`;
        },
        filesUpload: async (id, path, formData) => {
            formData.append('path', path);
            const token = localStorage.getItem('mcsp_token');
            const resp = await fetch(`${API.base}/servers/${id}/files/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData,
            });
            if (!resp.ok) throw new Error((await resp.json()).detail || resp.statusText);
            return resp.json();
        },
        filesMkdir: (id, path, name) => API.post(`/servers/${id}/files/mkdir?path=${encodeURIComponent(path)}&name=${encodeURIComponent(name)}`),
        filesDelete: (id, path) => API.del(`/servers/${id}/files?path=${encodeURIComponent(path)}`),
    },

    // Modpacks
    modpacks: {
        searchModrinth: (params) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/modpacks/search/modrinth?${q}`);
        },
        searchCurseforge: (params) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/modpacks/search/curseforge?${q}`);
        },
        detail: (id) => API.get(`/modpacks/detail/modrinth/${id}`),
        versions: (id, params = {}) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/modpacks/versions/modrinth/${id}?${q}`);
        },
        versionsCurseforge: (id, params = {}) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/modpacks/versions/curseforge/${id}?${q}`);
        },
        install: (serverId, data) => API.post(`/modpacks/install/${serverId}`, data),
        checkUpdate: (serverId) => API.get(`/modpacks/update-check/${serverId}`),
        export: (serverId, name) => API.post(`/modpacks/export/${serverId}`, { name }),
        import: (serverId, path) => API.post(`/modpacks/import/${serverId}`, { path }),
    },

    // Mods
    mods: {
        searchModrinth: (params) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/mods/search/modrinth?${q}`);
        },
        searchCurseforge: (params) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/mods/search/curseforge?${q}`);
        },
        detail: (id) => API.get(`/mods/detail/modrinth/${id}`),
        versions: (id, params = {}) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/mods/versions/modrinth/${id}?${q}`);
        },
        categories: () => API.get('/mods/categories/modrinth'),
        installed: (serverId) => API.get(`/mods/installed/${serverId}`),
        files: (serverId) => API.get(`/mods/files/${serverId}`),
        install: (serverId, data) => API.post(`/mods/install/${serverId}`, data),
        batchInstall: (serverId, mods) => API.post(`/mods/install-batch/${serverId}`, { mods }),
        uninstall: (serverId, modId) => API.del(`/mods/uninstall/${serverId}/${modId}`),
        deleteFile: (serverId, encodedFileName) => API.del(`/mods/file/${serverId}/${encodedFileName}`),
        checkUpdates: (serverId) => API.get(`/mods/updates/${serverId}`),
    },

    // Plugins
    plugins: {
        searchModrinth: (params) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/plugins/search/modrinth?${q}`);
        },
        searchHangar: (params) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/plugins/search/hangar?${q}`);
        },
        searchSpiget: (params) => {
            const q = new URLSearchParams(params).toString();
            return API.get(`/plugins/search/spiget?${q}`);
        },
        versions: (id, params = {}) => {
            const q = new URLSearchParams(params).toString();
            const source = params.source || 'modrinth';
            const actualParams = new URLSearchParams(params);
            actualParams.delete('source');
            return API.get(`/plugins/versions/${source}/${id}?${actualParams.toString()}`);
        },
        install: (serverId, data) => API.post(`/plugins/install/${serverId}`, data),
    },

    // System & Backups
    system: {
        stats: () => API.get('/system/stats'),
        network: () => API.get('/system/network'),
        features: () => API.get('/system/features'),
    },

    backups: {
        list: (serverId) => API.get(`/backups/${serverId}`),
        create: (serverId, data) => API.post(`/backups/${serverId}`, data),
        restore: (serverId, backupId) => API.post(`/backups/${serverId}/restore/${backupId}`),
        delete: (backupId) => API.del(`/backups/${backupId}`),
    },
};
