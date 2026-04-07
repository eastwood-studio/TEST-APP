# ══════════════════════════════════════════════════════════════════════════════
# MODULE BALANCE INTERNE v2
# Connecté aux opérations — pas de saisie directe
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import date

EW_V = "#7b506f"
EW_G = "#395f30"
EW_B = "#8a7968"
EW_S = "#ede3d3"
EW_C = "#f5f0e8"
EW_K = "#1a1a1a"
MEMBRES = ["Jules", "Corentin", "Alexis"]


def fmt_eur(v):
    if v is None: return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


def compute_soldes(conn):
    soldes = {m: 0.0 for m in MEMBRES}
    details = {m: [] for m in MEMBRES}
    try:
        df = pd.read_sql("""
            SELECT id, date_op, description, payeur, beneficiaire,
                   total_ht, type_op, categorie
            FROM transactions
            WHERE payeur IN ('Jules','Corentin','Alexis')
               OR beneficiaire IN ('Jules','Corentin','Alexis')
            ORDER BY date_op DESC
        """, conn)
    except Exception:
        return soldes, details
    if df.empty:
        return soldes, details
    for _, row in df.iterrows():
        montant = float(row.get("total_ht",0) or 0)
        payeur  = str(row.get("payeur","") or "")
        benef   = str(row.get("beneficiaire","") or "")
        type_op = str(row.get("type_op","") or "")
        desc    = str(row.get("description","") or "")
        d       = str(row.get("date_op","") or "")
        if payeur in MEMBRES and type_op in ("Achat","Achat perso"):
            soldes[payeur] += montant
            details[payeur].append({"date":d,"desc":desc,"montant":montant,"sens":"avance","color":EW_G})
        if benef in MEMBRES and type_op in ("Achat perso","Vente"):
            soldes[benef] -= montant
            details[benef].append({"date":d,"desc":desc,"montant":-montant,"sens":"reçu","color":"#c1440e"})
    return soldes, details


def page_balance(can_fn, DB_PATH):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    st.markdown("### Balance interne — Fondateurs")
    st.markdown(f"""
<div class="info-box">
La balance est calculée depuis les opérations. Pour enregistrer un mouvement,
créez une ligne d'opération avec le payeur ou bénéficiaire fondateur.
<br><strong>Achat + payeur fondateur</strong> → Eastwood lui doit.
<strong>Achat perso + bénéficiaire fondateur</strong> → il doit à Eastwood.
</div>""", unsafe_allow_html=True)

    tab_sol, tab_hist, tab_info = st.tabs(["⚖️ Soldes","📋 Historique","ℹ️ Comment enregistrer"])

    with tab_sol:
        soldes, details = compute_soldes(conn)
        cols_s = st.columns(3)
        total_du  = sum(s for s in soldes.values() if s > 0)
        total_rec = sum(-s for s in soldes.values() if s < 0)
        for i, membre in enumerate(MEMBRES):
            solde = soldes[membre]
            with cols_s[i]:
                color = EW_G if solde > 0 else ("#c1440e" if solde < 0 else EW_B)
                label = "Eastwood lui doit" if solde > 0 else ("Il doit à Eastwood" if solde < 0 else "Équilibré")
                st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};border-top:3px solid {color};
     padding:16px;text-align:center;">
  <div style="font-weight:500;font-size:14px;">{membre}</div>
  <div style="font-family:'DM Mono',monospace;font-size:22px;font-weight:500;
       color:{color};margin:8px 0;">{fmt_eur(abs(solde))}</div>
  <div style="font-size:11px;color:{EW_B};">{label}</div>
</div>""", unsafe_allow_html=True)
                if details[membre]:
                    with st.expander(f"Détail {membre}"):
                        for d in details[membre][:15]:
                            st.markdown(f"""
<div style="display:flex;justify-content:space-between;font-size:11px;
     border-bottom:1px solid {EW_S};padding:3px 0;">
  <span style="color:{EW_B};">{d["date"]} · {d["desc"][:40]}</span>
  <span style="font-family:'DM Mono',monospace;color:{d["color"]};">{d["sens"]} {fmt_eur(abs(d["montant"]))}</span>
</div>""", unsafe_allow_html=True)
        st.markdown(f"""
<div style="background:{EW_C};border:0.5px solid {EW_S};padding:12px 18px;margin-top:14px;display:flex;justify-content:space-between;">
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};text-transform:uppercase;letter-spacing:.15em;">Eastwood doit</div>
    <div style="font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:#c1440e;">{fmt_eur(total_du)}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'DM Mono',monospace;font-size:8px;color:{EW_B};text-transform:uppercase;letter-spacing:.15em;">Eastwood doit recevoir</div>
    <div style="font-family:'DM Mono',monospace;font-size:18px;font-weight:500;color:{EW_G};">{fmt_eur(total_rec)}</div>
  </div>
