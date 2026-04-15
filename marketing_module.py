# ══════════════════════════════════════════════════════════════════════════════
# MODULE MARKETING v2
# Posts par réseau · Calendrier contenu · Validation double · Alertes rythme
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
import base64
from datetime import date, datetime, timedelta

EW_V = "#7b506f"
EW_G = "#395f30"
EW_B = "#8a7968"
EW_S = "#ede3d3"
EW_C = "#f5f0e8"
EW_K = "#1a1a1a"

# ── Constantes ──────────────────────────────────────────────────────────────
RESEAUX = {
    "Instagram":   {"url": "https://www.instagram.com/eastwood.fr/",             "handle": "@eastwood.fr",       "color": "#E1306C", "objectif_semaine": 3,   "objectif_mois": 12},
    "Pinterest":   {"url": "https://fr.pinterest.com/Eastwoodstudiofr/",          "handle": "Eastwoodstudiofr",   "color": "#E60023", "objectif_semaine": 3,   "objectif_mois": 12},
    "TikTok":      {"url": "https://www.tiktok.com/@eastwood.studio",             "handle": "@eastwood.studio",   "color": "#010101", "objectif_semaine": 0,   "objectif_mois": 4},
    "TheRedNote":  {"url": "https://www.xiaohongshu.com",                         "handle": "Eastwood Studio",    "color": "#FF2442", "objectif_semaine": 3,   "objectif_mois": 12},
    "WeChat":      {"url": "https://weixin.qq.com",                               "handle": "Eastwood Studio",    "color": "#07C160", "objectif_semaine": 1,   "objectif_mois": 4},
    "LinkedIn":    {"url": "https://www.linkedin.com",                            "handle": "Eastwood Studio",    "color": "#0A66C2", "objectif_semaine": 0,   "objectif_mois": 0},
}

TYPES_POST = ["Post feed", "Story", "Reel / Vidéo", "Carrousel", "Épingle", "Article", "Autre"]

STATUTS_POST = [
    "Idée",
    "En préparation",
    "Visuels prêts",
    "Texte rédigé",
    "Proposition",        # En attente de 1ère validation
    "1 validation ✓",    # Un membre a validé
    "Validé ✓✓",         # Deux membres ont validé → prêt à publier
    "Publié",
    "Annulé",
]

# Statuts qui nécessitent 2 validations avant publication
STATUTS_VALIDATION = ["Proposition", "1 validation ✓", "Validé ✓✓"]
MEMBRES = ["Jules", "Corentin", "Alexis"]


def init_marketing_db(conn):
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reseau TEXT,
        type_post TEXT,
        titre TEXT,
        description TEXT,
        lien_visuel TEXT,
        visuel_data BLOB,
        visuel_nom TEXT,
        date_publication TEXT,
        heure_publication TEXT,
        statut TEXT DEFAULT 'Idée',
        validations TEXT DEFAULT '',
        createur TEXT,
        tags TEXT,
        produits_mis_en_avant TEXT,
        notes TEXT,
        lien_publie TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS campagnes_mk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT,
        type_camp TEXT,
        reseaux TEXT,
        date_debut TEXT,
        date_fin TEXT,
        statut TEXT DEFAULT 'Idée',
        budget REAL DEFAULT 0,
        description TEXT,
        objectif TEXT,
        resultats TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    conn.commit()


def get_posts(conn, reseau=None, statut=None, semaine=None, search=None):
    q = "SELECT * FROM posts WHERE 1=1"
    p = []
    if reseau:  q += " AND reseau=?";  p.append(reseau)
    if statut:  q += " AND statut=?";  p.append(statut)
    if semaine:
        # Filtrer par semaine ISO
        lundi = semaine
        vendredi = lundi + timedelta(days=6)
        q += " AND date_publication >= ? AND date_publication <= ?"
        p += [lundi.isoformat(), vendredi.isoformat()]
    df = pd.read_sql(q + " ORDER BY date_publication ASC, reseau ASC", conn, params=p)
    if search and not df.empty:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
    return df


