# ══════════════════════════════════════════════════════════════════════════════
# MODULE CRM COMMERCIAL
# Pipeline kanban · Comptes buyers/showrooms · Interactions · Zones géo
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import date, datetime, timedelta

# ── Palette ────────────────────────────────────────────────────────────────────
EW_V = "#7b506f"   # violet
EW_G = "#395f30"   # vert
EW_B = "#8a7968"   # marron
EW_S = "#ede3d3"   # sable
EW_C = "#f5f0e8"   # crème
EW_K = "#1a1a1a"   # noir

# ── Constantes ─────────────────────────────────────────────────────────────────
PIPELINE_STAGES = [
    "Prospection",
    "Contacté",
    "Lookbook envoyé",
    "Meeting / Showroom",
    "Négociation",
    "Commande wholesale",
    "Perdu",
    "On hold",
]

STAGE_COLORS = {
    "Prospection":         EW_B,
    "Contacté":            "#c9800a",
    "Lookbook envoyé":     EW_V,
    "Meeting / Showroom":  EW_V,
    "Négociation":         EW_G,
    "Commande wholesale":  EW_G,
    "Perdu":               "#c1440e",
    "On hold":             "#aaa",
}

ZONES_GEO = {
    "Asie":              {"responsable": "Alexis", "pays": ["JP","KR","CN","SG","TW","HK","TH"]},
    "Europe":            {"responsable": "Corentin", "pays": ["FR","DE","IT","BE","NL","GB","ES","CH","PT","DK","SE","NO"]},
    "USA / Monde":       {"responsable": "Jules", "pays": ["US","CA","MX","BR","AU","NZ","AE","SA"]},
}

TYPES_COMPTE = [
    "Boutique concept store",
    "Department store",
    "E-commerce pure player",
    "Showroom / Agent",
    "Distributeur",
    "Presse / Media",
    "Autre",
]

TYPES_INTERACTION = [
    "Email sortant",
    "Email entrant",
    "Appel",
    "Meeting physique",
    "Showroom",
    "Envoi lookbook",
    "Envoi samples",
    "Devis envoyé",
    "Commande reçue",
    "Note interne",
]

PRIORITES = ["Haute", "Normal", "Basse"]


