import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import io
import os
import hashlib
import base64

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

LOGO_SVG = """<svg width="140" height="28" viewBox="0 0 140 28" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="8" width="3" height="12" fill="#f0ece4"/>
  <text font-family="'DM Mono',monospace" font-size="11" font-weight="500"
        letter-spacing="3" fill="#f0ece4" x="8" y="19">EASTWOOD</text>
  <text font-family="'DM Mono',monospace" font-size="7" font-weight="300"
        letter-spacing="5" fill="#6b6660" x="8" y="27">STUDIO</text>
</svg>"""

LOGO_SVG_DARK = """<svg width="140" height="28" viewBox="0 0 140 28" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="8" width="3" height="12" fill="#1a1a1a"/>
  <text font-family="'DM Mono',monospace" font-size="11" font-weight="500"
        letter-spacing="3" fill="#1a1a1a" x="8" y="19">EASTWOOD</text>
  <text font-family="'DM Mono',monospace" font-size="7" font-weight="300"
        letter-spacing="5" fill="#888078" x="8" y="27">STUDIO</text>
</svg>"""

def show_login_page():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');
html,[class*="css"]{font-family:'DM Sans',sans-serif;}
.main .block-container{max-width:400px!important;margin:0 auto;padding-top:10vh;}
[data-testid="stSidebar"]{display:none;}
.stTextInput>div>div>input{border:1px solid #e0dbd2!important;border-radius:2px!important;font-family:'DM Mono',monospace!important;font-size:13px!important;background:#faf8f4!important;}
.stButton>button{font-family:'DM Mono',monospace!important;font-size:11px!important;letter-spacing:.12em!important;text-transform:uppercase!important;background:#1a1a1a!important;color:#f0ece4!important;border:none!important;border-radius:2px!important;width:100%;padding:10px!important;margin-top:8px;}
</style>""", unsafe_allow_html=True)

    logo_b64 = base64.b64encode(LOGO_SVG_DARK.encode()).decode()
    st.markdown(f"""
<div style="text-align:center;margin-bottom:40px;">
  <img src="data:image/svg+xml;base64,{logo_b64}" style="width:160px;margin:0 auto 12px;display:block;"/>
  <div style="font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.18em;color:#aaa49a;text-transform:uppercase;">
    Gestion interne · Paris
  </div>
</div>
<div style="background:#f7f5f0;border:1px solid #e0dbd2;border-radius:4px;padding:28px 28px 20px;">
""", unsafe_allow_html=True)

    username = st.text_input("Identifiant", placeholder="jules / corentin / alexis", label_visibility="collapsed")
    password = st.text_input("Mot de passe", type="password", placeholder="Mot de passe", label_visibility="collapsed")
    if st.button("Connexion →"):
        if check_login(username, password):
            st.rerun()
        else:
            st.error("Identifiant ou mot de passe incorrect.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("""
<p style="text-align:center;font-family:'DM Mono',monospace;font-size:9px;color:#ccc;margin-top:28px;letter-spacing:.1em;">
EASTWOOD STUDIO © 2024 · homemade by Jules Léger
</p>""", unsafe_allow_html=True)

if not st.session_state.get("logged_in"):
    show_login_page()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG & CSS
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
[data-testid="stSidebar"]{background:#0d0d0d;border-right:1px solid #1a1a1a;}
[data-testid="stSidebar"] *{color:#c8c4bc!important;}
[data-testid="stSidebar"] .stRadio label{font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#5a5550!important;padding:3px 0;}
.section-title{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:#888078;border-bottom:1px solid #e8e4dc;padding-bottom:8px;margin:24px 0 14px;}
.main .block-container{background:#faf8f4;padding-top:1.5rem;}
.stButton>button{font-family:'DM Mono',monospace!important;font-size:11px!important;letter-spacing:.1em!important;text-transform:uppercase!important;background:#1a1a1a!important;color:#f0ece4!important;border:none!important;border-radius:2px!important;padding:8px 18px!important;}
.stButton>button:hover{background:#333!important;}
.stDataFrame{border:1px solid #e8e4dc!important;border-radius:4px!important;}
.alert-box{background:#fff8e8;border:1px solid #f0c040;border-left:3px solid #c9800a;border-radius:2px;padding:12px 16px;font-size:13px;color:#5a4500;margin:10px 0;}
.info-box{background:#f0f6ff;border:1px solid #b5d4f4;border-left:3px solid #378add;border-radius:2px;padding:12px 16px;font-size:13px;color:#0a3d6b;margin:10px 0;}
.event-card{background:#f7f5f0;border:1px solid #e0dbd2;border-left:3px solid #1a1a1a;border-radius:2px;padding:14px 18px;margin:8px 0;}
.event-card.drop{border-left-color:#c9800a;}
.event-card.fw{border-left-color:#533AB7;}
.event-card.meeting{border-left-color:#0F6E56;}
.stat-card{background:#f7f5f0;border:1px solid #e0dbd2;border-radius:4px;padding:18px;text-align:center;}
.stat-num{font-family:'DM Mono',monospace;font-size:28px;font-weight:500;color:#1a1a1a;line-height:1;}
.stat-label{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:#888078;margin-top:4px;}
.badge{display:inline-block;font-family:'DM Mono',monospace;font-size:10px;padding:2px 8px;border-radius:2px;}
.badge-vente{background:#d4edda;color:#1a5c2e;}
.badge-achat{background:#cce5ff;color:#0a3d6b;}
.badge-perso{background:#e8e4dc;color:#555;}
.devise-badge{background:#fff3cd;color:#7a5100;display:inline-block;font-family:'DM Mono',monospace;font-size:10px;padding:2px 6px;border-radius:2px;}
[data-testid="stMetricDelta"]{font-family:'DM Mono',monospace;font-size:11px;}
footer{visibility:hidden;}
</style>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
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
<div style="padding:20px 0 16px;">
  <img src="data:image/svg+xml;base64,{logo_b64}" style="width:140px;"/>
</div>
<div style="height:1px;background:#1e1e1e;margin-bottom:20px;"></div>""", unsafe_allow_html=True)

    page = st.radio("Nav", [
        "🏠  Accueil",
        "💳  Transactions",
        "📦  Commandes",
        "🗃️  Stock & Produits",
        "📋  Finance & TVA",
        "👤  Contacts",
    ], label_visibility="collapsed")

    st.markdown("<div style='height:1px;background:#1a1a1a;margin:16px 0;'></div>", unsafe_allow_html=True)

    years = [2024, 2025, 2026]
    sel_year = st.selectbox("Année", years, index=years.index(2025),
                            label_visibility="visible")
    sel_month_label = st.selectbox("Mois", ["Tous"] + list(months_full.values()),
                                   label_visibility="visible")
    month_num = None if sel_month_label == "Tous" else list(months_full.keys())[list(months_full.values()).index(sel_month_label)]

    st.markdown("<div style='height:1px;background:#1a1a1a;margin:16px 0;'></div>", unsafe_allow_html=True)

    role_label = {"superuser":"Super-utilisateur","ops":"Opérations","crm":"CRM"}.get(st.session_state["user_role"],"")
    initial = st.session_state.get("user_initial","??")
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:4px 0;">
  <div style="width:28px;height:28px;background:#2a2a2a;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'DM Mono',monospace;font-size:10px;color:#c8c4bc;flex-shrink:0;">{initial}</div>
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:11px;color:#f0ece4;">{st.session_state['user_display']}</div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#4a4540;letter-spacing:.05em;">{role_label}</div>
  </div>
</div>""", unsafe_allow_html=True)

    if st.button("Déconnexion"):
        for k in ["logged_in","username","user_display","user_role","user_initial"]:
            st.session_state.pop(k, None)
        st.rerun()

    st.markdown("""
<div style="position:absolute;bottom:16px;left:16px;right:16px;">
  <div style="font-family:'DM Mono',monospace;font-size:8px;color:#2a2a2a;letter-spacing:.08em;">
    EASTWOOD STUDIO © 2024<br>homemade by Jules Léger
  </div>
</div>""", unsafe_allow_html=True)

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
# PAGE: TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💳  Transactions":
    st.markdown(f"### Transactions · {sel_year}{' · '+sel_month_label if sel_month_label != 'Tous' else ''}")

    if not can("finance_read"):
        st.warning("Accès limité — vue résumée uniquement.")
        ventes2, achats2, res2, *_ = compute_kpis(df_all)
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("CA HT", fmt_eur(ventes2))
        with c2: st.metric("Charges HT", fmt_eur(achats2))
        with c3: st.metric("Résultat", fmt_eur(res2))
        st.stop()

    _tabs = ["📋 Historique","📁 Factures"]
    if can("finance_write"): _tabs.append("➕ Nouvelle opération")
    tab_objs = st.tabs(_tabs)
    tab_hist = tab_objs[0]
    tab_fac  = tab_objs[1]
    tab_add  = tab_objs[2] if can("finance_write") else None

    with tab_hist:
        if df_tx.empty:
            st.info("Aucune transaction sur cette période.")
        else:
            c1,c2,c3,c4 = st.columns(4)
            with c1: f_type = st.selectbox("Type", ["Tous"]+TYPES_OP, key="ft")
            with c2: f_cat  = st.selectbox("Catégorie", ["Toutes"]+CATEGORIES, key="fc")
            with c3: f_dev  = st.selectbox("Devise", ["Toutes"]+DEVISES, key="fd")
            with c4: f_tva  = st.selectbox("TVA", ["Tous"]+TYPES_TVA, key="fv")

            dff = df_tx.copy()
            if f_type != "Tous":   dff = dff[dff["type_op"]==f_type]
            if f_cat != "Toutes":  dff = dff[dff["categorie"]==f_cat]
            if f_dev != "Toutes":  dff = dff[dff["devise"]==f_dev]
            if f_tva != "Tous":    dff = dff[dff["type_tva"]==f_tva]

            cols_show = ["date_op","ref_produit","info_process","description","categorie",
                         "type_op","quantite","unite","total_ht","devise","type_tva","tva","payeur"]
            st.dataframe(dff[cols_show].rename(columns={
                "date_op":"Date","ref_produit":"SKU","info_process":"Article",
                "description":"Description","categorie":"Catégorie","type_op":"Type",
                "quantite":"Qté","unite":"Unité","total_ht":"Total HT","devise":"Devise",
                "type_tva":"TVA","tva":"Mnt TVA","payeur":"Payeur"
            }), use_container_width=True, hide_index=True)

            st.markdown("---")
            c1,c2,c3 = st.columns(3)
            with c1: st.metric("Total HT", fmt_eur(dff["total_ht"].sum()))
            with c2: st.metric("TVA", fmt_eur(dff["tva"].sum()))
            with c3: st.metric("Nb opérations", len(dff))

            buf = io.BytesIO()
            dff.drop(columns=["facture_data"],errors="ignore").to_excel(buf, index=False, engine="openpyxl")
            st.download_button("⬇ Export Excel", buf.getvalue(),
                file_name=f"transactions_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab_fac:
        st.markdown('<div class="section-title">Espace factures</div>', unsafe_allow_html=True)
        conn = get_conn()
        df_fac = pd.read_sql("""
            SELECT t.id, t.date_op, t.description, t.total_ht, t.type_op,
                   t.beneficiaire, t.facture_nom, t.facture_data
            FROM transactions t WHERE t.facture_data IS NOT NULL
            ORDER BY t.date_op DESC""", conn)
        conn.close()

        if df_fac.empty:
            st.info("Aucune facture enregistrée. Ajoutez-en via 'Nouvelle opération'.")
        else:
            f1,f2 = st.columns(2)
            with f1: ff_type = st.selectbox("Type", ["Tous","Vente","Achat"], key="ff_t")
            with f2: ff_search = st.text_input("Rechercher", placeholder="fournisseur, description...")
            df_filt = df_fac.copy()
            if ff_type != "Tous": df_filt = df_filt[df_filt["type_op"]==ff_type]
            if ff_search:
                mask = df_filt.apply(lambda r: ff_search.lower() in str(r).lower(), axis=1)
                df_filt = df_filt[mask]

            for _, row in df_filt.iterrows():
                col_i, col_d = st.columns([3,1])
                with col_i:
                    badge = "badge-vente" if row["type_op"]=="Vente" else "badge-achat"
                    st.markdown(f"""
<div style="padding:8px 0;border-bottom:1px solid #e8e4dc;">
  <span class="badge {badge}">{row['type_op']}</span>
  <span style="margin-left:8px;font-size:13px;font-weight:500;">{row['description'][:50]}</span>
  <span style="margin-left:8px;font-family:'DM Mono',monospace;font-size:11px;color:#888078;">{row['date_op']} · {fmt_eur(row['total_ht'])}</span><br>
  <span style="font-size:12px;color:#aaa49a;">{row['facture_nom'] or 'facture'}</span>
</div>""", unsafe_allow_html=True)
                with col_d:
                    if row["facture_data"] is not None:
                        st.download_button("⬇", data=bytes(row["facture_data"]),
                            file_name=row["facture_nom"] or f"facture_{row['id']}.pdf",
                            key=f"dl_fac_{row['id']}")

    if tab_add is not None:
        with tab_add:
            st.markdown('<div class="section-title">Nouvelle opération</div>', unsafe_allow_html=True)
            c1,c2,c3 = st.columns(3)
            with c1:
                date_op  = st.date_input("Date", value=date.today())
                type_op  = st.selectbox("Type", TYPES_OP)
            with c2:
                categorie    = st.selectbox("Catégorie", CATEGORIES)
                ref_produit  = st.text_input("Réf. SKU", placeholder="MIRA-001")
            with c3:
                info_process = st.text_input("Article / Process", placeholder="Veste Miura Jacket")
                devise       = st.selectbox("Devise", DEVISES)

            description = st.text_area("Description", height=72, placeholder="Détail de l'opération...")

            c4,c5,c6,c7 = st.columns(4)
            with c4: quantite      = st.number_input("Quantité", min_value=0.0, value=1.0, step=0.1)
            with c5: unite         = st.selectbox("Unité", ["Euros","Article","Mètre","Pièces","Kg","Heure","Lot"])
            with c6: prix_unitaire = st.number_input("Prix unit. HT", min_value=0.0, value=0.0, step=0.01)
            with c7: taux_change   = st.number_input("Taux change", min_value=0.0001, value=1.0, step=0.0001,
                                                      help="1 EUR = X devise. Ex: 1 EUR = 160 JPY → 0.00625")

            tva_sug  = suggest_tva(type_op, categorie, devise)
            type_tva = st.selectbox("Type TVA", TYPES_TVA, index=TYPES_TVA.index(tva_sug),
                                    help=f"Suggestion auto : {tva_sug}")

            total_ht_calc  = round(quantite * prix_unitaire, 2) if prix_unitaire > 0 else 0.0
            tva_rate       = 0.20 if type_tva in ("Collectée","Déductible","Autoliquidée") else 0.0
            tva_amt        = round(total_ht_calc * tva_rate, 2)
            total_ttc_calc = round(total_ht_calc + tva_amt, 2)
            montant_orig   = round(total_ht_calc / taux_change, 2) if taux_change > 0 else 0.0

            if total_ht_calc > 0:
                sym = DEVISE_SYMBOLES.get(devise, devise)
                st.markdown(f"""
<div class="info-box">
💡 Total HT : <strong>{fmt_eur(total_ht_calc)}</strong> · TVA ({type_tva}) : <strong>{fmt_eur(tva_amt)}</strong> · Total TTC : <strong>{fmt_eur(total_ttc_calc)}</strong>
{f'<br>Montant original : <strong>{montant_orig:,.0f} {sym}</strong>' if devise != "EUR" else ''}
</div>""", unsafe_allow_html=True)

            c8,c9 = st.columns(2)
            with c8:
                payeur       = st.selectbox("Payeur", PAYEURS)
                source       = st.text_input("Source / Contact", placeholder="Jim Jin +86...")
            with c9:
                beneficiaire = st.text_input("Bénéficiaire", placeholder="Atelier Belleville")
                info_comp    = st.text_input("Info complémentaire", placeholder="N°commande...")

            facture_file = st.file_uploader("📎 Facture (PDF, PNG, JPG)",
                                            type=["pdf","png","jpg","jpeg","webp"])

            if st.button("✓ Enregistrer l'opération"):
                if not description:
                    st.error("Description obligatoire.")
                else:
                    fac_data = facture_file.read() if facture_file else None
                    fac_nom  = facture_file.name if facture_file else None
                    conn = get_conn()
                    conn.execute("""INSERT INTO transactions
                        (annee,mois,date_op,ref_produit,info_process,description,categorie,type_op,
                         quantite,unite,prix_unitaire,type_tva,total_ht,total_ttc,tva,
                         devise,taux_change,montant_original,payeur,beneficiaire,source,info_complementaire,
                         facture_data,facture_nom)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (date_op.year, date_op.month, str(date_op),
                         ref_produit, info_process, description, categorie, type_op,
                         quantite, unite, prix_unitaire, type_tva,
                         total_ht_calc, total_ttc_calc, tva_amt,
                         devise, taux_change, montant_orig,
                         payeur, beneficiaire, source, info_comp,
                         fac_data, fac_nom))
                    conn.commit(); conn.close()
                    st.success("✓ Opération enregistrée.")
                    st.rerun()

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
                done = sum(1 for v in steps.values() if v)
                pct  = int(done/len(steps)*100)
                etat_color = {"Livré":"#2d6a4f","En production":"#c9800a","En attente":"#c1440e",
                              "Prêt à envoyer":"#185FA5","Annulé":"#888"}.get(row["etat"],"#888")
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

                    step_cols = st.columns(len(steps))
                    for i, (label, val) in enumerate(steps.items()):
                        with step_cols[i]:
                            st.markdown(f"{'✅' if val else '⬜'} {label}")

                    if can("commandes_write"):
                        new_etat = st.selectbox("Changer état", ["En attente","En production","Prêt à envoyer","Livré","Annulé"],
                                                index=["En attente","En production","Prêt à envoyer","Livré","Annulé"].index(row["etat"]) if row["etat"] in ["En attente","En production","Prêt à envoyer","Livré","Annulé"] else 0,
                                                key=f"etat_{row['id']}")
                        if st.button("Mettre à jour", key=f"upd_{row['id']}"):
                            conn = get_conn()
                            conn.execute("UPDATE commandes SET etat=? WHERE id=?", (new_etat, row["id"]))
                            conn.commit(); conn.close()
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
                conn.commit(); conn.close()
                st.success("✓ Commande enregistrée.")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: STOCK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗃️  Stock & Produits":
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
elif page == "📋  Finance & TVA":
    st.markdown(f"### Finance & TVA · {sel_year}")

    if not can("finance_read"):
        st.warning("⛔ Accès non autorisé.")
        st.stop()

    _tabs_f = ["📊 Compte de résultat","⚖️ Bilan"]
    if can("tva_read"): _tabs_f.append("🧾 TVA")
    tab_objs_f = st.tabs(_tabs_f)
    tab_cr   = tab_objs_f[0]
    tab_bil  = tab_objs_f[1]
    tab_tva  = tab_objs_f[2] if can("tva_read") else None

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

    if tab_tva is not None:
        with tab_tva:
            st.markdown('<div class="section-title">Déclarations TVA — Jules uniquement</div>', unsafe_allow_html=True)
            df_tva = load_transactions(sel_year)
            df_tva["trimestre"] = ((df_tva["mois"]-1)//3+1)

            st.markdown("#### Synthèse par trimestre")
            for q in sorted(df_tva["trimestre"].unique()):
                dq = df_tva[df_tva["trimestre"]==q]
                tva_c_q = dq[dq["type_tva"]=="Collectée"]["tva"].sum()
                tva_d_q = dq[dq["type_tva"]=="Déductible"]["tva"].sum()
                tva_a_q = dq[dq["type_tva"]=="Autoliquidée"]["tva"].sum()
                due_q   = tva_c_q - tva_d_q
                st.markdown(f"**T{q} {sel_year}**")
                c1,c2,c3,c4 = st.columns(4)
                with c1: st.metric("Collectée",   fmt_eur(tva_c_q))
                with c2: st.metric("Déductible",  fmt_eur(tva_d_q))
                with c3: st.metric("Autoliquidée",fmt_eur(tva_a_q))
                with c4: st.metric("Due",fmt_eur(due_q), delta="À payer" if due_q>0 else "Crédit")

            st.markdown("---")
            st.markdown('<div class="section-title">Détail opérations TVA</div>', unsafe_allow_html=True)
            df_tva_det = df_tva[df_tva["type_tva"]!="Aucun"][
                ["date_op","ref_produit","description","categorie","type_op","total_ht","type_tva","tva","devise"]
            ].rename(columns={
                "date_op":"Date","ref_produit":"SKU","description":"Description",
                "categorie":"Catégorie","type_op":"Type","total_ht":"HT","type_tva":"Type TVA",
                "tva":"TVA","devise":"Devise"
            })
            st.dataframe(df_tva_det, use_container_width=True, hide_index=True)

            buf_tva = io.BytesIO()
            df_tva_det.to_excel(buf_tva, index=False, engine="openpyxl")
            st.download_button("⬇ Export déclaration TVA", buf_tva.getvalue(),
                file_name=f"TVA_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.markdown("""
<div class="alert-box">
<strong>Règles TVA automatiques :</strong><br>
• <strong>Collectée</strong> — Ventes France (TVA 20%)<br>
• <strong>Déductible</strong> — Achats fournisseurs France<br>
• <strong>Autoliquidée</strong> — Achats hors UE / intracommunautaires<br>
• <strong>Aucun</strong> — Frais hors champ TVA (banque, INPI, perso)
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CONTACTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👤  Contacts":
    st.markdown("### Contacts")

    IMPORTANCE = ["Normal","Important","Prioritaire"]
    TYPES_CONTACT = ["Client","Fournisseur","Collaborateur","Modèle","Autre"]
    SOUS_TYPES = {
        "Client":        ["Fidèle","Ponctuel","Potentiel","F&F"],
        "Fournisseur":   ["Tissu","Composant","Packaging","Production","Logistique","Autre"],
        "Collaborateur": ["Atelier","Photographe","Graphiste","Communication","Prestataire","Autre"],
        "Modèle":        ["Femme","Homme","Non-binaire"],
        "Autre":         ["Partenaire","Presse","Investisseur","Autre"],
    }

    _tc2 = ["📋 Répertoire"]
    if can("contacts_add"): _tc2.append("➕ Ajouter")
    _oc2 = st.tabs(_tc2)
    tab_cr2 = _oc2[0]
    tab_ca2 = _oc2[1] if can("contacts_add") else None

    with tab_cr2:
        df_ct = load_contacts()
        if df_ct.empty:
            st.info("Aucun contact.")
        else:
            c1,c2,c3 = st.columns(3)
            with c1: f_tc = st.selectbox("Type", ["Tous"]+TYPES_CONTACT)
            with c2: f_imp = st.selectbox("Importance", ["Toutes","Normal","Important","Prioritaire"])
            with c3: f_srch_ct = st.text_input("Recherche", placeholder="nom, email, instagram...")

            dfc3 = df_ct.copy()
            if f_tc != "Tous":     dfc3 = dfc3[dfc3["type_contact"]==f_tc]
            if f_imp != "Toutes":  dfc3 = dfc3[dfc3["importance"]==f_imp]
            if f_srch_ct:
                dfc3 = dfc3[dfc3.apply(lambda r: f_srch_ct.lower() in str(r).lower(), axis=1)]

            emoji_map = {"Client":"🛍️","Fournisseur":"🏭","Collaborateur":"🤝","Modèle":"📸","Autre":"👤"}
            imp_color = {"Normal":"#888","Important":"#c9800a","Prioritaire":"#c1440e"}

            for _, row in dfc3.iterrows():
                emoji = emoji_map.get(row["type_contact"],"👤")
                imp_c = imp_color.get(row["importance"],"#888")
                with st.expander(f"{emoji} {row['nom']} {('· '+row['entreprise']) if row.get('entreprise') else ''} · {row.get('pays','—')} · {row.get('sous_type','')}"):
                    if can("contacts_edit"):
                        with st.form(key=f"ct_{row['id']}"):
                            e1,e2 = st.columns(2)
                            with e1:
                                e_type = st.selectbox("Type", TYPES_CONTACT,
                                    index=TYPES_CONTACT.index(row["type_contact"]) if row["type_contact"] in TYPES_CONTACT else 0,
                                    key=f"et_{row['id']}")
                                st_list = SOUS_TYPES.get(e_type, ["Autre"])
                                e_sous = st.selectbox("Sous-type", st_list,
                                    index=st_list.index(row["sous_type"]) if row.get("sous_type") in st_list else 0,
                                    key=f"es_{row['id']}")
                                e_nom  = st.text_input("Nom", value=row["nom"] or "", key=f"en_{row['id']}")
                                e_ent  = st.text_input("Entreprise", value=row.get("entreprise","") or "", key=f"ee_{row['id']}")
                                e_imp  = st.selectbox("Importance", IMPORTANCE,
                                    index=IMPORTANCE.index(row["importance"]) if row.get("importance") in IMPORTANCE else 0,
                                    key=f"ei_{row['id']}")
                            with e2:
                                e_mail = st.text_input("Email", value=row["email"] or "", key=f"em_{row['id']}")
                                e_tel  = st.text_input("Téléphone", value=row["telephone"] or "", key=f"etel_{row['id']}")
                                e_ig   = st.text_input("Instagram", value=row.get("instagram","") or "", key=f"eig_{row['id']}")
                                e_act  = st.text_input("Activité", value=row.get("activite","") or "", key=f"eact_{row['id']}")
                                pays_list = ["FR","JP","DE","IT","US","CN","GB","BE","ES","MX","KR","Autre"]
                                e_pays = st.selectbox("Pays", pays_list,
                                    index=pays_list.index(row["pays"]) if row.get("pays") in pays_list else 0,
                                    key=f"epays_{row['id']}")
                            e_adr   = st.text_input("Adresse", value=row["adresse"] or "", key=f"eadr_{row['id']}")
                            e_notes = st.text_area("Notes", value=row["notes"] or "", height=60, key=f"enotes_{row['id']}")

                            btn_c = st.columns([2,1]) if can("contacts_delete") else st.columns([1])
                            with btn_c[0]:
                                ok = st.form_submit_button("💾 Enregistrer")
                            del_ok = False
                            if can("contacts_delete") and len(btn_c)>1:
                                with btn_c[1]:
                                    del_ok = st.form_submit_button("🗑 Supprimer")

                            if ok:
                                conn = get_conn()
                                conn.execute("""UPDATE contacts SET type_contact=?,sous_type=?,nom=?,entreprise=?,
                                    email=?,telephone=?,instagram=?,activite=?,adresse=?,pays=?,importance=?,notes=?
                                    WHERE id=?""",
                                    (e_type,e_sous,e_nom,e_ent,e_mail,e_tel,e_ig,e_act,e_adr,e_pays,e_imp,e_notes,row["id"]))
                                conn.commit(); conn.close()
                                st.success("✓ Mis à jour."); st.rerun()
                            if del_ok:
                                conn = get_conn()
                                conn.execute("DELETE FROM contacts WHERE id=?", (row["id"],))
                                conn.commit(); conn.close()
                                st.success("Supprimé."); st.rerun()
                    else:
                        c1,c2 = st.columns(2)
                        with c1:
                            for label, key in [("Type","type_contact"),("Email","email"),("Tél","telephone"),("Instagram","instagram")]:
                                st.write(f"**{label}** : {row.get(key,'—')}")
                        with c2:
                            for label, key in [("Activité","activite"),("Adresse","adresse"),("Notes","notes")]:
                                st.write(f"**{label}** : {row.get(key,'—')}")

        # Export
        if not df_ct.empty:
            st.markdown("---")
            buf_ct = io.BytesIO()
            df_ct.drop(columns=["id","created_at"],errors="ignore").to_excel(buf_ct, index=False, engine="openpyxl")
            st.download_button("⬇ Export contacts (Excel / Brevo)", buf_ct.getvalue(),
                file_name="contacts_eastwood.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    if tab_ca2 is not None:
        with tab_ca2:
            c1,c2 = st.columns(2)
            with c1:
                ntype  = st.selectbox("Type", TYPES_CONTACT, key="ntype")
                nstype_list = SOUS_TYPES.get(ntype,["Autre"])
                nstype = st.selectbox("Sous-type", nstype_list, key="nstype")
                nnom   = st.text_input("Nom / Prénom")
                nent   = st.text_input("Entreprise")
                nimp   = st.selectbox("Importance", IMPORTANCE)
            with c2:
                nmail  = st.text_input("Email")
                ntel   = st.text_input("Téléphone")
                nig    = st.text_input("Instagram", placeholder="@handle")
                nact   = st.text_input("Activité")
                npays  = st.selectbox("Pays", ["FR","JP","DE","IT","US","CN","GB","BE","ES","MX","KR","Autre"])
            nadr   = st.text_input("Adresse postale")
            nnotes = st.text_area("Notes", height=72)

            if st.button("✓ Ajouter le contact"):
                if not nnom:
                    st.error("Nom obligatoire.")
                else:
                    conn = get_conn()
                    conn.execute("""INSERT INTO contacts
                        (type_contact,sous_type,nom,entreprise,email,telephone,instagram,activite,adresse,pays,importance,notes)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (ntype,nstype,nnom,nent,nmail,ntel,nig,nact,nadr,npays,nimp,nnotes))
                    conn.commit(); conn.close()
                    st.success("✓ Contact ajouté.")
                    st.rerun()
