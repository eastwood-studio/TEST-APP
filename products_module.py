# products_module.py — v4.8 — 1776506064
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
STATUTS_PROD = ["Recherche", "Sample & Testing", "Disponible", "Archive"]
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
        df_arc = pd.read_sql("""SELECT type_archive, nom_fichier, notes
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
            _arc_note = str(arc.get("notes","") or arc.get("nom_fichier","") or "")
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

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(KRAFT)
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        # Grain
        import random; random.seed(42)
        canvas.setFillColor(KRAFT_D)
        for _ in range(200):
            x = random.uniform(0, W)
            y = random.uniform(0, H)
            canvas.circle(x, y, 0.25, fill=1, stroke=0)
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
        df_arc = pd.read_sql("SELECT type_archive, nom_fichier, notes FROM product_archives WHERE product_id=?",
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
    _tabs.append("📦 Packaging standard")

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
    tab_pkg      = tab_objs[idx]; idx += 1

    # ── CATALOGUE ──────────────────────────────────────────────────────────────
    with tab_cat:
        c1, c2, c3 = st.columns(3)
        with c1: f_coll  = st.selectbox("Collection", ["Toutes"]+COLLECTIONS_DYN, key="pcat_coll")
        with c2: f_stat  = st.selectbox("Statut",     ["Tous"]+STATUTS_PROD,   key="pcat_stat")
        with c3: f_cat_p = st.selectbox("Catégorie",  ["Toutes"]+CATEGORIES_PROD, key="pcat_cat")

        df_prods = get_products(
            conn,
            collection=None if f_coll=="Toutes" else f_coll,
            statut=None if f_stat=="Tous" else f_stat,
            categorie=None if f_cat_p=="Toutes" else f_cat_p,
        )

        if df_prods.empty:
            st.info("Aucun produit.")
        else:
            for coll_name, grp in df_prods.groupby("collection", sort=False):
                st.markdown(f'<div class="section-title">{coll_name}</div>', unsafe_allow_html=True)
                cols = st.columns(4)
                for i, (_, prod) in enumerate(grp.iterrows()):
                    with cols[i % 4]:
                        # Visuel
                        imgs = get_images(conn, prod["id"])
                        if not imgs.empty and imgs.iloc[0]["data"] is not None:
                            try:
                                b64  = base64.b64encode(bytes(imgs.iloc[0]["data"])).decode()
                                ext  = (imgs.iloc[0]["nom_fichier"] or "img.jpg").split(".")[-1].lower()
                                mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                                st.markdown(f'<div style="aspect-ratio:3/4;background:{EW_C};overflow:hidden;margin-bottom:6px;"><img src="data:{mime};base64,{b64}" style="width:100%;height:100%;object-fit:cover;"/></div>', unsafe_allow_html=True)
                            except Exception:
                                st.markdown(f'<div style="aspect-ratio:3/4;background:{EW_C};display:flex;align-items:center;justify-content:center;margin-bottom:6px;"><span style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_B};">VISUEL</span></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="aspect-ratio:3/4;background:{EW_C};display:flex;align-items:center;justify-content:center;margin-bottom:6px;"><span style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_B};">VISUEL</span></div>', unsafe_allow_html=True)

                        stat_c = {"Disponible":EW_G,"Développement":"#c9800a","Production":EW_V,
                                  "Concept":"#888","Soldé":"#c1440e","Archive":"#555"}.get(prod.get("statut",""),"#888")

                        # Badge coûts à définir
                        costs_ok = get_costs(conn, prod["id"])
                        couts_total = compute_cost_totals(dict(costs_ok)).get("TOTAL",0) if costs_ok is not None else 0
                        badge_cout = f'<div style="font-family:\'DM Mono\',monospace;font-size:8px;background:#fdf6ec;color:#c9800a;padding:2px 6px;display:inline-block;margin-top:2px;">COÛTS À DÉFINIR</div>' if couts_total == 0 else ""

                        st.markdown(f"""
<div style="margin-bottom:10px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_B};">{prod.get('ref','')}</div>
  <div style="font-size:13px;font-weight:500;color:#1a1a1a;margin:1px 0;">{prod['nom']}</div>
  {f'<div style="font-size:13px;font-weight:500;color:{EW_K};margin-top:2px;">{prod["variant"]}</div>' if prod.get("variant") else ''}
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{stat_c};">● {prod.get('statut','')}</div>

  {badge_cout}
</div>""", unsafe_allow_html=True)

                        if st.button("Voir →", key=f"voir_{prod['id']}"):
                            st.session_state["product_view"] = prod["id"]; st.rerun()


    # ── GESTION DES ARTICLES (Jules only) ───────────────────────────────────


    # ── NOUVEAU PRODUIT ────────────────────────────────────────────────────────
    if tab_new is not None:
        with tab_new:
            st.markdown(f'<div class="section-title">Nouveau produit</div>', unsafe_allow_html=True)
            nc1,nc2,nc3 = st.columns(3)
            with nc1:
                n_ref   = st.text_input("SKU *", placeholder="EWSJACKET-001A")
                n_iref  = st.text_input("Réf. interne")
                n_nom   = st.text_input("Nom *")
            with nc2:
                # Collection avec création inline
                coll_new_opts = COLLECTIONS_DYN + ["➕ Nouvelle collection..."]
                n_coll_sel = st.selectbox("Collection", coll_new_opts)
                if n_coll_sel == "➕ Nouvelle collection...":
                    n_coll = st.text_input("Nom de la nouvelle collection", placeholder="Chapter III — ...")
                else:
                    n_coll = n_coll_sel
                n_cat   = st.selectbox("Catégorie", CATEGORIES_PROD)
                n_stat  = st.selectbox("Statut", STATUTS_PROD)
                n_made  = st.text_input("Made in", placeholder="Paris / Japan")
            with nc3:
                n_mat   = st.text_input("Matières")
                n_coul  = st.text_input("Couleurs")
                n_tail  = st.text_input("Tailles", placeholder="1(S) / 2(M) / 3(L) / 4(XL)")
                n_moq   = st.number_input("MOQ", min_value=0, value=0)
                n_deliv = st.text_input("Delivery", placeholder="June 2026")
            n_desc = st.text_area("Description", height=70)

            st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;color:#8a7968;text-transform:uppercase;letter-spacing:.15em;margin:8px 0 4px;">Prix Retail (B2C)</div>', unsafe_allow_html=True)
            rp1,rp2,rp3 = st.columns(3)
            with rp1: n_preu = st.number_input("SRP EU (€)", min_value=0.0, value=0.0)
            with rp2: n_prjp = st.number_input("SRP JP (¥)", min_value=0.0, value=0.0)
            with rp3: n_prusd = st.number_input("SRP US ($)", min_value=0.0, value=0.0)

            st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;color:#8a7968;text-transform:uppercase;letter-spacing:.15em;margin:8px 0 4px;">Prix Wholesale (B2B)</div>', unsafe_allow_html=True)
            wp1,wp2,wp3,wp4 = st.columns(4)
            with wp1: n_pweu  = st.number_input("WP EU (€)", min_value=0.0, value=0.0)
            with wp2: n_pwas  = st.number_input("WP Asie (€)", min_value=0.0, value=0.0)
            with wp3: n_pwus  = st.number_input("WP US (€)", min_value=0.0, value=0.0)
            with wp4: n_pff   = st.number_input("F&F (€)", min_value=0.0, value=0.0)

            if st.button("✓ Créer le produit", type="primary"):
                if not n_ref or not n_nom:
                    st.error("SKU et nom obligatoires.")
                elif not n_coll:
                    st.error("Collection obligatoire.")
                else:
                    try:
                        # Auto-conv JPY/USD si vides
                        jpy_n = n_prjp if n_prjp > 0 else round(n_preu * 160, 0)
                        usd_n = n_prusd if n_prusd > 0 else round(n_preu * 1.08, 2)
                        conn.execute("""INSERT INTO products
                            (ref,internal_ref,nom,variant,categorie,collection,statut,
                             description,matieres,couleurs,tailles,made_in,moq,delivery,
                             prix_retail_eur,prix_retail_jpy,prix_retail_usd,
                             prix_wholesale_eu,prix_wholesale_asia,prix_wholesale_us,
                             prix_wholesale_fr,prix_ff)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (n_ref,n_iref,n_nom,n_var,n_cat,n_coll,n_stat,
                             n_desc,n_mat,n_coul,n_tail,n_made,n_moq,n_deliv,
                             n_preu, jpy_n, usd_n,
                             n_pweu, n_pwas, n_pwus, n_pweu, n_pff))
                        conn.commit()
                        st.success(f"✓ Produit {n_ref} créé dans « {n_coll} ».")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ce SKU existe déjà.")

    # ── GESTION DES ARTICLES ─────────────────────────────────────────────────
    if tab_gestion is not None:
      with tab_gestion:
        st.markdown('<div class="section-title">Gestion des articles</div>', unsafe_allow_html=True)
        # Filtres
        ga_f1, ga_f2, ga_f3 = st.columns(3)
        with ga_f1:
            ga_type_f = st.selectbox("Type", ["Produit fini","Archive","Sample","Tous"], key="ga_type_f")
        with ga_f2:
            ga_coll_f = st.selectbox("Collection", ["Toutes"] + get_collections_dynamic(conn), key="ga_coll_f")
        with ga_f3:
            ga_search = st.text_input("Rechercher", placeholder="nom ou SKU...", key="ga_search")

        df_pf_art = get_products(conn,
            collection=None if ga_coll_f=="Toutes" else ga_coll_f)
        if not df_pf_art.empty:
            if ga_type_f == "Produit fini":
                df_pf_art = df_pf_art[df_pf_art["statut"].isin(["Disponible","Sample & Testing","Recherche"])]
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
                    ga_mat  = st.text_area("Matières", value=str(art.get("matieres","") or ""), height=80)
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
                        tailles=?,made_in=?,matieres=?,description=?,delivery=?,moq=?,
                        collection=?,statut=? WHERE id=?""",
                        (ga_nom,ga_ref,ga_iref,ga_col,ga_tail,ga_made,ga_mat,ga_desc,
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
                if not df_comp_ga.empty:
                    for _, comp in df_comp_ga.iterrows():
                        st.markdown(f"**{comp.get('nom_exact') or comp.get('nom','')}** · {comp.get('categorie_comp','')} · {comp.get('quantite','')} {comp.get('unite','')}")
                else:
                    st.info("Aucun composant.")
                # Ajouter composant
                with st.expander("➕ Ajouter un composant"):
                    with st.form(f"ga_comp_{pid_art}"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            ca_nom = st.text_input("Nom composant")
                            ca_cat = st.selectbox("Catégorie", ["MP Principale","MP Secondaire","Doublure","Broderie","Zip","Bouton","Étiquette","Packaging","Autre"])
                        with c2:
                            ca_qte  = st.number_input("Quantité", min_value=0.0, step=0.1)
                            ca_unit = st.selectbox("Unité", ["Pièces","Mètres","kg","g","m²"])
                        with c3:
                            ca_ref = st.text_input("Référence fournisseur")
                            ca_desc = st.text_input("Description")
                        if st.form_submit_button("Ajouter"):
                            if ca_nom:
                                conn.execute("""INSERT INTO product_components
                                    (product_id,nom_exact,categorie_comp,quantite,unite,ref_fournisseur,description)
                                    VALUES (?,?,?,?,?,?,?)""",
                                    (pid_art,ca_nom,ca_cat,ca_qte,ca_unit,ca_ref,ca_desc))
                                conn.commit(); st.rerun()

            with ga_t2:
                try:
                    df_arc_ga = pd.read_sql("SELECT * FROM product_archives WHERE product_id=? ORDER BY id",
                                            conn, params=[pid_art])
                except Exception:
                    df_arc_ga = pd.DataFrame()
                if not df_arc_ga.empty:
                    for _, arc in df_arc_ga.iterrows():
                        st.markdown(f"**{arc.get('type_archive','')}** — {arc.get('notes','') or arc.get('nom_fichier','')}")
                else:
                    st.info("Aucune archive.")
                with st.expander("➕ Ajouter une archive"):
                    arc_type = st.selectbox("Type", ["Archive","Technique","Matière"], key=f"arc_t_{pid_art}")
                    arc_nom  = st.text_input("Titre / Notes", key=f"arc_n_{pid_art}")
                    arc_file = st.file_uploader("Fichier", type=["jpg","jpeg","png","pdf"], key=f"arc_f_{pid_art}")
                    if arc_file and st.button("✓ Ajouter archive", key=f"arc_btn_{pid_art}"):
                        arc_bytes = arc_file.read()
                        conn.execute("""INSERT INTO product_archives (product_id,type_archive,nom_fichier,fichier_data,notes)
                            VALUES (?,?,?,?,?)""",
                            (pid_art, arc_type, arc_file.name, arc_bytes, arc_nom))
                        conn.commit(); st.rerun()

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
    with tab_pkg:
        st.markdown(f'<div class="section-title">Packaging standard Eastwood</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="info-box">
Le packaging standard est automatiquement déduit du stock à chaque commande. Il s'applique à tous les envois.
</div>""", unsafe_allow_html=True)

        df_pkg = get_packaging(conn)
        if df_pkg.empty:
            st.info("Aucun élément de packaging.")
        else:
            for _, pkg in df_pkg.iterrows():
                pk1, pk2 = st.columns([4, 1])
                with pk1:
                    st.markdown(f"""
<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid {EW_S};">
  <div>
    <span style="font-weight:500;font-size:13px;">{pkg['nom']}</span>
    <span style="font-family:'DM Mono',monospace;font-size:10px;color:{EW_B};margin-left:10px;">{pkg.get('ref_stock','')}</span>
    {f'<div style="font-size:11px;color:{EW_B};">{pkg["notes"]}</div>' if pkg.get("notes") else ''}
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;">{pkg['quantite']} {pkg['unite']} / commande</div>
</div>""", unsafe_allow_html=True)
                with pk2:
                    if can_fn("stock_write"):
                        if st.button("🗑", key=f"del_pkg_{pkg['id']}"):
                            conn.execute("UPDATE packaging_standard SET actif=0 WHERE id=?", (pkg["id"],))
                            conn.commit(); st.rerun()

        if can_fn("stock_write"):
            st.markdown(f'<div class="section-title">Ajouter un élément de packaging</div>', unsafe_allow_html=True)
            with st.form("add_pkg"):
                p1,p2,p3 = st.columns(3)
                with p1: pk_nom  = st.text_input("Nom *")
                with p2: pk_ref  = st.text_input("Réf. stock")
                with p3: pk_qte  = st.number_input("Qté / commande", min_value=0.0, value=1.0)
                pk_unit = st.selectbox("Unité", ["Pièces","Lot","Mètre"])
                pk_cout = st.number_input("Coût unitaire (€)", min_value=0.0, value=0.0, step=0.01)
                pk_notes = st.text_input("Notes")
                if st.form_submit_button("➕ Ajouter"):
                    if not pk_nom: st.error("Nom obligatoire.")
                    else:
                        conn.execute("""INSERT INTO packaging_standard
                            (nom,ref_stock,quantite,unite,cout_unitaire,notes)
                            VALUES (?,?,?,?,?,?)""",
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

    # Vue globale : tableau de tous les coûts totaux
    st.markdown('<div class="section-title">Vue globale</div>', unsafe_allow_html=True)
    rows_global = []
    for _, prod in df_filtered.iterrows():
        cr = get_costs(conn, prod["id"])
        cd = dict(cr) if cr is not None else {}
        totals = compute_cost_totals(cd)
        grand = totals.get("TOTAL", 0)
        srp = float(prod.get("prix_retail_eur",0) or 0)
        marge = round((srp - grand)/srp*100, 1) if srp > 0 and grand > 0 else None
        rows_global.append({
            "Réf.":           prod.get("ref",""),
            "Nom":            f"{prod['nom']}{' / '+prod['variant'] if prod.get('variant') else ''}",
            "Collection":     prod.get("collection",""),
            "Coût total":     fmt_eur_fn(grand) if grand > 0 else "COÛTS À DÉFINIR",
            "SRP EU":         fmt_eur_fn(srp),
            "Marge brute":    f"{marge}%" if marge is not None else "—",
            "Statut":         "✓" if grand > 0 else "⚠",
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

    with st.form(f"costs_finance_{sel_pid}"):
        all_inputs = {}
        for sect, fields in COST_SECTIONS.items():
            # Titre de section plus grand
            st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#1a1a1a;border-bottom:2px solid #d9c8ae;padding:8px 0 4px;margin:14px 0 8px;">{sect}</div>', unsafe_allow_html=True)

            if sect == "Marketing":
                # Case à cocher + calcul auto
                apply_mkt = st.checkbox(
                    "Appliquer les frais marketing",
                    value=bool(costs_dict.get("cout_marketing_pct", 0)),
                    key=f"mkt_apply_{sel_pid}"
                )
                pct_mkt = st.number_input(
                    "Pourcentage marketing (%)", min_value=0.0, max_value=50.0,
                    value=float(costs_dict.get("cout_marketing_pct_val", 5.0) or 5.0),
                    step=0.1, key=f"mkt_pct_{sel_pid}"
                )
                # Calcul auto : 6% * (cout_sample + (cout_prod+mp+compo+etiq+log+pkg)*14/15)
                _s_keys = [k for k,_ in COST_SECTIONS.get("Développement sample",[])]
                _p_keys = ([k for k,_ in COST_SECTIONS.get("MP & Composants",[])] +
                           [k for k,_ in COST_SECTIONS.get("Étiquettes",[])] +
                           [k for k,_ in COST_SECTIONS.get("Production & Réalisation",[])] +
                           [k for k,_ in COST_SECTIONS.get("Logistique & Douanes",[])] +
                           [k for k,_ in COST_SECTIONS.get("Packaging",[])])
                _cout_sample = sum(float(costs_dict.get(k,0) or 0) for k in _s_keys)
                _cout_prod   = sum(float(costs_dict.get(k,0) or 0) for k in _p_keys)
                _mkt_calc = round(0.06 * (_cout_sample + (_cout_prod * 14 / 15)), 2)
                _pct_calc = round(_mkt_calc / max(_cout_sample + _cout_prod, 1) * 100, 1)
                st.markdown(f"""
<div style="background:#f5f0e8;border-left:3px solid #7b506f;padding:8px 12px;margin:4px 0;">
  <div style="font-size:11px;color:#8a7968;">Calcul automatique (6% × formule)</div>
  <div style="font-family:'DM Mono',monospace;font-size:14px;font-weight:500;">
    {fmt_eur_fn(_mkt_calc)} <span style="font-size:10px;color:#8a7968;">({_pct_calc}% du coût total)</span>
  </div>
  {'<div style="font-size:10px;color:#395f30;font-weight:500;">✓ Marketing appliqué</div>' if apply_mkt else '<div style="font-size:10px;color:#aaa;">Marketing non appliqué</div>'}
</div>""", unsafe_allow_html=True)
                all_inputs["cout_marketing_pct"] = 1 if apply_mkt else 0
                all_inputs["cout_marketing_pct_val"] = pct_mkt
                all_inputs["cout_marketing"] = _mkt_calc if apply_mkt else 0.0
                continue

            n_cols = min(len(fields), 3)
            fcols = st.columns(n_cols)
            for i, (key, label) in enumerate(fields):
                with fcols[i % n_cols]:
                    val = float(costs_dict.get(key, 0) or 0)
                    all_inputs[key] = st.number_input(
                        label, min_value=0.0, step=0.01, value=val,
                        key=f"cf_{key}_{sel_pid}")

        # Section automatique depuis les composants
        df_comps = get_components(conn, sel_pid)
        if not df_comps.empty:
            st.markdown(f'<div class="section-title">Composants liés (depuis fiche produit)</div>', unsafe_allow_html=True)
            total_comps = 0.0
            for _, comp in df_comps.iterrows():
                val_c = float(comp.get("quantite",0) or 0) * float(comp.get("cout_unitaire",0) or 0)
                total_comps += val_c
                st.markdown(f"""
<div style="display:flex;justify-content:space-between;font-size:12px;padding:3px 0;border-bottom:1px solid #f0ece4;">
  <span>{comp.get('nom_exact') or comp.get('nom','')} <span style="color:#8a7968;font-size:10px;">({comp.get('categorie_comp','')})</span></span>
  <span style="font-family:'DM Mono',monospace;">{comp['quantite']} {comp['unite']} × {fmt_eur_fn(comp['cout_unitaire'])} = {fmt_eur_fn(val_c)}</span>
</div>""", unsafe_allow_html=True)
            st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:12px;font-weight:500;margin-top:4px;">Total composants : {fmt_eur_fn(total_comps)}</div>', unsafe_allow_html=True)

        if st.form_submit_button("💾 Enregistrer les coûts", type="primary"):
            all_inputs["product_id"] = sel_pid
            cols_str = ", ".join(all_inputs.keys())
            ph_str   = ", ".join(["?"] * len(all_inputs))
            upd_str  = ", ".join(f"{k}=?" for k in all_inputs if k != "product_id")
            conn.execute(
                f"INSERT INTO product_costs ({cols_str}) VALUES ({ph_str}) "
                f"ON CONFLICT(product_id) DO UPDATE SET {upd_str}",
                list(all_inputs.values()) +
                [v for k,v in all_inputs.items() if k != "product_id"])
            conn.commit(); st.success("✓ Coûts enregistrés."); st.rerun()

    conn.close()
