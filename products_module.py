# products_module.py — v5.28 — 1777563907
# ══════════════════════════════════════════════════════════════════════════════
# MODULE PRODUITS v3
# Données réelles line sheet 26 · Order Sheet · Fiche Technique · Packaging
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
import base64
from datetime import date

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, Image as RLImage,
                                    HRFlowable, KeepTogether, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfgen import canvas as rl_canvas
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ── Palette ────────────────────────────────────────────────────────────────────
EW_V = "#7b506f"
EW_G = "#395f30"
EW_B = "#8a7968"
EW_S = "#ede3d3"
EW_C = "#f5f0e8"
EW_K = "#1a1a1a"

COLLECTIONS = [
    "Chapter II — Le Souvenir",
    "Chapter I — Hunting & Fishing",
    "Archive",
]
STATUTS_PROD = ["Recherche", "Sample & Testing", "Disponible", "Out of stock", "Archive"]
CATEGORIES_PROD = ["Jacket", "Shirt", "Trouser", "Knitwear", "Gear / Accessory", "Other"]
COMP_CATEGORIES = [
    "MP Principale (Main Fabric)",
    "MP Secondaire",
    "Doublure (Lining)",
    "Zips",
    "Boutons",
    "Broderie principale",
    "Broderie secondaire",
    "Patchs",
    "Prints / Sérigraphie",
    "Packaging & Accessoires produit",
    "Autre",
]
COMP_UNITES = ["Mètre", "Pièces", "Kg", "Litre", "Lot", "Bobine"]

# ── Données réelles — Line Sheet AW26 ─────────────────────────────────────────
PRODUCTS_SEED = [
    # ── Chapter II — Le Souvenir ────────────────────────────────────────────
    {
        "ref": "EWSJACKET-003A", "internal_ref": "EWSJACKET-003A",
        "nom": "Akagi Jacket", "variant": "Tobacco",
        "categorie": "Jacket", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 330, "prix_retail_eur": 700,
        "moq": 2, "delivery": "July 2026", "origine": "Japan",
        "description": "This piece features authentic Yokoburi embroidery, executed on a vintage traditional machine, using an original embroidery pattern from the 1950s, and equipped with vintage Talon zippers.",
        "matieres": "Rayon Gabardine", "couleurs": "Tobacco", "tailles": "1(S) / 2(M) / 3(L) / 4(XL) / 5(XXL)",
        "made_in": "Japan",
    },
    {
        "ref": "EWSJACKET-002A", "internal_ref": "EWSJACKET-002A",
        "nom": "Miura Jacket", "variant": "Green",
        "categorie": "Jacket", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 430, "prix_retail_eur": 880,
        "moq": 2, "delivery": "July 2026", "origine": "Japan",
        "description": "This design inspired by 1950s souvenir jackets features a Nishijin print (kimono pattern) and authentic Yokoburi embroidery made on a vintage machine using original 1950s embroidery patterns, complete with Waldes zippers.",
        "matieres": "Rayon Acetate", "couleurs": "Green", "tailles": "1(S) / 2(M) / 3(L) / 4(XL) / 5(XXL)",
        "made_in": "Japan",
    },
    {
        "ref": "EWSSHIRT-003A", "internal_ref": "EWSSHIRT-003A",
        "nom": "Research Club Shirt", "variant": "Cloud Blue",
        "categorie": "Shirt", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 300, "prix_retail_eur": 620,
        "moq": 3, "delivery": "June 2026", "origine": "France",
        "description": "Inspired by 1960s bowling shirts, featuring a rare double-breasted front, boxy tailored fit, chainstitched Cogg boat and Eiffel Tower embroidery, and mother of pearl buttons.",
        "matieres": "78% Rayon, 22% Linen", "couleurs": "Cloud Blue", "tailles": "1(S) / 2(M) / 3(L) / 4(XL)",
        "made_in": "Paris",
    },
    {
        "ref": "EWSSHIRT-003B", "internal_ref": "EWSSHIRT-003B",
        "nom": "Research Club Shirt", "variant": "Pastel Green",
        "categorie": "Shirt", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 300, "prix_retail_eur": 620,
        "moq": 3, "delivery": "June 2026", "origine": "France",
        "description": "Inspired by 1960s bowling shirts, featuring a rare double-breasted front, boxy tailored fit, chainstitched Cogg boat and Eiffel Tower embroidery, and mother of pearl buttons.",
        "matieres": "78% Rayon, 22% Linen", "couleurs": "Pastel Green", "tailles": "1(S) / 2(M) / 3(L) / 4(XL)",
        "made_in": "Paris",
    },
    {
        "ref": "EWSSHIRT-002A", "internal_ref": "EWSSHIRT-002A",
        "nom": "Lutece Plage Shirt", "variant": "Sand",
        "categorie": "Shirt", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 115, "prix_retail_eur": 260,
        "moq": 5, "delivery": "June 2026", "origine": "France",
        "description": "Inspired by 1930s Hawaiian shirts and a 1910s hand-painted U.S. Navy jacket, featuring a relaxed fit, reworked open collar, custom buttons, and an allover signature printed in France.",
        "matieres": "Rayon Twill", "couleurs": "Sand", "tailles": "1(S) / 2(M) / 3(L) / 4(XL)",
        "made_in": "Paris",
    },
    {
        "ref": "EWSGEAR-001A", "internal_ref": "EWSGEAR-001A",
        "nom": "Souvenir Cap", "variant": "Faded Green",
        "categorie": "Gear / Accessory", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 27, "prix_retail_eur": 65,
        "moq": 5, "delivery": "June 2026", "origine": "France",
        "description": "Inspired by postwar souvenir caps, reviving 1950s graphics through modern craftsmanship. Features front Eiffel Tower and palm tree embroidery, contrast sunfaded visor, side overstitching, back signature embroidery, and adjustable vegan leather strap.",
        "matieres": "Cotton", "couleurs": "Faded Green", "tailles": "One size adjustable",
        "made_in": "Paris",
    },
    {
        "ref": "EWSGEAR-001B", "internal_ref": "EWSGEAR-001B",
        "nom": "Souvenir Cap", "variant": "Deep Rust",
        "categorie": "Gear / Accessory", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 27, "prix_retail_eur": 65,
        "moq": 5, "delivery": "June 2026", "origine": "France",
        "description": "Inspired by postwar souvenir caps, reviving 1950s graphics through modern craftsmanship. Features front Eiffel Tower and palm tree embroidery, contrast sunfaded visor, side overstitching, back signature embroidery, and adjustable vegan leather strap.",
        "matieres": "Cotton", "couleurs": "Deep Rust", "tailles": "One size adjustable",
        "made_in": "Paris",
    },
    {
        "ref": "EWSGEAR-003A", "internal_ref": "EWSGEAR-003A",
        "nom": "Memory Card-Holder", "variant": "Baranil Gold",
        "categorie": "Gear / Accessory", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 145, "prix_retail_eur": 320,
        "moq": 3, "delivery": "June 2026", "origine": "France",
        "description": "Crafted with Parisian leatherworkers La Perruque, this wallet reinterprets 1950s souvenir pieces through French craftsmanship. Made from Baranil calf leather and Alran goatskin, it features a hand-painted tiger with French and Japanese flags, handstitched construction, and ultra-slim design.",
        "matieres": "Baranil calf leather, Alran goatskin", "couleurs": "Gold / Natural", "tailles": "One size (10x6.4cm)",
        "made_in": "Paris",
    },
    {
        "ref": "EWSGEAR-002A", "internal_ref": "EWSGEAR-002A",
        "nom": "Tresor Silk Square", "variant": "Red",
        "categorie": "Gear / Accessory", "collection": "Chapter II — Le Souvenir",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 59, "prix_retail_eur": 75,
        "moq": 5, "delivery": "June 2026", "origine": "France",
        "description": "Inspired by souvenir bandanas once sold in roadside shops, this piece reimagines Paris as a distant island, a treasure of culture and memory. Featuring hand-drawn motifs of monuments and symbols framed by a nautical rope border, printed on an off-white base in deep red and navy tones.",
        "matieres": "Organic Silk", "couleurs": "Red / Off-white", "tailles": "One size (55x55cm)",
        "made_in": "Paris",
    },
    # ── Chapter I — Hunting & Fishing ───────────────────────────────────────
    {
        "ref": "EWSJACKET-001A", "internal_ref": "EWSJACKET-001A",
        "nom": "Waterfowl Jacket", "variant": "Tobacco",
        "categorie": "Jacket", "collection": "Chapter I — Hunting & Fishing",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 480, "prix_retail_eur": 1100,
        "moq": 3, "delivery": "June 2026", "origine": "France",
        "description": "This jacket draws its inspiration from fishing and hunting garments. The jacket's short cut is inspired by 1940s fly-fishing clothing. It is entirely crafted from original 1950s French Whipcord and authentic 1950s French army buttons.",
        "matieres": "1950s Wool Whipcord", "couleurs": "Tobacco", "tailles": "1(S) / 2(M) / 3(L) / 4(XL)",
        "made_in": "Paris",
    },
    {
        "ref": "EWSJACKET-001B", "internal_ref": "EWSJACKET-001B",
        "nom": "Waterfowl Jacket", "variant": "Black",
        "categorie": "Jacket", "collection": "Chapter I — Hunting & Fishing",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 480, "prix_retail_eur": 1100,
        "moq": 3, "delivery": "June 2026", "origine": "France",
        "description": "This jacket draws its inspiration from fishing and hunting garments. The jacket's short cut is inspired by 1940s fly-fishing clothing. It is entirely crafted from original 1950s French Whipcord and authentic 1950s French army buttons.",
        "matieres": "1950s Wool Whipcord", "couleurs": "Black", "tailles": "1(S) / 2(M) / 3(L) / 4(XL)",
        "made_in": "Paris",
    },
    {
        "ref": "EWSJACKET-001C", "internal_ref": "EWSJACKET-001C",
        "nom": "Waterfowl Jacket", "variant": "Grey",
        "categorie": "Jacket", "collection": "Chapter I — Hunting & Fishing",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 480, "prix_retail_eur": 1100,
        "moq": 3, "delivery": "June 2026", "origine": "France",
        "description": "This jacket draws its inspiration from fishing and hunting garments. The jacket's short cut is inspired by 1940s fly-fishing clothing. It is entirely crafted from original 1950s French Whipcord and authentic 1950s French army buttons.",
        "matieres": "1950s Wool Whipcord", "couleurs": "Grey", "tailles": "1(S) / 2(M) / 3(L) / 4(XL)",
        "made_in": "Paris",
    },
]

# ── Packaging Eastwood (commun à tous les envois) ─────────────────────────────
PACKAGING_STANDARD = [
    {"nom": "Pochette enveloppe postal XL craft",   "ref_stock": "PKG-ENV-XL", "qte": 1, "unite": "Pièces"},
    {"nom": "Sticker logo blanc cercle",            "ref_stock": "PKG-STK-01", "qte": 1, "unite": "Pièces"},
    {"nom": "Tag numéro identification",            "ref_stock": "PKG-TAG-01", "qte": 1, "unite": "Pièces"},
    {"nom": "Étiquette textile Eastwood Studio",    "ref_stock": "ETQ-TXT-01", "qte": 1, "unite": "Pièces"},
    {"nom": "Étiquette fabrication Française",      "ref_stock": "ETQ-FAB-FR", "qte": 1, "unite": "Pièces"},
    {"nom": "Étiquette de composition",             "ref_stock": "ETQ-COMP",   "qte": 1, "unite": "Pièces"},
]



_COLLECTIONS_DEFAULT = [
    "Chapter I — Hunting & Fishing",
    "Chapter II — Le Souvenir",
]

COLLECTIONS = _COLLECTIONS_DEFAULT.copy()


def _normalize_collection(val):
    """Normalise un nom de collection vers les valeurs canoniques."""
    if not val: return None
    if "Hunting" in val or "Fishing" in val:
        return "Chapter I — Hunting & Fishing"
    if "Souvenir" in val:
        return "Chapter II — Le Souvenir"
    return val  # Collection personnalisée créée par l'utilisateur


def get_collections_dynamic(conn):
    """Collections depuis la DB, normalisées, fusionnées avec les défauts."""
    try:
        # Migrer d'abord les anciennes valeurs
        try:
            conn.execute("""UPDATE products SET collection='Chapter I — Hunting & Fishing'
                WHERE collection LIKE '%Hunting%' AND collection != 'Chapter I — Hunting & Fishing'""")
            conn.execute("""UPDATE products SET collection='Chapter II — Le Souvenir'
                WHERE collection LIKE '%Souvenir%' AND collection != 'Chapter II — Le Souvenir'""")
            conn.commit()
        except Exception:
            pass
        rows = conn.execute(
            "SELECT DISTINCT collection FROM products WHERE collection IS NOT NULL AND collection != '' ORDER BY collection"
        ).fetchall()
        from_db = []
        for r in rows:
            norm = _normalize_collection(r[0])
            if norm and norm not in from_db:
                from_db.append(norm)
        merged = list(dict.fromkeys(_COLLECTIONS_DEFAULT + from_db))
        return merged
    except Exception:
        return _COLLECTIONS_DEFAULT.copy()


def sync_product_status(conn, ref=None):
    """Synchronise le statut des produits selon leur stock.
    Si qte_stock <= 0 → statut "Out of stock"
    Si qte_stock > 0 et statut était "Out of stock" → statut "Disponible"
    Appelée après chaque modification de stock.
    """
    try:
        if ref:
            # Sync un seul produit
            row_s = conn.execute("SELECT qte_stock FROM stock WHERE ref=?", (ref,)).fetchone()
            if row_s is not None:
                qte = float(row_s[0] or 0)
                if qte <= 0:
                    conn.execute("""UPDATE products SET statut='Out of stock'
                        WHERE ref=? AND statut IN ('Disponible','Sample & Testing')""", (ref,))
                else:
                    conn.execute("""UPDATE products SET statut='Disponible'
                        WHERE ref=? AND statut='Out of stock'""", (ref,))
        else:
            # Sync tous les produits
            # Produits avec stock = 0 → Out of stock
            conn.execute("""UPDATE products SET statut='Out of stock'
                WHERE ref IN (
                    SELECT ref FROM stock WHERE qte_stock <= 0
                ) AND statut IN ('Disponible','Sample & Testing')""")
            # Produits avec stock > 0 qui étaient Out of stock → Disponible
            conn.execute("""UPDATE products SET statut='Disponible'
                WHERE ref IN (
                    SELECT ref FROM stock WHERE qte_stock > 0
                ) AND statut='Out of stock'""")
        conn.commit()
    except Exception:
        pass


def run_data_migration(conn):
    """Migration intelligente : ne reinsère que ce qui manque."""
    import traceback as _tb
    try:
        c = conn.cursor()

        # Compter ce qui existe
        n_prods = c.execute("SELECT COUNT(*) FROM products WHERE ref LIKE 'EWS%'").fetchone()[0]
        n_comps = c.execute("SELECT COUNT(*) FROM product_components").fetchone()[0]
        n_stock = c.execute("SELECT COUNT(*) FROM stock WHERE ref LIKE 'EWS%'").fetchone()[0]
        n_pkgs  = c.execute("SELECT COUNT(*) FROM packaging_types").fetchone()[0]

        # Tout est complet → rien à faire
        if n_prods >= 14 and n_comps >= 90 and n_stock >= 35 and n_pkgs >= 4:
            return

        # PRODUITS manquants → tout réinitialiser
        if n_prods < 14:
            _insert_migration_data(conn)
            return

        # COMPOSANTS manquants (produits OK) → insérer seulement les composants
        if n_comps < 90:
            try:
                c.execute("DELETE FROM product_components")
                conn.commit()
                _insert_only_components(conn)
            except Exception: _tb.print_exc()

        # STOCK manquant → insérer seulement le stock
        if n_stock < 35:
            try:
                c.execute("DELETE FROM stock WHERE ref LIKE 'EWS%'")
                conn.commit()
                _insert_only_stock(conn)
            except Exception: _tb.print_exc()

        # PACKAGINGS manquants
        if n_pkgs < 4:
            try:
                c.execute("DELETE FROM packaging_items")
                c.execute("DELETE FROM packaging_types")
                conn.commit()
                _insert_only_packagings(conn)
            except Exception: _tb.print_exc()

        # COÛTS — vérifier si remplis, sinon injecter
        try:
            n_costs = c.execute(
                "SELECT COUNT(*) FROM product_costs WHERE cout_montage > 0"
            ).fetchone()[0]
            if n_costs < 14:
                _insert_only_costs(conn)
        except Exception: _tb.print_exc()

    except Exception:
        _tb.print_exc()
        try: _insert_migration_data(conn)
        except Exception: pass


