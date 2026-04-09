import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import io
import os
import hashlib
import base64
import sys
import os as _os
for _p in [_os.path.dirname(_os.path.abspath(__file__)), ".", "/mount/src/test-app"]:
    if _p not in sys.path: sys.path.insert(0, _p)
try:
    from products_module import (page_produits, page_couts_produits, init_products_db, sync_from_commande, get_collections_dynamic, COST_SECTIONS, compute_cost_totals)
    PRODUCTS_MODULE = True
except Exception as _e:
    PRODUCTS_MODULE = False
    _PRODUCTS_ERR = str(_e)

try:
    from contacts_module import page_contacts
    CONTACTS_MODULE = True
except Exception:
    CONTACTS_MODULE = False

try:
    from calendar_module import page_calendrier
    CALENDAR_MODULE = True
except Exception:
    CALENDAR_MODULE = False

try:
    from marketing_module import page_marketing
    MARKETING_MODULE = True
except Exception:
    MARKETING_MODULE = False

try:
    from tva_module import page_tva
    TVA_MODULE = True
except Exception:
    TVA_MODULE = False

try:
    from operations_module import page_operations
    OPERATIONS_MODULE = True
except Exception:
    OPERATIONS_MODULE = False

try:
    from crm_module import page_crm
    CRM_MODULE = True
except Exception:
    CRM_MODULE = False

try:
    from todo_module import render_todo_widget, init_todo_db
    TODO_MODULE = True
except Exception:
    TODO_MODULE = False

try:
    from balance_module import page_balance
    BALANCE_MODULE = True
except Exception:
    BALANCE_MODULE = False

# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTIFICATION & PERMISSIONS
# ══════════════════════════════════════════════════════════════════════════════
USERS = {
    "jules": {
        "password_hash": hashlib.sha256("jules2025".encode()).hexdigest(),
        "role": "superuser", "display": "Jules Léger", "initial": "JL",
    },
    "corentin": {
        "password_hash": hashlib.sha256("corentin2025".encode()).hexdigest(),
        "role": "ops", "display": "Corentin", "initial": "CB",
    },
    "alexis": {
        "password_hash": hashlib.sha256("alexis2025".encode()).hexdigest(),
        "role": "crm", "display": "Alexis", "initial": "AB",
    },
}

PERMISSIONS = {
    "superuser": {
        "finance_read": True, "finance_write": True,
        "commandes_read": True, "commandes_write": True,
        "stock_read": True, "stock_write": True,
        "contacts_read": True, "contacts_add": True,
        "contacts_edit": True, "contacts_delete": True,
        "tva_read": True, "products_delete": True,
    },
    "ops": {
        "finance_read": True, "finance_write": False,
        "commandes_read": True, "commandes_write": True,
        "stock_read": True, "stock_write": True,   # Corentin peut ajouter stock
        "contacts_read": True, "contacts_add": True,
        "contacts_edit": True, "contacts_delete": False,
        "tva_read": False, "products_delete": False,
    },
    "crm": {
        "finance_read": True, "finance_write": False,
        "commandes_read": True, "commandes_write": False,
        "stock_read": True, "stock_write": False,
        "contacts_read": True, "contacts_add": True,
        "contacts_edit": True, "contacts_delete": False,
        "tva_read": False, "products_delete": False,
    },
}

def can(perm: str) -> bool:
    return PERMISSIONS.get(st.session_state.get("user_role", ""), {}).get(perm, False)

def check_login(username: str, password: str) -> bool:
    u = username.strip().lower()
    if u not in USERS:
        return False
    if hashlib.sha256(password.encode()).hexdigest() == USERS[u]["password_hash"]:
        st.session_state.update({
            "logged_in": True, "username": u,
            "user_display": USERS[u]["display"],
            "user_role": USERS[u]["role"],
            "user_initial": USERS[u]["initial"],
        })
        return True
    return False

# ── Palette Eastwood ──────────────────────────────────────────────────────────
EW_BEIGE   = "#d9c8ae"
EW_BROWN   = "#8a7968"
EW_GREEN   = "#395f30"
EW_VIOLET  = "#7b506f"
EW_BLACK   = "#1a1a1a"
EW_CREAM   = "#f5f0e8"
EW_SAND    = "#ede3d3"
EW_DARK    = "#0d0b09"

LOGO_SVG = """<svg width="148" height="30" viewBox="0 0 148 30" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="9" width="2.5" height="14" fill="#d9c8ae"/>
  <text font-family="'DM Mono',monospace" font-size="11.5" font-weight="500"
        letter-spacing="3.5" fill="#f5f0e8" x="9" y="20">EASTWOOD</text>
  <text font-family="'DM Mono',monospace" font-size="6.5" font-weight="300"
        letter-spacing="6" fill="#8a7968" x="9" y="29">STUDIO</text>
</svg>"""

LOGO_LOGIN = """<svg width="160" height="34" viewBox="0 0 160 34" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="10" width="2.5" height="16" fill="#7b506f"/>
  <text font-family="'DM Mono',monospace" font-size="13" font-weight="500"
        letter-spacing="4" fill="#1a1a1a" x="10" y="23">EASTWOOD</text>
  <text font-family="'DM Mono',monospace" font-size="7" font-weight="300"
        letter-spacing="7" fill="#8a7968" x="10" y="33">STUDIO</text>
</svg>"""

