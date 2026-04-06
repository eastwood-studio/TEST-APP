# ══════════════════════════════════════════════════════════════════════════════
# MODULE CONTACTS — book modèles, export Brevo, catégories enrichies
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
import base64

PAYS_LIST = ["FR","JP","DE","IT","US","CN","GB","BE","ES","MX","KR","AU","BR","Autre"]
IMPORTANCE_LIST = ["Normal","Important","Prioritaire"]
TYPES_CONTACT = ["Client","Fournisseur","Collaborateur","Modèle","Autre"]
SOUS_TYPES = {
    "Client":        ["Fidèle","Ponctuel","Potentiel","F&F","VIP"],
    "Fournisseur":   ["Tissu","Composant","Packaging","Production","Logistique","Impression","Autre"],
    "Collaborateur": ["Atelier","Photographe","Graphiste","Communication","Vidéaste","Styliste","Prestataire","Autre"],
    "Modèle":        ["Femme","Homme","Non-binaire"],
    "Autre":         ["Partenaire","Presse","Investisseur","Ambassadeur","Retail","Autre"],
}
GENRES_MODELE = ["Femme","Homme","Non-binaire"]
TAILLES_VETEMENT = ["XXS","XS","S","M","L","XL","XXL"]
STATUT_MODELE = ["Actif","En pause","Archivé"]