def get_semaine_posts(conn, debut_semaine: date):
    """Posts de la semaine, groupés par réseau et jour."""
    fin = debut_semaine + timedelta(days=6)
    return pd.read_sql("""
        SELECT * FROM posts
        WHERE date_publication >= ? AND date_publication <= ?
        ORDER BY reseau, date_publication
    """, conn, params=[debut_semaine.isoformat(), fin.isoformat()])


def compter_posts_semaine(conn, debut_semaine: date, reseau: str) -> int:
    fin = debut_semaine + timedelta(days=6)
    row = conn.execute("""
        SELECT COUNT(*) FROM posts
        WHERE reseau=? AND date_publication >= ? AND date_publication <= ?
        AND statut NOT IN ('Annulé', 'Idée')
    """, (reseau, debut_semaine.isoformat(), fin.isoformat())).fetchone()
    return row[0] if row else 0


def ajouter_validation(conn, post_id, membre, user_display):
    """
    Ajoute une validation. Retourne le nouveau statut.
    Règle : 2 membres différents doivent valider → Validé ✓✓
    """
    row = conn.execute("SELECT validations, statut FROM posts WHERE id=?", (post_id,)).fetchone()
    if not row: return None
    validations_str, statut = row
    validations = [v for v in validations_str.split(",") if v.strip()] if validations_str else []

    # Éviter double validation du même membre
    if membre in validations:
        return statut

    validations.append(membre)
    nb = len(validations)
    nouveau_statut = "Validé ✓✓" if nb >= 2 else "1 validation ✓"

    conn.execute("""UPDATE posts SET validations=?, statut=?, updated_at=? WHERE id=?""",
                 (",".join(validations), nouveau_statut, str(date.today()), post_id))
    conn.commit()
    return nouveau_statut


def lundi_semaine(d: date) -> date:
    return d - timedelta(days=d.weekday())


# ══════════════════════════════════════════════════════════════════════════════
# PAGE MARKETING PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_marketing(can_fn, DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_marketing_db(conn)

    user = st.session_state.get("user_display","Jules").split()[0]
    today = date.today()
    lundi = lundi_semaine(today)

    st.markdown("### Marketing & Médias")

    tab_objs = st.tabs([
        "📅 Calendrier",
        "📋 Liste posts",
        "➕ Nouveau post",
        "🔗 Réseaux",
        "🎯 Campagnes",
    ])
    tab_cal, tab_list, tab_new, tab_links, tab_camp = tab_objs

    # ── CALENDRIER CONTENU ─────────────────────────────────────────────────────
    with tab_cal:
        # Sélecteur semaine
        c1,c2 = st.columns([2,1])
        with c1:
            sem_offset = st.slider("Semaine", -2, 4, 0,
                                   format="S+%d" if True else "",
                                   help="-2 = il y a 2 semaines, 0 = cette semaine, +4 = dans 4 semaines")
        with c2:
            reseau_filter = st.selectbox("Réseau", ["Tous"]+list(RESEAUX.keys()), key="cal_res")

        sem_debut = lundi + timedelta(weeks=sem_offset)
        sem_fin   = sem_debut + timedelta(days=6)
        st.markdown(f'<div class="section-title">Semaine du {sem_debut.strftime("%d %B")} au {sem_fin.strftime("%d %B %Y")}</div>', unsafe_allow_html=True)

        # Alertes rythme
        alertes = []
        for res, info in RESEAUX.items():
            if reseau_filter != "Tous" and res != reseau_filter: continue
            nb = compter_posts_semaine(conn, sem_debut, res)
            obj = info["objectif_semaine"]
            if nb < obj:
                alertes.append((res, nb, obj, info["color"]))

        if alertes:
            cols_al = st.columns(len(alertes))
            for i, (res, nb, obj, col) in enumerate(alertes):
                with cols_al[i]:
                    manque = obj - nb
                    st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};border-top:2px solid #c1440e;
     padding:8px 12px;text-align:center;">
  <div style="font-family:'DM Mono',monospace;font-size:8px;color:#c1440e;
              text-transform:uppercase;letter-spacing:.12em;">{res}</div>
  <div style="font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:#c1440e;">{nb}/{obj}</div>
  <div style="font-size:10px;color:{EW_B};">Il manque {manque} post{'s' if manque>1 else ''}</div>
