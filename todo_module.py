# ══════════════════════════════════════════════════════════════════════════════
# MODULE TODO ACCUEIL
# TODO hebdo par utilisateur · Objectifs globaux semaine · Jules assigne
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta

EW_V = "#7b506f"
EW_G = "#395f30"
EW_B = "#8a7968"
EW_S = "#ede3d3"
EW_C = "#f5f0e8"
EW_K = "#1a1a1a"

MEMBRES = ["Jules", "Corentin", "Alexis", "Tous"]
PRIORITES_TODO = ["Urgent", "Cette semaine", "Quand possible"]


def init_todo_db(conn):
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semaine TEXT,
        titre TEXT NOT NULL,
        description TEXT,
        assignee TEXT,
        priorite TEXT DEFAULT 'Cette semaine',
        fait INTEGER DEFAULT 0,
        created_by TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        done_at TEXT
    )""")
    conn.commit()


def get_semaine_courante():
    """Retourne le lundi de la semaine courante au format YYYY-WW."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-W%V"), monday


def get_todos(conn, semaine=None, assignee=None):
    q = "SELECT * FROM todos WHERE 1=1"
    p = []
    if semaine:  q += " AND semaine=?";  p.append(semaine)
    if assignee and assignee != "Tous":
        q += " AND (assignee=? OR assignee='Tous')"; p.append(assignee)
    return pd.read_sql(q + " ORDER BY fait ASC, priorite ASC, created_at ASC", conn, params=p)


def prio_color(p):
    return {"Urgent": "#c1440e", "Cette semaine": EW_V, "Quand possible": EW_B}.get(p, EW_B)


def render_todo_widget(conn, user_display, user_role, can_fn, compact=False):
    """
    Widget TODO affiché sur l'accueil.
    compact=True → version réduite pour la sidebar/accueil
    """
    init_todo_db(conn)
    semaine_id, lundi = get_semaine_courante()
    vendredi = lundi + timedelta(days=4)

    # Todos de la semaine pour cet utilisateur
    prenom = user_display.split()[0]
    df_my  = get_todos(conn, semaine=semaine_id, assignee=prenom)
    df_global = get_todos(conn, semaine=semaine_id, assignee="Tous")

    if compact:
        # ── Version accueil (compacte) ─────────────────────────────────────────
        done_my    = len(df_my[df_my["fait"]==1])
        total_my   = len(df_my)
        done_g     = len(df_global[df_global["fait"]==1])
        total_g    = len(df_global)
        pct_my     = int(done_my/total_my*100) if total_my > 0 else 0
        pct_g      = int(done_g/total_g*100)   if total_g  > 0 else 0

        st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};border-left:3px solid {EW_V};
     padding:14px 18px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <div style="font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.18em;
                text-transform:uppercase;color:{EW_V};">Semaine du {lundi.strftime('%d %b')} au {vendredi.strftime('%d %b')}</div>
    <div style="font-family:'DM Mono',monospace;font-size:10px;color:{EW_B};">{done_my}/{total_my} tâches</div>
  </div>""", unsafe_allow_html=True)

        # Mes tâches
        if df_my.empty:
            st.markdown(f'<div style="font-size:12px;color:{EW_B};padding:4px 0;">Aucune tâche cette semaine.</div>', unsafe_allow_html=True)
        else:
            for _, todo in df_my.iterrows():
                if todo.get("fait"):
                    continue  # N'afficher que les non faites sur l'accueil
                pc = prio_color(todo.get("priorite","Cette semaine"))
                st.markdown(f"""
<div style="border-left:2px solid {pc};padding:4px 10px;margin:4px 0;">
  <div style="font-size:12px;font-weight:500;">{todo['titre']}</div>
  {f'<div style="font-size:11px;color:{EW_B};">{todo["description"]}</div>' if todo.get("description") else ''}
</div>""", unsafe_allow_html=True)

                if st.button("✓", key=f"done_compact_{todo['id']}"):
                    conn.execute("UPDATE todos SET fait=1, done_at=? WHERE id=?",
                                 (str(date.today()), todo["id"]))
                    conn.commit(); st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        # Objectifs globaux (résumé)
        if not df_global.empty:
            st.markdown(f"""
