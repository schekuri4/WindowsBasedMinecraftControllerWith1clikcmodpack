# MCServerPanel

A Windows-compatible Minecraft server management panel with integrated modpack and mod installation. Inspired by Crafty Controller, built with Python (FastAPI) and a modern web UI.

## Features

### Tier 1 — Server Management
- **Create servers** — Vanilla, Forge, or Fabric with automatic jar download
- **Import existing servers** — Point to a folder, auto-detects server type and jar
- **Start/Stop servers** — Process management with live console output
- **Send commands** — In-browser console with command input
- **Server settings** — RAM, JVM args, Java path, port, auto-start/restart
- **Java detection** — Auto-scans for installed Java versions on Windows
- **Multiple servers** — Run and manage many servers side by side

### Tier 2 — 1-Click Modpack Installer
- **Browse Modrinth** modpacks by name, MC version, and loader
- **Browse CurseForge** modpacks (requires API key)
- **1-click install** — Downloads all mods, configs, overrides, and sets up the loader
- **Create server from modpack** — One-click server + modpack setup
- **Update detection** — Check if a newer modpack version is available
- **Supports mrpack (Modrinth)** and manifest.json (CurseForge) formats

### Tier 3 — Modular Mod Installer
- **Search mods** by name, category, MC version, loader type
- **Compatibility checks** — Warns before installing incompatible mods
- **Auto-dependency resolution** — Installs required dependencies automatically
- **Batch install** — Queue multiple mods and install in one click
- **Uninstall mods** — Clean removal from both disk and database
- **Update checks** — Scan all installed mods for newer versions

### Tier 4 — Automation & UX
- **Dashboard** with system resource monitoring (CPU, RAM, disk, network)
- **Per-server resource stats** — CPU and memory usage of running servers
- **Backup system** — Full, world, mods, or config backups as zip files
- **Restore backups** — One-click restore from any backup
- **JVM presets** — Pre-configured memory and GC settings
- **Toast notifications** — Real-time feedback for all operations
- **Responsive design** — Works on desktop and tablet browsers

### Tier 5 — Advanced Features
- **Export/Import setups** — Save your server's mod/modpack config as JSON
- **Multiple MC versions** — Run different versions side by side
- **Rollback via backups** — Restore previous state if something breaks
- **Server folder detection** — Auto-detect Forge, Fabric, Paper, Spigot, Vanilla

## Quick Start

### Prerequisites
- **Python 3.10+** — [Download](https://python.org/downloads)
- **Java 17+** — Required to run Minecraft servers
- **Windows 10/11**

### Launch

**Option 1: Double-click the launcher**
```
start.bat
```

**Option 2: Manual**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

Then open **http://localhost:8080** in your browser.

### CurseForge API Key (Optional)
To enable CurseForge modpack/mod searching:
1. Get a free API key from [console.curseforge.com](https://console.curseforge.com/)
2. Copy `.env.example` to `.env`
3. Add your key: `CURSEFORGE_API_KEY=your_key_here`

Modrinth works out of the box with no API key.

## Project Structure

```
MCServerPanel/
├── app.py                      # FastAPI app entry point
├── start.bat                   # Windows launcher script
├── requirements.txt            # Python dependencies
├── .env.example                # Environment config template
├── backend/
│   ├── config.py               # App settings
│   ├── database.py             # SQLite + SQLAlchemy setup
│   ├── models.py               # Database models
│   ├── routes/
│   │   ├── servers.py          # Server CRUD & control API
│   │   ├── modpacks.py         # Modpack search & install API
│   │   ├── mods.py             # Mod search & install API
│   │   └── system.py           # System stats & backup API
│   └── services/
│       ├── server_manager.py   # Server process management
│       ├── modpack_installer.py # Modpack download & install
│       ├── mod_installer.py    # Individual mod management
│       ├── backup_manager.py   # Backup creation & restore
│       ├── java_manager.py     # Java detection
│       └── system_monitor.py   # CPU/RAM/disk monitoring
├── frontend/
│   ├── index.html              # Single-page app shell
│   ├── css/style.css           # Full UI styling
│   └── js/
│       ├── api.js              # API client
│       ├── utils.js            # Shared utilities
│       ├── app.js              # Router / navigation
│       └── pages/              # Page renderers
│           ├── dashboard.js
│           ├── servers.js
│           ├── server-detail.js
│           ├── create-server.js
│           ├── modpacks.js
│           ├── mods.js
│           ├── backups.js
│           └── settings.js
└── data/                       # Runtime data (auto-created)
    ├── servers/                # Server folders
    ├── backups/                # Backup archives
    └── mcserverpanel.db        # SQLite database
```

## API Documentation

The full REST API is documented at **http://localhost:8080/api/docs** (Swagger UI) when the panel is running.

### Key Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/servers` | GET | List all servers |
| `/api/servers` | POST | Create new server |
| `/api/servers/import` | POST | Import existing server folder |
| `/api/servers/{id}/start` | POST | Start a server |
| `/api/servers/{id}/stop` | POST | Stop a server |
| `/api/servers/{id}/console` | GET | Get console output |
| `/api/servers/{id}/command` | POST | Send command to server |
| `/api/modpacks/search/modrinth` | GET | Search Modrinth modpacks |
| `/api/modpacks/install/{server_id}` | POST | Install modpack on server |
| `/api/mods/search/modrinth` | GET | Search Modrinth mods |
| `/api/mods/install/{server_id}` | POST | Install mod on server |
| `/api/mods/install-batch/{server_id}` | POST | Batch install mods |
| `/api/backups/{server_id}` | POST | Create backup |
| `/api/system/stats` | GET | Get system resource stats |
