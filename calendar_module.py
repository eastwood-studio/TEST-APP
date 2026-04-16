# calendar_module.py — v2.6 — 1776288194
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
import io

EMAILS_FONDATEURS = [
    "alexis.barsus@gmail.com",
    "cobolou@laposte.net",
    "jules@eastwood-studio.fr",
]

TYPES_EVENT = ["Fashion Week", "Drop collection", "Shooting", "Pop-up", "Réunion", "Salon", "Deadline", "Autre"]
EVENT_COLORS = {
    "Fashion Week":   "#534AB7",
    "Drop collection":"#c9800a",
    "Shooting":       "#0F6E56",
    "Pop-up":         "#D85A30",
    "Réunion":        "#185FA5",
    "Salon":          "#72243E",
    "Deadline":       "#c1440e",
    "Autre":          "#888078",
}

# Fashion Weeks — PFW + TFW Tokyo
FASHION_WEEKS = [
    # ── Paris Fashion Week ────────────────────────────────────────────────────
    # PFW SS26 (Homme — Jan 2026)
    {"date": date(2026, 1, 21), "label": "PFW SS26 Homme — Ouverture", "type": "Fashion Week",
     "detail": "Paris Fashion Week Homme Printemps-Été 2026 · 21-25 jan 2026"},
    {"date": date(2026, 1, 25), "label": "PFW SS26 Homme — Clôture",   "type": "Fashion Week",
     "detail": "Fin semaine collections homme Paris SS26"},
    # PFW FW26 (Femme — Mars 2026)
    {"date": date(2026, 2, 24), "label": "PFW FW26 Femme — Ouverture", "type": "Fashion Week",
     "detail": "Paris Fashion Week Femme Automne-Hiver 2026 · 24 fév - 4 mars"},
    {"date": date(2026, 3, 4),  "label": "PFW FW26 Femme — Clôture",   "type": "Fashion Week",
     "detail": "Fin semaine collections femme Paris FW26"},
    # PFW SS27 (Homme — Juin 2026)
    {"date": date(2026, 6, 23), "label": "PFW SS27 Homme — Ouverture", "type": "Fashion Week",
     "detail": "Paris Fashion Week Homme Printemps-Été 2027"},
    # PFW FW27 (Femme — Sept-Oct 2026)
    {"date": date(2026, 9, 28), "label": "PFW FW27 Femme — Ouverture", "type": "Fashion Week",
     "detail": "Paris Fashion Week Femme Automne-Hiver 2027"},
    # ── Tokyo Fashion Week ────────────────────────────────────────────────────
    # TFW Rakuten SS26 (Mars 2026)
    {"date": date(2026, 3, 16), "label": "TFW SS26 — Rakuten Tokyo",    "type": "Fashion Week",
     "detail": "Tokyo Fashion Week Rakuten Printemps-Été 2026 · 16-21 mars 2026"},
    {"date": date(2026, 3, 21), "label": "TFW SS26 — Clôture",          "type": "Fashion Week",
     "detail": "Fin Tokyo Fashion Week SS26"},
    # TFW Rakuten FW26 (Oct 2026)
    {"date": date(2026, 10, 12), "label": "TFW FW26 — Rakuten Tokyo",   "type": "Fashion Week",
     "detail": "Tokyo Fashion Week Rakuten Automne-Hiver 2026 · oct 2026"},
    # ── Eastwood drops ────────────────────────────────────────────────────────
    {"date": date(2026, 6, 15), "label": "Drop Chapter I — Waterfowl","type": "Drop collection",
     "detail": "Drop Chapter I · Hunting & Fishing · livraison juin 2026"},
    {"date": date(2026, 7, 1),  "label": "Drop Chapter II — Souvenir","type": "Drop collection",
     "detail": "Drop Chapter II · Le Souvenir · livraison juillet 2026"},
]

EMAIL_INVITATION = "contact.eastwoodstudio@gmail.com"
ASSIGNEES_OBJ = ["Eastwood Studio", "Jules", "Corentin", "Alexis"]


def init_calendar_db(conn):
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT NOT NULL,
        type_event TEXT,
        date_debut TEXT NOT NULL,
        date_fin TEXT,
        heure TEXT,
        lieu TEXT,
        description TEXT,
        meet_link TEXT,
        recurrent INTEGER DEFAULT 0,
        freq_recurrence TEXT,
        created_by TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS objectifs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT,
        collection TEXT,
        type_obj TEXT,
        date_cible TEXT,
        description TEXT,
        statut TEXT DEFAULT 'En cours',
        priorite TEXT DEFAULT 'Normal',
        assignee TEXT DEFAULT 'Eastwood Studio',
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Migration silencieuse
    try:
        obj_cols = [r[1] for r in c.execute("PRAGMA table_info(objectifs)").fetchall()]
        if "assignee" not in obj_cols:
            c.execute("ALTER TABLE objectifs ADD COLUMN assignee TEXT DEFAULT 'Eastwood Studio'")
    except Exception:
        pass

    # Pas de seed events — l'utilisateur les crée à la main
    conn.commit()


