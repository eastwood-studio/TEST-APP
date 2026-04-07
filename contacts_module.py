# ══════════════════════════════════════════════════════════════════════════════
# MODULE CONTACTS v2
# Refonte UX · Modèle Booklist · Fournisseurs enrichis · Tri date · Export Brevo
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
import base64
from datetime import date, datetime

EW_V = "#7b506f"
EW_G = "#395f30"
EW_B = "#8a7968"
EW_S = "#ede3d3"
EW_C = "#f5f0e8"
EW_K = "#1a1a1a"

PAYS_LIST = ["FR","JP","DE","IT","US","CN","GB","BE","ES","MX","KR","AU","BR","SG","TW","HK","NL","CH","PT","DK","SE","Autre"]
IMPORTANCE_LIST = ["Prioritaire", "Important", "Normal", "Archivé"]

TYPES_CONTACT = ["Client", "Fournisseur", "Collaborateur", "Autre"]

SOUS_TYPES = {
    "Client":        ["Fidèle", "Ponctuel", "Potentiel", "F&F", "VIP", "Wholesale"],
    "Fournisseur":   ["Tissu", "Composant", "Packaging", "Production / Confection",
                      "Logistique", "Impression / Broderie", "Autre"],
    "Collaborateur": ["Atelier", "Photographe", "Vidéaste", "Graphiste",
                      "Communication / PR", "Styliste", "Prestataire", "Autre"],
    "Autre":         ["Partenaire", "Presse", "Investisseur", "Ambassadeur",
                      "Retail", "Influenceur", "Autre"],
}

GENRES_MODELE    = ["Femme", "Homme"]
TAILLES_VET      = ["XXS", "XS", "S", "M", "L", "XL", "XXL"]
STATUT_MODELE    = ["Disponible", "En pause", "Archivé"]
STATUT_FOURNISSEUR = ["Actif — on travaille", "À tester", "Out", "En veille"]

FOURNISSEURS_DEMO = [
    {
        "nom": "The Sky Fire", "sous_type": "Production / Confection",
        "email": "", "telephone": "", "site_web": "https://theskyfire.com",
        "instagram": "", "adresse": "Paris", "pays": "FR",
        "statut_fourn": "À tester", "deja_travaille": False,
        "notes": "Atelier parisien — à contacter", "importance": "Normal",
    },
    {
        "nom": "Denis Couture", "sous_type": "Production / Confection",
        "email": "", "telephone": "", "site_web": "",
        "instagram": "", "adresse": "Paris", "pays": "FR",
        "statut_fourn": "À tester", "deja_travaille": False,
        "notes": "Recommandé pour la confection fine", "importance": "Normal",
    },
    {
        "nom": "Manigance", "sous_type": "Production / Confection",
        "email": "contact@manigance.fr", "telephone": "+33 1 00 00 00 00",
        "site_web": "https://manigance.fr", "instagram": "@manigance",
        "adresse": "Paris 75020", "pays": "FR",
        "statut_fourn": "Actif — on travaille", "deja_travaille": True,
        "notes": "Atelier de confection Belleville — qualité éprouvée", "importance": "Important",
    },
    {
        "nom": "Tissus.net", "sous_type": "Tissu",
        "email": "contact@tissus.net", "telephone": "",
        "site_web": "https://tissus.net", "instagram": "",
        "adresse": "Lyon", "pays": "FR",
        "statut_fourn": "À tester", "deja_travaille": False,
        "notes": "Stock tissu en ligne — livraison rapide", "importance": "Normal",
    },
    {
        "nom": "Atelier Insho", "sous_type": "Impression / Broderie",
        "email": "", "telephone": "",
        "site_web": "", "instagram": "@atelierinsho",
        "adresse": "Paris", "pays": "FR",
        "statut_fourn": "À tester", "deja_travaille": False,
        "notes": "Broderie artisanale — devis en cours", "importance": "Normal",
    },
]


def init_contacts_v2(conn):
    c = conn.cursor()

    # Table contacts enrichie
    c.execute("""CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_contact TEXT,
        sous_type TEXT,
        nom TEXT,
        entreprise TEXT,
        email TEXT,
        telephone TEXT,
        instagram TEXT,
        activite TEXT,
        adresse TEXT,
        ville TEXT,
        pays TEXT,
        importance TEXT DEFAULT 'Normal',
        demandeur TEXT,
        reponse TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Migrations silencieuses
    existing = [r[1] for r in c.execute("PRAGMA table_info(contacts)").fetchall()]
    for col, defn in [
        ("ville",        "TEXT"),
        ("demandeur",    "TEXT"),
        ("reponse",      "TEXT"),
        ("sous_type",    "TEXT"),
        ("instagram",    "TEXT"),
        ("activite",     "TEXT"),
        ("importance",   "TEXT DEFAULT 'Normal'"),
    ]:
        if col not in existing:
            try: c.execute(f"ALTER TABLE contacts ADD COLUMN {col} {defn}")
            except Exception: pass

    # Table fournisseurs enrichie
    c.execute("""CREATE TABLE IF NOT EXISTS fournisseurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        sous_type TEXT,
        email TEXT,
        telephone TEXT,
        site_web TEXT,
        instagram TEXT,
        adresse TEXT,
        ville TEXT,
        pays TEXT,
        statut_fourn TEXT DEFAULT 'À tester',
        deja_travaille INTEGER DEFAULT 0,
        produits_fabriques TEXT,
        moq TEXT,
        delai_production TEXT,
        notes TEXT,
        importance TEXT DEFAULT 'Normal',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Table modèles booklist
    c.execute("""CREATE TABLE IF NOT EXISTS modeles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prenom TEXT,
        nom TEXT,
        genre TEXT,
        telephone TEXT,
        email TEXT,
        instagram TEXT,
        facebook TEXT,
        responsable_contact TEXT,
        statut TEXT DEFAULT 'Disponible',
        pays TEXT,
        localisation TEXT,
        height_cm INTEGER,
        weight_kg REAL,
        pointure INTEGER,
        taille_vetement TEXT,
        style_type TEXT,
        periode_dispo TEXT,
        shooting_prevu TEXT,
        pieces_a_porter TEXT,
        tenue_complete TEXT,
        valide INTEGER DEFAULT 0,
        avec_qui_travaille INTEGER DEFAULT 0,
        notes TEXT,
        photo_data BLOB,
        photo_nom TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Migration modèles
    existing_mod = [r[1] for r in c.execute("PRAGMA table_info(modeles)").fetchall()]
    if "avec_qui_travaille" not in existing_mod:
        try: c.execute("ALTER TABLE modeles ADD COLUMN avec_qui_travaille INTEGER DEFAULT 0")
        except Exception: pass

    # Seed fournisseurs démo
    c.execute("SELECT COUNT(*) FROM fournisseurs")
    if c.fetchone()[0] == 0:
        for f in FOURNISSEURS_DEMO:
            c.execute("""INSERT INTO fournisseurs
                (nom,sous_type,email,telephone,site_web,instagram,adresse,pays,
                 statut_fourn,deja_travaille,notes,importance)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f["nom"],f["sous_type"],f["email"],f["telephone"],
                 f["site_web"],f["instagram"],f["adresse"],f["pays"],
                 f["statut_fourn"],int(f["deja_travaille"]),
                 f["notes"],f["importance"]))

    conn.commit()


