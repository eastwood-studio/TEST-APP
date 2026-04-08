# ══════════════════════════════════════════════════════════════════════════════
# github_persistence.py
# Sauvegarde automatique de la DB SQLite dans GitHub via l'API
# Données permanentes même après reboot Streamlit Cloud
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import os
import base64
import sqlite3
import time
import threading

_last_save_time = 0
_save_lock = threading.Lock()
_SAVE_INTERVAL = 30  # secondes minimum entre deux sauvegardes auto


def _get_github_config():
    """Récupère la config GitHub depuis les secrets Streamlit."""
    try:
        token = st.secrets.get("GITHUB_TOKEN", None)
        repo  = st.secrets.get("GITHUB_REPO", None)   # ex: "jules-leger/eastwood-app"
        path  = st.secrets.get("GITHUB_DB_PATH", "eastwood_data.db")
        return token, repo, path
    except Exception:
        return None, None, None


def is_configured():
    """Retourne True si GitHub persistence est configuré."""
    token, repo, _ = _get_github_config()
    return bool(token and repo)


def load_db_from_github(local_db_path: str) -> bool:
    """
    Télécharge la DB depuis GitHub et l'écrit localement.
    Appelé au démarrage si la DB locale n'existe pas.
    Retourne True si succès.
    """
    token, repo, remote_path = _get_github_config()
    if not token or not repo:
        return False

    try:
        import urllib.request
        import json

        url = f"https://api.github.com/repos/{repo}/contents/{remote_path}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "EastwoodStudio-App"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        if "content" in data:
            db_bytes = base64.b64decode(data["content"])
            with open(local_db_path, "wb") as f:
                f.write(db_bytes)
            return True

    except Exception:
        pass

    return False


def save_db_to_github(local_db_path: str, message: str = "auto: sync eastwood data") -> bool:
    """
    Uploade la DB locale vers GitHub.
    Appelé après chaque opération d'écriture.
    Retourne True si succès.
    """
    global _last_save_time

    token, repo, remote_path = _get_github_config()
    if not token or not repo:
        return False

    if not os.path.exists(local_db_path):
        return False

    # Rate limiting : pas plus d'une sauvegarde toutes les 30s
    now = time.time()
    with _save_lock:
        if now - _last_save_time < _SAVE_INTERVAL:
            return True  # Skip mais pas d'erreur
        _last_save_time = now

    try:
        import urllib.request
        import urllib.error
        import json

        with open(local_db_path, "rb") as f:
            db_bytes = f.read()
        db_b64 = base64.b64encode(db_bytes).decode()

        url = f"https://api.github.com/repos/{repo}/contents/{remote_path}"

        # Récupérer le SHA actuel du fichier (nécessaire pour update)
        sha = None
        try:
            req_get = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "EastwoodStudio-App"
                }
            )
            with urllib.request.urlopen(req_get, timeout=8) as resp:
                existing = json.loads(resp.read().decode())
                sha = existing.get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            # 404 = fichier n'existe pas encore, ok

        # Préparer le payload
        payload = {
            "message": message,
            "content": db_b64,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        payload_bytes = json.dumps(payload).encode("utf-8")
        req_put = urllib.request.Request(
            url,
            data=payload_bytes,
            method="PUT",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
                "User-Agent": "EastwoodStudio-App"
            }
        )
        with urllib.request.urlopen(req_put, timeout=15) as resp:
            return resp.status in (200, 201)

    except Exception:
        return False


def save_async(local_db_path: str, message: str = "auto: sync"):
    """Lance la sauvegarde GitHub en arrière-plan (non bloquant)."""
    def _worker():
        save_db_to_github(local_db_path, message)
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