def get_events(conn, upcoming_only=False, type_filter=None):
    q = "SELECT * FROM events WHERE 1=1"
    p = []
    if upcoming_only:
        q += " AND date_debut >= ?"; p.append(date.today().isoformat())
    if type_filter:
        q += " AND type_event=?"; p.append(type_filter)
    return pd.read_sql(q + " ORDER BY date_debut ASC", conn, params=p)


def get_objectifs(conn, collection=None, statut=None):
    q = "SELECT * FROM objectifs WHERE 1=1"
    p = []
    if collection: q += " AND collection=?"; p.append(collection)
    if statut:     q += " AND statut=?";     p.append(statut)
    return pd.read_sql(q + " ORDER BY date_cible ASC", conn, params=p)


def generate_gcal_ics(events_df):
    """Génère un fichier .ics compatible Google Calendar / Apple Calendar."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Eastwood Studio//Gestion//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for _, ev in events_df.iterrows():
        try:
            d = datetime.strptime(ev["date_debut"], "%Y-%m-%d")
        except Exception:
            continue
        heure = ev.get("heure") or "10:00"
        try:
            h, m = heure.split(":")
        except Exception:
            h, m = "10", "00"
        dtstart = d.replace(hour=int(h), minute=int(m))
        dtend   = dtstart + timedelta(hours=1)
        uid = f"ew-{ev['id']}@eastwood-studio.fr"
        desc = str(ev.get("description","") or "").replace("\n","\\n")
        if ev.get("meet_link"):
            desc += f"\\nGoogle Meet : {ev['meet_link']}"

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{dtend.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{ev['titre']}",
            f"DESCRIPTION:{desc}",
            f"LOCATION:{ev.get('lieu','Paris') or 'Paris'}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CALENDRIER PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_calendrier(can_fn, DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_calendar_db(conn)

    st.markdown("### Calendrier & Objectifs")

    tab_cal, tab_obj, tab_add, tab_ics = st.tabs(["📅 Calendrier", "🎯 Plan Stratégie", "➕ Ajouter", "📥 Import ICS"])

    # ── CALENDRIER ─────────────────────────────────────────────────────────────
    with tab_cal:
        # ── Navigation semaine ──────────────────────────────────────────────────
        today = date.today()
        if "cal_week_offset" not in st.session_state:
            st.session_state["cal_week_offset"] = 0

        nav_c1, nav_c2, nav_c3 = st.columns([1, 4, 1])
        with nav_c1:
            if st.button("← Préc.", key="cal_prev"):
                st.session_state["cal_week_offset"] -= 1; st.rerun()
        with nav_c3:
            if st.button("Suiv. →", key="cal_next"):
                st.session_state["cal_week_offset"] += 1; st.rerun()

        week_offset = st.session_state["cal_week_offset"]
        lundi_cal = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        vendredi_cal = lundi_cal + timedelta(days=6)

        with nav_c2:
            st.markdown(f"""
<div style="text-align:center;font-family:'DM Mono',monospace;font-size:11px;color:#8a7968;padding:6px 0;">
  Semaine du {lundi_cal.strftime('%d %B')} au {vendredi_cal.strftime('%d %B %Y')}
