# ══════════════════════════════════════════════════════════════════════════════
# MODULE BALANCE INTERNE — style Tricount
# Suit les avances et remboursements entre fondateurs et Eastwood Studio
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import date, datetime

EW_V = "#7b506f"
EW_G = "#395f30"
EW_B = "#8a7968"
EW_S = "#ede3d3"
EW_C = "#f5f0e8"
EW_K = "#1a1a1a"

MEMBRES = ["Jules", "Corentin", "Alexis", "Eastwood Studio"]
TYPES_MOUVEMENT = [
    "Avance personnelle",        # Un fondateur avance pour Eastwood
    "Remboursement Eastwood",    # Eastwood rembourse un fondateur
    "Prise de stock",            # Un fondateur prend du stock (valorisé)
    "Note de frais validée",     # Frais remboursable validé
    "Prêt interne",              # Entre fondateurs
    "Apport en capital",         # Apport de fonds
    "Rémunération",              # Salaire / dividende
    "Autre",
]


def init_balance_db(conn):
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS balance_mouvements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_mouvement TEXT,
        type_mouvement TEXT,
        payeur TEXT,
        beneficiaire TEXT,
        montant REAL,
        description TEXT,
        ref_transaction INTEGER,
        valide INTEGER DEFAULT 0,
        valide_par TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.commit()


def get_mouvements(conn, membre=None):
    q = "SELECT * FROM balance_mouvements WHERE 1=1"
    p = []
    if membre:
        q += " AND (payeur=? OR beneficiaire=?)"; p += [membre, membre]
    return pd.read_sql(q + " ORDER BY date_mouvement DESC", conn, params=p)


def compute_soldes(conn):
    """
    Calcule le solde net de chaque fondateur vis-à-vis d'Eastwood Studio.
    Positif = Eastwood doit de l'argent au fondateur
    Négatif = Le fondateur doit de l'argent à Eastwood
    """
    df = get_mouvements(conn)
    soldes = {"Jules": 0.0, "Corentin": 0.0, "Alexis": 0.0}

    # Aussi récupérer depuis les transactions taguées avec un payeur fondateur
    try:
        df_tx = pd.read_sql("""
            SELECT payeur, beneficiaire, total_ht, type_op, description, date_op
            FROM transactions
            WHERE payeur IN ('Jules','Corentin','Alexis')
               OR beneficiaire IN ('Jules','Corentin','Alexis')
            ORDER BY date_op DESC
        """, conn)
    except Exception:
        df_tx = pd.DataFrame()

    if not df_tx.empty:
        for _, row in df_tx.iterrows():
            montant = float(row["total_ht"] or 0)
            if row["type_op"] in ("Achat", "Achat perso"):
                # Un fondateur a payé pour Eastwood → Eastwood lui doit
                if row["payeur"] in soldes:
                    soldes[row["payeur"]] += montant
            elif row["type_op"] == "Vente":
                # Un fondateur a reçu un paiement pour Eastwood → il doit à Eastwood
                if row["beneficiaire"] in soldes and row["beneficiaire"] != "Eastwood Studio":
                    soldes[row["beneficiaire"]] -= montant

    # Mouvements explicites de la table balance
    if not df.empty:
        for _, row in df.iterrows():
            montant = float(row["montant"] or 0)
            payeur = row.get("payeur","")
            benef  = row.get("beneficiaire","")

            if payeur in soldes:
                soldes[payeur] += montant   # a payé → lui doit
            if benef in soldes:
                soldes[benef] -= montant    # a reçu → doit à Eastwood

    return soldes


def fmt_eur(v):
    if v is None: return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE BALANCE INTERNE
# ══════════════════════════════════════════════════════════════════════════════
def page_balance(can_fn, DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_balance_db(conn)

    st.markdown("### Balance interne — Fondateurs")

    st.markdown("""
<div class="info-box">
Suivi des avances, remboursements et prises de stock entre les fondateurs et Eastwood Studio.
Le solde est calculé automatiquement depuis les transactions taguées avec un payeur fondateur.
</div>""", unsafe_allow_html=True)

    tab_soldes, tab_historique, tab_new = st.tabs([
        "⚖️ Soldes",
        "📋 Historique mouvements",
        "➕ Nouveau mouvement",
    ])

    with tab_soldes:
        soldes = compute_soldes(conn)

        # Cartes soldes
        cols_s = st.columns(3)
        for i, (membre, solde) in enumerate(soldes.items()):
            with cols_s[i]:
                color = EW_G if solde > 0 else ("#c1440e" if solde < 0 else EW_B)
                label = "Eastwood lui doit" if solde > 0 else ("Il doit à Eastwood" if solde < 0 else "Équilibré")
                initials = membre[:2].upper()
                st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};border-top:3px solid {color};
     padding:16px;text-align:center;">
  <div style="width:36px;height:36px;background:{color}18;border-radius:50%;
       display:flex;align-items:center;justify-content:center;
       font-family:'DM Mono',monospace;font-size:12px;color:{color};
       margin:0 auto 10px;">{initials}</div>
  <div style="font-weight:500;font-size:14px;color:{EW_K};">{membre}</div>
  <div style="font-family:'DM Mono',monospace;font-size:22px;font-weight:500;
       color:{color};margin:8px 0;">{fmt_eur(abs(solde))}</div>
  <div style="font-size:11px;color:{EW_B};">{label}</div>
