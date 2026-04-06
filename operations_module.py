# ══════════════════════════════════════════════════════════════════════════════
# MODULE OPÉRATIONS (ex-Transactions)
# Jules uniquement pour write · OCR via API Claude · SKU dropdown · filtres date
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
import base64
import json
import os
from datetime import date, datetime, timedelta

# ── Constantes ─────────────────────────────────────────────────────────────────
CATEGORIES = [
    "Matière première", "Composants", "Confection / Production", "Communication",
    "Transport / Logistique", "Stockage", "Salaire", "Autre frais",
    "Légal / Administratif", "Produit fini", "Facture", "Logiciel & outils", "Packaging",
]
TYPES_OP   = ["Achat", "Vente", "Utilisation", "Achat perso"]
TYPES_TVA  = ["Collectée", "Déductible", "Autoliquidée", "Aucun"]
PAYEURS    = ["Eastwood Studio", "Jules", "Corentin", "Alexis"]
BENEFICIAIRES = ["Eastwood Studio", "Jules", "Corentin", "Alexis"]
DEVISES    = ["EUR", "JPY", "USD", "GBP", "CNY", "CHF", "KRW"]
DEVISES_SYM = {"EUR":"€","JPY":"¥","USD":"$","GBP":"£","CNY":"¥","CHF":"Fr","KRW":"₩"}
UNITES     = ["Euros", "Article", "Mètre", "Pièces", "Kg", "Heure", "Lot", "/"]

TVA_RULES = {
    "Vente":       {"default": "Collectée"},
    "Achat":       {"default": "Déductible", "Légal / Administratif": "Aucun",
                    "Autre frais": "Aucun", "Stockage": "Aucun"},
    "Utilisation": {"default": "Aucun"},
    "Achat perso": {"default": "Aucun"},
}

PERIODES_FILTRE = [
    "Toutes", "Cette semaine", "Ce mois", "3 derniers mois",
    "6 derniers mois", "Cette année", "Personnalisée",
]


def suggest_tva(type_op, categorie, devise="EUR"):
    if devise not in ("EUR", ""):
        return "Autoliquidée"
    rules = TVA_RULES.get(type_op, {})
    return rules.get(categorie, rules.get("default", "Aucun"))


def fmt_eur(v):
    if v is None: return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


def get_sku_list(conn):
    """Récupère tous les SKUs disponibles dans la table produits."""
    try:
        df = pd.read_sql(
            "SELECT ref, nom, collection FROM products ORDER BY collection, nom", conn)
        if df.empty:
            return []
        return [f"{r['ref']} — {r['nom']}" for _, r in df.iterrows()]
    except Exception:
        return []


def get_date_filter(periode, date_debut_custom=None, date_fin_custom=None):
    """Retourne (date_debut, date_fin) selon la période choisie."""
    today = date.today()
    if periode == "Cette semaine":
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), today.isoformat()
    elif periode == "Ce mois":
        return today.replace(day=1).isoformat(), today.isoformat()
    elif periode == "3 derniers mois":
        return (today - timedelta(days=90)).isoformat(), today.isoformat()
    elif periode == "6 derniers mois":
        return (today - timedelta(days=180)).isoformat(), today.isoformat()
    elif periode == "Cette année":
        return today.replace(month=1, day=1).isoformat(), today.isoformat()
    elif periode == "Personnalisée" and date_debut_custom and date_fin_custom:
        return date_debut_custom.isoformat(), date_fin_custom.isoformat()
    return None, None


def load_operations(conn, periode="Toutes", date_debut=None, date_fin=None,
                    type_op=None, categorie=None, devise=None, tva_type=None,
                    search=None):
    q = "SELECT * FROM transactions WHERE 1=1"
    p = []
    if date_debut:
        q += " AND date_op >= ?"; p.append(date_debut)
    if date_fin:
        q += " AND date_op <= ?"; p.append(date_fin)
    if type_op:    q += " AND type_op=?";   p.append(type_op)
    if categorie:  q += " AND categorie=?"; p.append(categorie)
    if devise:     q += " AND devise=?";    p.append(devise)
    if tva_type:   q += " AND type_tva=?";  p.append(tva_type)
    df = pd.read_sql(q + " ORDER BY date_op DESC", conn, params=p)
    if search and not df.empty:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
    return df


