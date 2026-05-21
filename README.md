# AuraSafe v2.5
## Local AI-Powered Digital Safety Engine

---

## 📋 TABLE OF CONTENTS
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Project Structure](#project-structure)
4. [Features](#features)
5. [Tech Stack](#tech-stack)
6. [System Architecture](#system-architecture)
7. [Dashboard System](#dashboard-system)
8. [API Reference](#api-reference)
9. [Auto Startup](#auto-startup)
10. [Configuration](#configuration)
11. [Cross-Platform](#cross-platform)
12. [Security Model](#security-model)
13. [Future Scope](#future-scope)
14. [License](#license)

---

## 🛡 OVERVIEW

This is not a normal browser blocker.

It is a **local-first digital safety ecosystem** — a real-time moderation and productivity protection system built entirely around privacy, intervention, and intelligent monitoring.

AuraSafe combines:
- Browser extension monitoring
- Python backend orchestration
- Fullscreen protection overlays
- Focus lock systems
- Analytics dashboards
- Multilingual moderation engines

Everything runs locally.

No cloud. No trackers. No external surveillance.

---

## 🚀 QUICK START

```bash
# 1. Install dependencies
python setup.py

# 2. Run backend
cd backend
python main.py
```

Dashboard automatically opens at:

```plaintext
http://127.0.0.1:5000/dashboard
```

### Optional — Build Executable

```bash
python setup.py --exe
```

---

## 📁 PROJECT STRUCTURE

```plaintext
aurasafe/
│
├── backend/
│
│   ├── main.py
│   │    Orchestrator + watchdog manager
│   │
│   ├── detector.py
│   │    Multilingual keyword engine
│   │
│   ├── overlay.py
│   │    Fullscreen protection overlays
│   │
│   ├── lock_mode.py
│   │    PIN-protected focus mode
│   │
│   ├── logger.py
│   │    SQLite logging engine
│   │
│   ├── server.py
│   │    Flask API + dashboard routes
│   │
│   ├── templates/
│   │    └── dashboard.html
│   │         Web dashboard UI
│   │
│   ├── aurasafe.spec
│   │    PyInstaller executable config
│   │
│   └── config.json
│        Central configuration system
│
├── extension/
│
│   ├── manifest.json
│   ├── content.js
│   ├── background.js
│   ├── popup.html
│   ├── styles.css
│   └── icons/
│
├── startup/
│
│   ├── install_startup_windows.bat
│   ├── aurasafe_windows_startup.xml
│   └── com.aurasafe.plist
│
├── setup.py
│
└── README.md
```

---

## ✨ FEATURES

### Core Protection Engine
✅ Real-time content monitoring  
✅ Multilingual keyword filtering  
✅ English + Tamil + Tanglish detection  
✅ Dynamic keyword synchronization  
✅ Restricted application monitoring  

### Protection Systems
✅ Fullscreen warning overlays  
✅ Complete block mode  
✅ PIN-protected focus lock  
✅ Countdown-based focus timer  
✅ Manual unlock system  

### Dashboard & Analytics
✅ Full analytics dashboard  
✅ Daily / weekly activity charts  
✅ Event logging system  
✅ CSV export support  
✅ Live engine status monitoring  
✅ Language-based analytics breakdown  

### Configuration System
✅ Dashboard keyword editor  
✅ Auto-save configuration sync  
✅ Runtime settings updates  
✅ Persistent local storage  
✅ Extension-to-backend synchronization  

### Deployment Features
✅ Windows auto-startup integration  
✅ macOS LaunchAgent support  
✅ PyInstaller executable packaging  
✅ Localhost dashboard hosting  
✅ One-command setup installer  

---

## 🛠 TECH STACK

| Layer | Technology |
|---|---|
| Backend | Python |
| API Server | Flask |
| Database | SQLite |
| Dashboard | HTML5 + CSS3 + JavaScript |
| Browser Monitoring | Chrome Extension APIs |
| Packaging | PyInstaller |
| Configuration | JSON |
| Automation | Windows Task Scheduler / LaunchAgents |

---

## ⚙ SYSTEM ARCHITECTURE

```plaintext
┌──────────────────────┐
│  Chrome Extension    │
│ DOM Monitoring Layer │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Flask API Server   │
│ Local Communication  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Detection Engine    │
│ Multilingual Scanner │
└──────────┬───────────┘
           │
 ┌─────────┴─────────┐
 ▼                   ▼
Overlay System   Logger System
 ▼                   ▼
Fullscreen UI    SQLite Database
           │
           ▼
┌──────────────────────┐
│ Analytics Dashboard  │
│ Visual Monitoring UI │
└──────────────────────┘
```

---

## 📊 DASHBOARD SYSTEM

AuraSafe v2.5 introduces a complete analytics dashboard accessible locally.

### Dashboard Features
✅ Real-time engine monitoring  
✅ Event trend visualization  
✅ Language analytics breakdown  
✅ Keyword management interface  
✅ Focus mode controls  
✅ Exportable activity reports  

### Dashboard URL

```plaintext
http://127.0.0.1:5000/dashboard
```

---

## 🔌 API REFERENCE

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Dashboard home |
| `/dashboard` | GET | Analytics dashboard |
| `/status` | GET | Engine status |
| `/block` | POST | Trigger block overlay |
| `/unblock` | POST | Remove overlay |
| `/warn` | POST | Trigger warning banner |
| `/lock` | POST | Enable focus mode |
| `/unlock` | POST | Unlock focus mode |
| `/keywords` | GET | Fetch keyword lists |
| `/save_keywords` | POST | Save updated keywords |
| `/save_settings` | POST | Save configuration |
| `/logs` | GET | Retrieve event logs |
| `/stats` | GET | Fetch analytics statistics |

---

## 🔧 AUTO STARTUP

### Windows

```plaintext
Run:
startup/install_startup_windows.bat
as Administrator
```

### macOS

```bash
cp startup/com.aurasafe.plist ~/Library/LaunchAgents/

launchctl load ~/Library/LaunchAgents/com.aurasafe.plist
```

---

## ⚡ CONFIGURATION

```json
{
  "pin": "1234",

  "api": {
    "host": "127.0.0.1",
    "port": 5000
  },

  "detection": {
    "english_keywords": [],
    "tamil_keywords": [],
    "tanglish_keywords": []
  },

  "restricted_apps": []
}
```

Keywords edited via dashboard automatically sync with the extension.

---

## 📱 CROSS-PLATFORM

Tested and optimized for:

| Platform | Status |
|---|---|
| Windows | ✅ |
| macOS | ✅ |
| Chrome Browser | ✅ |
| Laptop/Desktop | ✅ |

### Platform Support
- Local dashboard access
- Extension synchronization
- Auto-start services
- Executable packaging
- Native fullscreen overlays

---

## 🔐 SECURITY MODEL

AuraSafe follows a **local-first privacy architecture**.

### Privacy Principles
✅ No cloud processing  
✅ No telemetry collection  
✅ No external tracking  
✅ All logs remain on-device  
✅ User data never leaves the system  

### Protection Layers
- PIN-protected focus mode
- Runtime process monitoring
- Local SQLite event logging
- Restricted application detection
- Overlay-based intervention system

---

## 🧩 FUTURE SCOPE

### Planned AI Features
- Vision-based NSFW image moderation
- AI toxicity classification
- Sentiment & mood analysis
- Smart adaptive filtering
- Behavioral wellness scoring

### Planned Platform Expansion
- Desktop application UI
- Cross-browser extension support
- Mobile companion integration
- Advanced analytics engine
- ML-assisted moderation models

---

## 👤 ABOUT

**M S Vishaal**  
B.Tech — Artificial Intelligence & Data Science  
Saveetha School of Engineering (SIMATS), Chennai

AuraSafe was built as a digital safety initiative focused on:
- privacy
- moderation
- productivity
- intelligent intervention systems
- local-first protection

---

## 📄 LICENSE

MIT License — feel free to learn from the code.

AuraSafe branding, architecture, and identity belong to M S Vishaal.

---

## 📝 VERSION HISTORY

### v2.5 — Dashboard Expansion Update (2026)
- Full analytics dashboard
- Keyword editor system
- CSV export support
- Focus mode timer
- Startup automation
- Executable packaging support

### v2.0 — Protection Engine Upgrade
- Multilingual detection engine
- Overlay protection system
- PIN-based lock mode

### v1.0 — Initial Release
- Browser extension foundation
- Local backend integration
- Basic moderation engine

---

**Built by MSV ; 2026**  
*Local-first. Privacy-driven. Built to protect.*
