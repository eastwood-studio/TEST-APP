# ══════════════════════════════════════════════════════════════════════════════
# MODULE TVA — Déclarations CA3, export PDF, historique
# Conforme au formulaire Cerfa n°3310-CA3
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import date, datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ── Taux TVA France ────────────────────────────────────────────────────────────
TAUX_TVA = {
    "20%": 0.20,   # Taux normal
    "10%": 0.10,   # Taux intermédiaire (restauration, travaux...)
    "5.5%": 0.055, # Taux réduit (alimentation, livres...)
    "2.1%": 0.021, # Taux super-réduit (médicaments remboursables...)
}

TRIMESTRES = {
    1: ("Janvier", "Février", "Mars"),
    2: ("Avril", "Mai", "Juin"),
    3: ("Juillet", "Août", "Septembre"),
    4: ("Octobre", "Novembre", "Décembre"),
}


def init_tva_db(conn):
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS declarations_tva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        annee INTEGER,
        periode TEXT,
        trimestre INTEGER,
        date_depot TEXT,
        statut TEXT DEFAULT 'Brouillon',
        tva_collectee_20 REAL DEFAULT 0,
        tva_collectee_10 REAL DEFAULT 0,
        tva_collectee_55 REAL DEFAULT 0,
        tva_deductible_immob REAL DEFAULT 0,
        tva_deductible_biens REAL DEFAULT 0,
        tva_deductible_services REAL DEFAULT 0,
        tva_autoliquidee REAL DEFAULT 0,
        credit_tva_precedent REAL DEFAULT 0,
        tva_nette REAL DEFAULT 0,
        notes TEXT,
        pdf_data BLOB,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    conn.commit()


def compute_tva_trimestre(conn, annee, trimestre):
    """Calcule automatiquement la TVA d'un trimestre depuis les transactions."""
    mois_list = list(range((trimestre - 1) * 3 + 1, trimestre * 3 + 1))
    ph = ",".join("?" * len(mois_list))

    df = pd.read_sql(
        f"SELECT * FROM transactions WHERE annee=? AND mois IN ({ph})",
        conn, params=[annee] + mois_list
    )

    if df.empty:
        return {
            "tva_collectee_20": 0, "tva_collectee_10": 0, "tva_collectee_55": 0,
            "base_collectee_20": 0, "base_collectee_10": 0, "base_collectee_55": 0,
            "tva_deductible_biens": 0, "tva_deductible_services": 0,
            "tva_deductible_immob": 0, "tva_autoliquidee": 0,
            "base_deductible": 0, "base_autoliq": 0,
            "nb_ventes": 0, "nb_achats": 0,
        }

    # Collectée (20% uniquement pour Eastwood — ventes France)
    df_coll = df[df["type_tva"] == "Collectée"]
    tva_coll_20 = df_coll["tva"].sum()
    base_coll_20 = df_coll["total_ht"].sum()

    # Déductible — on sépare biens/services approximativement par catégorie
    df_ded = df[df["type_tva"] == "Déductible"]
    cats_biens = ["Matière première", "Composants", "Produit fini", "Packaging",
                  "Logiciel & outils"]
    cats_services = ["Confection / Production", "Communication", "Transport / Logistique",
                     "Stockage", "Légal / Administratif", "Autre frais", "Salaire"]
    cats_immob = []  # à compléter si investissements

    df_biens    = df_ded[df_ded["categorie"].isin(cats_biens)]
    df_services = df_ded[df_ded["categorie"].isin(cats_services)]
    df_immob    = df_ded[df_ded["categorie"].isin(cats_immob)]
    df_other    = df_ded[~df_ded["categorie"].isin(cats_biens + cats_services + cats_immob)]

    tva_ded_biens    = df_biens["tva"].sum() + df_other["tva"].sum()
    tva_ded_services = df_services["tva"].sum()
    tva_ded_immob    = df_immob["tva"].sum()
    base_ded = df_ded["total_ht"].sum()

    # Autoliquidée
    df_autoliq   = df[df["type_tva"] == "Autoliquidée"]
    tva_autoliq  = df_autoliq["tva"].sum()
    base_autoliq = df_autoliq["total_ht"].sum()

    return {
        "tva_collectee_20":      round(tva_coll_20, 2),
        "tva_collectee_10":      0,
        "tva_collectee_55":      0,
        "base_collectee_20":     round(base_coll_20, 2),
        "base_collectee_10":     0,
        "base_collectee_55":     0,
        "tva_deductible_biens":   round(tva_ded_biens, 2),
        "tva_deductible_services":round(tva_ded_services, 2),
        "tva_deductible_immob":   round(tva_ded_immob, 2),
        "tva_autoliquidee":       round(tva_autoliq, 2),
        "base_deductible":        round(base_ded, 2),
        "base_autoliq":           round(base_autoliq, 2),
        "nb_ventes": len(df[df["type_op"] == "Vente"]),
        "nb_achats": len(df[df["type_op"].isin(["Achat", "Achat perso"])]),
    }


