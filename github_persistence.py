# github_persistence.py v3 - robuste avec diagnostic d'erreur clair
import streamlit as st
import os, base64, time, threading, json
import urllib.request, urllib.error

_SAVE_INTERVAL = 60
_last_save_time = 0
_pending_save = False
_lock = threading.Lock()
_bg_thread = None
_last_error = ""


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


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",  # Bearer fonctionne mieux que token
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "EastwoodApp/1.0",
    }


def load_db_from_github(local_path):
    """Télécharge la DB depuis GitHub."""
    global _last_error
    token, repo, remote_path, branch = _cfg()
    if not token or not repo:
        return False
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{remote_path}?ref={branch}"
        req = urllib.request.Request(url, headers=_headers(token))
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if "content" in data:
            db_bytes = base64.b64decode(data["content"])
            with open(local_path, "wb") as f:
                f.write(db_bytes)
            _last_error = ""
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode() if hasattr(e, "read") else ""
        _last_error = f"HTTP {e.code}: {body[:100]}"
    except Exception as e:
        _last_error = str(e)
    return False


def save_db_to_github(local_path, message="auto: sync data"):
    """Sauvegarde synchrone vers GitHub. Retourne (ok, erreur)."""
    global _last_save_time, _pending_save, _last_error
    token, repo, remote_path, branch = _cfg()
    if not token or not repo:
        return False, "GITHUB_TOKEN ou GITHUB_REPO manquant dans les secrets Streamlit"
    if not os.path.exists(local_path):
        return False, f"Fichier DB introuvable : {local_path}"
    try:
        with open(local_path, "rb") as f:
            db_b64 = base64.b64encode(f.read()).decode()

        url = f"https://api.github.com/repos/{repo}/contents/{remote_path}"

        # Récupérer le SHA du fichier existant
        sha = None
        try:
            req = urllib.request.Request(
                url + f"?ref={branch}", headers=_headers(token))
            with urllib.request.urlopen(req, timeout=10) as resp:
                existing = json.loads(resp.read().decode())
                sha = existing.get("sha")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                sha = None  # Fichier n'existe pas encore, ok
            elif e.code == 401:
                return False, "Token invalide (401). Vérifie que GITHUB_TOKEN est correct et a la permission 'repo'."
            elif e.code == 403:
                return False, "Token sans permission (403). Crée un nouveau token avec la permission 'repo' complète."
            else:
                return False, f"Erreur GitHub GET : HTTP {e.code}"

        payload = {"message": message, "content": db_b64, "branch": branch}
        if sha:
            payload["sha"] = sha

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, method="PUT", headers={**_headers(token), "Content-Type": "application/json"})

        with urllib.request.urlopen(req, timeout=25) as resp:
            status = resp.status

        with _lock:
            _last_save_time = time.time()
            _pending_save = False
            _last_error = ""

        return True, ""

    except urllib.error.HTTPError as e:
        body = ""
        try: body = e.read().decode()[:200]
        except: pass
        if e.code == 401:
            msg = "Token GitHub invalide (401). Va sur github.com → Settings → Developer settings → Personal access tokens → crée un nouveau token avec permission 'repo' et mets-le dans les secrets Streamlit."
        elif e.code == 403:
            msg = "Permission refusée (403). Le token n'a pas accès au repo. Vérifie qu'il a la permission 'repo' et que tu es bien owner du repo."
        elif e.code == 422:
            msg = "Rien à sauvegarder (données identiques)."
            with _lock:
                _last_save_time = time.time()
                _pending_save = False
            return True, ""
        else:
            msg = f"Erreur GitHub : HTTP {e.code} — {body}"
        _last_error = msg
        return False, msg
    except Exception as e:
        _last_error = str(e)
        return False, str(e)


def _bg_loop(local_path):
    global _pending_save, _last_save_time
    while True:
        time.sleep(5)
        now = time.time()
        with _lock:
            do_save = (
                (_pending_save and now - _last_save_time >= 5) or
                (now - _last_save_time >= _SAVE_INTERVAL)
            )
        if do_save and os.path.exists(local_path):
            save_db_to_github(local_path, "auto: background sync")


def start_background_sync(local_path):
    global _bg_thread
    if _bg_thread and _bg_thread.is_alive():
        return
    _bg_thread = threading.Thread(
        target=_bg_loop, args=(local_path,),
        daemon=True, name="GHSync"
    )
    _bg_thread.start()


def mark_dirty():
    global _pending_save
    with _lock:
        _pending_save = True


def get_status():
    with _lock:
        return {
            "pending":    _pending_save,
            "last_save":  _last_save_time,
            "configured": is_configured(),
            "thread_ok":  bool(_bg_thread and _bg_thread.is_alive()),
            "last_error": _last_error,
        }