</div>""", unsafe_allow_html=True)

        col_today_btn, col_edit_btn = st.columns([1, 3])
        with col_today_btn:
            if st.button("Aujourd'hui", key="cal_today"):
                st.session_state["cal_week_offset"] = 0; st.rerun()
        with col_edit_btn:
            # Toggle pour afficher le panneau de modification
            if st.button("✏️ Modifier / Supprimer un événement", key="cal_toggle_edit"):
                st.session_state["cal_show_edit"] = not st.session_state.get("cal_show_edit", False)

        # ── Charger les events de la semaine ──────────────────────────────────
        df_ev_cal = pd.read_sql("""
            SELECT * FROM events
            WHERE date_debut >= ? AND date_debut <= ?
            ORDER BY date_debut, heure
        """, conn, params=[lundi_cal.isoformat(), vendredi_cal.isoformat()])

        # ── Panneau de modification (affiché si toggle) ───────────────────────
        if st.session_state.get("cal_show_edit") and not df_ev_cal.empty:
            st.markdown('<div style="background:#f7f5f0;border:0.5px solid #e0dbd2;padding:12px 16px;margin-bottom:12px;">', unsafe_allow_html=True)
            # Filtres pour retrouver facilement un événement
            ef1, ef2 = st.columns(2)
            with ef1:
                _cat_filter = st.selectbox("Filtrer par type", ["Tous"] + TYPES_EVENT, key="cal_edit_cat")
            with ef2:
                _search_filter = st.text_input("Recherche par nom", placeholder="ex: Réunion hebdo S.18", key="cal_edit_search")
            df_edit_filtered = df_ev_cal.copy()
            if _cat_filter != "Tous":
                df_edit_filtered = df_edit_filtered[df_edit_filtered["type_event"]==_cat_filter]
            if _search_filter.strip():
                try:
                    df_edit_filtered = df_edit_filtered[
                        df_edit_filtered["titre"].fillna("").str.contains(_search_filter.strip(), case=False, na=False)
                    ]
                except Exception:
                    pass  # Si erreur regex, ignorer le filtre
            ev_labels_edit = [
                f"{str(ev.get('date_debut',''))[5:10]} {str(ev.get('heure','') or '')[:5]} — {str(ev.get('titre',''))[:35]}"
                for _, ev in df_edit_filtered.iterrows()
            ]
            sel_ev_label = st.selectbox("Événement à modifier", ["— Sélectionner —"] + ev_labels_edit,
                                        key="cal_ev_sel_edit")
            if sel_ev_label != "— Sélectionner —":
                sel_ev_idx = ev_labels_edit.index(sel_ev_label)
                sel_ev = df_edit_filtered.iloc[sel_ev_idx].to_dict()
                eid = int(sel_ev["id"])

                # Formulaire de modification
                with st.form(f"ev_edit_main_{eid}"):
                    ep1, ep2 = st.columns(2)
                    with ep1:
                        _et   = st.text_input("Titre *", value=str(sel_ev.get("titre","") or ""))
                        _etyp = st.selectbox("Type", TYPES_EVENT,
                            index=TYPES_EVENT.index(sel_ev.get("type_event","Autre"))
                            if sel_ev.get("type_event") in TYPES_EVENT else 0)
                        _el   = st.text_input("Lieu", value=str(sel_ev.get("lieu","") or ""))
                        _em   = st.text_input("Lien Meet", value=str(sel_ev.get("meet_link","") or ""))
                    with ep2:
                        _eh     = st.text_input("Heure début", value=str(sel_ev.get("heure","10:00") or "10:00"),
                                                placeholder="10:00")
                        _eh_fin = st.text_input("Heure fin", value=str(sel_ev.get("heure_fin","") or ""),
                                                placeholder="11:00")
                        _ed = st.text_area("Description", value=str(sel_ev.get("description","") or ""), height=80)

                    save_col, del_col = st.columns(2)
                    with save_col:
                        if st.form_submit_button("💾 Sauvegarder", type="primary"):
                            conn.execute("""UPDATE events
                                SET titre=?,heure=?,heure_fin=?,lieu=?,
                                    description=?,type_event=?,meet_link=?
                                WHERE id=?""",
                                (_et, _eh, _eh_fin, _el, _ed, _etyp, _em, eid))
                            conn.commit()
                            st.session_state["cal_show_edit"] = False
                            st.success("✓ Événement modifié."); st.rerun()
                    with del_col:
                        if st.form_submit_button("🗑 Supprimer définitivement"):
                            conn.execute("DELETE FROM events WHERE id=?", (eid,))
                            conn.commit()
                            st.session_state["cal_show_edit"] = False
                            st.success("✓ Supprimé."); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Migrer colonne heure_fin si absente ───────────────────────────────
        try:
            conn.execute("ALTER TABLE events ADD COLUMN heure_fin TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            pass

        # ── Grille HTML style Google Agenda ──────────────────────────────────
        jours_labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        HOUR_START = 8
        HOUR_END   = 21
        HOUR_H     = 60   # px par heure

        # Calculer top et height pour chaque event
        def _parse_h(s, default_h=10, default_m=0):
            try:
                parts = str(s or "").split(":")
                return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            except Exception:
                return default_h, default_m

        ev_by_day = {j: [] for j in range(7)}
        if not df_ev_cal.empty:
            for _, ev in df_ev_cal.iterrows():
                for j in range(7):
                    if str(ev["date_debut"]) == (lundi_cal + timedelta(days=j)).isoformat():
                        h_s, m_s = _parse_h(ev.get("heure","10:00"))
                        # Heure de fin
                        hf_raw = str(ev.get("heure_fin","") or "")
                        if hf_raw and ":" in hf_raw:
                            h_e, m_e = _parse_h(hf_raw)
                        else:
                            h_e, m_e = h_s + 1, m_s  # défaut 1h
                        top_px    = (h_s - HOUR_START) * HOUR_H + int(m_s/60*HOUR_H)
                        dur_h     = (h_e - h_s) + (m_e - m_s)/60
                        height_px = max(int(dur_h * HOUR_H) - 4, 20)
                        col_ev    = EVENT_COLORS.get(str(ev.get("type_event","Autre")), "#7b506f")
                        ev_by_day[j].append({
                            **{k: ev[k] for k in ev.index},
                            "top": top_px, "height": height_px, "col": col_ev
                        })

        # En-tête
        header_html = '<div style="display:grid;grid-template-columns:52px repeat(7,1fr);border-bottom:2px solid #e8e4de;background:#fff;">' + '<div style="border-right:1px solid #e8e4de;height:48px;"></div>'
        for j in range(7):
            jour_d   = lundi_cal + timedelta(days=j)
            is_today = (jour_d == today)
            bg_c = "#7b506f" if is_today else "transparent"
            fc   = "#fff"    if is_today else "#1a1a1a"
            fcs  = "#fff"    if is_today else "#8a7968"
            rnd  = "border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;margin:0 auto;" if is_today else ""
            header_html += (
                f'<div style="text-align:center;padding:6px 2px;border-right:1px solid #f0ece4;">' +
                f'<div style="font-family:DM Mono,monospace;font-size:9px;color:{fcs};text-transform:uppercase;">{jours_labels[j]}</div>' +
                f'<div style="font-size:20px;font-weight:500;color:{fc};background:{bg_c};{rnd}margin-top:2px;">{jour_d.day}</div>' +
                '</div>'
            )
        header_html += '</div>'

        # Corps grille
        total_h = (HOUR_END - HOUR_START) * HOUR_H
        grid_html = f'<div style="display:grid;grid-template-columns:52px repeat(7,1fr);height:{total_h}px;position:relative;">'

        # Colonne heures
        hours_col = '<div style="position:relative;border-right:1px solid #e8e4de;">'
        for h in range(HOUR_START, HOUR_END):
            top = (h - HOUR_START) * HOUR_H
            hours_col += f'<div style="position:absolute;top:{top}px;right:6px;font-family:DM Mono,monospace;font-size:9px;color:#aaa49a;transform:translateY(-50%);white-space:nowrap;">{h:02d}:00</div>'
        hours_col += '</div>'
        grid_html += hours_col

        # Colonnes jours
        for j in range(7):
            bg_d = "#faf9f7" if j >= 5 else "#fff"
            day_html = f'<div style="position:relative;background:{bg_d};border-right:1px solid #f0ece4;">'
            for h in range(HOUR_START, HOUR_END):
                top = (h - HOUR_START) * HOUR_H
                day_html += f'<div style="position:absolute;top:{top}px;left:0;right:0;border-top:1px solid #f0ece4;pointer-events:none;"></div>'
            for ev_p in ev_by_day[j]:
                c = ev_p["col"]
                t = str(ev_p.get("titre",""))[:24]
                lieu = str(ev_p.get("lieu","") or "")
                h_label = str(ev_p.get("heure","") or "")[:5]
                hf_label = str(ev_p.get("heure_fin","") or "")[:5]
                time_label = f"{h_label}–{hf_label}" if hf_label else h_label
                type_label = str(ev_p.get("type_event","") or "")
                # Couleur de fond selon type (superposition visuelle)
                bg_alpha = "33" if ev_p["height"] < 40 else "22"
                day_html += (
                    f'<div style="position:absolute;top:{ev_p["top"]+1}px;left:2px;right:2px;' +
                    f'height:{ev_p["height"]}px;background:{c}{bg_alpha};' +
                    f'border-left:3px solid {c};padding:2px 5px;overflow:hidden;' +
                    f'box-shadow:0 1px 3px rgba(0,0,0,0.08);z-index:2;' +
                    f'border-radius:0 3px 3px 0;">' +
                    f'<div style="font-family:DM Mono,monospace;font-size:8px;color:{c};font-weight:500;">{time_label}</div>' +
                    f'<div style="font-size:10px;font-weight:500;color:#1a1a1a;line-height:1.3;">{t}</div>' +
                    (f'<div style="font-size:9px;color:#8a7968;">{lieu}</div>' if lieu and ev_p["height"] > 40 else '') +
                    '</div>'
                )
            day_html += '</div>'
            grid_html += day_html
        grid_html += '</div>'

        st.markdown(
            f'<div style="border:1px solid #e8e4de;overflow:hidden;border-radius:4px;">' +
            header_html +
            f'<div style="overflow-y:auto;max-height:640px;">{grid_html}</div>' +
            '</div>',
            unsafe_allow_html=True
        )


    with tab_obj:
        c1,c2 = st.columns(2)
        with c1:
            f_coll_obj = st.selectbox("Collection", ["Toutes","Chapter I — Hunting & Fishing",
                "Chapter II — Le Souvenir","Général"], key="obj_coll")
        with c2:
            f_stat_obj = st.selectbox("Statut", ["Tous","En cours","À démarrer","Terminé","Annulé"],
                                      key="obj_stat")

        df_obj = get_objectifs(
            conn,
            collection=None if f_coll_obj == "Toutes" else f_coll_obj,
            statut=None if f_stat_obj == "Tous" else f_stat_obj,
        )

        if df_obj.empty:
            st.info("Aucun objectif. Ajoutez-en depuis l'onglet ➕ Ajouter.")
        else:
            stat_colors = {
                "En cours":   "#185FA5",
                "À démarrer": "#888078",
                "Terminé":    "#2d6a4f",
                "Annulé":     "#c1440e",
            }
            prio_colors = {"Haute":"#c1440e","Normal":"#888","Basse":"#aaa"}

            for _, obj in df_obj.iterrows():
                sc = stat_colors.get(obj.get("statut",""), "#888")
                pc = prio_colors.get(obj.get("priorite",""), "#888")
                try:
                    d_cible = datetime.strptime(str(obj["date_cible"])[:10], "%Y-%m-%d").date()
                    delta = (d_cible - date.today()).days
                    date_str = d_cible.strftime("%d %B %Y")
                    delta_str = f"J-{delta}" if delta >= 0 else f"Dépassé de {-delta}j"
                except Exception:
                    date_str = obj.get("date_cible","")
                    delta_str = ""

                col_obj, col_stat = st.columns([4, 1])
                with col_obj:
                    st.markdown(f"""
