# contacts_module.py — v2.12 — 1777006711
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
    "Client":        ["Fidèle", "Ponctuel", "Potentiel", "F&F", "VIP", "Wholesale B2B", "Retail B2C"],
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
    c.execute("""CREATE TABLE IF NOT EXISTS shooting_dossiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        description TEXT DEFAULT \'\',
        collection TEXT DEFAULT \'\',
        date_shooting TEXT DEFAULT \'\',
        lieu TEXT DEFAULT \'\',
        statut TEXT DEFAULT \'En préparation\',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS shooting_modeles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shooting_id INTEGER,
        modele_id INTEGER,
        notes TEXT DEFAULT \'\',
        FOREIGN KEY(shooting_id) REFERENCES shooting_dossiers(id),
        FOREIGN KEY(modele_id) REFERENCES modeles(id)
    )""")
    # Migration : ajouter shooting_id dans modeles si absent
    _mc = [r[1] for r in c.execute("PRAGMA table_info(modeles)").fetchall()]
    if "shooting_id" not in _mc:
        try: c.execute("ALTER TABLE modeles ADD COLUMN shooting_id INTEGER DEFAULT NULL")
        except Exception: pass
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


    # ── Import one-shot des modèles du fichier source ────────────────────────
    try:
        _done = c.execute("SELECT value FROM app_settings WHERE key='modeles_imported_v1'").fetchone()
    except Exception:
        _done = None
    if not _done:
        # S'assurer que app_settings existe
        try:
            c.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT DEFAULT '')")
        except Exception: pass
        _modeles_data = [
            # (prenom, nom, genre, instagram, email, telephone, responsable, statut, pays, localisation, height_cm, weight_kg, pointure, taille_vetement, style_type, periode_dispo, shooting_prevu, pieces_a_porter, valide, notes)
            ("Nora","Innocentin","Femme","norainnocentin","","","Jules","TBD","Allemagne","Berlin",180,57.0,"41","","Cheveux bruns, blanche fine, visage carré","Juillet & Août","To set","TODO",0,""),
            ("Liya","Tuaev","Femme","aliyen22","","","Jules","Stock","Allemagne","Berlin",176,59.0,"40.5","","Iranian/Ossetian, dark hair, brown eyes","June, July, August (sauf 16-22.08)","To set","TODO",0,""),
            ("Leticia","Rese do Nascimento","Femme","tici.ratops","","","Jules","Out","Allemagne","Berlin (Tempelhof)",172,70.0,"40.5","","Brazilian, long brown hair, tanned skin","June / August","","",0,""),
            ("Leen","Mustafa","Femme","leen_mu7","","","Jules","Stock","Allemagne","Hannover",169,60.0,"39.5","","Middle Eastern, olive skin, green eyes","After July 13","Collection 2","A voir",0,""),
            ("Valeria","Leonidovna","Femme","valeriaeonidovna","","","Jules","Stock","Allemagne","Cologne",171,55.0,"38.5","","Russian-Azerbaijani, light brown hair","A la demande","Collection 2","A voir",0,""),
            ("Jolene Joy","Sommer","Femme","jolenejolier","","","Jules","Stock","Allemagne","Heidelberg",174,62.0,"41.5","","European, warm undertone, blue/green eyes","Voir divergancy.com","Collection 2","A voir",0,""),
            ("Clara Carlotta","Prott","Femme","claraa.carlotta","","","Jules","Stock","Allemagne","Münster",164,62.0,"37.5","","Brown hair, brown eyes, fair skin","Juin au 17 Août","Collection 2","Foulard",0,""),
            ("Alicia","","Femme","aliciabse","","","Jules","Stock","France","Boulogne",174,0.0,"","","Blanche bronzée, cheveux bruns","Jusqu'au 12 juin puis Sud France","Collection 2","Chemise club",0,""),
            ("Maéva","Pinquier","Femme","vhanelll","","","Jules","Oui","France","Porte de Vanves",170,0.0,"","","Blanche châtain/rousse, pommettes ressortantes","Adaptable","Collection 2","Veste Miura + foulard",1,""),
            ("Lisa","Roger","Femme","lisaargr","","","Jules","Stock","France","Yvelines",170,52.0,"38","","Brune, yeux verts, méditerranéenne","Adaptable","Collection 2","A voir",0,""),
            ("","Felflla","Femme","felflla","","","Jules","Stock","France","Paris 11ème",175,0.0,"","","Rebeu, cheveux noir long, fine","Pas dispo avant 23 Juin","Collection 2","Foulard",0,""),
            ("","Jhoanne","Femme","ljhoannes","","","Alexis","Oui","Japon","Tokyo",173,65.0,"","","Japanese/European, blond hair","","Collection 2","Foulard",1,""),
            ("","Phoebe","Femme","souljafeebs","","","Alexis","Oui","Japon","Tokyo",170,62.0,"","","Japanese – VOGUE / ELLE","12-17 July","Collection 2","Foulard",1,""),
            ("Andrei","Fiadosik","Homme","andreyfedosik","","","Jules","Oui","Allemagne","Berlin",187,74.0,"46","","Belarusian, white skin, blond hair","15-16 August","To set","TODO",1,""),
            ("Jonas","Feser","Homme","jonah.fmwd","","","Jules","Out","Allemagne","Berlin",198,82.0,"46","","German, blond hair, blue eyes","A la demande","","",0,""),
            ("Shameer Nawaz","Khan","Homme","shameersnk","","","Jules","Oui","Allemagne","Berlin (Alexanderplatz)",183,78.0,"43","","South Asian, medium brown skin, black hair","15-16 August","To set","TODO",1,""),
            ("Elijah","Diakité","Homme","elijah_diakite","","","Jules","Stock","France","Paris",186,0.0,"","","Noir, cheveux longs (Afro/tresse)","Pas dispo 5-6 Juin","Collection 2","Chemise Lutèce",0,""),
            ("Mara","Modelo","Homme","mara.dka","","","Jules","Stock","France","Asnières-sur-Seine",186,0.0,"","","Noir, cheveux court, fin","Adaptable","Collection 2","Casquette + veste gabardine",0,""),
            ("Tom","Ly Blia May","Homme","tomlbm","","","Jules","Stock","France","Paris 8ème",181,56.0,"42","","Laotien/Français/Tunisien, visage carré","Adaptable (3 sem à l'avance)","Collection 2","A voir",0,""),
            ("","Yugo","Homme","qqugo","","","Alexis","Oui","Japon","Tokyo",174,74.0,"","","Japanese/European","16-31 July","Collection 2","Foulard",1,""),
            ("Daiki","Katsumata","Homme","kkavka_","","","Alexis","Oui","Japon","Tokyo",173,43.0,"","","Japanese, long hair","","Collection 2","Foulard",1,""),
            ("Arien","Okan","Femme","arien_okan","","","Jules","Oui","Allemagne","Berlin",166,56.0,"39","","Fair skin, curly light brown hair","15-17 August","To set","TODO",1,"15 Aug jusqu''à 19h"),
            ("Kani","Marceau","Femme","kani_mrc","","","Jules","Oui","Allemagne","Berlin (Prenzlauer Berg)",167,56.0,"38","","Blanche de peau, cheveux brun foncé","15-16 August","To set","TODO",1,""),
            ("Emily","Meier","Femme","_emilymeier","","","Jules","Oui","Allemagne","Berlin (Pberg)",173,55.0,"40","","Classic, blond hair, blue/green eyes","15 Aug full, 16 No, 17 sur demande","To set","TODO",1,""),
            ("Natalia","ZT","Femme","natalia_z_t","","","Jules","TBD","Allemagne","Berlin (Friedrichshain)",177,66.0,"40","","White skin, brown hair","15 No, 16 après 15h, 17 après 12h","To set","TODO",0,""),
            ("Eric","Vinsonneau","Homme","eric.vincent.model","","","Jules","Oui","Allemagne","Berlin",187,70.0,"43","","Caucasian, dark blond hair","15-16 Aug full, 17 No","To set","TODO",1,""),
            ("Anjeza","Bullari","Femme","agnese_bullari","","","Jules","Oui","Allemagne","Berlin",173,55.6,"39","","Half Albanian/Italian, pretty face","15 No, 16-17 full","To set","TODO",1,""),
            ("Maxime","Kilic","Homme","k__omax","","","Jules","TBD","Allemagne","Berlin (Schöneweide)",183,93.0,"45","","Français d''origine turque, cheveux marron","15 full, 16 No, 17 sur demande","To set","TODO",0,""),
            ("Alexander","Schubert","Homme","_alex.schubert","","4917634430321","Jules","Oui","Allemagne","Berlin (Schöneberg)",178,70.0,"41","","White Caucasian, brown hair buzz cut","15 Aug 11-13h, 16-17 full","Berlin Shoot 4","TODO",1,""),
            ("Aleksandra Aly","Tutaj","Femme","w0rms.png","","","Jules","TBD","Allemagne","Berlin (Friedrichshain)",166,53.0,"39","","Pale white, blonde, green eyes, alternative/vintage","15 full, 16 No, 17 full","To set","A voir",0,""),
            ("Hélène","Testa","Femme","whothefuckisln","","","Jules","Oui","Allemagne","Berlin (Neukölln)",172,67.0,"38","","Française, peau européenne, cheveux bruns","15 full, 16 fin journée, 17 matin","Berlin Shoot 1 & 4","A voir",1,"Plage de sable + Bateau lac"),
            ("Julia","Jordan","Femme","juliajordan.model","","","Jules","Out","Allemagne","","","","","","","To set","TODO","",0,""),
            ("Jade","Kergroas","Femme","","jadekergroas@yahoo.fr","0624931710","Jules","Oui","France","Paris & banlieue","","","38","M","Blanche, yeux bleus-verts, cheveux châtains clairs","","CHAPTER III","A voir",1,"Taille M; H 170cm"),
            ("Ambre","Malahel","Femme","ambremll","malahel.ambre@gmail.com","0778421384","Jules","Oui","France","95 (Val-d Oise)","","","37","XS/S","Métisse Guadeloupe/France, peau matte, cheveux bouclés","A la demande","CHAPTER III","A voir",1,"Taille XS/S; H 158cm"),
            ("Foued","Belaroussi","Homme","fouedbela","fouadbelaroussi748@gmail.com","33631323435","Jules","Oui","France","Paris & banlieue","","","43","L","Rebeu, visage structuré, crâne rasé, peau mate","A la demande","CHAPTER III","A voir",1,"Taille L; H 188cm"),
        ]
        for _m in _modeles_data:
            try:
                _pr,_nm,_gn,_ig,_ml,_tel,_rs,_st,_py,_lc,_ht,_wt,_pt,_tv,_sty,_pd,_sp,_pa,_vl,_no = _m
                # Convertir height_cm
                _ht_i = 0
                if _ht:
                    try: _ht_i = int(str(_ht).replace("m","").replace("cm","").replace(" ","").split(".")[0])
                    except: pass
                c.execute("""INSERT OR IGNORE INTO modeles
                    (prenom,nom,genre,instagram,email,telephone,responsable_contact,
                     statut,pays,localisation,height_cm,weight_kg,pointure,taille_vetement,
                     style_type,periode_dispo,shooting_prevu,pieces_a_porter,valide,notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (_pr,_nm,_gn,_ig,_ml,_tel,_rs,_st,_py,_lc,
                     _ht_i,float(_wt) if _wt else 0.0,str(_pt),str(_tv),
                     _sty,_pd,_sp,_pa,int(_vl),_no))
            except Exception as _e:
                pass
        try:
            c.execute("INSERT OR REPLACE INTO app_settings (key,value) VALUES ('modeles_imported_v1','done')")
        except Exception: pass
        conn.commit()
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
def _sync_modele_to_contact(conn, mod_row):
    """Synchronise un modèle validé+email vers la table contacts.
    Crée ou met à jour le contact correspondant.
    """
    email = str(mod_row.get("email","") or "").strip()
    valide = bool(mod_row.get("valide", 0))
    if not valide or not email:
        return  # Conditions non remplies

    prenom = str(mod_row.get("prenom","") or "").strip()
    nom    = str(mod_row.get("nom","") or "").strip()
    nom_complet = f"{prenom} {nom}".strip()
    loc_raw = str(mod_row.get("localisation","") or "").strip()
    # Extraire la ville (avant la parenthèse ou virgule)
    ville = loc_raw.split("(")[0].split(",")[0].strip()
    pays  = str(mod_row.get("pays","") or "").strip()
    ig    = str(mod_row.get("instagram","") or "").strip()
    tel   = str(mod_row.get("telephone","") or "").strip()
    avec  = bool(mod_row.get("avec_qui_travaille", 0))

    type_contact = "Collaborateur"
    sous_type    = "Modèle"
    if avec:
        importance = "Normal"
        activite   = f"Modèle shoot {ville}".strip()
    else:
        importance = "Normal"
        activite   = f"Modèle shoot {ville}".strip()

    # Vérifier si le contact existe déjà (par email)
    existing = conn.execute("SELECT id FROM contacts WHERE email=?", (email,)).fetchone()
    if existing:
        conn.execute("""UPDATE contacts SET
            nom=?, type_contact=?, sous_type=?, telephone=?, instagram=?,
            activite=?, adresse=?, pays=?, importance=?
            WHERE email=?""",
            (nom_complet, type_contact, sous_type, tel, ig,
             activite, ville, pays, importance, email))
    else:
        conn.execute("""INSERT INTO contacts
            (nom, type_contact, sous_type, email, telephone, instagram,
             activite, adresse, pays, importance)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (nom_complet, type_contact, sous_type, email, tel, ig,
             activite, ville, pays, importance))
    conn.commit()



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
                _no_mail = not str(row.get("email","") or "").strip()
                _mail_flag = " ⚠ email" if _no_mail else ""
                header = (f"{emoji} {row['nom']}"
                          + (f" · {row['entreprise']}" if row.get("entreprise") else "")
                          + (f" · {row.get('pays','')}" if row.get("pays") else "")
                          + (f" · {row.get('sous_type','')}" if row.get("sous_type") else "")
                          + _mail_flag)

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
        ff1,ff2,ff3,ff4 = st.columns(4)
        with ff1:
            f_stype = st.selectbox("Type", ["Tous"]+SOUS_TYPES["Fournisseur"], key="ff_stype")
        with ff2:
            f_statf = st.selectbox("Statut", ["Tous"]+STATUT_FOURNISSEUR, key="ff_stat")
        with ff3:
            f_travf = st.selectbox("Collaboration", ["Tous","Déjà travaillé","Pas encore"], key="ff_trav")
        with ff4:
            f_pays_f = st.selectbox("Pays", ["Tous"]+PAYS_LIST, key="ff_pays")

        qf = "SELECT * FROM fournisseurs WHERE 1=1"
        pf = []
        if f_stype != "Tous":   qf += " AND sous_type=?";      pf.append(f_stype)
        if f_statf != "Tous":   qf += " AND statut_fourn=?";   pf.append(f_statf)
        if f_travf == "Déjà travaillé": qf += " AND deja_travaille=1"
        elif f_travf == "Pas encore":   qf += " AND deja_travaille=0"
        if f_pays_f != "Tous":  qf += " AND pays=?";           pf.append(f_pays_f)
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
                            fe_prods  = st.text_area("Produits fabriqués (un par ligne)", value=row.get("produits_fabriques","") or "",
                                                       height=70, help="Ex: Waterfowl Jacket (MOQ: 3, délai: 8 sem)\nAkagi Jacket (MOQ: 2, délai: 10 sem)")
                            fe_moq    = st.text_input("MOQ général", value=row.get("moq","") or "")
                            fe_delai  = st.text_input("Délai production général", value=row.get("delai_production","") or "")
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
        # ── Reset des validations one-shot ────────────────────────────────────
        try:
            _rv = conn.execute("SELECT value FROM app_settings WHERE key='valide_reset_v1'").fetchone()
        except Exception: _rv = None
        if not _rv:
            try:
                conn.execute("UPDATE modeles SET valide=0, avec_qui_travaille=0")
                conn.execute("INSERT OR REPLACE INTO app_settings (key,value) VALUES ('valide_reset_v1','done')")
                conn.commit()
            except Exception: pass

        # ── Sync modèles validés → contacts ───────────────────────────────────
        try:
            _mods_to_sync = pd.read_sql(
                "SELECT * FROM modeles WHERE valide=1 AND email IS NOT NULL AND email != ''",
                conn)
            for _, _ms in _mods_to_sync.iterrows():
                _sync_modele_to_contact(conn, _ms.to_dict())
        except Exception:
            pass

        # ── Filtres ────────────────────────────────────────────────────────────
        _bf1,_bf2,_bf3,_bf4,_bf5 = st.columns([2,2,2,2,3])
        with _bf1: bm_genre = st.selectbox("Genre", ["Tous","Femme","Homme"], key="bm_g")
        with _bf2: bm_stat  = st.selectbox("Statut", ["Tous"]+STATUT_MODELE, key="bm_s")
        with _bf3: bm_valide= st.selectbox("Relation", ["Tous","Validé","Déjà travaillé ensemble","Nouveau"], key="bm_v")
        with _bf4: bm_pays  = st.selectbox("Pays", ["Tous","Allemagne","France","Japon"], key="bm_p")
        with _bf5: bm_srch  = st.text_input("Recherche", placeholder="nom, style, pointure, city...", key="bm_sr")

        qm = "SELECT * FROM modeles WHERE 1=1"
        pm = []
        if bm_genre != "Tous": qm += " AND genre=?"; pm.append(bm_genre)
        if bm_stat  != "Tous": qm += " AND statut=?"; pm.append(bm_stat)
        if bm_pays  != "Tous": qm += " AND pays=?";   pm.append(bm_pays)
        if bm_valide == "Validé":               qm += " AND valide=1"
        elif bm_valide == "Déjà travaillé ensemble": qm += " AND avec_qui_travaille=1"
        elif bm_valide == "Nouveau":            qm += " AND valide=0 AND avec_qui_travaille=0"
        df_mod = pd.read_sql(qm + " ORDER BY nom, prenom", conn, params=pm)
        if bm_srch and not df_mod.empty:
            df_mod = df_mod[df_mod.apply(lambda r: bm_srch.lower() in str(r).lower(), axis=1)]

        st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:{EW_B};margin:4px 0 12px;">{len(df_mod)} modèle(s)</div>', unsafe_allow_html=True)

        # ── Charger les produits pour "Pièces à porter" ────────────────────────
        try:
            _prods_book = conn.execute("SELECT ref, nom, couleurs, collection FROM products ORDER BY collection, nom").fetchall()
            _colls_book = ["Toutes"] + sorted(set(p[3] for p in _prods_book if p[3]))
            _prod_map_book = {}
            for p in _prods_book:
                _prod_map_book.setdefault(p[3] or "Sans collection", []).append(f"{p[1]}{' — '+p[2] if p[2] else ''} ({p[0]})")
        except Exception:
            _prods_book = []; _colls_book = ["Toutes"]; _prod_map_book = {}

        # ── Fiches horizontales ────────────────────────────────────────────────
        if df_mod.empty:
            st.info("Aucun modèle.")
        else:
            for _, mod in df_mod.iterrows():
                mid = mod["id"]
                _editing = st.session_state.get(f"mod_edit_{mid}", False)

                # ── Statut couleur ─────────────────────────────────────────────
                _sc = {"Oui":"#395f30","Stock":"#8a7968","Out":"#ccc","TBD":"#c9800a"}.get(str(mod.get("statut","")), "#8a7968")
                _valide_dot = f'<span style="color:#395f30;font-size:13px;">●</span>' if mod.get("valide") else f'<span style="color:#d9c8ae;font-size:13px;">○</span>'
                _avec_dot   = f'<span style="color:#7b506f;font-size:13px;">●</span>' if mod.get("avec_qui_travaille") else ''

                # ── Photo ──────────────────────────────────────────────────────
                _img_html = ""
                if mod.get("photo_data") is not None:
                    try:
                        _b64 = base64.b64encode(bytes(mod["photo_data"])).decode()
                        _ext = (mod.get("photo_nom") or "img.jpg").split(".")[-1].lower()
                        _mime = "image/jpeg" if _ext in ("jpg","jpeg") else f"image/{_ext}"
                        _img_html = f'<img src="data:{_mime};base64,{_b64}" style="width:100%;height:100%;object-fit:cover;"/>'
                    except Exception: pass

                # ── Infos compactes ────────────────────────────────────────────
                _nm   = f"{mod.get('prenom','') or ''} {mod.get('nom','') or ''}".strip()
                _ht   = f"{mod.get('height_cm','')}cm" if mod.get("height_cm") else "—"
                _wt   = f"{mod.get('weight_kg','')}kg" if mod.get("weight_kg") else "—"
                _pt   = str(mod.get("pointure","") or "—")
                _tv   = str(mod.get("taille_vetement","") or "—")
                _gn   = str(mod.get("genre","") or "")
                _py   = str(mod.get("pays","") or "")
                _lc   = str(mod.get("ville","") or "")
                _ig   = str(mod.get("instagram","") or "")
                _mail = str(mod.get("email","") or "")
                _tel  = str(mod.get("telephone","") or "")
                _res  = str(mod.get("responsable_contact","") or "")
                _sty  = str(mod.get("style_type","") or "")
                _dp   = str(mod.get("periode_dispo","") or "")
                _sh   = str(mod.get("shooting_prevu","") or "")
                _pa   = str(mod.get("pieces_a_porter","") or "")
                _ten  = str(mod.get("tenue_complete","") or "")
                _no   = str(mod.get("notes","") or "")

                def _cell(label, val, flex="1", minw="60px"):
                    col = "#1a1a1a" if val and val != "—" else "#ccc"
                    v = str(val or "—").replace("<","&lt;").replace(">","&gt;")
                    return (f'<div style="border:1px solid #e8e0d4;border-radius:5px;padding:4px 9px;'
                            f'min-width:{minw};flex:{flex};background:#fff;overflow:hidden;">'
                            f'<div style="font-family:DM Mono,monospace;font-size:7px;color:#bbb;'
                            f'text-transform:uppercase;letter-spacing:.08em;white-space:nowrap;">{label}</div>'
                            f'<div style="font-size:10px;color:{col};font-weight:500;line-height:1.3;'
                            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{v}</div>'
                            f'</div>')

                _row2 = (_cell("Taille",_ht,"0","62px") + _cell("Poids",_wt,"0","62px") +
                         _cell("Pointure",_pt,"0","62px") + _cell("Taille vêt.",_tv,"0","62px") +
                         _cell("E-mail",_mail,"2","80px") + _cell("Téléphone",_tel,"1","80px"))
                _row3 = _cell("Style / Type",_sty,"2","120px") + _cell("Période dispo",_dp,"2","100px") + _cell("Shooting prévu",_sh,"1","90px")
                _row4 = _cell("Pièces à porter",_pa,"2","100px") + _cell("Tenue complète",_ten,"2","100px") + _cell("Notes",_no,"1","80px")
                _ig_tag = (f'<span style="font-family:DM Mono,monospace;font-size:8px;color:{EW_V};">@{_ig}</span>' if _ig else "")
                _av_dot = f'<span style="color:#7b506f;font-size:11px;">●</span>' if mod.get("avec_qui_travaille") else ""
                _vl_dot = f'<span style="color:#395f30;font-size:11px;">●</span>' if mod.get("valide") else f'<span style="color:#d9c8ae;font-size:11px;">○</span>'
                _photo_div = (_img_html if _img_html else
                              f'<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;'
                              f'font-family:DM Mono,monospace;font-size:8px;color:#c8bfb3;letter-spacing:.1em;">PHOTO</div>')
                _nm_esc = _nm.replace("<","&lt;").replace(">","&gt;")
                _gn_loc = f"{_gn} · {_lc}{', ' if _lc and _py else ''}{_py}"

                st.markdown(
                    f'<div style="display:flex;background:#f5f0e8;border:1px solid #d9c8ae;border-radius:8px;'
                    f'overflow:hidden;margin-bottom:8px;">'
                    f'<div style="width:280px;min-width:280px;max-width:280px;background:#e8e0d4;'
                    f'overflow:hidden;position:relative;">'
                    f'{_photo_div}'
                    f'<div style="position:absolute;top:5px;left:5px;background:rgba(255,255,255,.88);'
                    f'border-radius:3px;padding:1px 5px;font-family:DM Mono,monospace;font-size:7px;'
                    f'font-weight:700;color:{_sc};">{mod.get("statut","")}</div>'
                    f'</div>'
                    f'<div style="flex:1;padding:8px 12px;display:flex;flex-direction:column;gap:4px;min-width:0;">'
                    f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:nowrap;overflow:hidden;">'
                    f'<span style="font-size:14px;font-weight:600;color:#1a1a1a;white-space:nowrap;">{_nm_esc}</span>'
                    f'{_vl_dot}{_av_dot}'
                    f'<span style="font-family:DM Mono,monospace;font-size:8px;color:{EW_B};white-space:nowrap;">{_gn_loc}</span>'
                    f'{_ig_tag}'
                    f'<span style="margin-left:auto;font-family:DM Mono,monospace;font-size:7px;color:#bbb;white-space:nowrap;">{_res}</span>'
                    f'</div>'
                    f'<div style="display:flex;gap:4px;flex-wrap:nowrap;">{_row2}</div>'
                    f'<div style="display:flex;gap:4px;">{_row3}</div>'
                    f'<div style="display:flex;gap:4px;">{_row4}</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # ── Bouton Modifier ────────────────────────────────────────────
                _btn_cols = st.columns([1, 8])
                with _btn_cols[0]:
                    if st.button("✏️" if not _editing else "✕", key=f"mod_tog_{mid}",
                                 help="Modifier" if not _editing else "Fermer"):
                        st.session_state[f"mod_edit_{mid}"] = not _editing
                        st.rerun()

                if _editing and can_fn("contacts_edit"):
                    with st.container():
                        st.markdown(f'<div style="background:#fff;border:1px solid #d9c8ae;border-radius:6px;padding:14px;margin-bottom:8px;">', unsafe_allow_html=True)
                        with st.form(f"edit_mod_{mid}"):
                            _e1,_e2,_e3 = st.columns(3)
                            with _e1:
                                m_prenom = st.text_input("Prénom",    value=str(mod.get("prenom","") or ""))
                                m_nom    = st.text_input("Nom",       value=str(mod.get("nom","") or ""))
                                m_genre  = st.selectbox("Genre", GENRES_MODELE,
                                    index=GENRES_MODELE.index(mod["genre"]) if mod.get("genre") in GENRES_MODELE else 0)
                                m_ig     = st.text_input("Instagram", value=str(mod.get("instagram","") or ""))
                                m_mail   = st.text_input("Email",     value=str(mod.get("email","") or ""))
                                m_tel    = st.text_input("Téléphone", value=str(mod.get("telephone","") or ""))
                            with _e2:
                                m_stat   = st.selectbox("Statut", STATUT_MODELE,
                                    index=STATUT_MODELE.index(mod["statut"]) if mod.get("statut") in STATUT_MODELE else 0)
                                m_pays   = st.selectbox("Pays", PAYS_LIST,
                                    index=PAYS_LIST.index(mod["pays"]) if mod.get("pays") in PAYS_LIST else 0)
                                m_loc    = st.text_input("Ville", value=str(mod.get("ville","") or ""))
                                m_h      = st.number_input("Taille (cm)", min_value=0, value=int(mod.get("height_cm",0) or 0))
                                m_w      = st.number_input("Poids (kg)", min_value=0.0, value=float(mod.get("weight_kg",0) or 0))
                                m_shoe   = st.text_input("Pointure", value=str(mod.get("pointure","") or ""))
                                m_size   = st.text_input("Taille vêt.", value=str(mod.get("taille_vetement","") or ""))
                                m_resp   = st.text_input("Responsable", value=str(mod.get("responsable_contact","") or ""))
                            with _e3:
                                m_style  = st.text_area("Style / Type", value=str(mod.get("style_type","") or ""), height=70)
                                m_dispo  = st.text_input("Période dispo", value=str(mod.get("periode_dispo","") or ""))
                                m_shoot  = st.text_input("Shooting prévu", value=str(mod.get("shooting_prevu","") or ""))
                                m_notes  = st.text_area("Notes", value=str(mod.get("notes","") or ""), height=50)

                            # Pièces à porter : sélection par collection + produits
                            st.markdown('<div style="font-family:DM Mono,monospace;font-size:9px;color:#8a7968;text-transform:uppercase;letter-spacing:.1em;margin:6px 0 3px;">Pièces à porter</div>', unsafe_allow_html=True)
                            _pa_cols = st.columns([2,4])
                            with _pa_cols[0]:
                                _coll_filt = st.selectbox("Collection", _colls_book, key=f"pa_coll_{mid}")
                            with _pa_cols[1]:
                                _prods_filt = _prod_map_book.get(_coll_filt, []) if _coll_filt != "Toutes" else [p for ps in _prod_map_book.values() for p in ps]
                                _pa_sel = st.multiselect("Produits", _prods_filt, default=[x for x in (str(mod.get("pieces_a_porter","") or "")).split("|") if x in _prods_filt], key=f"pa_sel_{mid}")
                            m_pieces = "|".join(_pa_sel) if _pa_sel else str(mod.get("pieces_a_porter","") or "")
                            m_tenue  = st.text_area("Tenue complète", value=str(mod.get("tenue_complete","") or ""), height=50)

                            _ck1,_ck2 = st.columns(2)
                            with _ck1: m_valide = st.checkbox("✓ Validé",                   value=bool(mod.get("valide",0)))
                            with _ck2: m_avec   = st.checkbox("✓ Déjà travaillé ensemble",   value=bool(mod.get("avec_qui_travaille",0)))

                            # Photo
                            ph_up = st.file_uploader("Changer la photo (1114×552)", type=["png","jpg","jpeg","webp"], key=f"mph_{mid}")

                            _sb1,_sb2 = st.columns([4,1])
                            with _sb1: mod_ok  = st.form_submit_button("💾 Enregistrer", type="primary")
                            with _sb2: mod_del = st.form_submit_button("🗑 Supprimer") if can_fn("contacts_delete") else False

                            if mod_ok:
                                _ph_data = None; _ph_nom = None
                                if ph_up:
                                    try:
                                        from PIL import Image as _PIL; import io as _io
                                        _i = _PIL.open(ph_up).convert("RGB").resize((1114,552),_PIL.LANCZOS)
                                        _b = _io.BytesIO(); _i.save(_b,format="JPEG",quality=92)
                                        _ph_data = _b.getvalue(); _ph_nom = ph_up.name
                                    except Exception: _ph_data = ph_up.read(); _ph_nom = ph_up.name
                                if _ph_data:
                                    conn.execute("UPDATE modeles SET photo_data=?,photo_nom=? WHERE id=?", (_ph_data,_ph_nom,mid))
                                conn.execute("""UPDATE modeles SET
                                    prenom=?,nom=?,genre=?,telephone=?,email=?,instagram=?,
                                    responsable_contact=?,statut=?,pays=?,localisation=?,
                                    height_cm=?,weight_kg=?,pointure=?,taille_vetement=?,
                                    style_type=?,periode_dispo=?,shooting_prevu=?,
                                    pieces_a_porter=?,tenue_complete=?,valide=?,
                                    avec_qui_travaille=?,notes=? WHERE id=?""",
                                    (m_prenom,m_nom,m_genre,m_tel,m_mail,m_ig,
                                     m_resp,m_stat,m_pays,m_loc,
                                     m_h,m_w,str(m_shoe),str(m_size),m_style,
                                     m_dispo,m_shoot,m_pieces,m_tenue,
                                     int(m_valide),int(m_avec),m_notes,mid))
                                conn.commit()
                                # Sync vers contacts si validé + email
                                _updated_mod = {"prenom":m_prenom,"nom":m_nom,"email":m_mail,
                                    "telephone":m_tel,"instagram":m_ig,"pays":m_pays,
                                    "localisation":m_loc,"valide":int(m_valide),
                                    "avec_qui_travaille":int(m_avec)}
                                _sync_modele_to_contact(conn, _updated_mod)
                                st.session_state.pop(f"mod_edit_{mid}", None)
                                st.success("✓ Mis à jour."); st.rerun()
                            if mod_del:
                                conn.execute("DELETE FROM modeles WHERE id=?", (mid,))
                                conn.commit(); st.session_state.pop(f"mod_edit_{mid}", None); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

        # ── Ajouter un modèle ──────────────────────────────────────────────────
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
                        nm_loc   = st.text_input("Ville")
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
                            if nm_photo:
                                try:
                                    from PIL import Image as _PIL; import io as _io
                                    _i = _PIL.open(nm_photo).convert("RGB").resize((1114,552),_PIL.LANCZOS)
                                    _b = _io.BytesIO(); _i.save(_b,format="JPEG",quality=92)
                                    ph_d = _b.getvalue()
                                except Exception: ph_d = nm_photo.read()
                            else:
                                ph_d = None
                            ph_n = nm_photo.name if nm_photo else None
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

        # Export CSV contacts (3 fichiers séparés — openpyxl non dispo sur Python 3.14)
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        with col_exp1:
            buf_ct = io.BytesIO()
            df_exp.drop(columns=["id","created_at"],errors="ignore").to_csv(buf_ct, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇ Contacts CSV",
                buf_ct.getvalue(),
                file_name=f"eastwood_contacts_{date.today()}.csv",
                mime="text/csv"
            )
        with col_exp2:
            buf_fh = io.BytesIO()
            df_all_fh.drop(columns=["id","created_at"],errors="ignore").to_csv(buf_fh, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇ Fournisseurs CSV",
                buf_fh.getvalue(),
                file_name=f"eastwood_fournisseurs_{date.today()}.csv",
                mime="text/csv"
            )
        with col_exp3:
            buf_mod = io.BytesIO()
            df_all_mod.drop(columns=["id","created_at","photo_data","photo_nom"],errors="ignore").to_csv(buf_mod, index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇ Modèles CSV",
                buf_mod.getvalue(),
                file_name=f"eastwood_modeles_{date.today()}.csv",
                mime="text/csv"
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
