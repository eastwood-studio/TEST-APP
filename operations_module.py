# operations_module.py — v3.17 — 1777113689
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
DEVISES = ["EUR", "USD", "JPY"]
DEVISES_SYM = {"EUR":"€","USD":"$","JPY":"¥"}
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
        return ["", "Chapter I — Hunting & Fishing", "Chapter II — Le Souvenir"]


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


def _migrate_collections(conn):
    """Renomme les anciennes collections avec (AW26)/(SS26) dans la DB."""
    try:
        conn.execute("""UPDATE transactions SET collection_op='Chapter I — Hunting & Fishing'
            WHERE collection_op LIKE '%Hunting%' AND collection_op != 'Chapter I — Hunting & Fishing'""")
        conn.execute("""UPDATE transactions SET collection_op='Chapter II — Le Souvenir'
            WHERE collection_op LIKE '%Souvenir%' AND collection_op != 'Chapter II — Le Souvenir'""")
        conn.commit()
    except Exception:
        pass


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
    """Renumérotation complète et continue par ordre chronologique.
    Appelée au chargement ET après chaque suppression.
    Garantit que les numéros sont toujours 1, 2, 3... sans trou.
    """
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
    """Prochain numéro = total actuel + 1 (après renumérotation)."""
    try:
        row = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
        return (row[0] or 0) + 1
    except Exception:
        return 1


def fmt_date_fr(d):
    """Convertit YYYY-MM-DD en JJ-MM-YYYY."""
    if not d: return "—"
    try:
        parts = str(d).strip()[:10].split("-")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return str(d)


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
    """Met à jour le stock ET synchronise le statut du produit dans le catalogue."""
    row = conn.execute("SELECT * FROM stock WHERE ref=?", (ref_produit,)).fetchone()
    if not row:
        # Créer une entrée stock si absente
        try:
            conn.execute("""INSERT OR IGNORE INTO stock (ref, description, type_produit, qte_stock)
                VALUES (?,?,?,?)""", (ref_produit, ref_produit, "Produit fini", 0))
        except Exception:
            pass

    if type_op == "Vente":
        conn.execute("""UPDATE stock SET
            qte_vendue=qte_vendue+?,
            qte_stock=MAX(0,qte_stock-?)
            WHERE ref=?""", (quantite, quantite, ref_produit))
    elif type_op in ("Achat","Achat perso"):
        conn.execute("UPDATE stock SET qte_stock=qte_stock+? WHERE ref=?",
                     (quantite, ref_produit))
    elif type_op == "Utilisation":
        conn.execute("""UPDATE stock SET
            qte_utilisee=qte_utilisee+?,
            qte_stock=MAX(0,qte_stock-?)
            WHERE ref=?""", (quantite, quantite, ref_produit))
    conn.commit()

    # ── Sync statut produit dans le catalogue ─────────────────────────────────
    try:
        qte_new = conn.execute(
            "SELECT qte_stock FROM stock WHERE ref=?", (ref_produit,)
        ).fetchone()
        if qte_new is not None:
            qte_val = float(qte_new[0] or 0)
            if qte_val <= 0:
                # Passer en Out of stock
                conn.execute("""UPDATE products SET statut='Out of stock'
                    WHERE ref=? AND statut IN ('Disponible','Sample & Testing')""",
                    (ref_produit,))
            else:
                # Remettre en Disponible si était Out of stock
                conn.execute("""UPDATE products SET statut='Disponible'
                    WHERE ref=? AND statut='Out of stock'""",
                    (ref_produit,))
            conn.commit()
    except Exception:
        pass

def _deduct_linked_stock(conn, ref_produit, type_op, quantite, source_stock="Eastwood"):
    """
    Déduit automatiquement du stock tous les composants/MP/packaging liés à un produit.
    
    - type_op="Vente" ou "Utilisation" : déduit produit fini + packaging retail
    - type_op="Achat" (sample) : déduit les MP/composants liés
    - type_op="Achat" (prod) + source_stock="Eastwood" : déduit MP/composants liés
    - type_op="Achat" (prod) + source_stock="Atelier" : ne déduit rien des MP
    """
    if not ref_produit:
        return []

    deduits = []  # Liste des déductions effectuées pour affichage

    # Trouver l'id du produit
    prod_row = conn.execute("SELECT id, nom FROM products WHERE ref=?", (ref_produit,)).fetchone()
    if not prod_row:
        return deduits
    prod_id = prod_row[0]

    if type_op in ("Vente", "Utilisation"):
        # ── Déduire les composants/MP liés (par la quantité vendue) ──────────
        try:
            comps = conn.execute("""
                SELECT nom_exact, ref_stock, quantite, unite, categorie_comp
                FROM product_components WHERE product_id=?
            """, (prod_id,)).fetchall()
            for comp in comps:
                c_ref = comp[1]
                c_qte = float(comp[2] or 0) * float(quantite)
                if c_ref and c_qte > 0:
                    conn.execute("UPDATE stock SET qte_stock=MAX(0,qte_stock-?) WHERE ref=?",
                                 (c_qte, c_ref))
                    deduits.append(f"{comp[0]} : −{c_qte} {comp[3] or ''}")
        except Exception:
            pass

        # ── Déduire le packaging retail lié au produit ────────────────────────
        try:
            # Récupérer le packaging_retail_id depuis product_costs
            pkg_row = conn.execute(
                "SELECT packaging_retail_id FROM product_costs WHERE product_id=?", (prod_id,)
            ).fetchone()
            if pkg_row and pkg_row[0]:
                pkg_items = conn.execute("""
                    SELECT nom_item, ref_stock, quantite FROM packaging_items
                    WHERE packaging_type_id=?
                """, (int(pkg_row[0]),)).fetchall()
                for pi in pkg_items:
                    pi_ref = pi[1]
                    pi_qte = float(pi[2] or 0) * float(quantite)
                    if pi_ref and pi_qte > 0:
                        conn.execute("UPDATE stock SET qte_stock=MAX(0,qte_stock-?) WHERE ref=?",
                                     (pi_qte, pi_ref))
                        deduits.append(f"Packaging — {pi[0]} : −{pi_qte}")
        except Exception:
            pass

    elif type_op in ("Achat", "Achat perso") and source_stock == "Eastwood":
        # ── Achat depuis stock Eastwood : déduire les MP/composants ──────────
        try:
            comps = conn.execute("""
                SELECT nom_exact, ref_stock, quantite, unite
                FROM product_components WHERE product_id=?
                AND categorie_comp IN ('MP Principale (Main Fabric)','MP Secondaire','Doublure','Broderie','Zip','Bouton','Composant','Autre')
            """, (prod_id,)).fetchall()
            for comp in comps:
                c_ref = comp[1]
                c_qte = float(comp[2] or 0) * float(quantite)
                if c_ref and c_qte > 0:
                    conn.execute("UPDATE stock SET qte_stock=MAX(0,qte_stock-?) WHERE ref=?",
                                 (c_qte, c_ref))
                    deduits.append(f"{comp[0]} : −{c_qte} {comp[3] or ''}")
        except Exception:
            pass

    conn.commit()
    return deduits



