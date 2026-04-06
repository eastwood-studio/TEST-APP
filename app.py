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
    from products_module import page_produits, init_products_db, sync_from_commande
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
  color:#888070!important;padding:2px 0;
}
[data-testid="stSidebar"] .stRadio label:hover{color:#d9c8ae!important;}

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
        ("Normal","2025-04-01","CMD-002","FAC-002","EW-0043","PANT-003",2,258.33,20.0,310.0,310.0,"Shopify","Léa","Martin","lea@gmail.fr","+33 6 12 34 56 78","12 rue de Rivoli, Paris",0,0,0,1,1,1,1,"2025-04-05","Livré","",0),
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
        ("Veste Miura Jacket","MIRA-001","Produit fini","Paris — Appartement Jules",5,0,4,420.0,0),
        ("Pantalon Kibo","PANT-003","Produit fini","Paris — Appartement Jules",8,0,2,310.0,0),
        ("Tissu Solotex (m)","MAT-TX-001","Matière première","Paris — Atelier Belleville",12,38,0,28.0,1),
        ("Étiquettes Fab. Fr.","COMP-ETQ-01","Composant","Paris — Atelier Belleville",480,20,0,0.35,0),
        ("Packaging Box L","PKG-BOX-L","Packaging","Paris — Appartement Jules",45,7,4,3.5,0),
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
TYPES_STOCK = ["Produit fini","Matière première","Composant","Packaging","Autre"]
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
    Synchronise automatiquement le stock quand une transaction est enregistrée.
    - Vente       → qte_vendue += quantite, qte_stock -= quantite
    - Achat/MP    → qte_stock += quantite
    - Utilisation → qte_utilisee += quantite, qte_stock -= quantite
    """
    if not ref_produit:
        return
    row = conn.execute("SELECT * FROM stock WHERE ref=?", (ref_produit,)).fetchone()
    if not row:
        return  # Pas de ligne stock pour cette ref, on ne crée pas automatiquement

    if type_op == "Vente":
        conn.execute("""UPDATE stock SET
            qte_vendue = qte_vendue + ?,
            qte_stock  = MAX(0, qte_stock - ?)
            WHERE ref=?""", (quantite, quantite, ref_produit))
    elif type_op in ("Achat", "Achat perso"):
        conn.execute("UPDATE stock SET qte_stock = qte_stock + ? WHERE ref=?",
                     (quantite, ref_produit))
    elif type_op == "Utilisation":
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
    st.markdown(f"""
<div style="padding:22px 0 14px;">
  <img src="data:image/svg+xml;base64,{logo_b64}" style="width:148px;"/>
</div>
<div style="height:1px;background:#1c1a17;margin-bottom:8px;"></div>""",
        unsafe_allow_html=True)

    # ── Navigation par grandes catégories ────────────────────────────────────
    # Toutes les pages dans un seul radio mais avec labels de section visuels
    st.markdown('<span class="nav-group-label">Général</span>', unsafe_allow_html=True)
    page = st.radio("Nav", [
        "🏠  Accueil",
    ], label_visibility="collapsed", key="nav_general")

    st.markdown('<span class="nav-group-label">Opérations & Finance</span>', unsafe_allow_html=True)
    page_ops = st.radio("Nav ops", [
        "⚙️  Opérations",
        "📦  Commandes",
        "📋  Finance",
        "🧾  TVA",
    ], label_visibility="collapsed", key="nav_ops")

    st.markdown('<span class="nav-group-label">Catalogue</span>', unsafe_allow_html=True)
    page_cat = st.radio("Nav cat", [
        "👕  Produits",
        "🗃️  Stock",
    ], label_visibility="collapsed", key="nav_cat")

    st.markdown('<span class="nav-group-label">Relations</span>', unsafe_allow_html=True)
    page_rel = st.radio("Nav rel", [
        "👤  Contacts",
        "🤝  CRM Commercial",
        "📣  Marketing",
    ], label_visibility="collapsed", key="nav_rel")

    st.markdown('<span class="nav-group-label">Équipe</span>', unsafe_allow_html=True)
    page_equipe = st.radio("Nav equipe", [
        "✅  TODO & Objectifs",
    ], label_visibility="collapsed", key="nav_equipe")

    st.markdown('<span class="nav-group-label">Finance avancée</span>', unsafe_allow_html=True)
    page_fin2 = st.radio("Nav fin2", [
        "⚖️  Balance interne",
    ], label_visibility="collapsed", key="nav_fin2")

    st.markdown('<span class="nav-group-label">Planification</span>', unsafe_allow_html=True)
    page_plan = st.radio("Nav plan", [
        "📅  Calendrier",
    ], label_visibility="collapsed", key="nav_plan")

    # Déterminer la page active (la dernière sélection change)
    # On utilise session_state pour tracker quelle catégorie a changé
    _candidates = {
        "nav_general": st.session_state.get("nav_general"),
        "nav_ops":     st.session_state.get("nav_ops"),
        "nav_cat":     st.session_state.get("nav_cat"),
        "nav_rel":     st.session_state.get("nav_rel"),
        "nav_plan":    st.session_state.get("nav_plan"),
        "nav_fin2":    st.session_state.get("nav_fin2"),
        "nav_equipe":  st.session_state.get("nav_equipe"),
    }
    # La page active = la valeur non-None du groupe qui a changé en dernier
    # On garde en session l'état précédent
    if "active_nav_group" not in st.session_state:
        st.session_state["active_nav_group"] = "nav_general"
        st.session_state["active_page"] = "🏠  Accueil"

    for group, val in _candidates.items():
        if val and val != st.session_state.get(f"_prev_{group}"):
            st.session_state["active_nav_group"] = group
            st.session_state["active_page"] = val
        st.session_state[f"_prev_{group}"] = val

    page = st.session_state.get("active_page", "🏠  Accueil")

    st.markdown("<div style='height:1px;background:#1c1a17;margin:14px 0 10px;'></div>",
                unsafe_allow_html=True)

    # ── Filtre année ──────────────────────────────────────────────────────────
    years = [2024, 2025, 2026]
    sel_year = st.selectbox("Année", years, index=years.index(2025),
                            label_visibility="visible")
    sel_month_label = st.selectbox("Mois", ["Tous"] + list(months_full.values()),
                                   label_visibility="visible")
    month_num = (None if sel_month_label == "Tous"
                 else list(months_full.keys())[list(months_full.values()).index(sel_month_label)])

    st.markdown("<div style='height:1px;background:#1c1a17;margin:14px 0 10px;'></div>",
                unsafe_allow_html=True)

    # ── Utilisateur ───────────────────────────────────────────────────────────
    role_label = {"superuser":"Super-utilisateur","ops":"Opérations","crm":"CRM"}.get(
        st.session_state["user_role"],"")
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
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;letter-spacing:.05em;">
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
                  "active_nav_group","active_page"] + [f"_prev_{g}" for g in
                  ["nav_general","nav_ops","nav_cat","nav_rel","nav_plan","nav_fin2","nav_equipe"]]:
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
if page == "🏠  Accueil":
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

    # 2 colonnes : agenda + commandes récentes
    col_ev, col_cmd = st.columns([1, 1])

    with col_ev:
        st.markdown('<div class="section-title">Agenda à venir</div>', unsafe_allow_html=True)
        for ev in future[1:6]:
            delta = (ev["date"] - now.date()).days
            color_map = {"fw":"#534AB7","drop":"#c9800a","meeting":"#0F6E56"}
            color = color_map.get(ev["type"],"#1a1a1a")
            label_type = {"fw":"Fashion Week","drop":"Drop","meeting":"Réunion"}.get(ev["type"],"Événement")
            st.markdown(f"""
<div class="event-card {ev['type']}">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:{color};">{label_type}</div>
      <div style="font-size:13px;font-weight:500;color:#1a1a1a;margin-top:2px;">{ev['label']}</div>
      <div style="font-size:11px;color:#888078;margin-top:1px;">{ev['detail']}</div>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#aaa49a;text-align:right;white-space:nowrap;margin-left:12px;">
      J-{delta}<br><span style="font-size:9px;">{ev['date'].strftime('%d %b')}</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        # Lien Google Meet réunion
        st.markdown("""
<div style="margin-top:8px;">
  <a href="https://meet.google.com/new" target="_blank"
     style="font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.08em;color:#0F6E56;text-decoration:none;text-transform:uppercase;">
    ↗ Créer un Google Meet
  </a>
</div>""", unsafe_allow_html=True)

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
elif page == "⚙️  Opérations":
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
elif page == "📦  Commandes":
    st.markdown("### Commandes")
    _tc = ["📋 Liste"]
    if can("commandes_write"): _tc.append("➕ Nouvelle commande")
    _oc = st.tabs(_tc)
    tab_cl, tab_ca = _oc[0], (_oc[1] if can("commandes_write") else None)

    with tab_cl:
        df_cmd = load_commandes()
        if df_cmd.empty:
            st.info("Aucune commande.")
        else:
            c1,c2 = st.columns(2)
            with c1:
                etats = ["Tous"] + df_cmd["etat"].dropna().unique().tolist()
                f_etat = st.selectbox("État", etats)
            with c2:
                f_srch = st.text_input("Recherche", placeholder="nom, réf, n° cmd...")
            dfc = df_cmd.copy()
            if f_etat != "Tous": dfc = dfc[dfc["etat"]==f_etat]
            if f_srch: dfc = dfc[dfc.apply(lambda r: f_srch.lower() in str(r).lower(), axis=1)]

            for _, row in dfc.iterrows():
                steps = {"MP":row["matiere_premiere"],"Prod":row["production"],
                         "Validé":row["pf_valide"],"Pack":row["packaging"],"Envoi":row["envoi"]}
                step_cols_db = {
                    "MP":"matiere_premiere","Prod":"production",
                    "Validé":"pf_valide","Pack":"packaging","Envoi":"envoi"
                }
                done = sum(1 for v in steps.values() if v)
                pct  = int(done/len(steps)*100)
                etat_color = {"Livré":"#395f30","En production":"#c9800a","En attente":"#c1440e",
                              "Prêt à envoyer":"#7b506f","Annulé":"#888"}.get(row["etat"],"#888")
                with st.expander(f"{'🟢' if pct==100 else '🟡' if pct>=60 else '🔴'} {row['num_commande'] or '—'} · {row['prenom']} {row['nom']} · {row['ref_article']} · {fmt_eur(row['prix_ttc'])}"):
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        st.write(f"**Date** : {row['date_commande']}")
                        st.write(f"**Plateforme** : {row['plateforme']}")
                        st.write(f"**Qté** : {row['qte']}")
                    with c2:
                        st.write(f"**Email** : {row['mail']}")
                        st.write(f"**Tél** : {row['telephone']}")
                        st.write(f"**Adresse** : {row['adresse']}")
                    with c3:
                        st.markdown(f"<span style='color:{etat_color};font-weight:500;'>● {row['etat']}</span>", unsafe_allow_html=True)
                        st.write(f"**Envoi** : {row['date_envoi'] or '—'}")
                        st.write(f"**Notes** : {row['notes'] or '—'}")

                    # ── Checklist cliquable ─────────────────────────────────
                    st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:#8a7968;margin:10px 0 6px;">Avancement production — {pct}%</div>', unsafe_allow_html=True)
                    if can("commandes_write"):
                        step_cols_ui = st.columns(len(steps))
                        for i, (label, val) in enumerate(steps.items()):
                            with step_cols_ui[i]:
                                new_val = st.checkbox(
                                    label, value=bool(val),
                                    key=f"chk_{row['id']}_{label}"
                                )
                                if new_val != bool(val):
                                    db_col = step_cols_db[label]
                                    conn_upd = get_conn()
                                    conn_upd.execute(
                                        f"UPDATE commandes SET {db_col}=? WHERE id=?",
                                        (int(new_val), row["id"]))
                                    conn_upd.commit(); conn_upd.close()
                                    st.rerun()
                    else:
                        step_cols_ui = st.columns(len(steps))
                        for i, (label, val) in enumerate(steps.items()):
                            with step_cols_ui[i]:
                                st.markdown(f"{'✅' if val else '⬜'} {label}")

                    if can("commandes_write"):
                        st.markdown("")
                        new_etat = st.selectbox(
                            "État", ["En attente","En production","Prêt à envoyer","Livré","Annulé"],
                            index=["En attente","En production","Prêt à envoyer","Livré","Annulé"].index(row["etat"])
                                  if row["etat"] in ["En attente","En production","Prêt à envoyer","Livré","Annulé"] else 0,
                            key=f"etat_{row['id']}")
                        if st.button("Mettre à jour état", key=f"upd_{row['id']}"):
                            conn_e = get_conn()
                            conn_e.execute("UPDATE commandes SET etat=? WHERE id=?",
                                           (new_etat, row["id"]))
                            conn_e.commit(); conn_e.close()
                            st.rerun()

    if tab_ca is not None:
        with tab_ca:
            st.markdown('<div class="section-title">Nouvelle commande</div>', unsafe_allow_html=True)
            c1,c2,c3 = st.columns(3)
            with c1:
                priorite  = st.selectbox("Priorité", ["Normal","Haute","Urgente"])
                date_cmd  = st.date_input("Date commande", value=date.today())
                num_cmd   = st.text_input("N° Commande", placeholder="CMD-00X")
            with c2:
                num_fac   = st.text_input("N° Facture", placeholder="FAC-00X")
                num_excl  = st.text_input("N° Exclusif", placeholder="EW-00XX")
                ref_art   = st.text_input("Réf. article", placeholder="MIRA-001")
            with c3:
                qte_cmd   = st.number_input("Quantité", min_value=1, value=1)
                prix_ht_c = st.number_input("Prix HT (€)", min_value=0.0, value=0.0)
                plateforme = st.selectbox("Plateforme", ["Shopify","Instagram DM","Pop-up","Email","Autre"])

            st.markdown("**Client**")
            c1,c2,c3 = st.columns(3)
            with c1: prenom_ = st.text_input("Prénom")
            with c2: nom_    = st.text_input("Nom")
            with c3: mail_   = st.text_input("Email")
            c4,c5 = st.columns(2)
            with c4: tel_ = st.text_input("Téléphone")
            with c5: adr_ = st.text_input("Adresse")

            etat_ = st.selectbox("État", ["En attente","En production","Prêt à envoyer","Livré","Annulé"])
            notes_ = st.text_area("Notes", height=60)
            prix_ttc_ = round(prix_ht_c * 1.2 * qte_cmd, 2)
            if prix_ht_c > 0:
                st.info(f"Prix TTC estimé : {fmt_eur(prix_ttc_)}")

            if st.button("✓ Enregistrer la commande"):
                conn = get_conn()
                conn.execute("""INSERT INTO commandes
                    (priorite,date_commande,num_commande,num_facture,num_exclusif,
                     ref_article,qte,prix_ht,vat,prix_ttc,prix_final,plateforme,
                     prenom,nom,mail,telephone,adresse,etat,notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (priorite,str(date_cmd),num_cmd,num_fac,num_excl,
                     ref_art,qte_cmd,prix_ht_c,20.0,prix_ttc_,prix_ttc_,
                     plateforme,prenom_,nom_,mail_,tel_,adr_,etat_,notes_))
                # Auto-sync : stock + contact client + transaction vente
                if PRODUCTS_MODULE and ref_art:
                    try:
                        sync_from_commande(
                            conn, ref_art, qte_cmd,
                            nom_, prenom_, mail_, tel_, adr_,
                            prix_ttc_, plateforme, num_cmd or "CMD")
                    except Exception:
                        pass
                conn.commit(); conn.close()
                st.success("✓ Commande enregistrée. Stock et contact mis à jour automatiquement.")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PRODUITS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👕  Produits":
    if PRODUCTS_MODULE:
        page_produits(can, DB_PATH, fmt_eur, fmt_jpy)
    else:
        st.error("Module produits non chargé. Vérifiez que products_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: STOCK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗃️  Stock":
    st.markdown("### Stock & Inventaire")
    _ts = ["📦 Inventaire"]
    if can("stock_write"): _ts.append("➕ Ajouter article")
    _os = st.tabs(_ts)
    tab_si, tab_sa = _os[0], (_os[1] if can("stock_write") else None)

    with tab_si:
        df_stk = load_stock()
        if df_stk.empty:
            st.info("Aucun article en stock.")
        else:
            df_stk["valeur_totale"] = df_stk["qte_stock"] * df_stk["prix_unitaire"]
            val_totale = df_stk["valeur_totale"].sum()

            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("Valeur totale", fmt_eur(val_totale))
            with c2: st.metric("Références", len(df_stk))
            with c3: st.metric("Réassort nécessaire", len(df_stk[df_stk["besoin_reassort"]==1]))
            with c4:
                locs = df_stk["localisation"].dropna().unique()
                st.metric("Sites de stockage", len(locs))

            # Filtre par type
            f_type_stk = st.selectbox("Filtrer par type", ["Tous"]+TYPES_STOCK)
            f_loc_stk  = st.selectbox("Filtrer par localisation", ["Toutes"]+list(df_stk["localisation"].dropna().unique()))

            dfs = df_stk.copy()
            if f_type_stk != "Tous":   dfs = dfs[dfs["type_produit"]==f_type_stk]
            if f_loc_stk != "Toutes":  dfs = dfs[dfs["localisation"]==f_loc_stk]

            for type_p in dfs["type_produit"].unique():
                st.markdown(f'<div class="section-title">{type_p}</div>', unsafe_allow_html=True)
                sub = dfs[dfs["type_produit"]==type_p].copy()
                sub["⚠"] = sub["besoin_reassort"].map({1:"⚠ Réassort",0:""})
                st.dataframe(sub[["ref","description","localisation","qte_stock","qte_utilisee",
                                   "qte_vendue","prix_unitaire","valeur_totale","⚠"]].rename(columns={
                    "ref":"Réf.","description":"Description","localisation":"Localisation",
                    "qte_stock":"Stock","qte_utilisee":"Utilisé","qte_vendue":"Vendu",
                    "prix_unitaire":"Prix unit.","valeur_totale":"Valeur"
                }), use_container_width=True, hide_index=True)

    if tab_sa is not None:
        with tab_sa:
            c1,c2,c3 = st.columns(3)
            with c1:
                ref_s   = st.text_input("Référence / SKU", placeholder="MIRA-001")
                desc_s  = st.text_input("Description", placeholder="Veste Miura Jacket")
                type_s  = st.selectbox("Type", TYPES_STOCK)
            with c2:
                loc_s      = st.selectbox("Localisation", LOCALISATIONS)
                qte_s      = st.number_input("Quantité en stock", min_value=0.0, value=0.0)
                prix_s     = st.number_input("Prix unitaire (€)", min_value=0.0, value=0.0, step=0.01)
            with c3:
                reassort_s = st.checkbox("Besoin réassort")
                notes_s    = st.text_area("Notes", height=90)

            if st.button("✓ Ajouter au stock"):
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
# PAGE: FINANCE & TVA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋  Finance":
    st.markdown(f"### Finance & TVA · {sel_year}")

    if not can("finance_read"):
        st.warning("⛔ Accès non autorisé.")
        st.stop()

    _tabs_f = ["📊 Compte de résultat","⚖️ Bilan"]
    tab_objs_f = st.tabs(_tabs_f)
    tab_cr   = tab_objs_f[0]
    tab_bil  = tab_objs_f[1]

    with tab_cr:
        df_cr = load_transactions(sel_year)
        ventes_cr  = df_cr[df_cr["type_op"]=="Vente"]["total_ht"].sum()
        ch_by_cat  = df_cr[df_cr["type_op"].isin(["Achat","Achat perso"])].groupby("categorie")["total_ht"].sum()
        ch_by_mois = df_cr[df_cr["type_op"].isin(["Achat","Achat perso"])].groupby("mois")["total_ht"].sum()
        vt_by_mois = df_cr[df_cr["type_op"]=="Vente"].groupby("mois")["total_ht"].sum()

        # KPIs
        charge_groups = {
            "Production":    ["Matière première","Composants","Confection / Production"],
            "Marketing":     ["Communication"],
            "Logistique":    ["Transport / Logistique","Stockage","Packaging"],
            "Structure":     ["Salaire","Logiciel & outils","Légal / Administratif","Autre frais"],
        }
        total_charges = sum(ch_by_cat.get(c,0) for cats in charge_groups.values() for c in cats)
        res_net = ventes_cr - total_charges
        marge   = (res_net / ventes_cr * 100) if ventes_cr > 0 else 0

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("CA HT", fmt_eur(ventes_cr))
        with c2: st.metric("Charges totales", fmt_eur(total_charges))
        with c3: st.metric("Résultat net", fmt_eur(res_net), delta="Bénéfice" if res_net>=0 else "Perte")
        with c4: st.metric("Marge nette", f"{marge:.1f}%")

        # Charts
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<div class="section-title">Charges par catégorie</div>', unsafe_allow_html=True)
            df_ch_plot = pd.DataFrame({"Catégorie":ch_by_cat.index,"Montant HT":ch_by_cat.values})
            st.bar_chart(df_ch_plot.set_index("Catégorie"), use_container_width=True)
        with col_r:
            st.markdown('<div class="section-title">Ventes vs Charges par mois</div>', unsafe_allow_html=True)
            all_mois = sorted(set(list(vt_by_mois.index) + list(ch_by_mois.index)))
            df_plot = pd.DataFrame({
                "Mois": [months_map.get(m,str(m)) for m in all_mois],
                "Ventes": [vt_by_mois.get(m,0) for m in all_mois],
                "Charges": [ch_by_mois.get(m,0) for m in all_mois],
            }).set_index("Mois")
            st.line_chart(df_plot, use_container_width=True)

        st.markdown('<div class="section-title">Détail des charges</div>', unsafe_allow_html=True)
        col_cl, col_cr = st.columns(2)
        with col_cl:
            st.markdown("**CHARGES**")
            for grp, cats in charge_groups.items():
                grp_total = sum(ch_by_cat.get(c,0) for c in cats)
                with st.expander(f"{grp} — {fmt_eur(grp_total)}"):
                    for cat in cats:
                        val = ch_by_cat.get(cat, 0)
                        if val > 0:
                            st.write(f"· {cat} : {fmt_eur(val)}")
            st.markdown(f"**Total charges : {fmt_eur(total_charges)}**")
        with col_cr:
            st.markdown("**PRODUITS**")
            st.write(f"· Ventes produits : {fmt_eur(ventes_cr)}")
            st.markdown(f"**Total produits : {fmt_eur(ventes_cr)}**")
            st.markdown("---")
            icon = "🟢" if res_net >= 0 else "🔴"
            st.markdown(f"### {icon} Résultat : {fmt_eur(res_net)}")

    with tab_bil:
        st.markdown('<div class="section-title">Bilan comptable simplifié</div>', unsafe_allow_html=True)
        st.info("Vue synthétique — faire valider par votre expert-comptable.")
        df_b   = load_transactions(sel_year)
        df_stk = load_stock()
        val_stk  = (df_stk["qte_stock"] * df_stk["prix_unitaire"]).sum()
        treso    = df_b[df_b["type_op"]=="Vente"]["total_ttc"].sum() - df_b[df_b["type_op"].isin(["Achat","Achat perso"])]["total_ttc"].sum()
        tva_c_b  = df_b[df_b["type_tva"]=="Collectée"]["tva"].sum()
        tva_d_b  = df_b[df_b["type_tva"]=="Déductible"]["tva"].sum()
        res_b    = ventes - achats

        c_l, c_r = st.columns(2)
        with c_l:
            st.markdown("**ACTIFS**")
            for k,v in [("Trésorerie estimée",max(treso,0)),("Stocks (valeur)",val_stk),("Créances clients",0)]:
                st.write(f"· {k} : {fmt_eur(v)}")
            st.markdown(f"**Total actif : {fmt_eur(max(treso,0)+val_stk)}**")
        with c_r:
            st.markdown("**PASSIFS**")
            for k,v in [("TVA nette due",tva_c_b-tva_d_b),("Résultat exercice",res_b)]:
                st.write(f"· {k} : {fmt_eur(v)}")
            st.markdown(f"**Total passif : {fmt_eur(tva_c_b-tva_d_b+res_b)}**")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TVA (Jules uniquement)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧾  TVA":
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
elif page == "👤  Contacts":
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
elif page == "📅  Calendrier":
    if CALENDAR_MODULE:
        page_calendrier(can, DB_PATH)
    else:
        st.error("Module calendrier non chargé. Vérifiez que calendar_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MARKETING & MÉDIAS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📣  Marketing":
    if MARKETING_MODULE:
        page_marketing(can, DB_PATH)
    else:
        st.error("Module marketing non chargé. Vérifiez que marketing_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CRM COMMERCIAL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤝  CRM Commercial":
    if CRM_MODULE:
        page_crm(can, DB_PATH)
    else:
        st.error("Module CRM non chargé. Vérifiez que crm_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: BALANCE INTERNE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚖️  Balance interne":
    if BALANCE_MODULE:
        page_balance(can, DB_PATH)
    else:
        st.error("Module balance non chargé. Vérifiez que balance_module.py est dans le même dossier.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TODO & OBJECTIFS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "✅  TODO & Objectifs":
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