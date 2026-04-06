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

# Données fixes — saisons fashion week Paris
FASHION_WEEKS = [
    {"date": date(2025, 6, 20), "label": "PFW SS26 — Ouverture",      "type": "Fashion Week",
     "detail": "Paris Fashion Week Printemps-Été 2026 · Drop 1 (3 items)"},
    {"date": date(2025, 7, 5),  "label": "PFW SS26 — Drop 2 en ligne","type": "Drop collection",
     "detail": "Mise en ligne collection légère complète SS26"},
    {"date": date(2025, 9, 22), "label": "PFW FW26 — Début semaine",  "type": "Fashion Week",
     "detail": "Paris Fashion Week Automne-Hiver 2026 · préparation 4 items hiver"},
    {"date": date(2025, 10, 6), "label": "PFW FW26 — Drop pré-comm.", "type": "Drop collection",
     "detail": "Ouverture pré-commandes collection hiver · 4 items"},
    {"date": date(2026, 2, 25), "label": "PFW SS27 — Préparation",    "type": "Fashion Week",
     "detail": "Début préparation saison suivante"},
]


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
        created_at TEXT DEFAULT (datetime('now'))
    )""")

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

    tab_cal, tab_obj, tab_add = st.tabs(["📅 Calendrier", "🎯 Objectifs", "➕ Ajouter"])

    # ── CALENDRIER ─────────────────────────────────────────────────────────────
    with tab_cal:
        c1, c2 = st.columns([2, 1])
        with c1:
            f_type_ev = st.selectbox("Filtrer", ["Tous"] + TYPES_EVENT, key="ev_type")
            f_upcoming = st.checkbox("À venir uniquement", value=True, key="ev_upcoming")
        with c2:
            # Lien Google Calendar
            st.markdown("""
<div style="margin-top:8px;">
  <a href="https://calendar.google.com/calendar/u/3/r" target="_blank"
     style="font-family:'DM Mono',monospace;font-size:10px;color:#185FA5;text-decoration:none;
            background:#E6F1FB;border:1px solid #B5D4F4;border-radius:2px;padding:6px 12px;
            display:inline-block;letter-spacing:.06em;text-transform:uppercase;">
    ↗ Ouvrir Google Calendar
  </a>
</div>""", unsafe_allow_html=True)

        df_ev = get_events(
            conn,
            upcoming_only=f_upcoming,
            type_filter=None if f_type_ev == "Tous" else f_type_ev,
        )

        if df_ev.empty:
            st.info("Aucun événement.")
        else:
            # Vue par mois
            df_ev["date_obj"] = pd.to_datetime(df_ev["date_debut"])
            df_ev["mois_an"]  = df_ev["date_obj"].dt.strftime("%B %Y")

            for mois, grp in df_ev.groupby("mois_an", sort=False):
                st.markdown(f'<div class="section-title">{mois.capitalize()}</div>',
                            unsafe_allow_html=True)
                for _, ev in grp.iterrows():
                    color = EVENT_COLORS.get(ev.get("type_event","Autre"), "#888")
                    d_obj = ev["date_obj"]
                    delta = (d_obj.date() - date.today()).days
                    heure_str = f" · {ev['heure']}" if ev.get("heure") else ""

                    badge_delta = ""
                    if 0 <= delta <= 7:
                        badge_delta = f'<span style="font-family:\'DM Mono\',monospace;font-size:9px;background:#fff3cd;color:#7a5100;padding:2px 6px;border-radius:2px;margin-left:8px;">J-{delta}</span>'
                    elif delta < 0:
                        badge_delta = f'<span style="font-family:\'DM Mono\',monospace;font-size:9px;color:#aaa49a;margin-left:8px;">Passé</span>'

                    meet_btn = ""
                    if ev.get("meet_link"):
                        meet_btn = f'<a href="{ev["meet_link"]}" target="_blank" style="font-family:\'DM Mono\',monospace;font-size:9px;color:#0F6E56;text-decoration:none;margin-left:10px;letter-spacing:.05em;">↗ Meet</a>'

                    recurrent_badge = ""
                    if ev.get("recurrent"):
                        recurrent_badge = '<span style="font-family:\'DM Mono\',monospace;font-size:9px;color:#888;margin-left:6px;">↻ hebdo</span>'

                    st.markdown(f"""
<div style="border-left:3px solid {color};padding:10px 16px;margin:6px 0;
     background:#f7f5f0;border-radius:0 4px 4px 0;">
  <div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
    <span style="font-family:'DM Mono',monospace;font-size:10px;color:{color};
                 text-transform:uppercase;letter-spacing:.1em;">{ev.get('type_event','')}</span>
    {badge_delta}{recurrent_badge}
  </div>
  <div style="font-size:14px;font-weight:500;color:#1a1a1a;margin:3px 0;">
    {ev['titre']}{meet_btn}
  </div>
  <div style="font-size:12px;color:#888078;">
    {d_obj.strftime('%d %B %Y')}{heure_str}
    {' · '+ev['lieu'] if ev.get('lieu') else ''}
  </div>
  {f'<div style="font-size:12px;color:#aaa49a;margin-top:3px;">{ev["description"]}</div>'
    if ev.get('description') else ''}