def page_operations(can_fn, DB_PATH, fmt_eur_fn=None):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    ensure_columns(conn)
    if fmt_eur_fn is None:
        fmt_eur_fn = fmt_eur

    st.markdown("### Opérations")

    # ops_write = finance_write → Jules ; ops_read seul → Corentin/Alexis (lecture seule)
    _can_write = can_fn("finance_write")
    _can_read_only = can_fn("ops_read") and not _can_write

    _tabs = ["📋 Historique"]
    if _can_write:
        _tabs += ["📁 Factures", "➕ Nouvelle opération", "🔍 OCR — Scan facture", "📥 Import en masse"]
    tab_objs = st.tabs(_tabs)
    idx = 0
    tab_hist = tab_objs[idx]; idx += 1
    tab_fac  = tab_objs[idx] if _can_write else None
    if _can_write: idx += 1
    tab_new  = tab_objs[idx] if _can_write else None
    if _can_write: idx += 1
    tab_ocr  = tab_objs[idx] if _can_write else None
    if _can_write: idx += 1
    tab_imp_ops = tab_objs[idx] if _can_write else None

    # ── HISTORIQUE ─────────────────────────────────────────────────────────────
    with tab_hist:
        if _can_read_only:
            # Lecture seule : tableau global uniquement, pas de filtres ni détail
            f_periode = "Cette année"; f_type = "Tous"; f_cat = "Toutes"
            f_coll = "Toutes"; f_dev = "Toutes"; f_tva = "Tous"; f_srch = ""
            d_debut_custom = d_fin_custom = None
        else:
            # Filtres complets pour Jules
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
            # KPIs supprimés

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

            # Toujours renuméroter au chargement pour garantir la cohérence chronologique
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
                "total_ht","devise","frais_envoi","type_tva","total_ttc","tva",
                "collection_op","payeur","beneficiaire","info_complementaire"
            ]
            if "date_op" in df_display.columns:
                df_display["date_op"] = df_display["date_op"].apply(fmt_date_fr)
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
            df_styled = df_display[existing_cols].rename(columns=cols_rename)

            # Surligner en rouge les cellules avec infos manquantes
            _CHAMPS_OBLIGATOIRES = {
                "Catégorie": lambda v: str(v or "").strip() not in ("","None","nan"),
                "Type TVA":  lambda v: str(v or "").strip() not in ("","None","nan"),
                "Description":lambda v: str(v or "").strip() not in ("","None","nan"),
                "Type":      lambda v: str(v or "").strip() not in ("","None","nan"),
            }
            def _highlight_missing(df):
                styles = pd.DataFrame("", index=df.index, columns=df.columns)
                for col, check_fn in _CHAMPS_OBLIGATOIRES.items():
                    if col in df.columns:
                        styles[col] = df[col].apply(
                            lambda v: "" if check_fn(v) else "background-color:#fde8e8;color:#c1440e;font-weight:600;"
                        )
                return styles
            try:
                st.dataframe(
                    df_styled.style.apply(_highlight_missing, axis=None),
                    use_container_width=True, hide_index=True
                )
            except Exception:
                st.dataframe(df_styled, use_container_width=True, hide_index=True)


            # Téléchargement factures par ligne
            if not _can_read_only:
                df_with_fac = df_ops[df_ops["facture_data"].notna()] if "facture_data" in df_ops.columns else pd.DataFrame()
            # Factures : section compacte
            if not df_with_fac.empty:
                st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#8a7968;text-transform:uppercase;letter-spacing:.12em;margin:6px 0 4px;">📎 {len(df_with_fac)} facture(s) attachée(s)</div>', unsafe_allow_html=True)
                fac_cols = st.columns(min(len(df_with_fac), 6))
                for i_fc, (_, frow) in enumerate(df_with_fac.iterrows()):
                    if i_fc < 6:
                        num = frow.get("num_operation","?")
                        fac_bytes = bytes(frow["facture_data"])
                        fac_name = frow.get("facture_nom") or f"facture_op{num}.pdf"
                        with fac_cols[i_fc]:
                            st.download_button(
                                f"📄 N°{num}",
                                data=fac_bytes,
                                file_name=fac_name,
                                mime="application/pdf",
                                key=f"dl_fac_hist_{frow['id']}_{i_fc}",
                                help=f"{str(frow.get('description',''))[:40]}"
                            )

            # ── Modifier une ligne : Jules uniquement ─────────────────────────
            if _can_write and not _can_read_only:
                with st.expander("✏️ Modifier / Supprimer une opération"):
                    search_num = st.text_input("N° d'opération", placeholder="ex: 3", key="edit_ops_num")
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
                        me1, me2, me3 = st.columns(3)
                        with me1:
                            e_date  = st.date_input("Date",
                                value=date.fromisoformat(str(row_edit["date_op"])[:10]))
                            e_type  = st.selectbox("Type", TYPES_OP,
                                index=TYPES_OP.index(row_edit["type_op"]) if row_edit["type_op"] in TYPES_OP else 0)
                            e_cat   = st.selectbox("Catégorie", CATEGORIES,
                                index=CATEGORIES.index(row_edit["categorie"]) if row_edit.get("categorie") in CATEGORIES else 0)
                            e_sku   = st.text_input("SKU", value=str(row_edit.get("ref_produit","") or ""))
                            e_art   = st.text_input("Article", value=str(row_edit.get("article","") or ""))
                        with me2:
                            e_desc  = st.text_input("Description", value=str(row_edit.get("description","") or ""))
                            e_qte   = st.number_input("Quantité", value=float(row_edit.get("quantite",1) or 1), min_value=0.0)
                            e_unit  = st.selectbox("Unité", UNITES,
                                index=UNITES.index(row_edit["unite"]) if row_edit.get("unite") in UNITES else 0)
                            e_ht    = st.number_input("Total HT", value=float(row_edit.get("total_ht",0) or 0), min_value=0.0)
                            e_tva_t = st.selectbox("Type TVA", TYPES_TVA,
                                index=TYPES_TVA.index(row_edit["type_tva"]) if row_edit.get("type_tva") in TYPES_TVA else 0)
                        with me3:
                            e_dev   = st.selectbox("Devise", DEVISES,
                                index=DEVISES.index(row_edit["devise"]) if row_edit.get("devise") in DEVISES else 0)
                            e_fenv  = st.number_input("Frais envoi", value=float(row_edit.get("frais_envoi",0) or 0), min_value=0.0)
                            e_coll  = st.text_input("Collection", value=str(row_edit.get("collection_op","") or ""))
                            e_pay   = st.text_input("Payeur", value=str(row_edit.get("payeur","") or ""))
                            e_ben   = st.text_input("Bénéficiaire", value=str(row_edit.get("beneficiaire","") or ""))
                        e_info  = st.text_input("Info complémentaire", value=str(row_edit.get("info_complementaire","") or ""))

                        # ── Facture / Lien Drive ──────────────────────────────
                        st.markdown('<div style="font-family:DM Mono,monospace;font-size:9px;color:#8a7968;text-transform:uppercase;letter-spacing:.12em;margin:8px 0 4px;">Facture</div>', unsafe_allow_html=True)
                        fac_col1, fac_col2 = st.columns(2)
                        with fac_col1:
                            # Afficher la facture existante
                            _cur_fac_nom = str(row_edit.get("facture_nom","") or "")
                            if _cur_fac_nom:
                                st.markdown(f'<div style="font-size:11px;color:#395f30;padding:4px 0;">📄 {_cur_fac_nom}</div>', unsafe_allow_html=True)
                                try:
                                    _cur_fac_bytes = bytes(row_edit["facture_data"]) if row_edit.get("facture_data") is not None else None
                                    if _cur_fac_bytes:
                                        st.download_button("⬇ Télécharger", _cur_fac_bytes,
                                            file_name=_cur_fac_nom, key=f"dl_cur_fac_{sel_id}")
                                except Exception:
                                    pass
                            e_fac_file = st.file_uploader(
                                "Remplacer / Ajouter une facture (PDF, image)",
                                type=["pdf","jpg","jpeg","png"],
                                key=f"fac_upload_{sel_id}"
                            )
                        with fac_col2:
                            e_drive_link = st.text_input(
                                "Lien Google Drive / facture",
                                value=str(row_edit.get("source","") or ""),
                                placeholder="https://drive.google.com/file/...",
                                key=f"drive_link_{sel_id}"
                            )
                            if e_drive_link and e_drive_link.startswith("http"):
                                st.markdown(f'<a href="{e_drive_link}" target="_blank" style="font-family:DM Mono,monospace;font-size:10px;color:#7b506f;">↗ Ouvrir le document</a>', unsafe_allow_html=True)

                        save_col, del_col = st.columns(2)
                        with save_col:
                            if st.form_submit_button("💾 Enregistrer", type="primary"):
                                tva_rate = 0.20 if e_tva_t in ("Collectée","Déductible","Autoliquidée") else 0.0
                                tva_amt  = round(e_ht * tva_rate, 2)
                                ttc_new  = round(e_ht + tva_amt + e_fenv, 2)

                                # Migrer les colonnes manquantes silencieusement
                                for _mc, _md in [
                                    ("article",          "TEXT DEFAULT ''"),
                                    ("frais_envoi",      "REAL DEFAULT 0"),
                                    ("collection_op",    "TEXT DEFAULT ''"),
                                    ("payeur",           "TEXT DEFAULT ''"),
                                    ("beneficiaire",     "TEXT DEFAULT ''"),
                                    ("info_complementaire","TEXT DEFAULT ''"),
                                    ("ref_produit",      "TEXT DEFAULT ''"),
                                    ("source",           "TEXT DEFAULT ''"),
                                ]:
                                    try:
                                        conn.execute(f"ALTER TABLE transactions ADD COLUMN {_mc} {_md}")
                                        conn.commit()
                                    except Exception:
                                        pass

                                # UPDATE uniquement les colonnes qui existent
                                _existing_cols = [r[1] for r in conn.execute(
                                    "PRAGMA table_info(transactions)").fetchall()]
                                _set_parts = [
                                    "date_op=?", "annee=?", "mois=?", "type_op=?", "categorie=?",
                                    "description=?", "total_ht=?", "tva=?", "total_ttc=?",
                                    "type_tva=?", "devise=?",
                                ]
                                _vals = [str(e_date), e_date.year, e_date.month, e_type, e_cat,
                                         e_desc, e_ht, tva_amt, ttc_new, e_tva_t, e_dev]

                                for col, val in [
                                    ("ref_produit",       e_sku),
                                    ("article",           e_art),
                                    ("quantite",          e_qte),
                                    ("unite",             e_unit),
                                    ("frais_envoi",       e_fenv),
                                    ("collection_op",     e_coll),
                                    ("payeur",            e_pay),
                                    ("beneficiaire",      e_ben),
                                    ("info_complementaire", e_info),
                                    ("source",            e_drive_link),
                                ]:
                                    if col in _existing_cols:
                                        _set_parts.append(f"{col}=?")
                                        _vals.append(val)

                                # Facture uploadée
                                if e_fac_file is not None:
                                    _fac_bytes = e_fac_file.read()
                                    for col, val in [("facture_data", _fac_bytes), ("facture_nom", e_fac_file.name)]:
                                        if col in _existing_cols:
                                            _set_parts.append(f"{col}=?")
                                            _vals.append(val)

                                _vals.append(sel_id)
                                conn.execute(
                                    f"UPDATE transactions SET {', '.join(_set_parts)} WHERE id=?",
                                    _vals)
                                conn.commit()
                                st.success("✓ Opération mise à jour."); st.rerun()
                        with del_col:
                            if st.form_submit_button("🗑 Supprimer cette opération"):
                                conn.execute("DELETE FROM transactions WHERE id=?", (sel_id,))
                                conn.commit()
                                assign_operation_numbers(conn)  # Renuméroter
                                st.success("✓ Supprimée."); st.rerun()


            # ── Suppression en masse par plage de numéros ─────────────────────
            if _can_write:
                with st.expander("🗑 Supprimer plusieurs opérations (par plage de N°) ou toutes"):
                    st.markdown("""
<div style="background:#fdf6ec;border-left:3px solid #c9800a;padding:8px 12px;font-size:11px;margin-bottom:10px;">
⚠ Cette action est <strong>irréversible</strong>. Les opérations supprimées ne pourront pas être récupérées.
</div>""", unsafe_allow_html=True)

                    # Infos sur les numéros disponibles
                    if not df_ops.empty and "num_operation" in df_ops.columns:
                        n_min = int(df_ops["num_operation"].min() or 1)
                        n_max = int(df_ops["num_operation"].max() or 1)
                        st.caption(f"Numéros d'opérations disponibles : N°{n_min} → N°{n_max} ({len(df_ops)} opérations affichées)")

                    # Option tout supprimer
                    all_total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
                    if all_total > 0:
                        st.markdown("---")
                        st.markdown(f"**Tout supprimer** — {all_total} opération(s) en base")
                        confirm_all = st.checkbox(f"Je confirme la suppression de TOUTES les {all_total} opérations", key="confirm_all_del")
                        if confirm_all:
                            if st.button("🚨 SUPPRIMER TOUTES LES OPÉRATIONS", key="btn_del_all", type="primary"):
                                conn.execute("DELETE FROM transactions")
                                conn.commit()
                                st.success(f"✓ {all_total} opérations supprimées. La liste est vide.")
                                st.rerun()
                        st.markdown("---")

                    bulk_c1, bulk_c2 = st.columns(2)
                    with bulk_c1:
                        del_from = st.number_input("Du N°", min_value=1, value=1, step=1, key="del_bulk_from")
                    with bulk_c2:
                        del_to = st.number_input("Au N°", min_value=1, value=1, step=1, key="del_bulk_to")

                    # Aperçu des opérations qui seront supprimées
                    if del_from <= del_to:
                        preview_del = conn.execute("""
                            SELECT num_operation, date_op, description, total_ht
                            FROM transactions
                            WHERE num_operation >= ? AND num_operation <= ?
                            ORDER BY num_operation
                        """, (int(del_from), int(del_to))).fetchall()

                        if preview_del:
                            st.markdown(f"**{len(preview_del)} opération(s) concernée(s) :**")
                            for row in preview_del[:10]:
                                st.markdown(
                                    f'<div style="font-size:11px;padding:2px 0;border-bottom:0.5px solid #f0ece4;">'
                                    f'N°{row[0]} · {row[1]} · {str(row[2])[:40]} · {row[3]} €'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )
                            if len(preview_del) > 10:
                                st.caption(f"... et {len(preview_del)-10} autres")

                            # Double confirmation
                            confirm_del = st.checkbox(
                                f"Je confirme la suppression définitive de {len(preview_del)} opération(s)",
                                key="confirm_bulk_del"
                            )
                            if confirm_del:
                                if st.button(
                                    f"⚠ SUPPRIMER {len(preview_del)} OPÉRATION(S) DÉFINITIVEMENT",
                                    type="primary", key="btn_bulk_del"
                                ):
                                    conn.execute("""
                                        DELETE FROM transactions
                                        WHERE num_operation >= ? AND num_operation <= ?
                                    """, (int(del_from), int(del_to)))
                                    conn.commit()
                                    assign_operation_numbers(conn)  # Renuméroter sans trous
                                    st.success(f"✓ {len(preview_del)} opération(s) supprimée(s). Numéros réattribués.")
                                    st.rerun()
                        else:
                            st.info(f"Aucune opération trouvée entre N°{del_from} et N°{del_to}.")
                    else:
                        st.warning("Le numéro de début doit être ≤ au numéro de fin.")

            # ── Modification en masse par sélection de numéros ─── Jules only ──
            if _can_write and not _can_read_only:
                with st.expander("✏️ Modifier plusieurs opérations en masse"):
                    st.markdown("""
<div class="info-box">
Sélectionnez les numéros à modifier. Syntaxe : <code>1, 25-29, 56-79, 102, 107-119</code><br>
Entrez les plages séparées par des virgules. Seuls les champs remplis ci-dessous seront modifiés.
</div>""", unsafe_allow_html=True)

                    bulk_sel_str = st.text_input(
                        "Numéros d'opérations",
                        placeholder="ex: 1, 25-29, 56-79, 102, 107-119",
                        key="bulk_edit_sel"
                    )

                    # Parser la sélection
                    def parse_nums(s):
                        nums = set()
                        for part in s.replace(" ","").split(","):
                            if not part: continue
                            if "-" in part:
                                try:
                                    a, b = part.split("-", 1)
                                    nums.update(range(int(a), int(b)+1))
                                except Exception: pass
                            else:
                                try: nums.add(int(part))
                                except Exception: pass
                        return sorted(nums)

                    selected_nums = parse_nums(bulk_sel_str) if bulk_sel_str.strip() else []

                    if selected_nums:
                        # Aperçu des opérations concernées
                        placeholders = ",".join("?" * len(selected_nums))
                        preview_bulk = conn.execute(f"""
                            SELECT num_operation, date_op, description, categorie, collection_op, total_ht
                            FROM transactions WHERE num_operation IN ({placeholders})
                            ORDER BY num_operation
                        """, selected_nums).fetchall()

                        if preview_bulk:
                            st.markdown(f"**{len(preview_bulk)} opération(s) sélectionnée(s) :**")
                            for row in preview_bulk[:8]:
                                st.markdown(
                                    f'<div style="font-size:11px;padding:2px 0;border-bottom:0.5px solid #f0ece4;">'
                                    f'N°{row[0]} · {row[1]} · {str(row[2])[:35]} · {row[3]} · {row[5]} €'
                                    f'</div>', unsafe_allow_html=True)
                            if len(preview_bulk) > 8:
                                st.caption(f"... et {len(preview_bulk)-8} autres")

                            st.markdown("**Champs à modifier** — laisser vide = ne pas modifier :")
                            bm1, bm2, bm3 = st.columns(3)
                            with bm1:
                                bm_coll = st.selectbox("Collection",
                                    ["— Ne pas modifier —",
                                     "Chapter I — Hunting & Fishing",
                                     "Chapter II — Le Souvenir", "Général", "Autre"],
                                    key="bm_coll")
                                bm_type = st.selectbox("Type opération",
                                    ["— Ne pas modifier —"] + TYPES_OP, key="bm_type")
                                bm_cat  = st.selectbox("Catégorie",
                                    ["— Ne pas modifier —"] + CATEGORIES, key="bm_cat")
                            with bm2:
                                bm_payeur = st.text_input("Payeur", placeholder="Laisser vide = ne pas modifier", key="bm_pay")
                                bm_bene   = st.text_input("Bénéficiaire", placeholder="Laisser vide = ne pas modifier", key="bm_ben")
                                bm_devise = st.selectbox("Devise",
                                    ["— Ne pas modifier —"] + DEVISES, key="bm_dev")
                            with bm3:
                                bm_tva  = st.selectbox("Type TVA",
                                    ["— Ne pas modifier —"] + TYPES_TVA, key="bm_tva")
                                bm_source = st.text_input("Source", placeholder="Laisser vide = ne pas modifier", key="bm_src")
                                bm_info   = st.text_input("Info complémentaire", placeholder="Laisser vide = ne pas modifier", key="bm_info")
                                bm_desc   = st.text_input("Description", placeholder="Laisser vide = ne pas modifier", key="bm_desc")
                                bm_art    = st.text_input("Article", placeholder="Laisser vide = ne pas modifier", key="bm_art")

                            if st.button(f"✓ Appliquer à {len(preview_bulk)} opération(s)", type="primary", key="btn_bulk_edit"):
                                # Construire le SET dynamiquement
                                set_parts = []; set_vals = []
                                if bm_coll  != "— Ne pas modifier —": set_parts.append("collection_op=?");       set_vals.append(bm_coll)
                                if bm_type  != "— Ne pas modifier —": set_parts.append("type_op=?");             set_vals.append(bm_type)
                                if bm_cat   != "— Ne pas modifier —": set_parts.append("categorie=?");           set_vals.append(bm_cat)
                                if bm_devise!= "— Ne pas modifier —": set_parts.append("devise=?");              set_vals.append(bm_devise)
                                if bm_tva   != "— Ne pas modifier —": set_parts.append("type_tva=?");            set_vals.append(bm_tva)
                                if bm_payeur.strip():                  set_parts.append("payeur=?");              set_vals.append(bm_payeur.strip())
                                if bm_bene.strip():                    set_parts.append("beneficiaire=?");        set_vals.append(bm_bene.strip())
                                if bm_source.strip():                  set_parts.append("source=?");              set_vals.append(bm_source.strip())
                                if bm_info.strip():                    set_parts.append("info_complementaire=?"); set_vals.append(bm_info.strip())
                                if bm_desc.strip():                    set_parts.append("description=?");         set_vals.append(bm_desc.strip())
                                if bm_art.strip():                     set_parts.append("article=?");             set_vals.append(bm_art.strip())

                                if set_parts:
                                    conn.execute(
                                        f"UPDATE transactions SET {', '.join(set_parts)} "
                                        f"WHERE num_operation IN ({placeholders})",
                                        set_vals + selected_nums
                                    )
                                    conn.commit()
                                    st.success(f"✓ {len(preview_bulk)} opération(s) modifiée(s).")
                                    st.rerun()
                                else:
                                    st.warning("Aucun champ sélectionné à modifier.")
                        else:
                            st.info(f"Aucune opération trouvée pour : {bulk_sel_str}")

            # Export
            buf = io.BytesIO()
            df_ops.drop(columns=["facture_data"], errors="ignore").to_csv(buf, index=False, encoding="utf-8-sig")
            st.download_button("⬇ Export CSV", buf.getvalue(),
                file_name=f"operations_{date.today()}.csv",
                mime="text/csv")

    # ── FACTURES ───────────────────────────────────────────────────────────────
    if tab_fac is not None:
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
                            key=f"dl_fac_tab_{row['id']}")
                    if _can_write:
                        if st.button("🗑", key=f"del_fac_{row['id']}", help="Supprimer cette facture"):
                            conn.execute("UPDATE transactions SET facture_data=NULL, facture_nom=NULL WHERE id=?",
                                         (int(row["id"]),))
                            conn.commit()
                            st.success("✓ Facture supprimée.")
                            st.rerun()

    # ── NOUVELLE OPÉRATION ─────────────────────────────────────────────────────
    if tab_new is not None:
        with tab_new:
            st.markdown('<div class="section-title">Nouvelle opération</div>', unsafe_allow_html=True)

            # ── Ligne 1 : Date / Type / Devise / Catégorie ─────────────────────
            r1a,r1b,r1c,r1d = st.columns(4)
            with r1a: date_op   = st.date_input("Date", value=date.today())
            with r1b: type_op   = st.selectbox("Type d'opération", TYPES_OP)
            with r1c: devise    = st.selectbox("Devise", DEVISES)
            with r1d: categorie = st.selectbox("Catégorie *", ["— Sélectionner —"] + CATEGORIES)

            # Sous-catégorie dynamique depuis l'inventaire
            try:
                _stk_types = conn.execute(
                    "SELECT DISTINCT type_produit FROM stock WHERE type_produit IS NOT NULL ORDER BY type_produit"
                ).fetchall()
                _subcats = ["— Aucune —"] + [r[0] for r in _stk_types if r[0]]
            except Exception:
                _subcats = ["— Aucune —"]
            sous_categorie = st.selectbox("Sous-catégorie (inventaire)", _subcats, key="new_op_subcat")
            if sous_categorie == "— Aucune —": sous_categorie = ""

            # Collection
            collections = get_collections_list(conn)
            col_op = st.selectbox("Collection", collections, key="new_op_coll_sel")
            description = st.text_area("Description *", height=55, placeholder="Détail de l'opération...")

            # Initialiser les variables communes
            articles_vente = []; articles_achat_mp = []
            info_process = ""; ref_produit = ""
            client_nom = client_email = client_tel = client_adresse = ""
            type_vente = plateforme = ""
            payeur = "Eastwood Studio"; beneficiaire = "Eastwood Studio"

            # ══ VENTE ══════════════════════════════════════════════════════════
            if type_op == "Vente":
                st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:{EW_B};text-transform:uppercase;letter-spacing:.15em;margin:8px 0 4px;">Client</div>', unsafe_allow_html=True)

                # Mode client : nouveau ou existant
                _client_mode = st.radio("Client", ["Nouveau client", "Client existant"], horizontal=True, key="vente_client_mode")
                client_nom = client_email = client_tel = client_adresse = ""

                if _client_mode == "Client existant":
                    try:
                        _df_cts = __import__("pandas").read_sql(
                            "SELECT nom, email, telephone, adresse FROM contacts ORDER BY nom",
                            conn)
                        _ct_opts = ["— Sélectionner —"] + [
                            f"{r['nom']} ({r['email'] or r['telephone'] or '—'})"
                            for _, r in _df_cts.iterrows()
                        ]
                        _ct_sel = st.selectbox("Rechercher un contact", _ct_opts, key="vente_ct_sel")
                        if _ct_sel != "— Sélectionner —":
                            _ct_idx = _ct_opts.index(_ct_sel) - 1
                            _ct_row = _df_cts.iloc[_ct_idx]
                            client_nom     = str(_ct_row.get("nom","") or "")
                            client_email   = str(_ct_row.get("email","") or "")
                            client_tel     = str(_ct_row.get("telephone","") or "")
                            client_adresse = str(_ct_row.get("adresse","") or "")
                            st.markdown(
                                f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#395f30;margin:3px 0;">'
                                f'✓ {client_nom} · {client_email} · {client_tel}</div>',
                                unsafe_allow_html=True)
                    except Exception:
                        st.info("Aucun contact trouvé.")
                else:
                    cv1,cv2 = st.columns(2)
                    with cv1:
                        client_nom   = st.text_input("Nom client")
                        client_email = st.text_input("Email client")
                    with cv2:
                        client_tel    = st.text_input("Téléphone")
                        client_adresse= st.text_input("Adresse")

                cv_last = st.columns(2)
                with cv_last[0]: type_vente = st.selectbox("Type de vente", ["B2C — Retail","B2B — Wholesale"])
                with cv_last[1]: plateforme = st.text_input("Plateforme / Source", placeholder="Shopify, DM Instagram...")
                payeur = "Client"; beneficiaire = "Eastwood Studio"

                st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:{EW_B};text-transform:uppercase;letter-spacing:.15em;margin:10px 0 4px;">Articles vendus</div>', unsafe_allow_html=True)
                try:
                    _prods_v = conn.execute("SELECT ref, nom, couleurs FROM products ORDER BY collection, nom").fetchall()
                    _popts_v = ["— Saisie libre —"] + [f"{p[1]}{'—'+p[2] if p[2] else ''} ({p[0]})" for p in _prods_v]
                    _pref_v  = {"— Saisie libre —":""} | {f"{p[1]}{'—'+p[2] if p[2] else ''} ({p[0]})": p[0] for p in _prods_v}
                    _pnom_v  = {"— Saisie libre —":""} | {f"{p[1]}{'—'+p[2] if p[2] else ''} ({p[0]})": p[1] for p in _prods_v}
                except Exception:
                    _popts_v=["— Saisie libre —"]; _pref_v={}; _pnom_v={}

                _TAILLES = ["— Sans taille —","XS","S","1(S)","M","2(M)","L","3(L)","XL","4(XL)","XXL","Unique"]
                n_art_v = st.number_input("Nombre d'articles", min_value=1, max_value=8, value=1, step=1, key="vente_n_art")
                for _vi in range(int(n_art_v)):
                    st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:8px;color:{EW_B};margin:4px 0 1px;">Article {_vi+1}</div>', unsafe_allow_html=True)
                    _va1,_va2,_va3 = st.columns([4,1,1])
                    with _va1:
                        _vsel = st.selectbox("Produit", _popts_v, key=f"vente_art_{_vi}")
                        if _vsel != "— Saisie libre —":
                            _vref = _pref_v.get(_vsel,""); _vnom = _pnom_v.get(_vsel,"")
                            st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#395f30;">✓ SKU : {_vref}</div>', unsafe_allow_html=True)
                        else:
                            _vref = st.text_input("SKU libre", key=f"vente_ref_{_vi}"); _vnom = _vref
                    with _va2: _vqte = st.number_input("Qté", min_value=1, value=1, step=1, key=f"vente_qte_{_vi}")
                    with _va3: _vtaille = st.selectbox("Taille *", _TAILLES, key=f"vente_taille_{_vi}")
                    articles_vente.append({"ref":_vref,"nom":_vnom,"qte":_vqte,"taille":_vtaille})

                _arts_f = [a for a in articles_vente if a.get("ref") or a.get("nom")]
                if _arts_f:
                    ref_produit  = _arts_f[0]["ref"]
                    info_process = " + ".join(f"{a['qte']}× {a['nom']}{(' T.'+a['taille']) if a.get('taille') and a['taille']!='— Sans taille —' else ''}" for a in _arts_f if a.get("nom"))
                    st.markdown(f'<div style="font-size:10px;color:{EW_B};margin:4px 0;font-family:DM Mono,monospace;">{info_process}</div>', unsafe_allow_html=True)

            # ══ ACHAT MP / COMPOSANT ═══════════════════════════════════════════
            elif type_op in ("Achat","Achat perso") and categorie in ("Matières premières","Composants","Composant","Matière première"):
                st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:{EW_B};text-transform:uppercase;letter-spacing:.15em;margin:10px 0 4px;">Matières / Composants achetés</div>', unsafe_allow_html=True)
                try:
                    _stk_mp = conn.execute("SELECT ref, description, type_produit FROM stock WHERE type_produit IN ('Matière première','Composant','MP','Composants') ORDER BY description").fetchall()
                    _mp_opts = ["— Nouvelle MP/Composant —"] + [f"{s[1] or s[0]} ({s[2]})" for s in _stk_mp]
                    _mp_refs = {f"{s[1] or s[0]} ({s[2]})": s[0] for s in _stk_mp}
                    _mp_noms = {f"{s[1] or s[0]} ({s[2]})": s[1] or s[0] for s in _stk_mp}
                except Exception:
                    _mp_opts=["— Nouvelle MP/Composant —"]; _mp_refs={}; _mp_noms={}

                n_mp = st.number_input("Nombre de matières/composants", min_value=1, max_value=10, value=1, step=1, key="achat_n_mp")
                for _mi in range(int(n_mp)):
                    st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:8px;color:{EW_B};margin:4px 0 1px;">MP / Composant {_mi+1}</div>', unsafe_allow_html=True)
                    _ma1,_ma2,_ma3 = st.columns([4,1,1])
                    with _ma1: _msel = st.selectbox("MP / Composant", _mp_opts, key=f"mp_art_{_mi}")
                    with _ma2: _mqte = st.number_input("Qté", min_value=0.0, step=0.5, key=f"mp_qte_{_mi}")
                    with _ma3: _munit = st.selectbox("Unité", ["Mètre","Pièces","kg","g","m²","Lot"], key=f"mp_unit_{_mi}")
                    if _msel == "— Nouvelle MP/Composant —":
                        st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#c9800a;">⚠ Nouvelle MP — infos obligatoires</div>', unsafe_allow_html=True)
                        _mn1,_mn2,_mn3,_mn4 = st.columns(4)
                        with _mn1: _new_mp_nom  = st.text_input("Nom *", key=f"mp_nom_{_mi}")
                        with _mn2: _new_mp_type = st.selectbox("Sous-type", ["Matière première","Composant","Packaging","Autre"], key=f"mp_type_{_mi}")
                        with _mn3: _new_mp_ref  = st.text_input("Code ref interne", key=f"mp_ref_{_mi}")
                        with _mn4: _new_mp_pu   = st.number_input("Coût unitaire (€)", min_value=0.0, step=0.01, key=f"mp_pu_{_mi}")
                        _mn5,_mn6,_mn7 = st.columns(3)
                        with _mn5: _new_mp_loc    = st.text_input("Localisation", key=f"mp_loc_{_mi}")
                        with _mn6: _new_mp_madein = st.text_input("Made in", key=f"mp_made_{_mi}")
                        with _mn7: _new_mp_four   = st.text_input("Fournisseur", key=f"mp_four_{_mi}")
                        articles_achat_mp.append({"new":True,"nom":_new_mp_nom,"type":_new_mp_type,"ref":_new_mp_ref,"pu":_new_mp_pu,"loc":_new_mp_loc,"madein":_new_mp_madein,"four":_new_mp_four,"qte":_mqte,"unit":_munit})
                    else:
                        articles_achat_mp.append({"new":False,"ref":_mp_refs.get(_msel,""),"nom":_mp_noms.get(_msel,""),"qte":_mqte,"unit":_munit})
                        st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#395f30;">✓ {_mp_refs.get(_msel,"")}</div>', unsafe_allow_html=True)

                ref_produit  = articles_achat_mp[0]["ref"] if articles_achat_mp else ""
                info_process = " + ".join(f"{a['qte']} {a['unit']} {a['nom']}" for a in articles_achat_mp if a.get("nom"))
                pv1,pv2 = st.columns(2)
                with pv1: payeur       = st.selectbox("Payeur", PAYEURS_ACHATS)
                with pv2: beneficiaire = st.selectbox("Bénéficiaire", BENEFICIAIRES)

            # ══ ACHAT PRODUIT FINI / AUTRE ═════════════════════════════════════
            else:
                articles_achat_mp = []
                try:
                    _colls_new = ["Toutes"] + [r[0] for r in conn.execute("SELECT DISTINCT collection FROM products WHERE collection IS NOT NULL ORDER BY collection").fetchall()]
                except Exception:
                    _colls_new = ["Toutes"]
                _coll_filter_new = st.selectbox("Collection produit", _colls_new, key="new_op_coll")
                try:
                    if _coll_filter_new == "Toutes":
                        _prods_new = conn.execute("SELECT nom, ref, couleurs FROM products ORDER BY nom").fetchall()
                    else:
                        _prods_new = conn.execute("SELECT nom, ref, couleurs FROM products WHERE collection=? ORDER BY nom",(_coll_filter_new,)).fetchall()
                    _prod_labels_new = ["— Saisie libre —"] + [f"{p[0]}{'—'+p[2] if p[2] else ''} ({p[1]})" for p in _prods_new]
                    _prod_refs_new   = [None] + [p[1] for p in _prods_new]
                    _prod_noms_new   = [None] + [p[0] for p in _prods_new]
                except Exception:
                    _prod_labels_new=["— Saisie libre —"]; _prod_refs_new=[None]; _prod_noms_new=[None]

                _prod_sel_new = st.selectbox("Article / Produit", _prod_labels_new, key="new_op_prod")
                _prod_idx_new = _prod_labels_new.index(_prod_sel_new)
                if _prod_sel_new != "— Saisie libre —":
                    ref_produit  = _prod_refs_new[_prod_idx_new] or ""
                    info_process = _prod_noms_new[_prod_idx_new] or ""
                    st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#395f30;">✓ SKU : {ref_produit}</div>', unsafe_allow_html=True)
                else:
                    ref_produit  = st.text_input("Réf. SKU libre", placeholder="ex: EWSJACKET-001A", key="new_op_sku_libre")
                    info_process = st.text_input("Article / Process", placeholder="ex: Waterfowl Jacket Tobacco")

                pv1,pv2 = st.columns(2)
                with pv1: payeur       = st.selectbox("Payeur", PAYEURS_ACHATS)
                with pv2: beneficiaire = st.selectbox("Bénéficiaire", BENEFICIAIRES)

            # ══ FOURNISSEUR (achats) ═══════════════════════════════════════════
            _CATS_NEED_FOUR = ("Matières premières","Matière première","Composants","Composant","Transport / Logistique","Confection / Production","Production / Confection")
            _four_required = type_op != "Vente" and categorie in _CATS_NEED_FOUR
            _four_sel = ""; _new_four_data = {}
            if type_op != "Vente":
                _four_label = "Fournisseur *" if _four_required else "Fournisseur (optionnel)"
                st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:{EW_B};text-transform:uppercase;letter-spacing:.15em;margin:10px 0 4px;">{_four_label}</div>', unsafe_allow_html=True)
                # Filtrer les fournisseurs selon la catégorie sélectionnée
                try:
                    _cat_to_stype = {
                        "Matière première":      "Matière première",
                        "Matières premières":    "Matière première",
                        "Composant":             "Composant",
                        "Composants":            "Composant",
                        "Transport / Logistique":"Logistique",
                        "Confection / Production":"Production / Confection",
                        "Production / Confection":"Production / Confection",
                    }
                    _stype_filter = _cat_to_stype.get(categorie)
                    if _stype_filter:
                        _fours_list = ["— Sélectionner / Nouveau —"] + [r[0] for r in conn.execute(
                            "SELECT DISTINCT nom FROM fournisseurs WHERE sous_type=? ORDER BY nom",
                            (_stype_filter,)).fetchall() if r[0]]
                        if len(_fours_list) == 1:  # Aucun trouvé → fallback tous
                            _fours_list = ["— Sélectionner / Nouveau —"] + [r[0] for r in conn.execute(
                                "SELECT DISTINCT nom FROM fournisseurs ORDER BY nom").fetchall() if r[0]]
                    else:
                        _fours_list = ["— Sélectionner / Nouveau —"] + [r[0] for r in conn.execute(
                            "SELECT DISTINCT nom FROM fournisseurs ORDER BY nom").fetchall() if r[0]]
                    # Aussi depuis contacts/fournisseurs
                    _ct_fours = [r[0] for r in conn.execute(
                        "SELECT DISTINCT nom FROM contacts WHERE type_contact='Fournisseur' ORDER BY nom").fetchall() if r[0]]
                    _fours_list = _fours_list + [f for f in _ct_fours if f not in _fours_list]
                except Exception:
                    _fours_list = ["— Sélectionner / Nouveau —"]
                _four_sel = st.selectbox("Fournisseur", _fours_list, key="new_op_four")
                _new_four_data = {}
                if _four_sel == "— Sélectionner / Nouveau —":
                    st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#c9800a;margin:2px 0 4px;">Nouveau fournisseur — tous les champs obligatoires</div>', unsafe_allow_html=True)
                    _nf1,_nf2,_nf3 = st.columns(3)
                    with _nf1:
                        _nf_nom  = st.text_input("Nom fournisseur *", key="nf_nom")
                        _nf_type = st.selectbox("Sous-type", ["Tissu","Composant","Packaging","Prestataire","Autre"], key="nf_type")
                        _nf_addr = st.text_input("Adresse complète *", placeholder="18 Rue de Picardie, 75003 Paris, France", key="nf_addr")
                    with _nf2:
                        _nf_email = st.text_input("Email *", key="nf_email")
                        _nf_tel   = st.text_input("Téléphone", key="nf_tel")
                        _nf_web   = st.text_input("Site web", key="nf_web")
                    with _nf3:
                        _nf_ig    = st.text_input("Instagram", key="nf_ig")
                        _nf_moq   = st.text_input("MOQ général", key="nf_moq")
                        _nf_delai = st.text_input("Délai production", placeholder="ex: 6 semaines", key="nf_delai")
                    _nf_pays = ""; _nf_ville = ""
                    if _nf_addr:
                        _parts = [p.strip() for p in _nf_addr.split(",")]
                        if len(_parts) >= 2:
                            _nf_pays  = _parts[-1]
                            _nf_ville = re.sub(r"^\d+\s*","", _parts[-2]).strip()
                        if _nf_pays:
                            st.markdown(f'<div style="font-size:10px;color:#395f30;">✓ Pays : {_nf_pays} · Ville : {_nf_ville}</div>', unsafe_allow_html=True)
                        else:
                            st.warning("⚠ Format adresse : Rue, CP Ville, Pays")
                    _new_four_data = {"nom":_nf_nom,"type":_nf_type,"adresse":_nf_addr,"email":_nf_email,"tel":_nf_tel,"web":_nf_web,"ig":_nf_ig,"moq":_nf_moq,"delai":_nf_delai,"pays":_nf_pays,"ville":_nf_ville}

            if type_op != "Vente":
                # ── Option source stock pour achat production ─────────────────
                _is_achat_prod = type_op in ("Achat","Achat perso") and categorie in (
                    "Confection / Production","Production / Confection",
                    "Produits finis","Produit fini")
                if _is_achat_prod and ref_produit:
                    st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:{EW_V};text-transform:uppercase;letter-spacing:.15em;margin:8px 0 4px;">Source des matières premières</div>', unsafe_allow_html=True)
                    _stock_source = st.radio(
                        "Les MP/composants associés à ce produit proviennent de :",
                        ["Depuis Stock Eastwood (déduit les MP du stock)", "Stock atelier de production (ne déduit pas les MP)"],
                        horizontal=False, key="op_stock_source")
                    _stock_src_key = "Eastwood" if "Eastwood" in _stock_source else "Atelier"
                    if _stock_src_key == "Eastwood" and ref_produit:
                        # Aperçu des composants qui seront déduits
                        try:
                            _prod_id_prev = conn.execute("SELECT id FROM products WHERE ref=?", (ref_produit,)).fetchone()
                            if _prod_id_prev:
                                _comps_prev = conn.execute("""SELECT nom_exact, quantite, unite FROM product_components
                                    WHERE product_id=? AND categorie_comp IN
                                    ('MP Principale (Main Fabric)','MP Secondaire','Doublure','Broderie','Zip','Bouton','Composant','Autre')""",
                                    (_prod_id_prev[0],)).fetchall()
                                if _comps_prev:
                                    st.markdown('<div style="font-size:10px;color:#8a7968;margin:3px 0 1px;">Matières qui seront déduites du stock Eastwood :</div>', unsafe_allow_html=True)
                                    for _cp in _comps_prev:
                                        st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#395f30;padding:1px 8px;">− {float(_cp[1] or 0)} {_cp[2] or ""} × qté → {_cp[0]}</div>', unsafe_allow_html=True)
                        except Exception: pass
                else:
                    _stock_src_key = "N/A"

                _source_mode = st.radio("Source", ["Libre", "Contact existant"], horizontal=True, key="op_src_mode")
                if _source_mode == "Contact existant":
                    try:
                        df_contacts_src = pd.read_sql(
                            "SELECT nom, email, telephone FROM contacts WHERE type_contact IN ('Fournisseur','Collaborateur') ORDER BY nom",
                            conn)
                        if not df_contacts_src.empty:
                            src_opts = [f"{r['nom']} — {r.get('email','') or r.get('telephone','')}"
                                       for _, r in df_contacts_src.iterrows()]
                            sel_src = st.selectbox("Contact", src_opts, key="op_src_sel")
                            source = sel_src.split(" — ")[0]
                        else:
                            source = st.text_input("Source (aucun contact enregistré)", key="op_src_free2")
                    except Exception:
                        source = st.text_input("Source / Contact", key="op_src_free3")
                else:
                    source = st.text_input("Source / Contact fournisseur", placeholder="ex: Jim Jin +86...", key="op_src_free")
            else:
                source = plateforme

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
            _tva_opts = ["— Sélectionner —"] + TYPES_TVA
            _tva_default_idx = _tva_opts.index(tva_sug) if tva_sug in _tva_opts else 0
            type_tva = st.selectbox("Type TVA *", _tva_opts,
                                    index=_tva_default_idx,
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

            # Valeurs par défaut si non définies (selon le type op)
            if 'articles_vente' not in dir():
                articles_vente = []
            # Pour vente multi-articles, construire ref_produit et info_process (tous les articles consolidés)
            if type_op == "Vente" and articles_vente:
                _arts_filled = [a for a in articles_vente if a.get("ref") or a.get("nom")]
                if _arts_filled:
                    ref_produit  = _arts_filled[0]["ref"]
                    # Consolider TOUS les articles + tailles dans info_process
                    info_process = " + ".join(
                        f"{a['qte']}× {a['nom']}{(' T.'+a['taille']) if a.get('taille') and a['taille']!='— Sans taille —' else ''}"
                        for a in _arts_filled if a.get("nom")
                    )
            if 'ref_produit' not in dir() or ref_produit is None:
                ref_produit = ""
            if 'info_process' not in dir() or info_process is None:
                info_process = ""

            if st.button("✓ Enregistrer l'opération", type="primary"):
                # ── Validation des champs obligatoires ──────────────────────
                _errors = []
                if not description:
                    _errors.append("La **description** est obligatoire.")
                if not categorie or categorie in ("","—","Toutes","— Sélectionner —"):
                    _errors.append("La **catégorie** est obligatoire.")
                if not type_tva or type_tva in ("","—","— Sélectionner —"):
                    _errors.append("Le **type de TVA** est obligatoire.")
                # Validation fournisseur obligatoire
                _CATS_NEED_FOUR_V = ("Matières premières","Matière première","Composants","Composant","Transport / Logistique","Confection / Production","Production / Confection")
                if type_op != "Vente" and categorie in _CATS_NEED_FOUR_V:
                    try:
                        _fs = _four_sel
                    except Exception:
                        _fs = ""
                    if not _fs or _fs == "— Sélectionner / Nouveau —":
                        try:
                            _nfd_check = _new_four_data
                        except Exception:
                            _nfd_check = {}
                        if not _nfd_check.get("nom","").strip():
                            _errors.append("Un **fournisseur** est obligatoire pour cette catégorie.")
                if type_op != "Vente":
                    try:
                        _nfd2 = _new_four_data
                    except Exception:
                        _nfd2 = {}
                    if _nfd2.get("nom","").strip():
                        if not _nfd2.get("email","").strip():
                            _errors.append("L'**email** du fournisseur est obligatoire.")
                        if not _nfd2.get("pays","").strip():
                            _errors.append("L'**adresse** du fournisseur (ville + pays) est obligatoire.")
                # Validation nouvelles MP
                if articles_achat_mp:
                    for _amp in [a for a in articles_achat_mp if a.get("new")]:
                        if not _amp.get("nom","").strip():
                            _errors.append("Le **nom** de chaque nouvelle MP est obligatoire.")
                # Taille obligatoire pour achat produit fini
                if type_op in ("Achat","Achat perso") and ref_produit and unite in ("Article","Pièces"):
                    _has_taille = bool(info_process and any(
                        t in info_process.upper() for t in ["XS","S)","M)","L)","XL","T1","T2","T3","T4","UNIQUE"]))
                    # Si on a un SKU produit fini mais pas de taille dans info_process → warning
                    try:
                        _is_pf = conn.execute(
                            "SELECT COUNT(*) FROM products WHERE ref=?", (ref_produit,)
                        ).fetchone()[0] > 0
                    except Exception:
                        _is_pf = False
                # Taille obligatoire si le produit a une étiquette de taille dans sa composition
                if type_op in ("Vente","Utilisation") and articles_vente:
                    for _a in articles_vente:
                        if not _a.get("nom"): continue
                        # Vérifier si ce produit nécessite une étiquette de taille
                        try:
                            _prod_has_taille = conn.execute("""
                                SELECT COUNT(*) FROM product_components pc
                                JOIN products p ON pc.product_id=p.id
                                WHERE p.ref=? AND pc.categorie_comp='Étiquette'
                                AND LOWER(pc.nom_exact) LIKE '%taille%'
                            """, (_a.get("ref",""),)).fetchone()
                            _needs_taille = _prod_has_taille and _prod_has_taille[0] > 0
                        except Exception:
                            _needs_taille = True  # Par défaut obligatoire si erreur
                        if _needs_taille and _a.get("taille","") in ("", "— Sans taille —"):
                            _errors.append(f"⚠ **Taille obligatoire** pour {_a.get('nom','ce produit')} (étiquette de taille dans la composition). Sélectionner T1, T2, T3 ou T4.")

                if _errors:
                    for _e in _errors:
                        st.error(_e)
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

                    # Sync stock — produit principal
                    if ref_produit and unite in ("Article","Pièces","Mètre","Kg","Lot"):
                        _sync_stock(db_conn, ref_produit, type_op, quantite)
                    # Sync stock — articles supplémentaires (vente multi)
                    if type_op == "Vente" and articles_vente:
                        for _art_s in articles_vente:
                            _ref_s = _art_s.get("ref","")
                            _qte_s = float(_art_s.get("qte",1) or 1)
                            if _ref_s and _ref_s != ref_produit:
                                _sync_stock(db_conn, _ref_s, "Vente", _qte_s)

                    # Si Vente → créer commande automatiquement
                    cmd_num = None
                    if type_op == "Vente":
                        tv = type_vente.split(" — ")[0] if type_vente else "B2C"
                        cmd_num = auto_create_commande(
                            db_conn, date_op, ref_produit, info_process, description,
                            quantite, pu_calc, total_ttc_calc, devise,
                            client_nom, client_email, client_tel, client_adresse,
                            source or plateforme or "Opérations", tv)

                    db_conn.commit()

                    # ── Déduction automatique stock lié (MP, packaging) ───────
                    _stock_src_use = "Eastwood"
                    try: _stock_src_use = _stock_src_key
                    except Exception: pass
                    _deduit_msgs = []
                    if type_op in ("Vente","Utilisation"):
                        _arts_to_sync = articles_vente if articles_vente else [{"ref":ref_produit,"qte":quantite}]
                        for _art in _arts_to_sync:
                            if _art.get("ref"):
                                _deduit_msgs.extend(_deduct_linked_stock(
                                    db_conn, _art["ref"], type_op, float(_art.get("qte",1)), "Eastwood"))
                    elif type_op in ("Achat","Achat perso") and ref_produit:
                        _deduit_msgs.extend(_deduct_linked_stock(
                            db_conn, ref_produit, type_op, float(quantite), _stock_src_use))

                    # ── Créer les nouvelles MP en stock ──────────────────────
                    try:
                        _amp_list = articles_achat_mp
                    except Exception:
                        _amp_list = []
                    for _amp in _amp_list:
                        if _amp.get("new") and _amp.get("nom","").strip():
                            _new_ref_mp = (_amp.get("ref","") or f"MP-{_amp['nom'][:8].upper().replace(' ','-')}").strip()
                            try:
                                db_conn.execute("""INSERT OR IGNORE INTO stock
                                    (ref, description, type_produit, qte_stock, localisation, prix_unitaire)
                                    VALUES (?,?,?,?,?,?)""",
                                    (_new_ref_mp, _amp["nom"], _amp.get("type","Matière première"),
                                     float(_amp.get("qte",0) or 0), _amp.get("loc",""), float(_amp.get("pu",0) or 0)))
                                db_conn.commit()
                            except Exception: pass
                        elif not _amp.get("new") and _amp.get("ref",""):
                            try:
                                db_conn.execute("UPDATE stock SET qte_stock=qte_stock+? WHERE ref=?",
                                                (float(_amp.get("qte",0) or 0), _amp["ref"]))
                                db_conn.commit()
                            except Exception: pass

                    # ── Créer le nouveau fournisseur en contacts ──────────────
                    try:
                        _nfd = _new_four_data
                    except Exception:
                        _nfd = {}
                    if _nfd and _nfd.get("nom","").strip() and type_op != "Vente":
                        try:
                            db_conn.execute("""INSERT OR IGNORE INTO contacts
                                (nom, type_contact, sous_type, email, telephone, instagram,
                                 activite, adresse, pays, importance)
                                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                                (_nfd["nom"], "Fournisseur", _nfd.get("type","Autre"),
                                 _nfd.get("email",""), _nfd.get("tel",""), _nfd.get("ig",""),
                                 f"Délai: {_nfd.get('delai','')} · MOQ: {_nfd.get('moq','')}",
                                 _nfd.get("adresse",""), _nfd.get("pays",""), "Normal"))
                            db_conn.commit()
                        except Exception: pass

                    db_conn.close()

                    msg = "✓ Opération enregistrée."
                    if ref_produit: msg += f" Stock mis à jour ({ref_produit})."
                    if cmd_num:     msg += f" Commande {cmd_num} créée automatiquement."
                    if _deduit_msgs:
                        msg += f" {len(_deduit_msgs)} déduction(s) stock liée(s)."
                    st.success(msg)
                    if _deduit_msgs:
                        with st.expander("Voir les déductions de stock automatiques"):
                            for _dm in _deduit_msgs:
                                st.markdown(f'<div style="font-family:DM Mono,monospace;font-size:10px;color:#395f30;">− {_dm}</div>', unsafe_allow_html=True)

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

    # ── IMPORT EN MASSE OPÉRATIONS ────────────────────────────────────────────
    if tab_imp_ops is not None:
        with tab_imp_ops:
            st.markdown('<div class="section-title">Import opérations en masse</div>', unsafe_allow_html=True)

            # ── Mode Google Sheets ────────────────────────────────────────────
            st.markdown("""
<div class="info-box">
<strong>Import depuis Google Sheets :</strong><br>
1. Dans Google Sheets → <strong>Fichier → Télécharger → CSV (.csv)</strong><br>
2. Activez le <strong>mode Google Sheets</strong> ci-dessous et uploadez le fichier.<br>
Le mapping des colonnes de ton tableau sera fait automatiquement.<br><br>
<strong>Format natif Eastwood :</strong> colonnes standards de l'app (voir template).
</div>""", unsafe_allow_html=True)

            import_mode = st.radio("Format du fichier",
                ["Format Google Sheets (tableau existant)", "Format natif Eastwood (template)"],
                key="imp_mode", horizontal=True)

            if import_mode.startswith("Format natif"):
                # Template standard
                tmpl_ops = pd.DataFrame([{
                    "date_op":"2026-04-08", "ref_produit":"EWSJACKET-001A",
                    "article":"Waterfowl Jacket", "description":"Achat tissu whipcord 5m",
                    "categorie":"Matière première", "type_op":"Achat",
                    "quantite":5, "unite":"Mètre", "prix_unitaire":45.0,
                    "type_tva":"Déductible", "total_ht":225.0, "total_ttc":270.0,
                    "tva":45.0, "devise":"EUR", "frais_envoi":0,
                    "payeur":"Eastwood", "beneficiaire":"Fournisseur",
                    "collection_op":"Chapter I — Hunting & Fishing",
                    "info_complementaire":"",
                }])
                buf_t = io.BytesIO()
                tmpl_ops.to_csv(buf_t, index=False, encoding="utf-8-sig")
                st.download_button("⬇ Télécharger le template Eastwood", buf_t.getvalue(),
                                   file_name="template_operations_eastwood.csv", mime="text/csv")

            st.markdown("---")
            imp_ops_file = st.file_uploader("Fichier CSV", type=["csv"], key="imp_ops")

            if imp_ops_file:
                try:
                    df_imp_raw = pd.read_csv(imp_ops_file, encoding="utf-8-sig")
                except Exception:
                    try:
                        df_imp_raw = pd.read_csv(imp_ops_file, encoding="latin-1")
                    except Exception as e:
                        st.error(f"Erreur lecture : {e}")
                        df_imp_raw = pd.DataFrame()

                if not df_imp_raw.empty:
                    # ── Mapping Google Sheets → Eastwood ──────────────────────
                    is_gsheet = import_mode.startswith("Format Google Sheets")

                    if is_gsheet:
                        st.markdown(f"**{len(df_imp_raw)} lignes détectées** — Format Google Sheets")
                        # Correspondance colonnes GSheets → Eastwood
                        # GSheet: Année Mois Date RefProduit InformationProcess Description
                        #         Catégorie Type Quantité Unité PrixUnitaire TypeTVA
                        #         TotalHT TotalTTC TVA Payeur Bénéficiaire Source InfosComp Facture
                        col_map = {
                            # Chercher les colonnes par nom partiel (insensible casse)
                            "date":        "date_op",
                            "ref produit": "ref_produit",
                            "ref_produit": "ref_produit",
                            "information process": "article",
                            "information": "article",
                            "description": "description",
                            "catégorie":   "categorie",
                            "categorie":   "categorie",
                            "type":        "type_op",
                            "quantité":    "quantite",
                            "quantite":    "quantite",
                            "unité":       "unite",
                            "unite":       "unite",
                            "prix unitaire":"prix_unitaire",
                            "prix_unitaire":"prix_unitaire",
                            "type tva":    "type_tva",
                            "type_tva":    "type_tva",
                            "total ht":    "total_ht",
                            "total_ht":    "total_ht",
                            "total ttc":   "total_ttc",
                            "total_ttc":   "total_ttc",
                            "tva":         "tva",
                            "payeur":      "payeur",
                            "bénéficiaire":"beneficiaire",
                            "beneficiaire":"beneficiaire",
                            "source":      "info_complementaire",
                            "informations complémentaires":"source",
                            "informations complementaires":"source",
                        }
                        # Renommer les colonnes
                        rename_dict = {}
                        for col in df_imp_raw.columns:
                            col_lower = col.lower().strip()
                            for key, target in col_map.items():
                                if key in col_lower and target not in rename_dict.values():
                                    rename_dict[col] = target
                                    break
                        df_imp_ops = df_imp_raw.rename(columns=rename_dict)

                        # Construire date_op depuis Année+Mois+Date si séparés
                        if "date_op" not in df_imp_ops.columns:
                            date_cols = [c for c in df_imp_ops.columns if "date" in c.lower() or "année" in c.lower() or "mois" in c.lower()]
                            if len(date_cols) >= 3:
                                # Colonnes séparées Année/Mois/Date
                                try:
                                    _ann = df_imp_ops.iloc[:,0].astype(str)
                                    _mois = df_imp_ops.iloc[:,1].astype(str).str.zfill(2)
                                    _jour = df_imp_ops.iloc[:,2].astype(str).str.zfill(2)
                                    df_imp_ops["date_op"] = _ann + "-" + _mois + "-" + _jour
                                except Exception:
                                    df_imp_ops["date_op"] = pd.Timestamp.today().strftime("%Y-%m-%d")
                    else:
                        df_imp_ops = df_imp_raw
                        st.markdown(f"**{len(df_imp_ops)} lignes détectées** — Format Eastwood")

                    # Aperçu des colonnes mappées
                    st.markdown("**Aperçu (10 premières lignes) :**")
                    preview_cols = [c for c in ["date_op","ref_produit","article","description",
                                                "categorie","type_op","quantite","unite",
                                                "total_ht","type_tva","payeur","beneficiaire"]
                                   if c in df_imp_ops.columns]
                    st.dataframe(df_imp_ops[preview_cols].head(10) if preview_cols else df_imp_ops.head(10),
                                 use_container_width=True, hide_index=True)

                    # Afficher un diagnostic de mapping clair
                    if is_gsheet:
                        mapped_count = len([c for c in ["date_op","total_ht","type_op","description",
                                                         "categorie","payeur"] if c in df_imp_ops.columns])
                        if mapped_count >= 4:
                            st.success(f"✓ Mapping détecté : {mapped_count} colonnes clés reconnues")
                        else:
                            unmapped_orig = [c for c in df_imp_raw.columns]
                            st.warning(f"⚠ Mapping partiel. Colonnes originales : {', '.join(unmapped_orig[:8])}...")

                    if st.button("✓ Valider et importer", type="primary", key="btn_imp_ops"):
                        from datetime import datetime as _dtp

                        def _cn(v, default=0):
                            try:
                                s = str(v or default).replace("€","").replace("$","").replace("¥","")
                                s = s.replace(" ","").replace("\u202f","").replace(",",".").strip()
                                if s in ("-","–","—","- €",""): return default
                                return float(s)
                            except Exception:
                                return default

                        def _norm_tva(v):
                            m = {"aucun":"Aucun","collecté":"Collectée","collectée":"Collectée",
                                 "déductible":"Déductible","autoliquidé":"Autoliquidée",
                                 "autoliquidée":"Autoliquidée","autoliquidé (achat)":"Autoliquidée"}
                            return m.get(str(v or "").strip().lower(), str(v or "Aucun").strip())

                        def _norm_type(v):
                            v = str(v or "").strip(); lv = v.lower()
                            if lv in ("achat perso","achat personnel"): return "Achat perso"
                            if lv == "achat": return "Achat"
                            if lv in ("vente","ventes"): return "Vente"
                            if lv == "utilisation": return "Utilisation"
                            if lv == "virement": return "Virement"
                            return v

                        for _mc, _md in [("article","TEXT DEFAULT ''"),("source","TEXT DEFAULT ''")]:
                            try: conn.execute(f"ALTER TABLE transactions ADD COLUMN {_mc} {_md}"); conn.commit()
                            except Exception: pass

                        ok_o = 0; err_o = 0; warn_o = 0
                        errors_detail = []; warnings_detail = []
                        next_n = get_next_num(conn)

                        for i_row, (_, row_o) in enumerate(df_imp_ops.iterrows(), 1):
                            row_errors = []; row_warnings = []

                            # Date
                            _date_raw = str(row_o.get("date_op","") or "").strip()
                            _date_str = None; _ann = None; _mois = None
                            for _fmt in ["%Y-%m-%d","%d/%m/%Y","%m/%d/%Y","%d-%m-%Y"]:
                                try:
                                    _dt = _dtp.strptime(_date_raw[:10], _fmt)
                                    _date_str = _dt.strftime("%Y-%m-%d"); _ann = _dt.year; _mois = _dt.month; break
                                except Exception: continue
                            if not _date_str:
                                row_errors.append(f"Date invalide ou manquante : '{_date_raw}'")
                                _date_str = str(date.today()); _ann = date.today().year; _mois = date.today().month

                            # Type op
                            _type_op = _norm_type(row_o.get("type_op",""))
                            if not _type_op:
                                row_errors.append("Type opération manquant (Achat / Vente / Achat perso)")

                            # Montants
                            ht    = _cn(row_o.get("total_ht"))
                            ttc   = _cn(row_o.get("total_ttc"))
                            tva_v = _cn(row_o.get("tva"))
                            pu    = _cn(row_o.get("prix_unitaire"))
                            qte   = _cn(row_o.get("quantite"), 1) or 1
                            _type_tva = _norm_tva(row_o.get("type_tva","Aucun"))

                            if ht > 0 and ttc == 0:
                                if _type_tva in ("Déductible","Collectée"):
                                    tva_v = round(ht * 0.20, 2); ttc = round(ht + tva_v, 2)
                                    row_warnings.append(f"TTC calculé automatiquement : {ttc:.2f} €")
                                else:
                                    ttc = ht; tva_v = 0.0
                            if ht == 0 and ttc == 0:
                                row_warnings.append("Montant HT = 0 (article sans prix renseigné)")

                            # Description
                            desc = str(row_o.get("description","") or "").strip()
                            art  = str(row_o.get("article","") or "").strip()
                            if not desc and not art:
                                row_errors.append("Description ET Article tous les deux vides")

                            # Unité
                            unite = str(row_o.get("unite","") or "").strip()
                            if unite in ("-","- €",""): unite = "Euros"

                            line_id = f"Ligne {i_row} · {_date_str} · {(desc or art)[:35]}"

                            if row_errors:
                                errors_detail.append((line_id, row_errors)); err_o += 1; continue

                            if row_warnings:
                                warnings_detail.append((line_id, row_warnings)); warn_o += 1

                            try:
                                conn.execute("""INSERT INTO transactions
                                    (annee,mois,date_op,ref_produit,info_process,article,description,
                                     categorie,type_op,quantite,unite,prix_unitaire,type_tva,
                                     total_ht,total_ttc,tva,devise,taux_change,montant_original,
                                     payeur,beneficiaire,source,info_complementaire,
                                     collection_op,num_operation)
                                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                    (_ann, _mois, _date_str,
                                     str(row_o.get("ref_produit","") or "")[:50],
                                     art[:60], art[:60], desc,
                                     str(row_o.get("categorie","Autre frais") or "Autre frais"),
                                     _type_op, float(qte), unite, float(pu), _type_tva,
                                     float(ht), float(ttc), float(tva_v),
                                     str(row_o.get("devise","EUR") or "EUR"), 1.0, float(ht),
                                     str(row_o.get("payeur","") or ""),
                                     str(row_o.get("beneficiaire","") or ""),
                                     str(row_o.get("source","") or ""),
                                     str(row_o.get("info_complementaire","") or ""),
                                     str(row_o.get("collection_op","") or ""),
                                     next_n + ok_o))
                                ok_o += 1
                            except Exception as _ie:
                                errors_detail.append((line_id, [f"Erreur DB : {str(_ie)[:80]}"])); err_o += 1

                        conn.commit()
                        assign_operation_numbers(conn); conn.commit()

                        # Rapport
                        if ok_o > 0:
                            st.success(f"✓ **{ok_o} opération(s) importée(s)** avec succès !")
                        if warn_o > 0:
                            with st.expander(f"⚠ {warn_o} avertissement(s) — lignes importées quand même"):
                                for lbl, warns in warnings_detail:
                                    for w in warns:
                                        st.markdown(f'<div style="font-size:11px;color:#c9800a;padding:1px 0;">· <b>{lbl}</b> → {w}</div>', unsafe_allow_html=True)
                        if err_o > 0:
                            with st.expander(f"🚫 {err_o} ligne(s) rejetée(s) — NON importées", expanded=True):
                                st.caption("Corrigez ces lignes dans votre fichier et réimportez.")
                                for lbl, errs in errors_detail:
                                    for e in errs:
                                        st.markdown(f'<div style="font-size:11px;color:#c1440e;padding:1px 0;">· <b>{lbl}</b> → {e}</div>', unsafe_allow_html=True)
                        if ok_o > 0:
                            st.rerun()

    conn.close()