# ── DB ─────────────────────────────────────────────────────────────────────────
def init_crm_db(conn):
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS crm_comptes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        type_compte TEXT,
        pays TEXT,
        ville TEXT,
        zone_geo TEXT,
        responsable TEXT,
        site_web TEXT,
        instagram TEXT,
        email_achat TEXT,
        telephone TEXT,
        contact_nom TEXT,
        statut_pipeline TEXT DEFAULT 'Prospection',
        priorite TEXT DEFAULT 'Normal',
        potentiel_eur REAL DEFAULT 0,
        moq_accepte REAL DEFAULT 0,
        collections_presentees TEXT,
        produits_interet TEXT,
        ca_total REAL DEFAULT 0,
        prochaine_action TEXT,
        date_prochaine_action TEXT,
        notes TEXT,
        contact_id INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS crm_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        compte_id INTEGER NOT NULL,
        type_interaction TEXT,
        date_interaction TEXT,
        responsable TEXT,
        sujet TEXT,
        contenu TEXT,
        resultat TEXT,
        prochaine_etape TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(compte_id) REFERENCES crm_comptes(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS crm_commandes_wholesale (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        compte_id INTEGER NOT NULL,
        num_commande TEXT,
        collection TEXT,
        date_commande TEXT,
        date_livraison TEXT,
        montant_eur REAL DEFAULT 0,
        statut TEXT DEFAULT 'En cours',
        conditions TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(compte_id) REFERENCES crm_comptes(id)
    )""")

    # Seed démo
    c.execute("SELECT COUNT(*) FROM crm_comptes")
    if c.fetchone()[0] == 0:
        demo = [
            ("BEAMS", "Department store", "JP", "Tokyo", "Asie", "Alexis",
             "https://www.beams.co.jp", "@beams_official", "buying@beams.co.jp",
             "+81 3-3470-3948", "Buying dept.", "Meeting / Showroom", "Haute",
             15000.0, 5.0, "Chapter N°II Souvenir", "Waterfowl Jacket, Souvenir Cap",
             0.0, "Follow-up après showroom Paris", "2025-07-15",
             "Très intéressés par les vestes. MOQ négociable sur la première commande.", None),
            ("Galeries Lafayette", "Department store", "FR", "Paris", "Europe", "Corentin",
             "https://www.galerieslafayette.com", "@galerieslafayette", "buyers@gl.fr",
             "+33 1 42 82 34 56", "Mode Hommes Buying", "Lookbook envoyé", "Haute",
             25000.0, 12.0, "Chapter N°II Souvenir", "Waterfowl Jacket, Research Club Shirt",
             0.0, "Relance après envoi lookbook", "2025-06-20",
             "Lookbook envoyé le 15/05. En attente retour acheteur.", None),
            ("Dover Street Market", "Boutique concept store", "GB", "London", "Europe", "Corentin",
             "https://london.doverstreetmarket.com", "@doverstreetmarket", "dsm@comme.com",
             "", "Buying team", "Contacté", "Haute",
             20000.0, 3.0, "", "Tous les jackets",
             0.0, "Envoyer lookbook + samples", "2025-06-10",
             "Premier contact via Instagram. Très réceptifs au concept.", None),
            ("Browns Fashion", "E-commerce pure player", "GB", "London", "Europe", "Corentin",
             "https://www.brownsfashion.com", "@brownsfashion", "buying@brownsfashion.com",
             "", "Womenswear / Unisex buyer", "Prospection", "Normal",
             8000.0, 0, "", "",
             0.0, "Premier contact email", "2025-07-01",
             "Identifié comme cible potentielle. Profil aligné avec Eastwood.", None),
            ("Opening Ceremony", "Boutique concept store", "US", "New York", "USA / Monde", "Jules",
             "", "@openingceremony", "buyers@oc.com",
             "", "Buying", "Prospection", "Normal",
             12000.0, 0, "", "",
             0.0, "Rechercher contact buyer direct", "2025-07-10",
             "À contacter pour SS26.", None),
        ]
        for d in demo:
            c.execute("""INSERT INTO crm_comptes
                (nom,type_compte,pays,ville,zone_geo,responsable,site_web,instagram,
                 email_achat,telephone,contact_nom,statut_pipeline,priorite,
                 potentiel_eur,moq_accepte,collections_presentees,produits_interet,
                 ca_total,prochaine_action,date_prochaine_action,notes,contact_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", d)

        # Interactions démo pour BEAMS
        c.execute("SELECT id FROM crm_comptes WHERE nom='BEAMS'")
        beams_id = c.fetchone()
        if beams_id:
            bid = beams_id[0]
            c.executemany("""INSERT INTO crm_interactions
                (compte_id,type_interaction,date_interaction,responsable,sujet,contenu,resultat,prochaine_etape)
                VALUES (?,?,?,?,?,?,?,?)""", [
                (bid, "Email sortant", "2025-05-10", "Alexis",
                 "Introduction Eastwood Studio",
                 "Email de présentation de la marque avec lookbook PDF joint.",
                 "Réponse positive. Intéressés par les vestes.", "Envoyer samples"),
                (bid, "Appel", "2025-05-20", "Alexis",
                 "Call de suivi post-lookbook",
                 "Appel de 30min avec le buyer. Questions sur les matières et la production française.",
                 "Rendez-vous showroom Paris confirmé pour juillet.", "Préparer samples showroom"),
                (bid, "Envoi samples", "2025-06-01", "Alexis",
                 "Envoi Waterfowl Jacket x2 + Souvenir Cap x2",
                 "Envoi DHL Express vers Tokyo. AWB 123456789.",
                 "Livrés. Retour très positif par email.", "Meeting showroom"),
            ])

    conn.commit()


def get_comptes(conn, zone=None, responsable=None, statut=None, search=None):
    q = "SELECT * FROM crm_comptes WHERE 1=1"
    p = []
    if zone:         q += " AND zone_geo=?";       p.append(zone)
    if responsable:  q += " AND responsable=?";    p.append(responsable)
    if statut:       q += " AND statut_pipeline=?"; p.append(statut)
    df = pd.read_sql(q + " ORDER BY priorite DESC, updated_at DESC", conn, params=p)
    if search and not df.empty:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
    return df


def get_interactions(conn, compte_id):
    return pd.read_sql(
        "SELECT * FROM crm_interactions WHERE compte_id=? ORDER BY date_interaction DESC",
        conn, params=[compte_id])


def get_wholesale(conn, compte_id=None):
    q = "SELECT * FROM crm_commandes_wholesale WHERE 1=1"
    p = []
    if compte_id: q += " AND compte_id=?"; p.append(compte_id)
    return pd.read_sql(q + " ORDER BY date_commande DESC", conn, params=p)


def fmt_eur(v):
    if not v or v == 0: return "—"
    return f"{float(v):,.0f} €".replace(",", " ")


def stage_badge(stage):
    color = STAGE_COLORS.get(stage, EW_B)
    return f'<span style="font-family:\'DM Mono\',monospace;font-size:9px;background:{color}18;color:{color};padding:2px 8px;letter-spacing:.06em;">{stage}</span>'


def zone_color(zone):
    return {
        "Asie": EW_V,
        "Europe": EW_B,
        "USA / Monde": EW_G,
    }.get(zone, EW_B)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CRM PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_crm(can_fn, DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_crm_db(conn)

    st.markdown("### CRM Commercial")

    tab_objs = st.tabs([
        "📊 Pipeline",
        "🗂 Comptes",
        "🌍 Par zone",
        "📅 Agenda commercial",
        "📦 Wholesale",
        "➕ Nouveau compte",
    ])
    tab_pipe, tab_list, tab_zone, tab_agenda, tab_ws, tab_new = tab_objs

    # ── PIPELINE KANBAN ────────────────────────────────────────────────────────
    with tab_pipe:
        df_all = get_comptes(conn)

        if df_all.empty:
            st.info("Aucun compte dans le CRM.")
        else:
            # KPIs globaux
            k1,k2,k3,k4 = st.columns(4)
            total_potentiel = df_all["potentiel_eur"].sum()
            actifs = df_all[~df_all["statut_pipeline"].isin(["Perdu","On hold"])]
            en_nego = df_all[df_all["statut_pipeline"].isin(["Négociation","Commande wholesale"])]
            ca_ws = get_wholesale(conn)["montant_eur"].sum() if not get_wholesale(conn).empty else 0
            with k1: st.metric("Comptes actifs", len(actifs))
            with k2: st.metric("Potentiel total", fmt_eur(total_potentiel))
            with k3: st.metric("En négociation", len(en_nego))
            with k4: st.metric("CA Wholesale", fmt_eur(ca_ws))

            # Pipeline visuel
            st.markdown(f'<div class="section-title">Pipeline</div>', unsafe_allow_html=True)

            active_stages = [s for s in PIPELINE_STAGES if s not in ["Perdu","On hold"]]
            stage_cols = st.columns(len(active_stages))

            for i, stage in enumerate(active_stages):
                with stage_cols[i]:
                    df_s = df_all[df_all["statut_pipeline"] == stage]
                    color = STAGE_COLORS.get(stage, EW_B)
                    pot_s = df_s["potentiel_eur"].sum()
                    st.markdown(f"""
<div style="border-top:2px solid {color};padding:10px 0;">
  <div style="font-family:'DM Mono',monospace;font-size:8px;letter-spacing:.14em;
       text-transform:uppercase;color:{color};margin-bottom:4px;">{stage}</div>
  <div style="font-family:'DM Mono',monospace;font-size:18px;font-weight:500;
       color:{EW_K};">{len(df_s)}</div>
  <div style="font-size:10px;color:{EW_B};">{fmt_eur(pot_s)}</div>
</div>""", unsafe_allow_html=True)

                    for _, row in df_s.iterrows():
                        zc = zone_color(row.get("zone_geo",""))
                        st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};border-left:2px solid {zc};
     padding:8px 10px;margin:4px 0;cursor:pointer;" title="{row.get('notes','')}">
  <div style="font-weight:500;font-size:11px;color:{EW_K};">{row['nom']}</div>
  <div style="font-size:10px;color:{EW_B};">{row.get('ville','')} · {row.get('pays','')}</div>
  <div style="font-size:10px;color:{EW_B};">{row.get('responsable','')}</div>
  {f'<div style="font-family:\'DM Mono\',monospace;font-size:10px;color:{EW_K};margin-top:2px;">{fmt_eur(row["potentiel_eur"])}</div>' if row.get("potentiel_eur") else ''}
</div>""", unsafe_allow_html=True)

            # Perdus / On hold
            df_lost = df_all[df_all["statut_pipeline"].isin(["Perdu","On hold"])]
            if not df_lost.empty:
                with st.expander(f"Perdu / On hold ({len(df_lost)})"):
                    for _, row in df_lost.iterrows():
                        st.markdown(f"· {row['nom']} — {row['statut_pipeline']} — {row.get('ville','')} {row.get('pays','')}")

    # ── LISTE COMPTES ──────────────────────────────────────────────────────────
    with tab_list:
        fc1,fc2,fc3,fc4 = st.columns(4)
        with fc1: f_zone = st.selectbox("Zone", ["Toutes"] + list(ZONES_GEO.keys()), key="crm_zone")
        with fc2: f_resp = st.selectbox("Responsable", ["Tous","Jules","Corentin","Alexis"], key="crm_resp")
        with fc3: f_stat = st.selectbox("Statut", ["Tous"]+PIPELINE_STAGES, key="crm_stat")
        with fc4: f_srch = st.text_input("Recherche", placeholder="nom, ville, pays...", key="crm_srch")

        df_list = get_comptes(
            conn,
            zone=None if f_zone=="Toutes" else f_zone,
            responsable=None if f_resp=="Tous" else f_resp,
            statut=None if f_stat=="Tous" else f_stat,
            search=f_srch or None,
        )

        if df_list.empty:
            st.info("Aucun compte.")
        else:
            for _, row in df_list.iterrows():
                zc = zone_color(row.get("zone_geo",""))
                prio_dot = {"Haute":"●","Normal":"·","Basse":"·"}.get(row.get("priorite","Normal"),"·")
                prio_col = {"Haute":"#c1440e","Normal":EW_B,"Basse":"#ccc"}.get(row.get("priorite","Normal"),EW_B)

                with st.expander(
                    f"{prio_dot} {row['nom']}  ·  {row.get('type_compte','')}  ·  "
                    f"{row.get('ville','')} {row.get('pays','')}  ·  {row.get('statut_pipeline','')}"
                ):
                    # ── Fiche compte ───────────────────────────────────────────
                    st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:14px;">
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};letter-spacing:.15em;text-transform:uppercase;margin-bottom:6px;">Compte</div>
    <div style="font-weight:500;font-size:14px;color:{EW_K};">{row['nom']}</div>
    <div style="font-size:12px;color:{EW_B};">{row.get('type_compte','')}</div>
    <div style="font-size:12px;color:{EW_B};">{row.get('ville','')} · {row.get('pays','')}</div>
    {f'<a href="{row["site_web"]}" target="_blank" style="font-size:11px;color:{EW_V};">{row["site_web"]}</a>' if row.get("site_web") else ''}
    {f'<div style="font-size:11px;color:{EW_B};">{row["instagram"]}</div>' if row.get("instagram") else ''}
  </div>
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};letter-spacing:.15em;text-transform:uppercase;margin-bottom:6px;">Contact</div>
    <div style="font-size:12px;">{row.get('contact_nom','—')}</div>
    <div style="font-size:12px;color:{EW_B};">{row.get('email_achat','')}</div>
    <div style="font-size:12px;color:{EW_B};">{row.get('telephone','')}</div>
    <div style="margin-top:8px;">{stage_badge(row.get('statut_pipeline',''))}</div>
  </div>
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};letter-spacing:.15em;text-transform:uppercase;margin-bottom:6px;">Commercial</div>
    <div style="font-size:12px;">Resp. : <strong>{row.get('responsable','')}</strong></div>
    <div style="font-size:12px;color:{EW_B};">Zone : {row.get('zone_geo','')}</div>
    <div style="font-family:'DM Mono',monospace;font-size:12px;margin-top:4px;">Potentiel : {fmt_eur(row.get('potentiel_eur'))}</div>
    <div style="font-size:12px;color:{EW_B};">MOQ accepté : {row.get('moq_accepte','—')}</div>
    <div style="font-size:12px;margin-top:4px;">CA total : {fmt_eur(row.get('ca_total'))}</div>
  </div>
</div>""", unsafe_allow_html=True)

                    if row.get("prochaine_action"):
                        st.markdown(f"""
<div style="background:{EW_C};border:0.5px solid {EW_S};border-left:2px solid {EW_V};
     padding:8px 12px;margin-bottom:10px;font-size:12px;">
  <span style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};
               text-transform:uppercase;letter-spacing:.1em;">Prochaine action</span><br>
  <strong>{row['prochaine_action']}</strong>
  {f' · <span style="color:{EW_B};">{row["date_prochaine_action"]}</span>' if row.get("date_prochaine_action") else ''}
</div>""", unsafe_allow_html=True)

                    if row.get("notes"):
                        st.markdown(f'<div style="font-size:12px;color:{EW_B};margin-bottom:10px;">{row["notes"]}</div>', unsafe_allow_html=True)

                    # Interactions
                    df_int = get_interactions(conn, row["id"])
                    int_tab, edit_tab = st.tabs([f"Historique ({len(df_int)})", "Modifier"])

                    with int_tab:
                        if not df_int.empty:
                            for _, inter in df_int.iterrows():
                                st.markdown(f"""
<div style="border-left:2px solid {EW_S};padding:6px 12px;margin:6px 0;">
  <div style="display:flex;justify-content:space-between;align-items:baseline;">
    <span style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_V};">{inter.get('type_interaction','')}</span>
    <span style="font-size:10px;color:{EW_B};">{inter.get('date_interaction','')} · {inter.get('responsable','')}</span>
  </div>
  <div style="font-weight:500;font-size:12px;margin:2px 0;">{inter.get('sujet','')}</div>
  <div style="font-size:11px;color:{EW_B};">{inter.get('contenu','')}</div>
  {f'<div style="font-size:11px;color:{EW_G};margin-top:2px;">→ {inter["resultat"]}</div>' if inter.get('resultat') else ''}
  {f'<div style="font-size:11px;color:{EW_V};margin-top:1px;">Prochaine étape : {inter["prochaine_etape"]}</div>' if inter.get('prochaine_etape') else ''}
</div>""", unsafe_allow_html=True)
                        else:
                            st.info("Aucune interaction enregistrée.")

                        # Ajouter interaction
                        if can_fn("commandes_write") or can_fn("finance_write"):
                            st.markdown(f'<div style="font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:{EW_B};margin:12px 0 6px;">Ajouter une interaction</div>', unsafe_allow_html=True)
                            with st.form(f"add_int_{row['id']}"):
                                ai1,ai2,ai3 = st.columns(3)
                                with ai1:
                                    i_type = st.selectbox("Type", TYPES_INTERACTION, key=f"itype_{row['id']}")
                                    i_date = st.date_input("Date", value=date.today(), key=f"idate_{row['id']}")
                                with ai2:
                                    i_resp = st.selectbox("Responsable", ["Jules","Corentin","Alexis"], key=f"iresp_{row['id']}")
                                    i_sujet = st.text_input("Sujet", key=f"isujet_{row['id']}")
                                with ai3:
                                    i_res = st.text_input("Résultat", key=f"ires_{row['id']}")
                                    i_next = st.text_input("Prochaine étape", key=f"inext_{row['id']}")
                                i_contenu = st.text_area("Détails", height=60, key=f"icont_{row['id']}")
                                if st.form_submit_button("➕ Ajouter"):
                                    conn.execute("""INSERT INTO crm_interactions
                                        (compte_id,type_interaction,date_interaction,responsable,
                                         sujet,contenu,resultat,prochaine_etape)
                                        VALUES (?,?,?,?,?,?,?,?)""",
                                        (row["id"],i_type,str(i_date),i_resp,
                                         i_sujet,i_contenu,i_res,i_next))
                                    conn.execute("UPDATE crm_comptes SET updated_at=? WHERE id=?",
                                                 (str(date.today()), row["id"]))
                                    conn.commit()
                                    st.success("✓ Interaction ajoutée."); st.rerun()

                    with edit_tab:
                        with st.form(f"edit_cpt_{row['id']}"):
                            ef1,ef2 = st.columns(2)
                            with ef1:
                                e_nom   = st.text_input("Nom boutique", value=row.get("nom",""))
                                e_type  = st.selectbox("Type", TYPES_COMPTE,
                                    index=TYPES_COMPTE.index(row["type_compte"]) if row.get("type_compte") in TYPES_COMPTE else 0)
                                e_pays  = st.text_input("Pays (code)", value=row.get("pays",""))
                                e_ville = st.text_input("Ville", value=row.get("ville",""))
                                e_zone  = st.selectbox("Zone", list(ZONES_GEO.keys()),
                                    index=list(ZONES_GEO.keys()).index(row["zone_geo"]) if row.get("zone_geo") in ZONES_GEO else 0)
                                e_resp  = st.selectbox("Responsable", ["Jules","Corentin","Alexis"],
                                    index=["Jules","Corentin","Alexis"].index(row["responsable"]) if row.get("responsable") in ["Jules","Corentin","Alexis"] else 0)
                            with ef2:
                                e_stat  = st.selectbox("Statut pipeline", PIPELINE_STAGES,
                                    index=PIPELINE_STAGES.index(row["statut_pipeline"]) if row.get("statut_pipeline") in PIPELINE_STAGES else 0)
                                e_prio  = st.selectbox("Priorité", PRIORITES,
                                    index=PRIORITES.index(row["priorite"]) if row.get("priorite") in PRIORITES else 1)
                                e_pot   = st.number_input("Potentiel (€)", value=float(row.get("potentiel_eur",0) or 0), min_value=0.0)
                                e_moq   = st.number_input("MOQ accepté", value=float(row.get("moq_accepte",0) or 0), min_value=0.0)
                                e_email = st.text_input("Email achat", value=row.get("email_achat","") or "")
                                e_ig    = st.text_input("Instagram", value=row.get("instagram","") or "")
                                e_web   = st.text_input("Site web", value=row.get("site_web","") or "")
                            e_contact = st.text_input("Nom contact", value=row.get("contact_nom","") or "")
                            e_prods   = st.text_input("Produits d'intérêt", value=row.get("produits_interet","") or "")
                            e_colls   = st.text_input("Collections présentées", value=row.get("collections_presentees","") or "")
                            e_action  = st.text_input("Prochaine action", value=row.get("prochaine_action","") or "")
                            e_d_act   = st.date_input("Date prochaine action",
                                value=date.fromisoformat(row["date_prochaine_action"]) if row.get("date_prochaine_action") else date.today())
                            e_notes   = st.text_area("Notes", value=row.get("notes","") or "", height=70)

                            bs1,bs2 = st.columns([3,1])
                            with bs1: sub_edit = st.form_submit_button("💾 Enregistrer")
                            with bs2:
                                del_edit = st.form_submit_button("🗑") if can_fn("products_delete") else False

                            if sub_edit:
                                conn.execute("""UPDATE crm_comptes SET
                                    nom=?,type_compte=?,pays=?,ville=?,zone_geo=?,responsable=?,
                                    statut_pipeline=?,priorite=?,potentiel_eur=?,moq_accepte=?,
                                    email_achat=?,instagram=?,site_web=?,contact_nom=?,
                                    produits_interet=?,collections_presentees=?,
                                    prochaine_action=?,date_prochaine_action=?,notes=?,
                                    updated_at=?
                                    WHERE id=?""",
                                    (e_nom,e_type,e_pays,e_ville,e_zone,e_resp,
                                     e_stat,e_prio,e_pot,e_moq,
                                     e_email,e_ig,e_web,e_contact,
                                     e_prods,e_colls,
                                     e_action,str(e_d_act),e_notes,
                                     str(date.today()), row["id"]))
                                conn.commit()
                                st.success("✓ Compte mis à jour."); st.rerun()
                            if del_edit:
                                conn.execute("DELETE FROM crm_interactions WHERE compte_id=?", (row["id"],))
                                conn.execute("DELETE FROM crm_comptes WHERE id=?", (row["id"],))
                                conn.commit(); st.rerun()

    # ── VUE PAR ZONE ──────────────────────────────────────────────────────────
    with tab_zone:
        for zone_name, zone_info in ZONES_GEO.items():
            zc = zone_color(zone_name)
            df_z = get_comptes(conn, zone=zone_name)
            active_z = df_z[~df_z["statut_pipeline"].isin(["Perdu","On hold"])] if not df_z.empty else df_z
            pot_z = df_z["potentiel_eur"].sum() if not df_z.empty else 0
            ca_z  = 0

            st.markdown(f"""
<div style="border-left:3px solid {zc};padding:10px 18px;margin:10px 0;background:#fff;
     border:0.5px solid {EW_S};border-left:3px solid {zc};">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="font-family:'DM Mono',monospace;font-size:8px;letter-spacing:.18em;
                  text-transform:uppercase;color:{zc};">{zone_name}</div>
      <div style="font-size:15px;font-weight:500;color:{EW_K};margin-top:2px;">
        {zone_info['responsable']}
      </div>
      <div style="font-size:11px;color:{EW_B};">{', '.join(zone_info['pays'])}</div>
    </div>
    <div style="text-align:right;">
      <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:{EW_K};">{len(active_z)}</div>
      <div style="font-size:10px;color:{EW_B};">comptes actifs</div>
      <div style="font-family:'DM Mono',monospace;font-size:12px;color:{EW_K};margin-top:4px;">{fmt_eur(pot_z)}</div>
      <div style="font-size:10px;color:{EW_B};">potentiel</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

            if not df_z.empty:
                cols_z = st.columns(min(len(df_z), 4))
                for i, (_, row) in enumerate(df_z.iterrows()):
                    with cols_z[i % min(len(df_z), 4)]:
                        stat_c = STAGE_COLORS.get(row.get("statut_pipeline",""), EW_B)
                        st.markdown(f"""
<div style="background:{EW_C};border:0.5px solid {EW_S};padding:8px 10px;margin-bottom:6px;">
  <div style="font-weight:500;font-size:12px;">{row['nom']}</div>
  <div style="font-size:10px;color:{EW_B};">{row.get('ville','')} · {row.get('type_compte','')}</div>
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{stat_c};margin-top:3px;">
    {row.get('statut_pipeline','')}
  </div>
</div>""", unsafe_allow_html=True)

    # ── AGENDA COMMERCIAL ──────────────────────────────────────────────────────
    with tab_agenda:
        st.markdown(f'<div class="section-title">Actions à venir</div>', unsafe_allow_html=True)
        df_agenda = get_comptes(conn)
        df_agenda = df_agenda[
            df_agenda["date_prochaine_action"].notna() &
            (df_agenda["date_prochaine_action"] != "")
        ].copy() if not df_agenda.empty else df_agenda

        if df_agenda.empty:
            st.info("Aucune action planifiée.")
        else:
            df_agenda["_d"] = pd.to_datetime(df_agenda["date_prochaine_action"], errors="coerce")
            df_agenda = df_agenda.sort_values("_d")
            today = date.today()

            for _, row in df_agenda.iterrows():
                try:
                    d = row["_d"].date()
                    delta = (d - today).days
                    if delta < 0:
                        urgency_c = "#c1440e"
                        urgency_label = f"En retard de {-delta}j"
                    elif delta == 0:
                        urgency_c = EW_V
                        urgency_label = "Aujourd'hui"
                    elif delta <= 7:
                        urgency_c = "#c9800a"
                        urgency_label = f"Dans {delta}j"
                    else:
                        urgency_c = EW_B
                        urgency_label = f"Dans {delta}j"
                except Exception:
                    urgency_c = EW_B
                    urgency_label = ""

                zc = zone_color(row.get("zone_geo",""))
                st.markdown(f"""
<div style="border:0.5px solid {EW_S};border-left:3px solid {urgency_c};
     padding:10px 16px;margin:6px 0;background:#fff;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="font-weight:500;font-size:13px;">{row['nom']}</div>
      <div style="font-size:12px;color:{EW_B};margin-top:2px;">{row.get('prochaine_action','')}</div>
      <div style="font-size:11px;color:{EW_B};">Resp. : {row.get('responsable','')} · {row.get('zone_geo','')}</div>
    </div>
    <div style="text-align:right;">
      <div style="font-family:'DM Mono',monospace;font-size:10px;color:{urgency_c};font-weight:500;">{urgency_label}</div>
      <div style="font-size:10px;color:{EW_B};">{row.get('date_prochaine_action','')}</div>
      {stage_badge(row.get('statut_pipeline',''))}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        # Filtrer par responsable
        st.markdown(f'<div class="section-title">Filtrer par responsable</div>', unsafe_allow_html=True)
        resp_sel = st.radio("", ["Jules","Corentin","Alexis"], horizontal=True, key="agenda_resp")
        df_resp = get_comptes(conn, responsable=resp_sel)
        df_resp_act = df_resp[~df_resp["statut_pipeline"].isin(["Perdu","On hold"])] if not df_resp.empty else df_resp
        st.markdown(f"**{len(df_resp_act)} comptes actifs pour {resp_sel}** · Potentiel : {fmt_eur(df_resp['potentiel_eur'].sum() if not df_resp.empty else 0)}")

    # ── COMMANDES WHOLESALE ────────────────────────────────────────────────────
    with tab_ws:
        st.markdown(f'<div class="section-title">Commandes wholesale</div>', unsafe_allow_html=True)
        df_ws = get_wholesale(conn)

        if not df_ws.empty:
            # Joindre avec noms comptes
            df_cptes = get_comptes(conn)[["id","nom","zone_geo","responsable"]]
            df_ws_j = df_ws.merge(df_cptes, left_on="compte_id", right_on="id", how="left", suffixes=("","_cpt"))

            w1,w2,w3 = st.columns(3)
            with w1: st.metric("Nb commandes", len(df_ws_j))
            with w2: st.metric("CA total wholesale", fmt_eur(df_ws_j["montant_eur"].sum()))
            with w3:
                en_cours = len(df_ws_j[df_ws_j["statut"]=="En cours"])
                st.metric("En cours de livraison", en_cours)

            for _, row in df_ws_j.iterrows():
                stat_ws_c = {"En cours":"#c9800a","Livré":EW_G,"Annulé":"#c1440e","Confirmé":EW_V}.get(row.get("statut",""),EW_B)
                st.markdown(f"""
<div style="border:0.5px solid {EW_S};padding:10px 16px;margin:6px 0;background:#fff;">
  <div style="display:flex;justify-content:space-between;">
    <div>
      <div style="font-weight:500;font-size:13px;">{row.get('nom','')} — {row.get('num_commande','')}</div>
      <div style="font-size:11px;color:{EW_B};">{row.get('collection','')} · {row.get('date_commande','')}</div>
      {f'<div style="font-size:11px;color:{EW_B};">Livraison prévue : {row["date_livraison"]}</div>' if row.get('date_livraison') else ''}
      {f'<div style="font-size:11px;color:{EW_B};">{row["conditions"]}</div>' if row.get('conditions') else ''}
    </div>
    <div style="text-align:right;">
      <div style="font-family:\'DM Mono\',monospace;font-size:16px;font-weight:500;">{fmt_eur(row["montant_eur"])}</div>
      <div style="font-family:\'DM Mono\',monospace;font-size:9px;color:{stat_ws_c};">{row.get('statut','')}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
        else:
            st.info("Aucune commande wholesale enregistrée.")

        # Nouvelle commande wholesale
        st.markdown(f'<div class="section-title">Nouvelle commande wholesale</div>', unsafe_allow_html=True)
        df_cptes2 = get_comptes(conn)
        if not df_cptes2.empty:
            with st.form("new_ws"):
                cpte_opts = {r["nom"]: r["id"] for _, r in df_cptes2.iterrows()}
                ws1,ws2 = st.columns(2)
                with ws1:
                    w_cpte = st.selectbox("Compte", list(cpte_opts.keys()))
                    w_num  = st.text_input("N° commande", placeholder="WS-2025-001")
                    w_coll = st.text_input("Collection", placeholder="Chapter N°II Souvenir")
                with ws2:
                    w_mont = st.number_input("Montant (€)", min_value=0.0, value=0.0)
                    w_d_cmd= st.date_input("Date commande", value=date.today())
                    w_d_liv= st.date_input("Date livraison prévue", value=date.today())
                w_stat = st.selectbox("Statut", ["Confirmé","En cours","Livré","Annulé"])
                w_cond = st.text_input("Conditions (paiement, délais...)")
                w_notes= st.text_area("Notes", height=50)
                if st.form_submit_button("✓ Enregistrer la commande wholesale"):
                    conn.execute("""INSERT INTO crm_commandes_wholesale
                        (compte_id,num_commande,collection,date_commande,date_livraison,
                         montant_eur,statut,conditions,notes)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                        (cpte_opts[w_cpte],w_num,w_coll,str(w_d_cmd),str(w_d_liv),
                         w_mont,w_stat,w_cond,w_notes))
                    # Mettre à jour CA total du compte
                    conn.execute("UPDATE crm_comptes SET ca_total=ca_total+? WHERE id=?",
                                 (w_mont, cpte_opts[w_cpte]))
                    conn.commit()
                    st.success("✓ Commande wholesale enregistrée."); st.rerun()

    # ── NOUVEAU COMPTE ─────────────────────────────────────────────────────────
    with tab_new:
        st.markdown(f'<div class="section-title">Nouveau compte</div>', unsafe_allow_html=True)
        with st.form("new_crm_compte"):
            nc1,nc2,nc3 = st.columns(3)
            with nc1:
                n_nom   = st.text_input("Nom boutique / buyer *")
                n_type  = st.selectbox("Type", TYPES_COMPTE)
                n_pays  = st.text_input("Pays (code)", placeholder="FR / JP / US")
                n_ville = st.text_input("Ville", placeholder="Paris")
            with nc2:
                n_zone  = st.selectbox("Zone géographique", list(ZONES_GEO.keys()))
                n_resp  = st.selectbox("Responsable", ["Jules","Corentin","Alexis"],
                    index=["Jules","Corentin","Alexis"].index(
                        ZONES_GEO.get(
                            st.session_state.get("nav_crm_zone","Asie"),
                            {"responsable":"Jules"}
                        )["responsable"]
                    ) if False else 0)
                n_stat  = st.selectbox("Statut initial", PIPELINE_STAGES)
                n_prio  = st.selectbox("Priorité", PRIORITES)
            with nc3:
                n_pot   = st.number_input("Potentiel estimé (€)", min_value=0.0, value=0.0)
                n_moq   = st.number_input("MOQ accepté", min_value=0.0, value=0.0)
                n_email = st.text_input("Email achat")
                n_ig    = st.text_input("Instagram", placeholder="@handle")
            n_web     = st.text_input("Site web")
            n_contact = st.text_input("Nom du contact (buyer)")
            n_action  = st.text_input("Première action à mener")
            n_d_act   = st.date_input("Date", value=date.today())
            n_prods   = st.text_input("Produits d'intérêt")
            n_notes   = st.text_area("Notes", height=60)

            if st.form_submit_button("✓ Créer le compte"):
                if not n_nom:
                    st.error("Nom obligatoire.")
                else:
                    conn.execute("""INSERT INTO crm_comptes
                        (nom,type_compte,pays,ville,zone_geo,responsable,
                         statut_pipeline,priorite,potentiel_eur,moq_accepte,
                         email_achat,instagram,site_web,contact_nom,
                         produits_interet,prochaine_action,date_prochaine_action,notes)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (n_nom,n_type,n_pays,n_ville,n_zone,n_resp,
                         n_stat,n_prio,n_pot,n_moq,
                         n_email,n_ig,n_web,n_contact,
                         n_prods,n_action,str(n_d_act),n_notes))
                    conn.commit()
                    st.success(f"✓ Compte {n_nom} créé."); st.rerun()

    # ── Export ─────────────────────────────────────────────────────────────────
    df_export = get_comptes(conn)
    if not df_export.empty:
        st.markdown("---")
        ec1, ec2 = st.columns(2)
        with ec1:
            buf_crm = io.BytesIO()
            df_export.drop(columns=["contact_id"],errors="ignore").to_csv(buf_crm, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇ Export Comptes CSV",
                buf_crm.getvalue(),
                file_name=f"crm_comptes_{date.today()}.csv",
                mime="text/csv"
            )
        with ec2:
            df_ws = get_wholesale(conn)
            if not df_ws.empty:
                buf_ws = io.BytesIO()
                df_ws.to_csv(buf_ws, index=False, encoding="utf-8-sig")
                st.download_button(
                    "⬇ Export Wholesale CSV",
                    buf_ws.getvalue(),
                    file_name=f"crm_wholesale_{date.today()}.csv",
                    mime="text/csv"
                )

    conn.close()
