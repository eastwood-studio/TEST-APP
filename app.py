import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import json
import io
import os

# ── Configuration ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Eastwood — Gestion",
    page_icon="🪡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;1,9..40,300&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d0d0d;
    border-right: 1px solid #1e1e1e;
}
[data-testid="stSidebar"] * {
    color: #c8c4bc !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6b6660 !important;
    padding: 4px 0;
}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {
    gap: 4px;
}

/* Header brand */
.brand-header {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f0ece4;
    padding: 24px 0 8px 0;
    border-bottom: 1px solid #1e1e1e;
    margin-bottom: 24px;
}
.brand-sub {
    font-size: 10px;
    color: #4a4540;
    letter-spacing: 0.1em;
    margin-top: 4px;
}

/* KPI Cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
}
.kpi-card {
    background: #f7f5f0;
    border: 1px solid #e8e4dc;
    border-radius: 4px;
    padding: 20px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: #1a1a1a;
}
.kpi-card.positive::before { background: #2d6a4f; }
.kpi-card.negative::before { background: #c1440e; }
.kpi-card.warning::before  { background: #c9800a; }
.kpi-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #888078;
    margin-bottom: 8px;
}
.kpi-value {
    font-family: 'DM Mono', monospace;
    font-size: 26px;
    font-weight: 500;
    color: #1a1a1a;
    line-height: 1;
}
.kpi-sub {
    font-size: 11px;
    color: #aaa49a;
    margin-top: 6px;
}

/* Section titles */
.section-title {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #888078;
    border-bottom: 1px solid #e8e4dc;
    padding-bottom: 8px;
    margin: 28px 0 16px 0;
}

/* Tables */
.stDataFrame {
    border: 1px solid #e8e4dc !important;
    border-radius: 4px !important;
}

/* Buttons */
.stButton > button {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    background: #1a1a1a;
    color: #f0ece4;
    border: none;
    border-radius: 2px;
    padding: 8px 20px;
    transition: background 0.15s;
}
.stButton > button:hover {
    background: #333;
    color: #f0ece4;
    border: none;
}

