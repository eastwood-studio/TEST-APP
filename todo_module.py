# todo_module.py — v2.3 — 1775684119 — 1775681681 — 1775665335
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
PRIORITES_TODO = ["Urgent", "Cette semaine", "Deux semaines", "Ce mois", "Quand possible"]


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

    c.execute("""CREATE TABLE IF NOT EXISTS todo_subtasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        todo_id INTEGER NOT NULL,
        titre TEXT NOT NULL,
        assignee TEXT,
        fait INTEGER DEFAULT 0,
        ordre INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(todo_id) REFERENCES todos(id)
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
        _tbs.append("📥 Import en masse")
    tab_obs = st.tabs(_tbs)
    tab_me = tab_obs[0]
    tab_team = tab_obs[1]
    tab_assign = tab_obs[2] if can_fn("finance_write") else None
    tab_import = tab_obs[3] if can_fn("finance_write") else None

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
        # ── Chart par individu ──────────────────────────────────────────────────
        st.markdown('<div class="section-title">Avancement par membre</div>', unsafe_allow_html=True)
        try:
            df_indiv = pd.read_sql("""
                SELECT assignee, fait, COUNT(*) as nb FROM todos
                WHERE semaine=?
                GROUP BY assignee, fait
            """, conn, params=[semaine_id])
            if not df_indiv.empty:
                membres_indiv = ["Jules","Corentin","Alexis","Tous"]
                bar_data = []
                for m in membres_indiv:
                    sub = df_indiv[df_indiv["assignee"]==m]
                    total_m = int(sub["nb"].sum())
                    done_m  = int(sub[sub["fait"]==1]["nb"].sum()) if not sub[sub["fait"]==1].empty else 0
                    if total_m > 0:
                        bar_data.append({"membre":m,"fait":done_m,"total":total_m})
                if bar_data:
                    bar_cols = st.columns(len(bar_data))
                    for i, bd in enumerate(bar_data):
                        pct_m = int(bd["fait"]/bd["total"]*100)
                        c_bar = "#395f30" if pct_m==100 else "#7b506f" if pct_m>50 else "#c9800a"
                        with bar_cols[i]:
                            st.markdown(f"""
<div style="text-align:center;padding:8px 4px;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;font-weight:500;">{bd['membre']}</div>
  <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:{c_bar};">{pct_m}%</div>
  <div style="height:5px;background:#ede3d3;margin:4px 0;border-radius:2px;">
    <div style="width:{pct_m}%;height:5px;background:{c_bar};border-radius:2px;"></div>
  </div>
  <div style="font-size:10px;color:#8a7968;">{bd['fait']}/{bd['total']}</div>
</div>""", unsafe_allow_html=True)
        except Exception:
            pass

        # ── Liste des tâches équipe ─────────────────────────────────────────────
        st.markdown('<div class="section-title">Tâches de la semaine</div>', unsafe_allow_html=True)

        df_team_all = pd.read_sql("""
            SELECT * FROM todos WHERE semaine=?
            ORDER BY fait ASC, assignee ASC, priorite ASC
        """, conn, params=[semaine_id])

        if df_team_all.empty:
            st.info("Aucune tâche cette semaine.")
        else:
            for _, todo in df_team_all.iterrows():
                pc = prio_color(todo.get("priorite","Cette semaine"))

                # Charger sous-tâches
                try:
                    df_sub = pd.read_sql(
                        "SELECT * FROM todo_subtasks WHERE todo_id=? ORDER BY ordre ASC",
                        conn, params=[int(todo["id"])])
                except Exception:
                    df_sub = pd.DataFrame()
                sub_total = len(df_sub)
                sub_done  = int(df_sub["fait"].sum()) if not df_sub.empty else 0

                done_c = "#ccc" if todo.get("fait") else pc
                done_s = "text-decoration:line-through;opacity:.5;" if todo.get("fait") else ""

                c_card, c_btns = st.columns([7, 1])
                with c_card:
                    st.markdown(f"""
<div style="border:0.5px solid #e0dbd2;border-left:3px solid {done_c};
     padding:8px 12px;margin:3px 0;background:{'#fafaf8' if todo.get('fait') else '#fff'};">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div style="flex:1;">
      <div style="font-size:13px;font-weight:500;{done_s}color:{'#aaa' if todo.get('fait') else '#1a1a1a'};">{todo['titre']}</div>
      {f'<div style="font-size:11px;color:#8a7968;">{todo["description"]}</div>' if todo.get("description") else ''}
      <div style="font-family:'DM Mono',monospace;font-size:8px;color:{pc};margin-top:3px;">
        {todo.get('assignee','')} · {todo.get('priorite','')}
      </div>
    </div>
    {f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;color:#395f30;margin-left:8px;">{sub_done}/{sub_total} ✓</div>' if sub_total > 0 else ''}
  </div>
</div>""", unsafe_allow_html=True)

                    # Afficher sous-tâches
                    if not df_sub.empty:
                        for _, sub in df_sub.iterrows():
                            dot = "#395f30" if sub.get("fait") else "#d9c8ae"
                            sub_s = "line-through;color:#aaa;" if sub.get("fait") else ""
                            sc1, sc2 = st.columns([8, 1])
                            with sc1:
                                st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;padding:3px 12px 3px 20px;">
  <div style="width:8px;height:8px;border-radius:50%;background:{dot};flex-shrink:0;
       border:1px solid {'#395f30' if sub.get('fait') else '#c8c3b8'};"></div>
  <div style="font-size:11px;text-decoration:{sub_s}">{sub['titre']}</div>
</div>""", unsafe_allow_html=True)
                            with sc2:
                                if not sub.get("fait"):
                                    if st.button("·", key=f"tsub_{sub['id']}",
                                                 help="Valider"):
                                        conn.execute("UPDATE todo_subtasks SET fait=1 WHERE id=?",
                                                     (sub["id"],))
                                        # Si toutes sous-tâches faites → todo fait
                                        n_left = conn.execute(
                                            "SELECT COUNT(*) FROM todo_subtasks WHERE todo_id=? AND fait=0",
                                            (todo["id"],)).fetchone()[0]
                                        if n_left == 0:
                                            conn.execute(
                                                "UPDATE todos SET fait=1, done_at=? WHERE id=?",
                                                (str(date.today()), todo["id"]))
                                        conn.commit(); st.rerun()

                with c_btns:
                    # Cocher/décocher
                    if not todo.get("fait"):
                        if st.button("☐", key=f"tdone_{todo['id']}", help="Marquer fait"):
                            conn.execute("UPDATE todos SET fait=1, done_at=? WHERE id=?",
                                         (str(date.today()), todo["id"]))
                            conn.commit(); st.rerun()
                    elif can_fn("finance_write"):
                        if st.button("☑", key=f"tundo_{todo['id']}", help="Remettre en non fait"):
                            conn.execute("UPDATE todos SET fait=0, done_at=NULL WHERE id=?",
                                         (todo["id"],))
                            # Réouvrir les sous-tâches
                            conn.execute("UPDATE todo_subtasks SET fait=0 WHERE todo_id=?",
                                         (todo["id"],))
                            conn.commit(); st.rerun()

                    # Jules : modifier et supprimer
                    if can_fn("finance_write"):
                        if st.button("⚙", key=f"tedit_{todo['id']}", help="Modifier"):
                            st.session_state[f"edit_team_{todo['id']}"] = not st.session_state.get(f"edit_team_{todo['id']}", False)
                        if st.button("🗑", key=f"tdel_{todo['id']}", help="Supprimer"):
                            conn.execute("DELETE FROM todo_subtasks WHERE todo_id=?", (todo["id"],))
                            conn.execute("DELETE FROM todos WHERE id=?", (todo["id"],))
                            conn.commit(); st.rerun()

                # Formulaire édition inline
                if can_fn("finance_write") and st.session_state.get(f"edit_team_{todo['id']}"):
                    with st.form(f"edit_team_form_{todo['id']}"):
                        et_titre = st.text_input("Titre", value=todo.get("titre",""))
                        et_prio  = st.selectbox("Priorité", PRIORITES_TODO,
                            index=PRIORITES_TODO.index(todo.get("priorite","Cette semaine"))
                            if todo.get("priorite") in PRIORITES_TODO else 0)
                        et_desc  = st.text_area("Détails", value=todo.get("description","") or "", height=50)
                        et_ass   = st.selectbox("Assigné à", MEMBRES,
                            index=MEMBRES.index(todo.get("assignee","Tous"))
                            if todo.get("assignee") in MEMBRES else 0)
                        if st.form_submit_button("💾"):
                            conn.execute(
                                "UPDATE todos SET titre=?,priorite=?,description=?,assignee=? WHERE id=?",
                                (et_titre,et_prio,et_desc,et_ass,todo["id"]))
                            st.session_state.pop(f"edit_team_{todo['id']}", None)
                            conn.commit(); st.rerun()

        # ── Chart trimestriel ───────────────────────────────────────────────────
        st.markdown('<div class="section-title">Suivi trimestriel</div>', unsafe_allow_html=True)
        try:
            df_all_hist = pd.read_sql("""
                SELECT semaine, fait, COUNT(*) as nb FROM todos
                WHERE semaine IS NOT NULL
                GROUP BY semaine, fait
                ORDER BY semaine ASC
            """, conn)
            if not df_all_hist.empty:
                sems = sorted(df_all_hist["semaine"].unique())[-13:]
                done_q  = []
                total_q = []
                for s in sems:
                    sub_s = df_all_hist[df_all_hist["semaine"]==s]
                    t = int(sub_s["nb"].sum())
                    d = int(sub_s[sub_s["fait"]==1]["nb"].sum()) if not sub_s[sub_s["fait"]==1].empty else 0
                    total_q.append(t); done_q.append(d)
                st.components.v1.html(f"""
<div style="position:relative;height:180px;">
<canvas id="chartTrimestre"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
new Chart(document.getElementById('chartTrimestre'), {{
  type:'bar',
  data:{{labels:{sems},datasets:[
    {{label:'Faites',data:{done_q},backgroundColor:'#395f3099',borderColor:'#395f30',borderWidth:1}},
    {{label:'Total',data:{total_q},backgroundColor:'#7b506f22',borderColor:'#7b506f',borderWidth:1}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top',labels:{{font:{{family:'DM Mono',size:9}}}}}}}},
    scales:{{x:{{ticks:{{font:{{family:'DM Mono',size:8}},maxRotation:45}}}},
             y:{{ticks:{{font:{{family:'DM Mono',size:9}},stepSize:1}}}}}}
  }}
}});
</script>""", height=200)
        except Exception:
            pass

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
                                          ["Cette semaine", "Semaine prochaine", "Date exacte"])
                    if as_sem == "Date exacte":
                        as_date_exacte = st.date_input("Date exacte", value=date.today())
                    else:
                        as_date_exacte = None
                    as_repete = st.checkbox("Répéter chaque semaine")
                    as_desc = st.text_area("Détails", height=60)
                    st.markdown("**Sous-tâches** (optionnel, max 10)")
                    as_subtasks = []
                    for _si in range(10):
                        _st_val = st.text_input(f"Sous-tâche {_si+1}", key=f"sub_{_si}",
                                                 label_visibility="collapsed" if _si > 0 else "visible",
                                                 placeholder=f"Sous-tâche {_si+1}")
                        if _st_val.strip():
                            as_subtasks.append(_st_val.strip())
                        elif _si > 0:
                            break  # Stop dès qu'une sous-tâche est vide

                if st.form_submit_button("✓ Assigner"):
                    if not as_titre:
                        st.error("Titre obligatoire.")
                    else:
                        if as_sem == "Semaine prochaine":
                            monday_next = lundi + timedelta(weeks=1)
                            sem_id = monday_next.strftime("%Y-W%V")
                        elif as_sem == "Date exacte" and as_date_exacte:
                            monday_exact = as_date_exacte - timedelta(days=as_date_exacte.weekday())
                            sem_id = monday_exact.strftime("%Y-W%V")
                        else:
                            sem_id = semaine_id

                        # Répétition hebdo : créer 4 occurrences
                        sems_to_create = [sem_id]
                        if as_repete:
                            # Calcul du lundi de la semaine sem_id sans strptime %V
                            from datetime import datetime as _dt
                            try:
                                base_monday = _dt.strptime(sem_id + "-1", "%Y-W%V-%w").date()
                            except Exception:
                                # Fallback : lundi courant
                                base_monday = lundi
                            for w in range(1, 4):
                                next_m = base_monday + timedelta(weeks=w)
                                sems_to_create.append(next_m.strftime("%Y-W%V"))

                        for sid in sems_to_create:
                            conn.execute("""INSERT INTO todos
                                (semaine,titre,description,assignee,priorite,created_by)
                                VALUES (?,?,?,?,?,?)""",
                                (sid, as_titre, as_desc, as_assign, as_prio,
                                 st.session_state.get("user_display","Jules")))
                        # Insérer les sous-tâches
                        if as_subtasks:
                            last_todo_id = conn.execute("SELECT MAX(id) FROM todos").fetchone()[0]
                            for _si, _st in enumerate(as_subtasks):
                                conn.execute("""INSERT INTO todo_subtasks
                                    (todo_id, titre, assignee, ordre)
                                    VALUES (?,?,?,?)""",
                                    (last_todo_id, _st, as_assign, _si))
                        conn.commit()
                        nb_sem = len(sems_to_create)
                        st.success(f"✓ Tâche assignée à {as_assign}{' · ' + str(nb_sem) + ' semaines' if nb_sem>1 else ''}."); st.rerun()

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

    # ── IMPORT EN MASSE (Jules only) ───────────────────────────────────────────
    if tab_import is not None:
        with tab_import:
            st.markdown('<div class="section-title">Import TODO en masse</div>', unsafe_allow_html=True)
            st.markdown("""
<div class="info-box">
Nouveau format d'import :<br>
<code>TODO 08/04/2025</code> → date de la semaine<br>
<code>• Réseaux sociaux</code> → catégorie (bullet •)<br>
<code>* Gestion Pinterest</code> → sous-catégorie (* étoile)<br>
<code>- 1. Analyser (Alexis)</code> → tâche avec assigné entre parenthèses<br>
<code>- 2a. Remplir onglet</code> → sous-tâche (lettre après chiffre)
</div>""", unsafe_allow_html=True)

            imp_sem = st.selectbox("Semaine cible", ["Cette semaine", "Semaine prochaine"], key="imp_sem")
            if imp_sem == "Semaine prochaine":
                target_lundi = lundi + timedelta(weeks=1)
            else:
                target_lundi = lundi
            target_sem_id = target_lundi.strftime("%Y-W%V")

            raw_text = st.text_area(
                "Coller les TODO ici",
                height=400,
                placeholder="TODO 08/04/2025\n\n• Réseaux sociaux\n* Gestion Pinterest\n- 1. Analyser les 18 catégories (Alexis)\n- 2. Remplir les onglets\n- 2a. Remplir 'Pour elle'",
                key="imp_raw"
            )

            if raw_text.strip():
                import re as _re
                tasks_parsed = []
                current_cat = ""
                current_subcat = ""
                current_assignee_cat = "Tous"
                current_prio = "Cette semaine"
                target_date_parsed = None
                lines_raw = raw_text.strip().split("\n")

                for line in lines_raw:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    # En-tête TODO avec date
                    m_date = _re.match(r"TODO\s+(\d{1,2}/\d{1,2}/\d{4})", stripped)
                    if m_date:
                        try:
                            from datetime import datetime as _dtp
                            target_date_parsed = _dtp.strptime(m_date.group(1), "%d/%m/%Y").date()
                        except Exception:
                            pass
                        continue
                    # Catégorie : bullet •
                    if stripped.startswith("•") or stripped.startswith("●"):
                        cat_text = stripped.lstrip("•● ").strip()
                        m_ca = _re.search(r"\(([^)]+)\)\s*$", cat_text)
                        if m_ca:
                            ra = m_ca.group(1).strip().lower()
                            cat_text = cat_text[:m_ca.start()].strip()
                            current_assignee_cat = ("Jules" if "jules" in ra else
                                                    "Corentin" if "corentin" in ra else
                                                    "Alexis" if "alexis" in ra else "Tous")
                        else:
                            current_assignee_cat = "Tous"
                        current_cat = cat_text
                        current_subcat = ""
                        continue
                    # Sous-catégorie : étoile *
                    if stripped.startswith("*") and not stripped.startswith("**"):
                        current_subcat = stripped.lstrip("* ").strip()
                        continue
                    # Tâche : tiret -
                    if stripped.startswith("-"):
                        task_raw = stripped.lstrip("- ").strip()
                        if not task_raw:
                            continue
                        task_raw = _re.sub(r"^\d+[a-z]?\.\s*", "", task_raw)
                        m_ta = _re.search(r"\(([^)]+)\)\s*$", task_raw)
                        assignee = current_assignee_cat
                        if m_ta:
                            ra = m_ta.group(1).strip().lower()
                            task_raw = task_raw[:m_ta.start()].strip()
                            assignee = ("Jules" if "jules" in ra else
                                        "Corentin" if "corentin" in ra else
                                        "Alexis" if "alexis" in ra else current_assignee_cat)
                        prio = "Urgent" if "urgent" in task_raw.lower() else current_prio
                        desc_ctx = current_subcat or current_cat
                        tasks_parsed.append({
                            "titre": task_raw[:120],
                            "categorie": desc_ctx[:60],
                            "assignee": assignee,
                            "priorite": prio,
                        })

                if tasks_parsed:
                    # Semaine effective
                    if target_date_parsed:
                        monday_p = target_date_parsed - timedelta(days=target_date_parsed.weekday())
                        effective_sem = monday_p.strftime("%Y-W%V")
                        st.info(f"Date détectée : {target_date_parsed.strftime('%d/%m/%Y')} → semaine {effective_sem}")
                    else:
                        effective_sem = target_sem_id

                    st.markdown(f'<div class="section-title">Aperçu — {len(tasks_parsed)} tâches détectées</div>', unsafe_allow_html=True)
                    by_assignee = {}
                    for t in tasks_parsed:
                        a = t["assignee"]
                        if a not in by_assignee:
                            by_assignee[a] = []
                        by_assignee[a].append(t)

                    for asgn, tasks in by_assignee.items():
                        st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:9px;color:#7b506f;
     text-transform:uppercase;letter-spacing:.15em;margin:10px 0 6px;">
  {asgn} ({len(tasks)} tâches)