</div>""", unsafe_allow_html=True)

        # Grille par jour
        jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        df_sem = get_semaine_posts(conn, sem_debut)
        if reseau_filter != "Tous" and not df_sem.empty:
            df_sem = df_sem[df_sem["reseau"]==reseau_filter]

        cols_cal = st.columns(7)
        for j in range(7):
            jour_date = sem_debut + timedelta(days=j)
            with cols_cal[j]:
                is_today = jour_date == today
                head_bg = EW_V if is_today else "transparent"
                head_c  = "#fff" if is_today else EW_K
                st.markdown(f"""
<div style="text-align:center;padding:6px 4px;background:{head_bg};margin-bottom:6px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{head_c};
              text-transform:uppercase;letter-spacing:.1em;">{jours[j]}</div>
  <div style="font-family:'DM Mono',monospace;font-size:13px;font-weight:500;color:{head_c};">
    {jour_date.day}
  </div>
</div>""", unsafe_allow_html=True)

                df_jour = df_sem[df_sem["date_publication"]==jour_date.isoformat()] if not df_sem.empty else pd.DataFrame()

                if not df_jour.empty:
                    for _, post in df_jour.iterrows():
                        res_color = RESEAUX.get(post["reseau"],{}).get("color", EW_B)
                        stat_c = {
                            "Validé ✓✓": EW_G, "Publié": EW_G,
                            "1 validation ✓": "#c9800a",
                            "Proposition": EW_V,
                            "En préparation": EW_B,
                            "Annulé": "#ccc",
                        }.get(post.get("statut",""), EW_B)

                        thumb = ""
                        if post.get("visuel_data") is not None:
                            try:
                                b64 = base64.b64encode(bytes(post["visuel_data"])).decode()
                                ext = (post["visuel_nom"] or "img.jpg").split(".")[-1].lower()
                                mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                                thumb = f'<div style="aspect-ratio:1;background:{EW_C};overflow:hidden;margin-bottom:4px;"><img src="data:{mime};base64,{b64}" style="width:100%;height:100%;object-fit:cover;"/></div>'
                            except Exception:
                                pass

                        is_publie = post.get("statut") == "Publié"
                        st.markdown(f"""
<div style="background:{'#f5fdf5' if is_publie else '#fff'};border:0.5px solid {EW_S};border-left:2px solid {res_color};
     padding:5px 7px;margin-bottom:4px;font-size:10px;">
  {thumb}
  <div style="font-family:'DM Mono',monospace;font-size:8px;color:{res_color};">{post['reseau']}</div>
  <div style="font-weight:500;line-height:1.2;margin:2px 0;">{str(post.get('titre',''))[:30]}</div>
  <div style="font-family:'DM Mono',monospace;font-size:8px;color:{stat_c};">{'✓ ' if is_publie else ''}{post.get('statut','')}</div>
  {f'<div style="font-size:8px;color:{EW_B};">{post["heure_publication"]}</div>' if post.get("heure_publication") else ''}
</div>""", unsafe_allow_html=True)

                        # Bouton "Marquer publié" direct dans le calendrier
                        if not is_publie and post.get("statut") not in ("Annulé",):
                            if st.button("✓ Publié", key=f"cal_pub_{post['id']}_{j}",
                                        help=f"Marquer '{post.get('titre','')[:20]}' comme publié"):
                                conn.execute("UPDATE posts SET statut='Publié', updated_at=? WHERE id=?",
                                             (str(date.today()), post["id"]))
                                conn.commit(); st.rerun()

        # Résumé semaine
        if not df_sem.empty:
            total_sem = len(df_sem[df_sem["statut"]!="Annulé"])
            publies   = len(df_sem[df_sem["statut"]=="Publié"])
            valides   = len(df_sem[df_sem["statut"]=="Validé ✓✓"])
            st.markdown(f"""