</div>""", unsafe_allow_html=True)

        # Total dettes Eastwood
        total_du = sum(s for s in soldes.values() if s > 0)
        total_recevable = sum(-s for s in soldes.values() if s < 0)
        st.markdown(f"""
<div style="background:{EW_C};border:0.5px solid {EW_S};padding:12px 18px;margin-top:16px;
     display:flex;justify-content:space-between;">
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};
                text-transform:uppercase;letter-spacing:.15em;">Eastwood doit (total)</div>
    <div style="font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:#c1440e;">
      {fmt_eur(total_du)}
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};
                text-transform:uppercase;letter-spacing:.15em;">Eastwood doit recevoir</div>
    <div style="font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:{EW_G};">
      {fmt_eur(total_recevable)}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        # Tableau détaillé des transactions impliquant des fondateurs
        st.markdown(f'<div class="section-title">Détail — Transactions avec fondateurs</div>', unsafe_allow_html=True)
        try:
            df_tx_fond = pd.read_sql("""
                SELECT date_op, description, payeur, beneficiaire, total_ht, type_op, categorie
                FROM transactions
                WHERE payeur IN ('Jules','Corentin','Alexis')
                   OR beneficiaire IN ('Jules','Corentin','Alexis')
                ORDER BY date_op DESC
                LIMIT 50
            """, conn)
            if not df_tx_fond.empty:
                st.dataframe(df_tx_fond.rename(columns={
                    "date_op":"Date","description":"Description",
                    "payeur":"Payeur","beneficiaire":"Bénéficiaire",
                    "total_ht":"Montant HT","type_op":"Type","categorie":"Catégorie"
                }), use_container_width=True, hide_index=True)
            else:
                st.info("Aucune transaction avec fondateur. Taguez vos opérations avec un payeur fondateur.")
        except Exception as e:
            st.info("Données non disponibles.")

    with tab_historique:
        df_hist = get_mouvements(conn)

        f_membre = st.selectbox("Filtrer par membre", ["Tous","Jules","Corentin","Alexis"])
        if f_membre != "Tous":
            df_hist = df_hist[(df_hist["payeur"]==f_membre) | (df_hist["beneficiaire"]==f_membre)]

        if df_hist.empty:
            st.info("Aucun mouvement enregistré.")
        else:
            for _, row in df_hist.iterrows():
                valide_c = EW_G if row.get("valide") else "#c9800a"
                valide_l = "✓ Validé" if row.get("valide") else "En attente"
                st.markdown(f"""
<div style="border:0.5px solid {EW_S};padding:10px 14px;margin:5px 0;background:#fff;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <span style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_V};
                   text-transform:uppercase;letter-spacing:.08em;">{row.get('type_mouvement','')}</span>
      <div style="font-weight:500;font-size:13px;margin-top:2px;">{row.get('description','')}</div>
      <div style="font-size:11px;color:{EW_B};">
        {row.get('payeur','')} → {row.get('beneficiaire','')} · {row.get('date_mouvement','')}
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-family:'DM Mono',monospace;font-size:16px;font-weight:500;">
        {fmt_eur(row.get('montant'))}
      </div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:{valide_c};">{valide_l}</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

                # Jules peut valider
                if can_fn("finance_write") and not row.get("valide"):
                    if st.button("✓ Valider", key=f"val_mov_{row['id']}"):
                        conn.execute("""UPDATE balance_mouvements
                            SET valide=1, valide_par=? WHERE id=?""",
                            (st.session_state.get("user_display","Jules"), row["id"]))
                        conn.commit(); st.rerun()

            # Export
            buf_bal = io.BytesIO()
            df_hist.to_excel(buf_bal, index=False, engine="openpyxl")
            st.download_button("⬇ Export Excel", buf_bal.getvalue(),
                file_name="balance_eastwood.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tab_new:
        st.markdown(f'<div class="section-title">Nouveau mouvement</div>', unsafe_allow_html=True)
        with st.form("new_mouvement"):
            nm1,nm2 = st.columns(2)
            with nm1:
                m_type  = st.selectbox("Type de mouvement", TYPES_MOUVEMENT)
                m_payeur= st.selectbox("De", MEMBRES)
                m_benef = st.selectbox("Vers", MEMBRES)
                m_date  = st.date_input("Date", value=date.today())
            with nm2:
                m_mont  = st.number_input("Montant (€)", min_value=0.0, value=0.0, step=0.01)
            m_desc = st.text_area("Description", height=70,
                                  placeholder="ex: Avance achat tissu Solotex — remb. à Jules")

            if st.form_submit_button("✓ Enregistrer le mouvement"):
                if not m_desc or m_mont == 0:
                    st.error("Description et montant obligatoires.")
                elif m_payeur == m_benef:
                    st.error("Le payeur et le bénéficiaire doivent être différents.")
                else:
                    conn.execute("""INSERT INTO balance_mouvements
                        (date_mouvement,type_mouvement,payeur,beneficiaire,montant,description,valide)
                        VALUES (?,?,?,?,?,?,?)""",
                        (str(m_date),m_type,m_payeur,m_benef,m_mont,m_desc,
                         1 if can_fn("finance_write") else 0))
                    conn.commit()
                    st.success("✓ Mouvement enregistré.")
                    if not can_fn("finance_write"):
                        st.info("En attente de validation par Jules.")
                    st.rerun()

    conn.close()