def fmt_eur(v):
    if not v or v == 0: return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


def importance_dot(imp):
    return {"Prioritaire": f'<span style="color:#c1440e;">●</span>',
            "Important":   f'<span style="color:#c9800a;">●</span>',
            "Normal":      f'<span style="color:{EW_B};">·</span>',
            "Archivé":     f'<span style="color:#ccc;">·</span>'}.get(imp, "·")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONTACTS PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_contacts(can_fn, DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_contacts_v2(conn)

    st.markdown("### Contacts & Relations")

    _tabs = ["👤 Contacts", "🏭 Fournisseurs", "📸 Modèle Booklist", "📥 Import Excel", "📤 Export"]
    if can_fn("contacts_add"):
        _tabs.insert(1, "➕ Ajouter contact")
    tab_objs = st.tabs(_tabs)

    idx = 0
    tab_rep   = tab_objs[idx]; idx += 1
    tab_add   = tab_objs[idx] if can_fn("contacts_add") else None
    if can_fn("contacts_add"): idx += 1
    tab_fourn = tab_objs[idx]; idx += 1
    tab_book  = tab_objs[idx]; idx += 1
    tab_imp   = tab_objs[idx]; idx += 1
    tab_exp   = tab_objs[idx]

    # ── RÉPERTOIRE CONTACTS ────────────────────────────────────────────────────
    with tab_rep:
        fc1,fc2,fc3,fc4 = st.columns(4)
        with fc1: f_tc  = st.selectbox("Type", ["Tous"]+TYPES_CONTACT, key="ct_tc")
        with fc2:
            sous_opts = (["Tous"] + SOUS_TYPES.get(f_tc, []) if f_tc != "Tous"
                         else ["Tous"] + [s for v in SOUS_TYPES.values() for s in v])
            f_sous = st.selectbox("Sous-type", sous_opts, key="ct_sous")
        with fc3: f_imp  = st.selectbox("Importance", ["Toutes"]+IMPORTANCE_LIST, key="ct_imp")
        with fc4: f_srch = st.text_input("Recherche", placeholder="nom, email, instagram...", key="ct_srch")

        q = "SELECT * FROM contacts WHERE 1=1"
        p = []
        if f_tc   != "Tous":   q += " AND type_contact=?"; p.append(f_tc)
        if f_sous != "Tous":   q += " AND sous_type=?";    p.append(f_sous)
        if f_imp  != "Toutes": q += " AND importance=?";   p.append(f_imp)
        df_ct = pd.read_sql(q + " ORDER BY created_at DESC", conn, params=p)
        if f_srch and not df_ct.empty:
            df_ct = df_ct[df_ct.apply(lambda r: f_srch.lower() in str(r).lower(), axis=1)]

        if df_ct.empty:
            st.info("Aucun contact.")
        else:
            # Stats
            s1,s2,s3,s4 = st.columns(4)
            with s1: st.metric("Total", len(df_ct))
            with s2: st.metric("Prioritaires", len(df_ct[df_ct["importance"]=="Prioritaire"]))
            with s3: st.metric("Avec email", len(df_ct[df_ct["email"].fillna("").str.strip()!=""]))
            with s4: st.metric("Avec Instagram", len(df_ct[df_ct.get("instagram","").fillna("").str.strip()!=""]) if "instagram" in df_ct.columns else 0)

            st.markdown("")

            emoji_map = {"Client":"🛍","Fournisseur":"🏭","Collaborateur":"🤝","Autre":"👤"}

            for _, row in df_ct.iterrows():
                emoji  = emoji_map.get(row.get("type_contact",""),"👤")
                imp_dot = importance_dot(row.get("importance","Normal"))
                header = (f"{emoji} {row['nom']}"
                          + (f" · {row['entreprise']}" if row.get("entreprise") else "")
                          + (f" · {row.get('pays','')}" if row.get("pays") else "")
                          + (f" · {row.get('sous_type','')}" if row.get("sous_type") else ""))

                with st.expander(header):
                    if can_fn("contacts_edit"):
                        with st.form(f"edit_ct_{row['id']}"):
                            ef1,ef2 = st.columns(2)
                            with ef1:
                                e_type = st.selectbox("Type", TYPES_CONTACT,
                                    index=TYPES_CONTACT.index(row["type_contact"]) if row.get("type_contact") in TYPES_CONTACT else 0,
                                    key=f"ect_{row['id']}")
                                st_list = SOUS_TYPES.get(e_type, ["Autre"])
                                e_sous  = st.selectbox("Sous-type", st_list,
                                    index=st_list.index(row["sous_type"]) if row.get("sous_type") in st_list else 0,
                                    key=f"ecs_{row['id']}")
                                e_nom   = st.text_input("Nom", value=row.get("nom","") or "", key=f"en_{row['id']}")
                                e_ent   = st.text_input("Entreprise", value=row.get("entreprise","") or "", key=f"ee_{row['id']}")
                                e_imp   = st.selectbox("Importance", IMPORTANCE_LIST,
                                    index=IMPORTANCE_LIST.index(row["importance"]) if row.get("importance") in IMPORTANCE_LIST else 2,
                                    key=f"ei_{row['id']}")
                                e_dem   = st.text_input("Demandeur", value=row.get("demandeur","") or "", key=f"ed_{row['id']}")
                                e_rep   = st.text_input("Réponse", value=row.get("reponse","") or "", key=f"er_{row['id']}")
                            with ef2:
                                e_mail  = st.text_input("Email", value=row.get("email","") or "", key=f"em_{row['id']}")
                                e_tel   = st.text_input("Téléphone", value=row.get("telephone","") or "", key=f"et_{row['id']}")
                                e_ig    = st.text_input("Instagram", value=row.get("instagram","") or "", placeholder="@handle", key=f"eig_{row['id']}")
                                e_act   = st.text_input("Activité", value=row.get("activite","") or "", key=f"ea_{row['id']}")
                                e_pays  = st.selectbox("Pays", PAYS_LIST,
                                    index=PAYS_LIST.index(row["pays"]) if row.get("pays") in PAYS_LIST else 0,
                                    key=f"ep_{row['id']}")
                                e_ville = st.text_input("Ville", value=row.get("ville","") or "", key=f"ev_{row['id']}")
                            e_adr   = st.text_input("Adresse postale", value=row.get("adresse","") or "", key=f"eadr_{row['id']}")
                            e_notes = st.text_area("Notes", value=row.get("notes","") or "", height=60, key=f"eno_{row['id']}")

                            bc = st.columns([3,1]) if can_fn("contacts_delete") else st.columns([1])
                            with bc[0]: ok = st.form_submit_button("💾 Enregistrer")
                            del_ok = False
                            if can_fn("contacts_delete"):
                                with bc[1]: del_ok = st.form_submit_button("🗑")

                            if ok:
                                conn.execute("""UPDATE contacts SET
                                    type_contact=?,sous_type=?,nom=?,entreprise=?,
                                    email=?,telephone=?,instagram=?,activite=?,
                                    adresse=?,ville=?,pays=?,importance=?,
                                    demandeur=?,reponse=?,notes=?
                                    WHERE id=?""",
                                    (e_type,e_sous,e_nom,e_ent,e_mail,e_tel,
                                     e_ig,e_act,e_adr,e_ville,e_pays,e_imp,
                                     e_dem,e_rep,e_notes,row["id"]))
                                conn.commit(); st.success("✓ Mis à jour."); st.rerun()
                            if del_ok:
                                conn.execute("DELETE FROM contacts WHERE id=?", (row["id"],))
                                conn.commit(); st.rerun()
                    else:
                        v1,v2 = st.columns(2)
                        with v1:
                            for lbl,key in [("Type","type_contact"),("Email","email"),
                                            ("Tél","telephone"),("Instagram","instagram")]:
                                st.write(f"**{lbl}** : {row.get(key,'—') or '—'}")
                        with v2:
                            for lbl,key in [("Activité","activite"),("Ville","ville"),
                                            ("Adresse","adresse"),("Notes","notes")]:
                                st.write(f"**{lbl}** : {row.get(key,'—') or '—'}")

    # ── AJOUTER CONTACT ────────────────────────────────────────────────────────
    if tab_add is not None:
        with tab_add:
            st.markdown(f'<div class="section-title">Nouveau contact</div>', unsafe_allow_html=True)
            with st.form("new_contact"):
                a1,a2 = st.columns(2)
                with a1:
                    a_type  = st.selectbox("Type *", TYPES_CONTACT, key="a_type")
                    a_sous_list = SOUS_TYPES.get(a_type, ["Autre"])
                    a_sous  = st.selectbox("Sous-type", a_sous_list)
                    a_nom   = st.text_input("Nom / Prénom *")
                    a_ent   = st.text_input("Entreprise")
                    a_imp   = st.selectbox("Importance", IMPORTANCE_LIST, index=2)
                    a_dem   = st.text_input("Demandeur", placeholder="Qui a initié le contact ?")
                    a_rep   = st.text_input("Réponse / Statut")
                with a2:
                    a_mail  = st.text_input("Email")
                    a_tel   = st.text_input("Téléphone")
                    a_ig    = st.text_input("Instagram", placeholder="@handle")
                    a_act   = st.text_input("Activité")
                    a_pays  = st.selectbox("Pays", PAYS_LIST)
                    a_ville = st.text_input("Ville")
                a_adr   = st.text_input("Adresse postale")
                a_notes = st.text_area("Notes", height=60)

                if st.form_submit_button("✓ Ajouter le contact"):
                    if not a_nom:
                        st.error("Nom obligatoire.")
                    else:
                        conn.execute("""INSERT INTO contacts
                            (type_contact,sous_type,nom,entreprise,email,telephone,
                             instagram,activite,adresse,ville,pays,importance,
                             demandeur,reponse,notes)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (a_type,a_sous,a_nom,a_ent,a_mail,a_tel,
                             a_ig,a_act,a_adr,a_ville,a_pays,a_imp,
                             a_dem,a_rep,a_notes))
                        conn.commit()
                        st.success("✓ Contact ajouté."); st.rerun()

    # ── FOURNISSEURS ───────────────────────────────────────────────────────────
    with tab_fourn:
        ff1,ff2,ff3 = st.columns(3)
        with ff1:
            f_stype = st.selectbox("Type", ["Tous"]+SOUS_TYPES["Fournisseur"], key="ff_stype")
        with ff2:
            f_statf = st.selectbox("Statut", ["Tous"]+STATUT_FOURNISSEUR, key="ff_stat")
        with ff3:
            f_travf = st.selectbox("Collaboration", ["Tous","Déjà travaillé","Pas encore"], key="ff_trav")

        qf = "SELECT * FROM fournisseurs WHERE 1=1"
        pf = []
        if f_stype != "Tous":   qf += " AND sous_type=?";      pf.append(f_stype)
        if f_statf != "Tous":   qf += " AND statut_fourn=?";   pf.append(f_statf)
        if f_travf == "Déjà travaillé": qf += " AND deja_travaille=1"
        elif f_travf == "Pas encore":   qf += " AND deja_travaille=0"
        df_fourn = pd.read_sql(qf + " ORDER BY importance DESC, nom", conn, params=pf)

        if df_fourn.empty:
            st.info("Aucun fournisseur.")
        else:
            stat_colors = {
                "Actif — on travaille": EW_G,
                "À tester":             "#c9800a",
                "Out":                  "#c1440e",
                "En veille":            EW_B,
            }

            for _, row in df_fourn.iterrows():
                sc = stat_colors.get(row.get("statut_fourn",""), EW_B)
                trav_badge = (f'<span style="background:{EW_G}18;color:{EW_G};font-family:\'DM Mono\',monospace;font-size:9px;padding:2px 7px;">✓ Collaboré</span>'
                              if row.get("deja_travaille")
                              else f'<span style="background:{EW_S};color:{EW_B};font-family:\'DM Mono\',monospace;font-size:9px;padding:2px 7px;">Pas encore</span>')

                with st.expander(
                    f"{row['nom']} · {row.get('sous_type','')} · "
                    f"{row.get('ville','') or row.get('adresse','')[:20] if row.get('adresse') else ''} "
                    f"{row.get('pays','')} · {row.get('statut_fourn','')}"
                ):
                    if can_fn("contacts_edit"):
                        with st.form(f"edit_fourn_{row['id']}"):
                            ff1e,ff2e = st.columns(2)
                            with ff1e:
                                fe_nom    = st.text_input("Nom", value=row.get("nom",""))
                                fe_stype  = st.selectbox("Type", SOUS_TYPES["Fournisseur"],
                                    index=SOUS_TYPES["Fournisseur"].index(row["sous_type"]) if row.get("sous_type") in SOUS_TYPES["Fournisseur"] else 0)
                                fe_statf  = st.selectbox("Statut", STATUT_FOURNISSEUR,
                                    index=STATUT_FOURNISSEUR.index(row["statut_fourn"]) if row.get("statut_fourn") in STATUT_FOURNISSEUR else 1)
                                fe_trav   = st.checkbox("✓ Déjà collaboré", value=bool(row.get("deja_travaille",0)))
                                fe_email  = st.text_input("Email", value=row.get("email","") or "")
                                fe_tel    = st.text_input("Téléphone", value=row.get("telephone","") or "")
                            with ff2e:
                                fe_web    = st.text_input("Site web", value=row.get("site_web","") or "")
                                fe_ig     = st.text_input("Instagram", value=row.get("instagram","") or "")
                                fe_adr    = st.text_input("Adresse", value=row.get("adresse","") or "")
                                fe_ville  = st.text_input("Ville", value=row.get("ville","") or "")
                                fe_pays   = st.selectbox("Pays", PAYS_LIST,
                                    index=PAYS_LIST.index(row["pays"]) if row.get("pays") in PAYS_LIST else 0)
                                fe_imp    = st.selectbox("Importance", IMPORTANCE_LIST,
                                    index=IMPORTANCE_LIST.index(row["importance"]) if row.get("importance") in IMPORTANCE_LIST else 2)
                            fe_prods  = st.text_input("Produits fabriqués", value=row.get("produits_fabriques","") or "",
                                                       help="Sélectionner dans la liste de produits disponibles")
                            fe_moq    = st.text_input("MOQ", value=row.get("moq","") or "")
                            fe_delai  = st.text_input("Délai production", value=row.get("delai_production","") or "")
                            fe_notes  = st.text_area("Notes", value=row.get("notes","") or "", height=60)

                            fb1,fb2 = st.columns([3,1]) if can_fn("contacts_delete") else st.columns([1])
                            with fb1: fe_ok = st.form_submit_button("💾 Enregistrer")
                            fe_del = False
                            if can_fn("contacts_delete"):
                                with fb2: fe_del = st.form_submit_button("🗑")

                            if fe_ok:
                                conn.execute("""UPDATE fournisseurs SET
                                    nom=?,sous_type=?,statut_fourn=?,deja_travaille=?,
                                    email=?,telephone=?,site_web=?,instagram=?,
                                    adresse=?,ville=?,pays=?,importance=?,
                                    produits_fabriques=?,moq=?,delai_production=?,notes=?
                                    WHERE id=?""",
                                    (fe_nom,fe_stype,fe_statf,int(fe_trav),
                                     fe_email,fe_tel,fe_web,fe_ig,
                                     fe_adr,fe_ville,fe_pays,fe_imp,
                                     fe_prods,fe_moq,fe_delai,fe_notes,row["id"]))
                                conn.commit(); st.success("✓ Mis à jour."); st.rerun()
                            if fe_del:
                                conn.execute("DELETE FROM fournisseurs WHERE id=?", (row["id"],))
                                conn.commit(); st.rerun()
                    else:
                        # Vue lecture
                        st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
  <div>
    <div style="font-weight:500;font-size:14px;">{row['nom']}</div>
    <div style="font-size:12px;color:{EW_B};">{row.get('sous_type','')} · {row.get('ville','') or row.get('adresse','')}</div>
    {f'<a href="{row["site_web"]}" style="font-size:11px;color:{EW_V};">{row["site_web"]}</a>' if row.get("site_web") else ''}
    {f'<div style="font-size:11px;">{row["email"]}</div>' if row.get("email") else ''}
    {f'<div style="font-size:11px;color:{EW_B};">{row["telephone"]}</div>' if row.get("telephone") else ''}
  </div>
  <div>
    <div style="margin-bottom:6px;">{trav_badge}</div>
    {f'<div style="font-size:11px;">Produits : {row["produits_fabriques"]}</div>' if row.get("produits_fabriques") else ''}
    {f'<div style="font-size:11px;color:{EW_B};">MOQ : {row["moq"]}</div>' if row.get("moq") else ''}
    {f'<div style="font-size:11px;color:{EW_B};">Délai : {row["delai_production"]}</div>' if row.get("delai_production") else ''}
    {f'<div style="font-size:11px;color:{EW_B};margin-top:4px;">{row["notes"]}</div>' if row.get("notes") else ''}
  </div>
</div>""", unsafe_allow_html=True)

        # Ajouter fournisseur
        if can_fn("contacts_add"):
            st.markdown(f'<div class="section-title">Ajouter un fournisseur</div>', unsafe_allow_html=True)
            with st.expander("➕ Nouveau fournisseur"):
                with st.form("new_fourn"):
                    nf1,nf2 = st.columns(2)
                    with nf1:
                        nf_nom   = st.text_input("Nom *")
                        nf_stype = st.selectbox("Type", SOUS_TYPES["Fournisseur"])
                        nf_stat  = st.selectbox("Statut", STATUT_FOURNISSEUR)
                        nf_trav  = st.checkbox("Déjà collaboré")
                        nf_email = st.text_input("Email")
                        nf_tel   = st.text_input("Téléphone")
                    with nf2:
                        nf_web   = st.text_input("Site web")
                        nf_ig    = st.text_input("Instagram")
                        nf_adr   = st.text_input("Adresse")
                        nf_ville = st.text_input("Ville")
                        nf_pays  = st.selectbox("Pays", PAYS_LIST)
                        nf_imp   = st.selectbox("Importance", IMPORTANCE_LIST, index=2)
                    nf_prods = st.text_input("Produits fabriqués (si déjà collaboré)")
                    nf_moq   = st.text_input("MOQ")
                    nf_delai = st.text_input("Délai production")
                    nf_notes = st.text_area("Notes", height=50)

                    if st.form_submit_button("✓ Ajouter"):
                        if not nf_nom:
                            st.error("Nom obligatoire.")
                        else:
                            conn.execute("""INSERT INTO fournisseurs
                                (nom,sous_type,statut_fourn,deja_travaille,email,telephone,
                                 site_web,instagram,adresse,ville,pays,importance,
                                 produits_fabriques,moq,delai_production,notes)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (nf_nom,nf_stype,nf_stat,int(nf_trav),nf_email,nf_tel,
                                 nf_web,nf_ig,nf_adr,nf_ville,nf_pays,nf_imp,
                                 nf_prods,nf_moq,nf_delai,nf_notes))
                            conn.commit(); st.success("✓ Fournisseur ajouté."); st.rerun()

    # ── MODÈLE BOOKLIST ────────────────────────────────────────────────────────
    with tab_book:
        st.markdown("""
<div style="font-size:11px;color:#8a7968;margin-bottom:12px;">
Modèles avec qui on n'a pas encore travaillé — base de casting pour futurs shootings.
Les modèles avec qui on a collaboré sont dans les Collaborateurs.
</div>""", unsafe_allow_html=True)

        bm1,bm2,bm3 = st.columns(3)
        with bm1: bm_genre  = st.selectbox("Genre", ["Tous"]+GENRES_MODELE, key="bm_g")
        with bm2: bm_stat   = st.selectbox("Statut", ["Tous"]+STATUT_MODELE, key="bm_s")
        with bm3: bm_srch   = st.text_input("Recherche", placeholder="nom, style, taille...", key="bm_sr")

        qm = "SELECT * FROM modeles WHERE 1=1"
        pm = []
        if bm_genre != "Tous": qm += " AND genre=?"; pm.append(bm_genre)
        if bm_stat  != "Tous": qm += " AND statut=?"; pm.append(bm_stat)
        df_mod = pd.read_sql(qm + " ORDER BY created_at DESC", conn, params=pm)
        if bm_srch and not df_mod.empty:
            df_mod = df_mod[df_mod.apply(lambda r: bm_srch.lower() in str(r).lower(), axis=1)]

        if df_mod.empty:
            st.info("Aucun modèle dans le book.")
        else:
            # Vue grille 3 colonnes
            cols_book = st.columns(3)
            for i, (_, mod) in enumerate(df_mod.iterrows()):
                with cols_book[i % 3]:
                    # Photo
                    if mod.get("photo_data") is not None:
                        try:
                            b64 = base64.b64encode(bytes(mod["photo_data"])).decode()
                            ext = (mod["photo_nom"] or "img.jpg").split(".")[-1].lower()
                            mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                            st.markdown(f"""
<div style="aspect-ratio:2/3;background:{EW_C};overflow:hidden;margin-bottom:8px;">
  <img src="data:{mime};base64,{b64}" style="width:100%;height:100%;object-fit:cover;"/>
</div>""", unsafe_allow_html=True)
                        except Exception:
                            st.markdown(f'<div style="aspect-ratio:2/3;background:{EW_C};display:flex;align-items:center;justify-content:center;margin-bottom:8px;"><span style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_B};">PHOTO</span></div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="aspect-ratio:2/3;background:{EW_C};display:flex;align-items:center;justify-content:center;margin-bottom:8px;"><span style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_B};">PHOTO</span></div>', unsafe_allow_html=True)

                    val_c = EW_G if mod.get("valide") else EW_B
                    val_l = "✓ Validé" if mod.get("valide") else "Non validé"
                    st.markdown(f"""
<div style="margin-bottom:12px;">
  <div style="font-size:14px;font-weight:500;">{mod.get('prenom','')} {mod.get('nom','')}</div>
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_B};">
    {mod.get('genre','')} · {mod.get('localisation','') or mod.get('pays','')}
  </div>
  <div style="font-size:10px;color:{EW_B};">
    {f"H {mod['height_cm']}cm" if mod.get('height_cm') else ''} 
    {f"· {mod['taille_vetement']}" if mod.get('taille_vetement') else ''}
    {f"· P {mod['pointure']}" if mod.get('pointure') else ''}
  </div>
  {f'<div style="font-size:11px;color:{EW_B};">{mod["instagram"]}</div>' if mod.get("instagram") else ''}
  <div style="font-family:\'DM Mono\',monospace;font-size:9px;color:{val_c};margin-top:3px;">{val_l}</div>
  {f'<div style="font-size:10px;color:{EW_B};margin-top:2px;">Dispo : {mod["periode_dispo"]}</div>' if mod.get("periode_dispo") else ''}
</div>""", unsafe_allow_html=True)

                    if st.button("Fiche →", key=f"mod_{mod['id']}"):
                        st.session_state["modele_view"] = mod["id"]
                        st.rerun()

        # Fiche modèle détaillée
        if "modele_view" in st.session_state:
            mid = st.session_state["modele_view"]
            df_m = pd.read_sql("SELECT * FROM modeles WHERE id=?", conn, params=[mid])
            if df_m.empty:
                del st.session_state["modele_view"]; st.rerun()
            mod = df_m.iloc[0]

            st.markdown("---")
            if st.button("← Retour au book"):
                del st.session_state["modele_view"]; st.rerun()

            mc1,mc2 = st.columns([1,2])
            with mc1:
                if mod.get("photo_data") is not None:
                    try:
                        b64 = base64.b64encode(bytes(mod["photo_data"])).decode()
                        ext = (mod["photo_nom"] or "img.jpg").split(".")[-1].lower()
                        mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                        st.markdown(f'<div style="background:{EW_C};overflow:hidden;"><img src="data:{mime};base64,{b64}" style="width:100%;object-fit:contain;max-height:360px;"/></div>', unsafe_allow_html=True)
                    except Exception: pass
                if can_fn("contacts_edit"):
                    ph = st.file_uploader("Changer la photo", type=["png","jpg","jpeg","webp"], key=f"mph_{mid}")
                    if ph and st.button("✓ Upload", key=f"mphu_{mid}"):
                        conn.execute("UPDATE modeles SET photo_data=?,photo_nom=? WHERE id=?",
                                     (ph.read(), ph.name, mid))
                        conn.commit(); st.rerun()

            with mc2:
                st.markdown(f"<div style='font-size:22px;font-weight:500;'>{mod.get('prenom','')} {mod.get('nom','')}</div>", unsafe_allow_html=True)
                if can_fn("contacts_edit"):
                    with st.form(f"edit_mod_{mid}"):
                        mf1,mf2 = st.columns(2)
                        with mf1:
                            m_prenom = st.text_input("Prénom",    value=mod.get("prenom","") or "")
                            m_nom    = st.text_input("Nom",       value=mod.get("nom","") or "")
                            m_genre  = st.selectbox("Genre", GENRES_MODELE,
                                index=GENRES_MODELE.index(mod["genre"]) if mod.get("genre") in GENRES_MODELE else 0)
                            m_tel    = st.text_input("Téléphone", value=mod.get("telephone","") or "")
                            m_email  = st.text_input("Email",     value=mod.get("email","") or "")
                            m_ig     = st.text_input("Instagram", value=mod.get("instagram","") or "")
                            m_resp   = st.text_input("Responsable contact", value=mod.get("responsable_contact","") or "")
                        with mf2:
                            m_stat   = st.selectbox("Statut", STATUT_MODELE,
                                index=STATUT_MODELE.index(mod["statut"]) if mod.get("statut") in STATUT_MODELE else 0)
                            m_pays   = st.selectbox("Pays", PAYS_LIST,
                                index=PAYS_LIST.index(mod["pays"]) if mod.get("pays") in PAYS_LIST else 0)
                            m_loc    = st.text_input("Localisation", value=mod.get("localisation","") or "")
                            m_h      = st.number_input("Taille (cm)", min_value=0, value=int(mod.get("height_cm",0) or 0))
                            m_w      = st.number_input("Poids (kg)", min_value=0.0, value=float(mod.get("weight_kg",0) or 0))
                            m_shoe   = st.number_input("Pointure", min_value=0, value=int(mod.get("pointure",0) or 0))
                            m_size   = st.selectbox("Taille vêt.", TAILLES_VET,
                                index=TAILLES_VET.index(mod["taille_vetement"]) if mod.get("taille_vetement") in TAILLES_VET else 2)
                            m_style  = st.text_input("Style / Type", value=mod.get("style_type","") or "")
                        m_dispo  = st.text_input("Période dispo",  value=mod.get("periode_dispo","") or "")
                        m_shoot  = st.text_input("Shooting prévu", value=mod.get("shooting_prevu","") or "")
                        m_pieces = st.text_area("Pièces à porter", value=mod.get("pieces_a_porter","") or "", height=50)
                        m_tenue  = st.text_area("Tenue complète",  value=mod.get("tenue_complete","") or "", height=50)
                        m_valide = st.checkbox("✓ Validé",         value=bool(mod.get("valide",0)))
                        m_avec   = st.checkbox("✓ Déjà travaillé ensemble", value=bool(mod.get("avec_qui_travaille",0)))
                        m_notes  = st.text_area("Notes",            value=mod.get("notes","") or "", height=50)

                        mb1,mb2 = st.columns([3,1]) if can_fn("contacts_delete") else st.columns([1])
                        with mb1: mod_ok = st.form_submit_button("💾 Enregistrer")
                        mod_del = False
                        if can_fn("contacts_delete"):
                            with mb2: mod_del = st.form_submit_button("🗑")

                        if mod_ok:
                            conn.execute("""UPDATE modeles SET
                                prenom=?,nom=?,genre=?,telephone=?,email=?,instagram=?,
                                responsable_contact=?,statut=?,pays=?,localisation=?,
                                height_cm=?,weight_kg=?,pointure=?,taille_vetement=?,
                                style_type=?,periode_dispo=?,shooting_prevu=?,
                                pieces_a_porter=?,tenue_complete=?,valide=?,
                                avec_qui_travaille=?,notes=? WHERE id=?""",
                                (m_prenom,m_nom,m_genre,m_tel,m_email,m_ig,
                                 m_resp,m_stat,m_pays,m_loc,
                                 m_h,m_w,m_shoe,m_size,m_style,
                                 m_dispo,m_shoot,m_pieces,m_tenue,
                                 int(m_valide),int(m_avec),m_notes,mid))
                            conn.commit(); st.success("✓ Mis à jour."); st.rerun()
                        if mod_del:
                            conn.execute("DELETE FROM modeles WHERE id=?", (mid,))
                            conn.commit(); del st.session_state["modele_view"]; st.rerun()

        # Ajouter modèle
        if can_fn("contacts_add"):
            st.markdown(f'<div class="section-title">Ajouter au book</div>', unsafe_allow_html=True)
            with st.expander("➕ Nouveau modèle"):
                with st.form("new_modele"):
                    nm1,nm2 = st.columns(2)
                    with nm1:
                        nm_prenom= st.text_input("Prénom *")
                        nm_nom   = st.text_input("Nom *")
                        nm_genre = st.selectbox("Genre", GENRES_MODELE)
                        nm_tel   = st.text_input("Téléphone")
                        nm_email = st.text_input("Email")
                        nm_ig    = st.text_input("Instagram", placeholder="@handle")
                        nm_resp  = st.text_input("Responsable contact")
                    with nm2:
                        nm_pays  = st.selectbox("Pays", PAYS_LIST)
                        nm_loc   = st.text_input("Localisation")
                        nm_h     = st.number_input("Taille (cm)", min_value=0, value=175)
                        nm_w     = st.number_input("Poids (kg)", min_value=0.0, value=60.0)
                        nm_shoe  = st.number_input("Pointure", min_value=0, value=38)
                        nm_size  = st.selectbox("Taille vêt.", TAILLES_VET, index=2)
                        nm_style = st.text_input("Style / Type")
                    nm_dispo = st.text_input("Période disponibilité")
                    nm_notes = st.text_area("Notes", height=50)
                    nm_photo = st.file_uploader("Photo book", type=["png","jpg","jpeg","webp"])

                    if st.form_submit_button("✓ Ajouter au book"):
                        if not nm_prenom or not nm_nom:
                            st.error("Prénom et nom obligatoires.")
                        else:
                            ph_d = nm_photo.read() if nm_photo else None
                            ph_n = nm_photo.name  if nm_photo else None
                            conn.execute("""INSERT INTO modeles
                                (prenom,nom,genre,telephone,email,instagram,responsable_contact,
                                 pays,localisation,height_cm,weight_kg,pointure,taille_vetement,
                                 style_type,periode_dispo,notes,photo_data,photo_nom)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (nm_prenom,nm_nom,nm_genre,nm_tel,nm_email,nm_ig,nm_resp,
                                 nm_pays,nm_loc,nm_h,nm_w,nm_shoe,nm_size,
                                 nm_style,nm_dispo,nm_notes,ph_d,ph_n))
                            conn.commit(); st.success("✓ Modèle ajouté au book."); st.rerun()

    # ── IMPORT EXCEL ───────────────────────────────────────────────────────────
    with tab_imp:
        st.markdown('<div class="section-title">Importer des contacts depuis Excel / CSV</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="info-box">
Colonnes attendues (nom exact) :<br>
<code>nom · type_contact · sous_type · email · telephone · instagram · activite · adresse · ville · pays · importance · notes</code><br>
<strong>type_contact</strong> : Client / Fournisseur / Collaborateur / Autre
</div>""", unsafe_allow_html=True)

        # Template CSV
        import io as _io
        tmpl = pd.DataFrame([{
            "nom":"Jean Dupont","type_contact":"Client","sous_type":"VIP",
            "email":"jean@example.com","telephone":"+33 6 00 00 00 00",
            "instagram":"@jean","activite":"Retail","adresse":"Paris",
            "ville":"Paris","pays":"FR","importance":"Normal","notes":""
        }])
        buf_tmpl_ct = _io.BytesIO()
        tmpl.to_csv(buf_tmpl_ct, index=False, encoding="utf-8-sig")
        st.download_button("⬇ Template CSV", buf_tmpl_ct.getvalue(),
            file_name="template_contacts.csv", mime="text/csv")

        st.markdown("---")
        imp_ct_file = st.file_uploader("Choisir le fichier", type=["csv","xlsx","xls"], key="imp_ct")

        if imp_ct_file:
            try:
                if imp_ct_file.name.lower().endswith(".csv"):
                    df_ct_imp = pd.read_csv(imp_ct_file)
                else:
                    df_ct_imp = pd.read_excel(imp_ct_file)

                st.markdown(f"**{len(df_ct_imp)} contacts** dans le fichier")
                st.dataframe(df_ct_imp.head(5), use_container_width=True, hide_index=True)

                missing_imp = [c for c in ["nom"] if c not in df_ct_imp.columns]
                if missing_imp:
                    st.error(f"Colonne manquante : {missing_imp}")
                else:
                    if st.button(f"✓ Importer {len(df_ct_imp)} contacts", type="primary"):
                        ok_ct = 0
                        for _, r in df_ct_imp.iterrows():
                            try:
                                conn.execute("""INSERT OR IGNORE INTO contacts
                                    (type_contact,sous_type,nom,email,telephone,instagram,
                                     activite,adresse,ville,pays,importance,notes)
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                    (str(r.get("type_contact","Autre")),
                                     str(r.get("sous_type","") or ""),
                                     str(r.get("nom","")),
                                     str(r.get("email","") or ""),
                                     str(r.get("telephone","") or ""),
                                     str(r.get("instagram","") or ""),
                                     str(r.get("activite","") or ""),
                                     str(r.get("adresse","") or ""),
                                     str(r.get("ville","") or ""),
                                     str(r.get("pays","FR") or "FR"),
                                     str(r.get("importance","Normal") or "Normal"),
                                     str(r.get("notes","") or "")))
                                ok_ct += 1
                            except Exception:
                                pass
                        conn.commit()
                        st.success(f"✓ {ok_ct} contacts importés.")
                        st.rerun()
            except Exception as e:
                st.error(f"Erreur lecture fichier : {e}")

    # ── EXPORT ─────────────────────────────────────────────────────────────────
    with tab_exp:
        st.markdown(f'<div class="section-title">Export & Emailing</div>', unsafe_allow_html=True)

        df_all_ct  = pd.read_sql("SELECT * FROM contacts  ORDER BY created_at DESC", conn)
        df_all_mod = pd.read_sql("SELECT * FROM modeles   ORDER BY created_at DESC", conn)
        df_all_fh  = pd.read_sql("SELECT * FROM fournisseurs ORDER BY nom", conn)

        ex1,ex2 = st.columns(2)
        with ex1:
            exp_type = st.selectbox("Type", ["Tous"]+TYPES_CONTACT, key="exp_tc")
        with ex2:
            exp_imp  = st.selectbox("Importance", ["Toutes"]+IMPORTANCE_LIST, key="exp_imp")

        df_exp = df_all_ct.copy()
        if exp_type != "Tous":   df_exp = df_exp[df_exp["type_contact"]==exp_type]
        if exp_imp  != "Toutes": df_exp = df_exp[df_exp["importance"]==exp_imp]

        st.markdown(f"**{len(df_exp)} contacts** · {len(df_exp[df_exp['email'].fillna('').str.strip()!=''])} avec email")

        # Excel complet multi-onglets
        buf_xl = io.BytesIO()
        with pd.ExcelWriter(buf_xl, engine="openpyxl") as writer:
            df_exp.drop(columns=["id","created_at"],errors="ignore").to_excel(
                writer, sheet_name="Contacts", index=False)
            df_all_fh.drop(columns=["id","created_at"],errors="ignore").to_excel(
                writer, sheet_name="Fournisseurs", index=False)
            df_all_mod.drop(columns=["id","created_at","photo_data","photo_nom"],errors="ignore").to_excel(
                writer, sheet_name="Modèles Book", index=False)
        st.download_button(
            "⬇ Export Excel complet (Contacts + Fournisseurs + Modèles)",
            buf_xl.getvalue(),
            file_name=f"eastwood_contacts_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # CSV Brevo
        df_brevo = df_exp[df_exp["email"].fillna("").str.strip() != ""].copy()
        if not df_brevo.empty:
            brevo_out = pd.DataFrame({
                "EMAIL":     df_brevo["email"],
                "PRENOM":    df_brevo["nom"].apply(lambda x: str(x).split()[0] if x else ""),
                "NOM":       df_brevo["nom"].fillna(""),
                "SMS":       df_brevo["telephone"].fillna(""),
                "PAYS":      df_brevo["pays"].fillna(""),
                "INSTAGRAM": df_brevo.get("instagram", pd.Series([""] * len(df_brevo))).fillna(""),
                "TYPE":      df_brevo["type_contact"].fillna(""),
            })
            st.download_button(
                f"⬇ Export CSV Brevo ({len(df_brevo)} contacts avec email)",
                brevo_out.to_csv(index=False).encode("utf-8"),
                file_name="brevo_eastwood.csv", mime="text/csv"
            )
            st.markdown("""
<div class="info-box">
Import Brevo : Contacts → Importer → choisir ce fichier CSV. Les colonnes EMAIL, PRENOM, NOM, SMS, PAYS sont reconnues automatiquement.
</div>""", unsafe_allow_html=True)

    conn.close()