def _insert_only_costs(conn):
    """Insère les coûts de production avec les colonnes exactes de product_costs."""
    import traceback
    try:
        c = conn.cursor()

        # Récupérer les colonnes existantes
        existing_cols = [r[1] for r in c.execute("PRAGMA table_info(product_costs)").fetchall()]

        COSTS = {
            "EWSJACKET-001A": {"cout_mp_principale":60.0,"cout_lining":30.0,"cout_bouton_principal":1.35,"cout_bouton_secondaire":0.20,"cout_patch":4.80,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":80.0,"cout_broderie_principale":8.0,"cout_marketing_pct":5.0},
            "EWSJACKET-001B": {"cout_mp_principale":60.0,"cout_lining":30.0,"cout_bouton_principal":1.35,"cout_bouton_secondaire":0.20,"cout_patch":4.80,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":80.0,"cout_broderie_principale":8.0,"cout_marketing_pct":5.0},
            "EWSJACKET-001C": {"cout_mp_principale":60.0,"cout_lining":30.0,"cout_bouton_principal":1.35,"cout_bouton_secondaire":0.20,"cout_patch":4.80,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":80.0,"cout_broderie_principale":8.0,"cout_marketing_pct":5.0},
            "EWSJACKET-001D": {"cout_mp_principale":60.0,"cout_lining":30.0,"cout_bouton_principal":1.35,"cout_bouton_secondaire":0.20,"cout_patch":4.80,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":80.0,"cout_broderie_principale":8.0,"cout_marketing_pct":5.0},
            "EWSJACKET-001E": {"cout_mp_principale":60.0,"cout_lining":30.0,"cout_bouton_principal":1.35,"cout_bouton_secondaire":0.20,"cout_patch":4.80,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":80.0,"cout_broderie_principale":8.0,"cout_marketing_pct":5.0},
            "EWSJACKET-002A": {"cout_patronage":150.0,"cout_assemblage":300.0,"cout_production":127.84,"cout_mp1_sample":350.0,"cout_mp2_sample":150.0,"cout_compo1_sample":240.82,"cout_log_sample":34.0,"cout_tax":129.99,"cout_mp_principale":68.0,"cout_lining":16.19,"cout_zip_principal":5.0,"cout_bouton_principal":1.0,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":285.0,"cout_broderie_principale":33.0,"cout_marketing_pct":5.0},
            "EWSJACKET-003A": {"cout_patronage":177.80,"cout_assemblage":240.0,"cout_production":124.37,"cout_mp1_sample":250.0,"cout_mp2_sample":100.0,"cout_compo1_sample":193.61,"cout_compo2_sample":14.96,"cout_tax":103.68,"cout_mp_principale":44.19,"cout_lining":16.19,"cout_zip_principal":9.0,"cout_zip_secondaire":1.35,"cout_bouton_principal":1.0,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":194.0,"cout_broderie_principale":31.62,"cout_marketing_pct":5.0},
            "EWSSHIRT-001A": {"cout_patronage":48.88,"cout_assemblage":150.0,"cout_mp1_sample":40.53,"cout_compo1_sample":25.90,"cout_compo2_sample":200.0,"cout_mp_principale":23.70,"cout_mp_secondaire":13.0,"cout_bouton_principal":4.10,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":60.0,"cout_coupe":30.0,"cout_broderie_principale":100.0,"cout_marketing_pct":5.0},
            "EWSSHIRT-001B": {"cout_mp_principale":23.70,"cout_mp_secondaire":13.0,"cout_bouton_principal":4.10,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":60.0,"cout_coupe":30.0,"cout_broderie_principale":100.0,"cout_marketing_pct":5.0},
            "EWSSHIRT-002A": {"cout_patronage":48.88,"cout_assemblage":150.0,"cout_mp1_sample":99.30,"cout_compo1_sample":12.95,"cout_bouton_principal":2.05,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":23.0,"cout_coupe":23.0,"cout_print":39.0,"cout_marketing_pct":5.0},
            "EWSGEAR-001A": {"cout_production":35.0,"cout_log_sample":18.14,"cout_tax":8.50,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":10.74,"cout_marketing_pct":5.0},
            "EWSGEAR-001B": {"cout_production":35.0,"cout_log_sample":18.14,"cout_tax":8.50,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":10.74,"cout_marketing_pct":5.0},
            "EWSGEAR-002A": {"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_montage":50.21,"cout_marketing_pct":5.0},
            "EWSGEAR-003A": {"cout_production":38.0,"cout_compo1_sample":150.0,"cout_mp_principale":40.80,"cout_etiq_textile":0.35,"cout_etiq_taille":0.80,"cout_etiq_compo":0.80,"cout_etiq_fab_fr":0.60,"cout_tag_numero":0.20,"cout_peinture":60.0,"cout_marketing_pct":5.0},
        }

        # Mapper les noms de colonnes personnalisés vers les colonnes réelles
        COL_MAP = {
            "cout_zip_principal":    "cout_zip",
            "cout_zip_secondaire":   "cout_zip",
            "cout_bouton_principal": "cout_boutons",
            "cout_bouton_secondaire":"cout_boutons",
            "cout_prints_principal": "cout_print",
            "cout_prints_secondaire":"cout_print",
            "cout_marketing_pct":    "cout_marketing",
            "cout_production_sample":"cout_production",
        }

        for sku, vals in COSTS.items():
            prod = c.execute("SELECT id FROM products WHERE ref=?", (sku,)).fetchone()
            if not prod: continue
            pid = prod[0]

            # Agréger les valeurs en mappant vers les colonnes réelles
            merged = {}
            for k, v in vals.items():
                real_col = COL_MAP.get(k, k)
                if real_col in existing_cols:
                    merged[real_col] = merged.get(real_col, 0) + float(v)
                elif k in existing_cols:
                    merged[k] = merged.get(k, 0) + float(v)
                else:
                    # Colonne pas encore créée → essayer de l'ajouter
                    try:
                        c.execute(f"ALTER TABLE product_costs ADD COLUMN {k} REAL DEFAULT 0")
                        conn.commit()
                        existing_cols.append(k)
                        merged[k] = float(v)
                    except Exception: pass

            if not merged: continue

            cols = list(merged.keys())
            vals_list = [merged[c_] for c_ in cols]
            set_clause = ", ".join(f"{c_}=?" for c_ in cols)

            ex = c.execute("SELECT id FROM product_costs WHERE product_id=?", (pid,)).fetchone()
            if ex:
                c.execute(f"UPDATE product_costs SET {set_clause} WHERE product_id=?",
                          vals_list + [pid])
            else:
                col_str = "product_id, " + ", ".join(cols)
                ph = "?, " + ", ".join("?" for _ in cols)
                c.execute(f"INSERT INTO product_costs ({col_str}) VALUES ({ph})",
                          [pid] + vals_list)
        conn.commit()
    except Exception:
        traceback.print_exc()


def _insert_only_components(conn):
    """Insère uniquement les composants sans toucher aux produits ni au stock."""
    import traceback
    try:
        c = conn.cursor()
        COMPS = {
            "EWSJACKET-001A":[("Laine Whipcord Chocolate","MP Principale (Main Fabric)",2.0,"Mètre","EWSWOOL-001A"),("Mix coton laine tartan Shadow","Doublure",1.7,"Mètre","EWSCOTT-001A"),("Patch brodé logo EWS","Broderie",1.0,"Pièces",""),("Boutton simple Maron 25mm","Bouton",4.0,"Pièces","EWSBTN-001A"),("Boutons Équipement Militaires Vintage 1960","Bouton",8.0,"Pièces","EWSBTN-002A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSJACKET-001B":[("Laine Whipcord Tobacco","MP Principale (Main Fabric)",2.0,"Mètre","EWSWOOL-001B"),("Mix coton laine tartan Shadow","Doublure",1.7,"Mètre","EWSCOTT-001A"),("Patch brodé logo EWS","Broderie",1.0,"Pièces",""),("Boutton simple Maron 25mm","Bouton",4.0,"Pièces","EWSBTN-001A"),("Boutons Équipement Militaires Vintage 1960","Bouton",8.0,"Pièces","EWSBTN-002A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSJACKET-001C":[("Laine Whipcord Greige","MP Principale (Main Fabric)",2.0,"Mètre","EWSWOOL-001C"),("Mix coton laine tartan Shadow","Doublure",1.7,"Mètre","EWSCOTT-001A"),("Patch brodé logo EWS","Broderie",1.0,"Pièces",""),("Boutton simple Maron 25mm","Bouton",4.0,"Pièces","EWSBTN-001A"),("Boutons Équipement Militaires Vintage 1960","Bouton",8.0,"Pièces","EWSBTN-002A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSJACKET-001D":[("Laine Whipcord Sand","MP Principale (Main Fabric)",2.0,"Mètre","EWSWOOL-001D"),("Mix coton laine tartan Clear","Doublure",1.7,"Mètre","EWSCOTT-001B"),("Patch brodé logo EWS","Broderie",1.0,"Pièces",""),("Boutton simple Maron 25mm","Bouton",4.0,"Pièces","EWSBTN-001A"),("Boutons Équipement Militaires Vintage 1960","Bouton",8.0,"Pièces","EWSBTN-002A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSJACKET-001E":[("Laine Whipcord Black","MP Principale (Main Fabric)",2.0,"Mètre","EWSWOOL-001E"),("Mix coton laine tartan Clear","Doublure",1.7,"Mètre","EWSCOTT-001B"),("Patch brodé logo EWS","Broderie",1.0,"Pièces",""),("Boutton simple Maron 25mm","Bouton",4.0,"Pièces","EWSBTN-001A"),("Boutons Équipement Militaires Vintage 1960","Bouton",8.0,"Pièces","EWSBTN-002A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSJACKET-002A":[("Rayonne satinée rembourée Verte","MP Principale (Main Fabric)",2.0,"Mètre","EWSCELL-001A"),("Rayonne satinée Nishijin EWS","Doublure",2.0,"Mètre","EWSCELL-001B"),("Dos brodé cigogne Yokoburi","Broderie",1.0,"Pièces",""),("Zip double face WALDES","Zip",1.0,"Pièces","EWSZIP-001A"),("Boutons cat's eye noir","Bouton",2.0,"Pièces","EWSBTN-004A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSJACKET-003A":[("Gabardine de rayonne Tobacco","MP Principale (Main Fabric)",2.0,"Mètre","EWSCELL-002A"),("Rayonne satinée Crème","Doublure",2.0,"Mètre","EWSCELL-003A"),("Dos brodé Paon Patron 1950 Yokoburi","Broderie",1.0,"Pièces",""),("Zip chainette doré Talon Vintage 1960","Zip",1.0,"Pièces","EWSZIP-002A"),("Zip doré Talon Vintage secondaire","Zip",1.0,"Pièces","EWSZIP-002B"),("Boutons cat's eye noir","Bouton",2.0,"Pièces","EWSBTN-004A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSSHIRT-001A":[("Lin & Viscose Bleu Pigeon","MP Principale (Main Fabric)",1.7,"Mètre","EWSBLND-001A"),("Lin & Viscose Blanc Cassé","MP Secondaire",0.9,"Mètre","EWSBLND-001C"),("Voile de coton blanc","Doublure",0.6,"Mètre","EWSCOTT-003A"),("Dos brodé Club Recherche EWS Chainstitch","Broderie",1.0,"Pièces",""),("Boutons nacrés Eastwood Studio","Bouton",10.0,"Pièces","EWSBTN-003A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSSHIRT-001B":[("Lin & Viscose Vert Pastel","MP Principale (Main Fabric)",1.7,"Mètre","EWSBLND-001B"),("Lin & Viscose Blanc Cassé","MP Secondaire",0.9,"Mètre","EWSBLND-001C"),("Voile de coton blanc","Doublure",0.6,"Mètre","EWSCOTT-003A"),("Dos brodé Club Recherche EWS Chainstitch","Broderie",1.0,"Pièces",""),("Boutons nacrés Eastwood Studio","Bouton",10.0,"Pièces","EWSBTN-003A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSSHIRT-002A":[("Sergé de viscose All-Over","MP Principale (Main Fabric)",1.9,"Mètre","EWSVSC-001A"),("Voile de coton blanc","Doublure",0.6,"Mètre","EWSCOTT-003A"),("Boutons nacrés Eastwood Studio","Bouton",5.0,"Pièces","EWSBTN-003A"),("Étiquette de composition","Étiquette",1.0,"Pièces","EWSETQ-001A"),("Étiquette de taille","Étiquette",1.0,"Pièces",""),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A"),("Étiquette textile Eastwood Studio","Étiquette",1.0,"Pièces","EWSETQ-004A")],
            "EWSGEAR-001A":[("Coton blanc casquette","MP Principale (Main Fabric)",1.0,"Pièces","EWSCOTT-002A"),("Lanière cuir végan","MP Secondaire",1.0,"Pièces","EWSLEAT-002A"),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A")],
            "EWSGEAR-001B":[("Coton blanc casquette","MP Principale (Main Fabric)",1.0,"Pièces","EWSCOTT-002A"),("Lanière cuir végan","MP Secondaire",1.0,"Pièces","EWSLEAT-002A"),("Étiquette fabrication Française","Étiquette",1.0,"Pièces","EWSETQ-003A")],
            "EWSGEAR-002A":[("Soie Motif Trésor 55x55cm","MP Principale (Main Fabric)",1.0,"Pièces","EWSSOIE-001A")],
            "EWSGEAR-003A":[("Wallet cuir de veau tanné marron","MP Principale (Main Fabric)",1.0,"Pièces","EWSLEAT-001A"),("Peinture main Xavier Boully","Peinture",1.0,"Pièces","")],
        }
        for sku, comps in COMPS.items():
            prod = c.execute("SELECT id FROM products WHERE ref=?", (sku,)).fetchone()
            if prod:
                for nom_c, cat_c, qte_c, unit_c, ref_c in comps:
                    try:
                        c.execute("INSERT INTO product_components (product_id,nom_exact,categorie_comp,quantite,unite,ref_stock) VALUES (?,?,?,?,?,?)",
                            (prod[0], nom_c, cat_c, float(qte_c), unit_c, ref_c))
                    except Exception: pass
        conn.commit()
    except Exception:
        traceback.print_exc()


def _insert_only_stock(conn):
    """Insère uniquement le stock MP/Composants/Packaging et Produits finis."""
    import traceback
    try:
        c = conn.cursor()
        STOCK = [
            ("EWSWOOL-001A","Laine Whipcord Chocolate","Matière première","Tissu lourd",60.0,2,"Mètre"),
            ("EWSWOOL-001B","Laine Whipcord Tobacco","Matière première","Tissu lourd",60.0,4,"Mètre"),
            ("EWSWOOL-001C","Laine Whipcord Greige","Matière première","Tissu lourd",60.0,0,"Mètre"),
            ("EWSWOOL-001D","Laine Whipcord Sand","Matière première","Tissu lourd",60.0,2,"Mètre"),
            ("EWSWOOL-001E","Laine Whipcord Black","Matière première","Tissu lourd",60.0,0,"Mètre"),
            ("EWSCOTT-001A","Mix coton laine tartan Shadow","Matière première","Tissu léger",30.0,20,"Mètre"),
            ("EWSCOTT-001B","Mix coton laine tartan Clear","Matière première","Tissu léger",30.0,10,"Mètre"),
            ("EWSCELL-001A","Rayonne satinée rembourée Verte","Matière première","Tissu lourd",0,0,"Mètre"),
            ("EWSCELL-001B","Rayonne satinée Nishijin All-Over","Matière première","Tissus imprimé / motif",0,0,"Mètre"),
            ("EWSCELL-002A","Gabardine de rayonne Tobacco","Matière première","Tissu léger",0,0,"Mètre"),
            ("EWSCELL-003A","Rayonne satinée Crème","Matière première","Tissu léger",0,0,"Mètre"),
            ("EWSBLND-001A","Lin & Viscose Bleu Pigeon","Matière première","Tissu léger",15.0,0,"Mètre"),
            ("EWSBLND-001B","Lin & Viscose Vert Pastel","Matière première","Tissu léger",15.0,0,"Mètre"),
            ("EWSBLND-001C","Lin & Viscose Blanc Cassé","Matière première","Tissu léger",15.0,2,"Mètre"),
            ("EWSCOTT-003A","Voile de coton blanc","Matière première","Tissu léger",0,0,"Mètre"),
            ("EWSVSC-001A","Sergé de viscose All-Over","Matière première","Tissus imprimé / motif",21.67,0,"Mètre"),
            ("EWSCOTT-002A","Coton blanc casquette","Matière première","Maille",0,0,"Pièces"),
            ("EWSSOIE-001A","Soie Motif Trésor 55x55cm","Matière première","Tissus imprimé / motif",50.0,0,"Pièces"),
            ("EWSLEAT-001A","Wallet cuir de veau tanné marron","Matière première","Cuir",0,0,"Pièces"),
            ("EWSLEAT-002A","Lanière cuir végan","Matière première","Cuir",0,0,"Pièces"),
            ("EWSZIP-001A","Zip double face WALDES","Composant","Zip",0,0,"Pièces"),
            ("EWSZIP-002A","Zip chainette doré Talon Vintage 1960","Composant","Zip",9.0,7,"Pièces"),
            ("EWSZIP-002B","Zip doré Talon Vintage","Composant","Zip",0,0,"Pièces"),
            ("EWSBTN-001A","Boutton simple Maron 25mm","Composant","Bouton",1.0,0,"Pièces"),
            ("EWSBTN-002A","Boutons Équipement Militaires Vintage 1960","Composant","Bouton",1.3,5,"Pièces"),
            ("EWSBTN-003A","Boutons nacrés Eastwood Studio","Composant","Bouton",0.41,150,"Pièces"),
            ("EWSBTN-004A","Boutons cat's eye noir","Composant","Bouton",0,0,"Pièces"),
            ("EWSETQ-001A","Étiquette de composition","Composant","Étiquette",0.80,0,"Pièces"),
            ("EWSETQ-002A","Étiquette de taille T1 (S)","Composant","Étiquette",0.80,0,"Pièces"),
            ("EWSETQ-002B","Étiquette de taille T2 (M)","Composant","Étiquette",0.80,0,"Pièces"),
            ("EWSETQ-002C","Étiquette de taille T3 (L)","Composant","Étiquette",0.80,0,"Pièces"),
            ("EWSETQ-002D","Étiquette de taille T4 (XL)","Composant","Étiquette",0.80,0,"Pièces"),
            ("EWSETQ-003A","Étiquette fabrication Française","Composant","Étiquette",0.60,0,"Pièces"),
            ("EWSETQ-004A","Étiquette textile Eastwood Studio","Composant","Étiquette",0.35,0,"Pièces"),
            ("EWSPKG-001A","Tag numéro identification","Packaging","Packaging",0.20,0,"Pièces"),
            ("EWSPKG-002A","Pochette enveloppe postal XL craft","Packaging","Packaging",0,0,"Pièces"),
            ("EWSPKG-003A","Feuille recherche A4 craft","Packaging","Packaging",0,0,"Pièces"),
            ("EWSPKG-004A","Sticker logo blanc cercle","Packaging","Packaging",0,0,"Pièces"),
        ]
        for ref,nom,type_p,sous_t,cout,qte,unite in STOCK:
            try:
                c.execute("INSERT OR REPLACE INTO stock (ref,description,type_produit,sous_type,prix_unitaire,qte_stock,unite) VALUES (?,?,?,?,?,?,?)",
                    (ref,nom,type_p,sous_t,cout,qte,unite))
            except Exception: pass
        # Stock produits finis
        STOCK_PF = {"EWSJACKET-001A":0,"EWSJACKET-001B":1,"EWSJACKET-001C":0,"EWSJACKET-001D":0,"EWSJACKET-001E":0,
                    "EWSJACKET-002A":0,"EWSJACKET-003A":0,"EWSSHIRT-001A":3,"EWSSHIRT-001B":3,"EWSSHIRT-002A":0,
                    "EWSGEAR-001A":11,"EWSGEAR-001B":11,"EWSGEAR-002A":0,"EWSGEAR-003A":8}
        for sku, qte in STOCK_PF.items():
            row = c.execute("SELECT nom,couleurs FROM products WHERE ref=?", (sku,)).fetchone()
            if row:
                desc = row[0] + (" — " + row[1] if row[1] else "")
                try:
                    c.execute("INSERT OR REPLACE INTO stock (ref,description,type_produit,qte_stock,unite) VALUES (?,?,'Produit fini',?,'Pièces')",
                        (sku, desc, qte))
                except Exception: pass
        conn.commit()
    except Exception:
        traceback.print_exc()


def _insert_only_packagings(conn):
    """Insère uniquement les packagings types et items."""
    import traceback
    try:
        c = conn.cursor()
        PKGS = [
            ("Packaging Chapter I","Waterfowl Jackets B2C",[("EWSPKG-001A","Tag numéro identification",1),("EWSPKG-004A","Sticker logo blanc cercle",2),("EWSPKG-002A","Pochette enveloppe postal XL craft",1),("EWSPKG-003A","Feuille recherche A4 craft",1)]),
            ("Packaging Chapter II","Chapter II B2C",[("EWSPKG-001A","Tag numéro identification",1),("EWSPKG-004A","Sticker logo blanc cercle",2),("EWSPKG-003A","Feuille recherche A4 craft",1)]),
            ("Packaging Wholesale","B2B",[("EWSPKG-001A","Tag numéro identification",1),("EWSPKG-003A","Feuille recherche A4 craft",1)]),
            ("Packaging Prêt à Porté","B2C popup",[("EWSPKG-001A","Tag numéro identification",1),("EWSPKG-004A","Sticker logo blanc cercle",2),("EWSPKG-003A","Feuille recherche A4 craft",1)]),
        ]
        for nom, notes, items in PKGS:
            ex = c.execute("SELECT id FROM packaging_types WHERE nom=?", (nom,)).fetchone()
            if not ex:
                c.execute("INSERT INTO packaging_types (nom,notes) VALUES (?,?)", (nom, notes))
                pkg_id = c.lastrowid
            else:
                pkg_id = ex[0]
            for ref_i, nom_i, qte_i in items:
                ex_i = c.execute("SELECT id FROM packaging_items WHERE packaging_type_id=? AND ref_stock=?", (pkg_id, ref_i)).fetchone()
                if not ex_i:
                    c.execute("INSERT INTO packaging_items (packaging_type_id,ref_stock,nom_item,quantite) VALUES (?,?,?,?)", (pkg_id, ref_i, nom_i, qte_i))
        conn.commit()
    except Exception:
        traceback.print_exc()


def _insert_migration_data(conn):
    """Insère toutes les données réelles Eastwood Studio — source: tableau produits v2."""
    import traceback
    try:
        c = conn.cursor()

        # ── PURGE COMPLÈTE ────────────────────────────────────────────────────
        for tbl in ["product_components","product_archives","products",
                    "packaging_items","packaging_types"]:
            c.execute(f"DELETE FROM {tbl}")
        c.execute("DELETE FROM stock WHERE type_produit IN ('Matière première','Composant','Packaging','Produit fini')")
        conn.commit()

        # ══ PRODUITS FINIS ════════════════════════════════════════════════════
        # (nom, couleur, sku, collection, tailles, made_in, delivery, moq, statut, description, packaging_nom)
        PRODUCTS = [
            ("Waterfowl Jacket","Chocolate","EWSJACKET-001A",
             "Chapter I — Hunting & Fishing",
             "T1(S) / T2(M) / T3(L)","Paris, France","3 months",5,"Out of stock",
             "This jacket draws its inspiration from fishing and hunting garments. The jacket's short cut is inspired by 1940s fly-fishing clothing. It is entirely crafted from original 1950s French Whipcord and authentic 1950s French army buttons.",
             "Packaging Chapter I"),
            ("Waterfowl Jacket","Tobacco","EWSJACKET-001B",
             "Chapter I — Hunting & Fishing",
             "T1(S) / T2(M) / T3(L)","Paris, France","3 months",5,"Out of stock",
             "This jacket draws its inspiration from fishing and hunting garments. The jacket's short cut is inspired by 1940s fly-fishing clothing. It is entirely crafted from original 1950s French Whipcord and authentic 1950s French army buttons.",
             "Packaging Chapter I"),
            ("Waterfowl Jacket","Greige","EWSJACKET-001C",
             "Chapter I — Hunting & Fishing",
             "T1(S) / T2(M) / T3(L)","Paris, France","3 months",5,"Out of stock",
             "This jacket draws its inspiration from fishing and hunting garments. The jacket's short cut is inspired by 1940s fly-fishing clothing. It is entirely crafted from original 1950s French Whipcord and authentic 1950s French army buttons.",
             "Packaging Chapter I"),
            ("Waterfowl Jacket","Sand","EWSJACKET-001D",
             "Chapter I — Hunting & Fishing",
             "T1(S) / T2(M) / T3(L)","Paris, France","3 months",5,"Out of stock",
             "This jacket draws its inspiration from fishing and hunting garments. The jacket's short cut is inspired by 1940s fly-fishing clothing. It is entirely crafted from original 1950s French Whipcord and authentic 1950s French army buttons.",
             "Packaging Chapter I"),
            ("Waterfowl Jacket","Black","EWSJACKET-001E",
             "Chapter I — Hunting & Fishing",
             "T1(S) / T2(M) / T3(L)","Paris, France","4 months",5,"Out of stock",
             "This jacket draws its inspiration from fishing and hunting garments. The jacket's short cut is inspired by 1940s fly-fishing clothing. It is entirely crafted from original 1950s French Whipcord and authentic 1950s French army buttons.",
             "Packaging Chapter I"),
            ("Miura Jacket","","EWSJACKET-002A",
             "Chapter II — Le Souvenir",
             "T1(S) / T2(M) / T3(L) / T4(XL)","Kiriu, Japan","4 months",5,"Out of stock",
             "This design inspired by 1950s souvenir jackets features a Nishijin print (kimono pattern) and authentic Yokoburi embroidery made on a vintage machine using original 1950s embroidery patterns, complete with Waldes zippers.",
             "Packaging Chapter II"),
            ("Akagi Jacket","","EWSJACKET-003A",
             "Chapter II — Le Souvenir",
             "T1(S) / T2(M) / T3(L) / T4(XL)","Kiriu, Japan","3 months",5,"Out of stock",
             "This piece features authentic Yokoburi embroidery, executed on a vintage traditional machine, using an original embroidery pattern from the 1950s, and equipped with vintage Talon zippers.",
             "Packaging Chapter II"),
            ("Recherche Club Shirt","Cloud Blue","EWSSHIRT-001A",
             "Chapter II — Le Souvenir",
             "T1(S) / T2(M) / T3(L) / T4(XL)","Paris, France","3 months",5,"Out of stock",
             "Inspired by 1960s bowling shirts, featuring a rare double-breasted front, boxy tailored fit, chainstitched Cogg boat and Eiffel Tower embroidery, and mother of pearl buttons.",
             "Packaging Chapter II"),
            ("Recherche Club Shirt","Pastel Green","EWSSHIRT-001B",
             "Chapter II — Le Souvenir",
             "T1(S) / T2(M) / T3(L) / T4(XL)","Paris, France","3 months",5,"Out of stock",
             "Inspired by 1960s bowling shirts, featuring a rare double-breasted front, boxy tailored fit, chainstitched Cogg boat and Eiffel Tower embroidery, and mother of pearl buttons.",
             "Packaging Chapter II"),
            ("Lutèce Plage Shirt","","EWSSHIRT-002A",
             "Chapter II — Le Souvenir",
             "T1(S) / T2(M) / T3(L) / T4(XL)","Paris, France","3 months",5,"Out of stock",
             "Inspired by 1930s Hawaiian shirts and a 1910s hand-painted U.S. Navy jacket, featuring a relaxed fit, reworked open collar, custom buttons, and an allover signature printed in France.",
             "Packaging Chapter II"),
            ("Souvenir Cap","Deep Rust","EWSGEAR-001A",
             "Chapter II — Le Souvenir",
             "Adjustable Size","Paris, France","3 months",5,"Out of stock",
             "Inspired by postwar souvenir caps, reviving 1950s graphics through modern craftsmanship. Features front Eiffel Tower and palm tree embroidery, contrast sunfaded visor, side overstitching, back signature embroidery, and adjustable vegan leather strap.",
             "Packaging Chapter II"),
            ("Souvenir Cap","Faded Green","EWSGEAR-001B",
             "Chapter II — Le Souvenir",
             "Adjustable Size","Paris, France","3 months",5,"Out of stock",
             "Inspired by postwar souvenir caps, reviving 1950s graphics through modern craftsmanship. Features front Eiffel Tower and palm tree embroidery, contrast sunfaded visor, side overstitching, back signature embroidery, and adjustable vegan leather strap.",
             "Packaging Chapter II"),
            ("Paris le trésor Silk Square","","EWSGEAR-002A",
             "Chapter II — Le Souvenir",
             "Unique Size (55cm×55cm)","Paris, France","3 months",5,"Out of stock",
             "Inspired by souvenir bandanas once sold in roadside shops, this piece reimagines Paris as a distant island. Featuring hand-drawn motifs of monuments and symbols framed by a nautical rope border, printed on an off-white base in deep red and navy tones.",
             "Packaging Chapter II"),
            ("Memory Wallet","","EWSGEAR-003A",
             "Chapter II — Le Souvenir",
             "Unique Size (10cm×6.6cm)","Paris, France","3 months",5,"Out of stock",
             "Crafted with Parisian leatherworkers La Perruque, this wallet reinterprets 1950s souvenir pieces through French craftsmanship. Made from Baranil calf leather and Alran goatskin, it features a hand-painted tiger with French and Japanese flags.",
             "Packaging Chapter II"),
        ]

        for nom,coul,sku,coll,tailles,madein,deliv,moq,statut,desc,pkg in PRODUCTS:
            c.execute("""INSERT OR REPLACE INTO products
                (nom,ref,collection,statut,categorie,description,couleurs,
                 tailles,made_in,moq,delivery,origine)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (nom,sku,coll,statut,"Produit fini",desc,coul,
                 tailles,madein,str(moq),deliv,"Paris, France"))
        conn.commit()

        # ══ STOCK MATIÈRES PREMIÈRES / COMPOSANTS / PACKAGING ════════════════
        # (ref, nom, type_produit, sous_type, cout_unitaire, qte_stock, unite)
        STOCK = [
            # Matières premières — Tissus
            ("EWSWOOL-001A","Laine Whipcord Chocolate","Matière première","Tissu lourd",60.0,2,"Mètre"),
            ("EWSWOOL-001B","Laine Whipcord Tobacco","Matière première","Tissu lourd",60.0,4,"Mètre"),
            ("EWSWOOL-001C","Laine Whipcord Greige","Matière première","Tissu lourd",60.0,0,"Mètre"),
            ("EWSWOOL-001D","Laine Whipcord Sand","Matière première","Tissu lourd",60.0,2,"Mètre"),
            ("EWSWOOL-001E","Laine Whipcord Black","Matière première","Tissu lourd",60.0,0,"Mètre"),
            ("EWSCOTT-001A","Mix coton laine tartan Shadow","Matière première","Tissu léger",30.0,20,"Mètre"),
            ("EWSCOTT-001B","Mix coton laine tartan Clear","Matière première","Tissu léger",30.0,10,"Mètre"),
            ("EWSCELL-001A","Rayonne satinée rembourée Verte","Matière première","Tissu lourd",0.0,0,"Mètre"),
            ("EWSCELL-001B","Rayonne satinée Nishijin All-Over","Matière première","Tissus imprimé / motif",0.0,0,"Mètre"),
            ("EWSCELL-002A","Gabardine de rayonne Tobacco","Matière première","Tissu léger",0.0,0,"Mètre"),
            ("EWSCELL-003A","Rayonne satinée Crème","Matière première","Tissu léger",0.0,0,"Mètre"),
            ("EWSBLND-001A","Lin & Viscose Bleu Pigeon","Matière première","Tissu léger",15.0,0,"Mètre"),
            ("EWSBLND-001B","Lin & Viscose Vert Pastel","Matière première","Tissu léger",15.0,0,"Mètre"),
            ("EWSBLND-001C","Lin & Viscose Blanc Cassé","Matière première","Tissu léger",15.0,2,"Mètre"),
            ("EWSCOTT-003A","Voile de coton blanc","Matière première","Tissu léger",0.0,0,"Mètre"),
            ("EWSVSC-001A","Sergé de viscose All-Over","Matière première","Tissus imprimé / motif",21.67,0,"Mètre"),
            ("EWSCOTT-002A","Coton blanc casquette","Matière première","Maille",0.0,0,"Pièces"),
            ("EWSSOIE-001A","Soie Motif Trésor 55x55cm","Matière première","Tissus imprimé / motif",50.0,0,"Pièces"),
            ("EWSLEAT-001A","Wallet cuir de veau tanné marron","Matière première","Cuir",0.0,0,"Pièces"),
            ("EWSLEAT-002A","Lanière cuir végan","Matière première","Cuir",0.0,0,"Pièces"),
            # Composants — Zips
            ("EWSZIP-001A","Zip double face WALDES","Composant","Zip",0.0,0,"Pièces"),
            ("EWSZIP-002A","Zip chainette doré Talon Vintage 1960","Composant","Zip",9.0,7,"Pièces"),
            ("EWSZIP-002B","Zip doré Talon Vintage","Composant","Zip",0.0,0,"Pièces"),
            # Composants — Boutons
            ("EWSBTN-001A","Boutton simple Maron 25mm","Composant","Bouton",1.0,0,"Pièces"),
            ("EWSBTN-002A","Boutons Équipement Militaires Vintage 1960","Composant","Bouton",1.3,5,"Pièces"),
            ("EWSBTN-003A","Boutons nacrés Eastwood Studio","Composant","Bouton",0.41,150,"Pièces"),
            ("EWSBTN-004A","Boutons cat's eye noir","Composant","Bouton",0.0,0,"Pièces"),
            # Composants — Étiquettes
            ("EWSETQ-001A","Étiquette de composition","Composant","Étiquette",0.0,0,"Pièces"),
            ("EWSETQ-002A","Étiquette de taille T1 (S)","Composant","Étiquette",0.0,0,"Pièces"),
            ("EWSETQ-002B","Étiquette de taille T2 (M)","Composant","Étiquette",0.0,0,"Pièces"),
            ("EWSETQ-002C","Étiquette de taille T3 (L)","Composant","Étiquette",0.0,0,"Pièces"),
            ("EWSETQ-002D","Étiquette de taille T4 (XL)","Composant","Étiquette",0.0,0,"Pièces"),
            ("EWSETQ-003A","Étiquette fabrication Française","Composant","Étiquette",0.0,0,"Pièces"),
            ("EWSETQ-004A","Étiquette textile Eastwood Studio","Composant","Étiquette",0.0,0,"Pièces"),
            # Packaging
            ("EWSPKG-001A","Tag numéro identification","Packaging","Packaging",0.0,0,"Pièces"),
            ("EWSPKG-002A","Pochette enveloppe postal XL craft","Packaging","Packaging",0.0,0,"Pièces"),
            ("EWSPKG-003A","Feuille recherche A4 craft","Packaging","Packaging",0.0,0,"Pièces"),
            ("EWSPKG-004A","Sticker logo blanc cercle","Packaging","Packaging",0.0,0,"Pièces"),
        ]
        for ref,nom,type_p,sous_t,cout,qte,unite in STOCK:
            c.execute("""INSERT OR REPLACE INTO stock
                (ref,description,type_produit,sous_type,prix_unitaire,qte_stock,unite)
                VALUES (?,?,?,?,?,?,?)""",
                (ref,nom,type_p,sous_t,cout,qte,unite))
        conn.commit()

        # ══ STOCK PRODUITS FINIS ══════════════════════════════════════════════
        # Issu du tableau : colonne "Produit inventaire"
        STOCK_PF = {
            "EWSJACKET-001A": 0,
            "EWSJACKET-001B": 1,   # 1 T2
            "EWSJACKET-001C": 0,
            "EWSJACKET-001D": 0,
            "EWSJACKET-001E": 0,
            "EWSJACKET-002A": 0,
            "EWSJACKET-003A": 0,
            "EWSSHIRT-001A":  3,   # 2T2 + 1T1
            "EWSSHIRT-001B":  3,   # 1T1 + 1T2 + 1T3
            "EWSSHIRT-002A":  0,
            "EWSGEAR-001A":   11,
            "EWSGEAR-001B":   11,
            "EWSGEAR-002A":   0,
            "EWSGEAR-003A":   8,
        }
        for sku, qte in STOCK_PF.items():
            row = c.execute("SELECT nom,couleurs FROM products WHERE ref=?", (sku,)).fetchone()
            if row:
                desc_pf = row[0] + (" — " + row[1] if row[1] else "")
                c.execute("""INSERT OR REPLACE INTO stock
                    (ref,description,type_produit,qte_stock,unite)
                    VALUES (?,?,'Produit fini',?,'Pièces')""",
                    (sku, desc_pf, qte))
        conn.commit()

        # ══ COMPOSITION PAR PRODUIT ═══════════════════════════════════════════
        # Exactement selon le tableau ligne par ligne
        # (nom_exact, categorie_comp, quantite, unite, ref_stock)
        COMPS = {
            "EWSJACKET-001A": [
                ("Laine Whipcord Chocolate","MP Principale (Main Fabric)","2","Mètre","EWSWOOL-001A"),
                ("Mix coton laine tartan Shadow","Doublure","1.7","Mètre","EWSCOTT-001A"),
                ("Patch brodé logo EWS","Broderie","1","Pièces",""),
                ("Boutton simple Maron 25mm","Bouton","4","Pièces","EWSBTN-001A"),
                ("Boutons Équipement Militaires Vintage 1960","Bouton","8","Pièces","EWSBTN-002A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSJACKET-001B": [
                ("Laine Whipcord Tobacco","MP Principale (Main Fabric)","2","Mètre","EWSWOOL-001B"),
                ("Mix coton laine tartan Shadow","Doublure","1.7","Mètre","EWSCOTT-001A"),
                ("Patch brodé logo EWS","Broderie","1","Pièces",""),
                ("Boutton simple Maron 25mm","Bouton","4","Pièces","EWSBTN-001A"),
                ("Boutons Équipement Militaires Vintage 1960","Bouton","8","Pièces","EWSBTN-002A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSJACKET-001C": [
                ("Laine Whipcord Greige","MP Principale (Main Fabric)","2","Mètre","EWSWOOL-001C"),
                ("Mix coton laine tartan Shadow","Doublure","1.7","Mètre","EWSCOTT-001A"),
                ("Patch brodé logo EWS","Broderie","1","Pièces",""),
                ("Boutton simple Maron 25mm","Bouton","4","Pièces","EWSBTN-001A"),
                ("Boutons Équipement Militaires Vintage 1960","Bouton","8","Pièces","EWSBTN-002A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSJACKET-001D": [
                ("Laine Whipcord Sand","MP Principale (Main Fabric)","2","Mètre","EWSWOOL-001D"),
                ("Mix coton laine tartan Clear","Doublure","1.7","Mètre","EWSCOTT-001B"),
                ("Patch brodé logo EWS","Broderie","1","Pièces",""),
                ("Boutton simple Maron 25mm","Bouton","4","Pièces","EWSBTN-001A"),
                ("Boutons Équipement Militaires Vintage 1960","Bouton","8","Pièces","EWSBTN-002A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSJACKET-001E": [
                ("Laine Whipcord Black","MP Principale (Main Fabric)","2","Mètre","EWSWOOL-001E"),
                ("Mix coton laine tartan Clear","Doublure","1.7","Mètre","EWSCOTT-001B"),
                ("Patch brodé logo EWS","Broderie","1","Pièces",""),
                ("Boutton simple Maron 25mm","Bouton","4","Pièces","EWSBTN-001A"),
                ("Boutons Équipement Militaires Vintage 1960","Bouton","8","Pièces","EWSBTN-002A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSJACKET-002A": [
                ("Rayonne satinée rembourée Verte","MP Principale (Main Fabric)","2","Mètre","EWSCELL-001A"),
                ("Rayonne satinée Nishijin EWS","Doublure","2","Mètre","EWSCELL-001B"),
                ("Dos brodé cigogne (Yokoburi)","Broderie","1","Pièces",""),
                ("Zip double face WALDES","Zip","1","Pièces","EWSZIP-001A"),
                ("Boutons cat's eye noir","Bouton","2","Pièces","EWSBTN-004A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSJACKET-003A": [
                ("Gabardine de rayonne Tobacco","MP Principale (Main Fabric)","2","Mètre","EWSCELL-002A"),
                ("Rayonne satinée Crème","Doublure","2","Mètre","EWSCELL-003A"),
                ("Dos brodé Paon — Patron 1950 (Yokoburi)","Broderie","1","Pièces",""),
                ("Zip chainette doré Talon Vintage 1960","Zip","1","Pièces","EWSZIP-002A"),
                ("Zip doré Talon Vintage (secondaire)","Zip","1","Pièces","EWSZIP-002B"),
                ("Boutons cat's eye noir","Bouton","2","Pièces","EWSBTN-004A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSSHIRT-001A": [
                ("Lin & Viscose Bleu Pigeon","MP Principale (Main Fabric)","1.7","Mètre","EWSBLND-001A"),
                ("Lin & Viscose Blanc Cassé","MP Secondaire","0.9","Mètre","EWSBLND-001C"),
                ("Voile de coton blanc","Doublure","0.6","Mètre","EWSCOTT-003A"),
                ("Dos brodé Club Recherche EWS (Chainstitch)","Broderie","1","Pièces",""),
                ("Boutons nacrés Eastwood Studio","Bouton","10","Pièces","EWSBTN-003A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSSHIRT-001B": [
                ("Lin & Viscose Vert Pastel","MP Principale (Main Fabric)","1.7","Mètre","EWSBLND-001B"),
                ("Lin & Viscose Blanc Cassé","MP Secondaire","0.9","Mètre","EWSBLND-001C"),
                ("Voile de coton blanc","Doublure","0.6","Mètre","EWSCOTT-003A"),
                ("Dos brodé Club Recherche EWS (Chainstitch)","Broderie","1","Pièces",""),
                ("Boutons nacrés Eastwood Studio","Bouton","10","Pièces","EWSBTN-003A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSSHIRT-002A": [
                ("Sergé de viscose All-Over","MP Principale (Main Fabric)","1.9","Mètre","EWSVSC-001A"),
                ("Voile de coton blanc","Doublure","0.6","Mètre","EWSCOTT-003A"),
                ("Boutons nacrés Eastwood Studio","Bouton","5","Pièces","EWSBTN-003A"),
                ("Étiquette de composition","Étiquette","1","Pièces","EWSETQ-001A"),
                ("Étiquette de taille","Étiquette","1","Pièces",""),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
                ("Étiquette textile Eastwood Studio","Étiquette","1","Pièces","EWSETQ-004A"),
            ],
            "EWSGEAR-001A": [
                ("Coton blanc casquette","MP Principale (Main Fabric)","1","Pièces","EWSCOTT-002A"),
                ("Lanière cuir végan","MP Secondaire","1","Pièces","EWSLEAT-002A"),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
            ],
            "EWSGEAR-001B": [
                ("Coton blanc casquette","MP Principale (Main Fabric)","1","Pièces","EWSCOTT-002A"),
                ("Lanière cuir végan","MP Secondaire","1","Pièces","EWSLEAT-002A"),
                ("Étiquette fabrication Française","Étiquette","1","Pièces","EWSETQ-003A"),
            ],
            "EWSGEAR-002A": [
                ("Soie Motif Trésor 55x55cm","MP Principale (Main Fabric)","1","Pièces","EWSSOIE-001A"),
            ],
            "EWSGEAR-003A": [
                ("Wallet cuir de veau tanné marron","MP Principale (Main Fabric)","1","Pièces","EWSLEAT-001A"),
                ("Peinture main — Xavier Boully","Peinture","1","Pièces",""),
            ],
        }
        for sku, comps in COMPS.items():
            prod = c.execute("SELECT id FROM products WHERE ref=?", (sku,)).fetchone()
            if prod:
                for nom_c, cat_c, qte_c, unit_c, ref_c in comps:
                    c.execute("""INSERT INTO product_components
                        (product_id,nom_exact,categorie_comp,quantite,unite,ref_stock)
                        VALUES (?,?,?,?,?,?)""",
                        (prod[0], nom_c, cat_c, float(qte_c), unit_c, ref_c))
        conn.commit()

        # ══ ARCHIVES PAR COLLECTION ═══════════════════════════════════════════
        ARCHIVES = [
            ("Chapter I — Hunting & Fishing","Shooting","Shooting Chapter I — Berlin Airport Tempelhof","2024",
             "Shooting principal Chapter I — Berlin, Aéroport Tempelhof. Ambiance chasse et pêche vintage des années 1940-1950."),
            ("Chapter I — Hunting & Fishing","Moodboard","Moodboard Hunting & Fishing","2023",
             "Références visuelles chasse anglaise, pêche vintage, vestes Whipcord années 1950. Boutons équipement militaire français."),
            ("Chapter II — Le Souvenir","Shooting","Shooting Chapter II — Berlin","2025",
             "Shooting principal Chapter II — Berlin été 2025. Références souvenir japonais, Berlin, Paris. Sukajan, casquettes vintage."),
            ("Chapter II — Le Souvenir","Moodboard","Moodboard Le Souvenir","2024",
             "Références visuelles sukajan japonais 1950s, Nishijin, Yokoburi, bowling shirts, imprimés all-over."),
            ("Chapter II — Le Souvenir","Référence","Référence Yokoburi — Kiryu Jumper Lab","2024",
             "Broderie Yokoburi traditionnelle japonaise sur machine vintage. Kiryu Jumper Lab, Kiryu City, Gunma Prefecture."),
        ]
        for coll, arc_type, arc_nom, annee, details in ARCHIVES:
            prods_c = c.execute("SELECT id FROM products WHERE collection=?", (coll,)).fetchall()
            for (pid,) in prods_c:
                c.execute("""INSERT INTO product_archives
                    (product_id,type_archive,nom_archive,annee,details)
                    VALUES (?,?,?,?,?)""",
                    (pid, arc_type, arc_nom, int(annee), details))
        conn.commit()

        # ══ FOURNISSEURS ══════════════════════════════════════════════════════
        FOURNISSEURS = [
            ("Rêve de Gosse","Matière première","France","Laines Whipcord (Chocolate, Tobacco, Greige, Sand, Black) et tartans (Shadow, Clear) pour Waterfowl Jackets"),
            ("Kiryu Jumper Lab","Production / Confection","Japon","Fabrication complète Miura Jacket & Akagi Jacket. Broderie Yokoburi. Matières japonaises (rayonne satinée, Nishijin). Kiryu City, Gunma Prefecture."),
            ("Le bar à broder","Impression / Broderie","France","Broderie main patch logo EWS sur Waterfowl Jackets (toutes couleurs)"),
            ("Salhedine Chainstitch","Impression / Broderie","France","Broderie chainstitch dos pour Recherche Club Shirt (Cloud Blue & Pastel Green)"),
            ("Dam Bouton","Composant","France","Boutons simples marron 25mm pour Waterfowl Jackets"),
            ("LeBonCoin","Composant","France","Boutons équipement militaire français vintage 1960 pour Waterfowl Jackets"),
            ("A&A Patrons (ma fashion mercerie)","Composant","France","Étiquettes de composition pour tous les produits"),
            ("Rubantin","Composant","France","Étiquettes de taille pour tous les produits"),
            ("mapetitemercerie","Composant","France","Étiquettes fabrication française et étiquettes textile Eastwood Studio"),
            ("Textrend.fr","Matière première","France","Lin & Viscose (Bleu Pigeon, Vert Pastel, Blanc Cassé) pour Recherche Club Shirts"),
            ("Insho Atelier","Matière première","France","Sergé de viscose All-Over pour Lutèce Plage Shirt + Soie Motif Trésor pour Silk Square"),
            ("Xiangtong","Matière première","Chine","Coton blanc casquette et lanière cuir végan pour Souvenir Cap"),
            ("Yiwu Aiyi E-Commerce Firm","Composant","Chine","Boutons nacrés Eastwood Studio pour Recherche Club Shirts et Lutèce Plage Shirt"),
            ("Ebay (vinty82)","Composant","France","Zip chainette doré Talon Vintage 1960 pour Akagi Jacket"),
            ("Laperruque","Matière première","France","Cuir de veau tanné marron (Baranil & Alran) pour Memory Wallet"),
            ("Xavier Boully","Impression / Broderie","France","Peinture main tigre sur Memory Wallet"),
        ]
        for nom_f, sous_t, pays, notes in FOURNISSEURS:
            ex = c.execute("SELECT id FROM contacts WHERE nom=? AND type_contact='Fournisseur'", (nom_f,)).fetchone()
            if not ex:
                c.execute("""INSERT INTO contacts (nom,type_contact,sous_type,pays,notes,importance)
                    VALUES (?,'Fournisseur',?,?,?,'Normal')""", (nom_f, sous_t, pays, notes))
            try:
                ex_f = c.execute("SELECT id FROM fournisseurs WHERE nom=?", (nom_f,)).fetchone()
                if not ex_f:
                    c.execute("""INSERT INTO fournisseurs (nom,sous_type,pays,notes,deja_travaille,statut_fourn,importance)
                        VALUES (?,?,?,?,1,'Actif — on travaille','Normal')""", (nom_f, sous_t, pays, notes))
            except Exception:
                pass
        conn.commit()

        # ══ PACKAGINGS TYPES ═════════════════════════════════════════════════
        # Exactement selon le tableau colonne Packaging
        PKGS = [
            ("Packaging Chapter I", "Waterfowl Jackets — B2C retail", [
                ("EWSPKG-001A", "Tag numéro identification", 1),
                ("EWSPKG-004A", "Sticker logo blanc cercle", 2),
                ("EWSPKG-002A", "Pochette enveloppe postal XL craft", 1),
                ("EWSPKG-003A", "Feuille recherche A4 craft", 1),
            ]),
            ("Packaging Chapter II", "Chapter II (Jackets, Shirts, Caps, Accessoires) — B2C retail", [
                ("EWSPKG-001A", "Tag numéro identification", 1),
                ("EWSPKG-004A", "Sticker logo blanc cercle", 2),
                ("EWSPKG-003A", "Feuille recherche A4 craft", 1),
            ]),
            ("Packaging Wholesale", "B2B Wholesale — Tag + feuille recherche", [
                ("EWSPKG-001A", "Tag numéro identification", 1),
                ("EWSPKG-003A", "Feuille recherche A4 craft", 1),
            ]),
            ("Packaging Prêt à Porté", "B2C site web / popup — sans pochette", [
                ("EWSPKG-001A", "Tag numéro identification", 1),
                ("EWSPKG-004A", "Sticker logo blanc cercle", 2),
                ("EWSPKG-003A", "Feuille recherche A4 craft", 1),
            ]),
        ]
        for pkg_nom, pkg_notes, pkg_items in PKGS:
            ex_pkg = c.execute("SELECT id FROM packaging_types WHERE nom=?", (pkg_nom,)).fetchone()
            if ex_pkg:
                pkg_id = ex_pkg[0]
            else:
                c.execute("INSERT INTO packaging_types (nom,notes) VALUES (?,?)", (pkg_nom, pkg_notes))
                pkg_id = c.lastrowid
            for ref_i, nom_i, qte_i in pkg_items:
                ex_pi = c.execute("SELECT id FROM packaging_items WHERE packaging_type_id=? AND ref_stock=?",
                                  (pkg_id, ref_i)).fetchone()
                if not ex_pi:
                    c.execute("""INSERT INTO packaging_items
                        (packaging_type_id,ref_stock,nom_item,quantite)
                        VALUES (?,?,?,?)""", (pkg_id, ref_i, nom_i, qte_i))
        conn.commit()

        # Marquer comme terminé
        c.execute("INSERT OR REPLACE INTO app_settings (key,value) VALUES ('data_migration_v3','done')")
        conn.commit()

    except Exception:
        traceback.print_exc()
        try: conn.rollback()
        except: pass


def init_products_db(conn):
    """Initialise la base produits. Try/except global pour debug Streamlit Cloud."""
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ref TEXT UNIQUE NOT NULL,
        internal_ref TEXT,
        nom TEXT NOT NULL,
        variant TEXT,
        categorie TEXT,
        collection TEXT,
        statut TEXT DEFAULT 'Développement',
        description TEXT,
        matieres TEXT,
        couleurs TEXT,
        tailles TEXT,
        made_in TEXT,
        prix_retail_eur REAL DEFAULT 0,
        prix_retail_jpy REAL DEFAULT 0,
        prix_retail_usd REAL DEFAULT 0,
        prix_wholesale_eu REAL DEFAULT 0,
        prix_wholesale_asia REAL DEFAULT 0,
        prix_wholesale_us REAL DEFAULT 0,
        prix_ff REAL DEFAULT 0,
        cost_eur REAL DEFAULT 0,
        moq INTEGER DEFAULT 0,
        delivery TEXT,
        origine TEXT,
        a_verifier INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Migrations silencieuses
    existing_cols = [r[1] for r in c.execute("PRAGMA table_info(products)").fetchall()]
    for col, defn in [
        ("internal_ref", "TEXT"), ("variant", "TEXT"), ("categorie", "TEXT"),
        ("cost_eur", "REAL DEFAULT 0"), ("a_verifier", "INTEGER DEFAULT 0"),
        ("made_in", "TEXT"), ("moq", "INTEGER DEFAULT 0"),
        ("delivery", "TEXT"), ("origine", "TEXT"),
        ("prix_retail_usd", "REAL DEFAULT 0"),
        ("prix_wholesale_eu", "REAL DEFAULT 0"),
        ("prix_wholesale_asia", "REAL DEFAULT 0"),
        ("prix_wholesale_us", "REAL DEFAULT 0"),
        ("prix_wholesale_fr", "REAL DEFAULT 0"),
        ("prix_ff", "REAL DEFAULT 0"),
    ]:
        if col not in existing_cols:
            try: c.execute(f"ALTER TABLE products ADD COLUMN {col} {defn}")
            except Exception: pass

    c.execute("""CREATE TABLE IF NOT EXISTS product_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        nom_fichier TEXT,
        data BLOB,
        ordre INTEGER DEFAULT 0,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS product_components (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        categorie_comp TEXT DEFAULT 'MP Principale (Main Fabric)',
        ref_stock TEXT,
        nom TEXT,
        nom_exact TEXT,
        quantite REAL DEFAULT 0,
        unite TEXT DEFAULT 'Mètre',
        cout_unitaire REAL DEFAULT 0,
        moq REAL DEFAULT 0,
        moq_unite TEXT DEFAULT 'Mètre',
        fournisseur TEXT,
        notes TEXT,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")

    # Migrations composants
    existing_comp = [r[1] for r in c.execute("PRAGMA table_info(product_components)").fetchall()]
    for col, defn in [
        ("categorie_comp", "TEXT DEFAULT 'MP Principale (Main Fabric)'"),
        ("nom_exact", "TEXT"), ("moq", "REAL DEFAULT 0"),
        ("moq_unite", "TEXT DEFAULT 'Mètre'"), ("fournisseur", "TEXT"), ("notes", "TEXT"),
    ]:
        if col not in existing_comp:
            try: c.execute(f"ALTER TABLE product_components ADD COLUMN {col} {defn}")
            except Exception: pass

    c.execute("""CREATE TABLE IF NOT EXISTS product_archives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        annee INTEGER, type_archive TEXT, matiere TEXT,
        nom_archive TEXT, lieu TEXT, details TEXT,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")
    # Migration : recréer product_archives sans nom_fichier si nécessaire
    try:
        _arc_cols = [r[1] for r in c.execute("PRAGMA table_info(product_archives)").fetchall()]
        if "nom_fichier" in _arc_cols:
            c.execute("ALTER TABLE product_archives RENAME TO _arc_bak")
            c.execute(
                "CREATE TABLE product_archives ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "product_id INTEGER,annee INTEGER,"
                "type_archive TEXT,nom_archive TEXT,"
                "lieu TEXT,details TEXT,"
                "FOREIGN KEY(product_id) REFERENCES products(id))"
            )
            c.execute(
                "INSERT INTO product_archives (product_id,annee,type_archive,nom_archive,lieu,details)"
                " SELECT product_id,annee,type_archive,nom_archive,lieu,details FROM _arc_bak"
            )
            c.execute("DROP TABLE _arc_bak")
            conn.commit()
    except Exception: pass
    # Migration colonne annee si absente
    _arc_cols = [r[1] for r in c.execute("PRAGMA table_info(product_archives)").fetchall()]
    for _acol, _adef in [("annee","INTEGER DEFAULT 0"),("details","TEXT DEFAULT ''"),("nom_archive","TEXT DEFAULT ''")]:
        if _acol not in _arc_cols:
            try: c.execute(f"ALTER TABLE product_archives ADD COLUMN {_acol} {_adef}")
            except Exception: pass



    # Coûts enrichis
    c.execute("""CREATE TABLE IF NOT EXISTS product_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER UNIQUE,
        cout_patronage REAL DEFAULT 0, cout_gradation REAL DEFAULT 0,
        cout_assemblage REAL DEFAULT 0, cout_production REAL DEFAULT 0,
        cout_mp1_sample REAL DEFAULT 0, cout_mp2_sample REAL DEFAULT 0, cout_mp3_sample REAL DEFAULT 0,
        cout_compo1_sample REAL DEFAULT 0, cout_compo2_sample REAL DEFAULT 0, cout_compo3_sample REAL DEFAULT 0,
        cout_log_sample REAL DEFAULT 0,
        cout_mp_principale REAL DEFAULT 0, cout_mp_secondaire REAL DEFAULT 0,
        cout_lining REAL DEFAULT 0, cout_zip REAL DEFAULT 0, cout_boutons REAL DEFAULT 0,
        cout_broderie_principale REAL DEFAULT 0, cout_broderie_secondaire REAL DEFAULT 0,
        cout_patch REAL DEFAULT 0, cout_print REAL DEFAULT 0,
        cout_etiq_textile REAL DEFAULT 0, cout_etiq_taille REAL DEFAULT 0,
        cout_etiq_compo REAL DEFAULT 0, cout_etiq_fab_fr REAL DEFAULT 0, cout_tag_numero REAL DEFAULT 0,
        cout_montage REAL DEFAULT 0, cout_coupe REAL DEFAULT 0, cout_finition REAL DEFAULT 0,
        cout_stockage REAL DEFAULT 0, cout_emballage REAL DEFAULT 0,
        cout_appro REAL DEFAULT 0, cout_douane REAL DEFAULT 0,
        cout_boite REAL DEFAULT 0, cout_sac REAL DEFAULT 0,
        cout_feuille_expl REAL DEFAULT 0, cout_lettre REAL DEFAULT 0,
        cout_enveloppe REAL DEFAULT 0, cout_stickers REAL DEFAULT 0,
        cout_marketing REAL DEFAULT 0,
        prix_vente_cible REAL DEFAULT 0, prix_vente_normalise REAL DEFAULT 0,
        prix_reco_wholesale REAL DEFAULT 0, prix_wholesale_japan REAL DEFAULT 0,
        prix_rdm REAL DEFAULT 0, srp_eu REAL DEFAULT 0, srp_jpn REAL DEFAULT 0, srp_rdm REAL DEFAULT 0,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")

    # Packaging dédié (commun à tous les produits)
    c.execute("""CREATE TABLE IF NOT EXISTS packaging_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        notes TEXT DEFAULT '',
        cout_total REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS packaging_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        packaging_type_id INTEGER,
        ref_stock TEXT,
        nom_item TEXT,
        quantite REAL DEFAULT 1,
        cout_unitaire REAL DEFAULT 0,
        FOREIGN KEY(packaging_type_id) REFERENCES packaging_types(id)
    )""")
    # Migration : recalculer cout_total dans packaging_types si absent
    try:
        c.execute("SELECT cout_total FROM packaging_types LIMIT 1")
    except Exception:
        try: c.execute("ALTER TABLE packaging_types ADD COLUMN cout_total REAL DEFAULT 0")
        except Exception: pass
    # Migration colonnes product_costs — ajouter colonnes manquantes
    try:
        _pc_cols = [r[1] for r in c.execute("PRAGMA table_info(product_costs)").fetchall()]
        for _mc, _md in [
            ("cout_peinture","REAL DEFAULT 0"),("cout_tax","REAL DEFAULT 0"),
            ("cout_douane_eu","REAL DEFAULT 0"),("cout_douane_us","REAL DEFAULT 0"),
            ("cout_douane_jp","REAL DEFAULT 0"),("cout_prints_secondaire","REAL DEFAULT 0"),
            ("cout_marketing_pct","REAL DEFAULT 0"),("cout_zip_principal","REAL DEFAULT 0"),
            ("cout_zip_secondaire","REAL DEFAULT 0"),("cout_bouton_principal","REAL DEFAULT 0"),
            ("cout_bouton_secondaire","REAL DEFAULT 0"),
            ("packaging_type_id","INTEGER DEFAULT 0"),("cout_packaging","REAL DEFAULT 0"),
            ("packaging_retail_id","INTEGER DEFAULT 0"),("packaging_wholesale_id","INTEGER DEFAULT 0"),
            ("cout_packaging_retail","REAL DEFAULT 0"),("cout_packaging_wholesale","REAL DEFAULT 0"),
            ("etiq_textile","INTEGER DEFAULT 0"),("etiq_taille","INTEGER DEFAULT 0"),
            ("etiq_compo","INTEGER DEFAULT 0"),("etiq_fab_fr","INTEGER DEFAULT 0"),("etiq_tag_num","INTEGER DEFAULT 0"),
        ]:
            if _mc not in _pc_cols:
                try: c.execute(f"ALTER TABLE product_costs ADD COLUMN {_mc} {_md}")
                except Exception: pass
        conn.commit()
    except Exception: pass
    # Migration colonnes product_costs pour packaging_type_id et étiquettes
    _pc_cols = [r[1] for r in c.execute("PRAGMA table_info(product_costs)").fetchall()] if c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='product_costs'").fetchone()[0] else []
    for _mc, _md in [("packaging_type_id","INTEGER DEFAULT 0"),("cout_packaging","REAL DEFAULT 0"),
                     ("packaging_retail_id","INTEGER DEFAULT 0"),("packaging_wholesale_id","INTEGER DEFAULT 0"),
                     ("cout_packaging_retail","REAL DEFAULT 0"),("cout_packaging_wholesale","REAL DEFAULT 0"),
                     ("etiq_textile","INTEGER DEFAULT 0"),("etiq_taille","INTEGER DEFAULT 0"),
                     ("etiq_compo","INTEGER DEFAULT 0"),("etiq_fab_fr","INTEGER DEFAULT 0"),("etiq_tag_num","INTEGER DEFAULT 0"),
                     ("cout_etiq_textile","REAL DEFAULT 0"),("cout_etiq_taille","REAL DEFAULT 0"),
                     ("cout_etiq_compo","REAL DEFAULT 0"),("cout_etiq_fab_fr","REAL DEFAULT 0"),("cout_etiq_tag_num","REAL DEFAULT 0")]:
        if _mc not in _pc_cols:
            try: c.execute(f"ALTER TABLE product_costs ADD COLUMN {_mc} {_md}")
            except Exception: pass
    c.execute("""CREATE TABLE IF NOT EXISTS packaging_standard (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        ref_stock TEXT,
        quantite REAL DEFAULT 1,
        unite TEXT DEFAULT 'Pièces',
        cout_unitaire REAL DEFAULT 0,
        actif INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Seed produits
    try:
        c.execute("SELECT COUNT(*) FROM products")
    except Exception:
        conn.commit()
        return  # Table pas encore créée
    if c.fetchone()[0] == 0:
        for p in PRODUCTS_SEED:
            try:
                c.execute("""INSERT OR IGNORE INTO products
                (ref, internal_ref, nom, variant, categorie, collection, statut,
                 description, matieres, couleurs, tailles,
                 prix_retail_eur, prix_wholesale_eu, cost_eur, moq, delivery, origine)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (p["ref"], p.get("internal_ref",""), p["nom"], p.get("variant",""),
                 p.get("categorie",""), p.get("collection",""), p.get("statut","Disponible"),
                 p.get("description",""), p.get("matieres",""), p.get("couleurs",""),
                 p.get("tailles",""),
                 p.get("prix_retail_eur",0), p.get("prix_wholesale_fr",0),
                 p.get("cost_eur",0), p.get("moq",0),
                 p.get("delivery",""), p.get("origine","")))
            except Exception as _seed_e:
                import streamlit as _st2
                _st2.warning(f"Seed erreur produit {p.get('ref','?')} : {_seed_e}")
                continue

    # Seed packaging
    c.execute("SELECT COUNT(*) FROM packaging_standard")
    if c.fetchone()[0] == 0:
        for pk in PACKAGING_STANDARD:
            c.execute("""INSERT INTO packaging_standard
                (nom, ref_stock, quantite, unite) VALUES (?,?,?,?)""",
                (pk["nom"], pk["ref_stock"], pk["qte"], pk["unite"]))

    # Migrations silencieuses : nouvelles colonnes coûts
    existing_cost_cols = [r[1] for r in c.execute("PRAGMA table_info(product_costs)").fetchall()]
    for col, defn in COST_NEW_COLS:
        if col not in existing_cost_cols:
            try: c.execute(f"ALTER TABLE product_costs ADD COLUMN {col} {defn}")
            except Exception: pass

    conn.commit()

    # ── Migration données Eastwood Studio ────────────────────────────────
    run_data_migration(conn)


def get_products(conn, collection=None, statut=None, categorie=None):
    q = "SELECT * FROM products WHERE 1=1"
    p = []
    if collection: q += " AND collection=?"; p.append(collection)
    if statut:     q += " AND statut=?";     p.append(statut)
    if categorie:  q += " AND categorie=?";  p.append(categorie)
    return pd.read_sql(q + " ORDER BY collection, categorie, nom, variant", conn, params=p)


def get_product(conn, pid):
    return pd.read_sql("SELECT * FROM products WHERE id=?", conn, params=[pid])


def get_images(conn, pid):
    return pd.read_sql("SELECT * FROM product_images WHERE product_id=? ORDER BY ordre",
                       conn, params=[pid])


def get_components(conn, pid):
    return pd.read_sql(
        "SELECT * FROM product_components WHERE product_id=? ORDER BY categorie_comp, id",
        conn, params=[pid])


def get_costs(conn, pid):
    df = pd.read_sql("SELECT * FROM product_costs WHERE product_id=?", conn, params=[pid])
    return df.iloc[0] if not df.empty else None


def get_packaging(conn):
    return pd.read_sql("SELECT * FROM packaging_standard WHERE actif=1 ORDER BY nom", conn)


def fmt_eur(v):
    if v is None or (isinstance(v, (int, float)) and v == 0): return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


def fmt_jpy(v):
    if v is None or v == 0: return "—"
    return f"¥ {float(v):,.0f}"


# ── AUTO-SYNC commande → stock ─────────────────────────────────────────────────
def sync_from_commande(conn, ref_article, qte, client_nom, client_prenom,
                       client_email, client_tel, client_adresse, prix_ttc,
                       plateforme, num_commande):
    try:
        # 1. Vérifier si produit fini en stock
        pf_row = conn.execute(
            "SELECT qte_stock FROM stock WHERE ref=? AND type_produit='Produit fini'",
            (ref_article,)).fetchone()
        if pf_row and float(pf_row[0] or 0) >= float(qte):
            # Déduire du stock PF directement
            conn.execute("""UPDATE stock SET
                qte_vendue=qte_vendue+?, qte_stock=MAX(0,qte_stock-?) WHERE ref=?""",
                (qte, qte, ref_article))
        else:
            # Produit à produire → déduire les MP/composants
            prod = conn.execute("SELECT id FROM products WHERE ref=?", (ref_article,)).fetchone()
            if prod:
                comps = conn.execute(
                    "SELECT ref_stock, quantite FROM product_components WHERE product_id=?",
                    (prod[0],)).fetchall()
                for ref_mp, qte_mp in comps:
                    if ref_mp:
                        needed = float(qte_mp) * float(qte)
                        conn.execute("""UPDATE stock SET
                            qte_utilisee=qte_utilisee+?, qte_stock=MAX(0,qte_stock-?)
                            WHERE ref=?""", (needed, needed, ref_mp))
            # Déduire packaging
            pkg_items = conn.execute(
                "SELECT ref_stock, quantite FROM packaging_standard WHERE actif=1").fetchall()
            for ref_pkg, qte_pkg in pkg_items:
                if ref_pkg:
                    conn.execute("""UPDATE stock SET
                        qte_utilisee=qte_utilisee+?, qte_stock=MAX(0,qte_stock-?)
                        WHERE ref=?""", (float(qte_pkg)*float(qte), float(qte_pkg)*float(qte), ref_pkg))

        # 2. Contact client auto
        if client_email:
            existing = conn.execute(
                "SELECT id FROM contacts WHERE email=?", (client_email,)).fetchone()
            if not existing:
                conn.execute("""INSERT INTO contacts
                    (type_contact,sous_type,nom,email,telephone,adresse,importance,notes)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    ("Client","Ponctuel",f"{client_prenom} {client_nom}".strip(),
                     client_email,client_tel,client_adresse,"Normal",
                     f"Client commande {num_commande} via {plateforme}"))

        # 3. Transaction vente auto
        from datetime import date as dt_date
        today = dt_date.today()
        conn.execute("""INSERT INTO transactions
            (annee,mois,date_op,ref_produit,info_process,description,categorie,type_op,
             quantite,unite,prix_unitaire,type_tva,total_ht,total_ttc,tva,
             devise,taux_change,montant_original,payeur,beneficiaire,source,info_complementaire)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (today.year,today.month,str(today),
             ref_article,"Vente produit",f"Commande {num_commande} — {client_prenom} {client_nom}",
             "Facture","Vente",qte,"Article",
             round(prix_ttc/1.2/qte,2) if qte>0 else 0,
             "Collectée",round(prix_ttc/1.2,2),prix_ttc,
             round(prix_ttc-prix_ttc/1.2,2),
             "EUR",1.0,round(prix_ttc/1.2,2),
             f"{client_prenom} {client_nom}","Eastwood Studio",
             plateforme,f"N°{num_commande}"))
        conn.commit()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION ORDER SHEET (une page par produit, style document vierge)
# ══════════════════════════════════════════════════════════════════════════════
def generate_order_sheet(conn, collection_filter=None):
    """Order sheet : 1 produit par SKU (chaque coloris = 1 ligne distincte), 4 produits/page."""
    if not REPORTLAB_OK:
        return None, "reportlab non installé"

    buf = io.BytesIO()
    W, H = A4
    M = 12 * mm

    EW_C_rl  = colors.HexColor("#f5f0e8")
    EW_S_rl  = colors.HexColor("#ede3d3")
    EW_K_rl  = colors.HexColor("#1a1a1a")
    EW_B_rl  = colors.HexColor("#8a7968")
    EW_V_rl  = colors.HexColor("#7b506f")
    GREY_rl  = colors.HexColor("#f0ede8")
    GREY2_rl = colors.HexColor("#fafaf8")

    q = "SELECT * FROM products WHERE 1=1"
    p = []
    if collection_filter:
        q += " AND collection=?"; p.append(collection_filter)
    df = pd.read_sql(q + " ORDER BY collection, categorie, nom, ref", conn, params=p)
    if df.empty:
        return None, "Aucun produit"

    s_brand = ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=18,
                              textColor=EW_K_rl, letterSpacing=4, alignment=TA_CENTER)
    s_sub   = ParagraphStyle("sub",   fontName="Helvetica", fontSize=7,
                              textColor=EW_B_rl, letterSpacing=5, alignment=TA_CENTER)
    s_coll  = ParagraphStyle("coll",  fontName="Helvetica-Bold", fontSize=9,
                              textColor=EW_K_rl, letterSpacing=2, alignment=TA_CENTER)
    s_label = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8, textColor=EW_K_rl)
    s_small = ParagraphStyle("small", fontName="Helvetica", fontSize=7.5, textColor=EW_K_rl)
    s_ref   = ParagraphStyle("ref",   fontName="Helvetica", fontSize=7, textColor=EW_B_rl)
    s_foot  = ParagraphStyle("foot",  fontName="Helvetica", fontSize=6.5,
                              textColor=EW_B_rl, alignment=TA_CENTER)

    # Grouper par collection
    by_collection = {}
    for _, prod in df.iterrows():
        coll = str(prod.get("collection","") or "")
        if coll not in by_collection:
            by_collection[coll] = []
        by_collection[coll].append(prod)

    story = []
    PRODUCTS_PER_PAGE = 4

    for coll_name, prods in by_collection.items():
        # Découper en pages de 4 produits
        for page_idx in range(0, len(prods), PRODUCTS_PER_PAGE):
            page_prods = prods[page_idx:page_idx + PRODUCTS_PER_PAGE]
            is_first_page = (page_idx == 0)

            # ── En-tête : seulement sur la 1ère page de chaque collection ──────
            story.append(Table(
                [[Paragraph("EASTWOOD STUDIO", s_brand)]],
                colWidths=[W - 2*M]
            ))
            story.append(Paragraph("ORDER SHEET · AW26", s_sub))
            story.append(HRFlowable(width="100%", thickness=1, color=EW_K_rl))
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(coll_name.upper(), s_coll))
            story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl))
            story.append(Spacer(1, 4*mm))

            for prod in page_prods:
                # Tailles
                tailles_str = str(prod.get("tailles","") or "")
                if "One size" in tailles_str or "OS" in tailles_str:
                    sizes = ["OS"]
                elif "XXL" in tailles_str:
                    sizes = ["S", "M", "L", "XL", "XXL"]
                else:
                    sizes = ["S", "M", "L", "XL"]

                n_sz = len(sizes)
                colorway = str(prod.get("couleurs","") or "—")
                ref_sku  = str(prod.get("ref","") or "")
                nom_prod = str(prod.get("nom","") or "")

                # Image
                imgs = pd.read_sql(
                    "SELECT data FROM product_images WHERE product_id=? ORDER BY ordre LIMIT 1",
                    conn, params=[prod["id"]])
                IMG_W = 32*mm; IMG_H = 38*mm
                if not imgs.empty and imgs.iloc[0]["data"] is not None:
                    try:
                        img_io = io.BytesIO(bytes(imgs.iloc[0]["data"]))
                        cell_img = RLImage(img_io, width=IMG_W, height=IMG_H, kind="proportional")
                    except Exception:
                        cell_img = Table([[""]], colWidths=[IMG_W], rowHeights=[IMG_H])
                        cell_img.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),EW_C_rl)]))
                else:
                    ph = Table([[Paragraph("VISUEL",s_ref)]], colWidths=[IMG_W], rowHeights=[IMG_H])
                    ph.setStyle(TableStyle([
                        ("BACKGROUND",(0,0),(-1,-1),EW_C_rl),
                        ("ALIGN",(0,0),(-1,-1),"CENTER"),
                        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                    ]))
                    cell_img = ph

                # Largeurs colonnes
                img_col_w  = IMG_W + 4*mm
                info_col_w = 45*mm
                sz_col_w   = (W - 2*M - img_col_w - info_col_w) / max(n_sz, 1)

                # Headers
                hdr_row = [
                    Paragraph(f"<b>{nom_prod}</b>", s_label),
                    Paragraph(f"{ref_sku} · {colorway}", s_ref),
                ] + [Paragraph(f"<b>{s}</b>", s_label) for s in sizes]

                # Ligne image + coloris + cases taille (1 ligne par coloris)
                img_row = [cell_img, Paragraph(colorway, s_small)] + [""] * n_sz

                # Ligne total
                tot_row = ["", Paragraph("TOTAL", s_ref)] + [""] * n_sz

                col_ws = [img_col_w, info_col_w] + [sz_col_w] * n_sz
                tbl_data = [hdr_row, img_row, tot_row]
                row_tbl = Table(tbl_data, colWidths=col_ws,
                                rowHeights=[None, IMG_H, 10*mm])
                row_tbl.setStyle(TableStyle([
                    ("FONTNAME",      (0,0), (-1,-1), "Helvetica"),
                    ("FONTSIZE",      (0,0), (-1,-1), 7.5),
                    ("BACKGROUND",    (0,0), (-1,0),  GREY_rl),
                    ("BACKGROUND",    (0,-1),(-1,-1), GREY2_rl),
                    ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                    ("ALIGN",         (2,0), (-1,-1), "CENTER"),
                    ("LEFTPADDING",   (0,0), (-1,-1), 4),
                    ("TOPPADDING",    (0,0), (-1,-1), 3),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
                    ("BOX",           (0,0), (-1,-1), 0.5, EW_S_rl),
                    ("INNERGRID",     (0,0), (-1,-1), 0.3, EW_S_rl),
                    ("SPAN",          (0,1), (0,2)),
                ]))
                story.append(row_tbl)
                story.append(Spacer(1, 2*mm))

            # Footer + contact
            story.append(Spacer(1, 3*mm))
            story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl))
            contact_data = [
                [Paragraph("<b>CONTACT &amp; INFORMATIONS</b>", s_label), "", "", ""],
                [Paragraph("Name", s_ref), "", Paragraph("E-mail", s_ref), ""],
                [Paragraph("Company", s_ref), "", Paragraph("Address", s_ref), ""],
            ]
            ct = Table(contact_data, colWidths=[(W-2*M)*0.12,(W-2*M)*0.38,(W-2*M)*0.12,(W-2*M)*0.38])
            ct.setStyle(TableStyle([
                ("SPAN",(0,0),(-1,0)),
                ("ALIGN",(0,0),(-1,0),"CENTER"),
                ("INNERGRID",(0,1),(-1,-1),0.3,EW_S_rl),
                ("TOPPADDING",(0,0),(-1,-1),3),
                ("BOTTOMPADDING",(0,0),(-1,-1),3),
                ("LEFTPADDING",(0,0),(-1,-1),4),
            ]))
            story.append(ct)
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(
                "Eastwood Studio — contact@eastwood-studio.fr  |  +33 (0)7 51 61 02 52", s_foot))
            story.append(PageBreak())

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=M, rightMargin=M,
                            topMargin=10*mm, bottomMargin=10*mm)
    doc.build(story)
    return buf.getvalue(), None


def generate_linesheet(conn, collection_filter=None):
    if not REPORTLAB_OK:
        return None, "reportlab non installé"

    buf = io.BytesIO()
    W, H = A4
    M = 12 * mm

    EW_K_rl = colors.HexColor("#1a1a1a")
    EW_B_rl = colors.HexColor("#8a7968")
    EW_S_rl = colors.HexColor("#ede3d3")
    EW_C_rl = colors.HexColor("#f5f0e8")
    EW_V_rl = colors.HexColor("#7b506f")

    s_brand = ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=18,
                              textColor=EW_K_rl, letterSpacing=5, alignment=TA_CENTER)
    s_sub   = ParagraphStyle("sub",   fontName="Helvetica", fontSize=7,
                              textColor=EW_B_rl, letterSpacing=8, spaceAfter=8, alignment=TA_CENTER)
    s_coll  = ParagraphStyle("coll",  fontName="Helvetica-Bold", fontSize=8,
                              textColor=EW_V_rl, letterSpacing=3, spaceBefore=10, spaceAfter=4)
    s_ref   = ParagraphStyle("ref",   fontName="Helvetica", fontSize=6.5, textColor=EW_B_rl, spaceAfter=1)
    s_nom   = ParagraphStyle("nom",   fontName="Helvetica-Bold", fontSize=9, textColor=EW_K_rl, spaceAfter=2)
    s_var   = ParagraphStyle("var",   fontName="Helvetica-Oblique", fontSize=7.5, textColor=EW_B_rl, spaceAfter=3)
    s_desc  = ParagraphStyle("desc",  fontName="Helvetica", fontSize=7, textColor=EW_B_rl, spaceAfter=3, leading=10)
    s_small = ParagraphStyle("small", fontName="Helvetica", fontSize=6.5, textColor=EW_B_rl)
    s_foot  = ParagraphStyle("foot",  fontName="Helvetica", fontSize=6, textColor=EW_B_rl, alignment=TA_CENTER)

    story = []
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("EASTWOOD STUDIO", s_brand))
    story.append(Paragraph("PARIS  ·  LINE SHEET  ·  AW26", s_sub))
    story.append(HRFlowable(width="100%", thickness=0.8, color=EW_K_rl))
    story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl, spaceAfter=6))

    # Info date + confidentiel
    info_data = [[
        Paragraph(f"Date : {date.today().strftime('%B %Y')}", s_small),
        Paragraph("Confidential — For trade use only", s_small),
        Paragraph("eastwood-studio.fr", s_small),
    ]]
    info_tbl = Table(info_data, colWidths=[(W-2*M)/3]*3)
    info_tbl.setStyle(TableStyle([
        ("ALIGN", (0,0),(0,-1),"LEFT"), ("ALIGN",(1,0),(1,-1),"CENTER"),
        ("ALIGN", (2,0),(2,-1),"RIGHT"), ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 4*mm))

    q = "SELECT * FROM products WHERE 1=1"
    p = []
    if collection_filter:
        q += " AND collection=?"; p.append(collection_filter)
    df_prods = pd.read_sql(q + " ORDER BY collection, categorie, nom, variant", conn, params=p)

    if df_prods.empty:
        story.append(Paragraph("Aucun produit.", s_desc))
    else:
        IMG_W = 68*mm
        IMG_H = 85*mm
        COL_W = (W - 2*M - 6*mm) / 2

        for coll_name, grp in df_prods.groupby("collection", sort=False):
            story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl))
            story.append(Paragraph(str(coll_name).upper(), s_coll))
            story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl, spaceAfter=4))

            prods = list(grp.iterrows())
            for i in range(0, len(prods), 2):
                row_cells = []
                for j in range(2):
                    if i + j >= len(prods):
                        row_cells.append(""); continue

                    _, prod = prods[i + j]
                    cell = []

                    # Image
                    imgs = pd.read_sql(
                        "SELECT data FROM product_images WHERE product_id=? ORDER BY ordre LIMIT 1",
                        conn, params=[prod["id"]])
                    if not imgs.empty and imgs.iloc[0]["data"] is not None:
                        try:
                            img_io = io.BytesIO(bytes(imgs.iloc[0]["data"]))
                            cell.append(RLImage(img_io, width=IMG_W, height=IMG_H, kind="proportional"))
                        except Exception:
                            ph = Table([[""]], colWidths=[IMG_W], rowHeights=[IMG_H])
                            ph.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),EW_C_rl),("BOX",(0,0),(-1,-1),0.3,EW_S_rl)]))
                            cell.append(ph)
                    else:
                        ph = Table([[""]], colWidths=[IMG_W], rowHeights=[IMG_H])
                        ph.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),EW_C_rl),("BOX",(0,0),(-1,-1),0.3,EW_S_rl)]))
                        cell.append(ph)

                    cell.append(Spacer(1, 2*mm))
                    ref_str = str(prod.get("ref",""))
                    if prod.get("internal_ref"):
                        ref_str += f"  ·  {prod['internal_ref']}"
                    cell.append(Paragraph(ref_str, s_ref))
                    cell.append(Paragraph(str(prod["nom"]), s_nom))
                    if prod.get("variant"):
                        cell.append(Paragraph(str(prod["variant"]), s_var))
                    if prod.get("description"):
                        desc = str(prod["description"])[:120]
                        if len(str(prod["description"])) > 120: desc += "..."
                        cell.append(Paragraph(desc, s_desc))
                    if prod.get("matieres"):
                        cell.append(Paragraph(f"Materials : {prod['matieres']}", s_small))
                    if prod.get("made_in"):
                        cell.append(Paragraph(f"Made in {prod['made_in']}", s_small))
                    if prod.get("tailles"):
                        cell.append(Paragraph(f"Sizes : {prod['tailles']}", s_small))
                    cell.append(Spacer(1, 2*mm))
                    if prod.get("delivery"):
                        cell.append(Paragraph(f"Delivery : {prod['delivery']}", s_small))
                    if prod.get("moq"):
                        cell.append(Paragraph(f"MOQ : {prod['moq']} units/size", s_small))

                    row_cells.append(cell)

                tbl = Table([row_cells], colWidths=[COL_W, COL_W])
                tbl.setStyle(TableStyle([
                    ("VALIGN",(0,0),(-1,-1),"TOP"),
                    ("LEFTPADDING",(0,0),(-1,-1),3*mm),
                    ("RIGHTPADDING",(0,0),(-1,-1),3*mm),
                    ("BOTTOMPADDING",(0,0),(-1,-1),6*mm),
                    ("TOPPADDING",(0,0),(-1,-1),2*mm),
                    ("LINEBEFORE",(1,0),(1,-1),0.3,EW_S_rl),
                ]))
                story.append(KeepTogether(tbl))

    story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"EASTWOOD STUDIO  ·  Paris, France  ·  eastwood-studio.fr  ·  "
        f"Generated {date.today().strftime('%d %B %Y')}  ·  Confidential — Not for distribution", s_foot))

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=M, rightMargin=M,
                            topMargin=M, bottomMargin=10*mm)
    doc.build(story)
    return buf.getvalue(), None


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION FICHE TECHNIQUE (style dossier confidentiel typewriter, format paysage)
# ══════════════════════════════════════════════════════════════════════════════
def generate_fiche_client(conn, product_id):
    """Fiche technique client — fond kraft, synthèse produit pour le client final."""
    if not REPORTLAB_OK:
        return None, "reportlab non installé"
    df_p = get_product(conn, product_id)
    if df_p.empty:
        return None, "Produit introuvable"
    prod = df_p.iloc[0]

    import base64 as _b64fc
    buf = io.BytesIO()
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors as rl_colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, HRFlowable, Image as RLImage,
                                    KeepTogether, KeepInFrame)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.platypus.flowables import Flowable

    W, H = A4
    M = 16 * mm

    # ── Palette Kraft ─────────────────────────────────────────────────────────
    KRAFT    = rl_colors.HexColor("#e8dcc8")   # fond kraft
    KRAFT_D  = rl_colors.HexColor("#c8b89a")   # kraft foncé pour lignes
    INK      = rl_colors.HexColor("#1a1508")   # encre presque noire
    INK_L    = rl_colors.HexColor("#5c4e35")   # encre claire
    EW_V     = rl_colors.HexColor("#7b506f")   # violet Eastwood
    WHITE    = rl_colors.HexColor("#f5f0e8")   # crème

    # ── Styles ────────────────────────────────────────────────────────────────
    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    s_brand  = S("brand",  fontName="Helvetica-Bold",    fontSize=22, textColor=INK,   letterSpacing=6,  alignment=TA_LEFT)
    s_sub    = S("sub",    fontName="Helvetica",          fontSize=7,  textColor=INK_L, letterSpacing=8,  alignment=TA_LEFT, spaceBefore=2)
    s_season = S("season", fontName="Helvetica",          fontSize=8,  textColor=EW_V,  letterSpacing=3,  alignment=TA_LEFT, spaceBefore=10)
    s_nom    = S("nom",    fontName="Helvetica-Bold",     fontSize=20, textColor=INK,   spaceBefore=4,    spaceAfter=2)
    s_var    = S("var",    fontName="Helvetica-Oblique",  fontSize=13, textColor=INK_L, spaceBefore=2,    spaceAfter=4)
    s_label  = S("label",  fontName="Helvetica-Bold",     fontSize=7.5,textColor=INK_L, letterSpacing=2,  spaceBefore=10, spaceAfter=2)
    s_val    = S("val",    fontName="Helvetica",          fontSize=9.5,textColor=INK,   leading=14)
    s_desc   = S("desc",   fontName="Helvetica",          fontSize=9,  textColor=INK,   leading=14, spaceBefore=6)
    s_foot   = S("foot",   fontName="Helvetica",          fontSize=7,  textColor=INK_L, alignment=TA_CENTER, spaceBefore=14)
    s_tag    = S("tag",    fontName="Helvetica-Oblique",  fontSize=8,  textColor=EW_V,  spaceBefore=2)
    s_ref    = S("ref",    fontName="Helvetica",          fontSize=7.5,textColor=INK_L, letterSpacing=1.5)

    # ── Données ───────────────────────────────────────────────────────────────
    try:
        df_arc = pd.read_sql("""SELECT type_archive, nom_archive, annee, details
            FROM product_archives WHERE product_id=? ORDER BY id""",
            conn, params=[product_id])
    except Exception:
        df_arc = pd.DataFrame()

    imgs = pd.read_sql("SELECT data, nom_fichier FROM product_images WHERE product_id=? ORDER BY ordre LIMIT 1",
                       conn, params=[product_id])
    img_elem = None
    IMG_W = 72*mm; IMG_H = 90*mm
    if not imgs.empty and imgs.iloc[0]["data"] is not None:
        try:
            img_io = io.BytesIO(bytes(imgs.iloc[0]["data"]))
            img_elem = RLImage(img_io, width=IMG_W, height=IMG_H, kind="proportional")
        except Exception:
            pass
    if img_elem is None:
        ph_data = [["VISUEL"]]
        img_elem = Table(ph_data, colWidths=[IMG_W], rowHeights=[IMG_H])
        img_elem.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),KRAFT_D),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTSIZE",(0,0),(-1,-1),8),
            ("TEXTCOLOR",(0,0),(-1,-1),INK_L),
        ]))

    # ── Colonne texte ─────────────────────────────────────────────────────────
    txt = []
    txt.append(Paragraph("EASTWOOD STUDIO", s_brand))
    txt.append(Paragraph("PARIS  ·  HANDCRAFTED IN FRANCE", s_sub))
    txt.append(HRFlowable(width="100%", thickness=0.8, color=KRAFT_D, spaceBefore=8, spaceAfter=4))

    # Infos produit
    txt.append(Paragraph(str(prod.get("collection","") or "").upper(), s_season))
    txt.append(Paragraph(str(prod.get("nom","") or ""), s_nom))
    if prod.get("couleurs"):
        txt.append(Paragraph(str(prod.get("couleurs","")), s_var))

    # Référence
    txt.append(Paragraph(str(prod.get("ref","") or ""), s_ref))
    txt.append(HRFlowable(width="100%", thickness=0.3, color=KRAFT_D, spaceBefore=8, spaceAfter=2))

    # Description
    if prod.get("description"):
        txt.append(Paragraph("DESCRIPTION", s_label))
        txt.append(Paragraph(str(prod.get("description","")), s_desc))

    # Matières
    mats = [m.strip() for m in str(prod.get("matieres","") or "").split("\n") if m.strip()]
    if mats:
        txt.append(Paragraph("MATIÈRES & COMPOSITION", s_label))
        for m in mats:
            txt.append(Paragraph(f"· {m}", s_val))

    # Made in
    if prod.get("made_in"):
        txt.append(Paragraph("FABRIQUÉ EN", s_label))
        txt.append(Paragraph(str(prod.get("made_in","")), s_val))

    # Archives
    if not df_arc.empty:
        txt.append(Paragraph("RÉFÉRENCES & ARCHIVES UTILISÉES", s_label))
        for _, arc in df_arc.iterrows():
            _arc_type = str(arc.get("type_archive","") or "")
            _arc_note = str(arc.get("notes","") or arc.get("nom_archive","") or "")
            txt.append(Paragraph(f"— {_arc_type} : {_arc_note}", s_tag))

    # Pied de page
    txt.append(Spacer(1, 6*mm))
    txt.append(HRFlowable(width="100%", thickness=0.3, color=KRAFT_D))
    txt.append(Paragraph("Eastwood Studio  ·  www.eastwood-studio.fr  ·  contact@eastwood-studio.fr", s_foot))

    # ── Mise en page côte à côte ──────────────────────────────────────────────
    COL_IMG = IMG_W + 6*mm
    COL_TXT = W - 2*M - COL_IMG - 6*mm

    txt_frame = KeepInFrame(COL_TXT, H - 3*M, txt, mode="shrink")

    page_table = Table(
        [[img_elem, txt_frame]],
        colWidths=[COL_IMG, COL_TXT]
    )
    page_table.setStyle(TableStyle([
        ("VALIGN",      (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING", (1,0),(1,-1), 14),
        ("TOPPADDING",  (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
    ]))

    class KraftBackground(Flowable):
        """Fond kraft pleine page."""
        def __init__(self, w, h):
            Flowable.__init__(self)
            self.w = w; self.h = h
        def draw(self):
            self.canv.saveState()
            self.canv.setFillColor(KRAFT)
            self.canv.rect(-M, -M, self.w + 2*M, self.h + 2*M, fill=1, stroke=0)
            # Grain texturé léger (petits points)
            self.canv.setFillColor(KRAFT_D)
            import random; random.seed(42)
            for _ in range(180):
                x = random.uniform(0, self.w)
                y = random.uniform(-M, self.h)
                self.canv.circle(x, y, 0.3, fill=1, stroke=0)
            self.canv.restoreState()

    class PageWithKraft(SimpleDocTemplate):
        def handle_pageBegin(self):
            self._handle_pageBegin()
        def afterPage(self):
            pass

    # Image kraft encodée en base64
    _KRAFT_B64 = "/9j/4Q/+RXhpZgAATU0AKgAAAAgABgESAAMAAAABAAEAAAEaAAUAAAABAAAAVgEbAAUAAAABAAAAXgEoAAMAAAABAAIAAAITAAMAAAABAAEAAIdpAAQAAAABAAAAZgAAAAAAAABIAAAAAQAAAEgAAAABAAeQAAAHAAAABDAyMjGRAQAHAAAABAECAwCgAAAHAAAABDAx[...]"  # tronqué pour lisibilité
    _KRAFT_JPEG = base64.b64decode("/9j/4Q/+RXhpZgAATU0AKgAAAAgABgESAAMAAAABAAEAAAEaAAUAAAABAAAAVgEbAAUAAAABAAAAXgEoAAMAAAABAAIAAAITAAMAAAABAAEAAIdpAAQAAAABAAAAZgAAAAAAAABIAAAAAQAAAEgAAAABAAeQAAAHAAAABDAyMjGRAQAHAAAABAECAwCgAAAHAAAABDAxMDCgAQADAAAAAQABAACgAgAEAAAAAQAAAnKgAwAEAAAAAQAAAaGkBgADAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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")

    def on_page(canvas, doc):
        canvas.saveState()
        # Fond kraft depuis l'image JPEG
        try:
            import tempfile, os
            _tf = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            _tf.write(_KRAFT_JPEG)
            _tf.close()
            canvas.drawImage(_tf.name, 0, 0, width=W, height=H,
                             preserveAspectRatio=False, mask='auto')
            os.unlink(_tf.name)
        except Exception:
            # Fallback couleur unie
            canvas.setFillColor(KRAFT)
            canvas.rect(0, 0, W, H, fill=1, stroke=0)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=M, rightMargin=M,
        topMargin=14*mm, bottomMargin=12*mm
    )
    doc.build([page_table], onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue(), None



def generate_fiche_atelier(conn, product_id):
    """Fiche technique atelier — données de production complètes."""
    if not REPORTLAB_OK:
        return None, "reportlab non installé"
    df_p = get_product(conn, product_id)
    if df_p.empty:
        return None, "Produit introuvable"
    prod = df_p.iloc[0]

    buf = io.BytesIO()
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors as rl_colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, HRFlowable, PageBreak)
    from reportlab.platypus import Image as RLImage
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    W, H = A4
    M = 14 * mm

    EW_K = rl_colors.HexColor("#1a1a1a")
    EW_B = rl_colors.HexColor("#8a7968")
    EW_V = rl_colors.HexColor("#7b506f")
    EW_C = rl_colors.HexColor("#f5f0e8")
    EW_S = rl_colors.HexColor("#ede3d3")
    GREY = rl_colors.HexColor("#f7f5f2")
    RED  = rl_colors.HexColor("#c1440e")

    s_brand = ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=16, textColor=EW_K, letterSpacing=4)
    s_sub   = ParagraphStyle("sub",   fontName="Helvetica", fontSize=7, textColor=EW_B, letterSpacing=6)
    s_title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=14, textColor=EW_K, spaceBefore=6)
    s_sect  = ParagraphStyle("sect",  fontName="Helvetica-Bold", fontSize=8, textColor=EW_V, letterSpacing=2, spaceBefore=12, spaceAfter=4)
    s_label = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8, textColor=EW_K)
    s_val   = ParagraphStyle("val",   fontName="Helvetica", fontSize=8, textColor=EW_K, leading=12)
    s_note  = ParagraphStyle("note",  fontName="Helvetica-Oblique", fontSize=7.5, textColor=EW_B, leading=11)
    s_warn  = ParagraphStyle("warn",  fontName="Helvetica-Bold", fontSize=7.5, textColor=RED)
    s_foot  = ParagraphStyle("foot",  fontName="Helvetica", fontSize=6.5, textColor=EW_B, alignment=TA_CENTER)

    # Charger les données
    costs = get_costs(conn, product_id)
    costs_dict = dict(costs) if costs is not None else {}
    df_comp = get_components(conn, product_id)

    try:
        df_arc = pd.read_sql("SELECT type_archive, nom_archive, annee, details FROM product_archives WHERE product_id=?",
                             conn, params=[product_id])
    except Exception:
        df_arc = pd.DataFrame()

    # Charger image
    imgs = pd.read_sql("SELECT data FROM product_images WHERE product_id=? ORDER BY ordre LIMIT 1",
                       conn, params=[product_id])
    img_elem = None
    if not imgs.empty and imgs.iloc[0]["data"] is not None:
        try:
            img_io = io.BytesIO(bytes(imgs.iloc[0]["data"]))
            img_elem = RLImage(img_io, width=55*mm, height=65*mm, kind="proportional")
        except Exception:
            pass

    story = []

    # ── En-tête ───────────────────────────────────────────────────────────────
    hdr = Table([
        [Paragraph("EASTWOOD STUDIO", s_brand), Paragraph("FICHE TECHNIQUE — ATELIER", s_sub)],
        [Paragraph("DOCUMENT INTERNE CONFIDENTIEL", s_warn),
         Paragraph(f"Réf : {prod.get('ref','')} · {date.today().strftime('%d/%m/%Y')}", s_note)],
    ], colWidths=[(W-2*M)*0.6, (W-2*M)*0.4])
    hdr.setStyle(TableStyle([
        ("ALIGN",(1,0),(-1,-1),"RIGHT"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ]))
    story.append(hdr)
    story.append(HRFlowable(width="100%", thickness=1.5, color=EW_K, spaceBefore=4, spaceAfter=6))

    # ── Identité produit + image ──────────────────────────────────────────────
    id_txt = [
        Paragraph(str(prod.get("nom","")), s_title),
        Paragraph(f"Collection : {prod.get('collection','')} · Coloris : {prod.get('couleurs','')}", s_val),
        Paragraph(f"Catégorie : {prod.get('categorie','')} · Statut : {prod.get('statut','')}", s_val),
        Spacer(1,4*mm),
        Paragraph("MATIÈRES", s_sect),
    ]
    mats = str(prod.get("matieres","") or "").split("\n")
    for m in mats:
        if m.strip():
            id_txt.append(Paragraph(f"• {m.strip()}", s_val))
    id_txt.append(Paragraph(f"Made in : {prod.get('made_in','')}", s_note))

    img_cell = img_elem if img_elem else Table([[""]], colWidths=[55*mm], rowHeights=[65*mm])
    if not img_elem:
        img_cell.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),EW_C)]))

    id_tbl = Table([[img_cell, id_txt]], colWidths=[60*mm, W-2*M-60*mm])
    id_tbl.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(1,0),(1,0),8)]))
    story.append(id_tbl)
    story.append(HRFlowable(width="100%", thickness=0.5, color=EW_S, spaceBefore=8, spaceAfter=4))

    # ── MESURES ────────────────────────────────────────────────────────────────
    story.append(Paragraph("MESURES & GABARITS", s_sect))
    tailles = str(prod.get("tailles","") or "")
    mesures_labels = ["Longueur totale (cm)", "Largeur poitrine (cm)", "Largeur épaules (cm)",
                      "Longueur manche (cm)", "Tour de taille (cm)", "Tour de hanches (cm)"]
    sizes = [s.strip() for s in tailles.replace("/"," ").split() if s.strip()] or ["S","M","L","XL"]
    sizes = [s for s in sizes if len(s) <= 5][:6]
    m_header = [""] + [Paragraph(f"<b>{s}</b>", s_label) for s in sizes]
    m_rows = [m_header] + [[Paragraph(ml, s_val)] + [""] * len(sizes) for ml in mesures_labels]
    col_w_m = (W-2*M) / (len(sizes)+1)
    m_tbl = Table(m_rows, colWidths=[col_w_m*1.8] + [col_w_m*0.8]*len(sizes))
    m_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),GREY),
        ("INNERGRID",(0,0),(-1,-1),0.3,EW_S),
        ("BOX",(0,0),(-1,-1),0.5,EW_S),
        ("FONTSIZE",(0,0),(-1,-1),7.5),
        ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("ALIGN",(1,0),(-1,-1),"CENTER"),
    ]))
    story.append(m_tbl)

    # ── QUANTITÉS ─────────────────────────────────────────────────────────────
    story.append(Paragraph("QUANTITÉS SOUHAITÉES", s_sect))
    q_header = [""] + [Paragraph(f"<b>{s}</b>", s_label) for s in sizes] + [Paragraph("<b>TOTAL</b>", s_label)]
    q_row    = [Paragraph("Qté sample", s_val)] + [""] * len(sizes) + [""]
    q_row2   = [Paragraph("Qté production", s_val)] + [""] * len(sizes) + [""]
    moq_txt  = f"MOQ indiqué : {prod.get('moq','—')} unités/taille"
    q_tbl = Table([q_header, q_row, q_row2], colWidths=[col_w_m*1.8]+[col_w_m*0.8]*len(sizes)+[col_w_m*0.8])
    q_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),GREY),
        ("INNERGRID",(0,0),(-1,-1),0.3,EW_S),
        ("BOX",(0,0),(-1,-1),0.5,EW_S),
        ("FONTSIZE",(0,0),(-1,-1),7.5),
        ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),4),
        ("ALIGN",(1,0),(-1,-1),"CENTER"),
    ]))
    story.append(q_tbl)
    story.append(Paragraph(moq_txt, s_note))

    # ── COMPOSANTS ────────────────────────────────────────────────────────────
    if not df_comp.empty:
        story.append(Paragraph("COMPOSANTS & MATIÈRES PREMIÈRES", s_sect))
        c_header = [Paragraph(h, s_label) for h in ["Composant","Référence","Catégorie","Qté","Unité","Notes"]]
        c_rows = [c_header]
        for _, comp in df_comp.iterrows():
            c_rows.append([
                Paragraph(str(comp.get("nom_exact","") or comp.get("nom","")), s_val),
                Paragraph(str(comp.get("ref","") or ""), s_note),
                Paragraph(str(comp.get("categorie_comp","") or ""), s_note),
                Paragraph(str(comp.get("quantite","") or ""), s_val),
                Paragraph(str(comp.get("unite","") or ""), s_val),
                Paragraph(str(comp.get("description","") or ""), s_note),
            ])
        c_ws = [(W-2*M)*w for w in [0.3,0.15,0.15,0.1,0.1,0.2]]
        c_tbl = Table(c_rows, colWidths=c_ws, repeatRows=1)
        c_tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),GREY),
            ("INNERGRID",(0,0),(-1,-1),0.3,EW_S),
            ("BOX",(0,0),(-1,-1),0.5,EW_S),
            ("FONTSIZE",(0,0),(-1,-1),7.5),
            ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("LEFTPADDING",(0,0),(-1,-1),4),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
        ]))
        story.append(c_tbl)

    # ── INSTRUCTIONS PRODUCTION ───────────────────────────────────────────────
    story.append(Paragraph("INSTRUCTIONS & NOTES DE PRODUCTION", s_sect))
    if prod.get("description"):
        story.append(Paragraph(str(prod.get("description","")), s_val))
    instr_rows = [
        ["Traitement des coutures", ""],
        ["Finitions intérieures", ""],
        ["Broderies / Prints", ""],
        ["Emballage / étiquetage", ""],
        ["Contrôle qualité", ""],
        ["Notes spéciales", ""],
    ]
    instr_tbl = Table([[Paragraph(r[0],s_label), ""] for r in instr_rows],
                      colWidths=[(W-2*M)*0.35, (W-2*M)*0.65])
    instr_tbl.setStyle(TableStyle([
        ("INNERGRID",(0,0),(-1,-1),0.3,EW_S),
        ("BOX",(0,0),(-1,-1),0.5,EW_S),
        ("FONTSIZE",(0,0),(-1,-1),7.5),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),5),
        ("BACKGROUND",(0,0),(0,-1),GREY),
    ]))
    story.append(instr_tbl)

    # ── DÉLAI & LIVRAISON ─────────────────────────────────────────────────────
    story.append(Paragraph("DÉLAI & LIVRAISON", s_sect))
    deliv_data = [
        [Paragraph("Livraison estimée", s_label), Paragraph(str(prod.get("delivery","")), s_val),
         Paragraph("Destination", s_label), ""],
        [Paragraph("Délai sample (sem.)", s_label), "",
         Paragraph("Délai production (sem.)", s_label), ""],
    ]
    d_tbl = Table(deliv_data, colWidths=[(W-2*M)/4]*4)
    d_tbl.setStyle(TableStyle([
        ("INNERGRID",(0,0),(-1,-1),0.3,EW_S),
        ("BOX",(0,0),(-1,-1),0.5,EW_S),
        ("FONTSIZE",(0,0),(-1,-1),7.5),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(d_tbl)

    # ── Pied de page ──────────────────────────────────────────────────────────
    story.append(Spacer(1,4*mm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S))
    story.append(Paragraph("Eastwood Studio · DOCUMENT INTERNE CONFIDENTIEL · contact@eastwood-studio.fr", s_foot))

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=M, rightMargin=M,
                            topMargin=10*mm, bottomMargin=8*mm)
    doc.build(story)
    return buf.getvalue(), None


def generate_fiche_technique(conn, product_id):
    return generate_fiche_client(conn, product_id)



# ══════════════════════════════════════════════════════════════════════════════
# SECTIONS DE COÛTS
# ══════════════════════════════════════════════════════════════════════════════
COST_SECTIONS = {
    "Développement sample": [
        ("cout_patronage",    "Patronage sample (€)"),
        ("cout_gradation",    "Gradation sample (€)"),
        ("cout_assemblage",   "Assemblage sample (€)"),
        ("cout_mp1_sample",   "MP 1 sample (€)"),
        ("cout_mp2_sample",   "MP 2 sample (€)"),
        ("cout_mp3_sample",   "MP 3 sample (€)"),
        ("cout_compo1_sample","Composant 1 sample (€)"),
        ("cout_compo2_sample","Composant 2 sample (€)"),
        ("cout_compo3_sample","Composant 3 sample (€)"),
        ("cout_log_sample",   "Logistique sample (€)"),
    ],
    "MP & Composants": [
        ("cout_mp_principale","MP Principale (€)"),
        ("cout_mp_secondaire","MP Secondaire (€)"),
        ("cout_lining",       "Doublure / Lining (€)"),
        ("cout_compo1",       "Composant 1 (€)"),
        ("cout_compo2",       "Composant 2 (€)"),
        ("cout_compo3",       "Composant 3 (€)"),
        ("cout_zip",          "Zips (€)"),
        ("cout_boutons",      "Boutons (€)"),
        ("cout_patch",        "Patchs (€)"),
    ],
    "Étiquettes": [
        ("cout_etiq_textile","Étiquette textile (€)"),
        ("cout_etiq_taille", "Étiquette taille (€)"),
        ("cout_etiq_compo",  "Étiquette composition (€)"),
        ("cout_etiq_fab_fr", "Étiquette Fab. Fr. (€)"),
        ("cout_tag_numero",  "Tag numéro (€)"),
    ],
    "Production & Réalisation": [
        ("cout_montage",            "Montage (€)"),
        ("cout_coupe",              "Coupe (€)"),
        ("cout_finition",           "Finition (€)"),
        ("cout_broderie_principale","Broderie principale (€)"),
        ("cout_broderie_secondaire","Broderie secondaire (€)"),
        ("cout_print",              "Prints / Sérigraphie (€)"),
    ],
    "Logistique & Douanes": [
        ("cout_stockage",    "Stockage (€)"),
        ("cout_emballage",   "Emballage (€)"),
        ("cout_appro",       "Approvisionnement (€)"),
        ("cout_douane_eu",   "Douane EU (€)"),
        ("cout_douane_us",   "Douane US (€)"),
        ("cout_douane_jp",   "Douane Japan (€)"),
    ],
    "Packaging": [
        ("cout_boite",        "Boîte (€)"),
        ("cout_sac",          "Sac (€)"),
        ("cout_feuille_expl", "Feuille explicative (€)"),
        ("cout_enveloppe",    "Enveloppe (€)"),
        ("cout_stickers",     "Stickers (€)"),
    ],
    "Marketing": [
        ("cout_marketing_pct", "Marketing % (appliqué si coché)"),
    ],
}

# Nouvelles colonnes coûts à migrer
COST_NEW_COLS = [
    ("cout_mp_autre",   "REAL DEFAULT 0"),
    ("cout_compo1",     "REAL DEFAULT 0"),
    ("cout_compo2",     "REAL DEFAULT 0"),
    ("cout_compo3",     "REAL DEFAULT 0"),
    ("cout_douane_eu",  "REAL DEFAULT 0"),
    ("cout_douane_us",  "REAL DEFAULT 0"),
    ("cout_douane_jp",  "REAL DEFAULT 0"),
    ("cout_broderie_principale",  "REAL DEFAULT 0"),
    ("cout_broderie_secondaire",  "REAL DEFAULT 0"),
]

# Nouvelles colonnes coûts à ajouter si manquantes
COST_NEW_COLS = [
    ("cout_mp_autre",  "REAL DEFAULT 0"),
    ("cout_compo1",    "REAL DEFAULT 0"),
    ("cout_compo2",    "REAL DEFAULT 0"),
    ("cout_compo3",    "REAL DEFAULT 0"),
]


def compute_cost_totals(row_dict):
    totals = {}
    grand = 0.0
    for sec, fields in COST_SECTIONS.items():
        t = sum(float(row_dict.get(k,0) or 0) for k,_ in fields)
        totals[sec] = t; grand += t
    totals["TOTAL"] = grand
    return totals


# ══════════════════════════════════════════════════════════════════════════════
# PAGE PRODUITS PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════
def page_produits(can_fn, DB_PATH, fmt_eur_fn=None, fmt_jpy_fn=None):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_products_db(conn)
    if fmt_eur_fn is None: fmt_eur_fn = fmt_eur
    if fmt_jpy_fn is None: fmt_jpy_fn = fmt_jpy

    st.markdown("### Produits & Collections")

    _tabs = ["🗂 Catalogue"]
    if can_fn("finance_write"): _tabs.append("🛠 Gestion des articles")  # Jules only
    if can_fn("stock_write"):   _tabs.append("➕ Nouveau produit")
    _tabs.append("📤 Export documents")

    # Collections dynamiques chargées depuis la DB
    COLLECTIONS_DYN = get_collections_dynamic(conn)

    tab_objs = st.tabs(_tabs)
    idx = 0
    tab_cat      = tab_objs[idx]; idx += 1
    tab_gestion  = tab_objs[idx] if can_fn("finance_write") else None
    if can_fn("finance_write"): idx += 1
    tab_new      = tab_objs[idx] if can_fn("stock_write") else None
    if can_fn("stock_write"): idx += 1
    tab_export   = tab_objs[idx]; idx += 1

    # ── CATALOGUE ──────────────────────────────────────────────────────────────
    with tab_cat:
        fc1, fc2, fc3 = st.columns(3)
        with fc1: f_coll = st.selectbox("Collection", ["Toutes"] + COLLECTIONS_DYN, key="pcat_coll")
        with fc2: f_stat = st.selectbox("Statut", ["Tous"] + STATUTS_PROD, key="pcat_stat")
        with fc3: f_cat2 = st.selectbox("Catégorie", ["Toutes"] + CATEGORIES_PROD, key="pcat_cat")

        df_prods = get_products(conn,
            collection=None if f_coll=="Toutes" else f_coll,
            statut=None     if f_stat=="Tous"   else f_stat,
            categorie=None  if f_cat2=="Toutes" else f_cat2)

        if df_prods.empty:
            st.info("Aucun produit dans le catalogue.")
        else:
            _cat_order = ["MP Principale (Main Fabric)","MP Secondaire","Doublure",
                          "Broderie","Peinture","Zip","Bouton","Étiquette","Packaging","Autre"]
            _lbl_map = {"MP Principale (Main Fabric)":"Matière principale","MP Secondaire":"Matière secondaire",
                        "Doublure":"Doublure","Broderie":"Broderie","Peinture":"Peinture","Zip":"Zip",
                        "Bouton":"Bouton","Étiquette":"Étiquettes","Packaging":"Packaging","Autre":"Autre"}

            for coll in df_prods["collection"].dropna().unique():
                df_coll = df_prods[df_prods["collection"]==coll]
                st.markdown(
                    f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#8a7968;'
                    f'text-transform:uppercase;letter-spacing:.2em;margin:20px 0 10px;'
                    f'border-bottom:0.5px solid #d9c8ae;padding-bottom:4px;">{coll}</div>',
                    unsafe_allow_html=True)

                cols_g = st.columns(3)
                for ci, (_, prod) in enumerate(df_coll.iterrows()):
                    pid   = int(prod["id"])
                    _coul = str(prod.get("couleurs","") or prod.get("variant","") or "")
                    _stat = str(prod.get("statut","") or "")
                    _sc   = {"Disponible":"#395f30","Sample & Testing":"#c9800a",
                             "Out of stock":"#c1440e","Recherche":"#7b506f","Archive":"#888"}.get(_stat,"#888")
                    _nom  = prod["nom"] + (" — " + _coul if _coul else "")
                    _desc = str(prod.get("description","") or "")
                    _ref  = str(prod.get("ref","") or "")

                    # Clés session pour l'accordéon
                    _key_comp = f"show_comp_{pid}"
                    _key_arc  = f"show_arc_{pid}"
                    _show_comp = st.session_state.get(_key_comp, False)
                    _show_arc  = st.session_state.get(_key_arc, False)

                    with cols_g[ci % 3]:
                        # ── Carte principale ────────────────────────────────
                        st.markdown(
                            f'<div style="background:#f5f0e8;border:0.5px solid #d9c8ae;'
                            f'border-radius:6px;padding:14px;margin-bottom:4px;">'
                            f'<div style="font-family:DM Mono,monospace;font-size:7px;color:#8a7968;margin-bottom:2px;">{_ref}</div>'
                            f'<div style="font-size:14px;font-weight:700;color:#1a1a1a;margin-bottom:2px;">{_nom}</div>'
                            f'<div style="font-family:DM Mono,monospace;font-size:8px;color:{_sc};margin-bottom:8px;">● {_stat}</div>'
                            + (f'<div style="font-size:10px;color:#1a1a1a;font-style:italic;line-height:1.6;margin-bottom:8px;">{_desc}</div>' if _desc else "")
                            + f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:2px;">'
                            + "".join([
                                f'<span style="font-family:DM Mono,monospace;font-size:7px;color:#8a7968;text-transform:uppercase;">{_l}</span>'
                                f'<span style="font-size:9px;color:#1a1a1a;margin-right:10px;"> {str(prod.get(_k,"") or "")}</span>'
                                for _l, _k in [("Made in","made_in"),("Tailles","tailles"),("Delivery","delivery")]
                                if str(prod.get(_k,"") or "")
                            ])
                            + '</div></div>',
                            unsafe_allow_html=True)

                        # ── Boutons accordéon ────────────────────────────────
                        _bc1, _bc2 = st.columns(2)
                        with _bc1:
                            if st.button(
                                "▼ Composition" if _show_comp else "▶ Composition",
                                key=f"btn_comp_{pid}", use_container_width=True):
                                st.session_state[_key_comp] = not _show_comp
                                st.session_state[_key_arc]  = False  # fermer l'autre
                        with _bc2:
                            if st.button(
                                "▼ Archives" if _show_arc else "▶ Archives",
                                key=f"btn_arc_{pid}", use_container_width=True):
                                st.session_state[_key_arc]  = not _show_arc
                                st.session_state[_key_comp] = False  # fermer l'autre

                        # ── Panneau Composition ──────────────────────────────
                        if _show_comp:
                            det_comps = get_components(conn, pid)
                            if det_comps.empty:
                                st.markdown('<div style="background:#fff;border-radius:4px;padding:10px;font-size:10px;color:#8a7968;margin-bottom:4px;">Aucune composition renseignée.</div>', unsafe_allow_html=True)
                            else:
                                _by_cat = {}
                                for _, row in det_comps.iterrows():
                                    _by_cat.setdefault(str(row.get("categorie_comp","") or "Autre"), []).append(row)
                                _html = '<div style="background:#fff;border-radius:4px;padding:12px;margin-bottom:4px;">'
                                for _cat in _cat_order + [c for c in _by_cat if c not in _cat_order]:
                                    if _cat not in _by_cat: continue
                                    _html += (
                                        f'<div style="margin-bottom:8px;">'
                                        f'<div style="font-family:DM Mono,monospace;font-size:7px;color:#8a7968;'
                                        f'text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px;">{_lbl_map.get(_cat,_cat)}</div>')
                                    for r in _by_cat[_cat]:
                                        _cn = str(r.get("nom_exact","") or r.get("nom",""))
                                        _cq = str(r.get("quantite","") or "")
                                        _cu = str(r.get("unite","") or "")
                                        _qs = f' <span style="color:#bbb;">({_cq} {_cu})</span>' if _cq else ""
                                        _html += f'<div style="font-size:10px;color:#1a1a1a;padding:1px 0;">{_cn}{_qs}</div>'
                                    _html += '</div>'
                                _html += '</div>'
                                st.markdown(_html, unsafe_allow_html=True)

                        # ── Panneau Archives ─────────────────────────────────
                        if _show_arc:
                            try:
                                arcs = conn.execute(
                                    "SELECT type_archive,nom_archive,annee,details "
                                    "FROM product_archives WHERE product_id=? ORDER BY annee DESC",
                                    (pid,)).fetchall()
                            except Exception:
                                arcs = []
                            if not arcs:
                                st.markdown('<div style="background:#fff;border-radius:4px;padding:10px;font-size:10px;color:#8a7968;margin-bottom:4px;">Aucune archive renseignée.</div>', unsafe_allow_html=True)
                            else:
                                _html = '<div style="background:#fff;border-radius:4px;padding:12px;margin-bottom:4px;">'
                                for arc in arcs:
                                    _ann = str(arc[2]) if arc[2] and arc[2] not in (0,"0") else ""
                                    _det = str(arc[3] or "")
                                    _html += (
                                        f'<div style="margin-bottom:8px;padding-bottom:6px;border-bottom:0.5px solid #f0ece4;">'
                                        f'<div style="font-size:10px;font-weight:600;color:#1a1a1a;">'
                                        f'{arc[1]}{(" — " + _ann) if _ann else ""} '
                                        f'<span style="font-family:DM Mono,monospace;font-size:7px;color:#8a7968;text-transform:uppercase;">{arc[0]}</span>'
                                        f'</div>'
                                        + (f'<div style="font-size:9px;color:#8a7968;line-height:1.5;margin-top:2px;">{_det}</div>' if _det else "")
                                        + '</div>')
                                _html += '</div>'
                                st.markdown(_html, unsafe_allow_html=True)


    # ── GESTION DES ARTICLES (Jules only) ───────────────────────────────────


    # ── NOUVEAU PRODUIT ────────────────────────────────────────────────────────
    if tab_new is not None:
        with tab_new:
            st.markdown(f'<div class="section-title">Nouveau produit</div>', unsafe_allow_html=True)

            # ── Infos principales ────────────────────────────────────────────
            nc1,nc2,nc3 = st.columns(3)
            with nc1:
                n_ref  = st.text_input("SKU *", placeholder="EWSJACKET-001A")
                n_iref = st.text_input("Réf. interne")
                n_nom  = st.text_input("Nom *")
            with nc2:
                coll_new_opts = COLLECTIONS_DYN + ["➕ Nouvelle collection..."]
                n_coll_sel = st.selectbox("Collection", coll_new_opts)
                if n_coll_sel == "➕ Nouvelle collection...":
                    n_coll = st.text_input("Nom de la nouvelle collection", placeholder="Chapter III — ...")
                else:
                    n_coll = n_coll_sel
                n_cat  = st.selectbox("Catégorie", CATEGORIES_PROD)
                n_stat = st.selectbox("Statut", STATUTS_PROD)
                n_made = st.text_input("Made in", placeholder="Paris / Japan")
            with nc3:
                n_coul  = st.text_input("Couleur / Variant")
                n_tail  = st.text_input("Tailles", placeholder="T1(S) / T2(M) / T3(L)")
                n_moq   = st.number_input("MOQ", min_value=0, value=0)
                n_deliv = st.text_input("Delivery", placeholder="3 months")
                n_orig  = st.text_input("Origine", placeholder="Paris, France")
            n_desc = st.text_area("Description", height=70)

            # ── Composition par catégorie ─────────────────────────────────────
            st.markdown(
                f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#8a7968;'
                f'text-transform:uppercase;letter-spacing:.12em;margin:14px 0 6px;'
                f'border-top:0.5px solid #d9c8ae;padding-top:10px;">Composition</div>',
                unsafe_allow_html=True)
            st.caption("Remplissez chaque catégorie. Le nom sera le composant exact, le coût alimentera automatiquement la fiche coûts produit.")

            # Catégories alignées sur COST_SECTIONS / product_costs
            COMP_CATS = [
                ("MP Principale (Main Fabric)", "cout_mp_principale"),
                ("MP Secondaire",               "cout_mp_secondaire"),
                ("Doublure",                    "cout_lining"),
                ("Zip",                         "cout_zip"),
                ("Bouton",                      "cout_boutons"),
                ("Patch",                       "cout_patch"),
                ("Broderie",                    "cout_broderie_principale"),
                ("Peinture",                    "cout_peinture"),
                ("Prints / Sérigraphie",        "cout_print"),
                ("Étiquette",                   None),
            ]

            n_comps = {}  # {cat: [(nom, qte, unite, cout)]}

            for _cat, _cost_col in COMP_CATS:
                _key = _cat.lower().replace(" ","_").replace("/","")[:20]
                with st.expander(f"▶ {_cat}", expanded=False):
                    _n_items = st.number_input(f"Nombre d'éléments — {_cat}", min_value=0, max_value=5, value=0, step=1, key=f"ncomp_{_key}_n")
                    _items = []
                    for _i in range(int(_n_items)):
                        _c1, _c2, _c3, _c4 = st.columns([3, 1, 1, 1])
                        with _c1: _cn = st.text_input("Nom *", key=f"ncomp_{_key}_{_i}_nom", placeholder=f"ex: Laine Whipcord Chocolate")
                        with _c2: _cq = st.number_input("Qté", min_value=0.0, step=0.1, key=f"ncomp_{_key}_{_i}_qte", value=1.0)
                        with _c3: _cu = st.selectbox("Unité", ["Pièces","Mètre","kg","m²","cm","Lot"], key=f"ncomp_{_key}_{_i}_unit")
                        with _c4: _cc = st.number_input("Coût (€)", min_value=0.0, step=0.01, key=f"ncomp_{_key}_{_i}_cout")
                        if _cn.strip():
                            _items.append((_cn.strip(), _cq, _cu, _cc))
                    if _items:
                        n_comps[_cat] = (_cost_col, _items)

            # Étiquettes standard (checkboxes)
            with st.expander("▶ Étiquettes", expanded=False):
                _ec1,_ec2,_ec3,_ec4,_ec5 = st.columns(5)
                with _ec1: n_etq_txt  = st.checkbox("Étiquette textile")
                with _ec2: n_etq_tail = st.checkbox("Étiquette taille")
                with _ec3: n_etq_comp = st.checkbox("Étiquette composition")
                with _ec4: n_etq_fr   = st.checkbox("Fab. Française")
                with _ec5: n_etq_tag  = st.checkbox("Tag numéro")

            # ── Bouton Créer ──────────────────────────────────────────────────
            if st.button("✓ Créer le produit", type="primary"):
                if not n_ref.strip() or not n_nom.strip():
                    st.error("SKU et Nom sont obligatoires.")
                elif conn.execute("SELECT id FROM products WHERE ref=?", (n_ref.strip(),)).fetchone():
                    st.error(f"SKU {n_ref.strip()} existe déjà.")
                else:
                    conn.execute("""INSERT INTO products
                        (nom,ref,internal_ref,couleurs,tailles,made_in,matieres,description,
                         delivery,moq,collection,statut,categorie,origine)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (n_nom.strip(), n_ref.strip(), n_iref.strip(), n_coul.strip(),
                         n_tail.strip(), n_made.strip(), "", n_desc.strip(),
                         n_deliv.strip(), n_moq, n_coll, n_stat, n_cat,
                         n_orig.strip() or n_made.strip()))
                    new_pid = conn.execute("SELECT id FROM products WHERE ref=?", (n_ref.strip(),)).fetchone()[0]

                    # ── Insérer les composants ────────────────────────────────
                    cost_vals = {}
                    for _cat, (_cost_col, _items) in n_comps.items():
                        for _cn, _cq, _cu, _cc in _items:
                            conn.execute("""INSERT INTO product_components
                                (product_id, nom_exact, categorie_comp, quantite, unite, ref_stock)
                                VALUES (?,?,?,?,?,?)""",
                                (new_pid, _cn, _cat, _cq, _cu, ""))
                            # Accumuler le coût dans la bonne colonne
                            if _cost_col:
                                cost_vals[_cost_col] = cost_vals.get(_cost_col, 0) + _cc

                    # Étiquettes standard
                    ETQ_STANDARD = []
                    if n_etq_txt:  ETQ_STANDARD.append(("Étiquette textile Eastwood Studio","Étiquette",1,"Pièces","EWSETQ-004A"))
                    if n_etq_tail: ETQ_STANDARD.append(("Étiquette de taille","Étiquette",1,"Pièces",""))
                    if n_etq_comp: ETQ_STANDARD.append(("Étiquette de composition","Étiquette",1,"Pièces","EWSETQ-001A"))
                    if n_etq_fr:   ETQ_STANDARD.append(("Étiquette fabrication Française","Étiquette",1,"Pièces","EWSETQ-003A"))
                    if n_etq_tag:  ETQ_STANDARD.append(("Tag numéro identification","Étiquette",1,"Pièces","EWSPKG-001A"))
                    for _en, _ec, _eq, _eu, _er in ETQ_STANDARD:
                        conn.execute("""INSERT INTO product_components
                            (product_id, nom_exact, categorie_comp, quantite, unite, ref_stock)
                            VALUES (?,?,?,?,?,?)""",
                            (new_pid, _en, _ec, _eq, _eu, _er))

                    conn.commit()

                    # ── Créer automatiquement la fiche coûts ──────────────────
                    ex_cost = conn.execute("SELECT id FROM product_costs WHERE product_id=?", (new_pid,)).fetchone()
                    if not ex_cost and cost_vals:
                        cols_c = list(cost_vals.keys())
                        set_c  = ", ".join(cols_c)
                        ph_c   = ", ".join("?" for _ in cols_c)
                        try:
                            conn.execute(f"INSERT INTO product_costs (product_id, {set_c}) VALUES (?, {ph_c})",
                                         [new_pid] + [cost_vals[c_] for c_ in cols_c])
                        except Exception:
                            conn.execute("INSERT INTO product_costs (product_id) VALUES (?)", (new_pid,))
                            for c_, v_ in cost_vals.items():
                                try: conn.execute(f"UPDATE product_costs SET {c_}=? WHERE product_id=?", (v_, new_pid))
                                except Exception: pass
                        conn.commit()

                    sync_product_status(conn)
                    conn.commit()

                    n_cost_fields = len(cost_vals)
                    st.success(
                        f"✓ Produit **{n_nom.strip()}** ({n_ref.strip()}) créé. "
                        f"Fiche coûts créée automatiquement avec {n_cost_fields} champs pré-remplis.")
                    if n_cost_fields == 0:
                        st.info("ℹ Aucun coût saisi dans la composition — ouvrez la fiche Coûts produits pour compléter.")
                    st.rerun()


    if tab_gestion is not None:
        with tab_gestion:
            st.markdown('<div class="section-title">Gestion des articles</div>', unsafe_allow_html=True)
            # Filtres
            ga_f1, ga_f2, ga_f3 = st.columns(3)
            with ga_f1:
                ga_type_f = st.selectbox("Type", ["Tous","Produit fini","Out of stock","Archive","Sample"], key="ga_type_f")
            with ga_f2:
                ga_coll_f = st.selectbox("Collection", ["Toutes"] + get_collections_dynamic(conn), key="ga_coll_f")
            with ga_f3:
                ga_search = st.text_input("Rechercher", placeholder="nom ou SKU...", key="ga_search")

            df_pf_art = get_products(conn,
                collection=None if ga_coll_f=="Toutes" else ga_coll_f)
            if not df_pf_art.empty:
                if ga_type_f not in ("Tous", None, "") and ga_type_f != "Produit fini":
                    if ga_type_f == "Archive":
                        df_pf_art = df_pf_art[df_pf_art["statut"]=="Archive"]
                    elif ga_type_f == "Sample":
                        df_pf_art = df_pf_art[df_pf_art["statut"]=="Sample & Testing"]
                    elif ga_type_f == "Out of stock":
                        df_pf_art = df_pf_art[df_pf_art["statut"]=="Out of stock"]
                if False and ga_type_f == "Produit fini":
                    df_pf_art = df_pf_art[df_pf_art["statut"].isin(["Disponible","Sample & Testing","Out of stock","Recherche"])]
                elif ga_type_f == "Archive":
                    df_pf_art = df_pf_art[df_pf_art["statut"]=="Archive"]
                elif ga_type_f == "Sample":
                    df_pf_art = df_pf_art[df_pf_art["statut"]=="Sample & Testing"]
                if ga_search.strip():
                    mask = (df_pf_art["nom"].fillna("").str.contains(ga_search,case=False,na=False) |
                            df_pf_art["ref"].fillna("").str.contains(ga_search,case=False,na=False))
                    df_pf_art = df_pf_art[mask]

            if df_pf_art.empty:
                st.info("Aucun article trouvé.")
            else:
                _art_options = [f"{r['ref']} — {r['nom']} / {r.get('couleurs','')}" for _, r in df_pf_art.iterrows()]
                # Présélection depuis le catalogue
                _presel_idx = 0
                _presel_id = st.session_state.pop("gestion_art_presel_id", None)
                if _presel_id:
                    try:
                        _presel_row = df_pf_art[df_pf_art["id"]==_presel_id]
                        if not _presel_row.empty:
                            _presel_label = f"{_presel_row.iloc[0]['ref']} — {_presel_row.iloc[0]['nom']} / {_presel_row.iloc[0].get('couleurs','')}"
                            _presel_idx = _art_options.index(_presel_label)
                    except Exception:
                        pass
                sel_art_ref = st.selectbox(
                    "Sélectionner un article",
                    options=_art_options,
                    index=_presel_idx,
                    key="gestion_art_sel"
                )
                sel_art_idx = [f"{r['ref']} — {r['nom']} / {r.get('couleurs','')}" for _, r in df_pf_art.iterrows()].index(sel_art_ref)
                art = df_pf_art.iloc[sel_art_idx]
                pid_art = int(art["id"])

                st.markdown('---')
                with st.form(f"gestion_art_form_{pid_art}"):
                    ga1, ga2 = st.columns(2)
                    with ga1:
                        ga_nom  = st.text_input("Nom", value=str(art.get("nom","") or ""))
                        ga_ref  = st.text_input("SKU / Référence", value=str(art.get("ref","") or ""))
                        ga_iref = st.text_input("Réf. interne", value=str(art.get("internal_ref","") or ""))
                        ga_col  = st.text_input("Couleur(s)", value=str(art.get("couleurs","") or ""))
                        ga_tail = st.text_input("Tailles", value=str(art.get("tailles","") or ""))
                        ga_made = st.text_input("Made in", value=str(art.get("made_in","") or ""))
                    with ga2:
                        ga_desc = st.text_area("Description", value=str(art.get("description","") or ""), height=80)
                        ga_del  = st.text_input("Delivery", value=str(art.get("delivery","") or ""))
                        ga_moq  = st.number_input("MOQ", value=int(art.get("moq",0) or 0), min_value=0)
                        _all_coll = get_collections_dynamic(conn)
                        ga_coll = st.selectbox("Collection",
                            options=_all_coll,
                            index=_all_coll.index(art.get("collection","")) if art.get("collection") in _all_coll else 0)
                        ga_stat = st.selectbox("Statut", STATUTS_PROD,
                            index=STATUTS_PROD.index(art.get("statut","Disponible"))
                            if art.get("statut") in STATUTS_PROD else 0)

                    if st.form_submit_button("💾 Sauvegarder les modifications", type="primary"):
                        conn.execute("""UPDATE products SET nom=?,ref=?,internal_ref=?,couleurs=?,
                            tailles=?,made_in=?,description=?,delivery=?,moq=?,
                            collection=?,statut=? WHERE id=?""",
                            (ga_nom,ga_ref,ga_iref,ga_col,ga_tail,ga_made,ga_desc,
                             ga_del,ga_moq,ga_coll,ga_stat,pid_art))
                        conn.commit()
                        st.success("✓ Article mis à jour."); st.rerun()

                # Visuels : afficher + supprimer + ajouter
                st.markdown("**Visuels**")
                try:
                    df_imgs_ga = pd.read_sql("SELECT id, nom_fichier, data FROM product_images WHERE product_id=? ORDER BY ordre",
                                             conn, params=[pid_art])
                    if not df_imgs_ga.empty:
                        img_cols = st.columns(min(len(df_imgs_ga), 4))
                        for i_gi, (_, gi_row) in enumerate(df_imgs_ga.iterrows()):
                            with img_cols[i_gi % 4]:
                                if gi_row["data"] is not None:
                                    try:
                                        _b64gi = base64.b64encode(bytes(gi_row["data"])).decode()
                                        st.markdown(f'<img src="data:image/jpeg;base64,{_b64gi}" style="width:100%;max-height:120px;object-fit:cover;margin-bottom:4px;"/>', unsafe_allow_html=True)
                                    except Exception:
                                        pass
                                if st.button("🗑", key=f"del_img_{gi_row['id']}_{pid_art}", help="Supprimer ce visuel"):
                                    conn.execute("DELETE FROM product_images WHERE id=?", (gi_row["id"],))
                                    conn.commit(); st.rerun()
                except Exception:
                    pass
                new_img = st.file_uploader("Ajouter une image", type=["jpg","jpeg","png","webp"], key=f"ga_img_{pid_art}")
                if new_img:
                    img_data = new_img.read()
                    conn.execute("INSERT INTO product_images (product_id,nom_fichier,data,ordre) VALUES (?,?,?,?)",
                                 (pid_art, new_img.name, img_data, 0))
                    conn.commit(); st.success("✓ Image ajoutée."); st.rerun()

                st.markdown("---")
                ga_t1, ga_t2, ga_t3 = st.tabs(["🧵 Composition", "📚 Archives", "🗑 Gestion"])

                with ga_t1:
                    df_comp_ga = get_components(conn, pid_art)
                    # Charger fournisseurs pour la liste déroulante
                    try:
                        _fours_ga = ["— Saisie libre —"] + [r[0] for r in conn.execute(
                            "SELECT DISTINCT nom FROM contacts WHERE type_contact='Fournisseur' ORDER BY nom"
                        ).fetchall() if r[0]]
                    except Exception:
                        _fours_ga = ["— Saisie libre —"]

                    if not df_comp_ga.empty:
                        for _, comp in df_comp_ga.iterrows():
                            cg1, cg2 = st.columns([6,1])
                            with cg1:
                                st.markdown(f"**{comp.get('nom_exact') or comp.get('nom','')}** · "
                                            f"{comp.get('categorie_comp','')} · "
                                            f"{comp.get('quantite','')} {comp.get('unite','')}"
                                            + (f" · _{comp.get('fournisseur','')}_" if comp.get('fournisseur') else ""))
                            with cg2:
                                if st.button("🗑", key=f"del_comp_{comp['id']}", help="Supprimer ce composant"):
                                    conn.execute("DELETE FROM product_components WHERE id=?", (int(comp["id"]),))
                                    conn.commit(); st.rerun()
                    else:
                        st.info("Aucun composant.")

                    # Charger le stock pour sélection
                    try:
                        _stk_ga = conn.execute("SELECT ref, description, type_produit FROM stock ORDER BY type_produit, description").fetchall()
                        _stk_opts_ga = {"— Saisie libre —": ""} | {f"{s[1] or s[0]} ({s[2]})": s[0] for s in _stk_ga}
                    except Exception:
                        _stk_opts_ga = {"— Saisie libre —": ""}

                    with st.expander("➕ Ajouter un composant"):
                        with st.form(f"ga_comp_{pid_art}"):
                            ca_cat = st.selectbox("Catégorie *", ["MP Principale (Main Fabric)","MP Secondaire","Doublure","Broderie","Zip","Bouton","Étiquette","Packaging","Autre"])
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                _ca_stk_sel = st.selectbox("Depuis le stock", list(_stk_opts_ga.keys()))
                                if _ca_stk_sel == "— Saisie libre —":
                                    ca_nom = st.text_input("Nom composant *")
                                else:
                                    ca_nom = _ca_stk_sel.split(" (")[0]
                                    st.markdown(f'<div style="font-size:10px;color:#395f30;padding:4px 0;">✓ Ref: {_stk_opts_ga[_ca_stk_sel]}</div>', unsafe_allow_html=True)
                            with c2:
                                ca_qte  = st.number_input("Quantité", min_value=0.0, step=0.1)
                                ca_unit = st.selectbox("Unité", ["Pièces","Mètre","kg","g","m²"])
                            with c3:
                                _ca_four_sel = st.selectbox("Fournisseur", _fours_ga)
                                if _ca_four_sel == "— Saisie libre —":
                                    ca_four = st.text_input("Nom fournisseur")
                                else:
                                    ca_four = _ca_four_sel
                                ca_notes = st.text_input("Notes")
                            if st.form_submit_button("Ajouter"):
                                if ca_nom:
                                    for _cc, _cd in [("fournisseur","TEXT DEFAULT ''"),("notes","TEXT DEFAULT ''")]:
                                        try: conn.execute(f"ALTER TABLE product_components ADD COLUMN {_cc} {_cd}"); conn.commit()
                                        except Exception: pass
                                    conn.execute("""INSERT INTO product_components
                                        (product_id,nom_exact,categorie_comp,quantite,unite,fournisseur,notes)
                                        VALUES (?,?,?,?,?,?,?)""",
                                        (pid_art,ca_nom,ca_cat,ca_qte,ca_unit,ca_four,ca_notes))
                                    conn.commit(); st.rerun()

                with ga_t2:
                    try:
                        df_arc_ga = pd.read_sql("SELECT * FROM product_archives WHERE product_id=? ORDER BY annee DESC, id",
                                                conn, params=[pid_art])
                    except Exception:
                        df_arc_ga = pd.DataFrame()
                    if not df_arc_ga.empty:
                        for _, arc in df_arc_ga.iterrows():
                            ag1, ag2 = st.columns([6,1])
                            with ag1:
                                _ann_str = f"{int(arc.get('annee',0))} · " if arc.get("annee") and int(arc.get("annee",0)) > 0 else ""
                                st.markdown(f"**{arc.get('type_archive','')}** · {_ann_str}{arc.get('nom_archive','') or arc.get('notes','') or arc.get('nom_archive','')}"
                                            + (f" — {arc.get('details','')}" if arc.get("details") else ""))
                            with ag2:
                                if st.button("🗑", key=f"del_arc_{arc['id']}", help="Supprimer cette archive"):
                                    conn.execute("DELETE FROM product_archives WHERE id=?", (int(arc["id"]),))
                                    conn.commit(); st.rerun()
                    else:
                        st.info("Aucune archive.")

                    with st.expander("➕ Ajouter une archive"):
                        _ARC_TYPES_GA = ["Photo","Sketch","Moodboard","Référence","Inspiration","Autre"]
                        arc_type = st.selectbox("Type", _ARC_TYPES_GA, key=f"arc_t_{pid_art}")
                        arc_ann  = st.number_input("Année", min_value=1900, max_value=2050, value=2025, step=1, key=f"arc_ann_{pid_art}")
                        arc_nom  = st.text_input("Titre / Notes", key=f"arc_n_{pid_art}")
                        arc_lieu = st.text_input("Lieu / Contexte", key=f"arc_l_{pid_art}")
                        arc_file = st.file_uploader("Fichier (optionnel)", type=["jpg","jpeg","png","pdf"], key=f"arc_f_{pid_art}")
                        if st.button("✓ Ajouter archive", key=f"arc_btn_{pid_art}"):
                            if arc_nom.strip() or arc_file:
                                arc_bytes = arc_file.read() if arc_file else None
                                arc_fname = arc_file.name if arc_file else ""
                                try:
                                    conn.execute("""INSERT INTO product_archives
                                        (product_id,type_archive,nom_archive,annee,lieu,details)
                                        VALUES (?,?,?,?,?,?)""",
                                        (pid_art, arc_type, arc_nom, int(arc_ann),
                                         arc_lieu, arc_details))
                                    conn.commit(); st.rerun()
                                except Exception as _e:
                                    st.error(f"Erreur: {_e}")

                with ga_t3:
                    st.markdown("**Supprimer le produit**")
                    if can_fn("products_delete") and st.button("🗑 Supprimer définitivement", key=f"ga_del_{pid_art}", type="primary"):
                        conn.execute("DELETE FROM products WHERE id=?", (pid_art,))
                        conn.execute("DELETE FROM product_images WHERE product_id=?", (pid_art,))
                        conn.execute("DELETE FROM product_components WHERE product_id=?", (pid_art,))
                        conn.commit(); st.success("✓ Supprimé."); st.rerun()

    # ── EXPORT DOCUMENTS ───────────────────────────────────────────────────────
    with tab_export:
        st.markdown(f'<div class="section-title">Export de documents</div>', unsafe_allow_html=True)

        exp_coll = st.selectbox("Collection", ["Toutes"]+COLLECTIONS_DYN, key="exp_coll")
        coll_arg = None if exp_coll == "Toutes" else exp_coll

        # Aperçu de la sélection
        df_exp_preview = get_products(conn, collection=coll_arg)
        st.markdown(f"**{len(df_exp_preview)} produits** dans cette sélection")

        st.markdown("---")
        col_d1, col_d2, col_d3 = st.columns(3)

        with col_d1:
            st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};padding:16px;text-align:center;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:{EW_B};
              text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;">Line Sheet</div>
  <div style="font-size:11px;color:{EW_B};margin-bottom:12px;">
    2 produits par ligne · sans prix · format showroom
  </div>
</div>""", unsafe_allow_html=True)
            if st.button("📄 Générer Line Sheet", key="gen_ls"):
                with st.spinner("Génération line sheet..."):
                    pdf_b, err = generate_linesheet(conn, coll_arg)
                if err: st.error(f"Erreur : {err}")
                elif pdf_b:
                    st.download_button("⬇ Télécharger Line Sheet", pdf_b,
                        file_name=f"linesheet_eastwood_AW26.pdf", mime="application/pdf",
                        key="dl_ls")

        with col_d2:
            st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};padding:16px;text-align:center;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:{EW_B};
              text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;">Order Sheet</div>
  <div style="font-size:11px;color:{EW_B};margin-bottom:12px;">
    1 produit par page · grille tailles/coloris · section contact
  </div>
</div>""", unsafe_allow_html=True)
            if st.button("📋 Générer Order Sheet", key="gen_os"):
                with st.spinner("Génération order sheet..."):
                    pdf_b, err = generate_order_sheet(conn, coll_arg)
                if err: st.error(f"Erreur : {err}")
                elif pdf_b:
                    st.download_button("⬇ Télécharger Order Sheet", pdf_b,
                        file_name=f"order_sheet_eastwood_{coll_arg.replace(" ","_") if coll_arg else "all"}.pdf", mime="application/pdf",
                        key="dl_os")

        with col_d3:
            st.markdown(f"""
<div style="background:#fff;border:0.5px solid {EW_S};padding:16px;text-align:center;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:{EW_B};
              text-transform:uppercase;letter-spacing:.12em;margin-bottom:8px;">Fiche Technique</div>
  <div style="font-size:11px;color:{EW_B};margin-bottom:12px;">
    Produit individuel · style dossier confidentiel · paysage
  </div>
</div>""", unsafe_allow_html=True)
            if not df_exp_preview.empty:
                ft_opts = {f"{r['ref']} — {r['nom']}": r["id"]
                           for _, r in df_exp_preview.iterrows()}
                sel_ft2 = st.selectbox("Produit", list(ft_opts.keys()), key="exp_ft_sel",
                                       label_visibility="collapsed")
                st.markdown("**Choisir le type de fiche :**")
                col_ft1, col_ft2 = st.columns(2)
                with col_ft1:
                    st.markdown("""<div style="background:#f5f0e8;border:0.5px solid #d9c8ae;padding:8px 10px;font-size:11px;">
<b>Fiche Client</b><br>
<span style="color:#8a7968;font-size:10px;">Direction artistique · description · matières · archives. Envoyée aux clients finaux.</span>
</div>""", unsafe_allow_html=True)
                    if st.button("📄 Générer Fiche Client", key="gen_ft_client"):
                        with st.spinner("Génération fiche client..."):
                            pdf_b, err = generate_fiche_client(conn, ft_opts[sel_ft2])
                        if err: st.error(f"Erreur : {err}")
                        elif pdf_b:
                            ref_slug = sel_ft2.split(" — ")[0].replace("/","_")
                            st.download_button("⬇ Télécharger Fiche Client", pdf_b,
                                file_name=f"fiche_client_{ref_slug}.pdf", mime="application/pdf",
                                key="dl_ft_client")
                with col_ft2:
                    st.markdown("""<div style="background:#1a1a1a;border:0.5px solid #333;padding:8px 10px;font-size:11px;color:#f5f0e8;">
<b>Fiche Atelier</b><br>
<span style="color:#8a7968;font-size:10px;">Mesures · quantités · composition matières · composants. Usage interne production.</span>
</div>""", unsafe_allow_html=True)
                    if st.button("📐 Générer Fiche Atelier", key="gen_ft_atelier"):
                        with st.spinner("Génération fiche atelier..."):
                            pdf_b, err = generate_fiche_atelier(conn, ft_opts[sel_ft2])
                        if err: st.error(f"Erreur : {err}")
                        elif pdf_b:
                            ref_slug = sel_ft2.split(" — ")[0].replace("/","_")
                            st.download_button("⬇ Télécharger Fiche Atelier", pdf_b,
                                file_name=f"fiche_atelier_{ref_slug}.pdf", mime="application/pdf",
                                key="dl_ft_atelier")

    # ── PACKAGING STANDARD ─────────────────────────────────────────────────────


def page_packaging(conn, can_fn, fmt_eur_fn=None):
    """Affiche et gère les types de packaging et les éléments standard."""
    import streamlit as st
    import pandas as pd
    if fmt_eur_fn is None:
        fmt_eur_fn = fmt_eur

    EW_B = "#8a7968"; EW_G = "#395f30"; EW_C = "#f5f0e8"; EW_S = "#d9c8ae"


    st.markdown(f'<div class="section-title">Packaging & Envois</div>', unsafe_allow_html=True)

    # ── Onglets Packaging ─────────────────────────────────────────────────
    _pkg_tabs = ["📦 Types de packaging", "🗂 Éléments standard"]
    _pt_obs = st.tabs(_pkg_tabs)

    with _pt_obs[0]:
        st.markdown('<div style="font-size:11px;color:#8a7968;margin-bottom:10px;">Créez des types de packaging (ex: Packaging Chapter I) en sélectionnant les items depuis l\'inventaire. Le coût total est calculé automatiquement.</div>', unsafe_allow_html=True)

        # Charger les types existants
        try:
            df_pkg_types = pd.read_sql("SELECT * FROM packaging_types ORDER BY nom", conn)
        except Exception:
            df_pkg_types = pd.DataFrame()

        if not df_pkg_types.empty:
            for _, pt in df_pkg_types.iterrows():
                ptid = int(pt["id"])
                try:
                    _pt_items = pd.read_sql(
                        "SELECT * FROM packaging_items WHERE packaging_type_id=?",
                        conn, params=[ptid])
                except Exception:
                    _pt_items = pd.DataFrame()

                _pt_cout = float(pt.get("cout_total",0) or 0)
                with st.expander(f"📦 {pt['nom']} — {fmt_eur_fn(_pt_cout)}"):
                    if not _pt_items.empty:
                        for _, it in _pt_items.iterrows():
                            _it_tot = float(it.get("quantite",1) or 1) * float(it.get("cout_unitaire",0) or 0)
                            _ic1,_ic2 = st.columns([5,1])
                            with _ic1:
                                st.markdown(
                                    f'<div style="font-size:11px;display:flex;justify-content:space-between;padding:2px 0;">'
                                    f'<span>{it.get("nom_item","")} <span style="color:#8a7968;font-size:9px;">({it.get("ref_stock","")})</span></span>'
                                    f'<span style="font-family:DM Mono,monospace;">{it.get("quantite",1)} × {fmt_eur_fn(it.get("cout_unitaire",0))} = {fmt_eur_fn(_it_tot)}</span>'
                                    f'</div>',
                                    unsafe_allow_html=True)
                            with _ic2:
                                if can_fn("stock_write") and st.button("🗑", key=f"del_pitem_{it['id']}"):
                                    conn.execute("DELETE FROM packaging_items WHERE id=?", (int(it["id"]),))
                                    # Recalculer cout_total
                                    _new_tot = conn.execute(
                                        "SELECT COALESCE(SUM(quantite*cout_unitaire),0) FROM packaging_items WHERE packaging_type_id=?",
                                        (ptid,)).fetchone()[0]
                                    conn.execute("UPDATE packaging_types SET cout_total=? WHERE id=?", (_new_tot, ptid))
                                    conn.commit(); st.rerun()
                    else:
                        st.markdown('<div style="font-size:11px;color:#ccc;">Aucun item.</div>', unsafe_allow_html=True)

                    if can_fn("stock_write"):
                        # Ajouter un item à ce packaging type
                        try:
                            _stk_items = conn.execute(
                                "SELECT ref, description, prix_unitaire FROM stock ORDER BY description"
                            ).fetchall()
                            _stk_opts_pt = ["— Saisie libre —"] + [f"{s[1] or s[0]} ({s[0]})" for s in _stk_items]
                            _stk_refs_pt = {f"{s[1] or s[0]} ({s[0]})": (s[0], float(s[2] or 0)) for s in _stk_items}
                        except Exception:
                            _stk_opts_pt = ["— Saisie libre —"]; _stk_refs_pt = {}

                        with st.form(f"add_pitem_{ptid}"):
                            _ai1,_ai2,_ai3 = st.columns([3,1,1])
                            with _ai1: _ai_sel = st.selectbox("Item (inventaire)", _stk_opts_pt, key=f"ai_sel_{ptid}")
                            with _ai2: _ai_qte = st.number_input("Qté", min_value=0.0, value=1.0, step=1.0, key=f"ai_qte_{ptid}")
                            with _ai3:
                                if _ai_sel == "— Saisie libre —":
                                    _ai_nom = st.text_input("Nom", key=f"ai_nom_{ptid}")
                                    _ai_ref = ""; _ai_pu = st.number_input("PU (€)", min_value=0.0, step=0.01, key=f"ai_pu_{ptid}")
                                else:
                                    _ai_ref_data = _stk_refs_pt.get(_ai_sel, ("",0))
                                    _ai_ref = _ai_ref_data[0]; _ai_pu_auto = _ai_ref_data[1]
                                    _ai_nom = _ai_sel.split(" (")[0]
                                    _ai_pu = st.number_input("PU (€)", min_value=0.0, value=_ai_pu_auto, step=0.01, key=f"ai_pu_{ptid}")

                            if st.form_submit_button("➕ Ajouter l'item"):
                                conn.execute("""INSERT INTO packaging_items
                                    (packaging_type_id, ref_stock, nom_item, quantite, cout_unitaire)
                                    VALUES (?,?,?,?,?)""",
                                    (ptid, _ai_ref, _ai_nom if _ai_sel=="— Saisie libre —" else _ai_nom, _ai_qte, _ai_pu))
                                _new_tot = conn.execute(
                                    "SELECT COALESCE(SUM(quantite*cout_unitaire),0) FROM packaging_items WHERE packaging_type_id=?",
                                    (ptid,)).fetchone()[0]
                                conn.execute("UPDATE packaging_types SET cout_total=? WHERE id=?", (_new_tot, ptid))
                                conn.commit(); st.rerun()

                    # Supprimer le type
                    if can_fn("stock_write"):
                        if st.button(f"🗑 Supprimer « {pt['nom']} »", key=f"del_pt_{ptid}"):
                            conn.execute("DELETE FROM packaging_items WHERE packaging_type_id=?", (ptid,))
                            conn.execute("DELETE FROM packaging_types WHERE id=?", (ptid,))
                            conn.commit(); st.rerun()
        else:
            st.info("Aucun type de packaging. Créez-en un ci-dessous.")

        # Créer un nouveau type
        if can_fn("stock_write"):
            st.markdown(f'<div class="section-title">Nouveau type de packaging</div>', unsafe_allow_html=True)
            with st.form("new_pkg_type"):
                _npt_nom   = st.text_input("Nom *", placeholder="ex: Packaging Chapter I")
                _npt_notes = st.text_input("Notes / Description")
                if st.form_submit_button("✓ Créer le type", type="primary"):
                    if _npt_nom.strip():
                        conn.execute("INSERT INTO packaging_types (nom, notes) VALUES (?,?)", (_npt_nom, _npt_notes))
                        conn.commit(); st.success(f"✓ '{_npt_nom}' créé."); st.rerun()
                    else:
                        st.error("Nom obligatoire.")

    with _pt_obs[1]:
        st.markdown('<div style="font-size:11px;color:#8a7968;margin-bottom:10px;">Éléments de packaging standard appliqués à toutes les commandes.</div>', unsafe_allow_html=True)
        df_pkg = get_packaging(conn)
        if df_pkg.empty:
            st.info("Aucun élément de packaging.")
        else:
            for _, pkg in df_pkg.iterrows():
                pk1, pk2 = st.columns([4, 1])
                with pk1:
                    _pkg_notes_html = f'<div style="font-size:11px;color:{EW_B};">{pkg["notes"]}</div>' if pkg.get("notes") else ""
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid {EW_S};">'
                        f'<div><span style="font-weight:500;font-size:13px;">{pkg["nom"]}</span>'
                        f'<span style="font-family:DM Mono,monospace;font-size:10px;color:{EW_B};margin-left:10px;">{pkg.get("ref_stock","")}</span>'
                        f'{_pkg_notes_html}'
                        f'</div><div style="font-family:DM Mono,monospace;font-size:11px;">{pkg["quantite"]} {pkg["unite"]} / commande</div></div>',
                        unsafe_allow_html=True)
                with pk2:
                    if can_fn("stock_write") and st.button("🗑", key=f"del_pkg_{pkg['id']}"):
                        conn.execute("UPDATE packaging_standard SET actif=0 WHERE id=?", (pkg["id"],))
                        conn.commit(); st.rerun()

        if can_fn("stock_write"):
            st.markdown(f'<div class="section-title">Ajouter un élément standard</div>', unsafe_allow_html=True)
            with st.form("add_pkg"):
                p1,p2,p3 = st.columns(3)
                with p1: pk_nom  = st.text_input("Nom *")
                with p2: pk_ref  = st.text_input("Réf. stock")
                with p3: pk_qte  = st.number_input("Qté / commande", min_value=0.0, value=1.0)
                pk_unit  = st.selectbox("Unité", ["Pièces","Lot","Mètre"])
                pk_cout  = st.number_input("Coût unitaire (€)", min_value=0.0, value=0.0, step=0.01)
                pk_notes = st.text_input("Notes")
                if st.form_submit_button("➕ Ajouter"):
                    if not pk_nom: st.error("Nom obligatoire.")
                    else:
                        conn.execute("INSERT INTO packaging_standard (nom,ref_stock,quantite,unite,cout_unitaire,notes) VALUES (?,?,?,?,?,?)",
                            (pk_nom,pk_ref,pk_qte,pk_unit,pk_cout,pk_notes))
                        conn.commit(); st.success("✓ Ajouté."); st.rerun()

    conn.close()



# ══════════════════════════════════════════════════════════════════════════════
# PAGE COÛTS PRODUITS — appelée depuis Finance & Comptabilité
# ══════════════════════════════════════════════════════════════════════════════

def page_couts_produits(can_fn, DB_PATH, fmt_eur_fn=None):
    if fmt_eur_fn is None: fmt_eur_fn = fmt_eur
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_products_db(conn)

    st.markdown("### Coûts de production")
    st.markdown("""
<div class="info-box">
Les coûts sont synchronisés depuis les fiches produit. Le prix unitaire doit être saisi manuellement.
Si un article n'a aucun coût renseigné, il affiche le badge <strong>COÛTS À DÉFINIR</strong>.
</div>""", unsafe_allow_html=True)

    COLLECTIONS_DYN = get_collections_dynamic(conn)
    df_all = get_products(conn)
    if df_all.empty:
        st.info("Aucun produit."); conn.close(); return

    # Filtres
    fp1,fp2,fp3 = st.columns(3)
    with fp1:
        f_coll_c = st.selectbox("Collection", ["Toutes"] + COLLECTIONS_DYN, key="cp_coll")
    with fp2:
        f_stat_c = st.selectbox("Statut", ["Tous"]+STATUTS_PROD, key="cp_stat")
    with fp3:
        # Créer une nouvelle collection
        with st.expander("➕ Nouvelle collection"):
            new_coll_name = st.text_input("Nom", placeholder="Chapter III — ...", key="cp_new_coll")
            if st.button("Créer", key="cp_create_coll") and new_coll_name.strip():
                st.success(f"✓ Collection '{new_coll_name}' disponible — assignez-la à un produit.")

    df_filtered = df_all.copy()
    if f_coll_c != "Toutes": df_filtered = df_filtered[df_filtered["collection"]==f_coll_c]
    if f_stat_c != "Tous":   df_filtered = df_filtered[df_filtered["statut"]==f_stat_c]

    # Vue globale : tableau avec coûts par catégorie
    st.markdown('<div class="section-title">Vue globale</div>', unsafe_allow_html=True)
    rows_global = []
    for _, prod in df_filtered.iterrows():
        cr = get_costs(conn, prod["id"])
        cd = dict(cr) if cr is not None else {}
        totals = compute_cost_totals(cd)
        srp = float(prod.get("prix_retail_eur",0) or 0)
        grand = totals.get("TOTAL", 0)
        marge = round((srp - grand)/srp*100, 1) if srp > 0 and grand > 0 else None
        _coul = str(prod.get("couleurs","") or prod.get("variant","") or "")
        rows_global.append({
            "Réf.":             prod.get("ref",""),
            "Nom":              prod["nom"] + (" — " + _coul if _coul else ""),
            "Dév. Sample":      fmt_eur_fn(totals.get("Développement sample",0)) if totals.get("Développement sample",0) > 0 else "—",
            "MP & Composants":  fmt_eur_fn(totals.get("MP & Composants",0)) if totals.get("MP & Composants",0) > 0 else "—",
            "Production":       fmt_eur_fn(totals.get("Production & Réalisation",0)) if totals.get("Production & Réalisation",0) > 0 else "—",
            "Logistique":       fmt_eur_fn(totals.get("Logistique & Douanes",0)) if totals.get("Logistique & Douanes",0) > 0 else "—",
            "Étiquettes":       fmt_eur_fn(totals.get("Étiquettes",0)) if totals.get("Étiquettes",0) > 0 else "—",
            "Coût total":       fmt_eur_fn(grand) if grand > 0 else "⚠ À DÉFINIR",
            "SRP EU":           fmt_eur_fn(srp) if srp > 0 else "—",
            "Marge brute":      f"{marge}%" if marge is not None else "—",
        })
    st.dataframe(pd.DataFrame(rows_global), use_container_width=True, hide_index=True)

    # Sélecteur produit pour le détail
    st.markdown('<div class="section-title">Détail par produit</div>', unsafe_allow_html=True)
    prod_opts = {f"{r['ref']} — {r['nom']}{' / '+r['variant'] if r.get('variant') else ''}": r["id"]
                 for _, r in df_filtered.iterrows()}

    if not prod_opts:
        st.info("Aucun produit dans la sélection."); conn.close(); return

    sel_p = st.selectbox("Produit", list(prod_opts.keys()), key="cp_prod")
    sel_pid = prod_opts[sel_p]
    prod_row = df_filtered[df_filtered["id"]==sel_pid].iloc[0]

    costs_row  = get_costs(conn, sel_pid)
    costs_dict = dict(costs_row) if costs_row is not None else {}

    # En-tête produit avec badge
    couts_tot = compute_cost_totals(costs_dict).get("TOTAL",0)
    srp_prod  = float(prod_row.get("prix_retail_eur",0) or 0)
    marge_prod = round((srp_prod - couts_tot)/srp_prod*100, 1) if srp_prod > 0 and couts_tot > 0 else None

    st.markdown(f"""
<div style="background:#fff;border:0.5px solid #ede3d3;border-left:3px solid #7b506f;
     padding:14px 18px;margin:10px 0;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-family:'DM Mono',monospace;font-size:9px;color:#8a7968;">{prod_row.get('ref','')}</div>
    <div style="font-size:16px;font-weight:500;">{prod_row['nom']}{f" / {prod_row['variant']}" if prod_row.get("variant") else ""}</div>
    <div style="font-size:12px;color:#8a7968;">{prod_row.get('collection','')} · {prod_row.get('statut','')}</div>
  </div>
  <div style="text-align:right;">
    <div style="font-family:'DM Mono',monospace;font-size:22px;font-weight:500;color:{'#c1440e' if couts_tot == 0 else '#1a1a1a'};">
      {fmt_eur_fn(couts_tot) if couts_tot > 0 else 'COÛTS À DÉFINIR'}
    </div>
    <div style="font-size:11px;color:#8a7968;">SRP : {fmt_eur_fn(srp_prod)}{f' · Marge : {marge_prod}%' if marge_prod else ''}</div>
  </div>
</div>""", unsafe_allow_html=True)

    # Formulaire coûts avec sections et devise
    DEVISES_COUT = ["EUR", "USD", "JPY"]

    _couts_editable = can_fn("couts_write")

    with st.form(f"costs_finance_{sel_pid}"):
        all_inputs = {}
        for sect, fields in COST_SECTIONS.items():
            # Titre de section plus grand
            st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#1a1a1a;border-bottom:2px solid #d9c8ae;padding:8px 0 4px;margin:14px 0 8px;">{sect}</div>', unsafe_allow_html=True)

            # Dans MP & Composants : une case par composant de la fiche produit
            if sect == "MP & Composants":
                _cost_to_cat = {
                    "cout_mp_principale": ["MP Principale (Main Fabric)"],
                    "cout_mp_secondaire": ["MP Secondaire"],
                    "cout_lining":        ["Doublure"],
                    "cout_zip":           ["Zip"],
                    "cout_boutons":       ["Bouton"],
                    "cout_patch":         ["Patch","Broderie"],
                }
                try:
                    _comps_prod = get_components(conn, sel_pid)
                except Exception:
                    _comps_prod = pd.DataFrame()

                _sect_total = 0.0
                _cats_done = set()

                for key, label in fields:
                    _cats = _cost_to_cat.get(key, [])
                    _matched = []
                    if _cats and not _comps_prod.empty:
                        _matched = _comps_prod[_comps_prod["categorie_comp"].isin(_cats)].to_dict("records")
                        _cats_done.update(_cats)

                    if len(_matched) > 1:
                        # Plusieurs composants → une case par composant
                        _base = label.split("(")[0].strip()
                        _ccols = st.columns(min(len(_matched), 3))
                        _agg = 0.0
                        _stored_tot = float(costs_dict.get(key, 0) or 0)
                        for _ci, _comp in enumerate(_matched):
                            _cn = str(_comp.get("nom_exact",""))
                            _sk = f"cf_{key}_{"".join(c if c.isalnum() else "_" for c in _cn.lower())[:15]}_{sel_pid}"
                            _v0 = round(_stored_tot / len(_matched), 4) if _stored_tot > 0 else 0.0
                            with _ccols[_ci % 3]:
                                _vi = st.number_input(
                                    f"{_base} — {_cn} (€)",
                                    min_value=0.0, step=0.01,
                                    value=float(st.session_state.get(_sk, _v0)),
                                    key=_sk, disabled=not _couts_editable)
                                _agg += _vi
                                _sect_total += _vi
                        all_inputs[key] = _agg
                    else:
                        _comp_name = _matched[0].get("nom_exact","") if _matched else ""
                        _disp = (f"{label.split('(')[0].strip()} — {_comp_name} (€)"
                                 if _comp_name else label)
                        val = float(costs_dict.get(key, 0) or 0)
                        all_inputs[key] = st.number_input(
                            _disp, min_value=0.0, step=0.01, value=val,
                            key=f"cf_{key}_{sel_pid}", disabled=not _couts_editable)
                        _sect_total += all_inputs[key]

                if _sect_total > 0:
                    st.markdown(
                        f'<div style="font-family:DM Mono,monospace;font-size:11px;font-weight:600;'
                        f'color:#395f30;background:#f5f0e8;padding:4px 10px;border-radius:3px;'
                        f'margin-top:4px;">Σ {sect} : {fmt_eur_fn(_sect_total)}</div>',
                        unsafe_allow_html=True)


                st.markdown('<div style="font-size:10px;color:#8a7968;margin:2px 0 6px;">Sélectionner le packaging selon le canal — coût calculé automatiquement depuis les items</div>', unsafe_allow_html=True)
                try:
                    # Filtrer uniquement les types de packaging dont les items sont de type "Packaging"
                    _pkg_types_all = pd.read_sql("SELECT * FROM packaging_types ORDER BY nom", conn)
                    # Garder tous les types (le filtrage par items "Packaging" se fait via packaging_items)
                    _pkg_opts_all  = ["— Aucun —"] + _pkg_types_all["nom"].tolist()
                    _pkg_ids_all   = {r["nom"]: r["id"] for _, r in _pkg_types_all.iterrows()}
                    _pkg_costs_all = {r["nom"]: float(r.get("cout_total",0) or 0) for _, r in _pkg_types_all.iterrows()}
                except Exception:
                    _pkg_opts_all = ["— Aucun —"]; _pkg_ids_all = {}; _pkg_costs_all = {}

                def _render_pkg_select(label, key_id_field, key_sel):
                    """Rend un selectbox packaging + détail items + total."""
                    _cur_id = int(costs_dict.get(key_id_field, 0) or 0)
                    _cur_nom = ""
                    try:
                        if _cur_id:
                            _rr = conn.execute("SELECT nom FROM packaging_types WHERE id=?", (_cur_id,)).fetchone()
                            if _rr: _cur_nom = _rr[0]
                    except Exception: pass
                    _default = _cur_nom if _cur_nom in _pkg_opts_all else "— Aucun —"
                    _sel = st.selectbox(label, _pkg_opts_all,
                        index=_pkg_opts_all.index(_default) if _default in _pkg_opts_all else 0,
                        key=key_sel)
                    _cout = 0.0
                    if _sel != "— Aucun —":
                        _cout = _pkg_costs_all.get(_sel, 0.0)
                        _pid_sel = _pkg_ids_all.get(_sel, 0)
                        try:
                            _its = conn.execute("SELECT nom_item, quantite, cout_unitaire FROM packaging_items WHERE packaging_type_id=?", (_pid_sel,)).fetchall()
                            for _it in _its:
                                _it_tot = float(_it[1] or 0) * float(_it[2] or 0)
                                st.markdown(
                                    f'<div style="display:flex;justify-content:space-between;font-size:10px;'
                                    f'padding:2px 0;border-bottom:1px solid #f0ece4;color:#8a7968;">'
                                    f'<span>{_it[0]}</span>'
                                    f'<span style="font-family:DM Mono,monospace;">{_it[1]} × {fmt_eur_fn(_it[2])} = {fmt_eur_fn(_it_tot)}</span>'
                                    f'</div>', unsafe_allow_html=True)
                        except Exception: pass
                        st.markdown(
                            f'<div style="font-family:DM Mono,monospace;font-size:11px;font-weight:600;'
                            f'color:#395f30;background:#f5f0e8;padding:3px 8px;border-radius:3px;margin-top:3px;">'
                            f'Σ {label} : {fmt_eur_fn(_cout)}</div>',
                            unsafe_allow_html=True)
                    return _sel, _pkg_ids_all.get(_sel, 0) if _sel != "— Aucun —" else 0, _cout

                _pkgr1, _pkgr2 = st.columns(2)
                with _pkgr1:
                    _sel_r, _id_r, _cout_r = _render_pkg_select("Packaging Retail", "packaging_retail_id", f"pkg_sel_retail_{sel_pid}")
                with _pkgr2:
                    _sel_w, _id_w, _cout_w = _render_pkg_select("Packaging Wholesale", "packaging_wholesale_id", f"pkg_sel_wholesale_{sel_pid}")

                all_inputs["packaging_retail_id"]     = _id_r
                all_inputs["packaging_wholesale_id"]  = _id_w
                all_inputs["cout_packaging_retail"]   = _cout_r
                all_inputs["cout_packaging_wholesale"]= _cout_w
                all_inputs["cout_packaging"] = max(_cout_r, _cout_w)  # compat calcul total

            elif sect == "Étiquettes":
                st.markdown('<div style="font-size:10px;color:#8a7968;margin:2px 0 6px;">Cochez les étiquettes incluses — coût récupéré depuis les composants de la fiche produit</div>', unsafe_allow_html=True)
                _etiq_fields = [
                    ("etiq_textile",  "Étiquette textile"),
                    ("etiq_taille",   "Étiquette de taille"),
                    ("etiq_compo",    "Étiquette composition"),
                    ("etiq_fab_fr",   "Étiquette Fabrication Française"),
                    ("etiq_tag_num",  "Tag numéro"),
                ]
                # Charger les coûts depuis product_components une seule fois
                try:
                    _etiq_comps = conn.execute(
                        "SELECT nom_exact, cout_unitaire FROM product_components WHERE product_id=?",
                        (sel_pid,)).fetchall()
                except Exception:
                    _etiq_comps = []

                def _find_etiq_cout(label):
                    """Cherche le coût d'une étiquette dans les composants."""
                    label_lower = label.lower()
                    for _nc, _cu in _etiq_comps:
                        if any(kw in (_nc or "").lower() for kw in label_lower.split()):
                            return float(_cu or 0)
                    return 0.0

                _ecols = st.columns(len(_etiq_fields))
                _etiq_total = 0.0
                for _ei, (_ek, _el) in enumerate(_etiq_fields):
                    with _ecols[_ei]:
                        _ev = st.checkbox(_el, value=bool(costs_dict.get(_ek, 0)), key=f"etiq_{_ek}_{sel_pid}", disabled=not _couts_editable)
                        all_inputs[_ek] = 1 if _ev else 0
                        _ec = _find_etiq_cout(_el) if _ev else 0.0
                        all_inputs[f"cout_{_ek}"] = _ec
                        _etiq_total += _ec
                        if _ev:
                            st.markdown(
                                f'<div style="font-family:DM Mono,monospace;font-size:9px;color:#395f30;">'
                                f'{fmt_eur_fn(_ec)}</div>',
                                unsafe_allow_html=True)
                        else:
                            _ec_info = _find_etiq_cout(_el)
                            if _ec_info > 0:
                                st.markdown(f'<div style="font-size:9px;color:#ccc;">{fmt_eur_fn(_ec_info)}</div>', unsafe_allow_html=True)

                if _etiq_total > 0:
                    st.markdown(
                        f'<div style="font-family:DM Mono,monospace;font-size:11px;font-weight:600;'
                        f'color:#395f30;background:#f5f0e8;padding:3px 8px;border-radius:3px;margin-top:6px;">'
                        f'Σ Étiquettes : {fmt_eur_fn(_etiq_total)}</div>',
                        unsafe_allow_html=True)

            elif sect == "Marketing":
                # Marketing géré hors du form (st.button interdit dans st.form)
                pct_mkt = float(costs_dict.get("cout_marketing_pct", 5.0) or 5.0)
                all_inputs["cout_marketing_pct"] = pct_mkt
                all_inputs["cout_marketing"] = 0.0  # calculé hors form

            else:
                # Rendu générique (Développement sample, Production, Logistique, Packaging)
                n_cols = min(len(fields), 3)
                fcols_g = st.columns(n_cols)
                _sect_total_g = 0.0
                for i_g, (key_g, label_g) in enumerate(fields):
                    with fcols_g[i_g % n_cols]:
                        val_g = float(costs_dict.get(key_g, 0) or 0)
                        all_inputs[key_g] = st.number_input(
                            label_g, min_value=0.0, step=0.01, value=val_g,
                            key=f"cf_{key_g}_{sel_pid}",
                            disabled=not _couts_editable)
                        _sect_total_g += all_inputs[key_g]
                if _sect_total_g > 0:
                    st.markdown(
                        f'<div style="font-family:DM Mono,monospace;font-size:11px;font-weight:600;'
                        f'color:#395f30;background:#f5f0e8;padding:4px 10px;border-radius:3px;'
                        f'margin-top:4px;">Σ {sect} : {fmt_eur_fn(_sect_total_g)}</div>',
                        unsafe_allow_html=True)

    # ── Section Prix de vente ──────────────────────────────────────────────
        st.markdown('<div style="font-family:\'DM Mono\',monospace;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#1a1a1a;border-bottom:2px solid #d9c8ae;padding:8px 0 4px;margin:14px 0 8px;">Prix de vente &amp; RTP</div>', unsafe_allow_html=True)

        # Charger les prix actuels depuis products
        _srp_eu_cur  = float(prod_row.get("prix_retail_eur",0) or 0)
        _srp_jp_cur  = float(prod_row.get("prix_retail_jpy",0) or 0)
        _srp_us_cur  = float(prod_row.get("prix_retail_usd",0) or 0)
        _wp_eu_cur   = float(prod_row.get("prix_wholesale_eu",0) or 0)
        _wp_as_cur   = float(prod_row.get("prix_wholesale_asia",0) or 0)
        _wp_us_cur   = float(prod_row.get("prix_wholesale_us",0) or 0)
        _ff_cur      = float(prod_row.get("prix_ff",0) or 0)
        _wp_fr_cur   = float(prod_row.get("prix_wholesale_fr",0) or 0)

        _pc1, _pc2, _pc3, _pc4 = st.columns(4)
        with _pc1:
            srp_eu_new  = st.number_input("SRP EU (€)",  min_value=0.0, step=5.0, value=_srp_eu_cur, key=f"srp_eu_{sel_pid}", disabled=not _couts_editable)
        with _pc2:
            srp_jp_new  = st.number_input("SRP JP (¥)",  min_value=0.0, step=100.0, value=_srp_jp_cur, key=f"srp_jp_{sel_pid}", disabled=not _couts_editable)
        with _pc3:
            srp_us_new  = st.number_input("SRP US ($)",  min_value=0.0, step=5.0, value=_srp_us_cur,  key=f"srp_us_{sel_pid}", disabled=not _couts_editable)
        with _pc4:
            srp_wd_new  = st.number_input("SRP WORLD ($)", min_value=0.0, step=5.0,
                                          value=_srp_us_cur if _srp_us_cur > 0 else 0.0,
                                          key=f"srp_wd_{sel_pid}", help="= SRP US par défaut")

        # Auto-calcul WP (/2.5) et F&F (-20%) — modifiables
        _auto_wp_eu  = round(srp_eu_new / 2.5, 2) if srp_eu_new > 0 else 0.0
        _auto_wp_as  = round(srp_jp_new / 2.5, 2) if srp_jp_new > 0 else 0.0
        _auto_wp_us  = round(srp_us_new / 2.5, 2) if srp_us_new > 0 else 0.0
        _auto_wp_wd  = round(srp_wd_new / 2.5, 2) if srp_wd_new > 0 else 0.0
        _auto_ff     = round(srp_eu_new * 0.80, 2) if srp_eu_new > 0 else 0.0

        st.markdown('<div style="font-size:10px;color:#8a7968;margin:4px 0 2px;">Wholesale Price — calculé automatiquement (/2.5 du SRP), modifiable</div>', unsafe_allow_html=True)
        _pw1,_pw2,_pw3,_pw4,_pw5 = st.columns(5)
        with _pw1:
            wp_eu_new  = st.number_input("WP EU (€)",    min_value=0.0, step=5.0,
                                         value=_wp_eu_cur if _wp_eu_cur > 0 else _auto_wp_eu,
                                         key=f"wp_eu_{sel_pid}")
        with _pw2:
            wp_as_new  = st.number_input("WP Asie (€)",  min_value=0.0, step=5.0,
                                         value=_wp_as_cur if _wp_as_cur > 0 else _auto_wp_as,
                                         key=f"wp_as_{sel_pid}")
        with _pw3:
            wp_us_new  = st.number_input("WP US ($)",    min_value=0.0, step=5.0,
                                         value=_wp_us_cur if _wp_us_cur > 0 else _auto_wp_us,
                                         key=f"wp_us_{sel_pid}")
        with _pw4:
            wp_wd_new  = st.number_input("WP WORLD ($)", min_value=0.0, step=5.0,
                                         value=_wp_fr_cur if _wp_fr_cur > 0 else _auto_wp_wd,
                                         key=f"wp_wd_{sel_pid}")
        with _pw5:
            ff_new     = st.number_input("F&F (€) −20%", min_value=0.0, step=5.0,
                                         value=_ff_cur if _ff_cur > 0 else _auto_ff,
                                         key=f"ff_{sel_pid}", help="SRP EU −20% par défaut")

        # Résumé visuel
        _couts_t = compute_cost_totals(all_inputs).get("TOTAL",0) or couts_tot
        _marge_v = round((srp_eu_new - _couts_t)/srp_eu_new*100,1) if srp_eu_new > 0 and _couts_t > 0 else None
        st.markdown(f"""
<div style="background:#f5f0e8;border-left:3px solid #395f30;padding:8px 14px;margin:8px 0;font-family:'DM Mono',monospace;font-size:11px;">
  SRP EU {srp_eu_new:,.0f} € · WP EU {wp_eu_new:,.0f} € · F&F {ff_new:,.0f} €
  {f" · Marge brute : <strong>{_marge_v}%</strong>" if _marge_v else ""}
</div>""", unsafe_allow_html=True)

        # ── Appliquer aux variantes de la même famille ────────────────────
        _sel_vars = []
        if _couts_editable:
            try:
                _base_nom = str(prod_row.get("nom","") or "")
                _variants = conn.execute(
                    "SELECT id, ref, couleurs FROM products WHERE nom=? AND id!=? ORDER BY ref",
                    (_base_nom, sel_pid)).fetchall()
            except Exception:
                _variants = []
            if _variants:
                st.markdown(
                    f'<div style="font-family:DM Mono,monospace;font-size:8px;color:#8a7968;'
                    f'text-transform:uppercase;letter-spacing:.1em;margin:10px 0 4px;">'
                    f'Appliquer ces mêmes coûts aux variantes couleur</div>',
                    unsafe_allow_html=True)
                _vcols = st.columns(min(len(_variants), 4))
                for _vi, _var in enumerate(_variants):
                    with _vcols[_vi % 4]:
                        if st.checkbox(
                            f"{_var[2] or _var[1]}",
                            key=f"apply_var_{_var[0]}"):
                            _sel_vars.append(_var[0])

        _submit_label = "💾 Enregistrer les coûts & prix" if _couts_editable else "👁 Lecture seule — modifications désactivées"
        if st.form_submit_button(_submit_label, type="primary", disabled=not _couts_editable):
            # 1. Migrer les colonnes manquantes dans product_costs
            _existing_pc_cols = [r[1] for r in conn.execute("PRAGMA table_info(product_costs)").fetchall()]
            _all_cost_keys = list(all_inputs.keys())
            for _ck in _all_cost_keys:
                if _ck not in _existing_pc_cols and _ck != "product_id":
                    try:
                        conn.execute(f"ALTER TABLE product_costs ADD COLUMN {_ck} REAL DEFAULT 0")
                        conn.commit()
                    except Exception:
                        pass
            # 2. Re-lire les colonnes après migration
            _valid_pc_cols = set(r[1] for r in conn.execute("PRAGMA table_info(product_costs)").fetchall())
            # 3. Filtrer all_inputs sur les colonnes valides + product_id
            all_inputs["product_id"] = sel_pid
            _safe_inputs = {k: v for k, v in all_inputs.items() if k in _valid_pc_cols}
            if "product_id" not in _safe_inputs:
                _safe_inputs["product_id"] = sel_pid
            cols_str = ", ".join(_safe_inputs.keys())
            ph_str   = ", ".join(["?"] * len(_safe_inputs))
            upd_str  = ", ".join(f"{k}=excluded.{k}" for k in _safe_inputs if k != "product_id")
            conn.execute(
                f"INSERT INTO product_costs ({cols_str}) VALUES ({ph_str}) "
                f"ON CONFLICT(product_id) DO UPDATE SET {upd_str}",
                list(_safe_inputs.values()))
            # 2. Synchroniser les prix dans la fiche produit (table products)
            conn.execute("""UPDATE products SET
                prix_retail_eur=?, prix_retail_jpy=?, prix_retail_usd=?,
                prix_wholesale_eu=?, prix_wholesale_asia=?, prix_wholesale_us=?,
                prix_wholesale_fr=?, prix_ff=?
                WHERE id=?""",
                (srp_eu_new, srp_jp_new, srp_us_new,
                 wp_eu_new, wp_as_new, wp_us_new,
                 wp_wd_new, ff_new, sel_pid))
            conn.commit()
            # Propager aux variantes sélectionnées
            for _var_pid in _sel_vars:
                try:
                    _var_ex = conn.execute("SELECT id FROM product_costs WHERE product_id=?", (_var_pid,)).fetchone()
                    _cost_cols = {k: v for k,v in all_inputs.items() if isinstance(v,(int,float))}
                    _set_str = ", ".join(f"{k}=?" for k in _cost_cols)
                    _set_vals = list(_cost_cols.values())
                    if _var_ex:
                        conn.execute(f"UPDATE product_costs SET {_set_str} WHERE product_id=?", _set_vals + [_var_pid])
                    else:
                        _col_str = "product_id, " + ", ".join(_cost_cols.keys())
                        _ph = "?, " + ", ".join("?" for _ in _cost_cols)
                        conn.execute(f"INSERT INTO product_costs ({_col_str}) VALUES ({_ph})", [_var_pid] + _set_vals)
                except Exception: pass
            conn.commit()

            _msg = "✓ Coûts & prix synchronisés vers la fiche produit."
            if _sel_vars: _msg += f" Propagé à {len(_sel_vars)} variante(s)."
            st.success(_msg)
            st.rerun()

    conn.close()