def show_login_page():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');
html,[class*="css"]{font-family:'DM Sans',sans-serif;background:#f5f0e8;}
.main .block-container{max-width:420px!important;margin:0 auto;padding-top:8vh;background:transparent;}
[data-testid="stSidebar"]{display:none;}
.stTextInput>div>div>input{
  border:1px solid #ede3d3!important;border-radius:0!important;
  font-family:'DM Mono',monospace!important;font-size:13px!important;
  background:#fff!important;color:#1a1a1a!important;padding:10px 14px!important;
}
.stTextInput>div>div>input:focus{border-color:#7b506f!important;outline:none!important;}
.stButton>button{
  font-family:'DM Mono',monospace!important;font-size:11px!important;
  letter-spacing:.14em!important;text-transform:uppercase!important;
  background:#7b506f!important;color:#fff!important;
  border:none!important;border-radius:0!important;
  width:100%;padding:12px!important;margin-top:10px!important;
}
.stButton>button:hover{background:#1a1a1a!important;}
</style>""", unsafe_allow_html=True)

    logo_b64 = base64.b64encode(LOGO_LOGIN.encode()).decode()
    st.markdown(f"""
<div style="text-align:center;margin-bottom:36px;">
  <img src="data:image/svg+xml;base64,{logo_b64}" style="width:180px;display:block;margin:0 auto 12px;"/>
  <div style="font-family:'DM Mono',monospace;font-size:8px;letter-spacing:.22em;color:#8a7968;text-transform:uppercase;">
    Gestion interne · Paris
  </div>
</div>
<div style="background:#fff;border:1px solid #ede3d3;padding:36px 32px 28px;">
""", unsafe_allow_html=True)

    username = st.text_input("", placeholder="Identifiant", label_visibility="collapsed")
    password = st.text_input("", type="password", placeholder="Mot de passe", label_visibility="collapsed")
    if st.button("Connexion →"):
        if check_login(username, password):
            st.rerun()
        else:
            st.error("Identifiant ou mot de passe incorrect.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;
     text-align:center;margin-top:28px;letter-spacing:.12em;">
  EASTWOOD STUDIO © 2024 · homemade by Jules Léger
</div>""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    show_login_page()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG & CSS GLOBAL
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Eastwood Studio — Gestion",
    page_icon="🪡", layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap');
html,[class*="css"]{font-family:'DM Sans',sans-serif;}

[data-testid="stSidebar"]{background:#0d0b09;border-right:1px solid #1c1a17;}
[data-testid="stSidebar"] *{color:#c8c3b8!important;}
[data-testid="stSidebar"] .stRadio label{
  font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.06em;
  color:#888070!important;padding:1px 0!important;cursor:pointer;
}
[data-testid="stSidebar"] .stRadio label:hover{color:#d9c8ae!important;}
[data-testid="stSidebar"] .stRadio label p{
  font-family:'DM Mono',monospace;font-size:11px;
  color:#888070!important;margin:0;
}

.nav-group-label{
  font-family:'DM Mono',monospace;font-size:8px;letter-spacing:.22em;
  text-transform:uppercase;color:#8a7968!important;
  padding:14px 0 4px;display:block;
}

.main .block-container{background:#f5f0e8;padding-top:1.4rem;min-height:100vh;}

.section-title{
  font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.2em;
  text-transform:uppercase;color:#8a7968;
  border-bottom:1px solid #ede3d3;padding-bottom:7px;margin:22px 0 14px;
}

.stButton>button{
  font-family:'DM Mono',monospace!important;font-size:10px!important;
  letter-spacing:.12em!important;text-transform:uppercase!important;
  background:#7b506f!important;color:#fff!important;
  border:none!important;border-radius:0!important;padding:8px 18px!important;
}
.stButton>button:hover{background:#1a1a1a!important;}
.stButton>button[kind="secondary"]{
  background:transparent!important;color:#8a7968!important;
  border:1px solid #ede3d3!important;
}
.stButton>button[kind="secondary"]:hover{background:#ede3d3!important;}

.stTextInput>div>div>input,
.stTextArea>div>div>textarea{
  border-radius:0!important;border-color:#ede3d3!important;
  font-family:'DM Mono',monospace!important;font-size:12px!important;
}
.stTextInput>div>div>input:focus,
.stTextArea>div>div>textarea:focus{
  border-color:#7b506f!important;box-shadow:0 0 0 1px #7b506f!important;
}

.stDataFrame{border:1px solid #ede3d3!important;border-radius:0!important;}

.alert-box{
  background:#fdf6ec;border:1px solid #e8c87a;border-left:3px solid #c9800a;
  padding:12px 16px;font-size:13px;color:#5a3e00;margin:10px 0;
}
.info-box{
  background:#f0f5ef;border:1px solid #a8c4a4;border-left:3px solid #395f30;
  padding:12px 16px;font-size:13px;color:#1e3a1a;margin:10px 0;
}

.badge{display:inline-block;font-family:'DM Mono',monospace;font-size:9px;padding:2px 8px;}
.badge-vente{background:#e8f2e8;color:#395f30;}
.badge-achat{background:#ede3d3;color:#8a7968;}
.badge-violet{background:#f0eaf0;color:#7b506f;}

[data-testid="stMetricDelta"]{font-family:'DM Mono',monospace;font-size:11px;}
[data-testid="stMetricValue"]{font-family:'DM Mono',monospace;}

.stTabs [data-baseweb="tab"]{
  font-family:'DM Mono',monospace;font-size:10px;
  letter-spacing:.1em;text-transform:uppercase;color:#8a7968!important;
}
.stTabs [aria-selected="true"]{
  color:#7b506f!important;border-bottom-color:#7b506f!important;
}

footer{visibility:hidden;}
</style>""", unsafe_allow_html=True)
# DATABASE
# ══════════════════════════════════════════════════════════════════════════════
import os as _os2
import shutil as _shutil

_DB_DIR = _os2.path.dirname(_os2.path.abspath(__file__)) if "__file__" in dir() else "."
DB_PATH        = _os2.path.join(_DB_DIR, "eastwood_data.db")
DB_BACKUP_PATH = _os2.path.join(_DB_DIR, "eastwood_backup.db")

# Au démarrage : si la DB runtime n'existe pas mais qu'un backup existe → restaurer
if not _os2.path.exists(DB_PATH) and _os2.path.exists(DB_BACKUP_PATH):
    try:
        _shutil.copy2(DB_BACKUP_PATH, DB_PATH)
    except Exception:
        pass

# ── Connexion DB : PostgreSQL (Supabase) si configuré, sinon SQLite ───────────
try:
    from db_connection import get_conn as _get_conn_impl, read_sql as _read_sql_impl, is_postgresql
    _USE_SUPABASE = is_postgresql()
except Exception:
    _USE_SUPABASE = False
    _get_conn_impl = None
    _read_sql_impl = None

# ── Persistence GitHub ────────────────────────────────────────────────────────
try:
    from github_persistence import (
        is_configured as _gh_configured,
        load_db_from_github as _gh_load,
        save_db_to_github as _gh_save,
        start_background_sync as _gh_start_sync,
        mark_dirty as _gh_mark_dirty,
        get_status as _gh_get_status,
    )
    _GH_PERSISTENCE = _gh_configured()
except Exception as _gh_err:
    _GH_PERSISTENCE = False
    _gh_load = _gh_save = _gh_start_sync = _gh_mark_dirty = _gh_get_status = None

# Au démarrage : charger la DB depuis GitHub si elle n'existe pas localement
if _GH_PERSISTENCE and not _USE_SUPABASE:
    if not _os2.path.exists(DB_PATH):
        _gh_load(DB_PATH)
    # Démarrer le thread de sync automatique (toutes les 60s)
    _gh_start_sync(DB_PATH)

class _AutoSaveConn:
    """
    Wrapper SQLite qui sauvegarde automatiquement sur GitHub
    après chaque commit(). Transparent pour tout le code existant.
    """
    def __init__(self, path):
        self._conn = sqlite3.connect(path, check_same_thread=False)

    def cursor(self):
        return self._conn.cursor()

    def execute(self, sql, params=()):
        return self._conn.execute(sql, params)

    def executemany(self, sql, params):
        return self._conn.executemany(sql, params)

    def commit(self):
        self._conn.commit()
        # Signaler au thread de sync qu'une sauvegarde est nécessaire
        if _GH_PERSISTENCE and _gh_mark_dirty and not _USE_SUPABASE:
            _gh_mark_dirty()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def get_conn():
    if _USE_SUPABASE and _get_conn_impl:
        return _get_conn_impl()
    return _AutoSaveConn(DB_PATH)

def init_db():
    conn = get_conn(); c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        annee INTEGER, mois INTEGER, date_op TEXT,
        ref_produit TEXT, info_process TEXT, description TEXT,
        categorie TEXT, type_op TEXT,
        quantite REAL, unite TEXT,
        prix_unitaire REAL, type_tva TEXT,
        total_ht REAL, total_ttc REAL, tva REAL,
        devise TEXT DEFAULT 'EUR', taux_change REAL DEFAULT 1.0, montant_original REAL,
        payeur TEXT, beneficiaire TEXT,
        source TEXT, info_complementaire TEXT,
        facture_data BLOB, facture_nom TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS commandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        priorite TEXT, date_commande TEXT,
        num_commande TEXT, num_facture TEXT, num_exclusif TEXT,
        ref_article TEXT, qte REAL,
        prix_ht REAL, vat REAL, prix_ttc REAL, prix_final REAL,
        plateforme TEXT,
        prenom TEXT, nom TEXT, mail TEXT, telephone TEXT, adresse TEXT,
        transporteur INTEGER DEFAULT 0, mesures INTEGER DEFAULT 0,
        matiere_premiere INTEGER DEFAULT 0, production INTEGER DEFAULT 0,
        pf_valide INTEGER DEFAULT 0, packaging INTEGER DEFAULT 0,
        envoi INTEGER DEFAULT 0, date_envoi TEXT,
        etat TEXT, notes TEXT, fnf INTEGER DEFAULT 0,
        type_cmd TEXT DEFAULT 'B2C',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT, ref TEXT UNIQUE,
        type_produit TEXT,
        localisation TEXT DEFAULT 'Paris — Atelier',
        qte_stock REAL DEFAULT 0, qte_utilisee REAL DEFAULT 0, qte_vendue REAL DEFAULT 0,
        prix_unitaire REAL DEFAULT 0,
        besoin_reassort INTEGER DEFAULT 0,
        notes TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_contact TEXT, sous_type TEXT,
        nom TEXT, entreprise TEXT, email TEXT, telephone TEXT,
        instagram TEXT, activite TEXT, adresse TEXT, pays TEXT,
        importance TEXT DEFAULT 'Normal',
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER,
        nom_fichier TEXT, date_facture TEXT,
        type_doc TEXT, prestataire TEXT,
        data BLOB,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("SELECT COUNT(*) FROM transactions")
    if c.fetchone()[0] == 0:
        _seed_demo(c)

    # Migrations silencieuses
    _tx_cols = [r[1] for r in c.execute("PRAGMA table_info(transactions)").fetchall()]
    for _col, _def in [
        ("frais_envoi","REAL DEFAULT 0"),
        ("collection_op","TEXT DEFAULT ''"),
        ("client_nom","TEXT DEFAULT ''"),
        ("client_email","TEXT DEFAULT ''"),
        ("client_tel","TEXT DEFAULT ''"),
        ("client_adresse","TEXT DEFAULT ''"),
        ("num_operation","INTEGER DEFAULT 0"),
        ("total_ttc","REAL DEFAULT 0"),
    ]:
        if _col not in _tx_cols:
            try: c.execute(f"ALTER TABLE transactions ADD COLUMN {_col} {_def}")
            except Exception: pass

    _cmd_cols = [r[1] for r in c.execute("PRAGMA table_info(commandes)").fetchall()]
    for _col, _def in [("type_cmd","TEXT DEFAULT 'B2C'")]:
        if _col not in _cmd_cols:
            try: c.execute(f"ALTER TABLE commandes ADD COLUMN {_col} {_def}")
            except Exception: pass

    conn.commit(); conn.close()

    # Migration collections DB
    try:
        c2 = conn2.cursor() if hasattr(conn2, "cursor") else None
        _conn_mig = get_conn()
        _conn_mig.execute("""UPDATE transactions SET collection_op='Chapter I — Hunting & Fishing'
            WHERE collection_op LIKE '%Hunting%' AND collection_op != 'Chapter I — Hunting & Fishing'""")
        _conn_mig.execute("""UPDATE transactions SET collection_op='Chapter II — Le Souvenir'
            WHERE collection_op LIKE '%Souvenir%' AND collection_op != 'Chapter II — Le Souvenir'""")
        _conn_mig.execute("""UPDATE products SET collection='Chapter I — Hunting & Fishing'
            WHERE collection LIKE '%Hunting%' AND collection != 'Chapter I — Hunting & Fishing'""")
        _conn_mig.execute("""UPDATE products SET collection='Chapter II — Le Souvenir'
            WHERE collection LIKE '%Souvenir%' AND collection != 'Chapter II — Le Souvenir'""")
        _conn_mig.commit()
        _conn_mig.close()
    except Exception:
        pass

    # Auto-backup local
    try:
        if _os2.path.exists(DB_PATH):
            _shutil.copy2(DB_PATH, DB_BACKUP_PATH)
    except Exception:
        pass

    # Démarrer le thread de sync (idempotent — ne lance pas deux fois)
    if _GH_PERSISTENCE and _gh_start_sync and not _USE_SUPABASE:
        _gh_start_sync(DB_PATH)
        if _gh_mark_dirty:
            _gh_mark_dirty()

def _seed_demo(c):
    demo_tx = [
        (2025,3,"2025-03-02","MIRA-001","Veste Miura Jacket","Achat tissu japonais SOLOTEX 50m","Matière première","Achat",50,"Mètre",28.0,"Déductible",1400.0,1680.0,280.0,"EUR",1.0,1400.0,"Eastwood","Atelier Soierie Lyon","Jim Jin +86 133 9131 8965","N°CMD 5960",None,None),
        (2025,3,"2025-03-05","GENE","Finance","Abonnement Brévo e-mail marketing","Logiciel & outils","Achat",1,"Euros",49.0,"Déductible",49.0,58.8,9.8,"EUR",1.0,49.0,"Eastwood","Brévo SAS","Brévo","INV-2025-0312",None,None),
        (2025,3,"2025-03-10","MIRA-001","Veste Miura Jacket","Vente pop-up Japon — 3 pièces","Facture","Vente",3,"Article",420.0,"Aucun",1260.0,1260.0,0.0,"JPY",0.006,210000.0,"Client JP","Eastwood","Pop-up Tokyo Shibuya","N°Client 0002142722",None,None),
        (2025,3,"2025-03-12","MIRA-001","Shipping","Envoi postal collection Tokyo → Berlin","Transport / Logistique","Achat",1,"Euros",185.0,"Déductible",185.0,222.0,37.0,"EUR",1.0,185.0,"Eastwood","DHL Express","DHL Business","AWB 1234567890",None,None),
        (2025,3,"2025-03-15","COMP-002","Étiquettes","Achat étiquettes 'Fabrication Française' x500","Composants","Achat",500,"Pièces",0.35,"Déductible",175.0,210.0,35.0,"EUR",1.0,175.0,"Eastwood","Imprimerie Parisienne","Manigance Paris","",None,None),
        (2025,3,"2025-03-18","GENE","Shooting","Shooting photo collection SS25 — studio Paris","Communication","Achat",1,"Euros",800.0,"Déductible",800.0,960.0,160.0,"EUR",1.0,800.0,"Jules","Studio Bastille","Studio Bastille 75011","FACT-2025-089",None,None),
        (2025,3,"2025-03-20","MIRA-001","Confection","Confection 10 vestes Miura — atelier Belleville","Confection / Production","Achat",10,"Article",95.0,"Déductible",950.0,1140.0,190.0,"EUR",1.0,950.0,"Eastwood","Atelier Belleville","Atelier des Créateurs 75020","N°CMD 6012",None,None),
        (2025,4,"2025-04-01","PANT-003","Pantalon Kibo","Vente en ligne — 2 pantalons","Facture","Vente",2,"Article",310.0,"Collectée",620.0,744.0,124.0,"EUR",1.0,620.0,"Client FR","Eastwood","Shopify Order #8821","N°8821",None,None),
        (2025,4,"2025-04-03","GENE","Finance","Frais bancaires Revolut Business — mars","Autre frais","Achat",1,"Euros",25.0,"Aucun",25.0,25.0,0.0,"EUR",1.0,25.0,"Eastwood","Revolut Business","Revolut Business","",None,None),
        (2025,4,"2025-04-05","GENE","Légal","Dépôt marque INPI — renouvellement","Légal / Administratif","Achat",1,"Euros",250.0,"Aucun",250.0,250.0,0.0,"EUR",1.0,250.0,"Eastwood","INPI","INPI France","REF-INPI-2025-441",None,None),
    ]
    c.executemany("""INSERT INTO transactions
        (annee,mois,date_op,ref_produit,info_process,description,categorie,type_op,
         quantite,unite,prix_unitaire,type_tva,total_ht,total_ttc,tva,
         devise,taux_change,montant_original,payeur,beneficiaire,source,info_complementaire,facture_data,facture_nom)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", demo_tx)

    demo_cmd = []  # Pas de données démo

    c.executemany("""INSERT OR IGNORE INTO stock
        (description,ref,type_produit,localisation,qte_stock,qte_utilisee,qte_vendue,prix_unitaire,besoin_reassort)
        VALUES (?,?,?,?,?,?,?,?,?)""", [
        # ── Composants & Étiquettes ───────────────────────────────────────────
        ("Boutons Eastwood Studio Nacre","COMP-BTN-001","Composant","Paris — Atelier",150,0,0,0.80,0),
        ("Étiquettes textile","COMP-ETQ-TEX","Composant","Paris — Atelier",100,0,0,0.30,0),
        ("Étiquettes fabrication Française","COMP-ETQ-FBF","Composant","Paris — Atelier",100,0,0,0.25,0),
        ("Étiquettes de taille T1 (S)","COMP-ETQ-T1","Composant","Paris — Atelier",50,0,0,0.10,0),
        ("Étiquettes de taille T2 (M)","COMP-ETQ-T2","Composant","Paris — Atelier",50,0,0,0.10,0),
        ("Étiquettes de taille T3 (L)","COMP-ETQ-T3","Composant","Paris — Atelier",50,0,0,0.10,0),
        ("Étiquettes de taille T4 (XL)","COMP-ETQ-T4","Composant","Paris — Atelier",50,0,0,0.10,0),
        ("Étiquette composition","COMP-ETQ-COMP","Composant","Paris — Atelier",50,0,0,0.15,0),
        ("Zip Talon 1060","COMP-ZIP-001","Composant","Paris — Atelier",6,0,0,2.50,1),
        ("Tissus Whipcord Noir","MAT-WPC-BLK","Matière première","Paris — Atelier",5,0,0,45.0,0),
        # ── Packaging ─────────────────────────────────────────────────────────
        ("Pochette enveloppe postale XL craft","PKG-ENV-XL","Packaging","Paris — Atelier",40,0,0,1.20,0),
        ("Stickers logo blanc cercle","PKG-STK-001","Packaging","Paris — Atelier",50,0,0,0.20,0),
        # ── Produits finis ────────────────────────────────────────────────────
        ("Waterfowl Jacket Tobacco T2 (M)","EWSJACKET-001A-TOB-T2","Produit fini","Paris — Atelier",1,0,0,480.0,0),
        ("Souvenir Cap Faded Green","EWSGEAR-001A-GRN","Produit fini","Paris — Atelier",12,0,0,27.0,0),
        ("Souvenir Cap Deep Rust","EWSGEAR-001B-RST","Produit fini","Paris — Atelier",12,0,0,27.0,0),
        ("Memory Card-Holder Baranil Gold","EWSGEAR-003A","Produit fini","Paris — Atelier",10,0,0,145.0,0),
        # ── Samples ───────────────────────────────────────────────────────────
        ("Akagi Jacket T1 (S) — sample","EWSJACKET-003A-SMPL-T1","Sample","Paris — Atelier",1,0,0,0.0,0),
        ("Miura Jacket T1 (S) — sample","EWSJACKET-002A-SMPL-T1","Sample","Paris — Atelier",1,0,0,0.0,0),
        ("Trésor Silk Square — sample","EWSGEAR-002A-SMPL","Sample","Paris — Atelier",4,0,0,0.0,0),
        ("Souvenir Cap — sample","EWSGEAR-001-SMPL","Sample","Paris — Atelier",4,0,0,0.0,0),
        ("Research Club Shirt T2 Cloud Blue — sample","EWSSHIRT-001A-SMPL-T2","Sample","Paris — Atelier",1,0,0,0.0,0),
        ("Lutèce Plage T1 — sample","EWSSHIRT-002A-SMPL-T1","Sample","Paris — Atelier",1,0,0,0.0,0),
        ("Lutèce Plage T2 — sample","EWSSHIRT-002A-SMPL-T2","Sample","Paris — Atelier",1,0,0,0.0,0),
    ])

    c.executemany("""INSERT INTO contacts
        (type_contact,sous_type,nom,entreprise,email,telephone,instagram,activite,adresse,pays,importance,notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", [
        ("Fournisseur","Tissu","Jim Jin","Shanghai Textiles Co.","jimjin@shanghaitex.cn","+86 133 9131 8965","","Textile import","Shanghai","CN","Haute","Tissu Solotex — délai 3 sem."),
        ("Collaborateur","Atelier","Atelier des Créateurs","Atelier Belleville","contact@atelierbell.fr","+33 1 43 21 00 11","@atelierbell","Confection","47 rue de Belleville, 75020 Paris","FR","Haute","10 pièces min."),
        ("Client","Fidèle","Yuki Tanaka","","yuki@mail.jp","+81 90 1234 5678","@yukitanaka","","Shibuya, Tokyo","JP","Haute","Client fidèle depuis 2024"),
        ("Collaborateur","Prestataire","Studio Bastille","","booking@studiobastille.fr","+33 1 44 22 11 00","@studiobastille","Studio photo","28 rue de la Roquette, 75011","FR","Normal","Shooting — 800€ HT/jour"),
    ])

init_db()

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES & HELPERS
# ══════════════════════════════════════════════════════════════════════════════
CATEGORIES = ["Matière première","Composants","Confection / Production","Communication",
              "Transport / Logistique","Stockage","Salaire","Autre frais",
              "Légal / Administratif","Produit fini","Facture","Logiciel & outils","Packaging"]
TYPES_OP   = ["Achat","Vente","Utilisation","Achat perso"]
TYPES_TVA  = ["Collectée","Déductible","Autoliquidée","Aucun"]
PAYEURS    = ["Eastwood","Jules","Corentin","Alexis"]
DEVISES = ["EUR", "USD", "JPY"]
DEVISE_SYMBOLES = {"EUR":"€","USD":"$","JPY":"¥"}
TYPES_STOCK = ["Produit fini","Sample","Matière première","Composant","Packaging","Autre"]
LOCALISATIONS = ["Paris — Atelier Belleville","Paris — Appartement Jules","Paris — Autre","Tokyo","Berlin","En transit","Autre"]

TVA_RULES = {
    "Vente":       {"default":"Collectée"},
    "Achat":       {"default":"Déductible","Légal / Administratif":"Aucun","Autre frais":"Aucun","Stockage":"Aucun"},
    "Utilisation": {"default":"Aucun"},
    "Achat perso": {"default":"Aucun"},
}

def suggest_tva(type_op, categorie, devise="EUR"):
    if devise not in ("EUR",""):
        return "Autoliquidée"
    rules = TVA_RULES.get(type_op, {})
    return rules.get(categorie, rules.get("default","Aucun"))

def fmt_eur(v):
    if v is None: return "—"
    return f"{v:,.2f} €".replace(",", " ")

def fmt_jpy(v):
    if v is None or v == 0: return "—"
    return f"¥ {float(v):,.0f}"

def sync_stock_from_transaction(conn, ref_produit, type_op, quantite):
    """
    Synchronise le stock quand une transaction est enregistrée.
    - Vente :
      · Si PF en stock → décrémente stock PF
      · Si PF pas en stock → décrémente les MP/composants (besoin de production)
    - Achat/MP    → qte_stock += quantite
    - Utilisation → qte_utilisee += quantite, qte_stock -= quantite
    """
    if not ref_produit:
        return
    row = conn.execute("SELECT * FROM stock WHERE ref=?", (ref_produit,)).fetchone()

    if type_op == "Vente":
        if row:
            stock_actuel = row[5] if row else 0  # qte_stock index
            try:
                cols = [d[0] for d in conn.execute("PRAGMA table_info(stock)").fetchall()]
                idx_stk = cols.index("qte_stock")
                stock_actuel = row[idx_stk]
            except Exception:
                stock_actuel = 0

            if stock_actuel >= quantite:
                # PF disponible → décrémenter directement
                conn.execute("""UPDATE stock SET
                    qte_vendue = qte_vendue + ?,
                    qte_stock  = MAX(0, qte_stock - ?)
                    WHERE ref=?""", (quantite, quantite, ref_produit))
            else:
                # PF pas en stock → déduire les MP/composants (besoin de production)
                # D'abord on décrémente ce qui reste en PF
                if stock_actuel > 0:
                    conn.execute("""UPDATE stock SET
                        qte_vendue = qte_vendue + ?,
                        qte_stock  = 0
                        WHERE ref=?""", (stock_actuel, ref_produit))
                    a_produire = quantite - stock_actuel
                else:
                    a_produire = quantite

                # Trouver les composants dans product_components
                try:
                    prod = conn.execute(
                        "SELECT id FROM products WHERE ref=?", (ref_produit,)).fetchone()
                    if prod:
                        comps = conn.execute("""
                            SELECT ref_stock, quantite FROM product_components
                            WHERE product_id=? AND ref_stock IS NOT NULL AND ref_stock != ''
                        """, (prod[0],)).fetchall()
                        for ref_mp, qte_mp in comps:
                            needed = float(qte_mp) * float(a_produire)
                            conn.execute("""UPDATE stock SET
                                qte_utilisee = qte_utilisee + ?,
                                qte_stock    = MAX(0, qte_stock - ?)
                                WHERE ref=?""", (needed, needed, ref_mp))
                except Exception:
                    pass
        # Si pas de ligne stock pour ce ref, rien à faire
    elif type_op in ("Achat", "Achat perso"):
        if row:
            conn.execute("UPDATE stock SET qte_stock = qte_stock + ? WHERE ref=?",
                         (quantite, ref_produit))
    elif type_op == "Utilisation":
        if row:
            conn.execute("""UPDATE stock SET
                qte_utilisee = qte_utilisee + ?,
                qte_stock    = MAX(0, qte_stock - ?)
                WHERE ref=?""", (quantite, quantite, ref_produit))
    conn.commit()


def _safe_date(s):
    """Convertit une string en date sans crasher."""
    if not s:
        return date.today()
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except Exception:
        return date.today()

def fmt_devise(v, devise="EUR"):
    if v is None: return "—"
    sym = DEVISE_SYMBOLES.get(devise, devise)
    return f"{v:,.0f} {sym}" if devise == "JPY" else f"{v:,.2f} {sym}"

months_map = {1:"Jan",2:"Fév",3:"Mar",4:"Avr",5:"Mai",6:"Jun",
              7:"Jul",8:"Aoû",9:"Sep",10:"Oct",11:"Nov",12:"Déc"}
months_full = {1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
               7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"}

def load_transactions(year=None, month=None):
    conn = get_conn()
    q = "SELECT * FROM transactions WHERE 1=1"
    p = []
    if year:  q += " AND annee=?"; p.append(year)
    if month: q += " AND mois=?";  p.append(month)
    df = (_read_sql_impl(q + " ORDER BY date_op DESC", conn, params=p) if _USE_SUPABASE and _read_sql_impl else pd.read_sql(q + " ORDER BY date_op DESC", conn, params=p))
    conn.close(); return df

def load_commandes():
    conn = get_conn()
    df = (_read_sql_impl("SELECT * FROM commandes ORDER BY date_commande DESC", conn) if _USE_SUPABASE and _read_sql_impl else pd.read_sql("SELECT * FROM commandes ORDER BY date_commande DESC", conn))
    conn.close(); return df

def load_stock():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM stock ORDER BY type_produit, description", conn)
    conn.close(); return df

def load_contacts():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM contacts ORDER BY type_contact, nom", conn)
    conn.close(); return df

def compute_kpis(df):
    ventes = df[df["type_op"]=="Vente"]["total_ht"].sum()
    achats  = df[df["type_op"].isin(["Achat","Achat perso"])]["total_ht"].sum()
    tva_c   = df[df["type_tva"]=="Collectée"]["tva"].sum()
    tva_d   = df[df["type_tva"]=="Déductible"]["tva"].sum()
    return ventes, achats, ventes-achats, tva_c, tva_d, tva_c-tva_d

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    _LOGO_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAABZMAAAF5CAYAAADqGrQHAAAACXBIWXMAAA7DAAAOwwHHb6hkAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAIABJREFUeJzs3Xl4JGW1P/Dvqe5kMpN0dybMpKonAQIOcB1kk0VWEREUBllFFmV1Y5HFFa96r9t1v+4LotcFcEVlV0FEEJGfCAgId2QZIQ5JqqoTMunqZLZ01fn90RlvCEmmk3T3eav7fJ7HR4bpft8vM+nu6lPve15iZiilKivwvCsBXDDPpz+ZdpxVAKIKRlINaKS3tx1NTT0Jy9qJgR4Q7QRgJwDLADQDaCegmYFWAG0AmgAUABSZaAMBg2AeAJAD8ByInuAoeipctOipjo6OQOq/Syml6kXB8x5lYM95PLVYjKKdO1aseK7ioZSKMdd1l6SIdmKinZi5h4HtASwj5u1AtB2A7VC67kkBAAMtBCyeePoogPGJfx4BMALmIRA9D2CIgOcioJeI/pkg6m3t7PRr/J+nVKUk876/PTP3JIAeBnoALKfSd4RlALbj0neDDABr4n+ZieduATAGAASMRaXXyjCInkcUPU9E/QT0hkAvgN52x+kDUKztf55Sqtoo8P2DpEOohYs2bXois8MO66VzKCC/bt1Sam5+DqUL1flanXacX1cqk2oAvb0thSVLXo4wPBBEB0dEBxJzVxVnfAbAAwQ8AOa/pMbG/oKVKzdXcb7YyPv+ThaRI51DmYOiKGhznP+t1HgjntdDzNtVarxK2AD8PZvNbpDOESd53381Md853+cT86dT2ewHK5mpEQSe9wUwz6eAXy0ctrScunTp0rx0kJhJjPn+qjCK9mSiPYlobzDvASBbwwzrGfgbAY8z89+I6OG04zwMLZwpgwwPDGzflEjsHUXRnhbRXgzsBWBnAMkaRdgMYA2Axwl4LGJ+NFy06M+6MKX2Rj1vVci8eNuPrE9RIjFulW4awgrDIJXNrgcQCseKLcq7ri5NrgNEdHzKtm+RzqGAvO9/gJg/vaBBmH+XzmaPqlAkVadGXfelEXAKiFYDeDlKq42lbADRvcR8Z8R8ZyabfRgNuro+8LxvALhIOocyCPN96Wz2kEoNV3DddzPRFyo1XiUQ0VtTtv1d6RxxEnjezQBev4AhhjcS7WDb9lilMtW79evXZxKbN+cg+3k51UNpx9lPOoTpXNddspjoAAs4DESHgvkgTKwuNswGBh4gonsRRX9Mh+E96O7eKB1KNQxrzPd3D5kPA/OhRHQYA93SoaYRMfC/BPwJzH9KJJO/a12+3JMOVe8Cz3scwO7SOQwTABgB0TCY+4moj5n7CVgXAv9MEq1ps+2cdEgT1epulFKNIknMCy8iEb1mpL9/7/aurkcqkEnVkZFcbi8rik5BqYi8SjrPJEvAfDQDRxMRAs8bZuBuAu5ky7o909n5D+mAStWLkOh6CzCqmMzMJwHQYnKZ8r6/EwHHLnCYjpYoOhPAdyqRqREkNm06DkQmFZIB5hulI5hqvevuYBGtJuD1rURHAGgBAJjdpnEJAYeD+XAQIZ9MbiTP+wOIfgPL+nV6+fK10gFVfRkcHGxrKhaPJqLjJj5XbAAAEQx+pVgE7AFgDxBdEIYhB573MDHfBuC2VDZ7H3TFqKqNNIA0mHcAsPfWNsCMUm+XiBmB5w0DWENEf4+i6CGOovvbu7oeR4PvQtGVyXVCVyabIfD9M8D84woN94O045xXobFUjA0NDaWai8WzUFrtGte7yX8l4GchcF274/RKh6kmXZmsXqTCK5MBoOC6jzDRXpUcc4E2F5ubO3XbankC1/0yiC6rwFD/m3acPQCTawbmKHjeLxg4RTrHZBbRHm22/bh0DlNMtPF5kwWcath7XGUQPcLAdSC6Tm+0q/ma+G5wEoAzABwBYJFwpErzAPzSYr6uLZu9Fw2627HSdGVyRW0A0cMURX+MLOt3mY0b/4Senk3SoWpJi8l1QovJZgg8788AXlGh4bYkk8meJcuWuRUaT8VMob9/VyQS5zPwdgBLpfNU0BoAP2fLurYev0hpMVm9SBWKyYHnfRTARyo55kIx0ekZ2/6ZdA7TTRQBnsP/HWa0IGxZR2U6O39XibHqWl/f4iCZHMTCzrSotLVpx9lFOoS0/Lp1S9HUdBoRvQnAIQBIOlONPMDA96NFi36sPbNVGRKB570OzG8C0QkAlkgHqgUm6reYf8iJxHfTy5c/LZ0nzrSYXD0MbCTme4no9ojo+oxtPyudqdos6QBK1YvCwMAhqFwhGQCai2GoBakGNJLL7RV43q85kXiCgStQX4VkAFgF4CMURU8Hvn9vwffP933fpC/3ShkvCkPjtsZTqdWF2obmMDwPFSokAwBFUSVWONe9QlPT0TCrkAwGbpDOIGl9Lrdnwfe/Tc3NfUR0JYBD0TiFZADYn4BvJjZv7g887/uFXO4g6UDKPAXXXZb3/Q8EnvcMgFtBdAYapJAMAMTcxcAVCMMnC573+8D3z8DatfW2ElvFHAGLQXQUA/9NzM8EnvdQ3vc/WOjv31U6W7VoMVmpSrGsyys+JvNFWmRrHCOe1xP4/rVWFP0VwDGo/y9UBOZDmPm7i5n7A8/7+qjvv0w6lFJxMNFT37RVD6vR29siHcJwhEqcrfBCqwuu+28VHrPusIE3OyzLMu6mUA1Yedc9Je95f0hE0aPM/DY0UGFsBq0AzuUoui/wvL8WfP98fS9V63O5PfOe9z0mem7icPcdpDMJIwaOAPOPg7a2dYHv/9fGvr4u6VBKzeDlxPxJTiSeDDzvwbzrvn1wcLBNOlQlaTFZqQoYcd0dGTixCkN3tETRWVUYVxlk/fr1mcD3v2gBT4D5zWjM9+YMgIsj5r8FnvebfC73GulAShmP6CbpCFO0BS0tR0qHMFnB91cD2K3CwxITXVzhMetNEsBq6RBT+KnOzj9Lh6iZNWuaC553XuB5a4joFwS8UjqSofZh5u8GLS3PFVz302ODg450IFVbhYGBQwLPuzURRY8QcB62HjypJusE84fGk8lnA8/7WeB5B0gHUmoW+xLRVYvCsD/wvCvrZfFUIxYslKo4IroEpS8q1Rj7XdDXat3K53JHJTZvfgzM70L9HZ4xHwTgdRRFdwSe99e8656C+l+hrdS8WMzGrWo0cfWnSTiKLq3S0OeO9Pa2V2ns2Mvncq8CsEw6x2RUuhlU/4dKrV27KPD9S4KOjrUMfA+Vv5lSr5Yx0QeKYfhM4HlfHR4Y2F46kKqufC73msDz7mHLuhelm196/bttTQDeCOD+wPdvL7juYdKBlJpFGsAFEfNjge/fm/e8U1GlGlItaIFKqQUaGhpKEdFbqjjFrhMrmVQdcV13ScHzPkNRdBsA/YIwvX2I6Bd5z/vbxIetXlQrNUmb49wLYFA6x2REdCJifGFcTaOetwpE1dp10ZZYtOj8Ko0dexRFxt3kYANvBlWYFXje2UFb2xNg/ir0WmdeCFgM4JKkZa0t+P63dFt//cm77n6B695BUXQHAC2Gzhfz0Ux0T97z7taisjIe8yEEXBd43pMF338r1qxplo40V1pMVmqBmsPwPDBXdzVQadWqqhOFXO6gVqLHJg7X0/fhbSDgZRMftvcFvn+gdB6lDBIycKt0iCm2G/W8Q6RDmIiJLkUVb4pNjJ+o1vgxRgQcLx1iikJ606a7pENUS+B5q/Oe9yiAqwH0CMepF83M/I7xZPKpwPc/MTQ0lJIOpBYmn8u9pOB5Pyeiv1TxRmPDIeBwJroncN0b9TwBFQM7M/N3go6OpwPPuyhOh0tqEUOphbGqcJDOizBwxMjAwD7VnkdVX+C6b+YougvAztJZYuhAMN8XuO6PdLunUiUWkXGrGyNtdfEi+XXrlnKpJ3417VhwXdOKpuIKudyBDHRL55jiV+jp2SQdotLyudxLAs+7BcCtBNRFT0gDLQHzh5uLxbV5170A+n0+dlzXXRL4/icoih5n4A3QnXfVQXQCEz0WeN43C/3920nHUWobdgDwjaCt7enA885GDN4X9MNHqQUo+P7rUaPeb5Zl6erkeKPA8z4KomugvZEXgkB0ZsKynix43meGh4fT0oGUkpTauPG3AArSOSYjIu11PoXV3Pw2AK3Vniciuqzac8RNZGKLCwNvAi1IX9/iwPM+TlH0OIDjpOM0iE4iujLwvPvzrruvdBhVnhHXPbmVaA2YPww9WK8WkgAu5ETiiYLvnw+9NlHm2x7A1YHn3VfI5Q6WDjMbLSYrtRDMl9dwttOH+/tNW1mjytHXt7jgeT8D8BHoRUxFELCYgSuSW7b8veB550D/XFWj6unZxMAd0jEmY6A777ovl85hkAQDF9RiIgIOz7vufrWYKy4IOEE6wxSbw6am30iHqJSC6x4aJBKPAvgPaHFMwn5EdH/geV/TG+zmGhscdPK+f71F9EsAO0rnaUDLmPm7gefdM+r7umtCxcGBHEX3Bp53TcF1jTpAeCstJis1T2O+vwcDh9dwyqYmy6p6Sw1VYX19iwvJ5K0MnCodpU6tYOAHgef9YdR1XyodRikJZOBBXmRZxq0GlZL3vJMA7FSr+YjonbWay3Rjvr8HgF2lc0xxZ0dHRyAdYsFKN8o/w0R3g2gX6TgNLgHgncktWx7L+/6R0mHUC+U979QwDB8jbQFlgkMj5r8GnvdR6BkDynwE4Cwmenyi9YVRtJis1DyFzO9BjVdDMtEFg4ODbbWcUy3A2rWLgmTyegZeLR2lARwWEf017/sfhF4cqgYTbd58C4At0jlegPlk6QimIKDWrSdOHxscdGo8p5FCA38O2cCbP3MVeN7+QTL5t4mDhPUz1xw7EPMdged91XXdJdJhGl3Q19eR9/3rCbgOgJErCxtUE4CPBK57TzA4uFI6jFJlsAFcnff9G0xapazFZKXmYdT3OwGcJjD10kVheI7AvGrumoK2tusAvE46SANpIeZPBp53bz6X0wMOVcNo7+kZAfM90jmmeKmeog5MHJ57aI2nXRSG4TtqPKeRDFwJGCWTyVukQywAFTzvPQDuBaBFGDMRgEtaif66PpfbUzpMoyq47qFIJh8x8D1IbUV0MMLwkYleykoZj5hPnFilfKx0FkCLyUrNS8R8MaT6wjFfBn3tmo4Cz/shgOOlgzSoAymKHiz4vv75q8ZBdJN0hKkibXUBy7JqebbCZBeht7eh+9eOeF4PE+0lneMFiP5f6/LlnnSM+Rj1vOWB5/2Kgf8G0CydR23TblYU/VkLZTVnBa77YSa6C6WDtJTZWid6KX9fV/OrmLAB3Jr3vM+idMCkGC1IKTVXa9cuAiC34odol4Lvv15sfrVNed//dwBvlM7R4JYy840Fz/sM9HA+1QCaisUbALB0jskafUXWxC4mqc+CzqClpaE/hxLAKdIZpjKxv3k5RgYG9omABwEcI51FlY+AxVooq53h4eF04Hk3g+gTEC7yqDk7dwnRnwsDA7tJB1GqDETA+/Oed+fEtaYILSYrNUeFVOrNKN0REhMxv0tyfjWzvO+/mpg/Lp1DAQCIgfcXBgYOlg6iVLUt7u7uR6nYY5L9hgcGGnZlVsR8IaR2MZVIrYo2AhOZdzMjDG+WjjBXec871bKsPwLYQTqLmrdz24D7Gvn9uNqCwcGVyS1b/h+A1dJZ1PwQsAdb1gOB5+nfoYoFAl4ZMT+Yd939JObXYrJSc8V8qXQEAg4PPO8A6RzqhTYMDWWJ+UfQw2iMQcDnUitW/Ek6h1K1wESmrXqkZCJxonQIEWvWNAO4QDjFPqOu+0rhDCLGcjkbzAdJ55iMgcdSXV1PSeeYAwp8/xME/AxAq3QYtTBMtFeTZd030cddVVA+lzsKYfgXAKuks6gFSwG4Me95F0oHUapM2xPR3YHn1XznkBaTlZqDfC73GgbMOMyCSLyorV4gURwf/wUARzqImsB8R8pxPiQdQ6laSRi4hb5RW10ES5eeBgM+D0Kiy6QzSCiG4Ukw7HsOAca9PmfRFHjeD8D8YWirqLrBQLdlWX8s+P4J0lnqReC6b6Yo+hWApdJZVMUkCfhm4LpfgWGfI0rNoBXAzQXff2stJ9UXh1JzQFFkzpZR5jfqdjVzBJ53IYi0nYI5/knAmQBC6SBK1Uqb46wB8KR0jskYeGXBdZdJ56g5okukIwAAASfkc7mdpXPUGhl4+CMbeLNnOr7vtwaedyOAs6WzqKpoZeZfFnz/LdJB4i7w/ctAdDWAJuksqgqILg0870fQv18VD0lm/nbB895Xqwm1mKxUmYLBwV1g1sEjTU2WdbF0CAWMDQ46E4dtKAMwsJGZT0lls0PSWZSqNQZuks4wRQJEDXVobGFg4BAA+0vnmJBAFF0kHaKWRnp728H8KukcU/wzk80+LB1iWwr9/dstZr4LwLHSWVRVJZj5O4HrmrNIJl4o8LwvgPnL0HpKvTs98Lwb9QBLFRPEwOcCz/uPWkymb35KlSsM3wXDXjNM9I7BwcE26RyNLgzDL4G5XTqHKrGACzPZ7EPSOZSSYFmWcasfGTBulWhVWZZRrSUIeNvw8HBaOketWIsWvR5As3SOFyitSmbpGLMpuO4yWNadMOdGiKouAtGXAs/7mHSQmKHA874K4N3SQVTNHNtKdFsjfY6q2Pt43nWr3urRqMKYUqbKr1u3FCZu92NuXxRF50nHaGT5XO4oAKdL51ATiL6UcpyrpWMoJSXV2Xk/AFc6xxRHDw0NpaRD1MLGvr4uBkw7dDCd3LLlLOkQtcIGtriIzDsc8wXy69YtZaLbmGgv6Syq5v4z73mflw4RExR43lcAvFM6iKq5w5Jbtvw+6OvrkA6iVDmI6L+q3fJCi8lKlaO5+e0w9SRr5ncBSEjHaFQURZ+UzqBKCLgrbdvvl86hlLCIiG6WDjHFoqZi8XXSIWqhmEi8Eyb2V2S+DA1w3e+67hJiPlo6xxTPtzvOvdIhZlJw3WVWc/PdAPYVjqKEEPDevOd9TjqH4SjwvK8DMKIfvhKxL5LJ34z09upuVBULDHy2mv3x6/6iUqkKSBJgcm/inQque7x0iEYUuO5rodtBTbGOgNMAFKWDKCWNo8i4VZDEbNxq0Yrr61vMRG+TjjEtol0CzzPp3IeqaANeC/Nu/t8CQz+bBgcH25joVwzsKZ1FySLgfXnP+2/pHKYquO5/AWio/vNqWgdYLS13aEFZxQQx81UjrntyNQbXYrJS2xD4/hsAbC+dYzZMpH27BDDRB6UzKADAJgBvaHOcQekgSpkgnc3eCaIR6RwvQHQc1q5dJB2jmvKJxJsBbCedY0al1cl1jYmMu2lBpra4WLOmeVEY/gLAAdJRlBkIeE/guh+WzmGawPMu1mt+Ncl+VkvLb3zfN+3GpVLTSVhE1xZyuYMqPbAWk5XaFuY4nHR8aOD7r5AO0UgKudxBBLxSOocCiOjitOM8IJ1DKYOMI4p+Ix1iilTQ1vZq6RDVZBGZ3UeT6Kj1uVw9r0BtAnCcdIgpNoxG0R3SIaZhBR0d16K0klup/0P0ibzrvl06hikC130zgK9J51DGOXAx808AJKWDKFWGJRxFNwwPDFR0gaQWk5WaRSGXOxhAPIq08Sh61w2OIl2hYIavp2z7e9IhlDINW9ZN0hmmIgNXjVZK3vePjEOrgCSzyW27FiTvukcAWCqdYzIGbstmsxukc0yV97xPA3ijdA5lJiL6Zt51T5HOIW3UdV8Jou8CIOksykivDzzvO9CfDxUPdtKybnJdd0mlBtRislKziaI4FWjfsN51d5AO0QjGcjkbQEMcJmU05vvSw8PvkY6hlIm2WNavUGoBYwxmPgF1emAsxaSFRMR8VqG/39xWHAtg4s0KYjauxUXgumcRoIfVqtkkiOiHjbzrccTzeiKinwNols6ijHZu4HnaGkbFxT6tlnVVpQbTYrJSM1jvujswYNwXk1kkLSI9YbgGoig6G7qtSZqbbGo6FatWbZEOopSJli9fPgrg99I5pugsuO7B0iEqLe/7OwE4VjpHOQhYHCWTZh4SuDAWgBOkQ0xRpCj6tXSIyQq53EEg+o50DhULLWC+cbi/v1s6SK0NDQ2lCLgZQKd0FhULH8t7nu70UPHA/OaC77+1EkNpMVmpGUwUZmNVMCTg7evXr89I56h3EXCWdIYGtxnAiUuWLRuQDqKUyZjZuFYXbFlxuklbFoqiyxCvFdfvRKm/cN0oDAwcBCArnWOKP6S6up6XDrHV2OCgw1F0PYC6PghTVZSTTCRuQF/fYukgNURNYXg1AXtIB1GxQQR8b6S/f2/pIEqVg5m/Nub7C36Pi1WhTKla8X2/dTFwvnSOeUgnNm06D8CXpYPUq7zr7ktEcb7ALAJYC+BpMD9LwGhEFIB5hCyrwMzjRJTkKEpZRBkGdgbRzsS8igEjVqcQ0cUp2/6LdA6lTJdMJG4Ko+ibMKnQyXwSgPcAYOkolTA0NJRqJjpXOsdcEHNX4PunpG37p9JZKiWyrJMMbFppUouLRBSGPwbgSAcRsgXAswCeBHMvARsiohECxggYi4BRAJi47mlloNViToNoKTO/BMCuACp6cFGM7Bckk1elgbOlg9RC4LqXm9gyp4aeI+BpEP0DzMMRc4GADQyMgWgEAFvAkghYAiBtMacZaAXQA6LdAOyMxmwN0molEjcGfX0vT3d3D0uHUWobWorMP0Zf3wHo7t4430G0mKzUNCYKyR3SOeaF6DIAX0epaKgqjeh06QhzFAF4CMCtFvPdY5b1kG3bY/MZaLi/vzuRSBxkER010ftUYvvft1K2/V2BeZWKndbOTj/w/T+D+RDpLJP0jAwM7N2+YsXD0kEqoTkMzwMQvx1BpR7PdVNMJuBE6QxTcDGKjNkZEPj+RwEcIZ2jRsYA3MtEdxPzo2xZT2U6O/+JBV4X+77fuigMd7USid0QRQeB6EgAu1cksfnOKvj+H+r9+ivw/QNB9FnpHDUSAniEgbsB3M+W9dTGMHy6AgeGJoPBwZ0QhrsC2JeAIxg4CI2xI2JHJJPfR+nzqC5umKv6RcDL8snkxzPA++Y9Rt51zflBZz7bsqzbpWPEUdvzz49o79CKocDz/g5gN+kg88XAqRnH+YV0jnoUeN5DAF4unaMMgyD6NgPfzdj2s1UY3yq47iERcA4RnQagrQpzvBDzfen1648w/b1ucHCwbXEUVeykXAlRFL0WRNdI59jKIrKlMyxEcePGLe09PSMScxc8770MfF5i7ll8Iu04/ykdogLifb1AdGDatu+XjrFQI7ncXlYUPSKdY4oH0o5zgHQIAMjnckdRFN2G+m1vGBFwT8T8OyuRuCvV2fkAgPFaTDw2OOiEUXQER9GRRHQcgFh/Vm3DBovoFW22/bh0kGrIr1u3lJqbHwawo3SWKnoKRL8m4K5w48Z7anZd0te3ON/cfKgVhq8GcAwT7VWTeYUQ83tS2ewXpXNMJ/C8x2HITTBm/jCInqrFXBawZGLXScpibmeiVgDLUbp+2w2llfaNKARwUNpxHpjPk40qJhPRCSnbvlk6h2psBd8/3sQ+k3PCfF86mzVpJVpdmLjQHILZX8gKDHxySyLxjYkDuKpueHg4ndi8+QwiejuqV2h3k8nkvkuWLXOrNL6axLT3wbTjGLiDPR7yudxLKIrWSueYjIHHM44T53ZBAICC7x/HzLdI55g35p+ks9kzpWMsVOB5HwXwEekckzHRhzK2/SnpHCO9ve2JlpbHTGlTVWFrGLgmDMMfdXR19UmHAdBU8P1jIuBcYl6N+tzqv2aMef8KrF41TuD714L5zdI5quB5AD8F0bWm3Dwc6e/f27Ksc0F0JkoFvXqzBcBhaccxriWfScVksqyDU52d/086BwAa8bwdLebdiGgvZn4NiA4D0CIdrBYYeCwzPLzffBZrmVwQUUoG8+XSERaM6ODA9w+UjlFvrKamw2Hy+ybRb4tRtHvGcT5bq0IyAHR0dASZbPaqtOPsy8z7AbgGlW2zsoUs6w1aSFZq7jKdnf9gwKiVZAS8rDAwEM/VvJNw6eC9+CJ6w3B/f+yLjAycLJ1hqgSzEf2SrcWLv1ZnheQxAF9n5v3SjrN7xnE+a0ghGQDGU7Z9c8a2Tybmrom2c09Kh6qwVa1En5EOUWkjrntynRWSGcCvifmk9PDwirTjvNOUQjIAtHd1PZLOZi9PO04XEZ0I4Deor7YQzQCubbCDK+OM2x2nN53N3p5ynM+ls9mj08ViB5hfB+CLYH5aOmA1EbBHsHTp++fzXHOLIkoJGPP9PRh4lXSOimB+l3SEesNm9xv8RNq2j+lYseI5yRCZbPahtOOcw0S7AvgWgM0LHZOZL0t1dt638HRKNSYiMqKw9QKWdYJ0hIUY9bxVEz1T46ypybIulA6xEMHg4EoCzFrlzvx0m+OskY5R8P0T6qhANgrmryaTyV3SjnNJJpt9SDrQbFLZ7FDatr+adpxVRHQ8gAelM1XQO/O53FHSISpl1POWW0TflM5RIQzgVgCvSDvO6lQ2e6PhreHGU7Z9U9pxjk2UWl9ci9K2+3qwa9DU9EnpEGqeurs3prPZ29OO8550NrsriA5C6XttzRZr1RTRvw8PDMz5kFktJis1Scj8bgD1sp36lHwut7N0iLpS+iAxDgHvn+g/Gkln2Spj28+mHefCZDK5M4i+hHkWlZn5u5ls9lsVjqdUQ+EoMq6YzMBJ0hkWgkurDmN/vcBEF7iuG9tegRSGxq1KJqLrpTPk161bysxXSedYMKIRAB9HsbhjOpu9LIY7lKKUbd+SdpwDJorKxqwOXQCiKLpqcHCw+mdl1EBUOrQ87r2uIwDXJYj2SjvO6+fb/1RSq20/lnacsy3mPVD5HY4ymC8ruO5h0jHUwqVt+89px7kw2rRpewLeD2BAOlOFLUla1ufm+iQtJis1YdT3OwGcLp2jghIURRdLh6gzu0oHmIqIrko5jmmHa/3LkmXLBtK2/W62rN0J+Pkcn/7XTBheUpVgSjWQiVV81TiIcyFeEdcWCxOFujdJ56iQjiVAbP9bTLwpwQbsBLAWLfo04l0gYwa+R1G0S9pnnLOeAAAgAElEQVRxPpLu7h6WDrRAPFFUPpCJTkf8CxE7LQrDT0uHWKjAdV8H4I3SORboIWZ+RdpxTmu17cekwyxUWzb797TjnGMBezNwj3SeBbKY6Hva7qJ+tPf0jKQc5/Pp4eGdAJwD4B/SmSro9FHXfeVcnqDFZKUmRMwXof4arb9t/fr1GekQ9WBscNABYNqf5T9SGzfGosd3prPzHynHeSMzvxbA38t4il8MwxPQ3b2x2tmUagjmHRRHyUTieOkQ89Lc/HYArdIxKoViusp64nP5AOkcU/hp2xY9dCnwvAOY+W2SGRboKSY6KuM4b0lls0PSYSotY9s/21hqBfYxlA7qiquLAs8z7fVXvr6+xSD6unSMBciD6PK047wik83WUxsVAECb4/xvxnEO51Kx35fOswArg2TyCukQqsJWrdqSdpxr0sPDq5j5HQB6pSNVQkQ0p9XJWkxWCgDWrl0E4B3SMaogldy06S3SIepBVCzuIp1hKgb+HT09m6RzzEUmm/1t2nH2QqmlzEx9p8Yt5jcadKiOUrHHlnWTdIYXYTZuVWkZElR/1wu753O52PV/DkstLkz7LnMDZFtOJYn52zDvz2WbGNg40bbrZRnbvlM6TzXZtj2WdpyPRpZ1AOLb+sIC8FXE8GcNAIKmpg8CeIl0jnm6LplMvjRt219B/fQYnlbGcX7OW7a8FKV+tXE9pO+KfC4X1581NZtVq7ZkstlvpzdteilKNwgXfFaQsFcEnre63AfH8s1fqUorpFJvAuBI56gGJroUQFI6R+xZlmktLv6ZcRzxvozzNJ7OZr+UTCZ3A/N0Ba53t2Wzcd/appRRMrb9BwBmrfIjOjzo6+uQjjEXec87CcBO0jkqjaLoMukMc2bgzQhmvkFy/rznvY1LB1nFzVNsWQdNtO0alw5TK+2dnY+mHedQlIoQxpx7MQevKPj++dIh5mrE83rA/F7pHPOwaWI18mkx7B8+b5kddlifdpwLiegEAHFsedNCUfQN6RCqinp6NqUd56MUhnsScJd0nAX6OMrcrabFZKUAIIoulY5QRTvmPc+4A2rihk0rHhD9EDFfjbBk2bKBdDZ7Iko9p7ZeHF6Tdpw4bztUylQhgF9Jh5iiCcnkcdIh5oKA+BVdy7O6MDCwm3SIco309raD6HDpHFPkM+vX3y01+dDQUIqAj0jNP2/MP9mSTO7X3tn5qHQUIcW043yUiE4CsF46zFwx86fj1lLPIvovxK+14RMW0f4Tq5EbUsq2b2Gi/QDEsa3Hawu+H6vrHTV3qa6up1KO8xoAFzMQ11aNLx9x3bJu1msxWTW8vO8fGdNVHGUjII53383CbNSFssV8h3SGSkk7zjUJy1rFwOfTxeIF0nmUqlc0/U4AUVwqoMTCyMDAPgAOlc5RJcSWFZtDexMtLScAaJLO8QLMv8KqVWI9cJvD8P2I16F7m5j5gnQ2e+ayZcsK0mGkpWz75gh4OYAHpLPM0bLkpk3vlw5Rrrzr7gfmM6VzzAnRjzYnEvu32fbj0lGkZWz72fTo6KEAYrfSN2L+NICEdA5VdVHacb7JYXgwgGekw8yHRfTBsh5X7SBKmY6YY3GA2QLtX8jlDpYOEXNt0gEm4S3NzQ9Lh6ik1s5OP+M479cD95SqnlHgdgBj0jlegPm1vu/H4jA7y7Lq/Xrh3LisMGQTW1wQ3Sg194ahoRUTZxHEA9EIMR+VyWavko5iknbH6U0Xi4cDuFU6y1ww0eUbhoZWSOcoh0X0ecTrwNH/TNv2m5cvXz7TOSONZ+XKzWnHeSdKrRxj00eZgJcVPO9s6RyqNtq7uh5Bsbg/gNuks8zDviOe96ptPUiLyaqhBYODuwA4VjpHTURRfL5kGIjMKiZ7HR0dgXQIpVS8ZLPZDUxk1K4GAhYviqLXSufYllHf70TpVPl6FotDe13XXQKio6RzTLF5PJkU+8JYLBY/AGCJ1Pxz5EXF4hGpbPZe6SBG6u7emHacEwH8QDrKHCwJw/Cj0iG2Je/7r2bgVdI5yhQy84Vpx/mEdBBTpW37a2A+CzHqsx4RfcJ13bi8V6sFSnd3D6cdZzWVVqXHilXGznYtJqvGFoaXo0FeBwycqCfJzh+bVUyO4+ETSikDWMxiqydnYlmWcatMp4qYL0T8emzO2cShvUZvw11CdCzMK5zeIdWqYWJF6Nsk5p4z5qeZ6OD2rq5HpKMYLkw7zlsAXCkdpFzMfF4wOLhSOsesmP9TOkKZNjPzaZls9lvSQUyXzmZ/RESnAtgknaUcxNzVCrxDOoeqqSiVzX6QgNi0A5pw7KjrvnS2BzREEU2p6Yz09rYDaKStJgkKw0ukQ8SYSduwY3HBpJQyDxeLtwAoSueY4jisWdMsHWJGpWyN0s99x4LrHi8dYjZkYIsLEmxxURwfvwIxuNFBwN8syzo0Y9vPSmeJiSjtOBcx8HnpIGVKcmmFvJFGPO9VBJh2aOd0NjDRsZls9pfSQeIiZds3MdFxsTnwjOi96O01/j1bVVbKcT7PpYUJkXSWMlG0jWtfLSarhpVoaXk7zFptWn1E508U0dUcsVlv/CnpAEqpeEp3dw8T8EfpHC/A3J5fuvRV0jFmEixdehoARzpHrUREl0lnmEUTiI6RDjFFZFnWryQmHhscdJgoDquSn00kk69rs+2cdJC4yTjOFcz8P9I5ykFEZ6133R2kc0wnAcRhVXKRiE7L2PbvpYPETca277SITod5N8unsyLf0nKedAhVe5ls9lvMfAHMqivMzLLOnq0tixaTVaNKMhCbU8srKJVoaYnDlw7jEGDSwRdZ6Pu3UmqeJA8KmwkRGbfa9F9KrR8aBgGHj/T37y2dYzp51z0CwFLpHFPc17p8uScxcRiGFxGwWGLuORikKDpmybJlrnSQmOJMNnsBAXFYqdqcIHqfdIipRgYG9mHgCOkc28BE9I6Ubcfq8EWTpGz7ZjCfjxgcykfAB4zekaWqJpPNfgdE75LOURbm9lbglJl+W4sRqiHlff8UAEbeOa+2iRVHTdI54oaADdIZJkmN+f7u0iGUUvEURtGNMO/L1kkw8Lq0MDBwCID9pHPUmpVIGLk6mYhOlM4wFTHfIDJxaZu06b03C8x8TGrFiielg8RcmCoWz4Jpu0qmwcBbRj1vuXSOySzLulw6w7YQ8IGUbX9POkfcpbPZa5now9I5yrDDxK4n1YDStv1VEH1ZOkdZZtn9ZNxFu1K1QMzGX1RUCzF3Bb7/BukcccNmFZMRRtEJ0hmUUvG0NJtdB+Bh6RxT2IVc7kDpEC9iWUYWVWvgjLHBQdNaexABr5cOMVWUSIis9C8sXnwmgE6JucsUsmWdkslmH5IOUhe6uzdGmzYdD+AJ6SizIWBxSPQW6RxbbRgaygI4XTrHrJi/mnKcz0nHqBcZ2/4U4nB4JdE7pSMoOWnbfg8D10vnKMNh+VzuJdP9hhaTVcMp5HIHATDvC2stMb9HOkIMjUkHeIHShbquMFdKzZdxrS6iKDKq1cXGvr4uBoxbCVsji8IwNGrVa+B5+zPQLZ1jMmJ+NNPZ+YzI5Mym3+j4WKaz8w7pEPWkvadnJEH0RtMPGqNST9CEdA4AKBaLFwAwuZ3A/els9r3SIepNenj4cgAPSufYhgMCz9tfOoQSE21gPgvAX6SDbBPzqdP9ay0mq4bDUdSwq5In2bfguodJh4gZXzrAFD2B718oHUIpFU8JE/smz9KXTUIxmbwEjX3T7iKTTpwnZuN25Ej1Hy/kcgcxsKfE3OUg4O6043xKOkc9arXtx2JwI2HHguuasIsgAcDcg86IRpjoDADj0lHqzqpVW9iyTgeQl46yDY14hpOakM1mNxSj6A0A1ktnmY0VRdPu7tBismooG/v6ulDqy9jwIsuKR+N3UzD/QzrCizB/fGRgYB/pGEqp+Gm17ccAPCWdY4qd1udyZhTI+voWM/BW6RjCOoOWljdKh9iKDeyXHIWhSDE5CsPzJeYtk28lEmcACKWD1KtMNvsdMP9EOsdsGLhIOkPgea8DsL10jhkwRdH5Gdt+VjpIvcp0dv6DAdMPnj+t0N+/nXQIJadjxYrnCDC6LsNEe4163ovOa9JismooW5JJPXxuAjGfEAwOrpTOERuWZV4xGchYlvXb6d7clVJqWxi4WTrDVAlDWl3kE4mzAOgXPMCI3VwT1yurpHNM0dve1fVorScdHBxsIyJTe8BGbFlvbl2+3JMOUu+2NDW9A8xPS+eYEdGRE4t4xLBBvZun8Y1UNitzeGcDyTjOzwF8SzrHLFqiRMKYm7ZKRspxrgbwM+kcswmZX3RDX4vJqmG4rruEAJMvKmrNQhheKh0iLiwTVyaXLIuA3+qNAaXUXFnMN0lnmIqYjSgmW0S69bRkHxPaYlEYGrcqGUQ3AOBaT9sSRacBaKv1vOVg5u9lOjt/J52jESxbtqzAlnWBdI5ZWMVk8gypycdyOZuYj5OafxvWbST6gHSIRrE5kXgfE/VL55gJEb1JOoOSR2F4MYAB6RwzIeDYqf9Oi8mqYbQSnQ+gQzqHYd6iW2vK0+Y4gzC379YKhOF9o553uHQQpVR8pLLZ+wAYtYKQifaa6dToWsn7/pEm96OtOSLx/qwMGNcv2Yoimb7jzGeKzLttwwmiD0qHaCQZ2/49gJ9K55gJCxbJwig6FYbuRiXmy23bNutg7zq2fPnyUQDmHj7PfHA+l9tZOoaSlerqeh5E75POMSOiA0d9v3Pyv9JismoUBG1wP50lUSLR6D0h58LkU4GXR8Dv8p53hXQQpVRsRER0i3SIqawoEl2FSuYfblVTDJyY9/2dpOaf+PJykNT8M3i+rXQzpqZGPW85A6+s9bzlYOZ/n7jxrmoomUy+B0BBOse0mPeWasXGwBsk5i3DbdreovYytv0zMJu6a4IQhmKr+JU50rb9EzDX/NqiTFYURUe/4F9IJVGqlgq+fxyAf5POYSSiS7BmTbN0jJj4g3SAbUgS8JnA866ZeudQKaWmw8wyqytnwURirS4mVkWvlprfUAkwix2mxcDrASSk5p8OAzcBKNZ63pD5FADJWs9bhgcz2ez/SIdoREuWLRsg4GPSOWYSAafUes6xwUGHgENrPW8ZNlMUGdGHviElkxcB2CwdYzpEdLJ0BmUEJsDcFjiW9doX/FIqh1I1xawf3DMg5q5g6dJTpXPEgQXcI52hTGdFzM8UPO8zQ0NDKekwSilzpUdH7wQQSOd4AeaDNgwNZSWmpjC8BHp9/CJE9NbBwUGRPr3MbF6LCyKRmzBEZOpqy4sBRNIhGlXKcb4C4EnpHDN4UZ/NagvD8BQYdgMKAIj5S6kVK0z9e6p76eXLn2bg69I5ZrDPhqGhFdIhlLxUNvtHBq6XzjEt5he01NSLZVX3Rn3/ZQwcIZ3DaETvlo4QB22bNt0PYJN0jjK1MnBFc7H4ZN51366rz5VS01q5cjOA26RjTGGNj48fX+tJh4aGUiA6t9bzxgJz+6IwPKfW07quuwTAkbWedxtGU+PjNd8uPTw8nIaZLS5uTzvOX6RDNLgiAZ+WDjGD/ccGB52azkhU88+PMmwgoi9Kh2h0Scv6PAMbpXNMg8bHx3VXlAIAWFH0QZh5g3b7EdfdcesvtJis6l7I/G6Ueiarmb1cD28rQ0/PJjDfKx1jjrJEdFV+u+2eKXje+ya+jCql1P8RWmU5GxJoddEchucByNR63tgo9ZKu6XeHxcDrACyp5ZzbQsBt6O6ueTHC2rz5NTDwQDFi/qR0BgWkHOfHAJ6VzjENKwrD19Vstr6+xcx8WM3mKxfRVdpTXF5rZ6dPwHelc0yHtMWWmjCxg+HX0jmmYwGHTfpnperXqO93EqAN7csQAbo6uQxE9EPpDPNBzF0MfC65Zctzec/73HB/f7d0JqWUGcLm5l8D2CKdY4pX59etW1rD+UiyL3AsEO0SeF7tikIALCLjWlxI9RlPTOlVaIh7U9nsH6VDKADAODN/TjrEdLh0U6gmgkTicAIW12q+Mm1uGh//gnQIVVKMos/BvGsegOhIGHjDUMlgoi9LZ5gOWda/+tFrMVnVtaj0xbBFOkdMvL7gunpI4TZsIPoFgFHpHAuQJuB9yUTin4Hr3pH3vFNh5mE+SqkaWbp0aR7AXdI5pmiipqaa9dos+P5qALvVar7YIrqshrMlINBvdRvGeXxcZLUQMx8lMe+sdFWyUTJjY99non7pHNOo5e7Hmt7wKgcRXb24u9vEv5eG1LFixXPMfK10jmm0BZ63j3QIZYaMbd9JzI9K55iKmffd+s9aTFb1a+3aRQDeIR0jRoiJLpEOYTrbtscA3CCdowIsEL2GgOsKnvds4HkfG/G8HulQSikZUqstZ1PLVhccRbUsksYX89Fjvr9HLaYa8bxXAlhWi7nKxnx3Zocd1td62mBwcCWAnWo972wYeDydzd4unUNNsnLlZjB/TTrGNJx8LveSWkzERK+uxTxzwCgWdVWyYSzmzwNg6RxT0aQWAkrBsr4qHWEae2BiBb0Wk1XdKrS1nQGgtgc+lK/mX0TKdE7Q19chHcJ0EfB96QyVxEA3gP+0gGcCz/tj3vMuLLiuWV/glVJVlUwkboBhh30wcMzEAWxVNep5qya2l6oyRMDFtZjHYjauxYVUf3EKw0Mk5p2NBVwNA4sxjS5pWT8AMC6dYyorig7d9qMWZnh4OE3A7tWeZ06I7kt1dT0lHUO90ERPWuPOwYmIqv46UfGRGh//CYCCdI4pFo3kcqsALSarOsa13YpZPuanwXypdIwZtHJT0wXSIUzX7jh3MXCPdI4qIACHEvBNJhoIPO/WwPdPn1jlr5SqY62dnT6Av0jnmGJJm2VVfWv/xPWCHtRbpoj57EJ//3ZVn4jo+KrPMTdcDMObRSYGDpSYdxZhIpn8sXQI9WKtnZ0+E/1KOsdUEfDKas+R2Lz5QBhW3+AoMrGdgir5H+kAUxHzodDrEbVVd/dGMN8iHWOqRBTtA5jWJ5N56Yahoax0jGpiZm5dvtyTzlHv8r7/amLeWzrHtIi+nHacnwWe9ykA20vHmYqYL8aaNf+NVavMO5jAIBbzh5iong+daQKwGsyrg1RqhHz/OgK+1mbbj0sHU0pVBwM3kmFFK2Y+CcBN1Ro/6OvrQDL55mqNv0C3oNT/06gDeQhYHCWTbwPwmWrNsT6X2zNhWFsHAA90dHX1SUxMwMGGLQG+Y8myZQPSIdT0LOB7DJwonWMya1KfzWohooOrPcccbbGi6BfSIdT00sXiz4Ompq+AuV06yyTL8r7fk7HtZ6WDKDOQZV3HzGdK55gsmtgBYlQxmYEfFItF6RjVtgnmnTBbd4j5cukMM1i/kejqNDDOwDeoil/EFmBF0NFxehq4RjqIyVLZ7L2B5/0a5h0OVHnM7Qy8nYG3B573EDN/OxOG16K7e6N0NKVU5VAicT3C0KzPJaITUCqmVmXbNieTbyOg6q005iNB9KEwikZBdIZ0lmm8E8AXUKW/l0QU1axfdrmYSOS8hMHBwbZF5m3d19WWBkvZ9m8CzxsAsEI6y1ZM9FJU8b18wiuqOPacEXBzqqvreekcagbd3RvJ93/Ghp2xZAF7AtBisgIApAqF24K2tjyAjHSWrYh5F8CwbSBKVUIwOLgLgNXSOaZDzFdOHOAG3rTpKgCjwpGmxcB7oVtstimyrA8CqPs7YFPsS0RXBclkb97zPjviujtKB1JKVUZ6+fKnAfxdOscLMLfnfb9a26MTBJja2un2Vtt+jIEvSgeZDjF35X3/5CpOYVy/ZCuKRPolL4qi3QEkJOaewYYxoT8LVbYiAz+UDjFF85jv/1uV59izyuPPDbO2gjEd0dXSEaZiZrN+jpWslSs3o4o79OaFSIvJqk6F4aUw82d7fDyKrtz6i/aenhEAP5CLMzMC9sj7/hHSOUzX3tn5KANfks4hpJOA91tEzwSed0s+l3uNdCCl1MIRs8jqy9lQqdVFxeU972QAPdUYuwK+AgCZbPZBAH8WzjItYq7K2RTrXXcHAKa1Knsqlc0+ITExlU5ONwfzn7LZ7AbpGGp2lmWZVXwAEEZR1YpkEweIG7MSG0AYbt58l3QINbtUZ+dfAAxL55jMuPd8JY/oN9IRpngJgISJBTel5m2kt7cdwLnSOWbw06m99pjoiwBCoTyzIuZ3SWeIg8zo6H/AtJV8tWUBOI6i6I7A8x4MPO9sGNZCSSlVPiYyccXhSajCbhky9aBe4Km049z+r18RfUUwy2wOCny/4tvKE5Z1IgzbHUXMv5Samw1rccGWdbd0BrVtqc7O+wEMSueYjICXVWtsK5k0rQD38MTCIWW2kIDfS4eYjKv4OlHxVCwW75XOMMWiEdft1mKyqiuJlpa3AWiTzjGDr039FxnbfpaJjDuhc8LqUdd9qXQI461cudkCLgRg2Nk4IvYFcHXgef8ouO67fd9vlQ6klJqbtOM8COA56RxTrAh8/4BKDph33ZeD+ZBKjlkpDHwZQLT112nb/gUBIge/bVMUXVrpIYnZuBYXojdZmI0qkllEutoyHkIw/046xGRMtHO1xo4MK8AxoK+TmIiY75DOMMVOMOyGqpI1sSDxn9I5JkswazFZ1ZUEl4p6xiHgrrTjPDDd7yWiyNQ2CRQRVfxLYj1qc5w/gOjL0jkMsgMTfWEx87N53//3oaGhlHQgpVTZGMDN0iGmqnSrC4NXJa/fRDT1ANxiRHTltI+WRnTqcH9/d6WGG+ntbWfgsEqNVwlM1D/TNVyNrBSce6rRVGfng9IhVHmY6I/SGaao3jkbRCa9TkBaTI4NJvqtdIYpWjYMDTnSIZRhiIxanRxZVpcWk1XdyHveKSjdyTMP0YwF47Zs9h4Af6lhmrIxcE7BdZdJ54iDtG2/n4C7pXMYZjkxf6q5WOwreN5n8uvWLZUOpJTaNrYs41pdcKnVRUWM5XI2gNMqNV4lMfA/Ww/qncyKom8zsFEi0zY0JZPJih1iaC1adByApkqNVwnEfDPkdh8lAXQJzT2dPwEYlw6hypMA7pHOMEXVvqdxNQvVc1fckkwaVfhRM2t3nF4Az0jnmCyMIjNrGkoMM/9JOsNkxLxCi8mqbhBwuXSGaTE/nbLtX836GEP7IRKwmM096d40RSI6zdityLLSDFxBzc3PBp738eHh4bR0IKXUzDKdnX8AsF46xxS7jnpeRXrHhlF0AYBFlRirwooR89en+41UNjsE5h/VOlBZmC90XXdJRYYiqsphiwvBlnW91NwjrtsFg84hIOAR6QyqfG2O8wSATdI5JumsVgs0Yu6pxrjz9MyyZcsK0iFU+Qj4q3SGydisn2dlACIy62eUSIvJqj7kXXc/AAdJ55hWqf1BNNtD0rb9c5jXo7KE6BL09rZIx4iDNtvOMdEbYNaFu0kyAP4juWXL04HnXQzDVp8ppf5lHESz3wQVEAEnL3iQNWuaYe5N0uuXZrPrZvrNROl6wsT+/B1tlnXmgkfp61tMwGsrkKdyiEYyQ0NiqzuTZq22BIielo6g5iRkYK10iMmWhGHF2uJMYdJrRV8nMcNET0hnmIyYq/U6UTFFUfQP6QyTEWBrMVnVBSJ6r3SGGazfSHR1GY8bZ+AbVU8zP52FlpbTpUPERdq27wfziQA2S2cxWCeArwee93je806FHjKhlHE4ioxrdYEKtLoIli49DYCRvQjJsmbdpdTmOP8Lw06d34qZL8cC38sLicRrAZh2cOutWLVqi9TkkWWZ1OICiKKnpCOoubEAo4pkSCa3q/iYpUUvHRUfd76I9HUSN1H0pHSEySJA20yqF0hls0MAAukc/8Kc0WKyir2NfX1dqMRqpSog5iun6304Hd606SoAo1WONC8R8B5owa9s6Wz2diY6B0AoncVwuxJwXeB590zsLlBKGWID8JvS/xlln7zvL6yPINElFcpSaQ+lOjvv29aDyNC2WAB2z/v+qxcygJEtLqRvqjBXvvC2AFYioUWymDFtxWU1fqY3VqNAvQCsN11ih0276QIY9TOtDEFkTG9vItJisoq/LcnkpTBzu/z4eBSVffp6e0/PCIAfVC/O/BHwsnwud6R0jjjJ2PbPAJyPbbQ4UQCAQ4no/sDzrtEDH5UyQzab3QDgTukcU1EUnTjf5xYGBg4BsH8F41QO0RfLeVjKtm8FYNQKqq2I+bIFPD0J4NhKZamQTeNNTb8VzmBSQaHQ2tnpS4dQc2TYistqFJM3NTeb9DoBLEvbXMTMlmTyCZjURorInJX2yhjEbEyrCwa0mKzizXXdJQS8RTrHDH7a0dU1p8PYuPRl0sjVrBRF75LOEDdpx7kGzOcAENsiGyMWgLOYaE3B98+HroRXShwRmdfqYiGrVy1rIcXOahpIP//8L8p8LIPom1VNM3/HFQYGdpvPE/O+fzjM29b7W/FDtJiNKSgw0CudQc0dJRLGrGQDUJWfaYoiY14nAACiXukIam6WL18+CmBIOsdWZNiuFGUGBv4pnWESLSareGslOhdmrdqY7GtzfULGtp9loluqEaYCjhn1vFXSIeImnc3+0AKOBjAsnSUmljPzdwPP+9Oo5+0uHUaphlYs3gSgKB1jikPGBgfn3PN4Y19fFwPzXtVcTUz0jbn05d2SSHwfQL6KkeaLmOii+T2RjWtxQYD8zRSipdIRtiIic3o1qrIRs1F/b0yUrvSYCWZjXicAkGCWvQml5sucz1WilHQEZSST3ltatZis4owAGNn7kIC70o7zwHyem4iiL1U6T4UQE10uHSKO2hznD0gkXgFAe6iV76AIeDDveVegtGpZKVVjqa6u5xnYZh/fGrOKxeLr5/qkYjJ5CQxsicXARiuKvj2X5yxbtqwAou9XK9OCEJ23fv36zFyfBeD4asRZgJCAW6VDENAineFfmI0810PNrhhFJhUfQMwVfx9myzLndQKgbXzcqD9zVSYic97jmJulIyjzEFDWWWXM6BIAACAASURBVFw10qRf0FVsFXx/NYB/k84xLaJ5F4Tbstl7APylgmkqhpnPHsvlbOkccZRevnwtMR8C4DbpLDHSQsBnAte9beKgTaVUjRGz/OrMKWiurS76+hYz8NYqxVkQi+jaiRO65yRi/grMbIuVSmzadP5cnhB43v4Atq9Snnlh4N42xxkUz2FQQYHMWhGlymSFoVF/bxHRokqPScwVH3MBQnR3b5QOoebBrBXlJv1MK0OwFpOVqgxmNnOVLPPTKdv+1QLH+GqF0lTaojCKLpAOEVepbHYo7TirmehDMG/ruLmIjhpPJv824ronS0dRqtFERDdIZ5jGa0Z6e9vLfXA+kTgLhrbEKhJ9Yz7Pa3ecXgALu9aoFqJLASTKfriJLS5MuYlCZEwxmQFzVu2psqW7u00qkIGAiv9MRwbddIG+TuLMpNeKST/Tyhwmvb9oMVnF06jvvwzAq6VzTIvoywCihQyRzmavA/BcZQJV3EXo7TVqO1nMRBnb/pTFfCQT9UuHiZEOi+gXBc/7DLTthVI10+44vcT8qHSOKZqsxYuPKffBFtHF1Qwzb0S/XdrZ+bf5Pp2JvlLJOBXUU3DdsluRMJFxvazZsm6SzjDBpIKCSSuiVPnGAWySDrEVEVX8OwQRmdTCSF8n8WVSf3FdmaxehJlNen9p1i/kKpZC5neh1GPPNOs3El1dgXHGGZjXaqUa6CwsXvwm6RBx15bN3mMVi3uB6IfSWWKEGLgi7/u/HBwcbJMOo1SjYCIzVmlOUu5q1nwu9xoG9qx2nnkptaqYt4xt/97AQn8J0WXlPGzUdV8K81qWPZyx7WelQwAAmFk6gqoLJn3nX9CCG6WqyKTXib73qxcjMqn+xSa9YJQqy6jnLSfgTOkc0yHmK23brsgdI9606SqYtZXhX9jcYn6spLq6nk/b9lkAVsPclejGIeYTW8LwTyOe1yOdRalGEFmWca0uGDimnF0yFEVlFTVrjvnptOMsvIe+ZX2tAmkqjoFXjfT3772tx4WWZVyLCwDm3Dwh2iIdYZKUdAA1D2vWNMOgFe4cRZsrPiazvk5UJZi0UKXirxMVf5ZBP6MMbNFisoqdCLgIJp1u/X/Gx6PoykoN1t7TMwLgB5Uar8J2D1z3aOkQ9SLtOL8uNje/DMCV0BUbZWFgTyK6tzAwsJt0FqXqXXtn56MAnpHOMUVbYfHio2Z7QDA4uBLAsTXKMzcVaIkFAKlC4YcAcgsPVHmUSFy6zccY2C85tCxjislsUDGZDfoSq8oXpNNG/b1V42faMuh1AqAVuuAmrky6EWDSz7QyBJfeX4xAWkxWsbN27SIAph4A99OOrq6+Sg7IRF+Emae1A0Tvko5QTzo6OoK041xkAXsAWPhqtQZAzF1sWX+Y6KGulKomIlN6yP5LtK1CZLF4CczatlpCNLI5kbimImOtXLkZRN+pyFgVRsCZY7mcPdPvD/f3dwPYt4aRytG7kD7WlWYxj0tn2IqIjCpKqvJEiYRJBTIQUeVXJptVTLZ8318iHULNi0nvcboyWb0IGVRMBjBu3gW2UrMotLWdAcCRzjGDim81zdj2s0x0S6XHrZDXrs/lzOxDGWNtjrMm7TjHsGUdBWCNdJ4YsCPmO/VnUanqsqLImNWaWxFwPIDkdL83NDSUAtE5NY5UFmb+zvLlyyvWxiqZSHwTZq5iWhRG0Ttm+s1kMnkyDFvBx8AvpTNMxlUovM0bs1FFSVWepGE3ATiK/j97dx4fSV3nf/z9qeokc6Srk0ySqkrCEGQAjQciInKJCrhesCDgAYqroiiiiKwru+7+QHfXlV3llFsFuURUkPsQRBAEOQQBg8AoAyRT1ZlMMt2dSSZJV31+fySjISSTq7s/3+7+PB8PH3LMdL2GmU66P/2t73ekCI9p1Ne/esvS50o5YjbpuVLw54kqfyatTIauTFblhud5oEupEXCP43mPFOOx7Tg+sxiPWwhWFM15C6tanFRr613OwMBuAL4I824vN02rHcd35Xp7d5YOUapS1fv+AwA2SHdMs2pTGO4307+ojaJPAUiVuGc+IhAVbEssAFjR3LwezEYNQaf44uRdZa9i4hYXFrNRH5oQYNLJ7SY+n9Qc2LLM+n0jGij4Qxp2xkw8NuZIN6hFIDLn960IzxNVAZhN+nqe1WGyKhubwvBdYJ7zMBcRREUb+Nb7/n0AHi7W4y8FEX1884YNpq4UL39dXWOO553veN5ORHQIgKJ8YFEhWti2bxtKp1ulQ5SqUBEDxt0pYwEzDSQJzMeXPGYeCLgu5bovFPpxGTij0I9ZIK3ZlSs/PP0f5np7VzGwr0TQNvQlff9B6YhXiOON0glTdMKwleRqbhxFr5FumKa/4I9o2OCNLWsH6Qa1MOl0eiUAc95DxHHhnyeqEnRKB0wxqMNkVTYs4CvSDTNifj7purcU+RrnFPXxF68uiiJT97CuJHHSdW9yPO9txLwfgJulgwz1mpj55iAIdK86pYrAIjJq1SYAMNGrtkrIpdMfAGDm4ZxxfHYxHjbl+48CeKgYj71kRK9+/Wbbs25RIoWZb4Rp51SYNSRbMdDb2y4doRaIaCfphFcgKvgHJGxZJn3oAliW3ilXZuqiaGeY9GFZEZ4nqvwxkUkfDm7SYbIqC5Mnsn9QumNGBTqRfVsc378WwMvFvMYSHI+enuXSEdUi6fv3O553MIA9GbgORf6zV4b2WEl0qXSEUpUomcvdCSAn3TEVMbdnw/CtU/8Zx7GRW2IBeCzZ1vZA0R6dqCiD6gJ4Sy4IXrEKmWdeUS6KDPywBIBJw2TYiYQOycqPUb9nnM8X/M80Dw8b9TwBs1H/zdXcyLLM+tAF0GGyehUCTLrrIaPDZFUeJvbmNfHP6+AI0Y9LcJ1xBs4rwXUWoyVj2x+Xjqg2juc9nPK8wymOu5j5h6wHNUz14UwQfFY6QqmKs2bNKAF3SmdMN3Xv3aEw7ALRAZI9s2Iu6hkIjuv+HKZ+8DzlzIsNGzbUM3CgZM4MhpwtW+6WjngVs1YmA3GsQ7LyY9TvmcX8UqEfs6GzMwMgX+jHXQLTBpNqDmTY3UxEZOb3ciVmc1+fC8CkQyI3mjicU+oVBgYGHABGnshOzBe6rluSw1F4y5aLYNgBE1sR0ckwc9hf8ZJtbc+mfP/YuK7OZ+bjGHhauskERHRmdsMGfTGvVIGxYQeUAQATHT7lr0+ESbeq/t16Z3DwZ0W+Rp4LfLhfoTBwWCad3gEAaqPovQSYdkfTrejs3CIdMR0zB9INU5FpWyao+TDp9yzndHQU4wMSBtBXhMddLKMG+GpeTHqeIAbWSTcos8SASVtcgIl6dfijjFczNvY5AOacrvp34+NxfH6pLtbQ2bkJwGWlut4C7ZINw3+QjqhmjY2NmZTvX5zyvDcy81sBXAFgTLpL0EpE0Y8B2NIhSlWSeHT0Zpj3tWXnoSB4XeallxqZ+WjpmJkw8/no6ir6fzcaH78IwHCxr7MINpi/ALxyJbkxzNziAhbROumGqQh4i3SDmr/JD9WT0h1bEVDww0f/hnld0R574bbP9fauko5Q88fAbtINr2DY134lb/L9vTEojnt0mKxMZzNg5InsAK5pam/vKeUFmegMmHY4zFbMJ0knqAkp33/M8bxjbNvenom+AeBF6SYhe2XTaVO/fihVlho6OzeB+T7pjukiyzoMtbWfA7BSumUGo7ZlXVKKCzkdHQNEdFUprrVQRPTZzEsvNYLofdIt04zHIyO3SUfMpN51N8CgDwcYeLuek1E+OJ9/l3TDVFzc1ZbFfOyFsiLL2l86Qs3PUDrdSsDrpTumiFKtrbrNhXol5n2kE6Ziy9KVycpsmTD8EMzaaHyqc0t9wZTrvsBEN5X6uvNCdNCmvr5dpTPU361saQlTrvttx/Neg4kDLG9GtR3Yx/zv/f39xqzKUaoiGLiKk5iPIEM/fGbmK+tdt2S3YBNwDiZu+zYLcwPV1FwKoFE65RWI7pm8+8tEDKDge8wuwbJNicTbpSPU/BCRacPkZ4v12GTYwgmL6J3SDWp+IuZ3wqTtsZj/CmBcOkMZZy/pgKmsKNJhsjIbMX9FumEmBNzjeN4jEte247ioB/gsBcXxiXP/KCUgdjzvFsfzDk4kEtsB+CaADdJRJdJam8+fLB2hVCWpyed/CfOGlbsBWC0dMZPYts8p5fXqXfdpAL8u5TXnjegfpROm4zi+XrphDuukA6ayAKMGlGpWBMCo1bFUxHM9YsOGyazPk7JBwDulG6ZioqekG5RZRnp62mHWa9woOTy8TofJyliZIHgriPaW7pgRkdhAt9737wPwsNT1t4WAo4b7+33pDjW7Fc3N6x3PO80ZGtoOzMcAeEi6qQROHkqnW6UjlKoUyzs6egGIfKBadpjvamxtfbLUlyWis0t9zTIV19TU3CgdsU1Ef5ZOmEaHZGVgKAheC8Co1+RxHBdtSGYDzxTrsReDgNdv7utzpTvUvLxbOmAqAnSYrF5hvKZmP+mGadZhzZpRHSYrYxGRmasJmZ9Puu4twg0lXeW0AHX5KDLyNmM1zZo1o47vX+F43l7MvDsRXQxgs3RWkdTHcfw56QilKgkT3SDdUA7IskSGuknXvRlFvKW8gvx+RXPzeumIbTFwsPC2TevWNUhHqG2LLes90g3TRA1jY0Ub+Ebj46Y9TyiKogOlI9S2bQqC7QHsIt0xFQN/km5QhmF+r3TCNM8BQEK6YprLmcioTxULzWLW/W/mYaSnpx2JxOHSHTMiOgvC+846vn9tNgz/B8B2kh0zYj4+nU5/x3XdSh1MVpyU7/8BwHGZl146xaqtPZaBkwFU1moKos8A+Daqbc9opYrEjuPrY6L/lu4wGvPzSc+7VerqIDofzLpCeRsIMG7/7+mY2bQhWS3V1X0YwMXSIWobmI+WTpiKgWfQ2bmlWI+fWr16MBeGPQx0FOsaC0b0cQBGHoiqJpBlHQU2a9cusu3HpRuUUWoAHCwd8QpEzwKGDZOJ6BeO65p9q5kqiXwi8SVMPHFMMzhC9GNHugIYZ+A8Ar4jHTKDpmVx/AkAF0qHqIVJrV49COD/sHbtOZmVKz8Jy/p/xNwu3VUgnZm+vgNSra2/kg5RqhLU+/4z2TB8Foat6DEK0TkQ/ABrzLYvrc3nvwUgJdVgvDg2foW9k88/nU0kIgC2dMtWRPQJ6DDZWLne3p1h23tId0xlET1Q7GvwxCp+c4bJwEHD/f3+iubmQDpEzYwmtvwzSdppaVkrHaHMkQ2CA0DUJN0xFcdxNwDoNhfKOEEQrGDgWOmOmRDzhaasuOUtWy4CMCTdMRMiOgn69aV8rVkzmvL9i1MjI2sAnADgZemkQqA4NvLrilLlqhxWdQrK5mtrL5cMaG5uzoHoUskGw/0p2dZm/lYgHR0jAP4inTHNPpm+vh2lI9QsLOuT0gmvwvxgsS9BQMn3p5+DHeXzR0lHqJllw3APAK+V7piKiX4n3aDMwkRHSjdMx8yPAoatTFYKAFYAxwBYJd0xA4ZlPZQJgt2lQwCA6uoA4B6YdtvDhJ1z6fT7J/dsVOWqs3OLA5yH7u5LMo2NnyKif4NZJ8ku1AeDIFjh+/6wdIhSlYCJfgnmr0t3mIiBi5uamrLSHTHz2RbwJRi0qtUYROX0YciDAHaWjpiCaOIutNOkQ9SrEBMZN8CMLev+ol+E6EHTtiyIgX8C8D3pDjWjT0gHTGcxF30FvyorNQT8o3TENGMNmzb9CW1tOkxWxiEi+rJ0xCyImW8gIumO8sB8EgAdJleCrq6xFHARursvza5a9QUAp4G5HA/fWVEPvAe6mlKpgnBc9/fG7VFphghE50tHAECD563LBsHNIDLtzYg4juOy+V7AzA8QkWmrTY8B8J8AIukQ9XeZvr4DCOiU7pgmSLW2Fn11PTH/jgEGYMybNQLekAmC3VO+/5h0i5pi3bplWLbso9IZ03EJtoNR5SMThoeSeYssn0RX1xigt6Erw2TD8P0AXifdoZaOgXdvWr9+N+kOVUBdXWOO656N8fEdCTgdwKh00kKxDlSUKiRm/dDwVQi4PuW6L0h3bBUT6SF80zBRbzkNd2yg+Ks6F26HXBh+XDpCvZIVx/8m3TCDO0txkXrP2wDguVJca0Es69+lE9QrZZcv/xyAFumOaQYd131EOkKZg4CvSjfM4NGtf6HDZGUW5q9IJ6jCsSxLfz8rkNPRMZD0vFNg229g4DrpngX6IPR7n1KFw1w2qztLhtmo4W2D591DzH+U7jAJMV+HiRWMZaHe9/8MoF+6YzoGTkN3d610h5qQ6+vbm4F3SXe8CtEdpboUA8at7CTmQ7Nh+DbpDjVp7do6Yv6adMYMfgW900NNyq1fvw+At0t3vArRb7f+pb6hVsYYCsPXg+gA6Q5VUB8b6O3V258rlNPSsjbleYcD+CAT9Ur3zFPzUBgaddiGUuXM8f1fg2iTdIdB/pD0ffNWkVrWudIJJuHy2i8ZmLgL4D7piBl0ZhobTdt+o2pxFJ0m3TCDmOL4V6W6GDHfU6prLdCp0gFqQra+/jMmbs9FRCVZwa/KQ2xZJq5KRj6KdJiszBNN7LFrzB5XqiBqaizrC9IRqrgcz7vFyud3BXCbdMt8MKCrQ5QqnHHEcVk890uC+UzphJkkc7krAaSlO4xAtCnlur+d+weaxSK6VbphJkT0DV2dLC/X17cXiA6S7pjBo0nfL9mqegJuh5mrO9+f6+vbSzqi6k18rTLx4GAez+dLtoJfmS27YcMaAw/eA4C/NLW1vbz1b3SYrIwwFIYtMPDkYbV0TPSFdDq9UrpDFVeyvX2j43kfBPBNGH7rsA6TlSqsMlzlWSyBMzh4rXTEjNasGQXRD6QzjMB8I4Bx6YyFsm37Vpj5/XX7bGPj8dIRVS+O/0s6YSal3g5tcnD9cCmvOV9xHP8PdOGUqOyqVccBWC3dMYOHm9rbe6QjlCGi6L8B2NIZ002/Q0qHycoIMfAFApZLd6iiaFzOrLdAVofY8bzTGPgoAyPSMdugw2SlCmhsYsi1RbpDHPP5W0+4NlHCts8HYGxfqVCZ7vO9ork5APC4dMeMiL6l25rJyabTRzHwbumOGVnWzwWuauTdMgTsnw3DT0h3VKvNfX0ugG9Jd8yEmM38IFqV3OQdDEdKd8ziFXdI6TBZyZu43eTz0hmqiCYOVtSvN1Ui5XnXWszvATAk3TKLnaUDlKokLS0tQwDulu4QNmrb9iXSEduyorl5PZglBjvGYGBk2LLKeV/Km6UDZpGsse2zpCOq0eDgYArM35PumMVjqdbWv5T6onEcm/o8AYDv5np7V0lHVKMois4Ac4N0xww4D1T192b1N8RR9F2YeQfDeFxX94r973W4o8Tlmpo+BsCX7lBFRLRTLp3+oHSGKp2k79/PlvUhAHnplhkksz09TdIRSlUSZr5BukESM1+5srXV+D2JGThDukEU0R2u626WzlgsC/ipdMNsGDhcX+uVnj06+l8APOmOmRAgstqyoa3tcQDPSlx7HlpiyzpdOqLaZNLpAwzeUvP3jb7/knSEkpcNgqNAtLd0x4yY721sbMxM/Uc6TFbiGDhRukGVwMQBi6qKpFpbf0XAKdIdM4kta3vpBqUqiW1ZN8DMQ49Kgm37XOmG+Uj5/mMAHpTukGKV6RYXW9V7XjeInpDumA0zn6vnZJROJgh2B2DqQdfReBRdLXj9nwhee5uI6NO5INhPuqNqrF1bR8znSWfMhoHLpRuUvGxPTxOI/le6YxtedQiwDpOVqE1h+E4Au0l3qOJj4J3ZMNxDukOVVtLzzoSBB6HYRJ3SDUpVknrX7UP1Dinvbmht/aN0xHwx0dnSDUIiMN8iHbFUxGzskAxA5zLmc6QjqkE6nV5JRFfAwEOaJt0heaAYW9aVMPPASgAgJrpS75IrjWx9/XcB7CLdMRMGRjA2do10hzJAInE+gDbpjFlwTHT99H+ow2QlyprYS1dVC6IvSyeokosBnDD5/8aIgRbpBqUqDQFVudUFldlwNuW6vwDwsnRHqRFwX9L3+6U7liqRz18Fw76nTkXAp7NBoIeMFdly5gsAvE66YzYx8w8lrz+5V/Ojkg1zWI1E4jKYuTdqxciE4RGYeB9iJCL6RWr16kHpDiVr8nvmR6Q7tuGBBs9bN/0f6jBZicmk0zuASPdWqybMHxlYv3476QxVWo7nPcKAUbcWE7BCukGpShNb1qtWLVSBtUnXLbfVrnkmukA6otSYyKjvQ4u1vKOjF4DZhwgSXTAUBMYOOstdJgg+B8DkgX1/w+bN4l8XWXigPQ8HZ8PweOmISpXp69uRgB9Id2yL9IcuSt5Ab28HzF+UMOPqeR0mKzEUx1+BubdmqeKoqbGsL0pHqNKziC6TbpiKLUuHyUoVWKq19S8MPCXdUVJE58DgVaKzGh29EEDZHkS3GAzcJN1QKERk7P6fk1ZGRNeip2e5dEil2ZxOvxFEZ0l3bAsxX4w1a0alO4aBKwCYvurze5kgeIt0RMVZu7aO4vhaACnplG14tsHz7pWOUILWrq1LJBLXAGiUTtmGyLasn8/0L3SYrEQMDAw4IPon6Q5Vekx03IYNG+qlO1RpEfND0g1T6cpkpYqDDLsLociy+ZqaH0tHLEZq9epBIpI8HKvUHku57gvSEYWSdN1bAfxVumNbCHhD1rZ/CL2Nv2CG+/v9iPkGAkwe0o+Px7ERdz74vj8MItO/RtcR0S+G+/t96ZAKYmVXrvwRAKOH9Mx8Fszd11sVH2Xr6y8B8z7SIXO4dWVra3qmf6HDZCWiZmzsswAc6Q4lgLmhLo4/JZ0hqru7NhMEb5XOKKX6gYGMdMNUzLxMukGpSsTMVTNMZuCSpqamrHTHYhHz2aiWN7KV9+cyJsCIgd02EX0sE4anS2dUgoGBASefz98CYAfplm1i/rnkwXuvYlnnwfy7RzrH8/k7Nq1b1yAdUgmyYfh/IDpKumMOg1ss6wrpCCUnGwTfgNnbFW0162sNHSYrCTYDutVBNWM+CVW6xUk6nV6ZbWq6AUT35fr69pbuKZVcKpWUbpiKquz2bqVKJeX7fwBQMStAtyGCZZ0vHbEU9Z73JzDfLd1RCpZlVdowGfHY2A8BGP9hBgFfy6bTegDzUqxbt8weG7sRwG7SKXOyrHOkE6ZyWlrWArhVumMuBLzRqqu7FkCNdEs5y6TTpwD4qnTHXBi4xHVdfS9SpTJBcDiIvindMQ8vOp436xkNOkxWJZcJw8Ng+qfqqth2yAXBIdIRpZbr7V21fOKN+3sJWM5xfEOut3dn6a5SiGtqjNqzjICcdINSFYu5YvamnQ0Bv0y1thq9zcB8kGWZfuhLIaytd92npSMKLbV69SAxf1+6Y16Yz8yE4ZHSGWXKzi1bdiUB+0uHzInoAcd1jdrWDACY+TSUw10YRAdlg+DH0K1hFiUbBJ8g5m9Ld8zDaG0+b9SHLqp0cun0IUR0JcpgFstEFwKIZvv3xv8CVOUhoq9INyh5THSSdEMpjfT0tLNt3wdgzyn/uBm2fXc1nHhOUbSTdMNUMbMOk5Uqkpio4laBvsrEFhFlL+m6twB4VrqjmBi4XrqhaOL4DJTHh6MWAVdk0+mPSoeUlbVr63Jh+BMGDpdOmQ8mOk26YSYp338MwG3SHfMysTXMDwAkpFPKSS6dPhZEl6I8BvE/WN7R0SsdoUovm05/jJl/DqActlsctuL4B9v6ATpMViWVCYLdy2CTcVUa+2XT6T3n/mHlL9PX95rxROJeAF3T/x0DHTHRA7m+vr0E0kqGiHaVbpiKLMv4W4OVKlcNnncfgH7pjiJ6POn7v5WOKBAGUVlv1zGXStziYqtke/tGYj5PumOe6sB8dTYMT5MOKQcbNmyozyaTNzJQLiu6H0q1tt4lHTErom9JJ8wXAZ/OBsFtAwMDer7QPGTC8OvMfDHKYwvF8Zj5/6QjVOllguDzYL4S5bKVDfMlSd/f5mt5HSarkiLgZOkGZZA4PlE6odg2rV+/G8XxgwB23MYPa+Q4vjOTTh9Qqq5SY2Bf6YapdJsLpYoqAnCLdEQRnSUdUEhjtn0pAKMOSS2gdLK11bjb7gvseyif3z8CcGo2DM9BeQx+RAz39/t1cfxbML9HumXemI3e/9Nx3d+jDPZO/huiAxNjY/ds3rDBk04xmJ0Nw/MI+A7KY0UyiOjSBt9/UbpDlZSVDcNvEdEFKJ/563gMnDnXDyqXX4yqAMP9/W0gOkK6QxmE6MjBIFgtnVEsQ2G4v2VZ9wBonccPryfmW3JheDIq7Gvz5OnURr0hiqJIby9TqoiIuVJXg/Y5W7ZcKx1RSM3NzbnJ24MrDhHdACCW7iimpO/3M9F3pDsW6EuZdPrnuvLy1YbS6Tfk8/kHwPxm6Zb5YuBex/dvl+6Yi0X0dWxj/08DvSWKogc39fUZdXefCfr7+5OZMLwWwPHSLQswPJ7P/6d0hCqdoTBsyabTtwH4D+mWBSH66Xw+9KiogYUyWzQ+/iWUy7J+VSoJi+gE6YhiyKXTh8TA7QAWcvBcHQPfzYbhnQO9vR3Fais1a9myjwOok+6YIh4hqug9QpWSloyiOwBU4knl56Gzc4t0RKHFE3tAl9OQZV64cj/UeIXUyMhZAMpqtRsxH5oYG3uy0rf5WohsGB4TMz+E8jqonAn4mnTEfNS77tNE9CPpjgXqtOL4oWw6fSLKZPVtsW1av3632vHxxwj4kHTLghCd0dTe3iOdoUojG4Z7xMDDZXWHyYSI4vi/5/MDdZisSiIIghVM9FnpDmUeAo6rtJUp2SD4+BI31z8gYdtPZ4Pg6EJ2iejpWc5Ep0hnTPOS7/vD0hFKVbSOjhEmulM6o8BGbcu6SDqiGBo8bx2Yb5buKLCcs2XLPdIRJdHZuQXM5bXyacL2HMf3Te6jXLXvS/v7+5PZILgKwI8BrJTuWRDmnzie94h0xnwRK9efrAAAIABJREFU8O8ov63OloH5rGwQXJ/t6WmSjpGUDcNjyLIeAJFRB3vPw4Z8TY3ulVwNurtrM0HwDQAPAOgUrlkwZr4s6ft/ns+Prdpv2qq0VgDHAFgl3aGM5CTGxz8lHVEo2SA4CUSXY+mr8FMgujIbBFdv7utzC9EmIZNIfJOY26U7pnlGOkCpamAx3yDdUEgMXLWytTUt3VEsMdHZ0g0FdkslriKfjeP7VwEom6HeFAlM7KN803B/vy8dU2rZdPrttfn8H0B0lHTLImyJib4hHbEQ9a7bB+b/le5YFKJ/RCLxh6Ew3F86pdSG0unWTDp9HYAfE7BcumehGDi1qalJD/+ucLkg2C/b1PQHIvovlOcd+WOwrHmtSgZ0mKxKg4joy9IRymDMX0EFHMSSC4L/BtEZKORtaEQfi+K4O5dOf7qgj1sCmb6+gww9dFOHyUqVAOfzNwHIS3cUClvWOdINxdTgefcQ8x+lOwqFiapii4spYmb+Asp3u5L35/P557NheBq6u2ulY4ot29PTlA2Cs8F8P4A10j2L9D8NnrdOOmKhnMHB/wUwr5V3Bto+Bn6TC8Nry3mxyQJYk9u//ImYD5OOWaTHUp53sXSEKp6hMGzJhuFlTHQvgNdL9ywa0Xkp131hvj9ch8mq6LJh+D4Ar5PuUEbrzATBodIRS2Dn0ukLmejfivT4Tcz8w0wY3pNbv36XIl2joIbCsIvi+BoY+H2GgKekG5SqBk5HxwAB90l3FAIBv25oba2YQeusKmdgPhrV1NwmHVFqKd9/DMAF0h1LsBLAqdmmpiczfX0HSscUiZUNw2OQSPwZE4ttynUxxVpny5byXOHb1TVmAZ8HwNIpi8XAkRHznyf3Ui7XP0PblAmCt2bD8EFMbP/SLN2zSDEmzgcq1w/51DbkentXZcPwtJjoOQCfRJkt/JpmQzwy8q2F/ATj3uSrCjSx6lSpbSLLOkm6YVG6u2tzYfgTZj6u2JciYH+2rD9m0+kzNm/Y4BX7eouV6+3defLwQSP3dYstqyKGW0qVg4pZHVp5W0DMKJnLXQWgErby+HW13lIc1dX9O4BAumOJdqE4vjObTl+Z6+3dWTqmQCgbhu/PhuHDmBiOtUgHLQVb1vHlvI1MvefdC6KrpTuWhLkBzGdlw/CRbBh+QDqnUHK9vTtnw/ByInoYwNuke5boQsd1H5KOUIWVC4LmbBiexrb9FwCngrlBummpmPkbDZ2dmxbyc3SYrIpqKAxfD6JKXVmgCol5n2w6/XbpjIXYsGFDfXbVqpsYOLKEl60D80lRFP3FxKFyNp1+O9v2/QC2k26Zxcup1ta/SkcoVS1qxsevQxmv/pr0QtJ1b5GOKIk1a0ZBdIl0xlIxc2V8iLEIjY2NmZj5BOmOAiAwH8223Z0NgquGwrBcbx22MmF4RDYMHwNwC4DdpYOWjOjKVGvrr6QzlsoCvgpgg3RHAewG4OZsGD6am7jTsyxXRw729b0pG4bXsG0/A+ATKNNfx1ZM1Btv2VJWe4qrbcutX79PJgguYaIXAZwKICXdVCCPp3z/hwv9STpMVkUVTaxKLutvBKqEymgVe663d1VdFN0F5vcIJayYOlQe7u9vE+rYysqF4b+A+V4YvNqGme+QblCqmizv6OgF8AfpjiUhOgtVdItqwrbPBzAm3bEEcU1NzU3SEZIafP86EF0p3VEgNoiOioEnc2H4s2wY7iEdNC/r1i3LheEns2H4NAE/w8TAr+wR0MOjoxVxFk696/ZN7jNeKXZnoutzYfhEJp3+SLnsPZ4Lgn2zYXijHcdPAPgIKmNGxRTHn1noSk9lnuH+fj+bTp+YC8M/smXdT0THAlgh3VVAEYDjAMQL/YmV8ERVhhoKwxYQHS3docrKEZl0egfpiLmM9PS0s23fC2BP6RZMDpXz+fy6XBj+fHKPwZJ+gJMNww9kw/BRBk4HYPQLV8uyqnrAoJSI8l4lmsvX1FwmHVFKK5qbAzD/XLpj0YgeXNHcXO7bPCxZVFt7AoCXpTsKyGLgCAAPZ8OwOxuGp5n4mjETBLtng+Ds7LJlLzNwGSrr3Bhm4HOp1asHpUMKJeX7vwDRVdIdhcTAm4j5muyqVelsGF4u8d5gLiM9Pe3ZdPrETBg+yUS/BXAwDGtcogsc39cFLGUoCIIVmb6+A3Nh+J1sGD6az+d7wHwWA2+SbisGBr7neN4ji/m5iULHKLVVDHyegOXSHaqs2GD+IoB/lg6ZTXbDhp2QSNwJoFO6ZZoaBg6nOD48GwTPE9HFYL4s6fv9xbjY4OBgKjE2diSYv4Ty+eY6NBTHdyWlK5SqMpZl/TJm/k/pjkUh+kE17r3LwBkEHCXdsRhU3h9eFExjY2MmGwSfBdFtqKwhDTAxoD2VmP8jG4b3ENHV+Ti+q9H3XxJosTb19b2RmD9AzMcQUVkclLxIFzqeV3EHW/Lo6JdQV/dOYm6XbimoiX1cP0Fx/IlsGD4H5isYuDXl+09gEasQl2qkp6c9n0gcxMxHI5F4N5itSvvCNGntCNG/ONIVatu6u2uHGht3ZGAXEO0Eop2Y+Q0rid6KOK4p9/3Z5um5VD5/2mJ/MmWCwKT/Tn9AZexbVHpEpzqu+3vpjClqMun0CxX3TVmVQi6qq9uusbExIx0y3ab163ezLOt2AK3SLfM0CuBuIrqOmG+s97wlfX0dWL9+u4RlHQzmQ0G0PwxfhTwdM/8w5fvHSneUg1w6fQgz3yDdsZXjeRX6fqN6ZMPwWQDldpBWzJa1c6q19S/SIRKyYfg7AHtJdywURdEuyfb256Q7TJEJw+8ScLJ0R4kEBNwfM9/FwB0Nvv9iMS6S6et7DaLoQIvoQAbeBaC5GNcxCQNPDzPv6fv+sHRLMQwFwTtiortRHYvthsD8EBPdBea7Ur7/OIowXM4FQTMsay8w78PAgQDegsr7YGu6cRC9w9RD97Jh+DQAU/affwTMJXm/T0QWT+xvXE/ASgZWAmhA5f953JaI4nj/ZFvbA4t9ANOGyWqRiOiQpOsac/t2NgyPwcRJxUotGDGfnPT9M6Q7phoKw/1j4AaU70b7DOAZIro/juPHmOj5OIqebxof759yGjdlXnqpAXV1DYjjRhCtIaI3IY7fAKI3AtgB5fxNl+jthn3oZiwdJqtCy4Th/5HBd53MhImuT7nuh6Q7pGTS6Y8Q8zXSHQvBwFMpzyuXu2VKpSYbBL8B0d7SIQI2AngOwLNM9DyYnyfgRYrjzDjzZjuKNk/bssHKvPRSKq6pSdYAK9m2G5h5BzDvgokPw3YGsBOAarvJaYiY90j6/p+lQ4opk07/KzF/W7qj1BgYsYDnATwP5uew9bliWZsiYDNGRzelVq8eAjC+9ecMDAw4y+J4ZZ55JefzKQvYDkQ7xcw7g2gnAnYBYNQh4SXyJcfzvi8dMRvDhslK1mmO531zKQ9QDZ+8KRmVcIq0EsJEXwZwDoC8dAswOVgDfgpgmXTLEhCALmbuIiIQAMu2kbVtIAzzAIYBOFRbO7EjHk3O7qb+dRkj5j8mPU8HyUoJseL4l2xZZTVMtpnPlm6QlHLdX2TD8GUA20m3zBcBusXFq43nmT+aIHocwCrpmBJbhYnV9XsR/339FFvWxJtg20Y2DAFgMwMWAcupthY2JpdpxiXfCcBMRMclPa+iB8kAkHLd07NhuB+A90m3lBIByyf3g33T317zE4GZJ1aQ1NZufZ6MAdgCwEng72/SiAg85a+rFQE/Sxo8SFZqivsdz/uvpT6IDpNVwQ0FwTtAZORJy8T8oXh8/DfSHcaorT2FgH+RzpjB9pkwPCzleT+TDskGwcdB9CMANdItRZQAUNFbezHRJdINSlWzZFvbg9kwDAD40i3z9Hi9590rHSEsz0TnE/P/SIfMF+t+yTNqamt7ORsER4PoFgC2dI+BVlbvCGxO5zuue7V0RInExHwMEz0C885GMUEtymyLuxJ6Zry2VrfSU+VgIGI+GkC01AfSYbIquMiyTpr66b9B/pT0/V8CMDJOwua+vjOiOP4yDFxxS8DXAIgOk7NBcBKIvody3tpBAcBQvGVLRZ3UrVQZionoJmb+nHTIfBBQ1auS/2Z09CLU1v47JvYXNN2Lk3t/qhk4vn9HNgi+BiKjthFT5mLgvtTAwEnwqme3gqTv9w+F4Qdi4Hco363tVGkNwLb/sRoP61VlJwLw8UIdVmsV4kGU2iqTTu9AzAdLd8yEiM6EDpJfYWVraxoT2zeYaI9cX5/Y/n6ZMPz65BsuHSSXvzMbOjs3SUcoVe1M2od7Dn3JLVtM/d5YUqnVqweJqDw+jJtYlayv87bB8f0ziehi6Q5VFv5qMR+Orq4x6ZBSq/e8bgAfQwFW7qmKN85ERzotLc9Lhyg1FwK+7njebYV6PB0mq4KiOD4RZt4+15ccGSmPN0MlZk+svDXzzVccnyRwVTuXTl9IwHcErq0KjWgTj42dKZ2hlAKcoaG7AZTDyp3zpxxMWvVoYu9oM18nTBET6RYX85DcuPFLDFT7Fi5q2wYpjt+f9P1+6RApjufdRsC/SncoszHzF1Ou+2vpDqXmxHx10vO+V8iH1GGyKpj+/v4kiP5JumMW+sZwFitd9ykARn4TZOCwTF/fjiW8ZCIbhlcz83ElvKYqImb+zrST2pVSUtasGQVQsBURRTJq2/ZF0hEmqfe8bjDfLd0xh40Nnne/dERZ6Ooai2prDwGgW4KoV2FghJgPSba1PSvdIi3pef8HQLeFUbM5LeX7eiaLKge/dUZHP1PoB9VhsiqYuvHxz8LMvaVGbcu6UDrCcKau3LSJ+YQSXi/PwLoSXk8VVzDMfK50hFJqCiKjt7pg4OqVLS2hdIdpyLJM30P6JgB56Yhy0dTUlLWI3gvgOekWZZRxAo5I+r5+MDPJ8bx/ZuBS6Q5lnAsdz/umdIRS8/AM8vlDi7GwUofJqlBsJvqidMRMiOjyyb2B1Swcz7sVwDPSHTNi/symdesaSnW5lOedQkS6Kq0CMPOpvu8PS3copf5uzLZvBjAq3TEbjqJzpBtMlHTdWwAYu1KRdIuLBat33T62rPcD0A9PFAAwmD8z+Z5A/R2nPO84ALdIhyhjXOt4npFzD6WmWR8zv8/p6BgoxoPrMFkVRCYIDgXwGumOGTAxnyUdUQaYJ/ZENFHSXrbs2BJej5OuezyAK0p4TVVgBPw65fs/kO5QSr1Sc3NzDsA90h0zIeCehvb2J6Q7DMUgOk86YhbDQ3H8K+mIcpRqbf0LxfE7AayXblGiGMAJju/ra9+ZjTtDQ4dj4g4IVd1ucYaGjgEQS4coNYc+i+gfGnz/xWJdQIfJqiCI6CvSDbO4bfJEXjWHVBRdDsDUgzZOBFBTwuvFjud9CsBlJbymKpzh2LI+hzI4MEqpasTMZq4iJTL1Q1UjjNn2ZQAy0h3TMXC73oWyeMm2tmcpit7FRL3SLUoEM/BFx/POlw4x2po1o87AwBEAbpROUTII+IXjeYdNnv+glMk2WEQH1Lvu08W8iA6T1ZJlgmB3APtKd8yELcvUvYDN09ExAuAC6YyZMNCRTacPL/FlI8fzPg3A1JVYanZfT7W2/kU6Qik1s4Rt/xLmrepZl3Tdm6UjTNbc3JwD0Y+kO6YjUz+cKCPJ9vbnyLLeRUCPdIsqqZiAT6c8z8jX/8bp6hpzBgaOZN1Wp+oQ8POk530MwLh0i1Jz2GCXYJAM6DBZFQABX5VumAkDT6VaW00/fdwoFtH3ARR8c/aCYD5Z4qqO530JOlAuJ7/V1TVKmW3yHIPfS3e8wsRWT5F0huli5nNg1n+nPMWx7vFaAE5Ly/OJfP7tINKtXqrDGIiOTnreZdIhZaWrayzlukcC0MPdq8dlOkhWZeJFiuP9VrruU6W4mA6T1ZIM9/e3gegI6Y6ZWMD3oLe5L0i96/Yx8BPpjlm8NRcEEivgtw6UzxC4tlqYMB9FR8G8FY9KqWkIMGllVy5atuxS6Yhy0OB565jIpH1D7022t2+UjqgUyzs6esds+x0AdEBf2YaY+WDHda+RDilTecfzvoCJbR71NWcFI+D0ya0P89ItSs2hOx/H+yXb2kp2WLIOk9WSROPjJwCole6YQTq5ZctPpSPKkU10BgwdwsdEJwldmh3POxnAt4Sur+Y2CqLDmtrb9RZdpcoA2/Z10g1/Q/TDxsZG4/YCNpVhB/aa9KFERWhubs45nncoM/9QukUVxfrYsvZN+f6d0iHlznHds0F0NEy9q1MtRcTMX0h63inSIUrNhYH7eGxs36a2tpdLeV0dJqvF6+lZzkSfk86YCTOfi85O/ca+CPWu+zSY75LumAkBh2b6+naUur7jeacS0Wegn04bh4i+6LjuQ9IdSqn5cVpa1gIw4YDcmCe2eFLz1OB5vyHmP0p3AOB8HN8gHVGhxlO+fywzHwdgTDpGFczjEfNeDa2tJjx/K4LjutfEcbw3gBekW1TBDLBlvS/l+7qViTIeEV2cGhg4KLV69WCpr63DZLVoGds+BsAq6Y4ZDFvARdIRZY3I1IMLLYqiL0sGJF33RzHzRxgYkexQUxCdmXRdXUGlVLkhul46gYlu1AM7F8GyzpFOAPBoqVfhVJuU71/MzPsAeEm6RS0R80+cfH6fRt/X38sCa2hre5yiaA8Q6Wrv8vccMe+Tam39lXSIUnPIM3BK0nWPQ1eXyIe+OkxWi0VEdKJ0xCx+nPT9fumIcuZ43u0wY8XYqxF9JtvT0ySZ0OD713EU7Q3gRckOBQC41nHdf5GOUEotArP4qlLDtmwoG8lc7ioAackGJtItLkog5fuP2ra9JwH3SLeoRRkH80mO7x+Fjg5dCFEkyfb2jY7rvp+Yvw3dR7ksMdH1Y4nEW5O+/2fpFqXm8BLF8TtTnne6ZIQOk9WiZIPgPQBeJ90xA6Y41jeGS8fMfJZ0xCxWUiJxrHREQ3v7E8T8VgJ+I91Sxa51PO9o6LYjSpUlx/MeBSC2spSBpxo8716p65e1NWtGQXSJZILNrMPkElnZ0hImPe+AyQPHdNuL8vESWdY7Hd839TV9pYmSvv+NGDiQAD3Do3yMgugrKdc9vLm5OScdo9S2MNEvkc/vlmxre0C6RYfJanEs66vSCbO4rZQnWFay1ObNl0N41dFsYqIvo7tb/ODHpO/3JwcG/gFEZ8HQQwsrFtFVjucdBR0kK1XOGIDY6mQLMPbA2XKQsO3zITVYZH6+3vPMvIOqcrHjumdPbnvxnHSM2jYmup7Hxt6cbG39nXRLtWnwvHvydXVvAPNPpFvUnJ6L43gvx3XPhr4eUGbbzMDxKdc9zOnoGJCOAXSYrBZhKAy7wHyQdMeMmM+VTqgYa9aMAjDy4AFibs82Nh4p3QEA6Ooac1z3JAAHA9ggnVMVmK92XPeTACLpFKXU0rBlSQ2T+5JbtlwjdO2KsKK5OQDRzySuTUTXSVxXTWx7sZl5t8nzNfT7sGmINhHw6ZTrfkjiQCY1obGxMeP4/lEgOhqAbr9oHgZwwaht797Q1va4dIxSc/gtRdFbUp53gXTIVDpMVgvGE7e4kXTHqzA/7/i+HnxQQBbR+QC2SHfMiMio1fGO592SSCTeDOAO6ZYKxiD6L8f3PwF9A6tURUi1tt4LQGKFxQXo7DTz+1sZ4TgWObBX90uW5fv+sOO6XwXRvgD+JN2j/ub2fBS9Kel5l0qHqAmO617NY2M7E9HF0i3qb9Yx0UGO5x3f0tIyJB2j1KyINhHRZx3P2z/Z3m7cHUE6TFYLku3paWLmo6U7ZmRZ50IPPCioetftY+arpDtm8ZahMNxfOmKqFc3N6x3Pey8DH4bMcKSSbQHzMY7r/gf0ea5UJRkHcEuJrzlq27aRd96Um5TvPwbgwRJfNu247sMlvqaageO6DzlDQ7sD+H8AhqV7qlg/gE86nve+prY2sX3o1cxSq1cPJl33OCI6BMBfpXuqWATg3FHbfmPKde+WjlFqGxjAFTbRa5Ou+wMYugWLDpPVwtj28QBWSGfMIJevqfmxdEQlsiduYzTyC1jMfJJ0w0xSnvezfBTtCkDf7BbGujiK9nJ8/0rpEKVU4cWlP0jtmpUtLWGJr1mxmKjUBx9fD/1Q0Rxr1ow6nvefNfn8zgCugKGvGStUDOAKC+hyPO9y6Ri1bUnXvcnxvNdOHmSpB72V1qMA9nY878u6GlkZ7hGyrH0czztmZWurkedXbaXDZLUQNUR0nHTEjJgvbWpqykpnVKJ6z/sTADO3DyE6JBcEr5XOmElTe3uP43n7gvmrADLSPeWKgeuIeY+G9vYnpFuUUsUxAtyOEq5qZObvl+pa1SDlur8AULrVkKX/8EHNw/KOjl7H846JgXcDeEy6pwr8npnf5njeMfWep2d2lI9xx3XPzkdRFyY+fNEPxoqrj4BPOZ73NsfzdJGPMlk3Ax92PG/PZGtrqe/4WhQdJqt5ywbBRxnokO6YARPz+dIRFY1ZZE/EeSAmOkE6YhvGHd8/k6JoRzCfA93ndyEGmfm4lOcdnvR9PbhEqQrm+/4wgLtKcS0G7k35/qOluFYVyfPEGQulkHEGB+8p0bXUIjR43m8cz9uDiA4h4Enpngr0IjMf53je3pPbzKgyNLno5BgLeCMBP4Ou6C+0zQScHtXV7Zz0vMug/32VqZifB/PHHc97Y8rzyuprgQ6T1fwRfUk6YRa3JdvanpWOqGSO799h8BuCT+V6e1dJR2xLsr19o+P7JwLYi4DfSPeYjoHrbMt6Xcr39bASpaoEASVZbWoxl3pLhuowOnoRgM1Fvw7zLejqGiv6ddRScdJ1b0p63u5E9BkAa6WDKkDIwPGO5+00+fpIV7RWgHrP60563odBtDf0EO9CGAdwnm1ZOyY975TGxka9O1SZiegJAJ90fL/L8f2rUIZf03WYrOZlKAjeAWAP6Y4ZMZ8rnVAViEz977wiTiQ+Jx0xH47nPZL0vHdZwDt1qDwD5udj5sNTnne46XtEKaUKLIpuBJAv8lXWJX3/xiJfoyqlVq8eJKKiH9jLRLrFRXnJJ133R47n7TJ5+JjeZr5waQZO2cy8Y8rzLsDEsExVGMd1H3I8772RZe2Kie0viv39sNKMAbgCtt3leN4J+j5CGSoGcEsMvNtx3d0m97ov2+e6DpPVvESW9RXphhkxP+/4vpn7+VaYZC53BQAjDywi5hPQ3V0r3TFf9Z53b9Lz3kVxvC+Am6V7DNDPwCnO5s1vbPD966RjlFKll2xv38jAA0W9iG43VFQ0seq7mLdnjo4nErcX8fFV8cSTh4/tycz/gInXPmW3CqvEXmDmzztDQ9unPO/0ye2AVIVrbG190vG8Y2Dbr5v8nqUra7dtM4jOTCQSOzied4zT0qJ3QSgThQSczpa1k+N5H2zwvIrYrkuHyWpOm8Kwk5gPke6YkWWdC30xWhpr1owCuEg6YxZt2cbGj0hHLFSyre0Bx/MOBrAngMsBbBFOKrUcgFNHbXuHlOedPvlnTClVpai4B6vlomXLflTEx6969Z7XDeZi7n39q+bm5lwRH1+VQMr373Q87+CafH41gG8C0MPj/o7BfNfkIUw7p3z/In1tVJ2clpa1ju+f6GzZ4gH4JDH/UbrJMGsZOIWYOx3X/eqK5ub10kFKTbMZwDVEdKjjedslPe+UVGvrX6WjCkmHyWpOFtGJAGzpjhnk8jU1P5aOqCYWcB4DI9IdMyGifwZA0h2L4Xjew47nfTLessUH0VcAvCDdVGTrAXyTomgHx/O+1dLSMiQdpJSSFwPXo1grW5l/pHsnlgBR0fakJt3ioqIs7+jodTzvNGdoaDtmPgLMN2DiVvVq1MfA92Dbuzi+f9DkIUxle+uzKqDOzi2O512e9P03Y2LxyfcBVOvB1KME/IIt6yDH83ZOed7peki3MkyGgJ8x8OHNzK2O530s6bo3oEK/nlMmCMrmtEA1OyI6JOm6NxX6cfv7+5O1+fzLAFKFfuwlYz5n8lAzVUKZILiEiI6V7phJDLy7Qm4bsbJB8B4QfRTAoTDx+bcIDNwH5nNSvv9L6K3mRsul04fwxBt7IzieV5YfFKmFy6bTj4P5zQV+2Jii6HXJ9vbnCvy46tUoG4bPANilwI8b27bdvrKlxcjttlRh5Hp7V7Ftf5SAwxl4B8xczFIoGQDXg/kax/fvgr4uUvNXk0un38dx/BEQfQAV8j5hFhGY7yHL+kk0MnJdQ2fnJumgcpYNw6cBvF66o4LkATwG4E6K4zuSbW2/R4UOjmeSkA5QZqsdHz8WRCZ+g2JiPl86ohpZzN/liZO5jRvuWMBJACphmBw7vn87gNuxdm1dLpn8h8kXjAcDSErHLdBaBq7nOP5JQ1vb49IxSinDTWx1UdhhMvNNOkguGQbReZN7fRbSAzpIrnzJ9vaNAM4DcF6ut3cVbPtgZj4URAcAqBfOK4QXAdxGRLcmR0Z+hc7OatveTBXGeNJ1bwRwI7q7a7ONje8iyzoMzB9goEM6rgByTHSXBdxqWdbN+rVfGSQA8AgTPcTMD44SPeK67mbpKCm6MrlCFGllsp0Nw+cAvKbAj1sItzqe9wHpiGqVDcPbALxXumMGbDG/vt73n5EOKYp165ZlVqzY14qid/PEG6vdYeaqnccB/NImun6l6z4lHaMWTlcmKymb+vp2teL4iUI+ZgXdtVIWNmzYUF8XRT0o4Go5Yj456ftnFOrxVNmpyQXBnpOvfQ4E8DYA5XDwcj+A3xFwHwG313ven6SDVGXLrV+/C1vWAUx0IDHvD6BJumkeRkH0KDHfHxPdmdq48X50dVXrljdFpSuT52WQgJcZeBHMf2Wg2wK6OYq6nY6OAek4k1A2DC+UjlBLZwHnFXpok+nr29Fi/pdCPmbBEF2WbG19UDqjWmXT6T0J+LR0xyxuLsaWLybatG5dg718+f4x8340sZLvzQBWlbKBgRECHmPg9wAeqs3nH1ze0dE4aN4lAAAgAElEQVRbygZVeIN9fW9KMB8v3bFV0nU/L92gSicbhn9BgT7IZuDplOe9CcXai1nNKJtOnwHmkwr1eGxZO1bawTVqCdaurcsmk7sB2BNx/DYQ7Q5gR8jedZsF89NkWU8BeARx/EDS95+Ffu1RcijX27sTW9aeINoTEx/CdAFYKdg0zsCzBDxNwB8Qx79LDg8/qgdNlkY2DE8lojbpDgkx8yZr4pBTjok2EdEI4niQLGsQUTRIljU4Ytsv6Vk+80fM+v1NKaUqxUhPT/t4IrErE+0K5jUEtAHYDkTtYG5Y5MPGBKxnYB2AF0D0IgHr4jh+IuX7TwIYL9gvQClV9bJh+D0AXy3EYxHw6aTnXVqIx1LztykMOy1gLQpw9wwx/3Hy8CmlZtfdXTvY3Pxai/l1xPxaBrYnYDWYV4NoNYC6JV4hArARkyvWCFgHohfBvDYGuhs8b92Sfw1KFR9l0ulOYn4dAV0MdALY/m/Pl8LcUZIB0IuJbV1e5InnyrqY6JnG1tZnoO8blKoIOkxWSqkqEQTBinrm7WKiesu262JghcW8ImauI6IEM+fBnGGiMWLO2cBwHhhuGBwM9HYzpVSpZPr6XoMoOrAQj5UaHb1c9yWVkQmCw1GAu2Us4Jmk7/+2AEmqiqXT6ZU1UdRkJRJNiOMmsqwE4rgBAIgowUAM5on/2XYGACiOM2xZG+Oamo2NjY0Z2V+BUiXQ3V27uaWliaOoiZmbYtteZkVRfUxUAwDEXMtEY5N/nWPbzlvAMKJogCxroN51N0IPk1SqKugwWSmllFJKKaWUUkoppdScLOkApZRSSimllFJKKaWUUubTYbJSSimllFJKKaWUUkqpOekwWSmllFJKKaWUUkoppdScdJislFJKKaWUUkoppZRSak46TFZKKaWUUkoppZRSSik1Jx0mK6WUUkoppZRSSimllJqTDpOVUkoppZRSSimllFJKzUmHyUoppZRSSimllFJKKaXmpMNkpZRSSimllFJKKaWUUnPSYbJSSimllFJKKaWUUkqpOekwWSmllFJKKaWUUkoppdScdJislFJKKaWUUkoppZRSak46TFZKKaWUUkoppZRSSik1Jx0mK6WUUkoppZRSSimllJqTDpOVUkoppZRSSimllFJKzUmHyUoppZRSSimllFJKKaXmpMNkpZRSSimllFJKKaWUUnPSYbJSSimllFJKKaWUUkqpOekwWSmllFJKKaWUUkoppdScdJislFJKKaWUUkoppZRSak46TFZKKaWUUkoppZRSSik1Jx0mK6WUUkoppZRSSimllJqTDpOVUkoppZRSSimllFJKzUmHyUoppZRSSimllFJKKaXmpMNkpZRSSimllFJKKaWUUnPSYbJSSimllFJKKaWUUkqpOSWkA5RSStpQGLbEwA4MdFpAZwy0WEQOMy8nYBkTpYi5hpkjACCiDANDBIRMFDDzeras5xrGxp5DR8eI9K9HKaWUUkopo61btyxXW7s9E3USkQ9gFZhXwbKawdwQAzYxOwBARAlmzmPibyICsgwMA9jIRBsRxxsty+ol5hc2E61zXXez4K9MKaUqHjGzdINSSpUKDQXBa5no7SDaC3H8NiZaA2BlgR6fAbzERI8DeARx/Gi8bNnvGxsbMwV6/HJiZfr6OqUjVGkMR1Ho+/6wdAe6u2szzc0dkgmpsbGgKj9UWrduWWbFijbJhCiR6G9qaspKNizF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"
    _user_prenom = st.session_state.get("user_display","").split()[0] if st.session_state.get("user_display") else "—"
    st.markdown(f"""
<div style="padding:18px 0 10px;">
  <img src="data:image/png;base64,{_LOGO_PNG_B64}" style="width:160px;opacity:0.92;"/>
</div>
<div style="height:1px;background:#1c1a17;margin-bottom:10px;"></div>""",
        unsafe_allow_html=True)

    # ── Navigation : UN SEUL st.radio — résout le bug de sélection multiple ──
    # Les labels de groupe sont injectés visuellement via CSS ::before
    # Structure finale :
    #   Général        → Accueil · Calendrier · TODO
    #   Opérations     → Opérations · Commandes
    #   Finance & Compta → Finance · TVA · Balance · Coûts produits
    #   Catalogue      → Produits · Stock · Packaging
    #   Relations      → Contacts · CRM · Marketing
    NAV_PAGES = [
        f"🏠  Accueil — {_user_prenom}",   # 0  │ GÉNÉRAL
        "📅  Calendrier",                   # 1
        "✅  TODO & Objectifs",             # 2
        "⚙️  Opérations",                   # 3  │ OPÉRATIONS
        "📦  Commandes",                    # 4
        "📋  Finance",                      # 5  │ FINANCE & COMPTABILITÉ
        "🧾  TVA",                          # 6
        "⚖️  Balance interne",              # 7
        "💰  Coûts produits",              # 8
        "👕  Produits",                     # 9  │ CATALOGUE
        "🗃️  Stock",                        # 10
        "📦  Packaging",                    # 11
        "👤  Contacts",                     # 12 │ RELATIONS
        "🤝  CRM Commercial",              # 13
        "📣  Marketing",                    # 14
    ]

    # Groupes : index → label affiché au-dessus
    _NAV_GROUPS = {
        0:  "Général",
        3:  "Opérations",
        5:  "Finance & Comptabilité",
        9:  "Catalogue",
        12: "Relations",
    }

    # CSS ::before pour les séparateurs de groupes (un seul radio = un seul sélecteur)
    # CSS navigation sidebar
    # Stratégie : ::before sur le label du 1er item de chaque groupe
    # nth-of-type = position réelle dans le DOM (1-based)
    _sep_css = """
[data-testid='stSidebar'] [data-testid='stRadio'] > div {gap:0 !important;}
[data-testid='stSidebar'] [data-testid='stRadio'] label {
  padding:3px 0 3px 4px !important;
  line-height:1.5 !important;
  display:block !important;
}
[data-testid='stSidebar'] [data-testid='stRadio'] label > div:first-child {
  display:none !important;
}
"""
    # Injecter les titres via ::before — nth-of-type correspond à la position du label
    _NAV_GROUP_CSS = {
        1:  ("GÉNÉRAL",              "8px 0 2px"),
        4:  ("OPÉRATIONS",           "14px 0 2px"),
        6:  ("FINANCE & COMPTABILITÉ","14px 0 2px"),
        10: ("CATALOGUE",            "14px 0 2px"),
        13: ("RELATIONS",            "14px 0 2px"),
    }
    for _nth, (_lbl, _pad) in _NAV_GROUP_CSS.items():
        _sep_css += f"""
[data-testid='stSidebar'] [data-testid='stRadio'] label:nth-of-type({_nth})::before {{
  content: "{_lbl}";
  display: block;
  font-family: 'DM Mono', monospace;
  font-size: 7px;
  letter-spacing: .20em;
  color: #6a6055;
  padding: {_pad};
  pointer-events: none;
  margin-left: -4px;
}}"""

    st.markdown(f"<style>{_sep_css}</style>", unsafe_allow_html=True)

    # Initialisation
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = NAV_PAGES[0]

    # Si la page stockée est l'ancien format "🏠  Accueil" sans prénom, corriger
    if st.session_state["active_page"] == "🏠  Accueil":
        st.session_state["active_page"] = NAV_PAGES[0]

    _cur = st.session_state["active_page"]
    _active_idx = NAV_PAGES.index(_cur) if _cur in NAV_PAGES else 0

    page = st.radio(
        "Navigation",
        NAV_PAGES,
        index=_active_idx,
        label_visibility="collapsed",
        key="nav_single",
    )
    st.session_state["active_page"] = page

    # Normaliser : "🏠  Accueil — Jules" → route "🏠  Accueil" pour les elif
    _PAGE_KEY = page.split(" — ")[0].strip() if " — " in page else page

    # Filtre année : valeur par défaut, pas affiché en sidebar
    sel_year = 2026
    month_num = None

    # ── Sauvegarde & Restauration ─────────────────────────────────────────────
    st.markdown("<div style='height:1px;background:#1c1a17;margin:8px 0;'></div>",
                unsafe_allow_html=True)

    st.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:8px;color:#5a5650;
     text-transform:uppercase;letter-spacing:.15em;padding:4px 0 6px;">
  Données
</div>""", unsafe_allow_html=True)

    if _GH_PERSISTENCE and not _USE_SUPABASE:
        # Statut de la sync
        _status = _gh_get_status() if _gh_get_status else {}
        _pending = _status.get("pending", False)
        _last_t  = _status.get("last_save", 0)
        _thread_ok = _status.get("thread_ok", False)

        if _last_t > 0:
            import time as _t
            _mins_ago = int((_t.time() - _last_t) / 60)
            _last_str = f"il y a {_mins_ago} min" if _mins_ago > 0 else "à l'instant"
        else:
            _last_str = "jamais"

        _dot_color = "#c9800a" if _pending else "#395f30"
        _dot_label = "En attente..." if _pending else f"Sync OK · {_last_str}"
        st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:9px;color:{_dot_color};padding:2px 0 4px;">
  ● {_dot_label}
</div>""", unsafe_allow_html=True)

        # Afficher la dernière erreur si présente
        _last_err = _status.get("last_error","")
        if _last_err:
            st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#c1440e;padding:2px 0;">{_last_err[:80]}</div>', unsafe_allow_html=True)

        if st.button("☁ Eastwood Studio Cloud", key="btn_gh_save"):
            with st.spinner("Sauvegarde..."):
                ok, err = _gh_save(DB_PATH, "manual: forced save")
            if ok:
                st.success("✓ Sauvegardé sur GitHub.")
            else:
                st.error(f"{err}")
    else:
        # Mode local — afficher le download
        st.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:9px;color:#c9800a;padding:2px 0 6px;">
  ● Mode local (config GitHub manquante)
</div>""", unsafe_allow_html=True)
        if _os2.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as _f_db:
                _db_bytes = _f_db.read()
            st.download_button(
                "⬇ Télécharger la DB",
                data=_db_bytes,
                file_name="eastwood_backup.db",
                mime="application/octet-stream",
                key="dl_db_backup"
            )


    st.markdown("<div style='height:1px;background:#1c1a17;margin:8px 0;'></div>",
                unsafe_allow_html=True)

    # ── Espace flex pour pousser user/footer vers le bas ─────────────────────
    st.markdown("<div style='flex:1;min-height:40px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:1px;background:#1c1a17;margin:8px 0;'></div>",
                unsafe_allow_html=True)

    # ── Utilisateur + Déconnexion (tout en bas) ───────────────────────────────
    ROLE_DESC = {
        "superuser": "Co-founder & Directeur Stratégie",
        "ops":        "Co-founder, Logistique & Marketing",
        "crm":        "Gestion Image & Production",
    }
    role_label = ROLE_DESC.get(st.session_state["user_role"], "")
    initial = st.session_state.get("user_initial","??")
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:6px 0 8px;">
  <div style="width:26px;height:26px;background:#1c1a17;border:1px solid #2a2520;
       display:flex;align-items:center;justify-content:center;
       font-family:'DM Mono',monospace;font-size:9px;color:#d9c8ae;flex-shrink:0;">
    {initial}
  </div>
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:10px;color:#c8c3b8;">
      {st.session_state['user_display']}
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:#5a5650;letter-spacing:.02em;line-height:1.5;">
      {role_label}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # Bouton déconnexion explicite
    if st.button("⟵ Déconnexion", key="logout_btn"):
        for k in ["logged_in","username","user_display","user_role","user_initial",
                  "active_page","nav_single"]:
            st.session_state.pop(k, None)
        st.rerun()

    # Copyright + signature
    st.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:7px;color:#2a2520;
     letter-spacing:.08em;padding:8px 0 2px;line-height:2;">
  EASTWOOD STUDIO © 2025<br>
  <span style="font-style:italic;font-size:7px;color:#1e1c19;">homemade by Jules Léger</span>
</div>""", unsafe_allow_html=True)

    # CSS sidebar global
    st.markdown("""
<style>
div[data-testid="stSidebar"] div[data-testid="stButton"] button {
  background:transparent!important;color:#5a5650!important;
  border:0.5px solid #2a2520!important;padding:4px 10px!important;
  font-size:9px!important;letter-spacing:.08em!important;
  font-family:'DM Mono',monospace!important;width:100%;margin-top:2px;
}
div[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
  color:#d9c8ae!important;border-color:#5a5650!important;
}
</style>""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────────────
try:
    df_tx  = load_transactions(sel_year, month_num)
    df_all = load_transactions(sel_year)
    ventes, achats, result, tva_c, tva_d, tva_due = compute_kpis(df_all)
except Exception:
    import pandas as _pd2
    df_tx = df_all = _pd2.DataFrame()
    ventes = achats = result = tva_c = tva_d = tva_due = 0.0

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ACCUEIL / DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if _PAGE_KEY == "🏠  Accueil":
    display = st.session_state["user_display"].split()[0]
    now = datetime.now()

    # Prochains événements Eastwood
    events = [
        {"date": date(2025, 6, 28), "label": "PFW SS26 — Drop 1", "type": "fw",
         "detail": "3 items été · Veste, Pantalon, Accessoire"},
        {"date": date(2025, 7, 5), "label": "PFW SS26 — Drop 2", "type": "drop",
         "detail": "Collection légère complète en ligne"},
        {"date": date(2025, 9, 27), "label": "Paris Fashion Week FW26", "type": "fw",
         "detail": "4 items hiver · préparation production"},
        {"date": date(2025, 10, 4), "label": "Drop FW — Pré-commandes", "type": "drop",
         "detail": "Ouverture commandes collection hiver"},
    ]
    # Ajouter les réunions hebdo (tous les mercredis à 18h)
    next_wed = now.date()
    while next_wed.weekday() != 2:
        next_wed += timedelta(days=1)
    for i in range(4):
        d = next_wed + timedelta(weeks=i)
        events.append({
            "date": d,
            "label": f"Réunion hebdo — Mercredi {d.strftime('%d %b')}",
            "type": "meeting",
            "detail": "18h00 · Google Meet · Jules, Corentin, Alexis"
        })
    events.sort(key=lambda e: e["date"])
    future = [e for e in events if e["date"] >= now.date()]

    # Header
    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:24px;">
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.15em;color:#888078;text-transform:uppercase;">Bonjour, {display}</div>
    <div style="font-family:'DM Mono',monospace;font-size:22px;font-weight:500;color:#1a1a1a;margin-top:4px;">
      {now.strftime('%A %d %B %Y').capitalize()}
    </div>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;letter-spacing:.1em;text-align:right;">
    EASTWOOD STUDIO<br>{sel_year}
  </div>
</div>""", unsafe_allow_html=True)

    # Prochain événement hero
    if future:
        next_ev = future[0]
        delta = (next_ev["date"] - now.date()).days
        color_map = {"fw":"#534AB7","drop":"#c9800a","meeting":"#0F6E56"}
        color = color_map.get(next_ev["type"],"#1a1a1a")
        st.markdown(f"""
<div style="background:#f7f5f0;border:1px solid #e0dbd2;border-left:4px solid {color};border-radius:4px;padding:20px 24px;margin-bottom:20px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:#aaa49a;">Prochain événement</div>
  <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:#1a1a1a;margin:6px 0 4px;">{next_ev['label']}</div>
  <div style="font-family:'DM Sans',sans-serif;font-size:13px;color:#666058;">{next_ev['detail']}</div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:{color};margin-top:8px;">
    {'Aujourd\'hui' if delta == 0 else f'Dans {delta} jour{"s" if delta>1 else ""}'} · {next_ev['date'].strftime('%d %B %Y')}
  </div>
</div>""", unsafe_allow_html=True)

    # 2 colonnes : objectifs groupe + commandes récentes
    col_ev, col_cmd = st.columns([1, 1])

    with col_ev:
        st.markdown('<div class="section-title">Objectifs équipe — cette semaine</div>', unsafe_allow_html=True)
        try:
            conn_dash = get_conn()
            today_d = date.today()
            lundi_d = today_d - timedelta(days=today_d.weekday())
            vendredi_d = lundi_d + timedelta(days=6)
            # Objectifs calendrier de la semaine
            df_obj_dash = pd.read_sql("""
                SELECT * FROM objectifs
                WHERE statut != 'Terminé' AND statut != 'Annulé'
                ORDER BY priorite DESC, date_cible ASC
                LIMIT 6
            """, conn_dash)
            # Aussi les todos équipe de la semaine
            sem_id_d = lundi_d.strftime("%Y-W%V")
            df_todo_dash = (_read_sql_impl("""
                SELECT * FROM todos WHERE semaine=? AND assignee='Tous' AND fait=0
                LIMIT 4
            """, conn_dash, params=[sem_id_d]) if _USE_SUPABASE and _read_sql_impl else pd.read_sql("""
                SELECT * FROM todos WHERE semaine=? AND assignee='Tous' AND fait=0
                LIMIT 4
            """, conn_dash, params=[sem_id_d]))
            conn_dash.close()

            if not df_obj_dash.empty:
                for _, obj in df_obj_dash.iterrows():
                    sc = {"En cours":"#395f30","À démarrer":"#c9800a","Terminé":"#888"}.get(obj.get("statut",""),"#888")
                    assignee = obj.get("assignee","Eastwood Studio") or "Eastwood Studio"
                    st.markdown(f"""
<div style="background:#fff;border:0.5px solid #ede3d3;border-left:3px solid {sc};
     padding:8px 12px;margin:4px 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="font-size:12px;font-weight:500;">{obj['titre']}</div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;">
        {obj.get('type_obj','')} · {assignee}
      </div>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:{sc};white-space:nowrap;margin-left:8px;">
      {obj.get('statut','')}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

            if not df_todo_dash.empty:
                st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:8px;color:#8a7968;text-transform:uppercase;letter-spacing:.15em;margin:10px 0 4px;">TODO équipe</div>', unsafe_allow_html=True)
                for _, td in df_todo_dash.iterrows():
                    st.markdown(f"""
<div style="border-left:2px solid #7b506f;padding:4px 10px;margin:3px 0;font-size:12px;">
  {td['titre']}
</div>""", unsafe_allow_html=True)

            if df_obj_dash.empty and df_todo_dash.empty:
                st.info("Aucun objectif cette semaine.")

        except Exception:
            st.info("Initialisez le Calendrier pour voir les objectifs ici.")

    with col_cmd:
        st.markdown('<div class="section-title">Commandes récentes</div>', unsafe_allow_html=True)
        df_cmd_dash = load_commandes().head(6)
        if not df_cmd_dash.empty:
            for _, row in df_cmd_dash.iterrows():
                steps = [row["matiere_premiere"],row["production"],row["pf_valide"],row["packaging"],row["envoi"]]
                done = sum(1 for v in steps if v)
                pct = int(done/5*100)
                bar_w = int(pct * 0.8)
                color_bar = "#2d6a4f" if pct==100 else "#c9800a" if pct>=60 else "#c1440e"
                st.markdown(f"""
<div style="background:#f7f5f0;border:1px solid #e0dbd2;border-radius:4px;padding:10px 14px;margin-bottom:6px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="font-size:13px;font-weight:500;color:#1a1a1a;">{row['prenom']} {row['nom']}</div>
    <div style="font-family:'DM Mono',monospace;font-size:10px;color:#888078;">{row['ref_article']}</div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;margin-top:6px;">
    <div style="flex:1;height:3px;background:#e0dbd2;border-radius:2px;">
      <div style="width:{pct}%;height:3px;background:{color_bar};border-radius:2px;"></div>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#aaa49a;">{pct}%</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── TODO & Objectifs semaine (compact) ───────────────────────────────────
    if TODO_MODULE:
        from todo_module import render_todo_widget, init_todo_db
        conn_todo = get_conn()
        init_todo_db(conn_todo)
        col_todo1, col_todo2 = st.columns(2)
        with col_todo1:
            st.markdown('<div class="section-title">Mes tâches cette semaine</div>', unsafe_allow_html=True)
            render_todo_widget(conn_todo,
                st.session_state.get("user_display","Jules"),
                st.session_state.get("user_role","superuser"),
                can, compact=True)
        conn_todo.close()

    # Alertes stock
    df_stk_dash = load_stock()
    reassort = df_stk_dash[df_stk_dash["besoin_reassort"]==1]
    if not reassort.empty:
        st.markdown('<div class="section-title">⚠ Réassort nécessaire</div>', unsafe_allow_html=True)
        cols_r = st.columns(len(reassort))
        for i, (_, row) in enumerate(reassort.iterrows()):
            with cols_r[i]:
                st.markdown(f"""
<div class="stat-card" style="border-left:3px solid #c9800a;">
  <div class="stat-num" style="font-size:20px;">{int(row['qte_stock'])}</div>
  <div class="stat-label">{row['description'][:20]}</div>
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:#aaa49a;margin-top:4px;">{row['localisation']}</div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: OPÉRATIONS
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "⚙️  Opérations":
    if not can("finance_read"):
        st.warning("Accès limité — vue résumée uniquement.")
        ventes2, achats2, res2, *_ = compute_kpis(df_all)
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("CA HT", fmt_eur(ventes2))
        with c2: st.metric("Charges HT", fmt_eur(achats2))
        with c3: st.metric("Résultat", fmt_eur(res2))
        st.stop()
    if OPERATIONS_MODULE:
        page_operations(can, DB_PATH, fmt_eur)
    else:
        st.error("Module opérations non chargé.")
# ══════════════════════════════════════════════════════════════════════════════
# PAGE: COMMANDES
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "📦  Commandes":
    st.markdown("### Commandes")

    # Nouveaux états
    ETATS_CMD = ["A produire", "En production", "En stock", "A envoyer", "En transit", "Fini", "Annulé"]
    ETAT_COLORS = {
        "A produire":    "#c1440e",
        "En production": "#c9800a",
        "En stock":      "#7b506f",
        "A envoyer":     "#185FA5",
        "En transit":    "#0F6E56",
        "Fini":          "#395f30",
        "Annulé":        "#888",
    }

    _tc = ["📋 Liste", "➕ Nouvelle commande", "📥 Importer CSV/Excel"] if can("commandes_write") else ["📋 Liste"]
    _oc = st.tabs(_tc)
    tab_cl = _oc[0]
    tab_ca = _oc[1] if can("commandes_write") else None
    tab_imp = _oc[2] if can("commandes_write") else None

    # ── LISTE ──────────────────────────────────────────────────────────────────
    with tab_cl:
        df_cmd = load_commandes()

        # Filtres
        fc1,fc2,fc3,fc4 = st.columns(4)
        with fc1:
            # Normaliser les états existants → nouveaux états
            f_etat = st.selectbox("État", ["Tous"] + ETATS_CMD)
        with fc2:
            f_type_cmd = st.selectbox("Type", ["Tous", "B2C — Retail", "B2B — Wholesale"])
        with fc3:
            f_prio = st.selectbox("Priorité", ["Toutes", "Urgente", "Haute", "Normal"])
        with fc4:
            f_srch = st.text_input("Recherche", placeholder="nom, réf, n° cmd...")

        if not df_cmd.empty:
            dfc = df_cmd.copy()
            if f_etat != "Tous":
                dfc = dfc[dfc["etat"]==f_etat]
            if f_type_cmd != "Tous":
                type_key = "B2C" if "B2C" in f_type_cmd else "B2B"
                if "type_cmd" in dfc.columns:
                    dfc = dfc[dfc["type_cmd"].fillna("B2C").str.startswith(type_key)]
            if f_prio != "Toutes":
                dfc = dfc[dfc["priorite"]==f_prio]
            if f_srch:
                dfc = dfc[dfc.apply(lambda r: f_srch.lower() in str(r).lower(), axis=1)]

        if df_cmd.empty or (not df_cmd.empty and dfc.empty):
            st.info("Aucune commande.")
        else:
            # KPIs
            k1,k2,k3,k4 = st.columns(4)
            with k1: st.metric("Total", len(dfc))
            with k2: st.metric("A produire", len(dfc[dfc["etat"]=="A produire"]) if not dfc.empty else 0)
            with k3: st.metric("En transit", len(dfc[dfc["etat"]=="En transit"]) if not dfc.empty else 0)
            with k4: st.metric("CA TTC", fmt_eur(dfc["prix_ttc"].sum()) if not dfc.empty else "—")

            for _, row in dfc.iterrows():
                steps = {"MP":row["matiere_premiere"],"Prod":row["production"],
                         "Validé":row["pf_valide"],"Pack":row["packaging"],"Envoi":row["envoi"]}
                step_cols_db = {"MP":"matiere_premiere","Prod":"production",
                                "Validé":"pf_valide","Pack":"packaging","Envoi":"envoi"}
                done = sum(1 for v in steps.values() if v)
                pct  = int(done/len(steps)*100)

                etat_val   = row.get("etat","") or ""
                etat_color = ETAT_COLORS.get(etat_val, "#888")
                type_cmd   = row.get("type_cmd","B2C") or "B2C"
                type_badge = "B2B" if "B2B" in str(type_cmd) else "B2C"
                type_c     = "#7b506f" if type_badge=="B2B" else "#395f30"

                title_str = (f"{'🟢' if pct==100 else '🟡' if pct>=60 else '🔴'} "
                             f"{row['num_commande'] or '—'} · "
                             f"{row['prenom']} {row['nom']} · "
                             f"{row['ref_article']} · "
                             f"{fmt_eur(row['prix_ttc'])} · "
                             f"{etat_val} [{type_badge}]")

                with st.expander(title_str):
                    ec1,ec2,ec3 = st.columns(3)
                    with ec1:
                        st.markdown(f"""
<div style="font-size:12px;line-height:2;">
  <strong>Date</strong> : {row['date_commande']}<br>
  <strong>Plateforme</strong> : {row.get('plateforme','')}<br>
  <strong>Réf.</strong> : {row['ref_article']} × {int(row['qte'])}
</div>""", unsafe_allow_html=True)
                    with ec2:
                        st.markdown(f"""
<div style="font-size:12px;line-height:2;">
  <strong>Email</strong> : {row.get('mail','—') or '—'}<br>
  <strong>Tél</strong> : {row.get('telephone','—') or '—'}<br>
  <strong>Adresse</strong> : {row.get('adresse','—') or '—'}
</div>""", unsafe_allow_html=True)
                    with ec3:
                        st.markdown(f"""
<div style="font-size:12px;line-height:2;">
  <span style="font-family:'DM Mono',monospace;color:{etat_color};font-weight:500;">● {etat_val}</span><br>
  <span style="background:{type_c}18;color:{type_c};font-family:'DM Mono',monospace;font-size:9px;padding:2px 7px;">{type_badge}</span><br>
  <strong>Envoi</strong> : {row.get('date_envoi','—') or '—'}
</div>""", unsafe_allow_html=True)

                    if row.get("notes"):
                        st.markdown(f'<div style="font-size:12px;color:#8a7968;margin:4px 0;">{row["notes"]}</div>', unsafe_allow_html=True)

                    # Checklist production
                    st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;color:#8a7968;text-transform:uppercase;letter-spacing:.15em;margin:10px 0 6px;">Avancement — {pct}%</div>', unsafe_allow_html=True)
                    if can("commandes_write"):
                        sc_cols = st.columns(len(steps))
                        for i, (label, val) in enumerate(steps.items()):
                            with sc_cols[i]:
                                new_val = st.checkbox(label, value=bool(val), key=f"chk_{row['id']}_{label}")
                                if new_val != bool(val):
                                    conn_upd = get_conn()
                                    conn_upd.execute(f"UPDATE commandes SET {step_cols_db[label]}=? WHERE id=?",
                                                     (int(new_val), row["id"]))
                                    # Auto-Fini si tout est coché
                                    row_check = conn_upd.execute(
                                        "SELECT matiere_premiere,production,pf_valide,packaging,envoi FROM commandes WHERE id=?",
                                        (row["id"],)).fetchone()
                                    if row_check and all(row_check):
                                        conn_upd.execute("UPDATE commandes SET etat='Fini' WHERE id=?", (row["id"],))
                                    conn_upd.commit(); conn_upd.close()
                                    st.rerun()


                    # Bouton supprimer commande (hors boucle colonnes)
                    if can("finance_write"):
                        if st.button("🗑 Supprimer cette commande", key=f"del_cmd_{row['id']}"):
                            conn_del = get_conn()
                            conn_del.execute("DELETE FROM commandes WHERE id=?", (row["id"],))
                            conn_del.commit(); conn_del.close()
                            st.rerun()
                    else:
                        sc_cols = st.columns(len(steps))
                        for i, (label, val) in enumerate(steps.items()):
                            with sc_cols[i]:
                                st.markdown(f"{'✅' if val else '⬜'} {label}")

                    # Modifier état + ligne complète
                    if can("commandes_write"):
                        with st.expander("✏️ Modifier cette commande"):
                            with st.form(f"edit_cmd_{row['id']}"):
                                mf1,mf2,mf3 = st.columns(3)
                                with mf1:
                                    m_etat  = st.selectbox("État", ETATS_CMD,
                                        index=ETATS_CMD.index(etat_val) if etat_val in ETATS_CMD else 0)
                                    m_prio  = st.selectbox("Priorité", ["Normal","Haute","Urgente"],
                                        index=["Normal","Haute","Urgente"].index(row.get("priorite","Normal"))
                                              if row.get("priorite") in ["Normal","Haute","Urgente"] else 0)
                                    m_type  = st.selectbox("Type", ["B2C — Retail","B2B — Wholesale"],
                                        index=1 if "B2B" in str(type_cmd) else 0)
                                with mf2:
                                    m_ref   = st.text_input("Réf. article", value=row.get("ref_article","") or "")
                                    m_qte   = st.number_input("Quantité", value=float(row.get("qte",1) or 1), min_value=0.0)
                                    m_ht    = st.number_input("Prix HT", value=float(row.get("prix_ht",0) or 0), min_value=0.0)
                                with mf3:
                                    m_plat  = st.text_input("Plateforme", value=row.get("plateforme","") or "")
                                    m_denv  = st.date_input("Date envoi",
                                        value=(_safe_date(row.get("date_envoi"))))
                                m_notes = st.text_area("Notes", value=row.get("notes","") or "", height=50)

                                if st.form_submit_button("💾 Enregistrer"):
                                    m_ttc = round(m_ht * 1.2 * m_qte, 2)
                                    m_type_key = "B2B" if "B2B" in m_type else "B2C"
                                    conn_m = get_conn()
                                    conn_m.execute("""UPDATE commandes SET
                                        etat=?,priorite=?,type_cmd=?,ref_article=?,
                                        qte=?,prix_ht=?,prix_ttc=?,prix_final=?,
                                        plateforme=?,date_envoi=?,notes=? WHERE id=?""",
                                        (m_etat, m_prio, m_type_key, m_ref,
                                         m_qte, m_ht, m_ttc, m_ttc,
                                         m_plat, str(m_denv), m_notes, row["id"]))
                                    conn_m.commit(); conn_m.close()
                                    st.success("✓ Commande mise à jour."); st.rerun()

    # ── NOUVELLE COMMANDE ──────────────────────────────────────────────────────
    if tab_ca is not None:
        with tab_ca:
            st.markdown('<div class="section-title">Nouvelle commande</div>', unsafe_allow_html=True)

            # SKU dynamique depuis produits
            conn_nc = get_conn()
            try:
                df_prods_nc = pd.read_sql(
                    "SELECT ref, nom, variant FROM products ORDER BY collection, nom", conn_nc)
                sku_opts_nc = ["— Saisie libre —"] + [
                    f"{r['ref']} — {r['nom']}{' / '+r['variant'] if r.get('variant') else ''}"
                    for _, r in df_prods_nc.iterrows()
                ]
            except Exception:
                sku_opts_nc = ["— Saisie libre —"]
            conn_nc.close()

            n1,n2,n3 = st.columns(3)
            with n1:
                priorite   = st.selectbox("Priorité", ["Normal","Haute","Urgente"])
                date_cmd   = st.date_input("Date commande", value=date.today())
                # Numéro auto CMD-EWS-XXXXXX
                # Déterminer type commande pour préfixe
                _cmd_type_sel = st.selectbox("Type commande", ["B2C — Retail","B2B — Wholesale"], key="new_cmd_type")
                _cmd_prefix = "CMD-EWS-WLS" if "B2B" in _cmd_type_sel else "CMD-EWS-RTL"
                _conn_nc2 = get_conn()
                try:
                    _last_cmd = _conn_nc2.execute(
                        f"SELECT MAX(num_commande) FROM commandes WHERE num_commande LIKE '{_cmd_prefix}-%'"
                    ).fetchone()
                    _last_n = 0
                    if _last_cmd and _last_cmd[0]:
                        try: _last_n = int(_last_cmd[0].split("-")[-1])
                        except: pass
                    _auto_num = f"{_cmd_prefix}-{_last_n+1:06d}"
                except Exception:
                    _auto_num = f"{_cmd_prefix}-000001"
                finally:
                    _conn_nc2.close()
                num_cmd = _auto_num
                st.info(f"N° commande : **{num_cmd}** (attribué automatiquement)")
                type_cmd_n = st.selectbox("Type", ["B2C — Retail","B2B — Wholesale"])
            with n2:
                sku_sel_nc = st.selectbox("SKU produit", sku_opts_nc)
                if sku_sel_nc == "— Saisie libre —":
                    ref_art = st.text_input("Réf. article libre")
                else:
                    ref_art = sku_sel_nc.split(" — ")[0]
                    st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:10px;color:#8a7968;background:#f0ece4;padding:4px 8px;margin-top:2px;">SKU : {ref_art}</div>', unsafe_allow_html=True)
                qte_cmd    = st.number_input("Quantité", min_value=1, value=1)
                plateforme = st.selectbox("Plateforme/Source", ["Hostinger","Instagram DM","Pop-up","Email","Showroom","Wholesale","Autre"])
            with n3:
                num_fac    = st.text_input("N° Facture")
                num_excl   = st.text_input("N° Exclusif")
                prix_ht_c  = st.number_input("Prix HT (€)", min_value=0.0, value=0.0)
                etat_n     = st.selectbox("État initial", ETATS_CMD)

            st.markdown(f'<div class="section-title">Client</div>', unsafe_allow_html=True)
            cl1,cl2,cl3 = st.columns(3)
            with cl1:
                prenom_ = st.text_input("Prénom")
                nom_    = st.text_input("Nom")
            with cl2:
                mail_   = st.text_input("Email")
                tel_    = st.text_input("Téléphone")
            with cl3:
                adr_    = st.text_input("Adresse")

            notes_     = st.text_area("Notes", height=60)
            prix_ttc_  = round(prix_ht_c * 1.2 * qte_cmd, 2)
            if prix_ht_c > 0:
                st.info(f"Prix TTC estimé : {fmt_eur(prix_ttc_)}")

            if st.button("✓ Enregistrer la commande", type="primary"):
                type_cmd_key = "B2B" if "B2B" in type_cmd_n else "B2C"
                conn_s = get_conn()
                conn_s.execute("""INSERT INTO commandes
                    (priorite,date_commande,num_commande,num_facture,num_exclusif,
                     ref_article,qte,prix_ht,vat,prix_ttc,prix_final,plateforme,
                     prenom,nom,mail,telephone,adresse,etat,notes,type_cmd)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (priorite, str(date_cmd), num_cmd, num_fac, num_excl,
                     ref_art, qte_cmd, prix_ht_c, 20.0, prix_ttc_, prix_ttc_,
                     plateforme, prenom_, nom_, mail_, tel_, adr_,
                     etat_n, notes_, type_cmd_key))
                if PRODUCTS_MODULE and ref_art:
                    try:
                        sync_from_commande(conn_s, ref_art, qte_cmd,
                            nom_, prenom_, mail_, tel_, adr_,
                            prix_ttc_, plateforme, num_cmd or "CMD")
                    except Exception: pass
                conn_s.commit(); conn_s.close()
                st.success("✓ Commande enregistrée.")
                st.rerun()

    # ── IMPORT CSV / EXCEL ─────────────────────────────────────────────────────
    if tab_imp is not None:
        with tab_imp:
            st.markdown('<div class="section-title">Import commandes depuis CSV ou Excel</div>', unsafe_allow_html=True)

            st.markdown("""
<div class="info-box">
Le fichier doit contenir les colonnes suivantes (même nom exactement) :<br>
<code>num_commande · date_commande · ref_article · qte · prix_ht · plateforme · prenom · nom · mail · telephone · adresse · etat · notes · type_cmd · priorite</code><br><br>
<strong>etat</strong> : A produire / En production / En stock / A envoyer / En transit / Fini / Annulé<br>
<strong>type_cmd</strong> : B2C ou B2B<br>
<strong>priorite</strong> : Normal / Haute / Urgente
</div>""", unsafe_allow_html=True)

            # Template téléchargeable
            template_data = pd.DataFrame([{
                "num_commande": "CMD-001",
                "date_commande": str(date.today()),
                "ref_article": "EWSJACKET-001A-TOB",
                "qte": 1,
                "prix_ht": 480.0,
                "plateforme": "Hostinger",
                "prenom": "Jean",
                "nom": "Dupont",
                "mail": "jean@example.com",
                "telephone": "+33 6 00 00 00 00",
                "adresse": "1 rue de la Paix, 75001 Paris",
                "etat": "A produire",
                "notes": "",
                "type_cmd": "B2C",
                "priorite": "Normal",
            }])
            buf_tmpl = io.BytesIO()
            template_data.to_csv(buf_tmpl, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇ Télécharger le template Excel",
                buf_tmpl.getvalue(),
                file_name="template_commandes_eastwood.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.markdown("---")
            imp_file = st.file_uploader("Choisir le fichier", type=["csv","xlsx","xls"])

            if imp_file:
                try:
                    if imp_file.name.lower().endswith(".csv"):
                        # Essayer différents séparateurs
                        try:
                            df_imp = pd.read_csv(imp_file, sep=",")
                        except Exception:
                            imp_file.seek(0)
                            df_imp = pd.read_csv(imp_file, sep=";")
                    else:
                        try:
                            df_imp = pd.read_excel(imp_file)
                        except Exception:
                            imp_file.seek(0)
                            df_imp = pd.read_csv(imp_file, sep=None, engine="python")

                    # Aperçu
                    st.markdown(f'<div class="section-title">Aperçu — {len(df_imp)} lignes</div>', unsafe_allow_html=True)
                    st.dataframe(df_imp.head(10), use_container_width=True, hide_index=True)

                    # Vérifier colonnes obligatoires
                    required = ["ref_article","qte","prix_ht"]
                    missing_cols = [c for c in required if c not in df_imp.columns]
                    if missing_cols:
                        st.error(f"Colonnes manquantes : {', '.join(missing_cols)}")
                    else:
                        imp_col1, imp_col2 = st.columns(2)
                        with imp_col1:
                            imp_type = st.selectbox("Type par défaut", ["B2C — Retail","B2B — Wholesale"], key="imp_type")
                        with imp_col2:
                            imp_etat = st.selectbox("État par défaut", ETATS_CMD, key="imp_etat")

                        if st.button("✓ Importer les commandes", type="primary"):
                            type_key_imp = "B2B" if "B2B" in imp_type else "B2C"
                            conn_imp = get_conn()
                            ok_count = 0
                            err_count = 0

                            for _, row_imp in df_imp.iterrows():
                                try:
                                    # Calculer TTC
                                    ht   = float(row_imp.get("prix_ht", 0) or 0)
                                    qty  = float(row_imp.get("qte", 1) or 1)
                                    ttc  = round(ht * 1.2 * qty, 2)
                                    etat_imp = str(row_imp.get("etat","")).strip() or imp_etat
                                    if etat_imp not in ETATS_CMD: etat_imp = imp_etat
                                    type_imp = str(row_imp.get("type_cmd","")).strip() or type_key_imp

                                    conn_imp.execute("""INSERT INTO commandes
                                        (priorite,date_commande,num_commande,ref_article,qte,
                                         prix_ht,vat,prix_ttc,prix_final,plateforme,
                                         prenom,nom,mail,telephone,adresse,etat,notes,type_cmd)
                                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                        (str(row_imp.get("priorite","Normal")),
                                         str(row_imp.get("date_commande", str(date.today()))),
                                         str(row_imp.get("num_commande","")).strip() or f"IMP-{ok_count+1}",
                                         str(row_imp.get("ref_article","")),
                                         qty, ht, 20.0, ttc, ttc,
                                         str(row_imp.get("plateforme","Import")),
                                         str(row_imp.get("prenom","")),
                                         str(row_imp.get("nom","")),
                                         str(row_imp.get("mail","")),
                                         str(row_imp.get("telephone","")),
                                         str(row_imp.get("adresse","")),
                                         etat_imp,
                                         str(row_imp.get("notes","")),
                                         type_imp))
                                    ok_count += 1
                                except Exception as e_imp:
                                    err_count += 1

                            conn_imp.commit(); conn_imp.close()
                            if ok_count:
                                st.success(f"✓ {ok_count} commande(s) importée(s).")
                            if err_count:
                                st.warning(f"⚠ {err_count} ligne(s) ignorée(s) (erreur de format).")
                            st.rerun()

                except Exception as e_read:
                    st.error(f"Erreur lecture fichier : {e_read}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PRODUITS
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "👕  Produits":
    if PRODUCTS_MODULE:
        page_produits(can, DB_PATH, fmt_eur, fmt_jpy)
    else:
        err_msg = globals().get("_PRODUCTS_ERR","fichier manquant")
        st.error(f"Module produits non chargé : {err_msg}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: STOCK
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "🗃️  Stock":
    st.markdown("### Stock & Inventaire")
    _ts = ["📋 Inventaire", "🏭 Stock Produits Finis", "🔬 Stock Samples", "🧵 Stock MP & Composants", "➕ Ajouter article"]
    _os = st.tabs(_ts)
    tab_si   = _os[0]
    tab_spf  = _os[1]
    tab_smp  = _os[2]
    tab_mp   = _os[3]
    tab_sa   = _os[4]

    with tab_si:
        df_stk = load_stock()
        # Exclure les samples de la vue principale
        df_stk_pf = df_stk[df_stk["type_produit"] != "Sample"] if not df_stk.empty else df_stk

        if df_stk_pf.empty:
            st.info("Aucun article en stock.")
        else:
            df_stk_pf = df_stk_pf.copy()
            df_stk_pf["valeur_totale"] = df_stk_pf["qte_stock"] * df_stk_pf["prix_unitaire"]
            val_totale = df_stk_pf["valeur_totale"].sum()

            # KPIs
            k1,k2,k3,k4,k5 = st.columns(5)
            with k1: st.metric("Valeur stock", fmt_eur(val_totale))
            with k2: st.metric("Références", len(df_stk_pf))
            with k3: st.metric("Produits finis", len(df_stk_pf[df_stk_pf["type_produit"]=="Produit fini"]))
            with k4: st.metric("Réassort", len(df_stk_pf[df_stk_pf["besoin_reassort"]==1]))
            with k5: st.metric("Samples", len(df_stk[df_stk["type_produit"]=="Sample"]) if not df_stk.empty else 0)

            # Filtres
            sf1,sf2,sf3 = st.columns(3)
            with sf1: f_type_stk = st.selectbox("Type", ["Tous"]+[t for t in TYPES_STOCK if t!="Sample"])
            with sf2: f_loc_stk  = st.selectbox("Localisation", ["Toutes"]+list(df_stk_pf["localisation"].dropna().unique()))
            with sf3: f_srch_stk = st.text_input("Recherche", placeholder="réf, description...", key="stk_srch")

            dfs = df_stk_pf.copy()
            if f_type_stk != "Tous":  dfs = dfs[dfs["type_produit"]==f_type_stk]
            if f_loc_stk != "Toutes": dfs = dfs[dfs["localisation"]==f_loc_stk]
            if f_srch_stk: dfs = dfs[dfs.apply(lambda r: f_srch_stk.lower() in str(r).lower(), axis=1)]

            TYPE_COLORS = {
                "Produit fini":    "#395f30",
                "Matière première":"#7b506f",
                "Composant":       "#8a7968",
                "Packaging":       "#185FA5",
                "Autre":           "#888",
            }

            for type_p, sub in dfs.groupby("type_produit", sort=False):
                tc = TYPE_COLORS.get(type_p, "#888")
                val_type = sub["valeur_totale"].sum()
                st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:9px;color:{tc};
     text-transform:uppercase;letter-spacing:.18em;border-bottom:1px solid #ede3d3;
     padding-bottom:5px;margin:14px 0 8px;display:flex;justify-content:space-between;">
  <span>{type_p}</span>
  <span>{fmt_eur(val_type)}</span>
</div>""", unsafe_allow_html=True)

                for _, item in sub.iterrows():
                    qte = float(item.get("qte_stock",0) or 0)
                    need_reassort = bool(item.get("besoin_reassort",0))
                    bar_c = "#c1440e" if need_reassort else (tc if qte > 5 else "#c9800a")
                    reassort_badge = f'<span style="background:#fdf6ec;color:#c1440e;font-family:\'DM Mono\',monospace;font-size:8px;padding:1px 6px;margin-left:6px;">⚠ RÉASSORT</span>' if need_reassort else ""

                    st.markdown(f"""
<div style="background:#fff;border:0.5px solid #ede3d3;border-left:3px solid {bar_c};
     padding:10px 14px;margin:4px 0;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-weight:500;font-size:13px;">{item['description']}{reassort_badge}</div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;">
      {item.get('ref','')} · {item.get('localisation','')}
    </div>
  </div>
  <div style="text-align:right;white-space:nowrap;margin-left:12px;">
    <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:{bar_c};">{int(qte)}</div>
    <div style="font-size:10px;color:#8a7968;">
      {f"Vendu : {int(item.get('qte_vendue',0))}" if item.get('qte_vendue') else ""}
      {f" · {fmt_eur(item.get('prix_unitaire',0))}/u" if item.get('prix_unitaire') else ""}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── STOCK PRODUITS FINIS ─────────────────────────────────────────────────────
    with tab_spf:
        df_stk_pf2 = load_stock()
        df_pf_only = df_stk_pf2[df_stk_pf2["type_produit"]=="Produit fini"] if not df_stk_pf2.empty else pd.DataFrame()
        st.markdown('<div class="section-title">Produits finis en stock</div>', unsafe_allow_html=True)
        if df_pf_only.empty:
            st.info("Aucun produit fini en stock. Ajoutez des articles depuis '➕ Ajouter article'.")
        else:
            k1,k2,k3 = st.columns(3)
            with k1: st.metric("Références PF", len(df_pf_only))
            with k2: st.metric("Valeur totale", fmt_eur((df_pf_only["qte_stock"]*df_pf_only["prix_unitaire"]).sum()))
            with k3: st.metric("Réassort", len(df_pf_only[df_pf_only["besoin_reassort"]==1]))
            for _, item in df_pf_only.iterrows():
                qte = int(item.get("qte_stock",0) or 0)
                need_r = bool(item.get("besoin_reassort",0))
                bc = "#c1440e" if need_r else ("#395f30" if qte > 0 else "#888")
                st.markdown(f"""
<div style="border:0.5px solid #ede3d3;border-left:3px solid {bc};
     padding:8px 14px;margin:3px 0;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-weight:500;font-size:13px;">{item['description']}</div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;">{item.get('ref','')}</div>
    {'<div style="font-size:10px;color:#c1440e;">⚠ Réassort nécessaire</div>' if need_r else ''}
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:22px;font-weight:500;color:{bc};">{qte}</div>
</div>""", unsafe_allow_html=True)

    # ── SAMPLES ──────────────────────────────────────────────────────────────────
    with tab_smp:
        df_stk_all = load_stock()
        df_samples = df_stk_all[df_stk_all["type_produit"]=="Sample"] if not df_stk_all.empty else pd.DataFrame()

        st.markdown(f"""
<div class="info-box">
Les samples sont différenciés des produits finis. Ils ne sont pas inclus dans la valeur de stock
ni dans le réassort. Ils sont listés ici séparément pour le suivi des pièces de développement.
</div>""", unsafe_allow_html=True)

        if df_samples.empty:
            st.info("Aucun sample enregistré.")
        else:
            st.metric("Samples en stock", len(df_samples))
            for _, item in df_samples.iterrows():
                qte = int(item.get("qte_stock",0) or 0)
                st.markdown(f"""
<div style="background:#fff;border:0.5px solid #ede3d3;border-left:3px solid #7b506f;
     padding:10px 14px;margin:4px 0;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-weight:500;font-size:13px;">{item['description']}</div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;">
      {item.get('ref','')} · {item.get('localisation','')}
    </div>
    {f'<div style="font-size:11px;color:#8a7968;">{item["notes"]}</div>' if item.get("notes") else ''}
  </div>
  <div style="text-align:right;">
    <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:#7b506f;">{qte}</div>
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:#8a7968;text-transform:uppercase;letter-spacing:.1em;">sample</div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── STOCK MP & COMPOSANTS ────────────────────────────────────────────────────
    with tab_mp:
        df_stk_all_mp = load_stock()
        df_mp_only = df_stk_all_mp[
            df_stk_all_mp["type_produit"].isin(["Matière première","Composant"])
        ] if not df_stk_all_mp.empty else pd.DataFrame()
        st.markdown('<div class="section-title">Matières premières & Composants</div>', unsafe_allow_html=True)
        if df_mp_only.empty:
            st.info("Aucune matière première ou composant en stock.")
        else:
            km1,km2,km3 = st.columns(3)
            with km1: st.metric("Références", len(df_mp_only))
            with km2: st.metric("Valeur totale", fmt_eur((df_mp_only["qte_stock"]*df_mp_only["prix_unitaire"]).sum()))
            with km3: st.metric("Réassort", len(df_mp_only[df_mp_only["besoin_reassort"]==1]))

            TYPE_MP_COLORS = {"Matière première":"#7b506f","Composant":"#8a7968"}
            for _, item in df_mp_only.iterrows():
                qte = float(item.get("qte_stock",0) or 0)
                need_r = bool(item.get("besoin_reassort",0))
                tc = TYPE_MP_COLORS.get(item.get("type_produit","Composant"),"#8a7968")
                bc = "#c1440e" if need_r else tc
                st.markdown(f"""
<div style="border:0.5px solid #ede3d3;border-left:3px solid {bc};
     padding:7px 12px;margin:3px 0;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-weight:500;font-size:12px;">{item['description']}</div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;">{item.get('ref','')} · {item.get('type_produit','')}</div>
    {'<div style="font-size:10px;color:#c1440e;">⚠ Réassort</div>' if need_r else ''}
  </div>
  <div style="text-align:right;">
    <div style="font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:{bc};">{int(qte)}</div>
    <div style="font-size:9px;color:#8a7968;">{item.get('localisation','')}</div>
  </div>
</div>""", unsafe_allow_html=True)

    with tab_sa:
            c1,c2,c3 = st.columns(3)
            with c1:
                ref_s   = st.text_input("Référence / SKU", placeholder="EWSJACKET-001A-TOB-T2")
                desc_s  = st.text_input("Description", placeholder="Waterfowl Jacket Tobacco T2")
                type_s  = st.selectbox("Type", TYPES_STOCK)
            with c2:
                loc_s      = st.selectbox("Localisation", LOCALISATIONS)
                qte_s      = st.number_input("Quantité en stock", min_value=0.0, value=0.0)
                prix_s     = st.number_input("Prix unitaire (€)", min_value=0.0, value=0.0, step=0.01)
            with c3:
                reassort_s = st.checkbox("Besoin réassort")
                notes_s    = st.text_area("Notes", height=90)

            if st.button("✓ Ajouter au stock", type="primary"):
                if not ref_s or not desc_s:
                    st.error("Référence et description obligatoires.")
                else:
                    conn = get_conn()
                    try:
                        conn.execute("""INSERT INTO stock
                            (description,ref,type_produit,localisation,qte_stock,prix_unitaire,besoin_reassort,notes)
                            VALUES (?,?,?,?,?,?,?,?)""",
                            (desc_s,ref_s,type_s,loc_s,qte_s,prix_s,int(reassort_s),notes_s))
                        conn.commit()
                        st.success("✓ Article ajouté.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Cette référence existe déjà.")
                    finally:
                        conn.close()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PACKAGING
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "📦  Packaging":
    st.markdown("### Packaging & Envois")
    conn_pkg = get_conn()
    df_pkg = (_read_sql_impl("""
        SELECT * FROM stock WHERE type_produit='Packaging'
        ORDER BY description
    """, conn_pkg) if _USE_SUPABASE and _read_sql_impl else pd.read_sql("""
        SELECT * FROM stock WHERE type_produit='Packaging'
        ORDER BY description
    """, conn_pkg))
    if not df_pkg.empty:
        st.markdown('<div class="section-title">Stock packaging</div>', unsafe_allow_html=True)
        p1,p2,p3 = st.columns(3)
        with p1: st.metric("Références", len(df_pkg))
        with p2: st.metric("Valeur totale", fmt_eur((df_pkg["qte_stock"]*df_pkg["prix_unitaire"]).sum()))
        with p3: st.metric("Réassort", len(df_pkg[df_pkg["besoin_reassort"]==1]))
        for _, item in df_pkg.iterrows():
            st.markdown(f"""
<div style="background:#fff;border:0.5px solid #ede3d3;padding:10px 14px;margin:5px 0;
     display:flex;justify-content:space-between;">
  <div>
    <div style="font-weight:500;font-size:13px;">{item['description']}</div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;">{item.get('ref','')}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'DM Mono',monospace;font-size:18px;font-weight:500;">{int(item['qte_stock'])}</div>
    <div style="font-size:10px;color:#8a7968;">unités · {fmt_eur(item['prix_unitaire'])} /u</div>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        st.info("Aucun item packaging. Ajoutez des articles avec le type 'Packaging' depuis Stock.")
    st.markdown("""
<div class="info-box">
Le packaging standard est automatiquement associé lors de la création de commandes.
Il peut être ajusté manuellement par collection dans la fiche produit.
</div>""", unsafe_allow_html=True)
    conn_pkg.close()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FINANCE & TVA
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "📋  Finance":
    st.markdown(f"### Finance · {sel_year}")

    if not can("finance_read"):
        st.warning("⛔ Accès non autorisé.")
        st.stop()

    _tabs_f = ["📊 KPI", "📋 Compte de résultat", "⚖️ Bilan"]
    tab_objs_f = st.tabs(_tabs_f)
    tab_kpi = tab_objs_f[0]
    tab_cr  = tab_objs_f[1]
    tab_bil = tab_objs_f[2]

    # Données communes
    df_cr = load_transactions(sel_year)
    ventes_cr  = df_cr[df_cr["type_op"]=="Vente"]["total_ht"].sum() if not df_cr.empty else 0
    df_achats  = df_cr[df_cr["type_op"].isin(["Achat","Achat perso"])] if not df_cr.empty else df_cr
    ch_by_cat  = df_achats.groupby("categorie")["total_ht"].sum() if not df_achats.empty else pd.Series(dtype=float)
    ch_by_mois = df_achats.groupby("mois")["total_ht"].sum() if not df_achats.empty else pd.Series(dtype=float)
    vt_by_mois = df_cr[df_cr["type_op"]=="Vente"].groupby("mois")["total_ht"].sum() if not df_cr.empty else pd.Series(dtype=float)

    charge_groups = {
        "Production":  ["Matière première","Composants","Confection / Production"],
        "Marketing":   ["Communication"],
        "Logistique":  ["Transport / Logistique","Stockage","Packaging"],
        "Structure":   ["Salaire","Logiciel & outils","Légal / Administratif","Autre frais"],
    }
    total_charges = sum(float(ch_by_cat.get(c,0)) for cats in charge_groups.values() for c in cats)
    res_net = ventes_cr - total_charges
    marge   = (res_net / ventes_cr * 100) if ventes_cr > 0 else 0
    tva_col = df_cr[df_cr["type_tva"]=="Collectée"]["tva"].sum() if not df_cr.empty else 0
    tva_ded = df_cr[df_cr["type_tva"]=="Déductible"]["tva"].sum() if not df_cr.empty else 0

    # ── KPI ────────────────────────────────────────────────────────────────────
    with tab_kpi:
        # Chiffres clés en tête
        k1,k2,k3,k4,k5 = st.columns(5)
        with k1: st.metric("CA HT", fmt_eur(ventes_cr))
        with k2: st.metric("Charges totales", fmt_eur(total_charges))
        with k3: st.metric("Résultat net", fmt_eur(res_net), delta="Bénéfice" if res_net>=0 else "Perte")
        with k4: st.metric("Marge nette", f"{marge:.1f}%")
        with k5: st.metric("TVA nette", fmt_eur(tva_col - tva_ded))

        # Détail charges par groupe
        cg1,cg2,cg3,cg4 = st.columns(4)
        for col_idx, (grp, cats) in enumerate(charge_groups.items()):
            grp_total = sum(float(ch_by_cat.get(c,0)) for c in cats)
            with [cg1,cg2,cg3,cg4][col_idx]:
                st.metric(grp, fmt_eur(grp_total))

        st.markdown("")

        # ── Chart 3 : Camembert répartition des charges ─────────────────────────
        pie_labels = []
        pie_values = []
        for grp, cats in charge_groups.items():
            v = sum(float(ch_by_cat.get(c,0)) for c in cats)
            if v > 0:
                pie_labels.append(grp)
                pie_values.append(round(v,2))

        if pie_values:
            st.markdown('<div class="section-title">Répartition des charges</div>', unsafe_allow_html=True)
            pie_colors = ["'#395f30'","'#7b506f'","'#8a7968'","'#d9c8ae'"]
            st.components.v1.html(f"""
<div style="display:flex;align-items:center;gap:24px;">
  <div style="position:relative;height:220px;width:220px;flex-shrink:0;">
    <canvas id="chartPie"></canvas>
  </div>
  <div id="pieLegend" style="font-family:'DM Mono',monospace;font-size:11px;color:#1a1a1a;line-height:2;"></div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
const total = {sum(pie_values)};
const chart = new Chart(document.getElementById('chartPie'), {{
  type: 'doughnut',
  data: {{
    labels: {pie_labels},
    datasets: [{{data:{pie_values},backgroundColor:[{','.join(pie_colors[:len(pie_values)])}],borderWidth:2,borderColor:'#f5f0e8'}}]
  }},
  options: {{
    responsive:false,
    plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:ctx=>` ${{ctx.label}} : ${{ctx.raw.toLocaleString('fr-FR')}} € (${{(ctx.raw/total*100).toFixed(1)}}%)`}}}}}}
  }}
}});
const leg = document.getElementById('pieLegend');
{pie_labels}.forEach((l,i)=>{{
  const pct = ({pie_values}[i]/total*100).toFixed(1);
  leg.innerHTML += `<div><span style="display:inline-block;width:10px;height:10px;background:{pie_colors[:len(pie_values)]}[i].replace(/'/g,'');margin-right:6px;"></span>${{l}} — ${{pct}}%</div>`;
}});
</script>""", height=320)



        # ── Chart 1 : Ventes vs Charges par mois (bar grouped) ─────────────────
        months_labels = [months_map.get(m,str(m)) for m in range(1,13)]
        ventes_by_month = [float(vt_by_mois.get(m,0)) for m in range(1,13)]
        charges_by_month = [float(ch_by_mois.get(m,0)) for m in range(1,13)]

        st.markdown('<div class="section-title">Ventes vs Charges par mois</div>', unsafe_allow_html=True)
        st.components.v1.html(f"""