<div style="padding:10px 14px;border:0.5px solid #e0dbd2;border-left:3px solid {sc};
     margin:4px 0;background:#f7f5f0;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div style="flex:1;">
      <div style="font-family:'DM Mono',monospace;font-size:8px;color:#aaa49a;
                  text-transform:uppercase;letter-spacing:.1em;">{obj.get('collection','')} · {obj.get('type_obj','')}</div>
      <div style="font-size:13px;font-weight:500;color:#1a1a1a;margin:2px 0;">{obj['titre']}</div>
      {f'<div style="font-size:11px;color:#888078;">{obj["description"]}</div>' if obj.get('description') else ''}
    </div>
    <div style="text-align:right;white-space:nowrap;margin-left:10px;">
      <div style="font-family:'DM Mono',monospace;font-size:10px;color:{sc};">{obj.get('statut','')}</div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:#aaa49a;">{date_str}</div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:{pc};">{delta_str}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

                with col_stat:
                    # Changement statut
                    new_stat = st.selectbox("", ["En cours","À démarrer","Terminé","Annulé"],
                                            index=["En cours","À démarrer","Terminé","Annulé"].index(
                                                obj.get("statut","En cours"))
                                            if obj.get("statut") in ["En cours","À démarrer","Terminé","Annulé"] else 0,
                                            key=f"obj_stat_{obj['id']}", label_visibility="collapsed")
                    if st.button("✓", key=f"obj_upd_{obj['id']}"):
                        conn.execute("UPDATE objectifs SET statut=? WHERE id=?", (new_stat, obj["id"]))
                        conn.commit(); st.rerun()

                    # Jules : modifier et supprimer
                    if can_fn("finance_write"):
                        ob1, ob2 = st.columns(2)
                        with ob1:
                            if st.button("⚙", key=f"obj_edit_btn_{obj['id']}", help="Modifier"):
                                st.session_state[f"edit_obj_{obj['id']}"] = not st.session_state.get(f"edit_obj_{obj['id']}", False)
                        with ob2:
                            if st.button("🗑", key=f"obj_del_{obj['id']}", help="Supprimer"):
                                conn.execute("DELETE FROM objectifs WHERE id=?", (obj["id"],))
                                conn.commit(); st.rerun()

                # Formulaire édition objectif (Jules only)
                if can_fn("finance_write") and st.session_state.get(f"edit_obj_{obj['id']}"):
                    with st.form(f"edit_obj_form_{obj['id']}"):
                        eo_titre = st.text_input("Titre", value=obj.get("titre",""))
                        eo_c1, eo_c2 = st.columns(2)
                        with eo_c1:
                            eo_coll = st.selectbox("Collection", ["Chapter I — Hunting & Fishing",
                                "Chapter II — Le Souvenir","Général"],
                                index=0)
                            eo_type = st.selectbox("Type", ["Production","Communication","Commercial",
                                                             "Finance","Logistique","RH","Autre"],
                                index=["Production","Communication","Commercial","Finance","Logistique","RH","Autre"].index(
                                    obj.get("type_obj","Production")) if obj.get("type_obj") in ["Production","Communication","Commercial","Finance","Logistique","RH","Autre"] else 0)
                        with eo_c2:
                            eo_prio = st.selectbox("Priorité", ["Haute","Normal","Basse"],
                                index=["Haute","Normal","Basse"].index(obj.get("priorite","Normal"))
                                if obj.get("priorite") in ["Haute","Normal","Basse"] else 1)
                            try:
                                _d_init = datetime.strptime(str(obj.get("date_cible",""))[:10], "%Y-%m-%d").date()
                            except Exception:
                                _d_init = date.today()
                            eo_date = st.date_input("Date cible", value=_d_init)
                        eo_desc = st.text_area("Description", value=obj.get("description","") or "", height=60)
                        if st.form_submit_button("💾 Sauvegarder"):
                            conn.execute("""UPDATE objectifs SET
                                titre=?,collection=?,type_obj=?,priorite=?,date_cible=?,description=?
                                WHERE id=?""",
                                (eo_titre,eo_coll,eo_type,eo_prio,eo_date.isoformat(),eo_desc,obj["id"]))
                            st.session_state.pop(f"edit_obj_{obj['id']}", None)
                            conn.commit(); st.rerun()

    # ── AJOUTER ────────────────────────────────────────────────────────────────
    with tab_add:
        st.markdown('<div class="section-title">Réunion récurrente rapide</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="info-box">
Crée automatiquement des réunions hebdomadaires nommées S.01, S.02... jusqu'à la date choisie.
Tu peux ensuite modifier chaque réunion individuellement.
</div>""", unsafe_allow_html=True)
        with st.form("add_reunion_recurrente"):
            rr1, rr2, rr3 = st.columns(3)
            with rr1:
                rr_titre   = st.text_input("Nom base", value="Réunion hebdo",
                                           help="Le nom sera complété par S.XX (semaine)")
                rr_heure   = st.text_input("Heure", value="18:00")
            with rr2:
                rr_jour    = st.selectbox("Jour", ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"],
                                          index=2)  # Mercredi par défaut
                rr_heure_fin = st.text_input("Heure fin", value="19:00")
            with rr3:
                rr_date_fin = st.date_input("Créer jusqu'au", value=date.today() + timedelta(weeks=8))
                rr_lieu     = st.text_input("Lieu", placeholder="En ligne / Paris")
            rr_desc = st.text_input("Description", placeholder="Réunion hebdomadaire Eastwood Studio")
            if st.form_submit_button("✓ Créer les réunions récurrentes"):
                jour_idx = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"].index(rr_jour)
                d = date.today()
                while d.weekday() != jour_idx:
                    d += timedelta(days=1)
                created_rr = 0
                while d <= rr_date_fin:
                    sem_num = d.isocalendar()[1]
                    titre_rr = f"{rr_titre} — S.{sem_num:02d}"
                    conn.execute("""INSERT INTO events
                        (titre,type_event,date_debut,heure,heure_fin,lieu,description,
                         recurrent,freq_recurrence,created_by)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (titre_rr, "Réunion", d.isoformat(), rr_heure, rr_heure_fin,
                         rr_lieu, rr_desc or "Réunion hebdomadaire Eastwood Studio",
                         1, "hebdomadaire",
                         st.session_state.get("user_display","Jules")))
                    d += timedelta(weeks=1)
                    created_rr += 1
                conn.commit()
                st.success(f"✓ {created_rr} réunions créées.")
                st.rerun()

        st.markdown('<div class="section-title">Nouvel événement</div>', unsafe_allow_html=True)
        with st.form("add_event"):
            e1,e2,e3 = st.columns(3)
            with e1:
                ev_titre  = st.text_input("Titre *")
                ev_type   = st.selectbox("Type", TYPES_EVENT)
            with e2:
                ev_date    = st.date_input("Date début *", value=date.today())
                ev_heure   = st.text_input("Heure début *", value="10:00", placeholder="10:00")
                ev_heure_fin = st.text_input("Heure fin * (ex: 11:00 ou 3j)", placeholder="11:00 ou +3j")
                ev_date_fin = st.date_input("Date fin (si multi-jours, optionnel)", value=None)
            with e3:
                ev_lieu   = st.text_input("Lieu", placeholder="Paris / En ligne")
                ev_meet   = st.text_input("Lien Meet/Zoom", placeholder="https://meet.google.com/...")
            ev_desc   = st.text_area("Description", height=60)

            # Récurrence enrichie
            ev_recur  = st.checkbox("Événement récurrent")
            if ev_recur:
                rf1,rf2 = st.columns(2)
                with rf1: ev_freq = st.selectbox("Fréquence", ["hebdomadaire","bimensuel","mensuel","annuel"])
                with rf2: ev_nb_occ = st.number_input("Nb occurrences à générer", min_value=1, max_value=52, value=8)
            else:
                ev_freq = None; ev_nb_occ = 1

            # Invitation automatique
            ev_invite = st.checkbox(
                f"Générer lien Google Calendar (avec {EMAIL_INVITATION})",
                value=(ev_type == "Réunion"),
                help="Génère un lien qui ouvre Google Calendar avec l'événement pré-rempli et {EMAIL_INVITATION} en invité. Clique le lien après création."
            )

            if st.form_submit_button("✓ Créer l'événement"):
                if not ev_titre:
                    st.error("Titre obligatoire.")
                else:
                    if ev_recur and ev_nb_occ > 1:
                        # Générer les occurrences
                        delta_map = {"hebdomadaire":7,"bimensuel":14,"mensuel":30,"annuel":365}
                        delta_days = delta_map.get(ev_freq, 7)
                        for i in range(ev_nb_occ):
                            d_occ = ev_date + timedelta(days=i*delta_days)
                            conn.execute("""INSERT INTO events
                                (titre,type_event,date_debut,date_fin,heure,lieu,description,
                                 meet_link,recurrent,freq_recurrence,created_by)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                                (f"{ev_titre}{' — '+d_occ.strftime('%d %b') if ev_nb_occ>1 else ''}",
                                 ev_type, d_occ.isoformat(),
                                 ev_date_fin.isoformat() if ev_date_fin else "",
                                 ev_heure, ev_lieu, ev_desc,
                                 ev_meet, 1, ev_freq,
                                 st.session_state.get("user_display","")))
                    else:
                        conn.execute("""INSERT INTO events
                            (titre,type_event,date_debut,date_fin,heure,lieu,description,
                             meet_link,recurrent,freq_recurrence,created_by)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                            (ev_titre, ev_type, ev_date.isoformat(),
                             ev_date_fin.isoformat() if ev_date_fin else "",
                             ev_heure, ev_lieu, ev_desc,
                             ev_meet, int(ev_recur), ev_freq or "",
                             st.session_state.get("user_display","")))
                    conn.commit()

                    msg = "✓ Événement créé."
                    if ev_recur and ev_nb_occ > 1:
                        msg += f" {ev_nb_occ} occurrences générées."
                    st.success(msg)

                    # Lien Google Calendar
                    if ev_invite:
                        try:
                            from datetime import datetime as _dti2
                            _hh, _mm = (ev_heure.split(":") + ["00"])[:2]
                            _dt_start = _dti2(ev_date.year, ev_date.month, ev_date.day, int(_hh), int(_mm))
                            _hf = ev_heure_fin if ev_heure_fin and ":" in ev_heure_fin else ""
                            if _hf:
                                _hfh, _hfm = (_hf.split(":") + ["00"])[:2]
                                _dt_end = _dti2(ev_date.year, ev_date.month, ev_date.day, int(_hfh), int(_hfm))
                            else:
                                from datetime import timedelta as _td
                                _dt_end = _dt_start + _td(hours=1)
                            _fmt = "%Y%m%dT%H%M%S"
                            import urllib.parse as _ulib
                            _gcal_params = {
                                "action": "TEMPLATE",
                                "text": ev_titre,
                                "dates": f"{_dt_start.strftime(_fmt)}/{_dt_end.strftime(_fmt)}",
                                "details": ev_desc or "",
                                "location": ev_lieu or "",
                                "add": EMAIL_INVITATION,
                            }
                            _gcal = "https://calendar.google.com/calendar/render?" + _ulib.urlencode(_gcal_params)
                            st.markdown(f'<a href="{_gcal}" target="_blank" style="font-family:DM Mono,monospace;font-size:11px;color:#395f30;font-weight:500;">↗ Ouvrir dans Google Calendar (ajoute {EMAIL_INVITATION} en invité)</a>', unsafe_allow_html=True)
                            st.info("Clique le lien ci-dessus pour créer l'événement dans Google Calendar avec l'invitation automatique.")
                        except Exception as _ge:
                            st.warning(f"Erreur lien Google Calendar : {_ge}")
                    st.rerun()

        st.markdown('<div class="section-title">Nouvel objectif stratégique</div>', unsafe_allow_html=True)
        with st.form("add_objectif"):
            o1,o2,o3 = st.columns(3)
            with o1:
                obj_titre  = st.text_input("Titre *")
                obj_coll   = st.selectbox("Collection", ["SS26 — Été 2026","FW26 — Hiver 2026",
                                                          "SS25 — Été 2025","Général"])
                obj_assign = st.selectbox("Attribué à", ASSIGNEES_OBJ)
            with o2:
                obj_type   = st.selectbox("Type", ["Production","Communication","Commercial",
                                                    "Finance","Logistique","RH","Autre"])
                obj_date   = st.date_input("Date cible", value=date.today())
            with o3:
                obj_prio   = st.selectbox("Priorité", ["Haute","Normal","Basse"])
                obj_stat   = st.selectbox("Statut", ["À démarrer","En cours","Terminé"])
            obj_desc = st.text_area("Description", height=60)

            if st.form_submit_button("✓ Créer l'objectif"):
                if not obj_titre:
                    st.error("Titre obligatoire.")
                else:
                    conn.execute("""INSERT INTO objectifs
                        (titre,collection,type_obj,date_cible,description,statut,priorite,assignee)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (obj_titre,obj_coll,obj_type,obj_date.isoformat(),
                         obj_desc,obj_stat,obj_prio,obj_assign))
                    conn.commit()
                    st.success("✓ Objectif créé."); st.rerun()


    # ── IMPORT ICS ────────────────────────────────────────────────────────────
    with tab_ics:
        st.markdown('<div class="section-title">Importer des événements (.ics)</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="info-box">
Compatible Google Calendar, Apple Calendar, Outlook.<br>
Chaque événement VEVENT du fichier sera ajouté au calendrier Eastwood.
</div>""", unsafe_allow_html=True)
        ics_file = st.file_uploader("Choisir un fichier .ics", type=["ics","ICS"], key="ics_upload_main")
        if ics_file is not None:
            try:
                raw = ics_file.read()
                # Essayer plusieurs encodages
                for enc in ["utf-8","latin-1","cp1252"]:
                    try:
                        ics_text = raw.decode(enc)
                        break
                    except Exception:
                        ics_text = None
                if not ics_text:
                    st.error("Impossible de lire le fichier.")
                else:
                    # Normaliser les lignes (unfold)
                    lines = []
                    for line in ics_text.replace("\r\n","\n").replace("\r","\n").split("\n"):
                        if line.startswith((" ","\t")) and lines:
                            lines[-1] += line.strip()
                        else:
                            lines.append(line)

                    events_parsed = []
                    current = {}
                    in_event = False
                    for line in lines:
                        line = line.strip()
                        if line == "BEGIN:VEVENT":
                            in_event = True; current = {}
                        elif line == "END:VEVENT":
                            in_event = False
                            if current.get("SUMMARY") and current.get("DATE"):
                                events_parsed.append(current.copy())
                        elif in_event:
                            key, _, val = line.partition(":")
                            key_base = key.split(";")[0].upper()
                            if key_base in ("DTSTART","DTSTART"):
                                # Extraire date et heure
                                try:
                                    v = val.strip()
                                    if "T" in v:
                                        d_part = v[:8]; t_part = v[9:13]
                                        from datetime import datetime as _dtz
                                        dt = _dtz.strptime(d_part, "%Y%m%d")
                                        heure = f"{t_part[:2]}:{t_part[2:]}"
                                        current["DATE"] = dt.strftime("%Y-%m-%d")
                                        current["HEURE"] = heure
                                    else:
                                        from datetime import datetime as _dtz2
                                        dt = _dtz2.strptime(val.strip()[:8], "%Y%m%d")
                                        current["DATE"] = dt.strftime("%Y-%m-%d")
                                        current["HEURE"] = "10:00"
                                except Exception:
                                    pass
                            elif key_base == "DTEND":
                                try:
                                    v = val.strip()
                                    if "T" in v:
                                        t_part = v[9:13]
                                        current["HEURE_FIN"] = f"{t_part[:2]}:{t_part[2:]}"
                                except Exception:
                                    pass
                            elif key_base == "SUMMARY":
                                current["SUMMARY"] = val.strip()
                            elif key_base == "DESCRIPTION":
                                current["DESCRIPTION"] = val.replace("\\n","\n").strip()
                            elif key_base == "LOCATION":
                                current["LOCATION"] = val.strip()

                    if events_parsed:
                        st.success(f"**{len(events_parsed)} événement(s) trouvé(s)**")
                        # Aperçu
                        for ep in events_parsed[:5]:
                            st.markdown(f"· {ep.get('DATE','')} {ep.get('HEURE','')} — **{ep.get('SUMMARY','')}**")
                        if len(events_parsed) > 5:
                            st.caption(f"... et {len(events_parsed)-5} autres")
                        if st.button(f"✓ Importer {len(events_parsed)} événement(s)", type="primary", key="btn_import_ics"):
                            imported = 0
                            for ep in events_parsed:
                                try:
                                    conn.execute("""INSERT INTO events
                                        (titre,type_event,date_debut,heure,heure_fin,lieu,description,created_by)
                                        VALUES (?,?,?,?,?,?,?,?)""",
                                        (ep.get("SUMMARY","")[:100], "Autre",
                                         ep.get("DATE",""), ep.get("HEURE","10:00"),
                                         ep.get("HEURE_FIN",""),
                                         ep.get("LOCATION",""),
                                         ep.get("DESCRIPTION",""), "import_ics"))
                                    imported += 1
                                except Exception:
                                    pass
                            conn.commit()
                            st.success(f"✓ {imported} événement(s) importé(s).")
                            st.rerun()
                    else:
                        st.warning("Aucun événement VEVENT trouvé dans ce fichier. Vérifiez le format .ics.")
            except Exception as e_ics:
                st.error(f"Erreur lecture : {e_ics}")

        st.markdown("---")
        # Export ICS (export PDF-like = export des events de la semaine en .ics)
        st.markdown('<div class="section-title">Exporter les événements</div>', unsafe_allow_html=True)
        exp_c1, exp_c2 = st.columns(2)
        with exp_c1:
            exp_from = st.date_input("Du", value=date.today(), key="exp_from")
        with exp_c2:
            exp_to   = st.date_input("Au", value=date.today() + timedelta(days=30), key="exp_to")
        if st.button("⬇ Exporter en .ics (Google Calendar / Apple Calendar)", key="btn_export_ics"):
            df_exp_ev = pd.read_sql("""
                SELECT * FROM events WHERE date_debut >= ? AND date_debut <= ?
                ORDER BY date_debut, heure
            """, conn, params=[exp_from.isoformat(), exp_to.isoformat()])
            if df_exp_ev.empty:
                st.warning("Aucun événement dans cette période.")
            else:
                ics_out = generate_gcal_ics(df_exp_ev)
                st.download_button(
                    "⬇ Télécharger le fichier .ics",
                    data=ics_out.encode("utf-8"),
                    file_name=f"eastwood_events_{exp_from}_{exp_to}.ics",
                    mime="text/calendar",
                    key="dl_ics_export"
                )
                st.info(f"✓ {len(df_exp_ev)} événement(s) exportés. Importez le fichier dans Google Calendar, Apple Calendar ou Outlook.")


    conn.close()