def fmt(v, suffix="€"):
    if v is None or v == 0:
        return "0,00 " + suffix
    return f"{float(v):,.2f} {suffix}".replace(",", " ").replace(".", ",")


def fmt_eur(v):
    if v is None: return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


# ── GÉNÉRATION PDF CA3 ─────────────────────────────────────────────────────────
def generate_ca3_pdf(annee, trimestre, data, credit_precedent=0.0,
                     raison_sociale="EASTWOOD STUDIO",
                     siren="XXX XXX XXX",
                     adresse="Paris, France"):
    if not REPORTLAB_OK:
        return None

    buf = io.BytesIO()
    W, H = A4
    M = 12 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=M, rightMargin=M,
                            topMargin=M, bottomMargin=M)

    # Styles
    styles = getSampleStyleSheet()
    s_title  = ParagraphStyle("title",  fontName="Helvetica-Bold", fontSize=13,
                               spaceAfter=4, alignment=TA_CENTER)
    s_sub    = ParagraphStyle("sub",    fontName="Helvetica",      fontSize=8,
                               textColor=colors.HexColor("#888078"),
                               spaceAfter=2, alignment=TA_CENTER)
    s_head   = ParagraphStyle("head",   fontName="Helvetica-Bold", fontSize=9,
                               textColor=colors.HexColor("#1a1a1a"), spaceAfter=3)
    s_label  = ParagraphStyle("label",  fontName="Helvetica",      fontSize=8,
                               textColor=colors.HexColor("#444441"))
    s_note   = ParagraphStyle("note",   fontName="Helvetica",      fontSize=7,
                               textColor=colors.HexColor("#888078"),
                               spaceBefore=4)
    s_footer = ParagraphStyle("footer", fontName="Helvetica",      fontSize=6.5,
                               textColor=colors.HexColor("#aaa49a"), alignment=TA_CENTER)

    # Couleurs
    C_DARK  = colors.HexColor("#1a1a1a")
    C_MID   = colors.HexColor("#f0ece4")
    C_LINE  = colors.HexColor("#e0dbd2")
    C_BLUE  = colors.HexColor("#E6F1FB")
    C_GREEN = colors.HexColor("#EAF3DE")
    C_RED   = colors.HexColor("#FCEBEB")

    story = []

    # ── En-tête ────────────────────────────────────────────────────────────────
    story.append(Paragraph("DÉCLARATION DE TVA — FORMULAIRE CA3", s_title))
    mois_names = TRIMESTRES.get(trimestre, ("","",""))
    periode_str = f"T{trimestre} {annee} — {mois_names[0]} à {mois_names[2]}"
    story.append(Paragraph(f"Cerfa n°3310-CA3 · {periode_str}", s_sub))
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_DARK))
    story.append(Spacer(1, 3*mm))

    # ── Identité ────────────────────────────────────────────────────────────────
    id_data = [
        ["Raison sociale", raison_sociale, "SIREN", siren],
        ["Adresse",        adresse,        "Période", periode_str],
        ["Date de dépôt",  date.today().strftime("%d/%m/%Y"),
         "Régime", "Réel normal — mensuel/trimestriel"],
    ]
    id_tbl = Table(id_data, colWidths=[(W-2*M)*0.18, (W-2*M)*0.38,
                                        (W-2*M)*0.16, (W-2*M)*0.28])
    id_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",  (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 8),
        ("TEXTCOLOR", (0,0), (0,-1), colors.HexColor("#888078")),
        ("TEXTCOLOR", (2,0), (2,-1), colors.HexColor("#888078")),
        ("BACKGROUND",(0,0), (-1,-1), C_MID),
        ("GRID",      (0,0), (-1,-1), 0.3, C_LINE),
        ("TOPPADDING",(0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(id_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Section A : TVA collectée ───────────────────────────────────────────────
    story.append(Paragraph("A — OPÉRATIONS IMPOSABLES (TVA COLLECTÉE)", s_head))
    story.append(Spacer(1, 1*mm))

    tva_coll_tot = (data.get("tva_collectee_20", 0) +
                    data.get("tva_collectee_10", 0) +
                    data.get("tva_collectee_55", 0))
    base_coll_tot = (data.get("base_collectee_20", 0) +
                     data.get("base_collectee_10", 0) +
                     data.get("base_collectee_55", 0))

    coll_data = [
        ["Ligne", "Opérations", "Base HT", "Taux", "TVA due"],
        ["01", "Ventes / prestations taux normal 20%",
         fmt(data.get("base_collectee_20", 0)), "20%",
         fmt(data.get("tva_collectee_20", 0))],
        ["02", "Ventes taux intermédiaire 10%",
         fmt(data.get("base_collectee_10", 0)), "10%",
         fmt(data.get("tva_collectee_10", 0))],
        ["03", "Ventes taux réduit 5,5%",
         fmt(data.get("base_collectee_55", 0)), "5,5%",
         fmt(data.get("tva_collectee_55", 0))],
        ["", "TOTAL TVA COLLECTÉE (A)",
         fmt(base_coll_tot), "", fmt(tva_coll_tot)],
    ]

    coll_tbl = Table(coll_data,
                     colWidths=[(W-2*M)*w for w in [0.08, 0.44, 0.18, 0.10, 0.20]])
    coll_tbl.setStyle(TableStyle([
        # En-tête
        ("BACKGROUND",   (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 8),
        ("ALIGN",        (2,0), (-1,-1), "RIGHT"),
        ("ALIGN",        (0,0), (1,-1),  "LEFT"),
        ("GRID",         (0,0), (-1,-1), 0.3, C_LINE),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("LEFTPADDING",  (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        # Total
        ("BACKGROUND",   (0,-1), (-1,-1), C_BLUE),
        ("FONTNAME",     (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(coll_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Section B : TVA déductible ─────────────────────────────────────────────
    story.append(Paragraph("B — TVA DÉDUCTIBLE", s_head))
    story.append(Spacer(1, 1*mm))

    tva_ded_tot = (data.get("tva_deductible_immob", 0) +
                   data.get("tva_deductible_biens", 0) +
                   data.get("tva_deductible_services", 0))

    ded_data = [
        ["Ligne", "Nature", "Montant TVA déductible"],
        ["19", "Immobilisations",
         fmt(data.get("tva_deductible_immob", 0))],
        ["20", "Biens et services (achats matières, packaging, logiciels...)",
         fmt(data.get("tva_deductible_biens", 0))],
        ["21", "Services extérieurs (confection, communication, transport...)",
         fmt(data.get("tva_deductible_services", 0))],
        ["22", "TVA autoliquidée (achats intracommunautaires / hors UE)",
         fmt(data.get("tva_autoliquidee", 0))],
        ["", "TOTAL TVA DÉDUCTIBLE (B)",
         fmt(tva_ded_tot + data.get("tva_autoliquidee", 0))],
    ]

    ded_tbl = Table(ded_data,
                    colWidths=[(W-2*M)*w for w in [0.08, 0.64, 0.28]])
    ded_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 8),
        ("ALIGN",        (2,0), (-1,-1), "RIGHT"),
        ("ALIGN",        (0,0), (1,-1),  "LEFT"),
        ("GRID",         (0,0), (-1,-1), 0.3, C_LINE),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("LEFTPADDING",  (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("BACKGROUND",   (0,-1), (-1,-1), C_GREEN),
        ("FONTNAME",     (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(ded_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Section C : Récapitulatif & solde ─────────────────────────────────────
    story.append(Paragraph("C — RÉCAPITULATIF ET SOLDE À PAYER", s_head))
    story.append(Spacer(1, 1*mm))

    tva_ded_total_final = tva_ded_tot + data.get("tva_autoliquidee", 0)
    tva_nette = tva_coll_tot - tva_ded_total_final - float(credit_precedent)
    tva_due   = max(tva_nette, 0)
    credit     = max(-tva_nette, 0)

    recap_data = [
        ["", "Libellé", "Montant"],
        ["A", "TVA collectée",         fmt(tva_coll_tot)],
        ["B", "TVA déductible totale", fmt(tva_ded_total_final)],
        ["C", "Crédit TVA période précédente", fmt(credit_precedent)],
        ["D", "TVA nette (A − B − C)", fmt(tva_nette)],
        ["→", "TVA À PAYER" if tva_due > 0 else "CRÉDIT DE TVA",
         fmt(tva_due if tva_due > 0 else credit)],
    ]
    recap_tbl = Table(recap_data,
                      colWidths=[(W-2*M)*w for w in [0.08, 0.64, 0.28]])
    recap_style = [
        ("BACKGROUND",    (0,0), (-1,0), C_DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ALIGN",         (2,0), (-1,-1), "RIGHT"),
        ("ALIGN",         (0,0), (1,-1),  "LEFT"),
        ("GRID",          (0,0), (-1,-1), 0.3, C_LINE),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("FONTNAME",      (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,-1), (-1,-1), 9),
    ]
    # Couleur solde
    if tva_due > 0:
        recap_style.append(("BACKGROUND", (0,-1), (-1,-1), C_RED))
    else:
        recap_style.append(("BACKGROUND", (0,-1), (-1,-1), C_GREEN))

    recap_tbl.setStyle(TableStyle(recap_style))
    story.append(recap_tbl)
    story.append(Spacer(1, 6*mm))

    # ── Détail opérations ──────────────────────────────────────────────────────
    story.append(Paragraph("D — DÉTAIL DES OPÉRATIONS TVA DU TRIMESTRE", s_head))
    story.append(Spacer(1, 1*mm))

    detail_rows = [["Date", "Description", "HT", "Type TVA", "TVA", "Devise"]]
    mois_list = list(range((trimestre - 1) * 3 + 1, trimestre * 3 + 1))
    ph = ",".join("?" * len(mois_list))
    df_det = pd.read_sql(
        f"""SELECT date_op, description, total_ht, type_tva, tva, devise
            FROM transactions
            WHERE annee=? AND mois IN ({ph}) AND type_tva != 'Aucun'
            ORDER BY date_op""",
        pd.read_sql.__self__ if hasattr(pd.read_sql, '__self__') else None,
        params=[annee] + mois_list
    ) if False else None

    # On passe par une connexion directe
    # (df_det calculé dans page_tva et passé ici via argument)
    story.append(Paragraph(
        "Voir tableau détaillé dans l'application ou l'export Excel.",
        s_note
    ))
    story.append(Spacer(1, 4*mm))

    # ── Résumé pour l'expert-comptable ────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    story.append(Spacer(1, 3*mm))
    ec_data = [
        ["Récapitulatif pour l'expert-comptable", ""],
        ["Chiffre d'affaires HT période", fmt(base_coll_tot)],
        ["Base HT achats déductibles",   fmt(data.get("base_deductible", 0))],
        ["Base HT opérations autoliquidées", fmt(data.get("base_autoliq", 0))],
        ["Nb ventes",  str(data.get("nb_ventes", 0))],
        ["Nb achats",  str(data.get("nb_achats", 0))],
    ]
    ec_tbl = Table(ec_data, colWidths=[(W-2*M)*0.65, (W-2*M)*0.35])
    ec_tbl.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("BACKGROUND",   (0,0), (-1,0), C_MID),
        ("SPAN",         (0,0), (-1,0)),
        ("FONTSIZE",     (0,0), (-1,-1), 8),
        ("ALIGN",        (1,1), (-1,-1), "RIGHT"),
        ("GRID",         (0,0), (-1,-1), 0.3, C_LINE),
        ("TOPPADDING",   (0,0), (-1,-1), 3),
        ("BOTTOMPADDING",(0,0), (-1,-1), 3),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
    ]))
    story.append(ec_tbl)
    story.append(Spacer(1, 6*mm))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.3,
                             color=colors.HexColor("#e0dbd2")))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"EASTWOOD STUDIO · {siren} · Paris · Généré le {date.today().strftime('%d/%m/%Y')} via application interne · "
        f"Document non officiel — à soumettre sur impots.gouv.fr",
        s_footer
    ))

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE TVA PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_tva(can_fn, DB_PATH, sel_year):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_tva_db(conn)

    st.markdown(f"### TVA & Déclarations · {sel_year}")
    st.markdown("""
<div style="background:#f7f5f0;border:1px solid #e0dbd2;border-left:3px solid #534AB7;
     border-radius:2px;padding:12px 18px;margin-bottom:16px;font-size:12px;color:#1a1a1a;">
<strong>Accès restreint — Jules uniquement.</strong>
Cette page génère les éléments préparatoires à votre déclaration CA3 sur impots.gouv.fr.
Faites valider par votre expert-comptable avant tout dépôt officiel.
</div>""", unsafe_allow_html=True)

    tab_synth, tab_decl, tab_hist = st.tabs([
        "📊 Synthèse annuelle",
        "📄 Préparer une déclaration",
        "📁 Historique déclarations",
    ])

    # ── SYNTHÈSE ANNUELLE ──────────────────────────────────────────────────────
    with tab_synth:
        # KPIs globaux de l'année
        df_an = pd.read_sql(
            "SELECT * FROM transactions WHERE annee=?", conn, params=[sel_year])

        if df_an.empty:
            st.info("Aucune transaction enregistrée pour cette année.")
        else:
            tva_c_an = df_an[df_an["type_tva"] == "Collectée"]["tva"].sum()
            tva_d_an = df_an[df_an["type_tva"] == "Déductible"]["tva"].sum()
            tva_a_an = df_an[df_an["type_tva"] == "Autoliquidée"]["tva"].sum()
            ca_an    = df_an[df_an["type_op"] == "Vente"]["total_ht"].sum()
            tva_nette_an = tva_c_an - tva_d_an

            c1,c2,c3,c4,c5 = st.columns(5)
            with c1: st.metric("CA HT année", fmt_eur(ca_an))
            with c2: st.metric("TVA collectée", fmt_eur(tva_c_an))
            with c3: st.metric("TVA déductible", fmt_eur(tva_d_an))
            with c4: st.metric("TVA autoliquidée", fmt_eur(tva_a_an))
            with c5:
                st.metric("Solde net",
                          fmt_eur(abs(tva_nette_an)),
                          delta="À payer" if tva_nette_an > 0 else "Crédit TVA")

            # Tableau par trimestre
            st.markdown('<div class="section-title">Détail par trimestre</div>',
                        unsafe_allow_html=True)

            rows = []
            for q in [1, 2, 3, 4]:
                d = compute_tva_trimestre(conn, sel_year, q)
                mois = TRIMESTRES[q]
                tva_c  = d["tva_collectee_20"]
                tva_d  = d["tva_deductible_biens"] + d["tva_deductible_services"] + d["tva_deductible_immob"]
                tva_a  = d["tva_autoliquidee"]
                solde  = tva_c - tva_d - tva_a
                rows.append({
                    "Trimestre": f"T{q} — {mois[0]}→{mois[2]}",
                    "CA HT":          fmt_eur(d["base_collectee_20"]),
                    "TVA collectée":  fmt_eur(tva_c),
                    "TVA déductible": fmt_eur(tva_d),
                    "Autoliquidée":   fmt_eur(tva_a),
                    "Solde":          fmt_eur(solde),
                    "Statut":         "✅ À payer" if solde > 0 else "↩ Crédit",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Détail opérations TVA
            st.markdown('<div class="section-title">Détail opérations TVA</div>',
                        unsafe_allow_html=True)

            c_f1, c_f2, c_f3 = st.columns(3)
            with c_f1:
                f_q = st.selectbox("Trimestre", ["Tous","T1","T2","T3","T4"])
            with c_f2:
                f_tva_type = st.selectbox("Type TVA",
                                          ["Tous","Collectée","Déductible","Autoliquidée"])
            with c_f3:
                f_cat = st.selectbox("Catégorie",
                                     ["Toutes"] + df_an["categorie"].dropna().unique().tolist())

            df_det = df_an[df_an["type_tva"] != "Aucun"].copy()
            if f_q != "Tous":
                qnum = int(f_q[1])
                mois_q = list(range((qnum-1)*3+1, qnum*3+1))
                df_det = df_det[df_det["mois"].isin(mois_q)]
            if f_tva_type != "Tous":
                df_det = df_det[df_det["type_tva"] == f_tva_type]
            if f_cat != "Toutes":
                df_det = df_det[df_det["categorie"] == f_cat]

            cols_show = ["date_op","ref_produit","description","categorie",
                         "type_op","total_ht","type_tva","tva","devise"]
            st.dataframe(
                df_det[cols_show].rename(columns={
                    "date_op":"Date","ref_produit":"SKU","description":"Description",
                    "categorie":"Catégorie","type_op":"Type","total_ht":"Base HT",
                    "type_tva":"Type TVA","tva":"TVA","devise":"Devise"
                }),
                use_container_width=True, hide_index=True
            )

            # Export Excel
            buf_xl = io.BytesIO()
            with pd.ExcelWriter(buf_xl, engine="openpyxl") as writer:
                df_det[cols_show].rename(columns={
                    "date_op":"Date","ref_produit":"SKU","description":"Description",
                    "categorie":"Catégorie","type_op":"Type","total_ht":"Base HT",
                    "type_tva":"Type TVA","tva":"TVA","devise":"Devise"
                }).to_excel(writer, sheet_name="TVA détail", index=False)

                # Onglet synthèse
                pd.DataFrame(rows).to_excel(writer, sheet_name="Synthèse trimestrielle", index=False)

            st.download_button(
                "⬇ Export Excel complet TVA",
                buf_xl.getvalue(),
                file_name=f"TVA_eastwood_{sel_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Règles TVA
            st.markdown("""
<div class="alert-box">
<strong>Règles TVA intégrées (France) :</strong><br>
• <strong>Collectée 20%</strong> — Ventes à des clients français (ligne 01 CA3)<br>
• <strong>Déductible</strong> — Achats auprès de fournisseurs français assujettis (lignes 19-21)<br>
• <strong>Autoliquidée</strong> — Acquisitions intracommunautaires & achats hors UE — vous collectez et déduisez simultanément (ligne 22)<br>
• <strong>Aucun</strong> — Hors champ TVA (frais bancaires, INPI, charges salariales)<br><br>
<strong>Ventes export (hors UE) :</strong> exonérées de TVA française — vérifier avec votre comptable si applicable.
</div>""", unsafe_allow_html=True)

    # ── PRÉPARER UNE DÉCLARATION ───────────────────────────────────────────────
    with tab_decl:
        st.markdown('<div class="section-title">Générer la déclaration CA3</div>',
                    unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            sel_q = st.selectbox("Trimestre", [1, 2, 3, 4],
                                 format_func=lambda q: f"T{q} — {TRIMESTRES[q][0]} à {TRIMESTRES[q][2]}")
        with c2:
            credit_prec = st.number_input("Crédit TVA période précédente (€)",
                                          min_value=0.0, value=0.0, step=0.01)
        with c3:
            siren_input = st.text_input("N° SIREN", value="XXX XXX XXX",
                                        placeholder="123 456 789")

        # Calcul automatique
        data = compute_tva_trimestre(conn, sel_year, sel_q)
        tva_coll  = data["tva_collectee_20"]
        tva_ded   = (data["tva_deductible_biens"] +
                     data["tva_deductible_services"] +
                     data["tva_deductible_immob"])
        tva_autoliq = data["tva_autoliquidee"]
        tva_nette = tva_coll - tva_ded - tva_autoliq - credit_prec
        tva_due   = max(tva_nette, 0)
        credit_res = max(-tva_nette, 0)

        mois_names = TRIMESTRES[sel_q]
        st.markdown(f"""
<div style="background:#f7f5f0;border:1px solid #e0dbd2;border-radius:4px;
     padding:20px 24px;margin:12px 0;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;
              letter-spacing:.15em;text-transform:uppercase;margin-bottom:12px;">
    Aperçu CA3 · T{sel_q} {sel_year} · {mois_names[0]} → {mois_names[2]}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
    <div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:#888078;text-transform:uppercase;">TVA collectée (A)</div>
      <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:#1a1a1a;">{fmt_eur(tva_coll)}</div>
      <div style="font-size:11px;color:#aaa49a;">Base HT : {fmt_eur(data["base_collectee_20"])}</div>
    </div>
    <div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:#888078;text-transform:uppercase;">TVA déductible (B)</div>
      <div style="font-family:'DM Mono',monospace;font-size:20px;font-weight:500;color:#1a1a1a;">{fmt_eur(tva_ded + tva_autoliq)}</div>
      <div style="font-size:11px;color:#aaa49a;">dont autoliquidée : {fmt_eur(tva_autoliq)}</div>
    </div>
    <div>
      <div style="font-family:'DM Mono',monospace;font-size:9px;color:#888078;text-transform:uppercase;">{'TVA à payer' if tva_due > 0 else 'Crédit TVA'}</div>
      <div style="font-family:'DM Mono',monospace;font-size:24px;font-weight:500;
                  color:{'#c1440e' if tva_due > 0 else '#2d6a4f'};">
        {fmt_eur(tva_due if tva_due > 0 else credit_res)}
      </div>
      {'<div style="font-size:11px;color:#c1440e;">À payer avant le 20 du mois suivant</div>' if tva_due > 0 else '<div style="font-size:11px;color:#2d6a4f;">Reportable sur la prochaine déclaration</div>'}
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        # Détail lignes
        with st.expander("Voir le détail des lignes CA3"):
            detail_lines = [
                ("01", "Ventes taux normal 20%",
                 fmt_eur(data["base_collectee_20"]), "20%",
                 fmt_eur(data["tva_collectee_20"])),
                ("02", "Ventes taux intermédiaire 10%", "—", "10%", "—"),
                ("03", "Ventes taux réduit 5,5%", "—", "5,5%", "—"),
                ("19", "TVA déductible — immobilisations",
                 "—", "—", fmt_eur(data["tva_deductible_immob"])),
                ("20", "TVA déductible — biens & services",
                 fmt_eur(data["base_deductible"]), "—",
                 fmt_eur(data["tva_deductible_biens"])),
                ("21", "TVA déductible — services extérieurs",
                 "—", "—", fmt_eur(data["tva_deductible_services"])),
                ("22", "TVA autoliquidée",
                 fmt_eur(data["base_autoliq"]), "—",
                 fmt_eur(data["tva_autoliquidee"])),
            ]
            df_lines = pd.DataFrame(detail_lines,
                                    columns=["Ligne","Libellé","Base HT","Taux","TVA"])
            st.dataframe(df_lines, use_container_width=True, hide_index=True)

        # Boutons de génération
        st.markdown("---")
        col_b1, col_b2 = st.columns(2)

        with col_b1:
            if st.button("📄 Générer PDF CA3"):
                if not REPORTLAB_OK:
                    st.error("reportlab non installé.")
                else:
                    with st.spinner("Génération PDF..."):
                        pdf_bytes = generate_ca3_pdf(
                            annee=sel_year,
                            trimestre=sel_q,
                            data=data,
                            credit_precedent=credit_prec,
                            siren=siren_input,
                        )
                    if pdf_bytes:
                        fname = f"CA3_T{sel_q}_{sel_year}_Eastwood.pdf"
                        st.download_button(
                            "⬇ Télécharger le PDF CA3",
                            pdf_bytes,
                            file_name=fname,
                            mime="application/pdf"
                        )

                        # Sauvegarder en historique
                        periode_label = f"T{sel_q} {sel_year}"
                        conn.execute("""INSERT OR REPLACE INTO declarations_tva
                            (annee,periode,trimestre,date_depot,statut,
                             tva_collectee_20,tva_deductible_biens,tva_deductible_services,
                             tva_autoliquidee,credit_tva_precedent,tva_nette,pdf_data)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (sel_year, periode_label, sel_q,
                             date.today().isoformat(), "Brouillon",
                             data["tva_collectee_20"],
                             data["tva_deductible_biens"],
                             data["tva_deductible_services"],
                             data["tva_autoliquidee"],
                             credit_prec, tva_nette, pdf_bytes))
                        conn.commit()
                        st.success("✓ PDF généré et sauvegardé dans l'historique.")

        with col_b2:
            st.markdown("""
<a href="https://cfspro-idp.impots.gouv.fr/oauth2/authorize" target="_blank"
   style="display:inline-block;font-family:'DM Mono',monospace;font-size:11px;
          background:#1a1a1a;color:#f0ece4;padding:8px 18px;border-radius:2px;
          text-decoration:none;letter-spacing:.1em;text-transform:uppercase;">
  ↗ Déclarer sur impots.gouv.fr
</a>""", unsafe_allow_html=True)
            st.caption("Se connecter avec votre espace professionnel → Déclarer → CA3")

    # ── HISTORIQUE ─────────────────────────────────────────────────────────────
    with tab_hist:
        st.markdown('<div class="section-title">Historique des déclarations</div>',
                    unsafe_allow_html=True)

        df_hist = pd.read_sql(
            "SELECT * FROM declarations_tva ORDER BY annee DESC, trimestre DESC", conn)

        if df_hist.empty:
            st.info("Aucune déclaration générée pour l'instant.")
        else:
            for _, row in df_hist.iterrows():
                stat_c = {"Déposée":"#2d6a4f","Brouillon":"#c9800a",
                          "En retard":"#c1440e"}.get(row.get("statut",""), "#888")
                col_i, col_btn = st.columns([4, 1])
                with col_i:
                    st.markdown(f"""
<div style="border-left:3px solid {stat_c};padding:10px 16px;margin:6px 0;
     background:#f7f5f0;border-radius:0 4px 4px 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div>
      <span style="font-family:'DM Mono',monospace;font-size:12px;font-weight:500;
                   color:#1a1a1a;">{row['periode']}</span>
      <span style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;
                   margin-left:10px;">TVA nette : {fmt_eur(row['tva_nette'])}</span>
    </div>
    <div style="display:flex;align-items:center;gap:12px;">
      <span style="font-family:'DM Mono',monospace;font-size:9px;
                   color:{stat_c};text-transform:uppercase;">{row['statut']}</span>
      <span style="font-size:11px;color:#aaa49a;">{row.get('date_depot','')}</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

                with col_btn:
                    # Télécharger le PDF si disponible
                    if row.get("pdf_data") is not None:
                        st.download_button(
                            "⬇ PDF",
                            data=bytes(row["pdf_data"]),
                            file_name=f"CA3_{row['periode'].replace(' ','_')}_Eastwood.pdf",
                            mime="application/pdf",
                            key=f"dl_decl_{row['id']}"
                        )

                    # Changer statut
                    if can_fn("tva_read"):
                        new_stat = st.selectbox(
                            "", ["Brouillon","Déposée","En retard"],
                            index=["Brouillon","Déposée","En retard"].index(row["statut"])
                                  if row.get("statut") in ["Brouillon","Déposée","En retard"] else 0,
                            key=f"decl_stat_{row['id']}", label_visibility="collapsed")
                        if st.button("✓", key=f"decl_upd_{row['id']}"):
                            conn.execute("UPDATE declarations_tva SET statut=? WHERE id=?",
                                         (new_stat, row["id"]))
                            conn.commit(); st.rerun()

    conn.close()