# ── OCR via API Claude ─────────────────────────────────────────────────────────
def ocr_facture_claude(image_bytes: bytes, filename: str) -> dict:
    """
    Envoie l'image de la facture à Claude claude-sonnet-4-20250514
    et retourne les champs extraits (date, montant, fournisseur, description, catégorie).
    Nécessite ANTHROPIC_API_KEY dans st.secrets ou les variables d'environnement.
    """
    try:
        import anthropic

        api_key = (
            st.secrets.get("ANTHROPIC_API_KEY", None)
            or os.environ.get("ANTHROPIC_API_KEY", None)
        )
        if not api_key:
            return {"error": "Clé API Anthropic manquante. Ajoutez ANTHROPIC_API_KEY dans les secrets Streamlit."}

        client = anthropic.Anthropic(api_key=api_key)

        # Détecter le type MIME
        ext = filename.lower().split(".")[-1] if filename else "jpg"
        media_types = {
            "pdf":  "application/pdf",
            "png":  "image/png",
            "jpg":  "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }
        media_type = media_types.get(ext, "image/jpeg")

        b64_data = base64.standard_b64encode(image_bytes).decode("utf-8")

        # Pour les PDF, on utilise le type document
        if media_type == "application/pdf":
            content_block = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": b64_data,
                }
            }
        else:
            content_block = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": b64_data,
                }
            }

        prompt = """Analyse cette facture et extrais les informations suivantes en JSON strict.
Réponds UNIQUEMENT avec du JSON valide, sans texte avant ni après, sans markdown.

Format requis :
{
  "date": "YYYY-MM-DD ou null si non trouvé",
  "fournisseur": "nom du fournisseur/émetteur",
  "description": "description courte de l'achat (max 80 chars)",
  "total_ht": "montant HT en chiffres uniquement (ex: 150.00) ou null",
  "total_ttc": "montant TTC en chiffres uniquement ou null",
  "tva": "montant TVA en chiffres uniquement ou null",
  "devise": "EUR ou JPY ou USD ou GBP selon la devise de la facture",
  "numero_facture": "numéro de facture si présent ou null",
  "categorie_suggeree": "une de ces catégories exactes : Matière première, Composants, Confection / Production, Communication, Transport / Logistique, Stockage, Salaire, Autre frais, Légal / Administratif, Produit fini, Facture, Logiciel & outils, Packaging",
  "type_op": "Achat ou Vente selon le type de document"
}"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[
                {
                    "role": "user",
                    "content": [content_block, {"type": "text", "text": prompt}]
                }
            ]
        )

        raw = response.content[0].text.strip()
        # Nettoyage au cas où il y aurait des backticks
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    except ImportError:
        return {"error": "Package 'anthropic' non installé. Ajoutez-le dans requirements.txt."}
    except json.JSONDecodeError as e:
        return {"error": f"Réponse OCR non parseable : {e}"}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# PAGE OPÉRATIONS PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_operations(can_fn, DB_PATH, fmt_eur_fn=None):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    if fmt_eur_fn is None:
        fmt_eur_fn = fmt_eur

    st.markdown("### Opérations")

    # Tabs selon droits
    _tabs = ["📋 Historique", "📁 Factures"]
    if can_fn("finance_write"):
        _tabs += ["➕ Nouvelle opération", "🔍 OCR — Scan facture"]
    tab_objs = st.tabs(_tabs)
    idx = 0
    tab_hist = tab_objs[idx]; idx += 1
    tab_fac  = tab_objs[idx]; idx += 1
    tab_new  = tab_objs[idx] if can_fn("finance_write") else None
    if can_fn("finance_write"): idx += 1
    tab_ocr  = tab_objs[idx] if can_fn("finance_write") else None

    # ── HISTORIQUE ─────────────────────────────────────────────────────────────
    with tab_hist:
        # Filtres
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_periode = st.selectbox("Période", PERIODES_FILTRE, key="ops_periode")
        with fc2:
            f_type = st.selectbox("Type", ["Tous"] + TYPES_OP, key="ops_type")
        with fc3:
            f_cat  = st.selectbox("Catégorie", ["Toutes"] + CATEGORIES, key="ops_cat")

        fc4, fc5, fc6 = st.columns(3)
        with fc4:
            f_dev  = st.selectbox("Devise", ["Toutes"] + DEVISES, key="ops_dev")
        with fc5:
            f_tva  = st.selectbox("TVA", ["Tous"] + TYPES_TVA, key="ops_tva")
        with fc6:
            f_srch = st.text_input("Recherche", placeholder="fournisseur, description, SKU...", key="ops_srch")

        # Dates personnalisées
        d_debut_custom = d_fin_custom = None
        if f_periode == "Personnalisée":
            pc1, pc2 = st.columns(2)
            with pc1: d_debut_custom = st.date_input("Du", value=date.today().replace(day=1), key="ops_d1")
            with pc2: d_fin_custom   = st.date_input("Au", value=date.today(), key="ops_d2")

        d_debut, d_fin = get_date_filter(f_periode, d_debut_custom, d_fin_custom)

        df_ops = load_operations(
            conn,
            date_debut=d_debut, date_fin=d_fin,
            type_op=None if f_type == "Tous" else f_type,
            categorie=None if f_cat == "Toutes" else f_cat,
            devise=None if f_dev == "Toutes" else f_dev,
            tva_type=None if f_tva == "Tous" else f_tva,
            search=f_srch or None,
        )

        if df_ops.empty:
            st.info("Aucune opération sur cette période.")
        else:
            # KPIs rapides
            k1, k2, k3, k4 = st.columns(4)
            ventes_f = df_ops[df_ops["type_op"]=="Vente"]["total_ht"].sum()
            achats_f = df_ops[df_ops["type_op"].isin(["Achat","Achat perso"])]["total_ht"].sum()
            with k1: st.metric("CA HT", fmt_eur_fn(ventes_f))
            with k2: st.metric("Charges HT", fmt_eur_fn(achats_f))
            with k3: st.metric("TVA", fmt_eur_fn(df_ops["tva"].sum()))
            with k4: st.metric("Nb opérations", len(df_ops))

            # Tableau
            cols_show = ["date_op","ref_produit","info_process","description",
                         "categorie","type_op","quantite","unite",
                         "total_ht","devise","type_tva","tva","payeur","beneficiaire"]
            cols_rename = {
                "date_op":"Date","ref_produit":"SKU","info_process":"Article",
                "description":"Description","categorie":"Catégorie","type_op":"Type",
                "quantite":"Qté","unite":"Unité","total_ht":"Total HT","devise":"Devise",
                "type_tva":"TVA","tva":"Mnt TVA","payeur":"Payeur","beneficiaire":"Bénéficiaire"
            }
            existing = [c for c in cols_show if c in df_ops.columns]
            st.dataframe(
                df_ops[existing].rename(columns=cols_rename),
                use_container_width=True, hide_index=True
            )

            # Export
            buf = io.BytesIO()
            df_ops.drop(columns=["facture_data"], errors="ignore").to_excel(
                buf, index=False, engine="openpyxl")
            st.download_button(
                "⬇ Export Excel",
                buf.getvalue(),
                file_name=f"operations_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ── FACTURES ───────────────────────────────────────────────────────────────
    with tab_fac:
        st.markdown('<div class="section-title">Espace factures</div>', unsafe_allow_html=True)

        df_fac = pd.read_sql("""
            SELECT id, date_op, description, total_ht, type_op,
                   beneficiaire, facture_nom, facture_data
            FROM transactions WHERE facture_data IS NOT NULL
            ORDER BY date_op DESC""", conn)

        if df_fac.empty:
            st.info("Aucune facture enregistrée.")
        else:
            ff1, ff2, ff3 = st.columns(3)
            with ff1: ff_type = st.selectbox("Type", ["Tous","Vente","Achat"], key="fac_type")
            with ff2: ff_srch = st.text_input("Rechercher", placeholder="fournisseur, description...", key="fac_srch")
            with ff3:
                ff_periode = st.selectbox("Période", PERIODES_FILTRE, key="fac_per")

            df_ff = df_fac.copy()
            if ff_type != "Tous": df_ff = df_ff[df_ff["type_op"]==ff_type]
            if ff_srch:
                df_ff = df_ff[df_ff.apply(lambda r: ff_srch.lower() in str(r).lower(), axis=1)]

            d_ff_debut, d_ff_fin = get_date_filter(ff_periode)
            if d_ff_debut:
                df_ff = df_ff[df_ff["date_op"] >= d_ff_debut]
            if d_ff_fin:
                df_ff = df_ff[df_ff["date_op"] <= d_ff_fin]

            for _, row in df_ff.iterrows():
                ci, cd = st.columns([4, 1])
                with ci:
                    badge_c = "#d4edda" if row["type_op"]=="Vente" else "#cce5ff"
                    badge_t = "#1a5c2e" if row["type_op"]=="Vente" else "#0a3d6b"
                    st.markdown(f"""