</div>""", unsafe_allow_html=True)

    with tab_hist:
        try:
            df_hist = pd.read_sql("""
                SELECT date_op, description, payeur, beneficiaire,
                       total_ht, type_op, categorie, devise
                FROM transactions
                WHERE payeur IN ('Jules','Corentin','Alexis')
                   OR beneficiaire IN ('Jules','Corentin','Alexis')
                ORDER BY date_op DESC
            """, conn)
        except Exception:
            df_hist = pd.DataFrame()

        fh1,fh2 = st.columns(2)
        with fh1: f_m = st.selectbox("Membre", ["Tous"]+MEMBRES, key="bal_m")
        with fh2: f_t = st.selectbox("Type", ["Tous","Achat","Achat perso","Vente"], key="bal_t")

        if not df_hist.empty:
            df_f = df_hist.copy()
            if f_m != "Tous": df_f = df_f[(df_f["payeur"]==f_m)|(df_f["beneficiaire"]==f_m)]
            if f_t != "Tous": df_f = df_f[df_f["type_op"]==f_t]
            if df_f.empty:
                st.info("Aucun mouvement.")
            else:
                hk1,hk2 = st.columns(2)
                with hk1: st.metric("Nb mouvements", len(df_f))
                with hk2: st.metric("Volume total", fmt_eur(df_f["total_ht"].sum()))
                for _, row in df_f.iterrows():
                    payeur = str(row.get("payeur","") or "")
                    benef  = str(row.get("beneficiaire","") or "")
                    type_o = str(row.get("type_op","") or "")
                    montant = float(row.get("total_ht",0) or 0)
                    if payeur in MEMBRES and type_o in ("Achat","Achat perso"):
                        sens, color = f"↗ {payeur} a payé", EW_G
                    elif benef in MEMBRES:
                        sens, color = f"↘ {benef} a reçu", "#c1440e"
                    else:
                        sens, color = "→", EW_B
                    st.markdown(f"""
<div style="border:0.5px solid {EW_S};padding:10px 14px;margin:5px 0;background:#fff;
     display:flex;justify-content:space-between;align-items:center;">
  <div>
    <span style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_V};">{type_o}</span>
    <div style="font-weight:500;font-size:13px;">{str(row.get("description",""))[:60]}</div>
    <div style="font-size:11px;color:{EW_B};">{row.get("date_op","")} · {row.get("categorie","")}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'DM Mono',monospace;font-size:16px;">{fmt_eur(montant)}</div>
    <div style="font-size:9px;color:{color};">{sens}</div>
  </div>
</div>""", unsafe_allow_html=True)
                buf_b = io.BytesIO()
                df_f.to_csv(buf_b, index=False, encoding="utf-8-sig")
                st.download_button("⬇ Export CSV", buf_b.getvalue(), file_name="balance.csv",
                    mime="text/csv")
        else:
            st.info("Aucune transaction avec fondateurs.")

    with tab_info:
        st.markdown(f"""
<div style="background:{EW_C};border:0.5px solid {EW_S};padding:16px 20px;">
  <div style="font-size:13px;font-weight:500;margin-bottom:8px;">Comment enregistrer un mouvement</div>
  <div style="font-size:12px;color:{EW_B};line-height:2.2;">
    <strong>Avance pour Eastwood</strong><br>
    → Opérations → Nouvelle → Type : Achat · Payeur : le fondateur<br><br>
    <strong>Remboursement par Eastwood</strong><br>
    → Opérations → Nouvelle → Type : Achat · Bénéficiaire : le fondateur<br><br>
    <strong>Prise de stock / frais perso</strong><br>
    → Opérations → Nouvelle → Type : Achat perso · Bénéficiaire : le fondateur
  </div>
</div>""", unsafe_allow_html=True)
        soldes2, _ = compute_soldes(conn)
        if any(abs(s) > 0.01 for s in soldes2.values()):
            st.markdown(f'<div class="section-title">Rééquilibrages suggérés</div>', unsafe_allow_html=True)
            for membre, solde in soldes2.items():
                if abs(solde) < 0.01: continue
                color = EW_G if solde > 0 else "#c1440e"
                action = (f"Eastwood rembourse {membre} : {fmt_eur(abs(solde))}"
                          if solde > 0 else f"{membre} rembourse Eastwood : {fmt_eur(abs(solde))}")
                st.markdown(f'<div style="border-left:3px solid {color};padding:8px 14px;margin:5px 0;background:#fff;font-size:12px;"><strong>{action}</strong></div>', unsafe_allow_html=True)
        else:
            st.success("✓ Tous les soldes sont équilibrés.")

    conn.close()