<div style="position:relative;height:260px;">
<canvas id="chartMois"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
new Chart(document.getElementById('chartMois'), {{
  type: 'bar',
  data: {{
    labels: {months_labels},
    datasets: [
      {{label:'Ventes HT',data:{ventes_by_month},backgroundColor:'#395f3099',borderColor:'#395f30',borderWidth:1}},
      {{label:'Charges HT',data:{charges_by_month},backgroundColor:'#7b506f88',borderColor:'#7b506f',borderWidth:1}}
    ]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{position:'top',labels:{{font:{{family:'DM Mono',size:11}}}}}}}},
    scales:{{
      x:{{grid:{{color:'#ede3d311'}},ticks:{{font:{{family:'DM Mono',size:10}}}}}},
      y:{{grid:{{color:'#ede3d322'}},ticks:{{font:{{family:'DM Mono',size:10}},callback:v=>v.toLocaleString('fr-FR')+'€'}}}}
    }}
  }}
}});
</script>""", height=280)



        # ── Chart 2 : Résultat cumulé ────────────────────────────────────────────
        cumul = []
        running = 0
        for m in range(1,13):
            running += float(vt_by_mois.get(m,0)) - float(ch_by_mois.get(m,0))
            cumul.append(round(running, 2))
        colors_cumul = ["'#395f3099'" if v>=0 else "'#c1440e99'" for v in cumul]

        st.markdown('<div class="section-title">Résultat cumulé</div>', unsafe_allow_html=True)
        st.components.v1.html(f"""
