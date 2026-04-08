# calendar_module.py — v2.0 — 1775665297
# ══════════════════════════════════════════════════════════════════════════════
# MODULE CALENDRIER & OBJECTIFS
# ══════════════════════════════════════════════════════════════════════════════

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
    {"date": date(2026, 6, 15), "label": "Drop Chapter N°I — Waterfowl","type": "Drop collection",
     "detail": "Drop Chapter N°I · Hunting & Fishing · livraison juin 2026"},
    {"date": date(2026, 7, 1),  "label": "Drop Chapter N°II — Souvenir","type": "Drop collection",
     "detail": "Drop Chapter N°II · Le Souvenir · livraison juillet 2026"},
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

    # Seed events si vide
    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] == 0:
        # Insérer les fashion weeks et drops
        for fw in FASHION_WEEKS:
            c.execute("""INSERT INTO events (titre,type_event,date_debut,description,created_by)
                VALUES (?,?,?,?,?)""",
                (fw["label"], fw["type"], fw["date"].isoformat(), fw["detail"], "system"))

        # Réunions hebdo — générer les 12 prochaines
        next_wed = date.today()
        while next_wed.weekday() != 2:
            next_wed += timedelta(days=1)
        for i in range(12):
            d = next_wed + timedelta(weeks=i)
            c.execute("""INSERT INTO events
                (titre,type_event,date_debut,heure,description,meet_link,recurrent,freq_recurrence,created_by)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (f"Réunion hebdo — {d.strftime('%d %b %Y')}",
                 "Réunion", d.isoformat(), "18:00",
                 "Réunion hebdomadaire des fondateurs · Jules, Corentin, Alexis",
                 "https://meet.google.com/new", 1, "hebdomadaire", "system"))

        # Objectifs
        c.executemany("""INSERT INTO objectifs (titre,collection,type_obj,date_cible,description,statut,priorite)
            VALUES (?,?,?,?,?,?,?)""", [
            ("Finaliser 3 items SS26","SS26 — Été 2026","Production","2025-06-01",
             "Veste légère, Pantalon, Accessoire","En cours","Haute"),
            ("Préparer shooting SS26","SS26 — Été 2026","Communication","2025-05-15",
             "Booking studio + modèles + stylisme","En cours","Haute"),
            ("Développer 4 items FW26","FW26 — Hiver 2026","Production","2025-08-01",
             "Collection hiver 4 pièces","À démarrer","Normal"),
            ("Line sheet PFW SS26","SS26 — Été 2026","Commercial","2025-06-10",
             "Préparer line sheet showroom","À démarrer","Haute"),
        ])

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

    tab_cal, tab_obj, tab_add, tab_todo_cal = st.tabs(["📅 Calendrier", "🎯 Plan Stratégie", "➕ Ajouter", "✅ Mes TODO"])

    # ── CALENDRIER ─────────────────────────────────────────────────────────────
    with tab_cal:
        # ── Navigation semaine ──────────────────────────────────────────────────
        today = date.today()
        if "cal_week_offset" not in st.session_state:
            st.session_state["cal_week_offset"] = 0

        nav_c1, nav_c2, nav_c3 = st.columns([1, 4, 1])
        with nav_c1:
            if st.button("← Préc.", key="cal_prev"):
                st.session_state["cal_week_offset"] -= 1
                st.rerun()
        with nav_c3:
            if st.button("Suiv. →", key="cal_next"):
                st.session_state["cal_week_offset"] += 1
                st.rerun()

        week_offset = st.session_state["cal_week_offset"]
        lundi_cal = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        vendredi_cal = lundi_cal + timedelta(days=6)

        with nav_c2:
            st.markdown(f"""
<div style="text-align:center;font-family:'DM Mono',monospace;font-size:11px;color:#8a7968;padding:6px 0;">
  Semaine du {lundi_cal.strftime('%d %B')} au {vendredi_cal.strftime('%d %B %Y')}
</div>""", unsafe_allow_html=True)

        if st.button("Aujourd'hui", key="cal_today"):
            st.session_state["cal_week_offset"] = 0
            st.rerun()

        # ── Grille 7 jours × tranches horaires ──────────────────────────────────
        jours_labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        heures = [f"{h:02d}:00" for h in range(8, 21)]  # 8h → 20h

        # Charger les events de la semaine
        df_ev_cal = pd.read_sql("""
            SELECT * FROM events
            WHERE date_debut >= ? AND date_debut <= ?
            ORDER BY date_debut, heure
        """, conn, params=[lundi_cal.isoformat(), vendredi_cal.isoformat()])

        # En-tête jours
        header_cols = st.columns([0.6] + [1]*7)
        with header_cols[0]:
            st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)
        for j in range(7):
            jour_d = lundi_cal + timedelta(days=j)
            is_today = jour_d == today
            bg = "#7b506f" if is_today else "transparent"
            tc = "#fff" if is_today else "#1a1a1a"
            with header_cols[j+1]:
                st.markdown(f"""
<div style="text-align:center;background:{bg};padding:4px 2px;margin-bottom:2px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{tc if is_today else '#8a7968'};">{jours_labels[j]}</div>
  <div style="font-size:14px;font-weight:500;color:{tc};">{jour_d.day}</div>
</div>""", unsafe_allow_html=True)

        # Lignes horaires
        for heure_str in heures:
            row_cols = st.columns([0.6] + [1]*7)
            with row_cols[0]:
                st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#aaa49a;padding:3px 4px 3px 0;text-align:right;border-right:1px solid #ede3d3;">{heure_str}</div>', unsafe_allow_html=True)

            for j in range(7):
                jour_d = lundi_cal + timedelta(days=j)
                # Events sur ce jour à cette heure
                ev_here = []
                if not df_ev_cal.empty:
                    for _, ev in df_ev_cal.iterrows():
                        if str(ev["date_debut"]) == jour_d.isoformat():
                            ev_h = str(ev.get("heure","") or "")[:2]
                            if ev_h == heure_str[:2]:
                                ev_here.append(ev)

                with row_cols[j+1]:
                    cell_bg = "#f9f8f6" if (j >= 5) else "#fff"  # weekend grisé
                    border_t = "1px solid #f0ece4"
                    if ev_here:
                        for ev in ev_here:
                            col_ev = EVENT_COLORS.get(ev.get("type_event","Autre"), "#888")
                            st.markdown(f"""
<div style="background:{col_ev}15;border-left:2px solid {col_ev};
     padding:2px 4px;margin:1px 0;font-size:9px;line-height:1.3;
     border-bottom:{border_t};">
  <div style="font-weight:500;color:#1a1a1a;">{str(ev.get('titre',''))[:18]}</div>
</div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="height:22px;background:{cell_bg};border-bottom:{border_t};"></div>', unsafe_allow_html=True)


    with tab_obj:
        c1,c2 = st.columns(2)
        with c1:
            coll_opts = ["Toutes","SS26 — Été 2026","FW26 — Hiver 2026",
                         "SS25 — Été 2025","FW25 — Hiver 2025","Général"]
            f_coll_obj = st.selectbox("Collection", coll_opts, key="obj_coll")
        with c2:
            f_stat_obj = st.selectbox("Statut", ["Tous","En cours","À démarrer","Terminé","Annulé"],
                                      key="obj_stat")

        df_obj = get_objectifs(
            conn,
            collection=None if f_coll_obj == "Toutes" else f_coll_obj,
            statut=None if f_stat_obj == "Tous" else f_stat_obj,
        )

        if df_obj.empty:
            st.info("Aucun objectif.")
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
                    d_cible = datetime.strptime(obj["date_cible"], "%Y-%m-%d").date()
                    delta = (d_cible - date.today()).days
                    date_str = d_cible.strftime("%d %B %Y")
                    delta_str = f"J-{delta}" if delta >= 0 else f"Dépassé de {-delta}j"
                except Exception:
                    date_str = obj.get("date_cible","")
                    delta_str = ""

                col_obj, col_stat = st.columns([4, 1])
                with col_obj:
                    st.markdown(f"""
<div style="padding:12px 16px;border:1px solid #e0dbd2;border-left:3px solid {sc};
     border-radius:2px;margin:6px 0;background:#f7f5f0;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:#aaa49a;
                  text-transform:uppercase;letter-spacing:.1em;">{obj.get('collection','')} · {obj.get('type_obj','')}</div>
      <div style="font-size:14px;font-weight:500;color:#1a1a1a;margin:3px 0;">{obj['titre']}</div>
      {f'<div style="font-size:12px;color:#888078;">{obj["description"]}</div>' if obj.get('description') else ''}
    </div>
    <div style="text-align:right;white-space:nowrap;margin-left:12px;">
      <div style="font-family:'DM Mono',monospace;font-size:11px;color:{sc};">{obj.get('statut','')}</div>
      <div style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">{date_str}</div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:{pc};">{delta_str}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

                with col_stat:
                    if can_fn("settings"):
                        new_stat = st.selectbox("", ["En cours","À démarrer","Terminé","Annulé"],
                                                index=["En cours","À démarrer","Terminé","Annulé"].index(obj.get("statut","En cours")) if obj.get("statut") in ["En cours","À démarrer","Terminé","Annulé"] else 0,
                                                key=f"obj_stat_{obj['id']}", label_visibility="collapsed")
                        if st.button("✓", key=f"obj_upd_{obj['id']}"):
                            conn.execute("UPDATE objectifs SET statut=? WHERE id=?", (new_stat, obj["id"]))
                            conn.commit(); st.rerun()

    # ── AJOUTER ────────────────────────────────────────────────────────────────
    with tab_add:
        st.markdown('<div class="section-title">Nouvel événement</div>', unsafe_allow_html=True)
        with st.form("add_event"):
            e1,e2,e3 = st.columns(3)
            with e1:
                ev_titre  = st.text_input("Titre *")
                ev_type   = st.selectbox("Type", TYPES_EVENT)
            with e2:
                ev_date   = st.date_input("Date *", value=date.today())
                ev_heure  = st.text_input("Heure", value="10:00", placeholder="18:00")
                ev_date_fin = st.date_input("Date de fin (optionnel)", value=None)
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
                f"Envoyer invitation à {EMAIL_INVITATION}",
                value=(ev_type == "Réunion"),
                help="Génère un lien mailto pour inviter le compte Eastwood Studio"
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

                    # Lien invitation email
                    if ev_invite and EMAIL_INVITATION:
                        subject = f"Eastwood Studio — {ev_titre} · {ev_date.strftime('%d %b %Y')}"
                        body = f"{ev_titre}\nDate : {ev_date.strftime('%d %B %Y')} à {ev_heure}\n"
                        if ev_lieu: body += f"Lieu : {ev_lieu}\n"
                        if ev_meet: body += f"Meet : {ev_meet}\n"
                        if ev_desc: body += f"\n{ev_desc}"
                        mailto = f"mailto:{EMAIL_INVITATION}?subject={subject}&body={body}".replace(" ","%20").replace("\n","%0A")
                        inv_html = '<a href="' + mailto + '" target="_blank" style="font-family:DM Mono,monospace;font-size:10px;color:#7b506f;">↗ Envoyer invitation email</a>'
                        st.markdown(inv_html, unsafe_allow_html=True)
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

    # ── MES TODO DANS LE CALENDRIER ────────────────────────────────────────────
    with tab_todo_cal:
        user_prenom = st.session_state.get("user_display","").split()[0] if st.session_state.get("user_display") else "Jules"
        st.markdown(f'<div class="section-title">TODO de la semaine — {user_prenom}</div>', unsafe_allow_html=True)

        # Charger les todos depuis la table todos
        try:
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            semaine_id = monday.strftime("%Y-W%V")

            df_todos = pd.read_sql("""
                SELECT * FROM todos
                WHERE semaine=? AND (assignee=? OR assignee='Tous')
                ORDER BY fait ASC, priorite ASC
            """, conn, params=[semaine_id, user_prenom])

            if df_todos.empty:
                st.info(f"Aucune tâche cette semaine pour {user_prenom}.")
            else:
                done_count = len(df_todos[df_todos["fait"]==1])
                total = len(df_todos)
                pct = int(done_count/total*100) if total > 0 else 0
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
  <div style="flex:1;height:4px;background:#ede3d3;">
    <div style="width:{pct}%;height:4px;background:#395f30;"></div>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:#8a7968;">{done_count}/{total} · {pct}%</div>
</div>""", unsafe_allow_html=True)

                prio_colors = {"Urgent":"#c1440e","Cette semaine":"#7b506f","Quand possible":"#8a7968"}
                for _, todo in df_todos.iterrows():
                    pc = prio_colors.get(todo.get("priorite","Cette semaine"), "#8a7968")
                    done_style = "text-decoration:line-through;opacity:.5;" if todo.get("fait") else ""
                    tc1, tc2 = st.columns([6, 1])
                    with tc1:
                        st.markdown(f"""
<div style="border-left:2px solid {'#ccc' if todo.get('fait') else pc};
     padding:6px 12px;margin:4px 0;">
  <div style="font-size:12px;font-weight:500;{done_style}">{todo['titre']}</div>
  {f'<div style="font-size:11px;color:#8a7968;">{todo["description"]}</div>' if todo.get("description") else ''}
  <div style="font-family:\'DM Mono\',monospace;font-size:9px;color:{pc};">{todo.get("priorite","")}</div>
</div>""", unsafe_allow_html=True)
                    with tc2:
                        if not todo.get("fait"):
                            if st.button("✓", key=f"cal_done_{todo['id']}"):
                                conn.execute("UPDATE todos SET fait=1, done_at=? WHERE id=?",
                                             (str(date.today()), todo["id"]))
                                conn.commit(); st.rerun()

            # Lien vers page TODO complète
            st.markdown(f"""
<div style="margin-top:12px;">
  <a href="#" onclick="return false;" style="font-family:'DM Mono',monospace;font-size:10px;
     color:#7b506f;text-decoration:none;text-transform:uppercase;letter-spacing:.1em;">
    → Voir tous les TODO & Objectifs
  </a>
</div>""", unsafe_allow_html=True)

        except Exception as e:
            st.info("Les TODO seront disponibles une fois la page TODO initialisée.")

    conn.close()
