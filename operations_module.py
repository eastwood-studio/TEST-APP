# ══════════════════════════════════════════════════════════════════════════════
# MODULE OPÉRATIONS v3
# Colonnes enrichies · Payeur Client · Modif ligne · Vente→Commande auto · Collection
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
PAYEURS_ACHATS = ["Eastwood Studio", "Jules", "Corentin", "Alexis"]
BENEFICIAIRES  = ["Eastwood Studio", "Jules", "Corentin", "Alexis"]
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

EW_V = "#7b506f"
EW_G = "#395f30"
EW_B = "#8a7968"
EW_S = "#ede3d3"
EW_K = "#1a1a1a"


def suggest_tva(type_op, categorie, devise="EUR"):
    if devise not in ("EUR", ""):
        return "Autoliquidée"
    rules = TVA_RULES.get(type_op, {})
    return rules.get(categorie, rules.get("default", "Aucun"))


def fmt_eur(v):
    if v is None: return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


def get_sku_list(conn):
    try:
        df = pd.read_sql(
            "SELECT ref, nom, variant, collection FROM products ORDER BY collection, nom", conn)
        if df.empty:
            return [], []
        labels = []
        refs   = []
        for _, r in df.iterrows():
            var = f" / {r['variant']}" if r.get("variant") else ""
            labels.append(f"{r['ref']} — {r['nom']}{var}")
            refs.append(r['ref'])
        return labels, refs
    except Exception:
        return [], []


def get_collections_list(conn):
    """Retourne les collections disponibles depuis la table products (dynamic)."""
    try:
        df = pd.read_sql(
            "SELECT DISTINCT collection FROM products WHERE collection IS NOT NULL ORDER BY collection",
            conn)
        return [""] + df["collection"].tolist() if not df.empty else [""]
    except Exception:
        return ["", "Chapter N°I — Hunting & Fishing", "Chapter N°II — Le Souvenir"]


def get_date_filter(periode, date_debut_custom=None, date_fin_custom=None):
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


def ensure_columns(conn):
    """Migration silencieuse : ajoute les nouvelles colonnes si manquantes."""
    c = conn.cursor()
    existing = [r[1] for r in c.execute("PRAGMA table_info(transactions)").fetchall()]
    new_cols = [
        ("frais_envoi",      "REAL DEFAULT 0"),
        ("total_ttc_calc",   "REAL DEFAULT 0"),
        ("collection_op",    "TEXT DEFAULT ''"),
        ("info_complementaire2", "TEXT DEFAULT ''"),
        ("client_nom",       "TEXT DEFAULT ''"),
        ("client_email",     "TEXT DEFAULT ''"),
        ("client_tel",       "TEXT DEFAULT ''"),
        ("client_adresse",   "TEXT DEFAULT ''"),
        ("num_operation",    "INTEGER DEFAULT 0"),
    ]
    for col, defn in new_cols:
        if col not in existing:
            try: c.execute(f"ALTER TABLE transactions ADD COLUMN {col} {defn}")
            except Exception: pass
    conn.commit()


def assign_operation_numbers(conn):
    """Attribue des numéros chronologiques à toutes les opérations sans numéro."""
    try:
        rows = conn.execute(
            "SELECT id FROM transactions ORDER BY date_op ASC, id ASC"
        ).fetchall()
        for i, (rid,) in enumerate(rows, 1):
            conn.execute("UPDATE transactions SET num_operation=? WHERE id=?", (i, rid))
        conn.commit()
    except Exception:
        pass


def get_next_num(conn):
    row = conn.execute("SELECT MAX(num_operation) FROM transactions").fetchone()
    return (row[0] or 0) + 1


def load_operations(conn, date_debut=None, date_fin=None,
                    type_op=None, categorie=None, devise=None,
                    tva_type=None, search=None, collection=None):
    q = "SELECT * FROM transactions WHERE 1=1"
    p = []
    if date_debut:   q += " AND date_op >= ?"; p.append(date_debut)
    if date_fin:     q += " AND date_op <= ?"; p.append(date_fin)
    if type_op:      q += " AND type_op=?";    p.append(type_op)
    if categorie:    q += " AND categorie=?";  p.append(categorie)
    if devise:       q += " AND devise=?";     p.append(devise)
    if tva_type:     q += " AND type_tva=?";   p.append(tva_type)
    if collection:   q += " AND collection_op=?"; p.append(collection)
    df = pd.read_sql(q + " ORDER BY date_op DESC", conn, params=p)
    if search and not df.empty:
        df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
    return df