<div style="background:{EW_C};border:0.5px solid {EW_S};padding:10px 16px;
     margin-top:12px;display:flex;gap:24px;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;">
    <span style="color:{EW_B};">Total planifiés</span> : <strong>{total_sem}</strong>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:10px;">
    <span style="color:{EW_G};">Publiés</span> : <strong>{publies}</strong>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:10px;">
    <span style="color:{EW_V};">Prêts à publier</span> : <strong>{valides}</strong>
  </div>
</div>""", unsafe_allow_html=True)

    # ── LISTE POSTS ────────────────────────────────────────────────────────────
    with tab_list:
        fl1,fl2,fl3,fl4 = st.columns(4)
        with fl1: f_res  = st.selectbox("Réseau", ["Tous"]+list(RESEAUX.keys()), key="list_res")
        with fl2: f_stat = st.selectbox("Statut", ["Tous"]+STATUTS_POST, key="list_stat")
        with fl3: f_srch = st.text_input("Recherche", placeholder="titre, tags...", key="list_srch")
        with fl4: f_sort = st.selectbox("Trier par", ["Date publication","Plus récent","Statut"], key="list_sort")

        df_posts = get_posts(
            conn,
            reseau=None if f_res=="Tous" else f_res,
            statut=None if f_stat=="Tous" else f_stat,
            search=f_srch or None,
        )

        if df_posts.empty:
            st.info("Aucun post planifié.")
        else:
            # Stats rapides
            sl1,sl2,sl3,sl4 = st.columns(4)
            with sl1: st.metric("Total", len(df_posts))
            with sl2: st.metric("Publiés", len(df_posts[df_posts["statut"]=="Publié"]))
            with sl3: st.metric("À valider", len(df_posts[df_posts["statut"].isin(["Proposition","1 validation ✓"])]))
            with sl4: st.metric("Prêts", len(df_posts[df_posts["statut"]=="Validé ✓✓"]))

            # Trier
            if f_sort == "Date publication":
                df_posts = df_posts.sort_values("date_publication", ascending=True)
            elif f_sort == "Plus récent":
                df_posts = df_posts.sort_values("created_at", ascending=False)
            elif f_sort == "Statut":
                order = {s:i for i,s in enumerate(STATUTS_POST)}
                df_posts["_ord"] = df_posts["statut"].map(order).fillna(99)
                df_posts = df_posts.sort_values("_ord")

            for _, post in df_posts.iterrows():
                res_color = RESEAUX.get(post["reseau"],{}).get("color", EW_B)
                stat_c = {
                    "Validé ✓✓": EW_G, "Publié": EW_G,
                    "1 validation ✓": "#c9800a",
                    "Proposition": EW_V,
                    "Annulé": "#ccc",
                }.get(post.get("statut",""), EW_K)

                validations_list = [v for v in (post.get("validations","") or "").split(",") if v.strip()]

                with st.expander(
                    f"[{post['reseau']}] {post.get('titre','Sans titre')[:50]}  ·  "
                    f"{post.get('date_publication','')}  ·  {post.get('statut','')}"
                ):
                    pc1, pc2 = st.columns([2, 1])

                    with pc1:
                        # Visuel
                        if post.get("visuel_data") is not None:
                            try:
                                b64 = base64.b64encode(bytes(post["visuel_data"])).decode()
                                ext = (post["visuel_nom"] or "img.jpg").split(".")[-1].lower()
                                mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                                st.markdown(f"""
<div style="max-width:280px;background:{EW_C};overflow:hidden;margin-bottom:8px;">
  <img src="data:{mime};base64,{b64}" style="width:100%;object-fit:contain;max-height:200px;"/>
</div>""", unsafe_allow_html=True)
                            except Exception: pass
                        elif post.get("lien_visuel"):
                            st.markdown(f'<a href="{post["lien_visuel"]}" target="_blank" style="font-size:11px;color:{EW_V};">↗ Voir le visuel (Drive)</a>', unsafe_allow_html=True)

                        st.markdown(f"""