<div style="background:{EW_C};border:0.5px solid {EW_S};padding:10px 14px;margin-bottom:10px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_B};
              text-transform:uppercase;letter-spacing:.15em;margin-bottom:6px;">
    Objectifs équipe — {done_g}/{total_g}
  </div>""", unsafe_allow_html=True)
            for _, todo in df_global.head(4).iterrows():
                done_c = EW_G if todo.get("fait") else EW_K
                st.markdown(f"""
<div style="font-size:11px;color:{done_c};padding:2px 0;">
  {'☑' if todo.get('fait') else '☐'} {todo['titre']}
</div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        return  # Fin version compacte

    # ── Version page complète (appelée depuis page Accueil full) ──────────────
    st.markdown(f'<div class="section-title">Semaine du {lundi.strftime("%d %B")} au {vendredi.strftime("%d %B %Y")}</div>', unsafe_allow_html=True)

    # Onglets
    _tbs = [f"📋 Mes tâches ({prenom})", "🎯 Objectifs équipe"]
    if can_fn("finance_write"):
        _tbs.append("✏️ Assigner des tâches")
    tab_obs = st.tabs(_tbs)
    tab_me = tab_obs[0]
    tab_team = tab_obs[1]
    tab_assign = tab_obs[2] if can_fn("finance_write") else None

    with tab_me:
        df_me2 = get_todos(conn, semaine=semaine_id, assignee=prenom)
        done2  = len(df_me2[df_me2["fait"]==1])
        total2 = len(df_me2)
        pct2   = int(done2/total2*100) if total2 > 0 else 0

        if total2 > 0:
            # Barre de progression
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
  <div style="flex:1;height:4px;background:{EW_S};">
    <div style="width:{pct2}%;height:4px;background:{EW_G if pct2==100 else EW_V};"></div>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:{EW_B};">{done2}/{total2} · {pct2}%</div>
</div>""", unsafe_allow_html=True)

        if df_me2.empty:
            st.info("Aucune tâche assignée cette semaine.")
        else:
            # Grouper par priorité
            for prio in ["Urgent", "Cette semaine", "Quand possible"]:
                df_p = df_me2[df_me2["priorite"]==prio]
                if df_p.empty: continue
                pc = prio_color(prio)
                st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;color:{pc};letter-spacing:.15em;text-transform:uppercase;margin:12px 0 6px;">{prio}</div>', unsafe_allow_html=True)
                for _, todo in df_p.iterrows():
                    done_style = f"text-decoration:line-through;opacity:.5;" if todo.get("fait") else ""
                    cc1,cc2 = st.columns([6,1])
                    with cc1:
                        st.markdown(f"""
<div style="border-left:2px solid {'#ccc' if todo.get('fait') else pc};
     padding:8px 12px;margin:4px 0;background:{'#f9f9f9' if todo.get('fait') else '#fff'};">
  <div style="font-size:13px;font-weight:500;{done_style}">{todo['titre']}</div>
  {f'<div style="font-size:11px;color:{EW_B};{done_style}">{todo["description"]}</div>' if todo.get("description") else ''}
