import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import io
import os
import hashlib
import base64
import sys
sys.path.insert(0, "/home/claude")
try:
    from products_module import (page_produits, page_couts_produits, init_products_db, sync_from_commande, get_collections_dynamic, COST_SECTIONS, compute_cost_totals)
    PRODUCTS_MODULE = True
except ImportError:
    PRODUCTS_MODULE = False

try:
    from contacts_module import page_contacts
    CONTACTS_MODULE = True
except ImportError:
    CONTACTS_MODULE = False

try:
    from calendar_module import page_calendrier
    CALENDAR_MODULE = True
except ImportError:
    CALENDAR_MODULE = False

try:
    from marketing_module import page_marketing
    MARKETING_MODULE = True
except ImportError:
    MARKETING_MODULE = False

try:
    from tva_module import page_tva
    TVA_MODULE = True
except ImportError:
    TVA_MODULE = False

try:
    from operations_module import page_operations
    OPERATIONS_MODULE = True
except ImportError:
    OPERATIONS_MODULE = False

try:
    from crm_module import page_crm
    CRM_MODULE = True
except ImportError:
    CRM_MODULE = False

try:
    from todo_module import render_todo_widget, init_todo_db
    TODO_MODULE = True
except ImportError:
    TODO_MODULE = False

try:
    from balance_module import page_balance
    BALANCE_MODULE = True