</div>""", unsafe_allow_html=True)
                        for t in tasks:
                            pc = {"Urgent":"#c1440e","Cette semaine":"#7b506f","Quand possible":"#8a7968"}.get(t["priorite"],"#8a7968")
                            st.markdown(f"""
<div style="display:flex;gap:10px;align-items:baseline;border-bottom:1px solid #ede3d3;
     padding:4px 0;font-size:12px;">
  <span style="font-family:'DM Mono',monospace;font-size:9px;color:{pc};">{t["priorite"]}</span>
  <span style="font-weight:500;">{t["titre"]}</span>
  <span style="color:#8a7968;font-size:11px;">{t["categorie"]}</span>
</div>""", unsafe_allow_html=True)

                    if st.button(f"✓ Importer {len(tasks_parsed)} tâches → semaine {effective_sem}", type="primary"):
                        conn.execute("DELETE FROM todos WHERE semaine=? AND created_by=?",
                                     (effective_sem, prenom))
                        for t in tasks_parsed:
                            conn.execute("""INSERT INTO todos
                                (semaine,titre,description,assignee,priorite,created_by)
                                VALUES (?,?,?,?,?,?)""",
                                (effective_sem, t["titre"], t["categorie"],
                                 t["assignee"], t["priorite"], prenom))
                        conn.commit()
                        st.success(f"✓ {len(tasks_parsed)} tâches importées pour la semaine {effective_sem}.")
                        st.rerun()
                else:
                    st.warning("Aucune tâche détectée. Assurez-vous que les tâches commencent par '- '.")
