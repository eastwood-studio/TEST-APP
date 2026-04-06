# ══════════════════════════════════════════════════════════════════════════════
# MODULE MARKETING & MÉDIAS
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import io

RESEAUX = {
    "Instagram": {
        "url":      "https://www.instagram.com/eastwood.fr/",
        "handle":   "@eastwood.fr",
        "color":    "#E1306C",
        "bg":       "#FFF0F5",
        "icon":     "IG",
        "desc":     "Compte principal · visuels, coulisses, drops",
    },
    "Pinterest": {
        "url":      "https://fr.pinterest.com/Eastwoodstudiofr/",
        "handle":   "Eastwoodstudiofr",
        "color":    "#E60023",
        "bg":       "#FFF0F0",
        "icon":     "PT",
        "desc":     "Moodboards, références, archives visuelles",
    },
    "TikTok": {
        "url":      "https://www.tiktok.com/@eastwood.studio",
        "handle":   "@eastwood.studio",
        "color":    "#010101",
        "bg":       "#F5F5F5",
        "icon":     "TK",
        "desc":     "Vidéos coulisses, process, storytelling",
    },
    "LinkedIn": {
        "url":      "https://www.linkedin.com/company/eastwood-studio",
        "handle":   "Eastwood Studio",
        "color":    "#0A66C2",
        "bg":       "#EEF4FB",
        "icon":     "LI",
        "desc":     "Professionnel · presse, partenariats, B2B",
    },
    "TheRedNote": {
        "url":      "https://www.xiaohongshu.com",
        "handle":   "Eastwood Studio",
        "color":    "#FF2442",
        "bg":       "#FFF0F2",
        "icon":     "XHS",
        "desc":     "Marché chinois · Xiaohongshu (小红书)",
    },
    "Site web": {
        "url":      "https://eastwood-studio.fr/boutique",
        "handle":   "eastwood-studio.fr",
        "color":    "#1a1a1a",
        "bg":       "#F7F5F0",
        "icon":     "WEB",
        "desc":     "Boutique en ligne · collections, lookbook",
    },
}

TYPES_CAMPAGNE = ["Drop collection","Shooting","Collaboration","Presse","Ads","Newsletter","Autre"]
STATUTS_CAMP   = ["Idée","En préparation","En cours","Terminé","Annulé"]