except ImportError:
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
DB_PATH = "eastwood.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

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

    demo_cmd = [
        ("Haute","2025-03-10","CMD-001","FAC-001","EW-0042","MIRA-001",1,350.0,20.0,420.0,420.0,"Instagram DM","Yuki","Tanaka","yuki@mail.jp","+81 90 1234 5678","Shibuya, Tokyo",0,1,0,1,1,1,1,"2025-03-18","Livré","Client fidèle Tokyo",0),
        ("Normal","2025-04-01","CMD-002","FAC-002","EW-0043","PANT-003",2,258.33,20.0,310.0,310.0,"Hostinger","Léa","Martin","lea@gmail.fr","+33 6 12 34 56 78","12 rue de Rivoli, Paris",0,0,0,1,1,1,1,"2025-04-05","Livré","",0),
        ("Haute","2025-04-08","CMD-003","","EW-0044","MIRA-001",1,350.0,20.0,420.0,420.0,"Pop-up","Carlos","Reyes","carlos@studio.mx","+52 55 9876 5432","Ciudad de México",1,1,0,1,0,0,0,"","En production","Mesures sur commande",0),
    ]
    c.executemany("""INSERT INTO commandes
        (priorite,date_commande,num_commande,num_facture,num_exclusif,ref_article,qte,
         prix_ht,vat,prix_ttc,prix_final,plateforme,prenom,nom,mail,telephone,adresse,
         transporteur,mesures,matiere_premiere,production,pf_valide,packaging,envoi,
         date_envoi,etat,notes,fnf) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", demo_cmd)

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
DEVISES    = ["EUR","JPY","USD","GBP","CNY","CHF","KRW"]
DEVISE_SYMBOLES = {"EUR":"€","JPY":"¥","USD":"$","GBP":"£","CNY":"¥","CHF":"Fr","KRW":"₩"}
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
    df = pd.read_sql(q + " ORDER BY date_op DESC", conn, params=p)
    conn.close(); return df

def load_commandes():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM commandes ORDER BY date_commande DESC", conn)
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
    logo_b64 = base64.b64encode(LOGO_SVG.encode()).decode()
    _user_prenom = st.session_state.get("user_display","").split()[0] if st.session_state.get("user_display") else "—"
    st.markdown(f"""
<div style="padding:22px 0 10px;">
  <img src="data:image/svg+xml;base64,{logo_b64}" style="width:148px;"/>
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
    _sep_css = "[data-testid='stSidebar'] [data-testid='stRadio'] > div {gap:0;}"
    for _idx, _lbl in _NAV_GROUPS.items():
        _pad = "4px 0 5px" if _idx == 0 else "12px 0 5px"
        _sep_css += f"""
[data-testid="stSidebar"] [data-testid="stRadio"] label:nth-child({_idx+1})::before{{
  content:"{_lbl.upper()}";display:block;
  font-family:'DM Mono',monospace;font-size:8px;letter-spacing:.22em;
  color:#8a7968;padding:{_pad};pointer-events:none;}}"""

    # Style radio items : pas de bullet visible, spacing réduit
    _sep_css += """
[data-testid="stSidebar"] [data-testid="stRadio"] label{
  padding:2px 0!important;line-height:1.4!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label span:first-child{
  display:none!important;}"""

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
    # On stocke la clé de routage séparément
    _PAGE_KEY = page.split(" — ")[0].strip() if " — " in page else page

    st.markdown("<div style='height:1px;background:#1c1a17;margin:14px 0 10px;'></div>",
                unsafe_allow_html=True)

    # Filtre année : gardé en session mais pas affiché en sidebar (utilise 2026 par défaut)
    sel_year = 2026
    month_num = None

    # ── Utilisateur ───────────────────────────────────────────────────────────
    ROLE_DESC = {
        "superuser": "Co-founder & Directeur Stratégie",
        "ops":        "Co-founder, Logistique & Marketing",
        "crm":        "Gestion Image & Production",
    }
    role_label = ROLE_DESC.get(st.session_state["user_role"], "")
    initial = st.session_state.get("user_initial","??")
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:4px 0 10px;">
  <div style="width:28px;height:28px;background:#1c1a17;border:1px solid #2a2520;
       display:flex;align-items:center;justify-content:center;
       font-family:'DM Mono',monospace;font-size:10px;color:#d9c8ae;flex-shrink:0;">
    {initial}
  </div>
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#d9c8ae;">
      {st.session_state['user_display']}
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;letter-spacing:.03em;line-height:1.4;">
      {role_label}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Footer + déconnexion ──────────────────────────────────────────────────
    # Le footer "homemade by Jules Léger" est cliquable → déconnexion
    st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:8px;color:#3a3530;
     letter-spacing:.1em;line-height:1.8;padding-bottom:4px;">
  EASTWOOD STUDIO © 2024
</div>""", unsafe_allow_html=True)

    if st.button("homemade by Jules Léger", help="Cliquer pour se déconnecter",
                 key="logout_btn"):
        for k in ["logged_in","username","user_display","user_role","user_initial",
                  "active_page","nav_single"]:
            st.session_state.pop(k, None)
        st.rerun()

    # CSS du bouton footer (discret)
    st.markdown("""
<style>
div[data-testid="stSidebar"] div[data-testid="stButton"] button[key="logout_btn"],
div[data-testid="stSidebar"] button:has(+div .logout) {
  background:transparent!important;color:#3a3530!important;
  border:none!important;padding:0!important;font-size:8px!important;
  letter-spacing:.1em!important;text-transform:none!important;
  text-decoration:underline!important;cursor:pointer!important;
  font-family:'DM Mono',monospace!important;
}
div[data-testid="stSidebar"] div[data-testid="stButton"] button {
  background:transparent!important;color:#3a3530!important;
  border:none!important;padding:0 2px!important;font-size:8px!important;
  letter-spacing:.08em!important;text-transform:none!important;
  text-decoration:underline!important;
}
</style>""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────────────
df_tx  = load_transactions(sel_year, month_num)
df_all = load_transactions(sel_year)
ventes, achats, result, tva_c, tva_d, tva_due = compute_kpis(df_all)

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
            df_todo_dash = pd.read_sql("""
                SELECT * FROM todos WHERE semaine=? AND assignee='Tous' AND fait=0
                LIMIT 4
            """, conn_dash, params=[sem_id_d])
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
                                    conn_upd.commit(); conn_upd.close()
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
                                        value=date.fromisoformat(row["date_envoi"]) if row.get("date_envoi") else date.today())
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
                num_cmd    = st.text_input("N° Commande", placeholder="CMD-00X")
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
        st.error("Module produits non chargé. Vérifiez que products_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: STOCK
# ══════════════════════════════════════════════════════════════════════════════
elif _PAGE_KEY == "🗃️  Stock":
    st.markdown("### Stock & Inventaire")
    _ts = ["📦 Inventaire", "🔬 Samples"]
    if can("stock_write"): _ts.append("➕ Ajouter article")
    _os = st.tabs(_ts)
    tab_si  = _os[0]
    tab_smp = _os[1]
    tab_sa  = _os[2] if can("stock_write") else None

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

    if tab_sa is not None:
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
    df_pkg = pd.read_sql("""
        SELECT * FROM stock WHERE type_produit='Packaging'
        ORDER BY description
    """, conn_pkg)
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
        st.error("Module produits non chargé.")

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