<div style="position:relative;height:200px;">
<canvas id="chartCumul"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
new Chart(document.getElementById('chartCumul'), {{
  type: 'bar',
  data: {{
    labels: {months_labels},
    datasets: [{{
      label:'Résultat cumulé',
      data:{cumul},
      backgroundColor:[{','.join(colors_cumul)}],
      borderWidth:0
    }}]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{grid:{{color:'#ede3d311'}},ticks:{{font:{{family:'DM Mono',size:10}}}}}},
      y:{{grid:{{color:'#ede3d322'}},ticks:{{font:{{family:'DM Mono',size:10}},callback:v=>v.toLocaleString('fr-FR')+'€'}}}}
    }}
  }}
}});
</script>""", height=220)

    # ── COMPTE DE RÉSULTAT (sans charts) ───────────────────────────────────────
    with tab_cr:
        k1,k2,k3,k4 = st.columns(4)
        with k1: st.metric("CA HT", fmt_eur(ventes_cr))
        with k2: st.metric("Charges totales", fmt_eur(total_charges))
        with k3: st.metric("Résultat net", fmt_eur(res_net), delta="Bénéfice" if res_net>=0 else "Perte")
        with k4: st.metric("Marge nette", f"{marge:.1f}%")

        st.markdown('<div class="section-title">Détail charges</div>', unsafe_allow_html=True)
        col_cl, col_cr_inner = st.columns(2)
        with col_cl:
            for grp, cats in charge_groups.items():
                grp_total = sum(float(ch_by_cat.get(c,0)) for c in cats)
                with st.expander(f"{grp} — {fmt_eur(grp_total)}"):
                    for cat in cats:
                        val = float(ch_by_cat.get(cat,0))
                        if val > 0:
                            st.write(f"· {cat} : {fmt_eur(val)}")
            st.markdown(f"**Total charges : {fmt_eur(total_charges)}**")
        with col_cr_inner:
            st.write(f"**CA HT** : {fmt_eur(ventes_cr)}")
            tva_due = tva_col - tva_ded
            st.write(f"**TVA collectée** : {fmt_eur(tva_col)}")
            st.write(f"**TVA déductible** : {fmt_eur(tva_ded)}")
            st.write(f"**TVA due** : {fmt_eur(tva_due)}")
            st.markdown("---")
            icon = "🟢" if res_net >= 0 else "🔴"
            st.markdown(f"### {icon} Résultat : {fmt_eur(res_net)}")

        # Export
        if not df_cr.empty:
            buf_fin = io.BytesIO()
            df_cr.drop(columns=["facture_data"],errors="ignore").to_csv(buf_fin, index=False, encoding="utf-8-sig")
            st.download_button("⬇ Export CSV", buf_fin.getvalue(),
                file_name=f"finance_{sel_year}.csv",
                mime="text/csv")

    # ── BILAN ───────────────────────────────────────────────────────────────────
    with tab_bil:
        st.markdown('<div class="section-title">Bilan simplifié</div>', unsafe_allow_html=True)
        st.info("Vue synthétique — faire valider par votre expert-comptable.")
        df_stk = load_stock()
        val_stk = (df_stk["qte_stock"] * df_stk["prix_unitaire"]).sum() if not df_stk.empty else 0
        treso   = (df_cr[df_cr["type_op"]=="Vente"]["total_ttc"].sum()
                   - df_cr[df_cr["type_op"].isin(["Achat","Achat perso"])]["total_ttc"].sum()) if not df_cr.empty else 0

        c_l, c_r = st.columns(2)
        with c_l:
            st.markdown("**ACTIFS**")
            for k,v in [("Trésorerie estimée",max(treso,0)),("Stocks (valeur)",val_stk),("Créances clients",0)]:
                st.write(f"· {k} : {fmt_eur(v)}")
            st.markdown(f"**Total actif : {fmt_eur(max(treso,0)+val_stk)}**")
        with c_r:
            st.markdown("**PASSIFS**")
            tva_due_b = tva_col - tva_ded
            for k,v in [("TVA nette due",tva_due_b),("Résultat exercice",res_net)]:
                st.write(f"· {k} : {fmt_eur(v)}")
            st.markdown(f"**Total passif : {fmt_eur(tva_due_b+res_net)}**")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TVA (Jules uniquement)
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "🧾  TVA":
    if not can("tva_read"):
        st.error("⛔ Accès réservé à Jules.")
        st.stop()
    if TVA_MODULE:
        page_tva(can, DB_PATH, sel_year)
    else:
        st.error("Module TVA non chargé. Vérifiez que tva_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CONTACTS
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "👤  Contacts":
    if CONTACTS_MODULE:
        page_contacts(can, DB_PATH)
    else:
        st.error("Module contacts non chargé. Vérifiez que contacts_module.py est dans le même dossier.")
        # Fallback minimal
        st.markdown("### Contacts")
        df_ct = load_contacts()
        st.dataframe(df_ct, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CALENDRIER & OBJECTIFS
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "📅  Calendrier":
    if CALENDAR_MODULE:
        page_calendrier(can, DB_PATH)
    else:
        st.error("Module calendrier non chargé. Vérifiez que calendar_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MARKETING & MÉDIAS
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "📣  Marketing":
    if MARKETING_MODULE:
        page_marketing(can, DB_PATH)
    else:
        st.error("Module marketing non chargé. Vérifiez que marketing_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CRM COMMERCIAL
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "🤝  CRM Commercial":
    if CRM_MODULE:
        page_crm(can, DB_PATH)
    else:
        st.error("Module CRM non chargé. Vérifiez que crm_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: BALANCE INTERNE
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "⚖️  Balance interne":
    if BALANCE_MODULE:
        page_balance(can, DB_PATH)
    else:
        st.error("Module balance non chargé. Vérifiez que balance_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: COÛTS PRODUITS (Finance & Comptabilité)
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "💰  Coûts produits":
    if PRODUCTS_MODULE:
        page_couts_produits(can, DB_PATH, fmt_eur)
    else:
        err_msg = globals().get("_PRODUCTS_ERR","fichier manquant")
        st.error(f"Module produits non chargé : {err_msg}")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TODO & OBJECTIFS
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "✅  TODO & Objectifs":
    st.markdown("### TODO & Objectifs semaine")
    if TODO_MODULE:
        from todo_module import render_todo_widget, init_todo_db
        conn_todo = get_conn()
        init_todo_db(conn_todo)
        render_todo_widget(
            conn_todo,
            st.session_state.get("user_display","Jules"),
            st.session_state.get("user_role","superuser"),
            can,
            compact=False
        )
        conn_todo.close()
    else:
        st.error("Module TODO non chargé.")