def init_marketing_db(conn):
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS stats_reseaux (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reseau TEXT,
        date_saisie TEXT,
        abonnes INTEGER DEFAULT 0,
        posts INTEGER DEFAULT 0,
        vues_mois INTEGER DEFAULT 0,
        likes_mois INTEGER DEFAULT 0,
        saves_mois INTEGER DEFAULT 0,
        partages_mois INTEGER DEFAULT 0,
        reach_mois INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS campagnes (
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


def get_latest_stats(conn):
    """Récupère les stats les plus récentes pour chaque réseau."""
    return pd.read_sql("""
        SELECT s.* FROM stats_reseaux s
        INNER JOIN (
            SELECT reseau, MAX(date_saisie) as max_date
            FROM stats_reseaux GROUP BY reseau
        ) latest ON s.reseau = latest.reseau AND s.date_saisie = latest.max_date
        ORDER BY s.reseau
    """, conn)


def get_campagnes(conn, statut=None):
    q = "SELECT * FROM campagnes WHERE 1=1"
    p = []
    if statut: q += " AND statut=?"; p.append(statut)
    return pd.read_sql(q + " ORDER BY date_debut DESC", conn, params=p)


def fmt_num(v):
    if not v or v == 0: return "—"
    v = int(v)
    if v >= 1000000: return f"{v/1000000:.1f}M"
    if v >= 1000:    return f"{v/1000:.1f}k"
    return str(v)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE MARKETING PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_marketing(can_fn, DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_marketing_db(conn)

    st.markdown("### Marketing & Médias")

    tab_reseaux, tab_stats, tab_camp, tab_saisie = st.tabs([
        "🔗 Réseaux sociaux",
        "📊 Statistiques",
        "🎯 Campagnes",
        "📝 Saisir stats",
    ])

    # ── RÉSEAUX SOCIAUX ────────────────────────────────────────────────────────
    with tab_reseaux:
        st.markdown('<div class="section-title">Présence en ligne</div>',
                    unsafe_allow_html=True)

        # Grille 3 colonnes
        cols = st.columns(3)
        for i, (name, info) in enumerate(RESEAUX.items()):
            with cols[i % 3]:
                st.markdown(f"""
<div style="background:{info['bg']};border:1px solid {info['color']}33;border-radius:6px;
     padding:16px;margin-bottom:12px;position:relative;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
    <div style="width:32px;height:32px;background:{info['color']};border-radius:6px;
         display:flex;align-items:center;justify-content:center;
         font-family:'DM Mono',monospace;font-size:9px;font-weight:500;color:#fff;
         flex-shrink:0;">{info['icon']}</div>
    <div>
      <div style="font-weight:500;font-size:13px;color:#1a1a1a;">{name}</div>
      <div style="font-family:'DM Mono',monospace;font-size:10px;color:#888078;">{info['handle']}</div>
    </div>
  </div>
  <div style="font-size:12px;color:#666058;margin-bottom:10px;line-height:1.4;">{info['desc']}</div>
  <a href="{info['url']}" target="_blank"
     style="font-family:'DM Mono',monospace;font-size:10px;color:{info['color']};
            text-decoration:none;text-transform:uppercase;letter-spacing:.06em;">
    ↗ Ouvrir
  </a>
</div>""", unsafe_allow_html=True)

        # Stats rapides si disponibles
        df_stats = get_latest_stats(conn)
        if not df_stats.empty:
            st.markdown('<div class="section-title">Aperçu stats récentes</div>',
                        unsafe_allow_html=True)
            s_cols = st.columns(len(df_stats))
            for i, (_, row) in enumerate(df_stats.iterrows()):
                with s_cols[i]:
                    info = RESEAUX.get(row["reseau"], {})
                    color = info.get("color", "#1a1a1a")
                    st.markdown(f"""
<div style="text-align:center;padding:12px;background:#f7f5f0;border:1px solid #e0dbd2;
     border-top:3px solid {color};border-radius:4px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:#aaa49a;
              text-transform:uppercase;letter-spacing:.1em;">{row['reseau']}</div>
  <div style="font-family:'DM Mono',monospace;font-size:22px;font-weight:500;
              color:#1a1a1a;margin:4px 0;">{fmt_num(row['abonnes'])}</div>
  <div style="font-size:10px;color:#888078;">abonnés</div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:#aaa49a;margin-top:4px;">
    {fmt_num(row['vues_mois'])} vues/mois
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown("""
<div class="info-box" style="margin-top:16px;">
<strong>Note Instagram API :</strong> Depuis 2024, l'API publique Instagram Basic Display est fermée.
Les statistiques précises (impressions, reach, saves) nécessitent un compte Meta Business vérifié.
Pour les données détaillées, accédez directement à Instagram Insights / TikTok Analytics / Pinterest Analytics via les apps.
Vous pouvez saisir vos stats manuellement dans l'onglet "Saisir stats".
</div>""", unsafe_allow_html=True)

    # ── STATISTIQUES DÉTAILLÉES ────────────────────────────────────────────────
    with tab_stats:
        df_stats_all = pd.read_sql(
            "SELECT * FROM stats_reseaux ORDER BY date_saisie DESC", conn)

        if df_stats_all.empty:
            st.info("Aucune statistique enregistrée. Allez dans 'Saisir stats' pour commencer.")
        else:
            # Évolution abonnés par réseau
            st.markdown('<div class="section-title">Évolution abonnés</div>',
                        unsafe_allow_html=True)

            reseaux_dispo = df_stats_all["reseau"].unique()
            sel_reseau = st.selectbox("Réseau", reseaux_dispo, key="stats_res")
            df_evo = df_stats_all[df_stats_all["reseau"] == sel_reseau].sort_values("date_saisie")

            if not df_evo.empty:
                c_s1, c_s2, c_s3, c_s4 = st.columns(4)
                latest = df_evo.iloc[-1]
                prev   = df_evo.iloc[-2] if len(df_evo) > 1 else None

                def delta_str(curr, prev_row, key):
                    if prev_row is None: return None
                    d = int(curr[key] or 0) - int(prev_row[key] or 0)
                    return f"+{d}" if d >= 0 else str(d)

                with c_s1:
                    st.metric("Abonnés", fmt_num(latest["abonnes"]),
                              delta=delta_str(latest, prev, "abonnes"))
                with c_s2:
                    st.metric("Vues/mois", fmt_num(latest["vues_mois"]),
                              delta=delta_str(latest, prev, "vues_mois"))
                with c_s3:
                    st.metric("Likes/mois", fmt_num(latest["likes_mois"]),
                              delta=delta_str(latest, prev, "likes_mois"))
                with c_s4:
                    st.metric("Reach/mois", fmt_num(latest["reach_mois"]),
                              delta=delta_str(latest, prev, "reach_mois"))

                if len(df_evo) > 1:
                    df_chart = df_evo[["date_saisie","abonnes","vues_mois"]].copy()
                    df_chart = df_chart.rename(columns={
                        "date_saisie":"Date","abonnes":"Abonnés","vues_mois":"Vues/mois"
                    }).set_index("Date")
                    st.line_chart(df_chart, use_container_width=True)

            # Tableau historique
            st.markdown('<div class="section-title">Historique complet</div>',
                        unsafe_allow_html=True)
            st.dataframe(
                df_stats_all.drop(columns=["id","created_at"], errors="ignore").rename(columns={
                    "reseau":"Réseau","date_saisie":"Date","abonnes":"Abonnés",
                    "posts":"Posts","vues_mois":"Vues/mois","likes_mois":"Likes/mois",
                    "saves_mois":"Saves/mois","partages_mois":"Partages/mois",
                    "reach_mois":"Reach/mois","notes":"Notes"
                }),
                use_container_width=True, hide_index=True
            )

            # Export
            buf_stats = io.BytesIO()
            df_stats_all.drop(columns=["id","created_at"],errors="ignore").to_excel(
                buf_stats, index=False, engine="openpyxl")
            st.download_button("⬇ Export stats Excel", buf_stats.getvalue(),
                file_name="eastwood_stats_reseaux.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── CAMPAGNES ──────────────────────────────────────────────────────────────
    with tab_camp:
        c1, c2 = st.columns(2)
        with c1:
            f_stat_camp = st.selectbox("Statut", ["Tous"]+STATUTS_CAMP, key="camp_stat")
        with c2:
            f_type_camp = st.selectbox("Type", ["Tous"]+TYPES_CAMPAGNE, key="camp_type")

        df_camp = get_campagnes(conn, statut=None if f_stat_camp=="Tous" else f_stat_camp)
        if f_type_camp != "Tous":
            df_camp = df_camp[df_camp["type_camp"]==f_type_camp]

        if df_camp.empty:
            st.info("Aucune campagne enregistrée.")
        else:
            stat_c_map = {
                "Idée":"#888","En préparation":"#c9800a",
                "En cours":"#185FA5","Terminé":"#2d6a4f","Annulé":"#c1440e"
            }
            for _, camp in df_camp.iterrows():
                sc = stat_c_map.get(camp.get("statut","Idée"), "#888")
                st.markdown(f"""
<div style="border:1px solid #e0dbd2;border-left:3px solid {sc};border-radius:2px;
     padding:14px 18px;margin:8px 0;background:#f7f5f0;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div style="flex:1;">
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:4px;">
        <span style="font-family:'DM Mono',monospace;font-size:9px;text-transform:uppercase;
                     color:{sc};letter-spacing:.1em;">{camp.get('statut','')}</span>
        <span style="font-family:'DM Mono',monospace;font-size:9px;color:#aaa49a;">{camp.get('type_camp','')}</span>
      </div>
      <div style="font-size:14px;font-weight:500;color:#1a1a1a;">{camp['titre']}</div>
      {f'<div style="font-size:12px;color:#888078;margin-top:3px;">{camp["description"]}</div>' if camp.get('description') else ''}
      {f'<div style="font-size:12px;color:#aaa49a;margin-top:2px;">Réseaux : {camp["reseaux"]}</div>' if camp.get('reseaux') else ''}
    </div>
    <div style="text-align:right;margin-left:16px;white-space:nowrap;">
      {f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;color:#1a1a1a;">{camp["budget"]:.0f} €</div>' if camp.get('budget') else ''}
      <div style="font-family:\'DM Mono\',monospace;font-size:10px;color:#aaa49a;">
        {camp.get('date_debut','')}{' → '+camp['date_fin'] if camp.get('date_fin') else ''}
      </div>
    </div>
  </div>
  {f'<div style="font-size:12px;color:#2d6a4f;margin-top:6px;border-top:1px solid #e0dbd2;padding-top:6px;">Résultats : {camp["resultats"]}</div>' if camp.get('resultats') else ''}
</div>""", unsafe_allow_html=True)

                if can_fn("settings"):
                    with st.expander(f"Modifier — {camp['titre']}"):
                        with st.form(f"edit_camp_{camp['id']}"):
                            ec1,ec2 = st.columns(2)
                            with ec1:
                                ec_stat = st.selectbox("Statut", STATUTS_CAMP,
                                    index=STATUTS_CAMP.index(camp["statut"]) if camp.get("statut") in STATUTS_CAMP else 0,
                                    key=f"ec_stat_{camp['id']}")
                                ec_res = st.text_area("Résultats", value=camp.get("resultats","") or "", height=60,
                                                       key=f"ec_res_{camp['id']}")
                            with ec2:
                                ec_bud = st.number_input("Budget (€)", value=float(camp.get("budget",0) or 0),
                                                          min_value=0.0, key=f"ec_bud_{camp['id']}")
                            bsub, bdel = st.columns([3,1])
                            with bsub: ec_ok = st.form_submit_button("💾 Enregistrer")
                            with bdel: ec_del = st.form_submit_button("🗑") if can_fn("settings") else False

                            if ec_ok:
                                conn.execute("UPDATE campagnes SET statut=?,resultats=?,budget=? WHERE id=?",
                                             (ec_stat, ec_res, ec_bud, camp["id"]))
                                conn.commit(); st.rerun()
                            if ec_del:
                                conn.execute("DELETE FROM campagnes WHERE id=?", (camp["id"],))
                                conn.commit(); st.rerun()

        # Nouvelle campagne
        st.markdown('<div class="section-title">Nouvelle campagne</div>',
                    unsafe_allow_html=True)
        with st.form("new_camp"):
            nc1,nc2,nc3 = st.columns(3)
            with nc1:
                nc_titre = st.text_input("Titre *")
                nc_type  = st.selectbox("Type", TYPES_CAMPAGNE)
            with nc2:
                nc_debut = st.date_input("Date début", value=date.today())
                nc_fin   = st.date_input("Date fin",   value=date.today())
            with nc3:
                nc_stat  = st.selectbox("Statut", STATUTS_CAMP)
                nc_bud   = st.number_input("Budget (€)", min_value=0.0, value=0.0)
            nc_reseaux = st.multiselect("Réseaux concernés", list(RESEAUX.keys()))
            nc_obj     = st.text_input("Objectif")
            nc_desc    = st.text_area("Description", height=60)

            if st.form_submit_button("✓ Créer la campagne"):
                if not nc_titre:
                    st.error("Titre obligatoire.")
                else:
                    conn.execute("""INSERT INTO campagnes
                        (titre,type_camp,reseaux,date_debut,date_fin,statut,budget,description,objectif)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                        (nc_titre, nc_type, ", ".join(nc_reseaux),
                         nc_debut.isoformat(), nc_fin.isoformat(),
                         nc_stat, nc_bud, nc_desc, nc_obj))
                    conn.commit()
                    st.success("✓ Campagne créée."); st.rerun()

    # ── SAISIR STATS ──────────────────────────────────────────────────────────
    with tab_saisie:
        st.markdown('<div class="section-title">Saisie manuelle des statistiques</div>',
                    unsafe_allow_html=True)
        st.markdown("""
<div class="info-box">
Saisissez les stats depuis vos dashboards natifs : Instagram Insights, TikTok Studio, Pinterest Analytics, LinkedIn Analytics.
</div>""", unsafe_allow_html=True)

        with st.form("saisie_stats"):
            ss1, ss2 = st.columns(2)
            with ss1:
                ss_reseau = st.selectbox("Réseau *", list(RESEAUX.keys()))
                ss_date   = st.date_input("Date de relevé", value=date.today())
                ss_abonn  = st.number_input("Abonnés",   min_value=0, value=0, step=1)
                ss_posts  = st.number_input("Nb posts",  min_value=0, value=0, step=1)
            with ss2:
                ss_vues   = st.number_input("Vues / mois",     min_value=0, value=0, step=100)
                ss_likes  = st.number_input("Likes / mois",    min_value=0, value=0, step=10)
                ss_saves  = st.number_input("Saves / mois",    min_value=0, value=0, step=10)
                ss_reach  = st.number_input("Reach / mois",    min_value=0, value=0, step=100)
                ss_parts  = st.number_input("Partages / mois", min_value=0, value=0, step=10)
            ss_notes = st.text_input("Notes", placeholder="Ex : pic à cause du reel X")

            if st.form_submit_button("✓ Enregistrer les stats"):
                conn.execute("""INSERT INTO stats_reseaux
                    (reseau,date_saisie,abonnes,posts,vues_mois,likes_mois,
                     saves_mois,partages_mois,reach_mois,notes)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (ss_reseau, ss_date.isoformat(), ss_abonn, ss_posts,
                     ss_vues, ss_likes, ss_saves, ss_parts, ss_reach, ss_notes))
                conn.commit()
                st.success(f"✓ Stats {ss_reseau} enregistrées pour le {ss_date}."); st.rerun()

    conn.close()