<div style="padding:10px 0;border-bottom:1px solid #e8e4dc;display:flex;align-items:center;gap:10px;">
  <span style="font-family:'DM Mono',monospace;font-size:10px;background:{badge_c};
               color:{badge_t};padding:2px 8px;border-radius:2px;">{row['type_op']}</span>
  <span style="font-size:13px;font-weight:500;">{str(row['description'])[:60]}</span>
  <span style="font-family:'DM Mono',monospace;font-size:11px;color:#888078;margin-left:auto;">
    {row['date_op']} · {fmt_eur_fn(row['total_ht'])}
  </span>
</div>""", unsafe_allow_html=True)
                with cd:
                    if row["facture_data"] is not None:
                        st.download_button(
                            "⬇",
                            data=bytes(row["facture_data"]),
                            file_name=row["facture_nom"] or f"facture_{row['id']}.pdf",
                            key=f"dl_fac_{row['id']}"
                        )

    # ── NOUVELLE OPÉRATION ─────────────────────────────────────────────────────
    if tab_new is not None:
        with tab_new:
            st.markdown('<div class="section-title">Nouvelle opération</div>',
                        unsafe_allow_html=True)

            # Récupérer la liste des SKUs depuis les produits
            sku_list = get_sku_list(conn)
            sku_options = ["— Saisie libre —"] + sku_list

            c1, c2, c3 = st.columns(3)
            with c1:
                date_op  = st.date_input("Date", value=date.today())
                type_op  = st.selectbox("Type d'opération", TYPES_OP)
            with c2:
                categorie = st.selectbox("Catégorie", CATEGORIES)
                devise    = st.selectbox("Devise", DEVISES)
            with c3:
                sku_sel   = st.selectbox("SKU Produit", sku_options, key="sku_sel")
                if sku_sel == "— Saisie libre —":
                    ref_produit = st.text_input("Réf. SKU libre", placeholder="ex: MIRA-001")
                else:
                    ref_produit = sku_sel.split(" — ")[0]
                    st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:10px;color:#888078;
     background:#f0ece4;padding:4px 8px;border-radius:2px;margin-top:2px;">
  SKU : {ref_produit}
</div>""", unsafe_allow_html=True)

            info_process = st.text_input("Article / Process", placeholder="ex: Veste Miura Jacket")
            description  = st.text_area("Description", height=68,
                                        placeholder="Détail de l'opération...")

            # ── Mode de saisie prix ────────────────────────────────────────────
            mode_prix = st.radio(
                "Mode de saisie",
                ["Prix unitaire → total auto", "Prix total → unitaire auto"],
                horizontal=True, key="mode_prix"
            )

            c4, c5, c6, c7 = st.columns(4)
            with c4:
                quantite = st.number_input("Quantité", min_value=0.0, value=1.0, step=0.1)
            with c5:
                unite = st.selectbox("Unité", UNITES)
            with c6:
                if mode_prix == "Prix unitaire → total auto":
                    prix_unitaire = st.number_input("Prix unit. HT (€)", min_value=0.0,
                                                    value=0.0, step=0.01)
                    total_ht_input = None
                else:
                    total_ht_input = st.number_input("Total HT (€)", min_value=0.0,
                                                     value=0.0, step=0.01)
                    prix_unitaire = None
            with c7:
                taux_change = st.number_input(
                    "Taux change", min_value=0.0001, value=1.0, step=0.0001,
                    help="1 EUR = X devise. Ex JPY: saisir 0.00625 si 1€=160¥"
                )

            # Calculs automatiques
            if mode_prix == "Prix unitaire → total auto":
                pu = prix_unitaire or 0.0
                total_ht_calc = round(quantite * pu, 2) if pu > 0 else 0.0
                pu_calc = pu
            else:
                th = total_ht_input or 0.0
                total_ht_calc = th
                pu_calc = round(th / quantite, 4) if quantite > 0 else 0.0

            # TVA auto-suggérée
            tva_sug  = suggest_tva(type_op, categorie, devise)
            type_tva = st.selectbox(
                "Type TVA", TYPES_TVA,
                index=TYPES_TVA.index(tva_sug),
                help=f"Suggestion automatique : {tva_sug}"
            )

            tva_rate       = 0.20 if type_tva in ("Collectée","Déductible","Autoliquidée") else 0.0
            tva_amt        = round(total_ht_calc * tva_rate, 2)
            total_ttc_calc = round(total_ht_calc + tva_amt, 2)
            montant_orig   = round(total_ht_calc / taux_change, 2) if taux_change > 0 and devise != "EUR" else total_ht_calc

            if total_ht_calc > 0:
                sym = DEVISES_SYM.get(devise, devise)
                orig_str = f" · Montant original : <strong>{montant_orig:,.0f} {sym}</strong>" if devise != "EUR" else ""
                if mode_prix == "Prix total → unitaire auto" and pu_calc > 0:
                    pu_str = f" · Prix unit. calculé : <strong>{fmt_eur_fn(pu_calc)}</strong>"
                else:
                    pu_str = ""
                st.markdown(f"""
<div class="info-box">
💡 Total HT : <strong>{fmt_eur_fn(total_ht_calc)}</strong>
{pu_str}
· TVA ({type_tva}) : <strong>{fmt_eur_fn(tva_amt)}</strong>
· Total TTC : <strong>{fmt_eur_fn(total_ttc_calc)}</strong>
{orig_str}
</div>""", unsafe_allow_html=True)

            c8, c9 = st.columns(2)
            with c8:
                payeur = st.selectbox("Payeur", PAYEURS)
                source = st.text_input("Source / Contact", placeholder="ex: Jim Jin +86...")
            with c9:
                beneficiaire = st.selectbox("Bénéficiaire", BENEFICIAIRES)
                info_comp    = st.text_input("Info complémentaire",
                                             placeholder="N°commande, N°client...")

            facture_file = st.file_uploader(
                "📎 Facture (PDF, PNG, JPG)",
                type=["pdf","png","jpg","jpeg","webp"]
            )

            if st.button("✓ Enregistrer l'opération", type="primary"):
                if not description:
                    st.error("La description est obligatoire.")
                else:
                    fac_data = facture_file.read() if facture_file else None
                    fac_nom  = facture_file.name  if facture_file else None
                    db_conn  = sqlite3.connect(DB_PATH, check_same_thread=False)
                    db_conn.execute("""INSERT INTO transactions
                        (annee,mois,date_op,ref_produit,info_process,description,
                         categorie,type_op,quantite,unite,prix_unitaire,type_tva,
                         total_ht,total_ttc,tva,devise,taux_change,montant_original,
                         payeur,beneficiaire,source,info_complementaire,
                         facture_data,facture_nom)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (date_op.year, date_op.month, str(date_op),
                         ref_produit, info_process, description,
                         categorie, type_op, quantite, unite, pu_calc, type_tva,
                         total_ht_calc, total_ttc_calc, tva_amt,
                         devise, taux_change, montant_orig,
                         payeur, beneficiaire, source, info_comp,
                         fac_data, fac_nom))
                    # Sync stock auto
                    if ref_produit and unite in ("Article","Pièces","Mètre","Kg","Lot"):
                        _sync_stock(db_conn, ref_produit, type_op, quantite)
                    db_conn.commit(); db_conn.close()
                    msg = "✓ Opération enregistrée."
                    if ref_produit: msg += f" Stock mis à jour ({ref_produit})."
                    st.success(msg)
                    st.rerun()

    # ── OCR — SCAN FACTURE ─────────────────────────────────────────────────────
    if tab_ocr is not None:
        with tab_ocr:
            st.markdown('<div class="section-title">Scan OCR de facture</div>',
                        unsafe_allow_html=True)
            st.markdown("""
<div class="info-box">
Uploadez une photo ou un PDF de facture. Claude extrait automatiquement les informations
et pré-remplit le formulaire. Vous pouvez corriger avant d'enregistrer.
</div>""", unsafe_allow_html=True)

            ocr_file = st.file_uploader(
                "📸 Photo ou PDF de la facture",
                type=["pdf","png","jpg","jpeg","webp"],
                key="ocr_upload"
            )

            if ocr_file:
                col_prev, col_res = st.columns([1, 2])

                with col_prev:
                    st.markdown("**Aperçu**")
                    if ocr_file.name.lower().endswith(".pdf"):
                        st.info("PDF chargé — aperçu non disponible.")
                    else:
                        st.image(ocr_file, use_container_width=True)
                    ocr_file.seek(0)

                with col_res:
                    if st.button("🔍 Analyser avec Claude", type="primary"):
                        with st.spinner("Analyse OCR en cours..."):
                            ocr_file.seek(0)
                            img_bytes = ocr_file.read()
                            result = ocr_facture_claude(img_bytes, ocr_file.name)

                        if "error" in result:
                            st.error(f"Erreur OCR : {result['error']}")
                        else:
                            st.session_state["ocr_result"] = result
                            st.session_state["ocr_filename"] = ocr_file.name
                            st.session_state["ocr_data"] = img_bytes
                            st.success("✓ Analyse terminée — vérifiez et corrigez ci-dessous.")

            # Formulaire pré-rempli depuis OCR
            if "ocr_result" in st.session_state:
                r = st.session_state["ocr_result"]
                st.markdown('<div class="section-title">Données extraites — à valider</div>',
                            unsafe_allow_html=True)

                with st.form("ocr_confirm"):
                    oc1, oc2, oc3 = st.columns(3)
                    with oc1:
                        try:
                            ocr_date = date.fromisoformat(r.get("date") or date.today().isoformat())
                        except Exception:
                            ocr_date = date.today()
                        ocr_date_in = st.date_input("Date", value=ocr_date)
                        ocr_type = st.selectbox(
                            "Type", TYPES_OP,
                            index=TYPES_OP.index(r.get("type_op","Achat"))
                                  if r.get("type_op") in TYPES_OP else 0
                        )
                    with oc2:
                        ocr_cat = st.selectbox(
                            "Catégorie", CATEGORIES,
                            index=CATEGORIES.index(r.get("categorie_suggeree","Autre frais"))
                                  if r.get("categorie_suggeree") in CATEGORIES else 7
                        )
                        ocr_dev = st.selectbox(
                            "Devise", DEVISES,
                            index=DEVISES.index(r.get("devise","EUR"))
                                  if r.get("devise") in DEVISES else 0
                        )
                    with oc3:
                        sku_list2 = get_sku_list(conn)
                        ocr_sku = st.selectbox("SKU", ["— Saisie libre —"] + sku_list2)
                        ref_ocr = ocr_sku.split(" — ")[0] if ocr_sku != "— Saisie libre —" else ""
                        ocr_source = st.text_input("Fournisseur", value=r.get("fournisseur",""))

                    ocr_desc = st.text_input("Description", value=r.get("description",""))

                    om1, om2, om3 = st.columns(3)
                    with om1:
                        ocr_ht  = st.number_input("Total HT (€)", value=float(r.get("total_ht") or 0), min_value=0.0, step=0.01)
                    with om2:
                        ocr_tva_amt = st.number_input("TVA (€)", value=float(r.get("tva") or 0), min_value=0.0, step=0.01)
                    with om3:
                        ocr_ttc = st.number_input("Total TTC (€)", value=float(r.get("total_ttc") or 0), min_value=0.0, step=0.01)

                    tva_sug2 = suggest_tva(ocr_type, ocr_cat, ocr_dev)
                    ocr_tva_type = st.selectbox(
                        "Type TVA", TYPES_TVA,
                        index=TYPES_TVA.index(tva_sug2) if tva_sug2 in TYPES_TVA else 0
                    )
                    ocr_info = st.text_input("N° Facture", value=r.get("numero_facture","") or "")
                    ocr_benef = st.selectbox("Bénéficiaire", BENEFICIAIRES)

                    if st.form_submit_button("✓ Enregistrer l'opération OCR", type="primary"):
                        db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                        img_bytes_save = st.session_state.get("ocr_data")
                        fname_save     = st.session_state.get("ocr_filename")
                        db_conn.execute("""INSERT INTO transactions
                            (annee,mois,date_op,ref_produit,info_process,description,
                             categorie,type_op,quantite,unite,prix_unitaire,type_tva,
                             total_ht,total_ttc,tva,devise,taux_change,montant_original,
                             payeur,beneficiaire,source,info_complementaire,
                             facture_data,facture_nom)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (ocr_date_in.year, ocr_date_in.month, str(ocr_date_in),
                             ref_ocr, ocr_source, ocr_desc,
                             ocr_cat, ocr_type, 1.0, "Euros",
                             ocr_ht, ocr_tva_type,
                             ocr_ht, ocr_ttc, ocr_tva_amt,
                             ocr_dev, 1.0, ocr_ht,
                             "Eastwood Studio", ocr_benef, ocr_source, ocr_info,
                             img_bytes_save, fname_save))
                        db_conn.commit(); db_conn.close()

                        # Nettoyer session
                        for k in ["ocr_result","ocr_filename","ocr_data"]:
                            st.session_state.pop(k, None)
                        st.success("✓ Opération enregistrée depuis OCR.")
                        st.rerun()

    conn.close()


def _sync_stock(conn, ref_produit, type_op, quantite):
    """Sync stock interne au module opérations."""
    row = conn.execute("SELECT * FROM stock WHERE ref=?", (ref_produit,)).fetchone()
    if not row:
        return
    if type_op == "Vente":
        conn.execute("""UPDATE stock SET
            qte_vendue=qte_vendue+?, qte_stock=MAX(0,qte_stock-?) WHERE ref=?""",
            (quantite, quantite, ref_produit))
    elif type_op in ("Achat","Achat perso"):
        conn.execute("UPDATE stock SET qte_stock=qte_stock+? WHERE ref=?",
                     (quantite, ref_produit))
    elif type_op == "Utilisation":
        conn.execute("""UPDATE stock SET
            qte_utilisee=qte_utilisee+?, qte_stock=MAX(0,qte_stock-?) WHERE ref=?""",
            (quantite, quantite, ref_produit))
    conn.commit()