<div style="font-size:13px;font-weight:500;margin-bottom:6px;">{post.get('titre','')}</div>
<div style="font-size:12px;color:{EW_B};margin-bottom:8px;">{post.get('description','')}</div>""", unsafe_allow_html=True)

                        if post.get("tags"):
                            for tag in str(post["tags"]).split(","):
                                if tag.strip():
                                    st.markdown(f'<span style="background:{EW_C};color:{EW_B};font-family:\'DM Mono\',monospace;font-size:9px;padding:2px 7px;margin-right:4px;">{tag.strip()}</span>', unsafe_allow_html=True)

                    with pc2:
                        st.markdown(f"""
<div style="border:0.5px solid {EW_S};padding:12px;">
  <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};
              text-transform:uppercase;letter-spacing:.12em;margin-bottom:6px;">Infos</div>
  <div style="font-size:11px;margin-bottom:3px;">
    <span style="display:inline-block;width:10px;height:10px;background:{res_color};margin-right:6px;"></span>
    <strong>{post['reseau']}</strong> · {post.get('type_post','')}
  </div>
  <div style="font-size:11px;color:{EW_B};">📅 {post.get('date_publication','')} {post.get('heure_publication','') or ''}</div>
  <div style="font-size:11px;color:{EW_B};">✏️ {post.get('createur','')}</div>
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:{stat_c};margin-top:6px;">{post.get('statut','')}</div>
</div>""", unsafe_allow_html=True)

                        # Validations
                        if post.get("statut") not in ("Publié","Annulé"):
                            st.markdown(f"""