/* TVA badges */
.badge {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.08em;
    padding: 3px 8px;
    border-radius: 2px;
    font-weight: 500;
}
.badge-collectee  { background: #d4edda; color: #1a5c2e; }
.badge-deductible { background: #cce5ff; color: #0a3d6b; }
.badge-autoliq    { background: #fff3cd; color: #7a5100; }
.badge-aucun      { background: #e8e4dc; color: #666058; }

/* Alert box */
.alert-box {
    background: #fff8e8;
    border: 1px solid #f0c040;
    border-left: 3px solid #c9800a;
    border-radius: 2px;
    padding: 12px 16px;
    font-size: 13px;
    color: #5a4500;
    margin: 12px 0;
}

/* Page main bg */
.main .block-container {
    background: #faf8f4;
    padding-top: 2rem;
}

/* Form fields */
.stSelectbox, .stTextInput, .stNumberInput {
    font-family: 'DM Sans', sans-serif;
}

/* Metric delta */
[data-testid="stMetricDelta"] {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
}
</style>
""", unsafe_allow_html=True)

# ── Database ───────────────────────────────────────────────────────────────────
DB_PATH = "eastwood.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        annee INTEGER, mois INTEGER, date_op TEXT,
        ref_produit TEXT, info_process TEXT, description TEXT,
        categorie TEXT, type_op TEXT,
        quantite REAL, unite TEXT,
        prix_unitaire REAL, type_tva TEXT,
        total_ht REAL, total_ttc REAL, tva REAL,
        payeur TEXT, beneficiaire TEXT,
        source TEXT, info_complementaire TEXT, facture_url TEXT,
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
        transporteur INTEGER DEFAULT 0,
        mesures INTEGER DEFAULT 0,
        matiere_premiere INTEGER DEFAULT 0,
        production INTEGER DEFAULT 0,
        pf_valide INTEGER DEFAULT 0,
        packaging INTEGER DEFAULT 0,
        envoi INTEGER DEFAULT 0,
        date_envoi TEXT, etat TEXT, notes TEXT,
        fnf INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT, ref TEXT UNIQUE,
        type_produit TEXT,
        qte_stock REAL DEFAULT 0,
        qte_utilisee REAL DEFAULT 0,
        qte_vendue REAL DEFAULT 0,
        prix_unitaire REAL DEFAULT 0,
        besoin_reassort INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_contact TEXT,
        nom TEXT, entreprise TEXT, email TEXT, telephone TEXT,
        adresse TEXT, pays TEXT, notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Seed demo data si vide
    c.execute("SELECT COUNT(*) FROM transactions")
    if c.fetchone()[0] == 0:
        _seed_demo(c)

    conn.commit()
    conn.close()

def _seed_demo(c):
    demo_tx = [
        (2025, 3, "2025-03-02", "MIRA-001", "Veste Miura Jacket", "Achat tissu japonais SOLOTEX 50m", "Matière première", "Achat", 50, "Mètre", 28.0, "Déductible", 1400.0, 1680.0, 280.0, "Eastwood", "Atelier Soierie Lyon", "Jim Jin +86 133 9131 8965", "N°CMD 5960", ""),
        (2025, 3, "2025-03-05", "GENE", "Finance", "Abonnement Brévo e-mail marketing", "Logiciel & outils", "Achat", 1, "Euros", 49.0, "Déductible", 49.0, 58.8, 9.8, "Eastwood", "Brévo SAS", "Brévo", "INV-2025-0312", ""),
        (2025, 3, "2025-03-10", "MIRA-001", "Veste Miura Jacket", "Vente pop-up Japon — 3 pièces", "Facture", "Vente", 3, "Article", 420.0, "Aucun", 1260.0, 1260.0, 0.0, "Client JP", "Eastwood", "Pop-up Tokyo Shibuya", "N°Client 0002142722", ""),
        (2025, 3, "2025-03-12", "MIRA-001", "Shipping", "Envoi postal collection Tokyo → Berlin", "Transport / Logistique", "Achat", 1, "Euros", 185.0, "Déductible", 185.0, 222.0, 37.0, "Eastwood", "DHL Express", "DHL Business", "AWB 1234567890", ""),
        (2025, 3, "2025-03-15", "COMP-002", "Étiquettes", "Achat étiquettes 'Fabrication Française' x500", "Composants", "Achat", 500, "Pièces", 0.35, "Déductible", 175.0, 210.0, 35.0, "Eastwood", "Imprimerie Parisienne", "Manigance Paris", "", ""),
        (2025, 3, "2025-03-18", "GENE", "Shooting", "Shooting photo collection SS25 — studio Paris", "Communication", "Achat", 1, "Euros", 800.0, "Déductible", 800.0, 960.0, 160.0, "Jules", "Studio Bastille", "Studio Bastille 75011", "FACT-2025-089", ""),
        (2025, 3, "2025-03-20", "MIRA-001", "Confection", "Confection 10 vestes Miura — atelier Belleville", "Confection / Production", "Achat", 10, "Article", 95.0, "Déductible", 950.0, 1140.0, 190.0, "Eastwood", "Atelier Belleville", "Atelier des Créateurs 75020", "N°CMD 6012", ""),
        (2025, 4, "2025-04-01", "PANT-003", "Pantalon Kibo", "Vente en ligne — 2 pantalons", "Facture", "Vente", 2, "Article", 310.0, "Collectée", 620.0, 744.0, 124.0, "Client FR", "Eastwood", "Shopify Order #8821", "N°8821", ""),
        (2025, 4, "2025-04-03", "GENE", "Finance", "Frais bancaires Revolut Business — mars", "Autre frais", "Achat", 1, "Euros", 25.0, "Aucun", 25.0, 25.0, 0.0, "Eastwood", "Revolut Business", "Revolut Business", "", ""),
        (2025, 4, "2025-04-05", "GENE", "Légal", "Dépôt marque INPI — renouvellement", "Légal / Administratif", "Achat", 1, "Euros", 250.0, "Aucun", 250.0, 250.0, 0.0, "Eastwood", "INPI", "INPI France", "REF-INPI-2025-441", ""),
    ]
    c.executemany("""INSERT INTO transactions
        (annee,mois,date_op,ref_produit,info_process,description,categorie,type_op,
         quantite,unite,prix_unitaire,type_tva,total_ht,total_ttc,tva,
         payeur,beneficiaire,source,info_complementaire,facture_url)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", demo_tx)

    demo_cmd = [
        ("Haute", "2025-03-10", "CMD-001", "FAC-001", "EW-0042", "MIRA-001", 1, 350.0, 20.0, 420.0, 420.0, "Instagram DM", "Yuki", "Tanaka", "yuki@mail.jp", "+81 90 1234 5678", "Shibuya, Tokyo", 0, 1, 0, 1, 1, 1, 1, "2025-03-18", "Livré", "Client fidèle Tokyo", 0),
        ("Normal", "2025-04-01", "CMD-002", "FAC-002", "EW-0043", "PANT-003", 2, 258.33, 20.0, 310.0, 310.0, "Shopify", "Léa", "Martin", "lea@gmail.fr", "+33 6 12 34 56 78", "12 rue de Rivoli, Paris", 0, 0, 0, 1, 1, 1, 1, "2025-04-05", "Livré", "", 0),
        ("Haute", "2025-04-08", "CMD-003", "", "EW-0044", "MIRA-001", 1, 350.0, 20.0, 420.0, 420.0, "Pop-up", "Carlos", "Reyes", "carlos@studio.mx", "+52 55 9876 5432", "Ciudad de México", 1, 1, 0, 1, 0, 0, 0, "", "En production", "Mesures sur commande", 0),
    ]
    c.executemany("""INSERT INTO commandes
        (priorite,date_commande,num_commande,num_facture,num_exclusif,
         ref_article,qte,prix_ht,vat,prix_ttc,prix_final,plateforme,
         prenom,nom,mail,telephone,adresse,
         transporteur,mesures,matiere_premiere,production,pf_valide,packaging,envoi,
         date_envoi,etat,notes,fnf)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", demo_cmd)

    demo_stock = [
        ("Veste Miura Jacket", "MIRA-001", "Produit fini", 5, 0, 4, 420.0, 0),
        ("Pantalon Kibo", "PANT-003", "Produit fini", 8, 0, 2, 310.0, 0),
        ("Tissu Solotex (m)", "MAT-TX-001", "Matière première", 12, 38, 0, 28.0, 1),
        ("Étiquettes Fab. Fr.", "COMP-ETQ-01", "Composant", 480, 20, 0, 0.35, 0),
        ("Packaging Box L", "PKG-BOX-L", "Packaging", 45, 7, 4, 3.5, 0),
    ]
    c.executemany("""INSERT OR IGNORE INTO stock
        (description,ref,type_produit,qte_stock,qte_utilisee,qte_vendue,prix_unitaire,besoin_reassort)
        VALUES (?,?,?,?,?,?,?,?)""", demo_stock)

    demo_contacts = [
        ("Fournisseur", "Jim Jin", "Shanghai Textiles Co.", "jimjin@shanghaitex.cn", "+86 133 9131 8965", "Shanghai, Chine", "CN", "Tissu Solotex — délai 3 sem."),
        ("Atelier", "Atelier des Créateurs", "Atelier Belleville", "contact@atelierbell.fr", "+33 1 43 21 00 11", "47 rue de Belleville, 75020 Paris", "FR", "Confection — 10 pièces min."),
        ("Client", "Yuki Tanaka", "", "yuki@mail.jp", "+81 90 1234 5678", "Shibuya, Tokyo", "JP", "Client fidèle depuis 2024"),
        ("Prestataire", "Studio Bastille", "", "booking@studiobastille.fr", "+33 1 44 22 11 00", "28 rue de la Roquette, 75011 Paris", "FR", "Shooting photo — tarif journée 800€ HT"),
    ]
    c.executemany("""INSERT INTO contacts
        (type_contact,nom,entreprise,email,telephone,adresse,pays,notes)
        VALUES (?,?,?,?,?,?,?,?)""", demo_contacts)

init_db()

# ── Helpers ────────────────────────────────────────────────────────────────────
CATEGORIES = [
    "Matière première", "Composants", "Confection / Production",
    "Communication", "Transport / Logistique", "Stockage",
    "Salaire", "Autre frais", "Légal / Administratif",
    "Produit fini", "Facture", "Logiciel & outils", "Packaging",
]
TYPES_OP = ["Achat", "Vente", "Utilisation", "Achat perso"]
TYPES_TVA = ["Collectée", "Déductible", "Autoliquidée", "Aucun"]
PAYEURS = ["Eastwood", "Jules", "Corentin", "Alexis"]

TVA_RULES = {
    "Vente":       {"Facture": "Collectée", "default": "Collectée"},
    "Achat":       {"default": "Déductible", "Légal / Administratif": "Aucun", "Autre frais": "Aucun"},
    "Utilisation": {"default": "Aucun"},
    "Achat perso": {"default": "Aucun"},
}

def suggest_tva(type_op: str, categorie: str, pays_beneficiaire: str = "FR") -> str:
    if pays_beneficiaire not in ("FR", ""):
        return "Autoliquidée"
    rules = TVA_RULES.get(type_op, {})
    return rules.get(categorie, rules.get("default", "Aucun"))

def fmt_eur(v):
    if v is None: return "—"
    return f"{v:,.2f} €".replace(",", " ")

def load_transactions(year=None, month=None):
    conn = get_conn()
    q = "SELECT * FROM transactions WHERE 1=1"
    params = []
    if year:  q += " AND annee=?";  params.append(year)
    if month: q += " AND mois=?";   params.append(month)
    q += " ORDER BY date_op DESC"
    df = pd.read_sql(q, conn, params=params)
    conn.close()
    return df

def load_commandes():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM commandes ORDER BY date_commande DESC", conn)
    conn.close()
    return df

def load_stock():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM stock ORDER BY type_produit, description", conn)
    conn.close()
    return df

def load_contacts():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM contacts ORDER BY type_contact, nom", conn)
    conn.close()
    return df

def compute_kpis(df):
    ventes = df[df["type_op"] == "Vente"]["total_ht"].sum()
    achats = df[df["type_op"].isin(["Achat", "Achat perso"])]["total_ht"].sum()
    result = ventes - achats
    tva_c  = df[df["type_tva"] == "Collectée"]["tva"].sum()
    tva_d  = df[df["type_tva"] == "Déductible"]["tva"].sum()
    tva_due = tva_c - tva_d
    return ventes, achats, result, tva_c, tva_d, tva_due

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="brand-header">
        🪡 EASTWOOD<br>
        <span class="brand-sub">PARIS · GESTION</span>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("Navigation", [
        "📊 Dashboard",
        "💳 Transactions",
        "📦 Commandes",
        "🗃️ Stock",
        "📋 TVA & Comptabilité",
        "👤 Contacts",
    ], label_visibility="collapsed")

    st.markdown("---")
    years = [2023, 2024, 2025]
    sel_year = st.selectbox("Année", years, index=len(years)-1)
    months_map = {1:"Janvier",2:"Février",3:"Mars",4:"Avril",5:"Mai",6:"Juin",
                  7:"Juillet",8:"Août",9:"Septembre",10:"Octobre",11:"Novembre",12:"Décembre"}
    sel_month = st.selectbox("Mois (optionnel)", ["Tous"] + list(months_map.values()))
    month_num = None if sel_month == "Tous" else list(months_map.keys())[list(months_map.values()).index(sel_month)]

    st.markdown("---")
    st.markdown('<span style="font-family:\'DM Mono\',monospace;font-size:10px;color:#444;letter-spacing:0.1em;">EASTWOOD © 2025</span>', unsafe_allow_html=True)

# ── Load data ──────────────────────────────────────────────────────────────────
df_tx   = load_transactions(sel_year, month_num)
df_all  = load_transactions(sel_year)
ventes, achats, result, tva_c, tva_d, tva_due = compute_kpis(df_all)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown(f"### Dashboard · {sel_year}")

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Chiffre d'affaires HT", fmt_eur(ventes), delta=None)
    with col2:
        st.metric("Charges HT", fmt_eur(achats))
    with col3:
        delta_color = "normal" if result >= 0 else "inverse"
        st.metric("Résultat net", fmt_eur(result), delta=f"{'Bénéfice' if result >= 0 else 'Perte'}")
    with col4:
        st.metric("TVA nette due", fmt_eur(tva_due), delta=f"Collectée {fmt_eur(tva_c)}")

    # Charts
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-title">Charges par catégorie</div>', unsafe_allow_html=True)
        df_charges = df_all[df_all["type_op"].isin(["Achat","Achat perso"])].groupby("categorie")["total_ht"].sum().reset_index()
        df_charges = df_charges.sort_values("total_ht", ascending=False)
        if not df_charges.empty:
            st.bar_chart(df_charges.set_index("categorie")["total_ht"])
        else:
            st.info("Aucune charge enregistrée.")

    with col_b:
        st.markdown('<div class="section-title">Ventes par mois</div>', unsafe_allow_html=True)
        df_ventes_m = df_all[df_all["type_op"] == "Vente"].groupby("mois")["total_ht"].sum().reset_index()
        df_ventes_m["mois_label"] = df_ventes_m["mois"].map(months_map)
        if not df_ventes_m.empty:
            st.bar_chart(df_ventes_m.set_index("mois_label")["total_ht"])
        else:
            st.info("Aucune vente enregistrée.")

    # Commandes récentes
    st.markdown('<div class="section-title">Commandes récentes</div>', unsafe_allow_html=True)
    df_cmd = load_commandes().head(5)
    if not df_cmd.empty:
        cols_show = ["num_commande","date_commande","ref_article","prenom","nom","prix_ttc","etat"]
        st.dataframe(df_cmd[cols_show].rename(columns={
            "num_commande":"N° Commande","date_commande":"Date",
            "ref_article":"Réf.","prenom":"Prénom","nom":"Nom",
            "prix_ttc":"Prix TTC","etat":"État"
        }), use_container_width=True, hide_index=True)

    # Alertes stock
    df_stk = load_stock()
    reassort = df_stk[df_stk["besoin_reassort"] == 1]
    if not reassort.empty:
        st.markdown('<div class="section-title">⚠ Alertes réassort</div>', unsafe_allow_html=True)
        for _, row in reassort.iterrows():
            st.markdown(f'<div class="alert-box">📦 <strong>{row["description"]}</strong> ({row["ref"]}) — stock: {row["qte_stock"]} unités</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💳 Transactions":
    st.markdown(f"### Transactions · {sel_year}{' · '+sel_month if sel_month != 'Tous' else ''}")

    tab_list, tab_add = st.tabs(["📋 Historique", "➕ Nouvelle opération"])

    with tab_list:
        if df_tx.empty:
            st.info("Aucune transaction sur cette période.")
        else:
            # Filtres rapides
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                f_type = st.selectbox("Type", ["Tous"] + TYPES_OP, key="f_type")
            with col_f2:
                f_cat = st.selectbox("Catégorie", ["Toutes"] + CATEGORIES, key="f_cat")
            with col_f3:
                f_tva = st.selectbox("TVA", ["Tous"] + TYPES_TVA, key="f_tva")

            dff = df_tx.copy()
            if f_type != "Tous":   dff = dff[dff["type_op"] == f_type]
            if f_cat != "Toutes":  dff = dff[dff["categorie"] == f_cat]
            if f_tva != "Tous":    dff = dff[dff["type_tva"] == f_tva]

            cols_show = ["date_op","info_process","description","categorie","type_op","quantite","unite","total_ht","type_tva","tva","payeur"]
            st.dataframe(
                dff[cols_show].rename(columns={
                    "date_op":"Date","info_process":"Article / Process",
                    "description":"Description","categorie":"Catégorie",
                    "type_op":"Type","quantite":"Qté","unite":"Unité",
                    "total_ht":"Total HT","type_tva":"TVA","tva":"Montant TVA","payeur":"Payeur"
                }),
                use_container_width=True, hide_index=True
            )

            # Totaux filtrés
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total HT (sélection)", fmt_eur(dff["total_ht"].sum()))
            with c2: st.metric("TVA (sélection)", fmt_eur(dff["tva"].sum()))
            with c3: st.metric("Nb opérations", len(dff))

            # Export
            buf = io.BytesIO()
            dff.to_excel(buf, index=False, engine="openpyxl")
            st.download_button("⬇ Exporter Excel", buf.getvalue(), file_name=f"transactions_{sel_year}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab_add:
        st.markdown('<div class="section-title">Nouvelle opération</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            date_op = st.date_input("Date", value=date.today())
        with col2:
            type_op = st.selectbox("Type d'opération", TYPES_OP)
        with col3:
            categorie = st.selectbox("Catégorie", CATEGORIES)

        col4, col5 = st.columns(2)
        with col4:
            ref_produit  = st.text_input("Réf. produit / SKU", placeholder="ex: MIRA-001")
            info_process = st.text_input("Article / Process", placeholder="ex: Veste Miura Jacket")
        with col5:
            description  = st.text_area("Description", height=88, placeholder="Détail de l'opération...")

        col6, col7, col8 = st.columns(3)
        with col6:
            quantite = st.number_input("Quantité", min_value=0.0, value=1.0, step=0.1)
        with col7:
            unite = st.selectbox("Unité", ["Euros","Article","Mètre","Pièces","Kg","Heure","Lot"])
        with col8:
            prix_unitaire = st.number_input("Prix unitaire HT (€)", min_value=0.0, value=0.0, step=0.01)

        # TVA auto-suggérée
        tva_suggestion = suggest_tva(type_op, categorie)
        type_tva = st.selectbox("Type TVA", TYPES_TVA,
                                index=TYPES_TVA.index(tva_suggestion),
                                help=f"Suggestion auto : {tva_suggestion}")

        # Calculs auto
        total_ht  = round(quantite * prix_unitaire, 2) if prix_unitaire > 0 else 0.0
        tva_rate  = 0.20 if type_tva in ("Collectée","Déductible","Autoliquidée") else 0.0
        tva_amt   = round(total_ht * tva_rate, 2)
        total_ttc = round(total_ht + tva_amt, 2)

        if total_ht > 0:
            st.markdown(f"""
            <div class="alert-box" style="background:#f0f8ff;border-color:#3b82f6;color:#1a3a5c;">
            💡 Total HT : <strong>{fmt_eur(total_ht)}</strong> · 
            TVA ({type_tva}) : <strong>{fmt_eur(tva_amt)}</strong> · 
            Total TTC : <strong>{fmt_eur(total_ttc)}</strong>
            </div>
            """, unsafe_allow_html=True)

        col9, col10 = st.columns(2)
        with col9:
            payeur = st.selectbox("Payeur", PAYEURS)
        with col10:
            beneficiaire = st.text_input("Bénéficiaire", placeholder="ex: Atelier Belleville")

        source = st.text_input("Source / Contact", placeholder="ex: Jim Jin +86 133...")
        info_comp = st.text_input("Info complémentaire", placeholder="N°commande, N°client...")
        facture_url = st.text_input("Lien facture (Drive)", placeholder="https://drive.google.com/...")

        if st.button("✓ Enregistrer l'opération"):
            if not description:
                st.error("La description est obligatoire.")
            else:
                conn = get_conn()
                conn.execute("""INSERT INTO transactions
                    (annee,mois,date_op,ref_produit,info_process,description,
                     categorie,type_op,quantite,unite,prix_unitaire,type_tva,
                     total_ht,total_ttc,tva,payeur,beneficiaire,source,info_complementaire,facture_url)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (date_op.year, date_op.month, str(date_op),
                     ref_produit, info_process, description,
                     categorie, type_op, quantite, unite, prix_unitaire, type_tva,
                     total_ht, total_ttc, tva_amt, payeur, beneficiaire,
                     source, info_comp, facture_url))
                conn.commit()
                conn.close()
                st.success("✓ Opération enregistrée.")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: COMMANDES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📦 Commandes":
    st.markdown("### Commandes")

    tab_list2, tab_add2 = st.tabs(["📋 Liste", "➕ Nouvelle commande"])

    with tab_list2:
        df_cmd = load_commandes()
        if df_cmd.empty:
            st.info("Aucune commande.")
        else:
            # Filtres
            col1, col2 = st.columns(2)
            with col1:
                etats = ["Tous"] + df_cmd["etat"].dropna().unique().tolist()
                f_etat = st.selectbox("État", etats)
            with col2:
                f_search = st.text_input("Recherche (nom, réf, n° cmd...)")

            dfc = df_cmd.copy()
            if f_etat != "Tous":   dfc = dfc[dfc["etat"] == f_etat]
            if f_search:
                mask = dfc.apply(lambda r: f_search.lower() in str(r).lower(), axis=1)
                dfc = dfc[mask]

            # Checklist de production par commande
            for _, row in dfc.iterrows():
                steps = {
                    "Matière première": row["matiere_premiere"],
                    "Production":       row["production"],
                    "PF validé":        row["pf_valide"],
                    "Packaging":        row["packaging"],
                    "Envoi":            row["envoi"],
                }
                done = sum(1 for v in steps.values() if v)
                pct  = int(done/len(steps)*100)
                bar_color = "#2d6a4f" if pct == 100 else "#c9800a" if pct >= 60 else "#c1440e"

                with st.expander(f"{'🟢' if pct==100 else '🟡' if pct>=60 else '🔴'} {row['num_commande']} · {row['prenom']} {row['nom']} · {row['ref_article']} · {fmt_eur(row['prix_ttc'])} · {row['etat']}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.write(f"**Date** : {row['date_commande']}")
                        st.write(f"**Plateforme** : {row['plateforme']}")
                        st.write(f"**Qté** : {row['qte']}")
                    with c2:
                        st.write(f"**Email** : {row['mail']}")
                        st.write(f"**Tél** : {row['telephone']}")
                        st.write(f"**Adresse** : {row['adresse']}")
                    with c3:
                        st.write(f"**Envoi** : {row['date_envoi'] or '—'}")
                        st.write(f"**Notes** : {row['notes'] or '—'}")

                    # Progress
                    st.markdown(f"**Avancement production ({pct}%)**")
                    cols_steps = st.columns(len(steps))
                    for i, (label, val) in enumerate(steps.items()):
                        with cols_steps[i]:
                            st.markdown(f"{'✅' if val else '⬜'} {label}")

    with tab_add2:
        st.markdown('<div class="section-title">Nouvelle commande</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            priorite = st.selectbox("Priorité", ["Normal","Haute","Urgente"])
            date_cmd = st.date_input("Date commande", value=date.today())
            num_cmd  = st.text_input("N° Commande", placeholder="CMD-00X")
        with col2:
            num_fac   = st.text_input("N° Facture", placeholder="FAC-00X")
            num_excl  = st.text_input("N° Exclusif", placeholder="EW-00XX")
            ref_art   = st.text_input("Réf. article", placeholder="MIRA-001")
        with col3:
            qte_cmd  = st.number_input("Quantité", min_value=1, value=1)
            prix_ht_ = st.number_input("Prix HT (€)", min_value=0.0, value=0.0)
            plateforme = st.selectbox("Plateforme", ["Shopify","Instagram DM","Pop-up","Email","Autre"])

        st.markdown("**Client**")
        c1, c2, c3 = st.columns(3)
        with c1: prenom_ = st.text_input("Prénom")
        with c2: nom_    = st.text_input("Nom")
        with c3: mail_   = st.text_input("Email")
        c4, c5 = st.columns(2)
        with c4: tel_ = st.text_input("Téléphone")
        with c5: adr_ = st.text_input("Adresse")

        etat_ = st.selectbox("État", ["En attente","En production","Prêt à envoyer","Livré","Annulé"])
        notes_ = st.text_area("Notes", height=70)

        vat_pct = 0.20
        prix_ttc_ = round(prix_ht_ * (1 + vat_pct) * qte_cmd, 2)
        if prix_ht_ > 0:
            st.info(f"Prix TTC estimé : {fmt_eur(prix_ttc_)}")

        if st.button("✓ Enregistrer la commande"):
            conn = get_conn()
            conn.execute("""INSERT INTO commandes
                (priorite,date_commande,num_commande,num_facture,num_exclusif,
                 ref_article,qte,prix_ht,vat,prix_ttc,prix_final,plateforme,
                 prenom,nom,mail,telephone,adresse,etat,notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (priorite, str(date_cmd), num_cmd, num_fac, num_excl,
                 ref_art, qte_cmd, prix_ht_, vat_pct*100, prix_ttc_, prix_ttc_,
                 plateforme, prenom_, nom_, mail_, tel_, adr_, etat_, notes_))
            conn.commit()
            conn.close()
            st.success("✓ Commande enregistrée.")
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: STOCK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗃️ Stock":
    st.markdown("### Inventaire & Stock")

    tab_s1, tab_s2 = st.tabs(["📦 Inventaire", "➕ Ajouter article"])

    with tab_s1:
        df_stk = load_stock()
        if df_stk.empty:
            st.info("Aucun article en stock.")
        else:
            # Valeur totale stock
            df_stk["valeur_totale"] = df_stk["qte_stock"] * df_stk["prix_unitaire"]
            val_totale = df_stk["valeur_totale"].sum()

            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Valeur totale stock", fmt_eur(val_totale))
            with c2: st.metric("Nb références", len(df_stk))
            with c3: st.metric("Articles à réapprovisionner", len(df_stk[df_stk["besoin_reassort"]==1]))

            # Par type
            for type_p in df_stk["type_produit"].unique():
                st.markdown(f'<div class="section-title">{type_p}</div>', unsafe_allow_html=True)
                sub = df_stk[df_stk["type_produit"] == type_p].copy()
                sub["⚠"] = sub["besoin_reassort"].map({1:"⚠ Réassort", 0:""})
                cols_show = ["ref","description","qte_stock","qte_utilisee","qte_vendue","prix_unitaire","valeur_totale","⚠"]
                st.dataframe(sub[cols_show].rename(columns={
                    "ref":"Réf.","description":"Description",
                    "qte_stock":"Stock","qte_utilisee":"Utilisé","qte_vendue":"Vendu",
                    "prix_unitaire":"Prix unit.","valeur_totale":"Valeur"
                }), use_container_width=True, hide_index=True)

    with tab_s2:
        col1, col2, col3 = st.columns(3)
        with col1:
            ref_s   = st.text_input("Référence / SKU", placeholder="MIRA-001")
            desc_s  = st.text_input("Description", placeholder="Veste Miura Jacket")
        with col2:
            type_s  = st.selectbox("Type", ["Produit fini","Matière première","Composant","Packaging"])
            qte_s   = st.number_input("Quantité en stock", min_value=0.0, value=0.0)
        with col3:
            prix_s  = st.number_input("Prix unitaire (€)", min_value=0.0, value=0.0, step=0.01)
            reassort_s = st.checkbox("Besoin réassort")

        if st.button("✓ Ajouter au stock"):
            if not ref_s or not desc_s:
                st.error("Référence et description obligatoires.")
            else:
                conn = get_conn()
                try:
                    conn.execute("""INSERT INTO stock (description,ref,type_produit,qte_stock,prix_unitaire,besoin_reassort)
                        VALUES (?,?,?,?,?,?)""", (desc_s, ref_s, type_s, qte_s, prix_s, int(reassort_s)))
                    conn.commit()
                    st.success("✓ Article ajouté.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Cette référence existe déjà.")
                finally:
                    conn.close()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TVA & COMPTABILITÉ
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 TVA & Comptabilité":
    st.markdown(f"### TVA & Comptabilité · {sel_year}")

    tab_tva, tab_cr, tab_bilan = st.tabs(["🧾 TVA", "📊 Compte de résultat", "⚖️ Bilan"])

    with tab_tva:
        st.markdown('<div class="section-title">Synthèse TVA annuelle</div>', unsafe_allow_html=True)

        df_tva = load_transactions(sel_year)

        # Par trimestre
        df_tva["trimestre"] = ((df_tva["mois"] - 1) // 3 + 1)
        for q in sorted(df_tva["trimestre"].unique()):
            dq = df_tva[df_tva["trimestre"] == q]
            tva_c_q = dq[dq["type_tva"]=="Collectée"]["tva"].sum()
            tva_d_q = dq[dq["type_tva"]=="Déductible"]["tva"].sum()
            tva_a_q = dq[dq["type_tva"]=="Autoliquidée"]["tva"].sum()
            due_q   = tva_c_q - tva_d_q

            st.markdown(f"**T{q} {sel_year}**")
            c1,c2,c3,c4 = st.columns(4)
            with c1: st.metric("TVA collectée",   fmt_eur(tva_c_q))
            with c2: st.metric("TVA déductible",  fmt_eur(tva_d_q))
            with c3: st.metric("TVA autoliquidée",fmt_eur(tva_a_q))
            with c4:
                color = "normal" if due_q >= 0 else "inverse"
                st.metric("TVA due",fmt_eur(due_q), delta="À payer" if due_q > 0 else "Crédit TVA")

        st.markdown("---")
        st.markdown('<div class="section-title">Détail par opération</div>', unsafe_allow_html=True)

        df_tva_det = df_tva[df_tva["type_tva"] != "Aucun"][
            ["date_op","description","categorie","type_op","total_ht","type_tva","tva"]
        ].rename(columns={
            "date_op":"Date","description":"Description","categorie":"Catégorie",
            "type_op":"Type","total_ht":"HT","type_tva":"Type TVA","tva":"TVA"
        })
        st.dataframe(df_tva_det, use_container_width=True, hide_index=True)

        # Export TVA
        buf2 = io.BytesIO()
        df_tva_det.to_excel(buf2, index=False, engine="openpyxl")
        st.download_button("⬇ Exporter déclaration TVA", buf2.getvalue(),
                           file_name=f"TVA_{sel_year}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("""
        <div class="alert-box">
        ℹ️ <strong>Règles TVA appliquées automatiquement :</strong><br>
        • <strong>Collectée</strong> — Ventes à des clients français (TVA 20%)<br>
        • <strong>Déductible</strong> — Achats auprès de fournisseurs français<br>
        • <strong>Autoliquidée</strong> — Achats intracommunautaires / hors UE (auto-déclarée)<br>
        • <strong>Aucun</strong> — Frais hors champ TVA (frais bancaires, INPI, achats perso)
        </div>
        """, unsafe_allow_html=True)

    with tab_cr:
        st.markdown('<div class="section-title">Compte de résultat</div>', unsafe_allow_html=True)

        df_cr = load_transactions(sel_year)
        ventes_cr = df_cr[df_cr["type_op"]=="Vente"]["total_ht"].sum()
        charges_by_cat = df_cr[df_cr["type_op"].isin(["Achat","Achat perso"])].groupby("categorie")["total_ht"].sum()

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("**CHARGES**")
            total_charges = 0
            charge_groups = {
                "Production": ["Matière première","Composants","Confection / Production"],
                "Marketing & Comm.": ["Communication"],
                "Logistique": ["Transport / Logistique","Stockage","Packaging"],
                "Structure": ["Salaire","Logiciel & outils","Légal / Administratif","Autre frais"],
            }
            for grp, cats in charge_groups.items():
                grp_total = sum(charges_by_cat.get(c, 0) for c in cats)
                total_charges += grp_total
                with st.expander(f"{grp} — {fmt_eur(grp_total)}"):
                    for cat in cats:
                        val = charges_by_cat.get(cat, 0)
                        if val > 0:
                            st.write(f"  · {cat} : {fmt_eur(val)}")

            st.markdown(f"**Total charges : {fmt_eur(total_charges)}**")

        with col_right:
            st.markdown("**PRODUITS**")
            st.write(f"· Ventes produits : {fmt_eur(ventes_cr)}")
            st.markdown(f"**Total produits : {fmt_eur(ventes_cr)}**")
            st.markdown("---")
            res = ventes_cr - total_charges
            color_res = "🟢" if res >= 0 else "🔴"
            st.markdown(f"### {color_res} Résultat : {fmt_eur(res)}")
            st.caption("Bénéfice" if res >= 0 else "Perte")

            marge = (res / ventes_cr * 100) if ventes_cr > 0 else 0
            st.metric("Marge nette", f"{marge:.1f}%")

    with tab_bilan:
        st.markdown('<div class="section-title">Bilan comptable (simplifié)</div>', unsafe_allow_html=True)
        st.info("Le bilan est une vue synthétique. Pour un bilan certifié, exportez et faites valider par votre expert-comptable.")

        df_stk_b = load_stock()
        val_stock = (df_stk_b["qte_stock"] * df_stk_b["prix_unitaire"]).sum()
        df_b = load_transactions(sel_year)
        treso = df_b[df_b["type_op"]=="Vente"]["total_ttc"].sum() - df_b[df_b["type_op"].isin(["Achat","Achat perso"])]["total_ttc"].sum()
        tva_collectee_total = df_b[df_b["type_tva"]=="Collectée"]["tva"].sum()
        tva_ded_total = df_b[df_b["type_tva"]=="Déductible"]["tva"].sum()

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**ACTIFS**")
            actifs = {
                "Trésorerie (estimée)": max(treso, 0),
                "Stocks (valeur)": val_stock,
                "Créances clients": 0,
            }
            total_actif = sum(actifs.values())
            for k, v in actifs.items():
                st.write(f"· {k} : {fmt_eur(v)}")
            st.markdown(f"**Total actif : {fmt_eur(total_actif)}**")

        with col_r:
            st.markdown("**PASSIFS**")
            res_b = ventes - achats
            passifs = {
                "TVA collectée due": tva_collectee_total - tva_ded_total,
                "Résultat de l'exercice": res_b,
            }
            total_passif = sum(passifs.values())
            for k, v in passifs.items():
                st.write(f"· {k} : {fmt_eur(v)}")
            st.markdown(f"**Total passif : {fmt_eur(total_passif)}**")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CONTACTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👤 Contacts":
    st.markdown("### Contacts")

    tab_c1, tab_c2 = st.tabs(["📋 Répertoire", "➕ Ajouter"])

    with tab_c1:
        df_ct = load_contacts()
        if df_ct.empty:
            st.info("Aucun contact.")
        else:
            f_type_c = st.selectbox("Type", ["Tous","Fournisseur","Atelier","Client","Prestataire"])
            dfc2 = df_ct if f_type_c == "Tous" else df_ct[df_ct["type_contact"]==f_type_c]

            for _, row in dfc2.iterrows():
                emoji = {"Fournisseur":"🏭","Atelier":"🪡","Client":"🛍️","Prestataire":"🎨"}.get(row["type_contact"],"👤")
                with st.expander(f"{emoji} {row['nom']} {('· '+row['entreprise']) if row['entreprise'] else ''} · {row['pays']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Type** : {row['type_contact']}")
                        st.write(f"**Email** : {row['email']}")
                        st.write(f"**Tél** : {row['telephone']}")
                    with c2:
                        st.write(f"**Adresse** : {row['adresse']}")
                        st.write(f"**Notes** : {row['notes']}")

    with tab_c2:
        c1, c2 = st.columns(2)
        with c1:
            type_ct = st.selectbox("Type de contact", ["Fournisseur","Atelier","Client","Prestataire"])
            nom_ct  = st.text_input("Nom / Prénom")
            ent_ct  = st.text_input("Entreprise")
            pays_ct = st.selectbox("Pays", ["FR","JP","DE","IT","US","CN","GB","BE","ES","Autre"])
        with c2:
            email_ct = st.text_input("Email")
            tel_ct   = st.text_input("Téléphone")
            adr_ct   = st.text_input("Adresse")

        notes_ct = st.text_area("Notes", height=80)

        if st.button("✓ Ajouter le contact"):
            if not nom_ct:
                st.error("Nom obligatoire.")
            else:
                conn = get_conn()
                conn.execute("""INSERT INTO contacts (type_contact,nom,entreprise,email,telephone,adresse,pays,notes)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (type_ct, nom_ct, ent_ct, email_ct, tel_ct, adr_ct, pays_ct, notes_ct))
                conn.commit()
                conn.close()
                st.success("✓ Contact ajouté.")
                st.rerun()
