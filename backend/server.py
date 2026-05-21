"""
AuraSafe — server.py
Local Flask API server for Chrome extension communication.
Endpoints: /block, /unblock, /warn, /status, /lock, /unlock, /logs, /stats, /keywords
Runs in a daemon thread.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import logging as pylog
import json
import os

pylog.getLogger("werkzeug").setLevel(pylog.ERROR)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def create_server(config: dict, state: dict, overlay, lock_manager, logger):
    import os as _os
    _tmpl = _os.path.join(_os.path.dirname(__file__), "templates")
    app = Flask("AuraSafe", template_folder=_tmpl)
    CORS(app, origins=["chrome-extension://*", "http://localhost*"])

    # ── Routes ───────────────────────────────────────────────────────────

    @app.route("/status", methods=["GET"])
    def status():
        return jsonify({
            "running":    True,
            "blocked":    state.get("blocked", False),
            "locked":     lock_manager.is_locked,
            "last_event": state.get("last_event", "none"),
            "version":    config.get("version", "2.0")
        })

    @app.route("/keywords", methods=["GET"])
    def keywords():
        """
        Sync endpoint — extension pulls latest keyword lists from backend config.
        Allows single source of truth in config.json.
        """
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                live_config = json.load(f)
            detection = live_config.get("detection", {})
            return jsonify({
                "ok": True,
                "english":   detection.get("english_keywords",  []),
                "tamil":     detection.get("tamil_keywords",    []),
                "tanglish":  detection.get("tanglish_keywords", []),
                "version":   live_config.get("version", "2.0")
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/block", methods=["POST"])
    def block():
        data    = request.get_json(silent=True) or {}
        reason  = data.get("reason",  "Extension-triggered block")
        keyword = data.get("keyword", "")
        source  = data.get("source",  "extension")

        state["blocked"]    = True
        state["last_event"] = f"block:{reason}"

        overlay.show_block(reason)
        logger.log("BLOCK", content=keyword, action="block_overlay", source=source)
        return jsonify({"ok": True, "action": "blocked"})

    @app.route("/unblock", methods=["POST"])
    def unblock():
        data   = request.get_json(silent=True) or {}
        source = data.get("source", "extension")

        state["blocked"]    = False
        state["last_event"] = "unblocked"

        overlay.hide()
        logger.log("UNBLOCK", action="hide_overlay", source=source)
        return jsonify({"ok": True, "action": "unblocked"})

    @app.route("/warn", methods=["POST"])
    def warn():
        data    = request.get_json(silent=True) or {}
        message = data.get("message", "Suspicious content detected")
        keyword = data.get("keyword", "")
        source  = data.get("source",  "extension")

        state["last_event"] = f"warn:{message}"
        overlay.show_warning(message)
        logger.log("DETECTION", content=keyword, action="warning_overlay", source=source)
        return jsonify({"ok": True, "action": "warned"})

    @app.route("/lock", methods=["POST"])
    def lock():
        data   = request.get_json(silent=True) or {}
        reason = data.get("reason", "Focus Mode")

        if not lock_manager.is_locked:
            lock_manager.lock(reason)
            state["locked"] = True

        return jsonify({"ok": True, "action": "locked"})

    @app.route("/unlock", methods=["POST"])
    def unlock():
        data    = request.get_json(silent=True) or {}
        pin     = data.get("pin", "")
        success = lock_manager.unlock_attempt(pin)

        if success:
            state["locked"] = False

        return jsonify({
            "ok":     success,
            "action": "unlocked" if success else "wrong_pin"
        })

    @app.route("/logs", methods=["GET"])
    def logs():
        limit      = int(request.args.get("limit", 50))
        event_type = request.args.get("type", None)
        entries    = logger.get_recent(limit=limit, event_type=event_type)
        return jsonify({"logs": entries, "count": len(entries)})

    @app.route("/stats", methods=["GET"])
    def stats():
        return jsonify(logger.get_stats())

    add_dashboard_routes(app, CONFIG_PATH)
    add_analytics_routes(app, logger)
    return app


class APIServer:
    def __init__(self, config: dict, state: dict, overlay, lock_manager, logger):
        self._config = config
        self._app    = create_server(config, state, overlay, lock_manager, logger)
        self._thread: threading.Thread | None = None

    def start(self):
        host = self._config.get("api", {}).get("host", "127.0.0.1")
        port = self._config.get("api", {}).get("port", 5000)

        self._thread = threading.Thread(
            target=lambda: self._app.run(
                host=host, port=port, debug=False, use_reloader=False
            ),
            name="APIServerThread",
            daemon=True
        )
        self._thread.start()
        print(f"[AuraSafe] API server running at http://{host}:{port}")


# ── Dashboard + Settings routes (appended to existing server.py) ────────────

def add_dashboard_routes(app, config_path):
    """Add dashboard UI + save_keywords + save_settings routes."""
    import json, os
    from flask import render_template, send_from_directory

    @app.route("/", methods=["GET"])
    @app.route("/dashboard", methods=["GET"])
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/save_keywords", methods=["POST"])
    def save_keywords():
        """Write new keyword lists back to config.json."""
        try:
            data = request.get_json(silent=True) or {}
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["detection"]["english_keywords"]  = data.get("english",  [])
            cfg["detection"]["tanglish_keywords"] = data.get("tanglish", [])
            cfg["detection"]["tamil_keywords"]    = data.get("tamil",    [])
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/save_settings", methods=["POST"])
    def save_settings():
        """Update PIN and/or port in config.json."""
        try:
            data = request.get_json(silent=True) or {}
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if "pin" in data and data["pin"]:
                cfg["pin"] = str(data["pin"])
            if "port" in data and data["port"]:
                cfg["api"]["port"] = int(data["port"])
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500


def add_analytics_routes(app, logger):
    """Real SQLite-backed analytics endpoints."""
    from datetime import datetime, timedelta
    import sqlite3, os

    def get_db():
        from logger import AuraLogger
        # Access the db_path from logger instance
        return logger.db_path

    @app.route("/analytics/daily", methods=["GET"])
    def analytics_daily():
        """Events grouped by day for last 30 days."""
        try:
            conn = sqlite3.connect(get_db())
            rows = conn.execute("""
                SELECT DATE(timestamp) as day, event_type, COUNT(*) as cnt
                FROM events
                WHERE timestamp >= DATE('now', '-30 days')
                GROUP BY day, event_type
                ORDER BY day ASC
            """).fetchall()
            conn.close()

            # Build day-keyed dict
            data = {}
            for row in rows:
                day, etype, cnt = row
                if day not in data:
                    data[day] = {}
                data[day][etype] = cnt

            # Fill missing days
            result = []
            for i in range(30):
                d = (datetime.utcnow() - timedelta(days=29-i)).strftime("%Y-%m-%d")
                result.append({
                    "date":      d,
                    "label":     (datetime.strptime(d, "%Y-%m-%d")).strftime("%-m/%-d") if os.name != 'nt'
                                 else (datetime.strptime(d, "%Y-%m-%d")).strftime("%m/%d").lstrip("0"),
                    "BLOCK":     data.get(d, {}).get("BLOCK", 0),
                    "DETECTION": data.get(d, {}).get("DETECTION", 0),
                    "APP_BLOCKED":data.get(d,{}).get("APP_BLOCKED",0),
                    "FOCUS_LOCK":data.get(d, {}).get("FOCUS_LOCK", 0),
                })
            return jsonify({"ok": True, "days": result})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/analytics/hourly", methods=["GET"])
    def analytics_hourly():
        """Events grouped by hour of day (last 7 days)."""
        try:
            conn = sqlite3.connect(get_db())
            rows = conn.execute("""
                SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                       COUNT(*) as cnt
                FROM events
                WHERE timestamp >= DATE('now', '-7 days')
                GROUP BY hour
                ORDER BY hour ASC
            """).fetchall()
            conn.close()

            hour_map = {r[0]: r[1] for r in rows}
            data = [hour_map.get(h, 0) for h in range(24)]
            return jsonify({"ok": True, "hours": data})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/analytics/languages", methods=["GET"])
    def analytics_languages():
        """
        Breakdown by language based on keyword source in content field.
        Uses source column tagged 'extension' + content keyword matching.
        """
        try:
            conn = sqlite3.connect(get_db())
            # Count by language tag stored in extra field or infer from content
            rows = conn.execute("""
                SELECT
                    CASE
                        WHEN extra LIKE '%tamil%'    OR content LIKE '%tamil%'    THEN 'Tamil'
                        WHEN extra LIKE '%tanglish%' OR content LIKE '%tanglish%' THEN 'Tanglish'
                        ELSE 'English'
                    END as lang,
                    COUNT(*) as cnt
                FROM events
                WHERE event_type IN ('BLOCK','DETECTION')
                GROUP BY lang
            """).fetchall()
            conn.close()

            result = {"English": 0, "Tamil": 0, "Tanglish": 0}
            for lang, cnt in rows:
                result[lang] = cnt
            return jsonify({"ok": True, "languages": result})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/analytics/weekly", methods=["GET"])
    def analytics_weekly():
        """Events grouped by day of week (last 4 weeks)."""
        try:
            conn = sqlite3.connect(get_db())
            rows = conn.execute("""
                SELECT strftime('%w', timestamp) as dow, COUNT(*) as cnt
                FROM events
                WHERE timestamp >= DATE('now', '-28 days')
                GROUP BY dow
                ORDER BY dow ASC
            """).fetchall()
            conn.close()

            # 0=Sun ... 6=Sat → remap to Mon-Sun
            dow_map = {int(r[0]): r[1] for r in rows}
            days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
            data = [dow_map.get(i, 0) for i in range(7)]
            return jsonify({"ok": True, "days": days, "counts": data})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