<div style="border:0.5px solid {EW_S};border-top:none;padding:10px 12px;">
  <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};
              text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;">
    Validations ({len(validations_list)}/2)
  </div>""", unsafe_allow_html=True)

                            for m in MEMBRES:
                                checked = m in validations_list
                                mc = EW_G if checked else EW_S
                                st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
  <div style="width:12px;height:12px;background:{mc};border:0.5px solid {EW_B};"></div>
  <span style="font-size:11px;">{m}</span>
</div>""", unsafe_allow_html=True)

                            st.markdown("</div>", unsafe_allow_html=True)

                            # Bouton valider pour l'utilisateur connecté
                            user_prenom = st.session_state.get("user_display","Jules").split()[0]
                            if user_prenom not in validations_list and post.get("statut") not in ("Validé ✓✓","Publié","Annulé"):
                                if st.button(f"✓ Je valide ce post", key=f"val_{post['id']}"):
                                    nouveau = ajouter_validation(conn, post["id"], user_prenom, user_prenom)
                                    st.success(f"✓ Validation ajoutée. Statut : {nouveau}"); st.rerun()
                            elif user_prenom in validations_list:
                                st.markdown(f'<div style="font-size:11px;color:{EW_G};">Tu as déjà validé ce post ✓</div>', unsafe_allow_html=True)

                        # Marquer publié
                        if post.get("statut") == "Validé ✓✓":
                            lien_pub = st.text_input("Lien du post publié", key=f"lp_{post['id']}")
                            if st.button("📢 Marquer comme publié", key=f"pub_{post['id']}"):
                                conn.execute("UPDATE posts SET statut='Publié',lien_publie=?,updated_at=? WHERE id=?",
                                             (lien_pub, str(date.today()), post["id"]))
                                conn.commit(); st.rerun()

                        # Modifier statut
                        if can_fn("stock_write") or can_fn("finance_write"):
                            new_stat = st.selectbox("Changer statut", STATUTS_POST,
                                index=STATUTS_POST.index(post["statut"]) if post.get("statut") in STATUTS_POST else 0,
                                key=f"chg_stat_{post['id']}")
                            if st.button("Appliquer", key=f"appl_{post['id']}"):
                                conn.execute("UPDATE posts SET statut=?,updated_at=? WHERE id=?",
                                             (new_stat, str(date.today()), post["id"]))
                                conn.commit(); st.rerun()

    # ── NOUVEAU POST ───────────────────────────────────────────────────────────
    with tab_new:
        st.markdown(f'<div class="section-title">Planifier un post</div>', unsafe_allow_html=True)
        with st.form("new_post"):
            np1,np2,np3 = st.columns(3)
            with np1:
                p_res  = st.selectbox("Réseau *", list(RESEAUX.keys()))
                p_type = st.selectbox("Type", TYPES_POST)
                p_date = st.date_input("Date de publication *", value=date.today())
            with np2:
                p_heure = st.text_input("Heure", placeholder="09:00", value="09:00")
                p_stat  = st.selectbox("Statut initial", STATUTS_POST[:5])  # Jusqu'à Proposition
                p_tags  = st.text_input("Tags", placeholder="#eastwood #paris #fashion")
            with np3:
                p_prods = st.text_input("Produits mis en avant", placeholder="Waterfowl Jacket")
                p_creat = st.selectbox("Créateur", MEMBRES)

            p_titre = st.text_input("Titre / Accroche *", placeholder="ex: Drop N°2 — Waterfowl en Tobacco")
            p_desc  = st.text_area("Description / Légende", height=100,
                                   placeholder="Texte du post, hashtags, mention...")
            p_lien  = st.text_input("Lien visuel (Google Drive)", placeholder="https://drive.google.com/...")
            p_visuel = st.file_uploader("Ou uploader le visuel directement",
                                        type=["png","jpg","jpeg","webp","mp4"])
            p_notes  = st.text_input("Notes internes")

            if st.form_submit_button("✓ Planifier le post"):
                if not p_titre or not p_res:
                    st.error("Réseau et titre obligatoires.")
                else:
                    vis_data = p_visuel.read() if p_visuel else None
                    vis_nom  = p_visuel.name  if p_visuel else None
                    conn.execute("""INSERT INTO posts
                        (reseau,type_post,titre,description,lien_visuel,visuel_data,visuel_nom,
                         date_publication,heure_publication,statut,createur,tags,
                         produits_mis_en_avant,notes)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (p_res,p_type,p_titre,p_desc,p_lien,vis_data,vis_nom,
                         str(p_date),p_heure,p_stat,p_creat,p_tags,p_prods,p_notes))
                    conn.commit()
                    st.success(f"✓ Post planifié pour le {p_date} sur {p_res}.")
                    st.rerun()

    # ── RÉSEAUX & LIENS ────────────────────────────────────────────────────────
    with tab_links:
        st.markdown(f'<div class="section-title">Présence en ligne</div>', unsafe_allow_html=True)

        cols_r = st.columns(3)
        for i, (name, info) in enumerate(RESEAUX.items()):
            with cols_r[i % 3]:
                # Stats posts cette semaine
                nb_this_week = compter_posts_semaine(conn, lundi, name)
                obj = info["objectif_semaine"]
                prog_c = EW_G if nb_this_week >= obj else ("#c9800a" if nb_this_week > 0 else "#c1440e")

                st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};padding:16px;margin-bottom:10px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
    <div style="width:28px;height:28px;background:{info['color']};
         display:flex;align-items:center;justify-content:center;
         font-family:'DM Mono',monospace;font-size:9px;color:#fff;">
      {name[:2].upper()}
    </div>
    <div>
      <div style="font-weight:500;font-size:13px;">{name}</div>
      <div style="font-family:'DM Mono',monospace;font-size:10px;color:{EW_B};">{info['handle']}</div>
    </div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <div style="font-size:11px;color:{EW_B};">Posts cette semaine</div>
    <div style="font-family:'DM Mono',monospace;font-size:13px;color:{prog_c};">{nb_this_week}/{obj}</div>
  </div>
  <div style="height:3px;background:{EW_S};margin-bottom:10px;">
    <div style="width:{min(nb_this_week/obj*100,100) if obj>0 else 0:.0f}%;height:3px;background:{prog_c};"></div>
  </div>
  <a href="{info['url']}" target="_blank"
     style="font-family:'DM Mono',monospace;font-size:9px;color:{info['color']};
            text-decoration:none;text-transform:uppercase;letter-spacing:.08em;">
    ↗ Ouvrir
  </a>
</div>""", unsafe_allow_html=True)

        # Objectif hebdo global
        total_posts_week = sum(compter_posts_semaine(conn, lundi, r) for r in RESEAUX)
        total_obj_week   = sum(info["objectif_semaine"] for info in RESEAUX.values())
        st.markdown(f"""
<div style="background:{EW_C};border:0.5px solid {EW_S};padding:14px 18px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};
                  text-transform:uppercase;letter-spacing:.15em;">Objectif global cette semaine</div>
      <div style="font-family:'DM Mono',monospace;font-size:22px;font-weight:500;
                  color:{EW_G if total_posts_week>=total_obj_week else EW_K};">
        {total_posts_week} / {total_obj_week} posts
      </div>
    </div>
    <div style="font-size:12px;color:{EW_B};text-align:right;">
      IG 3x · Pinterest 3x · TikTok 3x<br>TheRedNote 3x · LinkedIn 1x
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── CAMPAGNES ──────────────────────────────────────────────────────────────
    with tab_camp:
        TYPES_CAMP   = ["Drop collection","Shooting","Collaboration","Presse","Ads","Newsletter","Autre"]
        STATUTS_CAMP = ["Idée","En préparation","En cours","Terminé","Annulé"]

        df_camp = pd.read_sql("SELECT * FROM campagnes_mk ORDER BY date_debut DESC", conn)

        if not df_camp.empty:
            for _, camp in df_camp.iterrows():
                sc = {"En cours": EW_V, "Terminé": EW_G, "Annulé": "#ccc",
                      "En préparation": "#c9800a"}.get(camp.get("statut",""), EW_B)
                with st.expander(f"{camp['titre']} · {camp.get('statut','')} · {camp.get('date_debut','')}"):
                    st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
  <div>
    <div style="font-size:12px;color:{EW_B};">Type : {camp.get('type_camp','')}</div>
    <div style="font-size:12px;color:{EW_B};">Réseaux : {camp.get('reseaux','')}</div>
    <div style="font-size:12px;color:{EW_B};">{camp.get('date_debut','')} → {camp.get('date_fin','')}</div>
    {f'<div style="font-size:12px;margin-top:4px;">{camp["description"]}</div>' if camp.get('description') else ''}
  </div>
  <div>
    <div style="font-family:\'DM Mono\',monospace;font-size:9px;color:{sc};">{camp.get('statut','')}</div>
    {f'<div style="font-size:12px;">Objectif : {camp["objectif"]}</div>' if camp.get('objectif') else ''}
    {f'<div style="font-size:12px;color:{EW_G};">Résultats : {camp["resultats"]}</div>' if camp.get('resultats') else ''}
    {f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;">Budget : {float(camp["budget"]):,.0f} €</div>' if camp.get('budget') else ''}
  </div>
</div>""", unsafe_allow_html=True)
        else:
            st.info("Aucune campagne.")

        # Nouvelle campagne
        st.markdown(f'<div class="section-title">Nouvelle campagne</div>', unsafe_allow_html=True)
        with st.form("new_camp"):
            cc1,cc2,cc3 = st.columns(3)
            with cc1:
                c_titre = st.text_input("Titre *")
                c_type  = st.selectbox("Type", TYPES_CAMP)
            with cc2:
                c_debut = st.date_input("Début", value=date.today())
                c_fin   = st.date_input("Fin",   value=date.today()+timedelta(days=14))
            with cc3:
                c_stat  = st.selectbox("Statut", STATUTS_CAMP)
                c_bud   = st.number_input("Budget (€)", min_value=0.0, value=0.0)
            c_res  = st.multiselect("Réseaux", list(RESEAUX.keys()))
            c_obj  = st.text_input("Objectif")
            c_desc = st.text_area("Description", height=60)
            if st.form_submit_button("✓ Créer la campagne"):
                if not c_titre:
                    st.error("Titre obligatoire.")
                else:
                    conn.execute("""INSERT INTO campagnes_mk
                        (titre,type_camp,reseaux,date_debut,date_fin,statut,budget,description,objectif)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                        (c_titre,c_type,", ".join(c_res),str(c_debut),str(c_fin),
                         c_stat,c_bud,c_desc,c_obj))
                    conn.commit(); st.success("✓ Campagne créée."); st.rerun()

    conn.close()