</div>""", unsafe_allow_html=True)

                    if can_fn("settings"):
                        if st.button("🗑", key=f"del_ev_{ev['id']}", help="Supprimer"):
                            conn.execute("DELETE FROM events WHERE id=?", (ev["id"],))
                            conn.commit(); st.rerun()

        st.markdown("---")

        # Export ICS
        df_all_ev = get_events(conn)
        if not df_all_ev.empty:
            ics_content = generate_gcal_ics(df_all_ev)
            st.download_button(
                "⬇ Exporter tous les événements (.ics — Google Calendar / Apple)",
                ics_content.encode("utf-8"),
                file_name="eastwood_calendrier.ics",
                mime="text/calendar",
            )
            st.markdown("""
<div class="info-box">
<strong>Importer dans Google Calendar :</strong> Paramètres → Importer et exporter → Importer → sélectionner le fichier .ics<br>
<strong>Partager avec les fondateurs :</strong> Envoyer le fichier .ics à
alexis.barsus@gmail.com · cobolou@laposte.net · jules@eastwood-studio.fr
</div>""", unsafe_allow_html=True)

        # Réunion hebdo — section dédiée
        st.markdown('<div class="section-title">Réunions hebdomadaires</div>',
                    unsafe_allow_html=True)
        st.markdown("""
<div style="background:#f7f5f0;border:1px solid #e0dbd2;border-left:3px solid #185FA5;
     border-radius:2px;padding:16px 20px;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#185FA5;letter-spacing:.1em;text-transform:uppercase;">Récurrence</div>
  <div style="font-size:15px;font-weight:500;color:#1a1a1a;margin:4px 0;">Tous les mercredis · 18h00</div>
  <div style="font-size:12px;color:#888078;margin-bottom:10px;">Jules · Corentin · Alexis · Google Meet</div>
  <div style="display:flex;gap:12px;flex-wrap:wrap;">
    <a href="https://meet.google.com/new" target="_blank"
       style="font-family:'DM Mono',monospace;font-size:10px;background:#185FA5;color:#fff;
              padding:6px 14px;border-radius:2px;text-decoration:none;letter-spacing:.06em;text-transform:uppercase;">
      ↗ Créer Google Meet
    </a>
    <a href="mailto:alexis.barsus@gmail.com,cobolou@laposte.net?subject=Réunion Eastwood Studio — Mercredi 18h&body=Réunion hebdomadaire Eastwood Studio.%0AGoogle Meet : https://meet.google.com/new"
       style="font-family:'DM Mono',monospace;font-size:10px;background:#f0ece4;color:#1a1a1a;
              border:1px solid #e0dbd2;padding:6px 14px;border-radius:2px;text-decoration:none;
              letter-spacing:.06em;text-transform:uppercase;">
      ✉ Envoyer invitation
    </a>
  </div>
</div>""", unsafe_allow_html=True)

    # ── OBJECTIFS ──────────────────────────────────────────────────────────────
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
            with e3:
                ev_lieu   = st.text_input("Lieu", placeholder="Paris / En ligne")
                ev_meet   = st.text_input("Lien Meet/Zoom", placeholder="https://meet.google.com/...")
            ev_desc   = st.text_area("Description", height=72)
            ev_recur  = st.checkbox("Événement récurrent")
            ev_freq   = st.selectbox("Fréquence", ["hebdomadaire","bimensuel","mensuel"]) if ev_recur else None

            if st.form_submit_button("✓ Créer l'événement"):
                if not ev_titre:
                    st.error("Titre obligatoire.")
                else:
                    conn.execute("""INSERT INTO events
                        (titre,type_event,date_debut,heure,lieu,description,meet_link,recurrent,freq_recurrence,created_by)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (ev_titre, ev_type, ev_date.isoformat(), ev_heure,
                         ev_lieu, ev_desc, ev_meet, int(ev_recur), ev_freq or "",
                         st.session_state.get("user_display","")))
                    conn.commit()
                    st.success("✓ Événement créé."); st.rerun()

        st.markdown('<div class="section-title">Nouvel objectif</div>', unsafe_allow_html=True)
        with st.form("add_objectif"):
            o1,o2,o3 = st.columns(3)
            with o1:
                obj_titre = st.text_input("Titre *")
                obj_coll  = st.selectbox("Collection", ["SS26 — Été 2026","FW26 — Hiver 2026",
                                                         "SS25 — Été 2025","Général"])
            with o2:
                obj_type  = st.selectbox("Type", ["Production","Communication","Commercial",
                                                   "Finance","Logistique","RH","Autre"])
                obj_date  = st.date_input("Date cible", value=date.today())
            with o3:
                obj_prio  = st.selectbox("Priorité", ["Haute","Normal","Basse"])
                obj_stat  = st.selectbox("Statut", ["À démarrer","En cours","Terminé"])
            obj_desc = st.text_area("Description", height=60)

            if st.form_submit_button("✓ Créer l'objectif"):
                if not obj_titre:
                    st.error("Titre obligatoire.")
                else:
                    conn.execute("""INSERT INTO objectifs
                        (titre,collection,type_obj,date_cible,description,statut,priorite)
                        VALUES (?,?,?,?,?,?,?)""",
                        (obj_titre,obj_coll,obj_type,obj_date.isoformat(),
                         obj_desc,obj_stat,obj_prio))
                    conn.commit()
                    st.success("✓ Objectif créé."); st.rerun()

    conn.close()