def auto_create_commande(conn, date_op, ref_produit, info_process, description,
                         quantite, prix_unitaire, total_ttc, devise,
                         client_nom, client_email, client_tel, client_adresse,
                         source, type_vente="B2C"):
    """Quand une vente est enregistrée → créer la commande correspondante automatiquement."""
    try:
        # Extraire prénom/nom
        parts = (client_nom or "").strip().split()
        prenom_ = parts[0] if parts else ""
        nom_    = " ".join(parts[1:]) if len(parts) > 1 else (parts[0] if parts else "")

        # Créer contact si email fourni
        if client_email:
            existing = conn.execute(
                "SELECT id FROM contacts WHERE email=?", (client_email,)).fetchone()
            if not existing:
                conn.execute("""INSERT INTO contacts
                    (type_contact, sous_type, nom, email, telephone, adresse, importance)
                    VALUES (?,?,?,?,?,?,?)""",
                    ("Client", type_vente, client_nom or "Client", client_email,
                     client_tel or "", client_adresse or "", "Normal"))

        # Créer commande
        num_auto = f"CMD-{date_op.strftime('%Y%m%d')}-{ref_produit[:6] if ref_produit else 'VENTE'}"
        conn.execute("""INSERT INTO commandes
            (priorite, date_commande, num_commande, ref_article, qte,
             prix_ht, vat, prix_ttc, prix_final, plateforme,
             prenom, nom, mail, telephone, adresse, etat, notes,
             type_cmd)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("Normal", str(date_op), num_auto, ref_produit or "", quantite,
             round(total_ttc / 1.2, 2), 20.0, total_ttc, total_ttc,
             source or "Opérations",
             prenom_, nom_, client_email or "", client_tel or "", client_adresse or "",
             "A produire",
             description or "",
             type_vente))
        conn.commit()
        return num_auto
    except Exception as e:
        return None


# ── OCR via API Claude ─────────────────────────────────────────────────────────
def ocr_facture_claude(image_bytes: bytes, filename: str) -> dict:
    try:
        import anthropic
        api_key = (st.secrets.get("ANTHROPIC_API_KEY", None)
                   or os.environ.get("ANTHROPIC_API_KEY", None))
        if not api_key:
            return {"error": "Clé API Anthropic manquante dans les secrets Streamlit."}
        client = anthropic.Anthropic(api_key=api_key)
        ext = filename.lower().split(".")[-1] if filename else "jpg"
        media_types = {"pdf":"application/pdf","png":"image/png",
                       "jpg":"image/jpeg","jpeg":"image/jpeg","webp":"image/webp"}
        media_type = media_types.get(ext, "image/jpeg")
        b64_data = base64.standard_b64encode(image_bytes).decode("utf-8")
        content_block = ({"type":"document","source":{"type":"base64","media_type":"application/pdf","data":b64_data}}
                         if media_type == "application/pdf"
                         else {"type":"image","source":{"type":"base64","media_type":media_type,"data":b64_data}})
        prompt = """Analyse cette facture. Réponds UNIQUEMENT en JSON valide sans markdown.
{
  "date": "YYYY-MM-DD ou null",
  "fournisseur": "nom émetteur",
  "description": "description courte (max 80 chars)",
  "total_ht": "montant HT chiffres ou null",
  "total_ttc": "montant TTC chiffres ou null",
  "tva": "montant TVA chiffres ou null",
  "devise": "EUR ou JPY ou USD ou GBP",
  "numero_facture": "numéro ou null",
  "categorie_suggeree": "Matière première|Composants|Confection / Production|Communication|Transport / Logistique|Stockage|Salaire|Autre frais|Légal / Administratif|Produit fini|Facture|Logiciel & outils|Packaging",
  "type_op": "Achat ou Vente"
}"""
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=800,
            messages=[{"role":"user","content":[content_block,{"type":"text","text":prompt}]}])
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw.strip())
    except ImportError:
        return {"error": "Package 'anthropic' non installé."}
    except json.JSONDecodeError as e:
        return {"error": f"Réponse OCR non parseable : {e}"}
    except Exception as e:
        return {"error": str(e)}


def _sync_stock(conn, ref_produit, type_op, quantite):
    row = conn.execute("SELECT * FROM stock WHERE ref=?", (ref_produit,)).fetchone()
    if not row: return
    if type_op == "Vente":
        conn.execute("UPDATE stock SET qte_vendue=qte_vendue+?, qte_stock=MAX(0,qte_stock-?) WHERE ref=?",
                     (quantite, quantite, ref_produit))
    elif type_op in ("Achat","Achat perso"):
        conn.execute("UPDATE stock SET qte_stock=qte_stock+? WHERE ref=?", (quantite, ref_produit))
    elif type_op == "Utilisation":
        conn.execute("UPDATE stock SET qte_utilisee=qte_utilisee+?, qte_stock=MAX(0,qte_stock-?) WHERE ref=?",
                     (quantite, quantite, ref_produit))
    conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE OPÉRATIONS PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_operations(can_fn, DB_PATH, fmt_eur_fn=None):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    ensure_columns(conn)
    if fmt_eur_fn is None:
        fmt_eur_fn = fmt_eur

    st.markdown("### Opérations")

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
        # Filtres ligne 1
        fc1,fc2,fc3,fc4 = st.columns(4)
        with fc1: f_periode = st.selectbox("Période", PERIODES_FILTRE, key="ops_periode")
        with fc2: f_type    = st.selectbox("Type", ["Tous"]+TYPES_OP, key="ops_type")
        with fc3: f_cat     = st.selectbox("Catégorie", ["Toutes"]+CATEGORIES, key="ops_cat")
        with fc4:
            colls = get_collections_list(conn)
            f_coll = st.selectbox("Collection", ["Toutes"]+[c for c in colls if c], key="ops_coll")

        fc5,fc6,fc7 = st.columns(3)
        with fc5: f_dev  = st.selectbox("Devise", ["Toutes"]+DEVISES, key="ops_dev")
        with fc6: f_tva  = st.selectbox("TVA", ["Tous"]+TYPES_TVA, key="ops_tva")
        with fc7: f_srch = st.text_input("Recherche", placeholder="fournisseur, SKU, client...", key="ops_srch")

        d_debut_custom = d_fin_custom = None
        if f_periode == "Personnalisée":
            pc1,pc2 = st.columns(2)
            with pc1: d_debut_custom = st.date_input("Du", value=date.today().replace(day=1), key="ops_d1")
            with pc2: d_fin_custom   = st.date_input("Au", value=date.today(), key="ops_d2")

        d_debut, d_fin = get_date_filter(f_periode, d_debut_custom, d_fin_custom)

        df_ops = load_operations(
            conn,
            date_debut=d_debut, date_fin=d_fin,
            type_op=None if f_type=="Tous" else f_type,
            categorie=None if f_cat=="Toutes" else f_cat,
            devise=None if f_dev=="Toutes" else f_dev,
            tva_type=None if f_tva=="Tous" else f_tva,
            search=f_srch or None,
            collection=None if f_coll=="Toutes" else f_coll,
        )

        if df_ops.empty:
            st.info("Aucune opération sur cette période.")
        else:
            # KPIs
            k1,k2,k3,k4 = st.columns(4)
            ventes_f = df_ops[df_ops["type_op"]=="Vente"]["total_ht"].sum()
            achats_f = df_ops[df_ops["type_op"].isin(["Achat","Achat perso"])]["total_ht"].sum()
            with k1: st.metric("CA HT", fmt_eur_fn(ventes_f))
            with k2: st.metric("Charges HT", fmt_eur_fn(achats_f))
            with k3: st.metric("TVA collectée", fmt_eur_fn(df_ops[df_ops["type_tva"]=="Collectée"]["tva"].sum()))
            with k4: st.metric("Nb opérations", len(df_ops))

            # ── Tableau enrichi avec colonnes demandées ─────────────────────────
            # Colonnes : Qté | Unité | Total HT | Frais envoi | Type TVA | Total TTC | Montant TVA | Info complémentaire | Collection
            df_display = df_ops.copy()

            # Calculer Total TTC si pas stocké
            if "total_ttc_calc" not in df_display.columns:
                df_display["total_ttc_calc"] = df_display["total_ttc"]
            if "frais_envoi" not in df_display.columns:
                df_display["frais_envoi"] = 0.0
            if "collection_op" not in df_display.columns:
                df_display["collection_op"] = ""
            if "info_complementaire" not in df_display.columns:
                df_display["info_complementaire"] = ""

            # Assigner numéros chronologiques si manquants
            if "num_operation" not in df_ops.columns or df_ops["num_operation"].fillna(0).sum() == 0:
                assign_operation_numbers(conn)
                df_ops = load_operations(
                    conn,
                    date_debut=d_debut, date_fin=d_fin,
                    type_op=None if f_type=="Tous" else f_type,
                    categorie=None if f_cat=="Toutes" else f_cat,
                    devise=None if f_dev=="Toutes" else f_dev,
                    tva_type=None if f_tva=="Tous" else f_tva,
                    search=f_srch or None,
                    collection=None if f_coll=="Toutes" else f_coll,
                )
            cols_show = [
                "num_operation","date_op","ref_produit","info_process","description",
                "categorie","type_op","quantite","unite",
                "total_ht","frais_envoi","type_tva","total_ttc","tva",
                "collection_op","payeur","beneficiaire","info_complementaire","devise"
            ]
            cols_rename = {
                "num_operation":"N°","date_op":"Date","ref_produit":"SKU","info_process":"Article",
                "description":"Description","categorie":"Catégorie","type_op":"Type",
                "quantite":"Qté","unite":"Unité","total_ht":"Total HT",
                "frais_envoi":"Frais envoi","type_tva":"Type TVA",
                "total_ttc":"Total TTC","tva":"Montant TVA",
                "collection_op":"Collection","payeur":"Payeur",
                "beneficiaire":"Bénéficiaire","info_complementaire":"Info complémentaire",
                "devise":"Devise"
            }
            existing_cols = [c for c in cols_show if c in df_display.columns]
            st.dataframe(
                df_display[existing_cols].rename(columns=cols_rename),
                use_container_width=True, hide_index=True
            )

            # Téléchargement factures par ligne
            df_with_fac = df_ops[df_ops["facture_data"].notna()] if "facture_data" in df_ops.columns else pd.DataFrame()
            if not df_with_fac.empty:
                st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#8a7968;text-transform:uppercase;letter-spacing:.12em;margin:10px 0 6px;">Factures attachées ({len(df_with_fac)})</div>', unsafe_allow_html=True)
                for _, frow in df_with_fac.iterrows():
                    fc1, fc2, fc3 = st.columns([1,4,2])
                    with fc1:
                        num = frow.get("num_operation","?")
                        st.markdown(f'<span style="font-family:DM Mono,monospace;font-size:10px;color:#7b506f;">N°{num}</span>', unsafe_allow_html=True)
                    with fc2:
                        desc_frow = str(frow.get('description',''))[:50]
                        date_frow = frow.get('date_op','')
                        st.markdown(f'<span style="font-size:11px;">{desc_frow} · {date_frow}</span>', unsafe_allow_html=True)
                    with fc3:
                        fac_bytes = bytes(frow["facture_data"])
                        fac_name = frow.get("facture_nom") or f"facture_op{num}.pdf"
                        st.download_button(
                            "⬇ Facture",
                            data=fac_bytes,
                            file_name=fac_name,
                            mime="application/pdf" if fac_name.lower().endswith(".pdf") else "application/octet-stream",
                            key=f"dl_fac_hist_{frow['id']}"
                        )

            # ── Modifier une ligne ─────────────────────────────────────────────
            if can_fn("finance_write"):
                with st.expander("✏️ Modifier une ligne d'opération"):
                    # Recherche par numéro d'opération
                    search_num = st.text_input("N° d'opération à modifier", placeholder="ex: 3", key="edit_ops_num")
                    ids_ops = df_ops["id"].tolist()
                    if search_num.strip().isdigit():
                        match_num = df_ops[df_ops["num_operation"]==int(search_num.strip())]
                        sel_id = match_num["id"].iloc[0] if not match_num.empty else ids_ops[0]
                    else:
                        labels_ops = [
                            f"N°{r.get('num_operation',i+1)} · {r['date_op']} · {r['type_op']} · {str(r['description'])[:35]}"
                            for i,(_, r) in enumerate(df_ops.iterrows())
                        ]
                        sel_label = st.selectbox("Ou sélectionner", labels_ops, key="edit_ops_sel")
                        sel_id = ids_ops[labels_ops.index(sel_label)]
                    row_edit = df_ops[df_ops["id"]==sel_id].iloc[0]

                    with st.form(f"edit_op_{sel_id}"):
                        me1,me2,me3 = st.columns(3)
                        with me1:
                            e_date  = st.date_input("Date", value=date.fromisoformat(str(row_edit["date_op"])))
                            e_type  = st.selectbox("Type", TYPES_OP,
                                index=TYPES_OP.index(row_edit["type_op"]) if row_edit["type_op"] in TYPES_OP else 0)
                            e_cat   = st.selectbox("Catégorie", CATEGORIES,
                                index=CATEGORIES.index(row_edit["categorie"]) if row_edit.get("categorie") in CATEGORIES else 0)
                        with me2:
                            e_desc  = st.text_input("Description", value=str(row_edit.get("description","") or ""))
                            e_ht    = st.number_input("Total HT", value=float(row_edit.get("total_ht",0) or 0), min_value=0.0)
                            e_tva_t = st.selectbox("Type TVA", TYPES_TVA,
                                index=TYPES_TVA.index(row_edit["type_tva"]) if row_edit.get("type_tva") in TYPES_TVA else 0)
                        with me3:
                            e_dev   = st.selectbox("Devise", DEVISES,
                                index=DEVISES.index(row_edit["devise"]) if row_edit.get("devise") in DEVISES else 0)
                            e_fenv  = st.number_input("Frais envoi", value=float(row_edit.get("frais_envoi",0) or 0), min_value=0.0)
                            e_coll  = st.text_input("Collection", value=str(row_edit.get("collection_op","") or ""))
                        e_info  = st.text_input("Info complémentaire", value=str(row_edit.get("info_complementaire","") or ""))

                        if st.form_submit_button("💾 Enregistrer les modifications"):
                            tva_rate = 0.20 if e_tva_t in ("Collectée","Déductible","Autoliquidée") else 0.0
                            tva_amt  = round(e_ht * tva_rate, 2)
                            ttc_new  = round(e_ht + tva_amt + e_fenv, 2)
                            conn.execute("""UPDATE transactions SET
                                date_op=?, annee=?, mois=?, type_op=?, categorie=?,
                                description=?, total_ht=?, tva=?, total_ttc=?,
                                type_tva=?, devise=?, frais_envoi=?,
                                collection_op=?, info_complementaire=?
                                WHERE id=?""",
                                (str(e_date), e_date.year, e_date.month, e_type, e_cat,
                                 e_desc, e_ht, tva_amt, ttc_new,
                                 e_tva_t, e_dev, e_fenv,
                                 e_coll, e_info, sel_id))
                            conn.commit()
                            st.success("✓ Opération mise à jour."); st.rerun()

            # Export
            buf = io.BytesIO()
            df_ops.drop(columns=["facture_data"], errors="ignore").to_csv(buf, index=False, encoding="utf-8-sig")
            st.download_button("⬇ Export CSV", buf.getvalue(),
                file_name=f"operations_{date.today()}.csv",
                mime="text/csv")

    # ── FACTURES ───────────────────────────────────────────────────────────────
    with tab_fac:
        st.markdown('<div class="section-title">Espace factures</div>', unsafe_allow_html=True)
        df_fac = pd.read_sql("""
            SELECT id, date_op, description, total_ht, type_op,
                   beneficiaire, facture_nom, facture_data
            FROM transactions WHERE facture_data IS NOT NULL ORDER BY date_op DESC""", conn)

        if df_fac.empty:
            st.info("Aucune facture enregistrée.")
        else:
            ff1,ff2,ff3 = st.columns(3)
            with ff1: ff_type = st.selectbox("Type", ["Tous","Vente","Achat"], key="fac_type")
            with ff2: ff_srch = st.text_input("Rechercher", key="fac_srch")
            with ff3: ff_per  = st.selectbox("Période", PERIODES_FILTRE, key="fac_per")

            df_ff = df_fac.copy()
            if ff_type != "Tous": df_ff = df_ff[df_ff["type_op"]==ff_type]
            if ff_srch: df_ff = df_ff[df_ff.apply(lambda r: ff_srch.lower() in str(r).lower(), axis=1)]
            d1,d2 = get_date_filter(ff_per)
            if d1: df_ff = df_ff[df_ff["date_op"] >= d1]
            if d2: df_ff = df_ff[df_ff["date_op"] <= d2]

            for _, row in df_ff.iterrows():
                ci,cd = st.columns([4,1])
                with ci:
                    bc = "#e8f2e8" if row["type_op"]=="Vente" else "#ede3d3"
                    bt = EW_G if row["type_op"]=="Vente" else EW_B
                    st.markdown(f"""
<div style="padding:10px 0;border-bottom:1px solid {EW_S};display:flex;align-items:center;gap:10px;">
  <span style="font-family:'DM Mono',monospace;font-size:10px;background:{bc};color:{bt};padding:2px 8px;">
    {row['type_op']}
  </span>
  <span style="font-size:13px;font-weight:500;">{str(row['description'])[:60]}</span>
  <span style="font-family:'DM Mono',monospace;font-size:11px;color:{EW_B};margin-left:auto;">
    {row['date_op']} · {fmt_eur_fn(row['total_ht'])}
  </span>
</div>""", unsafe_allow_html=True)
                with cd:
                    if row["facture_data"] is not None:
                        st.download_button("⬇", data=bytes(row["facture_data"]),
                            file_name=row["facture_nom"] or f"facture_{row['id']}.pdf",
                            key=f"dl_fac_{row['id']}")

    # ── NOUVELLE OPÉRATION ─────────────────────────────────────────────────────
    if tab_new is not None:
        with tab_new:
            st.markdown('<div class="section-title">Nouvelle opération</div>', unsafe_allow_html=True)

            sku_labels, sku_refs = get_sku_list(conn)
            sku_options = ["— Saisie libre —"] + sku_labels

            c1,c2,c3 = st.columns(3)
            with c1:
                date_op  = st.date_input("Date", value=date.today())
                type_op  = st.selectbox("Type d'opération", TYPES_OP)
            with c2:
                categorie = st.selectbox("Catégorie", CATEGORIES)
                devise    = st.selectbox("Devise", DEVISES)
            with c3:
                sku_sel = st.selectbox("SKU Produit", sku_options, key="sku_sel")
                if sku_sel == "— Saisie libre —":
                    ref_produit = st.text_input("Réf. SKU libre", placeholder="ex: EWSJACKET-001A-TOB")
                else:
                    ref_produit = sku_refs[sku_labels.index(sku_sel)]
                    st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:10px;color:{EW_B};
     background:#f0ece4;padding:4px 8px;margin-top:2px;">SKU : {ref_produit}</div>""",
                        unsafe_allow_html=True)

            # Collection dynamique
            collections = get_collections_list(conn)
            col_op = st.selectbox("Collection", collections, key="new_op_coll")

            info_process = st.text_input("Article / Process", placeholder="ex: Waterfowl Jacket Tobacco")
            description  = st.text_area("Description", height=60, placeholder="Détail de l'opération...")

            # ── Payeur : Client si Vente ───────────────────────────────────────
            if type_op == "Vente":
                st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_B};text-transform:uppercase;letter-spacing:.15em;margin:8px 0 4px;">Client (payeur)</div>', unsafe_allow_html=True)
                cv1,cv2,cv3 = st.columns(3)
                with cv1:
                    client_nom    = st.text_input("Nom client", placeholder="Ex: Jean Dupont")
                    client_email  = st.text_input("Email client")
                with cv2:
                    client_tel    = st.text_input("Téléphone")
                    client_adresse= st.text_input("Adresse")
                with cv3:
                    type_vente    = st.selectbox("Type de vente", ["B2C — Retail","B2B — Wholesale"])
                    plateforme    = st.text_input("Plateforme / Source", placeholder="Shopify, Showroom, DM Instagram...")
                payeur    = "Client"
                beneficiaire = "Eastwood Studio"
            else:
                client_nom = client_email = client_tel = client_adresse = ""
                type_vente = plateforme = ""
                pv1,pv2 = st.columns(2)
                with pv1: payeur      = st.selectbox("Payeur", PAYEURS_ACHATS)
                with pv2: beneficiaire = st.selectbox("Bénéficiaire", BENEFICIAIRES)

            source = st.text_input("Source / Contact fournisseur", placeholder="ex: Jim Jin +86...") if type_op != "Vente" else plateforme

            # ── Mode prix ────────────────────────────────────────────────────────
            mode_prix = st.radio("Mode de saisie prix",
                                 ["Prix unitaire → total auto", "Prix total → unitaire auto"],
                                 horizontal=True, key="mode_prix")

            c4,c5,c6,c7,c8 = st.columns(5)
            with c4: quantite = st.number_input("Quantité", min_value=0.0, value=1.0, step=0.1)
            with c5: unite    = st.selectbox("Unité", UNITES)
            with c6:
                if mode_prix == "Prix unitaire → total auto":
                    prix_unitaire = st.number_input("Prix unit. HT (€)", min_value=0.0, value=0.0, step=0.01)
                    total_ht_input = None
                else:
                    total_ht_input = st.number_input("Total HT (€)", min_value=0.0, value=0.0, step=0.01)
                    prix_unitaire = None
            with c7:
                frais_envoi = st.number_input("Frais envoi (€)", min_value=0.0, value=0.0, step=0.01)
            with c8:
                taux_change = st.number_input("Taux change", min_value=0.0001, value=1.0, step=0.0001)

            # Calculs
            if mode_prix == "Prix unitaire → total auto":
                pu = prix_unitaire or 0.0
                total_ht_calc = round(quantite * pu, 2)
                pu_calc = pu
            else:
                th = total_ht_input or 0.0
                total_ht_calc = th
                pu_calc = round(th / quantite, 4) if quantite > 0 else 0.0

            tva_sug  = suggest_tva(type_op, categorie, devise)
            type_tva = st.selectbox("Type TVA", TYPES_TVA,
                                    index=TYPES_TVA.index(tva_sug),
                                    help=f"Suggestion : {tva_sug}")

            tva_rate       = 0.20 if type_tva in ("Collectée","Déductible","Autoliquidée") else 0.0
            tva_amt        = round(total_ht_calc * tva_rate, 2)
            total_ttc_calc = round(total_ht_calc + tva_amt + frais_envoi, 2)
            montant_orig   = round(total_ht_calc / taux_change, 2) if taux_change > 0 and devise != "EUR" else total_ht_calc

            if total_ht_calc > 0:
                sym = DEVISES_SYM.get(devise, devise)
                pu_str = f" · Prix unit. : <strong>{fmt_eur(pu_calc)}</strong>" if mode_prix == "Prix total → unitaire auto" else ""
                orig_str = f" · Montant original : <strong>{montant_orig:,.0f} {sym}</strong>" if devise != "EUR" else ""
                env_str  = f" · Frais envoi : <strong>{fmt_eur(frais_envoi)}</strong>" if frais_envoi > 0 else ""
                st.markdown(f"""
<div class="info-box">
Total HT : <strong>{fmt_eur(total_ht_calc)}</strong>{pu_str}
· TVA ({type_tva}) : <strong>{fmt_eur(tva_amt)}</strong>
{env_str}
· <strong>Total TTC : {fmt_eur(total_ttc_calc)}</strong>
{orig_str}
</div>""", unsafe_allow_html=True)

            info_comp = st.text_input("Info complémentaire", placeholder="N°commande, N°client, référence...")
            facture_file = st.file_uploader("📎 Facture (PDF, PNG, JPG)", type=["pdf","png","jpg","jpeg","webp"])

            if st.button("✓ Enregistrer l'opération", type="primary"):
                if not description:
                    st.error("La description est obligatoire.")
                else:
                    fac_data = facture_file.read() if facture_file else None
                    fac_nom  = facture_file.name  if facture_file else None
                    db_conn  = sqlite3.connect(DB_PATH, check_same_thread=False)
                    ensure_columns(db_conn)
                    _next_n = get_next_num(db_conn)
                    db_conn.execute("""INSERT INTO transactions
                        (annee,mois,date_op,ref_produit,info_process,description,
                         categorie,type_op,quantite,unite,prix_unitaire,type_tva,
                         total_ht,total_ttc,tva,devise,taux_change,montant_original,
                         payeur,beneficiaire,source,info_complementaire,
                         facture_data,facture_nom,frais_envoi,collection_op,
                         client_nom,client_email,client_tel,client_adresse,num_operation)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (date_op.year, date_op.month, str(date_op),
                         ref_produit, info_process, description,
                         categorie, type_op, quantite, unite, pu_calc, type_tva,
                         total_ht_calc, total_ttc_calc, tva_amt,
                         devise, taux_change, montant_orig,
                         payeur, beneficiaire, source or "", info_comp or "",
                         fac_data, fac_nom,
                         frais_envoi, col_op or "",
                         client_nom or "", client_email or "",
                         client_tel or "", client_adresse or "", _next_n))

                    # Sync stock
                    if ref_produit and unite in ("Article","Pièces","Mètre","Kg","Lot"):
                        _sync_stock(db_conn, ref_produit, type_op, quantite)

                    # Si Vente → créer commande automatiquement
                    cmd_num = None
                    if type_op == "Vente":
                        tv = type_vente.split(" — ")[0] if type_vente else "B2C"
                        cmd_num = auto_create_commande(
                            db_conn, date_op, ref_produit, info_process, description,
                            quantite, pu_calc, total_ttc_calc, devise,
                            client_nom, client_email, client_tel, client_adresse,
                            source or plateforme or "Opérations", tv)

                    db_conn.commit(); db_conn.close()

                    msg = "✓ Opération enregistrée."
                    if ref_produit: msg += f" Stock mis à jour ({ref_produit})."
                    if cmd_num:     msg += f" Commande {cmd_num} créée automatiquement."
                    st.success(msg)
                    st.rerun()

    # ── OCR ────────────────────────────────────────────────────────────────────
    if tab_ocr is not None:
        with tab_ocr:
            st.markdown('<div class="section-title">Scan OCR de facture</div>', unsafe_allow_html=True)
            st.markdown('<div class="info-box">Uploadez une photo ou PDF de facture. Claude extrait les informations et pré-remplit le formulaire.</div>', unsafe_allow_html=True)

            ocr_file = st.file_uploader("📸 Photo ou PDF", type=["pdf","png","jpg","jpeg","webp"], key="ocr_upload")

            if ocr_file:
                col_prev, col_res = st.columns([1,2])
                with col_prev:
                    if not ocr_file.name.lower().endswith(".pdf"):
                        st.image(ocr_file, use_container_width=True)
                    else:
                        st.info("PDF chargé.")
                    ocr_file.seek(0)

                with col_res:
                    if st.button("🔍 Analyser avec Claude", type="primary"):
                        with st.spinner("Analyse OCR..."):
                            ocr_file.seek(0)
                            img_bytes = ocr_file.read()
                            result = ocr_facture_claude(img_bytes, ocr_file.name)
                        if "error" in result:
                            st.error(f"Erreur OCR : {result['error']}")
                        else:
                            st.session_state["ocr_result"]   = result
                            st.session_state["ocr_filename"] = ocr_file.name
                            st.session_state["ocr_data"]     = img_bytes
                            st.success("✓ Analyse terminée — vérifiez et corrigez ci-dessous.")

            if "ocr_result" in st.session_state:
                r = st.session_state["ocr_result"]
                st.markdown('<div class="section-title">Données extraites — à valider</div>', unsafe_allow_html=True)

                with st.form("ocr_confirm"):
                    oc1,oc2,oc3 = st.columns(3)
                    with oc1:
                        try: ocr_date = date.fromisoformat(r.get("date") or date.today().isoformat())
                        except: ocr_date = date.today()
                        ocr_date_in = st.date_input("Date", value=ocr_date)
                        ocr_type    = st.selectbox("Type", TYPES_OP,
                            index=TYPES_OP.index(r.get("type_op","Achat")) if r.get("type_op") in TYPES_OP else 0)
                    with oc2:
                        ocr_cat = st.selectbox("Catégorie", CATEGORIES,
                            index=CATEGORIES.index(r.get("categorie_suggeree","Autre frais")) if r.get("categorie_suggeree") in CATEGORIES else 7)
                        ocr_dev = st.selectbox("Devise", DEVISES,
                            index=DEVISES.index(r.get("devise","EUR")) if r.get("devise") in DEVISES else 0)
                    with oc3:
                        sku_labels2, sku_refs2 = get_sku_list(conn)
                        ocr_sku = st.selectbox("SKU", ["— Saisie libre —"]+sku_labels2)
                        ref_ocr = sku_refs2[sku_labels2.index(ocr_sku)] if ocr_sku != "— Saisie libre —" else ""
                        ocr_src = st.text_input("Fournisseur", value=r.get("fournisseur",""))

                    ocr_desc = st.text_input("Description", value=r.get("description",""))

                    om1,om2,om3,om4 = st.columns(4)
                    with om1: ocr_ht  = st.number_input("Total HT (€)", value=float(r.get("total_ht") or 0), min_value=0.0)
                    with om2: ocr_tva = st.number_input("TVA (€)",       value=float(r.get("tva") or 0), min_value=0.0)
                    with om3: ocr_ttc = st.number_input("Total TTC (€)", value=float(r.get("total_ttc") or 0), min_value=0.0)
                    with om4: ocr_env = st.number_input("Frais envoi",   value=0.0, min_value=0.0)

                    ocr_tva_t = st.selectbox("Type TVA", TYPES_TVA,
                        index=TYPES_TVA.index(suggest_tva(r.get("type_op","Achat"), r.get("categorie_suggeree",""), r.get("devise","EUR"))))
                    ocr_info  = st.text_input("N° Facture", value=r.get("numero_facture","") or "")
                    ocr_benef = st.selectbox("Bénéficiaire", BENEFICIAIRES)
                    ocr_coll  = st.selectbox("Collection", get_collections_list(conn))

                    if st.form_submit_button("✓ Enregistrer l'opération OCR", type="primary"):
                        db_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                        ensure_columns(db_conn)
                        img_save  = st.session_state.get("ocr_data")
                        fname_save= st.session_state.get("ocr_filename")
                        db_conn.execute("""INSERT INTO transactions
                            (annee,mois,date_op,ref_produit,info_process,description,
                             categorie,type_op,quantite,unite,prix_unitaire,type_tva,
                             total_ht,total_ttc,tva,devise,taux_change,montant_original,
                             payeur,beneficiaire,source,info_complementaire,
                             facture_data,facture_nom,frais_envoi,collection_op)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (ocr_date_in.year, ocr_date_in.month, str(ocr_date_in),
                             ref_ocr, ocr_src, ocr_desc,
                             ocr_cat, ocr_type, 1.0, "Euros",
                             ocr_ht, ocr_tva_t,
                             ocr_ht, ocr_ttc + ocr_env, ocr_tva,
                             ocr_dev, 1.0, ocr_ht,
                             "Eastwood Studio", ocr_benef, ocr_src, ocr_info,
                             img_save, fname_save, ocr_env, ocr_coll or ""))
                        db_conn.commit(); db_conn.close()
                        for k in ["ocr_result","ocr_filename","ocr_data"]:
                            st.session_state.pop(k, None)
                        st.success("✓ Opération enregistrée depuis OCR."); st.rerun()

    conn.close()