</div>""", unsafe_allow_html=True)
                    with cc2:
                        if not todo.get("fait"):
                            if st.button("✓", key=f"done_{todo['id']}"):
                                conn.execute("UPDATE todos SET fait=1, done_at=? WHERE id=?",
                                             (str(date.today()), todo["id"]))
                                conn.commit(); st.rerun()
                        else:
                            if st.button("↩", key=f"undo_{todo['id']}", help="Marquer comme non fait"):
                                conn.execute("UPDATE todos SET fait=0, done_at=NULL WHERE id=?",
                                             (todo["id"],))
                                conn.commit(); st.rerun()

        # Ajouter une tâche perso
        st.markdown(f'<div class="section-title">Ajouter une tâche personnelle</div>', unsafe_allow_html=True)
        with st.form(f"add_todo_me_{prenom}"):
            at1,at2 = st.columns(2)
            with at1: at_titre = st.text_input("Tâche *")
            with at2: at_prio  = st.selectbox("Priorité", PRIORITES_TODO)
            at_desc = st.text_input("Détails (optionnel)")
            if st.form_submit_button("➕ Ajouter"):
                if not at_titre:
                    st.error("Titre obligatoire.")
                else:
                    conn.execute("""INSERT INTO todos
                        (semaine,titre,description,assignee,priorite,created_by)
                        VALUES (?,?,?,?,?,?)""",
                        (semaine_id, at_titre, at_desc, prenom, at_prio, prenom))
                    conn.commit(); st.rerun()

    with tab_team:
        df_team = get_todos(conn, semaine=semaine_id, assignee="Tous")
        done_t  = len(df_team[df_team["fait"]==1])
        total_t = len(df_team)

        if df_team.empty:
            st.info("Aucun objectif d'équipe défini cette semaine.")
        else:
            pct_t = int(done_t/total_t*100) if total_t > 0 else 0
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
  <div style="flex:1;height:4px;background:{EW_S};">
    <div style="width:{pct_t}%;height:4px;background:{EW_G if pct_t==100 else EW_V};"></div>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:{EW_B};">Équipe : {done_t}/{total_t} · {pct_t}%</div>
</div>""", unsafe_allow_html=True)

            for _, todo in df_team.iterrows():
                done_style = "text-decoration:line-through;opacity:.5;" if todo.get("fait") else ""
                pc = prio_color(todo.get("priorite","Cette semaine"))
                ct1,ct2 = st.columns([6,1])
                with ct1:
                    st.markdown(f"""
<div style="border-left:2px solid {'#ccc' if todo.get('fait') else pc};
     padding:8px 12px;margin:4px 0;">
  <div style="font-size:13px;font-weight:500;{done_style}">{todo['titre']}</div>
  {f'<div style="font-size:11px;color:{EW_B};">{todo["description"]}</div>' if todo.get("description") else ''}
  <div style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_B};margin-top:3px;">
    Créé par {todo.get('created_by','')} · {todo.get('priorite','')}
  </div>
</div>""", unsafe_allow_html=True)
                with ct2:
                    if not todo.get("fait"):
                        if st.button("✓", key=f"done_t_{todo['id']}"):
                            conn.execute("UPDATE todos SET fait=1, done_at=? WHERE id=?",
                                         (str(date.today()), todo["id"]))
                            conn.commit(); st.rerun()

    # ── Assigner des tâches (Jules only) ──────────────────────────────────────
    if tab_assign is not None:
        with tab_assign:
            st.markdown(f'<div class="section-title">Assigner une tâche à quelqu\'un</div>', unsafe_allow_html=True)
            with st.form("assign_todo"):
                as1,as2 = st.columns(2)
                with as1:
                    as_titre  = st.text_input("Tâche *")
                    as_assign = st.selectbox("Assigner à", MEMBRES)
                    as_prio   = st.selectbox("Priorité", PRIORITES_TODO)
                with as2:
                    as_sem = st.selectbox("Pour quelle semaine",
                                          ["Cette semaine", "Semaine prochaine"])
                    as_desc = st.text_area("Détails", height=80)

                if st.form_submit_button("✓ Assigner"):
                    if not as_titre:
                        st.error("Titre obligatoire.")
                    else:
                        if as_sem == "Semaine prochaine":
                            monday_next = lundi + timedelta(weeks=1)
                            sem_id = monday_next.strftime("%Y-W%V")
                        else:
                            sem_id = semaine_id
                        conn.execute("""INSERT INTO todos
                            (semaine,titre,description,assignee,priorite,created_by)
                            VALUES (?,?,?,?,?,?)""",
                            (sem_id, as_titre, as_desc, as_assign, as_prio,
                             st.session_state.get("user_display","Jules")))
                        conn.commit()
                        st.success(f"✓ Tâche assignée à {as_assign}."); st.rerun()

            # Historique semaines précédentes
            st.markdown(f'<div class="section-title">Semaines précédentes</div>', unsafe_allow_html=True)
            prev_sems = pd.read_sql(
                "SELECT DISTINCT semaine FROM todos WHERE semaine!=? ORDER BY semaine DESC LIMIT 4",
                conn, params=[semaine_id])
            if not prev_sems.empty:
                for sem in prev_sems["semaine"].tolist():
                    df_prev = get_todos(conn, semaine=sem)
                    done_prev = len(df_prev[df_prev["fait"]==1])
                    with st.expander(f"Semaine {sem} — {done_prev}/{len(df_prev)} terminées"):
                        for _, t in df_prev.iterrows():
                            icon = "☑" if t.get("fait") else "☐"
                            st.markdown(f"`{icon}` **{t['assignee']}** — {t['titre']}")