def init_contacts_db(conn):
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
        pays TEXT,
        importance TEXT DEFAULT 'Normal',
        demandeur TEXT,
        reponse TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Migration silencieuse — ajout colonnes si absentes
    existing = [r[1] for r in c.execute("PRAGMA table_info(contacts)").fetchall()]
    for col, typedef in [
        ("demandeur", "TEXT"),
        ("reponse",   "TEXT"),
        ("sous_type", "TEXT"),
        ("instagram", "TEXT"),
        ("activite",  "TEXT"),
        ("importance","TEXT DEFAULT 'Normal'"),
    ]:
        if col not in existing:
            try:
                c.execute(f"ALTER TABLE contacts ADD COLUMN {col} {typedef}")
            except Exception:
                pass

    # Table modèles (book complet)
    c.execute("""CREATE TABLE IF NOT EXISTS modeles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        prenom TEXT,
        genre TEXT,
        telephone TEXT,
        email TEXT,
        instagram TEXT,
        facebook TEXT,
        responsable_contact TEXT,
        statut TEXT DEFAULT 'Actif',
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
        notes TEXT,
        photo_data BLOB,
        photo_nom TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    conn.commit()


def get_all_contacts(conn, type_ct=None, sous_type=None, importance=None, search=None):
    q = "SELECT * FROM contacts WHERE 1=1"
    p = []
    if type_ct:    q += " AND type_contact=?";  p.append(type_ct)
    if sous_type:  q += " AND sous_type=?";     p.append(sous_type)
    if importance: q += " AND importance=?";    p.append(importance)
    df = pd.read_sql(q + " ORDER BY type_contact, importance DESC, nom", conn, params=p)
    if search and not df.empty:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
    return df


def get_modeles(conn, statut=None, genre=None, search=None):
    q = "SELECT * FROM modeles WHERE 1=1"
    p = []
    if statut: q += " AND statut=?"; p.append(statut)
    if genre:  q += " AND genre=?";  p.append(genre)
    df = pd.read_sql(q + " ORDER BY nom, prenom", conn, params=p)
    if search and not df.empty:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
    return df


def fmt_eur(v):
    if v is None: return "—"
    return f"{v:,.2f} €".replace(",", " ")


# ── EXPORT BREVO / CSV ────────────────────────────────────────────────────────
def export_brevo(df):
    """
    Format CSV compatible Brevo (Sendinblue) :
    EMAIL, PRENOM, NOM, SMS, PAYS, ...
    """
    brevo_df = pd.DataFrame()
    brevo_df["EMAIL"]   = df["email"].fillna("")
    brevo_df["PRENOM"]  = df["nom"].apply(lambda x: str(x).split()[0] if x else "")
    brevo_df["NOM"]     = df["nom"].fillna("")
    brevo_df["SMS"]     = df["telephone"].fillna("")
    brevo_df["PAYS"]    = df["pays"].fillna("")
    brevo_df["INSTAGRAM"] = df.get("instagram", pd.Series([""] * len(df))).fillna("")
    brevo_df["TYPE"]    = df["type_contact"].fillna("")
    brevo_df["NOTES"]   = df["notes"].fillna("")
    # Exclure les lignes sans email
    brevo_df = brevo_df[brevo_df["EMAIL"].str.strip() != ""]
    return brevo_df.to_csv(index=False, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONTACTS PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_contacts(can_fn, DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_contacts_db(conn)

    st.markdown("### Contacts & Relations")

    # Tabs
    _tabs = ["📋 Répertoire", "📸 Book modèles", "📤 Export"]
    if can_fn("contacts_add"):
        _tabs.insert(2, "➕ Ajouter")
    tab_objs = st.tabs(_tabs)

    idx = 0
    tab_rep  = tab_objs[idx]; idx += 1
    tab_book = tab_objs[idx]; idx += 1
    tab_add  = tab_objs[idx] if can_fn("contacts_add") else None
    if can_fn("contacts_add"): idx += 1
    tab_exp  = tab_objs[idx]

    # ── RÉPERTOIRE ─────────────────────────────────────────────────────────────
    with tab_rep:
        c1,c2,c3,c4 = st.columns(4)
        with c1: f_tc   = st.selectbox("Type", ["Tous"]+TYPES_CONTACT, key="rep_tc")
        with c2:
            sous_opts = ["Tous"] + (SOUS_TYPES.get(f_tc, []) if f_tc != "Tous" else
                                    [s for v in SOUS_TYPES.values() for s in v])
            f_sous  = st.selectbox("Sous-type", sous_opts, key="rep_sous")
        with c3: f_imp  = st.selectbox("Importance", ["Toutes"]+IMPORTANCE_LIST, key="rep_imp")
        with c4: f_srch = st.text_input("Recherche", placeholder="nom, instagram, email...", key="rep_srch")

        df_ct = get_all_contacts(
            conn,
            type_ct    = None if f_tc   == "Tous"   else f_tc,
            sous_type  = None if f_sous  == "Tous"   else f_sous,
            importance = None if f_imp   == "Toutes" else f_imp,
            search     = f_srch or None,
        )

        # Stats rapides
        if not df_ct.empty:
            sc1,sc2,sc3,sc4 = st.columns(4)
            with sc1: st.metric("Total", len(df_ct))
            with sc2: st.metric("Prioritaires", len(df_ct[df_ct["importance"]=="Prioritaire"]))
            with sc3: st.metric("Avec email", len(df_ct[df_ct["email"].str.strip()!=""]) if "email" in df_ct else 0)
            with sc4: st.metric("Avec Instagram", len(df_ct[df_ct.get("instagram","").str.strip()!=""]) if "instagram" in df_ct else 0)

        st.markdown("")

        if df_ct.empty:
            st.info("Aucun contact dans cette sélection.")
        else:
            emoji_map = {
                "Client":"🛍️","Fournisseur":"🏭","Collaborateur":"🤝",
                "Modèle":"📸","Autre":"👤"
            }
            imp_color = {"Normal":"#888078","Important":"#c9800a","Prioritaire":"#c1440e"}
            imp_dot   = {"Normal":"●","Important":"●","Prioritaire":"●"}

            for _, row in df_ct.iterrows():
                emoji  = emoji_map.get(row.get("type_contact",""),"👤")
                imp_c  = imp_color.get(row.get("importance","Normal"),"#888")
                header = f"{emoji} {row['nom']}"
                if row.get("entreprise"): header += f" · {row['entreprise']}"
                header += f" · {row.get('pays','—')}"
                if row.get("sous_type"):  header += f" · {row['sous_type']}"

                with st.expander(header):
                    if can_fn("contacts_edit"):
                        with st.form(key=f"ct_edit_{row['id']}"):
                            f1,f2 = st.columns(2)
                            with f1:
                                e_type = st.selectbox("Type", TYPES_CONTACT,
                                    index=TYPES_CONTACT.index(row["type_contact"]) if row.get("type_contact") in TYPES_CONTACT else 0,
                                    key=f"etype_{row['id']}")
                                st_list = SOUS_TYPES.get(e_type, ["Autre"])
                                e_sous  = st.selectbox("Sous-type", st_list,
                                    index=st_list.index(row["sous_type"]) if row.get("sous_type") in st_list else 0,
                                    key=f"esous_{row['id']}")
                                e_nom   = st.text_input("Nom", value=row.get("nom","") or "", key=f"enom_{row['id']}")
                                e_ent   = st.text_input("Entreprise", value=row.get("entreprise","") or "", key=f"eent_{row['id']}")
                                e_imp   = st.selectbox("Importance", IMPORTANCE_LIST,
                                    index=IMPORTANCE_LIST.index(row["importance"]) if row.get("importance") in IMPORTANCE_LIST else 0,
                                    key=f"eimp_{row['id']}")
                                e_dem   = st.text_input("Demandeur", value=row.get("demandeur","") or "", key=f"edem_{row['id']}")
                                e_rep   = st.text_input("Réponse", value=row.get("reponse","") or "", key=f"erep_{row['id']}")
                            with f2:
                                e_mail  = st.text_input("Email", value=row.get("email","") or "", key=f"email_{row['id']}")
                                e_tel   = st.text_input("Téléphone", value=row.get("telephone","") or "", key=f"etel_{row['id']}")
                                e_ig    = st.text_input("Instagram", value=row.get("instagram","") or "", placeholder="@handle", key=f"eig_{row['id']}")
                                e_act   = st.text_input("Activité", value=row.get("activite","") or "", key=f"eact_{row['id']}")
                                e_pays  = st.selectbox("Pays", PAYS_LIST,
                                    index=PAYS_LIST.index(row["pays"]) if row.get("pays") in PAYS_LIST else 0,
                                    key=f"epays_{row['id']}")
                            e_adr   = st.text_input("Adresse postale", value=row.get("adresse","") or "", key=f"eadr_{row['id']}")
                            e_notes = st.text_area("Notes", value=row.get("notes","") or "", height=60, key=f"enotes_{row['id']}")

                            btn_cols = st.columns([3,1]) if can_fn("contacts_delete") else st.columns([1])
                            with btn_cols[0]:
                                sub_ok = st.form_submit_button("💾 Enregistrer")
                            del_ok = False
                            if can_fn("contacts_delete"):
                                with btn_cols[1]:
                                    del_ok = st.form_submit_button("🗑 Supprimer")

                            if sub_ok:
                                conn.execute("""UPDATE contacts SET
                                    type_contact=?,sous_type=?,nom=?,entreprise=?,
                                    email=?,telephone=?,instagram=?,activite=?,
                                    adresse=?,pays=?,importance=?,demandeur=?,reponse=?,notes=?
                                    WHERE id=?""",
                                    (e_type,e_sous,e_nom,e_ent,e_mail,e_tel,
                                     e_ig,e_act,e_adr,e_pays,e_imp,e_dem,e_rep,e_notes,row["id"]))
                                conn.commit()
                                st.success("✓ Contact mis à jour."); st.rerun()
                            if del_ok:
                                conn.execute("DELETE FROM contacts WHERE id=?", (row["id"],))
                                conn.commit()
                                st.success("Contact supprimé."); st.rerun()
                    else:
                        # Vue lecture
                        v1,v2 = st.columns(2)
                        with v1:
                            for lbl, key in [("Type","type_contact"),("Email","email"),
                                             ("Tél","telephone"),("Instagram","instagram")]:
                                v = row.get(key,"") or "—"
                                st.write(f"**{lbl}** : {v}")
                        with v2:
                            for lbl, key in [("Activité","activite"),("Adresse","adresse"),
                                             ("Importance","importance"),("Notes","notes")]:
                                v = row.get(key,"") or "—"
                                st.write(f"**{lbl}** : {v}")

    # ── BOOK MODÈLES ───────────────────────────────────────────────────────────
    with tab_book:
        bm_c1,bm_c2,bm_c3 = st.columns(3)
        with bm_c1: bm_statut = st.selectbox("Statut", ["Tous"]+STATUT_MODELE, key="bm_stat")
        with bm_c2: bm_genre  = st.selectbox("Genre",  ["Tous"]+GENRES_MODELE,  key="bm_gen")
        with bm_c3: bm_srch   = st.text_input("Recherche", placeholder="nom, style, taille...", key="bm_srch")

        df_mod = get_modeles(
            conn,
            statut = None if bm_statut == "Tous" else bm_statut,
            genre  = None if bm_genre  == "Tous" else bm_genre,
            search = bm_srch or None,
        )

        if df_mod.empty:
            st.info("Aucun modèle enregistré.")
        else:
            # Vue liste — cards en grille 3 colonnes
            cols_mod = st.columns(3)
            for i, (_, mod) in enumerate(df_mod.iterrows()):
                with cols_mod[i % 3]:
                    # Photo
                    if mod["photo_data"] is not None:
                        try:
                            img_bytes = bytes(mod["photo_data"])
                            b64 = base64.b64encode(img_bytes).decode()
                            ext = (mod["photo_nom"] or "img.jpg").split(".")[-1].lower()
                            mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                            st.markdown(f"""
<div style="aspect-ratio:2/3;background:#f0ece4;border-radius:6px;overflow:hidden;margin-bottom:6px;">
  <img src="data:{mime};base64,{b64}" style="width:100%;height:100%;object-fit:cover;"/>
</div>""", unsafe_allow_html=True)
                        except Exception:
                            st.markdown("""<div style="aspect-ratio:2/3;background:#f0ece4;border-radius:6px;
display:flex;align-items:center;justify-content:center;margin-bottom:6px;">
<span style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">PHOTO</span></div>""",
                                        unsafe_allow_html=True)
                    else:
                        st.markdown("""<div style="aspect-ratio:2/3;background:#f0ece4;border-radius:6px;
display:flex;align-items:center;justify-content:center;margin-bottom:6px;">
<span style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">PHOTO</span></div>""",
                                    unsafe_allow_html=True)

                    val_badge = "✓ Validé" if mod["valide"] else "Non validé"
                    val_color = "#2d6a4f" if mod["valide"] else "#888"
                    st.markdown(f"""
<div style="margin-bottom:10px;">
  <div style="font-size:14px;font-weight:500;color:#1a1a1a;">{mod['prenom']} {mod['nom']}</div>
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#888078;margin:2px 0;">
    {mod.get('genre','')} · {mod.get('localisation','') or mod.get('pays','')}
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{val_color};">{val_badge}</div>
  {'<div style="font-size:11px;color:#aaa49a;">'+mod["instagram"]+'</div>' if mod.get("instagram") else ''}
</div>""", unsafe_allow_html=True)

                    if st.button("Fiche →", key=f"mod_view_{mod['id']}"):
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

            mc1, mc2 = st.columns([1, 2])
            with mc1:
                if mod["photo_data"] is not None:
                    try:
                        img_bytes = bytes(mod["photo_data"])
                        b64 = base64.b64encode(img_bytes).decode()
                        ext = (mod["photo_nom"] or "img.jpg").split(".")[-1].lower()
                        mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                        st.markdown(f"""<div style="background:#f0ece4;border-radius:6px;overflow:hidden;">
<img src="data:{mime};base64,{b64}" style="width:100%;object-fit:contain;max-height:360px;"/></div>""",
                                    unsafe_allow_html=True)
                    except Exception:
                        pass

                if can_fn("contacts_edit"):
                    ph_up = st.file_uploader("Changer la photo", type=["png","jpg","jpeg","webp"],
                                             key=f"mod_ph_{mid}")
                    if ph_up and st.button("✓ Upload photo", key=f"mod_ph_save_{mid}"):
                        conn.execute("UPDATE modeles SET photo_data=?,photo_nom=? WHERE id=?",
                                     (ph_up.read(), ph_up.name, mid))
                        conn.commit(); st.rerun()

            with mc2:
                st.markdown(f"""
<div style="margin-bottom:12px;">
  <div style="font-size:22px;font-weight:500;">{mod['prenom']} {mod['nom']}</div>
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#888078;margin-top:4px;">
    {mod.get('genre','')} · {'✓ Validé' if mod['valide'] else 'Non validé'} · {mod.get('statut','')}
  </div>
</div>""", unsafe_allow_html=True)

                if can_fn("contacts_edit"):
                    with st.form(f"mod_edit_{mid}"):
                        mf1,mf2 = st.columns(2)
                        with mf1:
                            m_prenom  = st.text_input("Prénom",    value=mod.get("prenom","") or "")
                            m_nom     = st.text_input("Nom",       value=mod.get("nom","") or "")
                            m_genre   = st.selectbox("Genre", GENRES_MODELE,
                                index=GENRES_MODELE.index(mod["genre"]) if mod.get("genre") in GENRES_MODELE else 0)
                            m_tel     = st.text_input("Téléphone", value=mod.get("telephone","") or "")
                            m_email   = st.text_input("Email",     value=mod.get("email","") or "")
                            m_ig      = st.text_input("Instagram", value=mod.get("instagram","") or "")
                            m_fb      = st.text_input("Facebook",  value=mod.get("facebook","") or "")
                            m_resp    = st.text_input("Responsable contact", value=mod.get("responsable_contact","") or "")
                        with mf2:
                            m_stat   = st.selectbox("Statut", STATUT_MODELE,
                                index=STATUT_MODELE.index(mod["statut"]) if mod.get("statut") in STATUT_MODELE else 0)
                            m_pays   = st.selectbox("Pays", PAYS_LIST,
                                index=PAYS_LIST.index(mod["pays"]) if mod.get("pays") in PAYS_LIST else 0)
                            m_loc    = st.text_input("Localisation", value=mod.get("localisation","") or "")
                            m_height = st.number_input("Taille (cm)", min_value=0, value=int(mod.get("height_cm",0) or 0))
                            m_weight = st.number_input("Poids (kg)",  min_value=0.0, value=float(mod.get("weight_kg",0) or 0))
                            m_shoe   = st.number_input("Pointure",    min_value=0, value=int(mod.get("pointure",0) or 0))
                            m_size   = st.selectbox("Taille vêtement", TAILLES_VETEMENT,
                                index=TAILLES_VETEMENT.index(mod["taille_vetement"]) if mod.get("taille_vetement") in TAILLES_VETEMENT else 2)
                            m_style  = st.text_input("Style / Type", value=mod.get("style_type","") or "")

                        m_dispo   = st.text_input("Période disponibilité", value=mod.get("periode_dispo","") or "")
                        m_shoot   = st.text_input("Shooting prévu",        value=mod.get("shooting_prevu","") or "")
                        m_pieces  = st.text_area("Pièces à porter",        value=mod.get("pieces_a_porter","") or "", height=60)
                        m_tenue   = st.text_area("Tenue complète",         value=mod.get("tenue_complete","") or "", height=60)
                        m_valide  = st.checkbox("✓ Validé",                value=bool(mod.get("valide",0)))
                        m_notes   = st.text_area("Notes",                  value=mod.get("notes","") or "", height=60)

                        bm1,bm2 = st.columns([3,1]) if can_fn("contacts_delete") else st.columns([1])
                        with bm1:
                            mod_ok = st.form_submit_button("💾 Enregistrer")
                        mod_del = False
                        if can_fn("contacts_delete"):
                            with bm2:
                                mod_del = st.form_submit_button("🗑 Supprimer")

                        if mod_ok:
                            conn.execute("""UPDATE modeles SET
                                prenom=?,nom=?,genre=?,telephone=?,email=?,instagram=?,facebook=?,
                                responsable_contact=?,statut=?,pays=?,localisation=?,
                                height_cm=?,weight_kg=?,pointure=?,taille_vetement=?,style_type=?,
                                periode_dispo=?,shooting_prevu=?,pieces_a_porter=?,tenue_complete=?,
                                valide=?,notes=? WHERE id=?""",
                                (m_prenom,m_nom,m_genre,m_tel,m_email,m_ig,m_fb,
                                 m_resp,m_stat,m_pays,m_loc,
                                 m_height,m_weight,m_shoe,m_size,m_style,
                                 m_dispo,m_shoot,m_pieces,m_tenue,
                                 int(m_valide),m_notes,mid))
                            conn.commit()
                            st.success("✓ Modèle mis à jour."); st.rerun()
                        if mod_del:
                            conn.execute("DELETE FROM modeles WHERE id=?", (mid,))
                            conn.commit()
                            del st.session_state["modele_view"]
                            st.success("Modèle supprimé."); st.rerun()
                else:
                    # Vue lecture
                    infos = [
                        ("Genre", mod.get("genre","")), ("Taille", f"{mod.get('height_cm','')} cm"),
                        ("Poids", f"{mod.get('weight_kg','')} kg"), ("Pointure", mod.get("pointure","")),
                        ("Taille vêt.", mod.get("taille_vetement","")), ("Style", mod.get("style_type","")),
                        ("Instagram", mod.get("instagram","")), ("Email", mod.get("email","")),
                        ("Tél", mod.get("telephone","")), ("Dispo", mod.get("periode_dispo","")),
                    ]
                    v1,v2 = st.columns(2)
                    for i,(lbl,val) in enumerate(infos):
                        with (v1 if i%2==0 else v2):
                            st.write(f"**{lbl}** : {val or '—'}")

        # Ajouter un nouveau modèle
        if can_fn("contacts_add"):
            st.markdown("---")
            st.markdown('<div class="section-title">Ajouter un modèle</div>', unsafe_allow_html=True)
            with st.expander("➕ Nouveau modèle"):
                with st.form("new_modele"):
                    nm1,nm2 = st.columns(2)
                    with nm1:
                        nm_prenom = st.text_input("Prénom *")
                        nm_nom    = st.text_input("Nom *")
                        nm_genre  = st.selectbox("Genre", GENRES_MODELE)
                        nm_tel    = st.text_input("Téléphone")
                        nm_email  = st.text_input("Email")
                        nm_ig     = st.text_input("Instagram", placeholder="@handle")
                        nm_resp   = st.text_input("Responsable contact")
                    with nm2:
                        nm_pays   = st.selectbox("Pays", PAYS_LIST)
                        nm_loc    = st.text_input("Localisation")
                        nm_height = st.number_input("Taille (cm)", min_value=0, value=175)
                        nm_weight = st.number_input("Poids (kg)",  min_value=0.0, value=60.0)
                        nm_shoe   = st.number_input("Pointure",    min_value=0, value=38)
                        nm_size   = st.selectbox("Taille vêt.", TAILLES_VETEMENT, index=2)
                        nm_style  = st.text_input("Style / Type")
                    nm_dispo  = st.text_input("Période disponibilité")
                    nm_notes  = st.text_area("Notes", height=60)
                    nm_photo  = st.file_uploader("Photo book", type=["png","jpg","jpeg","webp"])

                    if st.form_submit_button("✓ Ajouter le modèle"):
                        if not nm_prenom or not nm_nom:
                            st.error("Prénom et nom obligatoires.")
                        else:
                            photo_data = nm_photo.read() if nm_photo else None
                            photo_nom  = nm_photo.name  if nm_photo else None
                            conn.execute("""INSERT INTO modeles
                                (prenom,nom,genre,telephone,email,instagram,responsable_contact,
                                 pays,localisation,height_cm,weight_kg,pointure,taille_vetement,
                                 style_type,periode_dispo,notes,photo_data,photo_nom)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (nm_prenom,nm_nom,nm_genre,nm_tel,nm_email,nm_ig,nm_resp,
                                 nm_pays,nm_loc,nm_height,nm_weight,nm_shoe,nm_size,
                                 nm_style,nm_dispo,nm_notes,photo_data,photo_nom))
                            conn.commit()
                            st.success("✓ Modèle ajouté."); st.rerun()

    # ── AJOUT CONTACT ──────────────────────────────────────────────────────────
    if tab_add is not None:
        with tab_add:
            st.markdown('<div class="section-title">Nouveau contact</div>', unsafe_allow_html=True)
            a1,a2 = st.columns(2)
            with a1:
                a_type  = st.selectbox("Type *", TYPES_CONTACT, key="a_type")
                a_sstype_list = SOUS_TYPES.get(a_type, ["Autre"])
                a_sous  = st.selectbox("Sous-type", a_sstype_list, key="a_sous")
                a_nom   = st.text_input("Nom / Prénom *")
                a_ent   = st.text_input("Entreprise")
                a_imp   = st.selectbox("Importance", IMPORTANCE_LIST)
                a_dem   = st.text_input("Demandeur", placeholder="Qui a pris contact ?")
                a_rep   = st.text_input("Réponse", placeholder="Réponse donnée / statut")
            with a2:
                a_mail  = st.text_input("Email")
                a_tel   = st.text_input("Téléphone")
                a_ig    = st.text_input("Instagram", placeholder="@handle")
                a_act   = st.text_input("Activité")
                a_pays  = st.selectbox("Pays", PAYS_LIST)
            a_adr   = st.text_input("Adresse postale")
            a_notes = st.text_area("Notes", height=72)

            if st.button("✓ Ajouter le contact"):
                if not a_nom:
                    st.error("Nom obligatoire.")
                else:
                    conn.execute("""INSERT INTO contacts
                        (type_contact,sous_type,nom,entreprise,email,telephone,
                         instagram,activite,adresse,pays,importance,demandeur,reponse,notes)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (a_type,a_sous,a_nom,a_ent,a_mail,a_tel,
                         a_ig,a_act,a_adr,a_pays,a_imp,a_dem,a_rep,a_notes))
                    conn.commit()
                    st.success("✓ Contact ajouté."); st.rerun()

    # ── EXPORT ─────────────────────────────────────────────────────────────────
    with tab_exp:
        st.markdown('<div class="section-title">Export & Emailing</div>', unsafe_allow_html=True)

        df_all = get_all_contacts(conn)
        df_mod_all = get_modeles(conn)

        if df_all.empty:
            st.info("Aucun contact à exporter.")
        else:
            # Sélection pour export
            ex1,ex2 = st.columns(2)
            with ex1:
                exp_type = st.selectbox("Filtrer par type", ["Tous"]+TYPES_CONTACT, key="exp_type")
            with ex2:
                exp_imp  = st.selectbox("Filtrer par importance", ["Toutes"]+IMPORTANCE_LIST, key="exp_imp")

            df_exp = df_all.copy()
            if exp_type != "Tous":   df_exp = df_exp[df_exp["type_contact"]==exp_type]
            if exp_imp  != "Toutes": df_exp = df_exp[df_exp["importance"]==exp_imp]

            st.markdown(f"**{len(df_exp)} contacts sélectionnés** · {len(df_exp[df_exp['email'].str.strip()!=''])} avec email")

            st.markdown("---")

            # Export 1 : Excel complet
            buf_xl = io.BytesIO()
            with pd.ExcelWriter(buf_xl, engine="openpyxl") as writer:
                df_exp.drop(columns=["id","created_at"],errors="ignore").to_excel(
                    writer, sheet_name="Contacts", index=False)
                if not df_mod_all.empty:
                    df_mod_all.drop(columns=["id","created_at","photo_data","photo_nom"],errors="ignore").to_excel(
                        writer, sheet_name="Modèles", index=False)
            st.download_button(
                "⬇ Export Excel complet (Contacts + Modèles)",
                buf_xl.getvalue(),
                file_name="eastwood_contacts_complet.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.markdown("")

            # Export 2 : CSV Brevo
            df_avec_email = df_exp[df_exp["email"].str.strip() != ""]
            if not df_avec_email.empty:
                csv_brevo = export_brevo(df_avec_email)
                st.download_button(
                    f"⬇ Export CSV Brevo ({len(df_avec_email)} contacts avec email)",
                    csv_brevo.encode("utf-8"),
                    file_name="brevo_import_eastwood.csv",
                    mime="text/csv"
                )
                st.markdown("""
<div class="info-box">
<strong>Import Brevo :</strong> Dans Brevo → Contacts → Importer des contacts → Téléverser ce fichier CSV.
Les colonnes EMAIL, PRENOM, NOM, SMS, PAYS sont reconnues automatiquement.
</div>""", unsafe_allow_html=True)
            else:
                st.info("Aucun contact avec email dans cette sélection.")

            st.markdown("---")

            # Export 3 : CSV modèles
            if not df_mod_all.empty:
                buf_mod = io.BytesIO()
                df_mod_all.drop(columns=["photo_data","photo_nom"],errors="ignore").to_excel(
                    buf_mod, index=False, engine="openpyxl")
                st.download_button(
                    f"⬇ Export book modèles ({len(df_mod_all)} modèles)",
                    buf_mod.getvalue(),
                    file_name="eastwood_modeles.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    conn.close()
