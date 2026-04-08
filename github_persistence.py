# ══════════════════════════════════════════════════════════════════════════════
# github_persistence.py v2
# Sauvegarde auto fiable : thread permanent + sync après chaque write
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import os, base64, time, threading, json
import urllib.request, urllib.error

_SAVE_INTERVAL = 60
_last_save_time = 0
_pending_save = False
_lock = threading.Lock()
_bg_thread = None


def _cfg():
    try:
        t = st.secrets.get("GITHUB_TOKEN", None)
        r = st.secrets.get("GITHUB_REPO", None)
        p = st.secrets.get("GITHUB_DB_PATH", "eastwood_data.db")
        b = st.secrets.get("GITHUB_BRANCH", "main")
        return t, r, p, b
    except Exception:
        return None, None, "eastwood_data.db", "main"


def is_configured():
    t, r, _, _ = _cfg()
    return bool(t and r)


def _api_get(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "EastwoodApp"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _api_put(url, token, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "EastwoodApp"
    })
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())


def load_db_from_github(local_path):
    token, repo, remote_path, branch = _cfg()
    if not token or not repo:
        return False
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{remote_path}?ref={branch}"
        data = _api_get(url, token)
        if "content" in data:
            db_bytes = base64.b64decode(data["content"])
            with open(local_path, "wb") as f:
                f.write(db_bytes)
            return True
    except Exception:
        pass
    return False


def save_db_to_github(local_path, message="auto: sync"):
    global _last_save_time, _pending_save
    token, repo, remote_path, branch = _cfg()
    if not token or not repo:
        return False, "Secrets GITHUB_TOKEN / GITHUB_REPO manquants"
    if not os.path.exists(local_path):
        return False, "DB introuvable"
    try:
        with open(local_path, "rb") as f:
            db_b64 = base64.b64encode(f.read()).decode()
        url = f"https://api.github.com/repos/{repo}/contents/{remote_path}"
        sha = None
        try:
            data = _api_get(url + f"?ref={branch}", token)
            sha = data.get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
        payload = {"message": message, "content": db_b64, "branch": branch}
        if sha:
            payload["sha"] = sha
        _api_put(url, token, payload)
        with _lock:
            _last_save_time = time.time()
            _pending_save = False
        return True, ""
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


def _bg_loop(local_path):
    global _pending_save, _last_save_time
    while True:
        time.sleep(5)
        now = time.time()
        with _lock:
            do_save = (_pending_save and now - _last_save_time >= 5) or (now - _last_save_time >= _SAVE_INTERVAL)
        if do_save and os.path.exists(local_path):
            save_db_to_github(local_path, "auto: background sync")


def start_background_sync(local_path):
    global _bg_thread
    if _bg_thread and _bg_thread.is_alive():
        return
    _bg_thread = threading.Thread(target=_bg_loop, args=(local_path,), daemon=True, name="GHSync")
    _bg_thread.start()


def mark_dirty():
    global _pending_save
    with _lock:
        _pending_save = True


def get_status():
    with _lock:
        return {
            "pending": _pending_save,
            "last_save": _last_save_time,
            "configured": is_configured(),
            "thread_ok": bool(_bg_thread and _bg_thread.is_alive()),
        }
