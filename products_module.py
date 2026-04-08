# products_module.py — v3.1 — build 1775605457
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
    "Chapter N°II — Le Souvenir (SS26)",
    "Chapter N°I — Hunting & Fishing (AW26)",
    "Archive",
]
STATUTS_PROD = ["Recherche", "Sample & Testing", "Production", "Disponible", "Archive"]
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
    # ── Chapter N°II — Le Souvenir ────────────────────────────────────────────
    {
        "ref": "EWSJACKET-003A", "internal_ref": "EWSJACKET-003A",
        "nom": "Akagi Jacket", "variant": "Tobacco",
        "categorie": "Jacket", "collection": "Chapter N°II — Le Souvenir (SS26)",
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
        "categorie": "Jacket", "collection": "Chapter N°II — Le Souvenir (SS26)",
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
        "categorie": "Shirt", "collection": "Chapter N°II — Le Souvenir (SS26)",
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
        "categorie": "Shirt", "collection": "Chapter N°II — Le Souvenir (SS26)",
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
        "categorie": "Shirt", "collection": "Chapter N°II — Le Souvenir (SS26)",
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
        "categorie": "Gear / Accessory", "collection": "Chapter N°II — Le Souvenir (SS26)",
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
        "categorie": "Gear / Accessory", "collection": "Chapter N°II — Le Souvenir (SS26)",
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
        "categorie": "Gear / Accessory", "collection": "Chapter N°II — Le Souvenir (SS26)",
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
        "categorie": "Gear / Accessory", "collection": "Chapter N°II — Le Souvenir (SS26)",
        "statut": "Disponible",
        "cost_eur": 0, "prix_wholesale_fr": 59, "prix_retail_eur": 75,
        "moq": 5, "delivery": "June 2026", "origine": "France",
        "description": "Inspired by souvenir bandanas once sold in roadside shops, this piece reimagines Paris as a distant island, a treasure of culture and memory. Featuring hand-drawn motifs of monuments and symbols framed by a nautical rope border, printed on an off-white base in deep red and navy tones.",
        "matieres": "Organic Silk", "couleurs": "Red / Off-white", "tailles": "One size (55x55cm)",
        "made_in": "Paris",
    },
    # ── Chapter N°I — Hunting & Fishing ───────────────────────────────────────
    {
        "ref": "EWSJACKET-001A", "internal_ref": "EWSJACKET-001A",
        "nom": "Waterfowl Jacket", "variant": "Tobacco",
        "categorie": "Jacket", "collection": "Chapter N°I — Hunting & Fishing (AW26)",
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
        "categorie": "Jacket", "collection": "Chapter N°I — Hunting & Fishing (AW26)",
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
        "categorie": "Jacket", "collection": "Chapter N°I — Hunting & Fishing (AW26)",
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
    "Chapter N°I — Hunting & Fishing",
    "Chapter N°II — Le Souvenir",
]

COLLECTIONS = _COLLECTIONS_DEFAULT.copy()


def get_collections_dynamic(conn):
    """Collections depuis la DB, fusionnées avec les défauts."""
    try:
        rows = conn.execute(
            "SELECT DISTINCT collection FROM products WHERE collection IS NOT NULL AND collection != '' ORDER BY collection"
        ).fetchall()
        from_db = [r[0] for r in rows if r[0]]
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
    if not REPORTLAB_OK:
        return None, "reportlab non installé"

    buf = io.BytesIO()
    W, H = A4
    M = 15 * mm

    EW_C_rl = colors.HexColor("#f5f0e8")
    EW_S_rl = colors.HexColor("#ede3d3")
    EW_K_rl = colors.HexColor("#1a1a1a")
    EW_B_rl = colors.HexColor("#8a7968")
    EW_V_rl = colors.HexColor("#7b506f")
    GREY_rl  = colors.HexColor("#f0ede8")

    q = "SELECT * FROM products WHERE 1=1"
    p = []
    if collection_filter:
        q += " AND collection=?"; p.append(collection_filter)
    df = pd.read_sql(q + " ORDER BY collection, categorie, nom, variant", conn, params=p)

    if df.empty:
        return None, "Aucun produit"

    s_brand = ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=16,
                              textColor=EW_K_rl, letterSpacing=3, alignment=TA_CENTER)
    s_sub   = ParagraphStyle("sub",   fontName="Helvetica", fontSize=7,
                              textColor=EW_B_rl, letterSpacing=5, alignment=TA_CENTER, spaceAfter=2)
    s_coll  = ParagraphStyle("coll",  fontName="Helvetica-Bold", fontSize=8,
                              textColor=EW_K_rl, letterSpacing=2, alignment=TA_CENTER)
    s_label = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8, textColor=EW_K_rl)
    s_small = ParagraphStyle("small", fontName="Helvetica", fontSize=7.5, textColor=EW_B_rl)
    s_ref   = ParagraphStyle("ref",   fontName="Helvetica", fontSize=7, textColor=EW_B_rl)
    s_foot  = ParagraphStyle("foot",  fontName="Helvetica", fontSize=6.5,
                              textColor=EW_B_rl, alignment=TA_CENTER)

    story = []

    # Grouper par nom de produit (regrouper les coloris)
    seen_products = {}
    for _, prod in df.iterrows():
        key = prod["nom"]
        if key not in seen_products:
            seen_products[key] = []
        seen_products[key].append(prod)

    for prod_nom, variants in seen_products.items():
        first = variants[0]

        # ── En-tête page ─────────────────────────────────────────────────────
        story.append(Paragraph("EASTWOOD STUDIO", s_brand))
        story.append(Paragraph("ORDER SHEET  ·  AW26", s_sub))

        coll_name = str(first.get("collection","")).upper()
        story.append(HRFlowable(width="100%", thickness=0.8, color=EW_K_rl))
        story.append(Spacer(1, 1*mm))
        story.append(Paragraph(coll_name, s_coll))
        story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl))
        story.append(Spacer(1, 4*mm))

        # ── Header produit ────────────────────────────────────────────────────
        hdr_data = [[
            Paragraph(f"<b>{prod_nom}</b>", s_label),
            Paragraph(str(first.get("ref","")), s_ref),
            Paragraph("<b>Retail</b>", s_label),
        ]]
        hdr_tbl = Table(hdr_data, colWidths=[(W-2*M)*0.4, (W-2*M)*0.35, (W-2*M)*0.25])
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), GREY_rl),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
        ]))
        story.append(hdr_tbl)

        # ── Tableau tailles par coloris ────────────────────────────────────────
        # Déterminer les tailles dispo
        tailles_str = str(first.get("tailles",""))
        sizes = []
        if "XXL" in tailles_str or "5(XXL)" in tailles_str:
            sizes = ["T1 (S)", "T2 (M)", "T3 (L)", "T4 (XL)", "T5 (XXL)"]
        elif "One size" in tailles_str or "one size" in tailles_str or "OS" in tailles_str:
            sizes = ["OS"]
        else:
            sizes = ["T1 (S)", "T2 (M)", "T3 (L)", "T4 (XL)"]

        IMG_W = 55*mm
        IMG_H = 70*mm
        COL_IMG = IMG_W + 2*mm

        # Colonnes : image | Quantity header | size columns
        n_sizes = len(sizes)
        size_col_w = (W - 2*M - COL_IMG - 40*mm) / max(n_sizes, 1)

        for variant_prod in variants:
            variant_name = str(variant_prod.get("variant",""))

            # Image
            imgs = pd.read_sql(
                "SELECT data FROM product_images WHERE product_id=? ORDER BY ordre LIMIT 1",
                conn, params=[variant_prod["id"]])

            if not imgs.empty and imgs.iloc[0]["data"] is not None:
                try:
                    img_io = io.BytesIO(bytes(imgs.iloc[0]["data"]))
                    cell_img = RLImage(img_io, width=IMG_W, height=IMG_H, kind="proportional")
                except Exception:
                    cell_img = ""
            else:
                # Placeholder
                ph_tbl = Table([[""]], colWidths=[IMG_W], rowHeights=[IMG_H])
                ph_tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0,0),(-1,-1), EW_C_rl),
                    ("BOX",        (0,0),(-1,-1), 0.3, EW_S_rl),
                ]))
                cell_img = ph_tbl

            # Ligne Quantity header
            qty_header = ["", "Quantity", ""] + [""] * (n_sizes - 1)
            # Ligne Color/Size
            color_size = ["Color", "Size"] + sizes
            # Ligne variant
            variant_row = [cell_img, Paragraph(variant_name, s_small)] + [""] * n_sizes
            # Ligne Total
            total_row = ["", "TOTAL"] + [""] * n_sizes

            col_widths = [COL_IMG, 40*mm] + [size_col_w] * n_sizes
            tbl_data = [color_size, variant_row, total_row]

            row_tbl = Table(tbl_data, colWidths=col_widths, rowHeights=[None, IMG_H, None])
            row_tbl.setStyle(TableStyle([
                ("FONTNAME",      (0,0), (-1,-1), "Helvetica"),
                ("FONTSIZE",      (0,0), (-1,-1), 7.5),
                ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
                ("BACKGROUND",    (0,0), (-1,0),  GREY_rl),
                ("BACKGROUND",    (0,-1),(-1,-1), GREY_rl),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                ("ALIGN",         (2,0), (-1,-1), "CENTER"),
                ("ALIGN",         (0,0), (1,-1),  "LEFT"),
                ("LEFTPADDING",   (0,0), (-1,-1), 5),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("BOX",           (0,0), (-1,-1), 0.5, EW_S_rl),
                ("INNERGRID",     (0,0), (-1,-1), 0.3, EW_S_rl),
            ]))
            story.append(row_tbl)
            story.append(Spacer(1, 2*mm))

        # ── Infos produit (matieres, livraison, MOQ) ──────────────────────────
        story.append(Spacer(1, 2*mm))
        info_rows = []
        if first.get("matieres"):
            info_rows.append([Paragraph("Materials", s_ref), Paragraph(str(first["matieres"]), s_small)])
        if first.get("made_in"):
            info_rows.append([Paragraph("Made in", s_ref), Paragraph(str(first["made_in"]), s_small)])
        if first.get("delivery"):
            info_rows.append([Paragraph("Delivery window", s_ref), Paragraph(str(first["delivery"]), s_small)])
        if first.get("moq"):
            info_rows.append([Paragraph("MOQ", s_ref), Paragraph(f"{first['moq']} units", s_small)])

        if info_rows:
            info_tbl = Table(info_rows, colWidths=[(W-2*M)*0.25, (W-2*M)*0.75])
            info_tbl.setStyle(TableStyle([
                ("TOPPADDING",    (0,0),(-1,-1), 2),
                ("BOTTOMPADDING", (0,0),(-1,-1), 2),
                ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ]))
            story.append(info_tbl)

        # ── Section contact ────────────────────────────────────────────────────
        story.append(Spacer(1, 8*mm))
        story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl))
        story.append(Spacer(1, 3*mm))

        contact_data = [
            [Paragraph("<b>CONTACT</b>", s_label), "", "", ""],
            [Paragraph("Name", s_ref), "", Paragraph("E-mail", s_ref), ""],
            [Paragraph("Tel.", s_ref), "", Paragraph("Address", s_ref), ""],
        ]
        contact_tbl = Table(contact_data,
                            colWidths=[(W-2*M)*0.12, (W-2*M)*0.38, (W-2*M)*0.12, (W-2*M)*0.38])
        contact_tbl.setStyle(TableStyle([
            ("SPAN",          (0,0), (-1,0)),
            ("ALIGN",         (0,0), (-1,0), "CENTER"),
            ("INNERGRID",     (0,1), (-1,-1), 0.3, EW_S_rl),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ]))
        story.append(contact_tbl)

        # ── Footer ─────────────────────────────────────────────────────────────
        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S_rl))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(
            "Eastwood Studio — SAS 933845042 — contact@eastwood-studio.fr  "
            "+33 (0)7 51 61 02 52  |  +33 (0)6 74 61 80 98", s_foot))

        story.append(PageBreak())

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=M, rightMargin=M,
                            topMargin=10*mm, bottomMargin=10*mm)
    doc.build(story)
    return buf.getvalue(), None


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION LINE SHEET (sans prix détaillés — visuels + matières + MOQ)
# ══════════════════════════════════════════════════════════════════════════════
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
def generate_fiche_technique(conn, product_id):
    if not REPORTLAB_OK:
        return None, "reportlab non installé"

    df_p = get_product(conn, product_id)
    if df_p.empty:
        return None, "Produit introuvable"
    prod = df_p.iloc[0]
    comps = get_components(conn, product_id)
    archives = pd.read_sql("SELECT * FROM product_archives WHERE product_id=?", conn, params=[product_id])

    buf = io.BytesIO()
    W, H = landscape(A4)
    M = 14 * mm

    # Couleurs
    EW_K_rl = colors.HexColor("#1a1a1a")
    EW_B_rl = colors.HexColor("#8a7968")
    EW_S_rl = colors.HexColor("#ede3d3")
    EW_C_rl = colors.HexColor("#f5f0e8")
    RED_rl  = colors.HexColor("#8b0000")  # Tampon rouge confidentiel

    # Styles typewriter
    s_tw_title = ParagraphStyle("tw_title", fontName="Courier-Bold", fontSize=13,
                                textColor=EW_K_rl, letterSpacing=2, spaceAfter=4)
    s_tw_head  = ParagraphStyle("tw_head",  fontName="Courier-Bold", fontSize=8,
                                textColor=EW_K_rl, letterSpacing=1, spaceAfter=2)
    s_tw_body  = ParagraphStyle("tw_body",  fontName="Courier", fontSize=7.5,
                                textColor=EW_K_rl, leading=12, spaceAfter=2)
    s_tw_small = ParagraphStyle("tw_small", fontName="Courier", fontSize=6.5,
                                textColor=EW_B_rl, leading=10)
    s_tw_ref   = ParagraphStyle("tw_ref",   fontName="Courier-Oblique", fontSize=7,
                                textColor=EW_B_rl)
    s_tw_conf  = ParagraphStyle("tw_conf",  fontName="Courier-Bold", fontSize=16,
                                textColor=RED_rl, letterSpacing=4, alignment=TA_CENTER)

    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=M, rightMargin=M,
                            topMargin=M, bottomMargin=M)
    story = []

    # ── En-tête confidentiel ────────────────────────────────────────────────
    story.append(Paragraph("EASTWOOD STUDIO — DOSSIER TECHNIQUE", s_tw_head))
    story.append(Paragraph("CONFIDENTIEL", s_tw_conf))
    story.append(HRFlowable(width="100%", thickness=1, color=EW_K_rl))
    story.append(Spacer(1, 3*mm))

    # ── Layout principal : image gauche | infos droite ─────────────────────
    IMG_COL = 80*mm
    INFO_COL = W - 2*M - IMG_COL - 8*mm

    # Colonne image
    imgs = get_images(conn, product_id)
    if not imgs.empty and imgs.iloc[0]["data"] is not None:
        try:
            img_io = io.BytesIO(bytes(imgs.iloc[0]["data"]))
            img_cell = RLImage(img_io, width=IMG_COL, height=100*mm, kind="proportional")
        except Exception:
            img_cell = ""
    else:
        ph = Table([[Paragraph("[ VISUEL ]", s_tw_small)]], colWidths=[IMG_COL], rowHeights=[100*mm])
        ph.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),EW_C_rl),
            ("BOX",(0,0),(-1,-1),0.5,EW_K_rl),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        img_cell = ph

    # Colonne infos
    info_content = []
    info_content.append(Paragraph(f"REF : {prod.get('ref','')}", s_tw_ref))
    if prod.get("internal_ref"):
        info_content.append(Paragraph(f"INT : {prod['internal_ref']}", s_tw_ref))
    info_content.append(Spacer(1, 2*mm))
    info_content.append(Paragraph(str(prod["nom"]).upper(), s_tw_title))
    if prod.get("variant"):
        info_content.append(Paragraph(str(prod["variant"]), s_tw_body))
    info_content.append(Spacer(1, 2*mm))

    # Fiche ID
    id_fields = [
        ("COLLECTION",  str(prod.get("collection",""))),
        ("STATUT",      str(prod.get("statut",""))),
        ("MADE IN",     str(prod.get("made_in",""))),
        ("MATIÈRES",    str(prod.get("matieres",""))),
        ("COULEURS",    str(prod.get("couleurs",""))),
        ("TAILLES",     str(prod.get("tailles",""))),
        ("LIVRAISON",   str(prod.get("delivery",""))),
        ("MOQ",         f"{prod.get('moq','')} units/size" if prod.get("moq") else "—"),
    ]
    for lbl, val in id_fields:
        if val and val != "None":
            info_content.append(Paragraph(f"{lbl} :", s_tw_head))
            info_content.append(Paragraph(val, s_tw_body))

    info_content.append(Spacer(1, 3*mm))
    if prod.get("description"):
        info_content.append(Paragraph("DESCRIPTION :", s_tw_head))
        info_content.append(Paragraph(str(prod["description"]), s_tw_body))

    main_tbl = Table([[img_cell, info_content]],
                     colWidths=[IMG_COL, INFO_COL])
    main_tbl.setStyle(TableStyle([
        ("VALIGN",      (0,0),(-1,-1),"TOP"),
        ("RIGHTPADDING",(0,0),(0,-1), 8*mm),
        ("BOX",         (0,0),(0,-1), 0.5, EW_K_rl),
    ]))
    story.append(main_tbl)
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=EW_K_rl))
    story.append(Spacer(1, 3*mm))

    # ── Composition matières ────────────────────────────────────────────────
    if not comps.empty:
        story.append(Paragraph("COMPOSITION / MATIÈRES :", s_tw_head))
        story.append(Spacer(1, 1*mm))

        comp_data = [["CATÉGORIE", "MATIÈRE EXACTE", "REF", "QTÉ", "UNITÉ", "FOURNISSEUR"]]
        for _, comp in comps.iterrows():
            comp_data.append([
                str(comp.get("categorie_comp",""))[:25],
                str(comp.get("nom_exact") or comp.get("nom",""))[:30],
                str(comp.get("ref_stock","") or ""),
                str(comp.get("quantite","") or ""),
                str(comp.get("unite","") or ""),
                str(comp.get("fournisseur","") or ""),
            ])
        comp_tbl = Table(comp_data, colWidths=[
            (W-2*M)*0.22, (W-2*M)*0.28, (W-2*M)*0.13,
            (W-2*M)*0.08, (W-2*M)*0.08, (W-2*M)*0.21
        ])
        comp_tbl.setStyle(TableStyle([
            ("FONTNAME",      (0,0),(-1,0),  "Courier-Bold"),
            ("FONTNAME",      (0,1),(-1,-1), "Courier"),
            ("FONTSIZE",      (0,0),(-1,-1), 6.5),
            ("BACKGROUND",    (0,0),(-1,0),  EW_C_rl),
            ("GRID",          (0,0),(-1,-1), 0.3, EW_S_rl),
            ("TOPPADDING",    (0,0),(-1,-1), 2),
            ("BOTTOMPADDING", (0,0),(-1,-1), 2),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ]))
        story.append(comp_tbl)
        story.append(Spacer(1, 3*mm))

    # ── Archives & références ────────────────────────────────────────────────
    if not archives.empty:
        story.append(HRFlowable(width="100%", thickness=0.3, color=EW_K_rl))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph("RÉFÉRENCES & ARCHIVES UTILISÉES :", s_tw_head))
        story.append(Spacer(1, 1*mm))
        for _, arch in archives.iterrows():
            story.append(Paragraph(
                f"[{arch.get('annee','')}] {arch.get('type_archive','')} — "
                f"{arch.get('nom_archive','')} | {arch.get('lieu','')} | {arch.get('details','')}",
                s_tw_small))

    # ── Footer ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=EW_K_rl))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        f"EASTWOOD STUDIO — FICHE TECHNIQUE {prod.get('ref','')} — "
        f"Généré le {date.today().strftime('%d/%m/%Y')} — DOCUMENT INTERNE CONFIDENTIEL",
        s_tw_small))

    doc.build(story)
    return buf.getvalue(), None


# ══════════════════════════════════════════════════════════════════════════════
# SECTIONS DE COÛTS
# ══════════════════════════════════════════════════════════════════════════════
COST_SECTIONS = {
    "Développement sample": [
        ("cout_patronage",    "Patronage (€)"),
        ("cout_gradation",    "Gradation (€)"),
        ("cout_assemblage",   "Assemblage (€)"),
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
        ("cout_lining",       "Doublure / Lining (€)"),
        ("cout_mp_secondaire","MP Secondaire (€)"),
        ("cout_zip",          "Zips (€)"),
        ("cout_boutons",      "Boutons (€)"),
        ("cout_patch",        "Patchs (€)"),
        ("cout_print",        "Prints / Sérigraphie (€)"),
        ("cout_compo1",       "Composant 1 (€)"),
        ("cout_compo2",       "Composant 2 (€)"),
        ("cout_compo3",       "Composant 3 (€)"),
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
        ("cout_marketing", "Marketing % (€)"),
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
    if can_fn("stock_write"): _tabs.append("➕ Nouveau produit")
    _tabs.append("📤 Export documents")
    _tabs.append("📦 Packaging standard")

    # Collections dynamiques chargées depuis la DB
    COLLECTIONS_DYN = get_collections_dynamic(conn)

    tab_objs = st.tabs(_tabs)
    idx = 0
    tab_cat    = tab_objs[idx]; idx += 1
    tab_new    = tab_objs[idx] if can_fn("stock_write") else None
    if can_fn("stock_write"): idx += 1
    tab_export = tab_objs[idx]; idx += 1
    tab_pkg    = tab_objs[idx]; idx += 1

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

        # ── FICHE PRODUIT ──────────────────────────────────────────────────────
        if "product_view" in st.session_state:
            pid = st.session_state["product_view"]
            df_p = get_product(conn, pid)
            if df_p.empty:
                del st.session_state["product_view"]; st.rerun()
            prod = df_p.iloc[0]

            st.markdown("---")
            if st.button("← Retour au catalogue"):
                del st.session_state["product_view"]; st.rerun()

            hc1, hc2 = st.columns([1, 2])
            with hc1:
                imgs = get_images(conn, pid)
                img_idx = st.session_state.get(f"img_idx_{pid}", 0)
                if not imgs.empty:
                    row_img = imgs.iloc[img_idx]
                    if row_img["data"] is not None:
                        try:
                            b64  = base64.b64encode(bytes(row_img["data"])).decode()
                            ext  = (row_img["nom_fichier"] or "img.jpg").split(".")[-1].lower()
                            mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                            st.markdown(f'<div style="background:{EW_C};overflow:hidden;"><img src="data:{mime};base64,{b64}" style="width:100%;object-fit:contain;max-height:300px;"/></div>', unsafe_allow_html=True)
                        except Exception: pass
                    if len(imgs) > 1:
                        nc1,nc2 = st.columns(2)
                        with nc1:
                            if st.button("‹",key=f"prev_{pid}") and img_idx > 0:
                                st.session_state[f"img_idx_{pid}"] = img_idx-1; st.rerun()
                        with nc2:
                            if st.button("›",key=f"next_{pid}") and img_idx < len(imgs)-1:
                                st.session_state[f"img_idx_{pid}"] = img_idx+1; st.rerun()
                else:
                    st.markdown(f'<div style="aspect-ratio:3/4;background:{EW_C};display:flex;align-items:center;justify-content:center;"><span style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_B};">AUCUN VISUEL</span></div>', unsafe_allow_html=True)

                if can_fn("stock_write"):
                    new_imgs = st.file_uploader("Ajouter visuels", accept_multiple_files=True,
                                                type=["png","jpg","jpeg","webp"], key=f"img_up_{pid}")
                    if new_imgs and st.button("✓ Upload", key=f"img_save_{pid}"):
                        for k, f in enumerate(new_imgs):
                            conn.execute("INSERT INTO product_images (product_id,nom_fichier,data,ordre) VALUES (?,?,?,?)",
                                         (pid,f.name,f.read(),len(imgs)+k))
                        conn.commit(); st.success("✓ Visuel(s) ajouté(s)."); st.rerun()

            with hc2:
                st.markdown(f"""
<div style="margin-bottom:14px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_B};letter-spacing:.12em;">
    {prod.get('ref','')} · {prod.get('collection','')}
  </div>
  <div style="font-size:22px;font-weight:500;color:#1a1a1a;margin:4px 0 2px;">
    {prod['nom']}{f' — <span style="font-size:16px;font-style:italic;color:{EW_B};">{prod["variant"]}</span>' if prod.get("variant") else ''}
  </div>
  <div style="font-size:12px;color:{EW_B};">{prod.get('made_in','')} · {prod.get('matieres','')} · {prod.get('tailles','')}</div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;margin-top:4px;">
    WP : {fmt_eur_fn(prod.get('prix_wholesale_fr'))} · SRP : {fmt_eur_fn(prod.get('prix_retail_eur'))} · MOQ : {prod.get('moq','—')} units
  </div>
</div>""", unsafe_allow_html=True)

                if can_fn("stock_write"):
                    with st.form(f"edit_prod_{pid}"):
                        ep1,ep2 = st.columns(2)
                        with ep1:
                            e_nom  = st.text_input("Nom", value=prod.get("nom",""))
                            e_var  = st.text_input("Variant", value=prod.get("variant","") or "")
                            e_ref  = st.text_input("SKU", value=prod.get("ref",""))
                            # Collection dynamique avec option création
                            coll_opts = COLLECTIONS_DYN + ["➕ Nouvelle collection..."]
                            cur_coll  = prod.get("collection","")
                            coll_idx  = COLLECTIONS_DYN.index(cur_coll) if cur_coll in COLLECTIONS_DYN else 0
                            e_coll_sel = st.selectbox("Collection", coll_opts, index=coll_idx)
                            if e_coll_sel == "➕ Nouvelle collection...":
                                e_coll = st.text_input("Nom de la nouvelle collection")
                            else:
                                e_coll = e_coll_sel
                            e_stat = st.selectbox("Statut", STATUTS_PROD,
                                index=STATUTS_PROD.index(prod["statut"]) if prod.get("statut") in STATUTS_PROD else 0)
                            e_cat  = st.selectbox("Catégorie", CATEGORIES_PROD,
                                index=CATEGORIES_PROD.index(prod["categorie"]) if prod.get("categorie") in CATEGORIES_PROD else 0)
                        with ep2:
                            e_mat   = st.text_input("Matières",  value=prod.get("matieres","") or "")
                            e_coul  = st.text_input("Couleurs",  value=prod.get("couleurs","") or "")
                            e_tail  = st.text_input("Tailles",   value=prod.get("tailles","") or "")
                            e_made  = st.text_input("Made in",   value=prod.get("made_in","") or "")
                            e_moq   = st.number_input("MOQ",     value=int(prod.get("moq",0) or 0), min_value=0)
                            e_deliv = st.text_input("Delivery",  value=prod.get("delivery","") or "")
                            e_orig  = st.text_input("Origine",   value=prod.get("origine","") or "")
                        e_desc = st.text_area("Description", value=prod.get("description","") or "", height=80)

                        # ── Grille prix enrichie ──────────────────────────────
                        st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;color:#8a7968;text-transform:uppercase;letter-spacing:.15em;margin:10px 0 6px;">Prix Retail (B2C)</div>', unsafe_allow_html=True)
                        rp1,rp2,rp3 = st.columns(3)
                        with rp1: e_preu  = st.number_input("Site EU (€)", value=float(prod.get("prix_retail_eur",0) or 0), min_value=0.0)
                        with rp2: e_prjp  = st.number_input("Site JP (¥)", value=float(prod.get("prix_retail_jpy",0) or 0), min_value=0.0)
                        with rp3: e_prusd = st.number_input("Site US ($)", value=float(prod.get("prix_retail_usd",0) or 0), min_value=0.0)
                        # Auto-calcul JPY/USD depuis EUR si non saisi
                        if e_preu > 0:
                            jpy_calc = round(e_preu * 160, 0) if e_prjp == 0 else e_prjp
                            usd_calc = round(e_preu * 1.08, 2) if e_prusd == 0 else e_prusd
                            st.markdown(f'<div style="font-size:11px;color:#8a7968;">Auto-conv. : ¥{jpy_calc:,.0f} · ${usd_calc:.2f} (taux indicatifs)</div>', unsafe_allow_html=True)
                        else:
                            jpy_calc = e_prjp; usd_calc = e_prusd

                        st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;color:#8a7968;text-transform:uppercase;letter-spacing:.15em;margin:10px 0 6px;">Prix Wholesale (B2B)</div>', unsafe_allow_html=True)
                        wp1,wp2,wp3,wp4 = st.columns(4)
                        with wp1: e_pweu  = st.number_input("Wholesale EU (€)", value=float(prod.get("prix_wholesale_eu",0) or prod.get("prix_wholesale_fr",0) or 0), min_value=0.0)
                        with wp2: e_pwas  = st.number_input("Wholesale Asie (€)", value=float(prod.get("prix_wholesale_asia",0) or 0), min_value=0.0)
                        with wp3: e_pwus  = st.number_input("Wholesale US (€)", value=float(prod.get("prix_wholesale_us",0) or 0), min_value=0.0)
                        with wp4: e_pff   = st.number_input("F&F (€)", value=float(prod.get("prix_ff",0) or 0), min_value=0.0)

                        if st.form_submit_button("💾 Enregistrer"):
                            conn.execute("""UPDATE products SET
                                nom=?,variant=?,ref=?,collection=?,statut=?,categorie=?,
                                description=?,matieres=?,couleurs=?,tailles=?,made_in=?,
                                moq=?,delivery=?,origine=?,
                                prix_retail_eur=?,prix_retail_jpy=?,prix_retail_usd=?,
                                prix_wholesale_eu=?,prix_wholesale_asia=?,prix_wholesale_us=?,
                                prix_wholesale_fr=?,prix_ff=? WHERE id=?""",
                                (e_nom,e_var,e_ref,e_coll,e_stat,e_cat,
                                 e_desc,e_mat,e_coul,e_tail,e_made,
                                 e_moq,e_deliv,e_orig,
                                 e_preu, jpy_calc, usd_calc,
                                 e_pweu, e_pwas, e_pwus, e_pweu, e_pff,
                                 pid))
                            conn.commit(); st.success("✓ Mis à jour."); st.rerun()

            # Sous-onglets composition / archives
            st.markdown("---")
            ft1, ft2, ft3 = st.tabs(["🧵 Composition", "📚 Archives", "🗑 Gestion"])

            with ft1:
                df_comp = get_components(conn, pid)
                if not df_comp.empty:
                    for cat_c, grp_c in df_comp.groupby("categorie_comp", sort=False):
                        total_cat = (grp_c["quantite"] * grp_c["cout_unitaire"]).sum()
                        st.markdown(f'<div style="font-family:\'DM Mono\',monospace;font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:{EW_V};border-bottom:1px solid {EW_S};padding-bottom:4px;margin:12px 0 8px;">{cat_c} · {fmt_eur_fn(total_cat)}</div>', unsafe_allow_html=True)
                        for _, comp in grp_c.iterrows():
                            st.markdown(f"""
<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f0ece4;font-size:12px;">
  <div>
    <span style="font-weight:500;">{comp.get('nom_exact') or comp.get('nom','')}</span>
    {f'<span style="color:{EW_B};margin-left:8px;font-size:11px;">{comp["fournisseur"]}</span>' if comp.get("fournisseur") else ''}
    {f'<span style="color:{EW_B};margin-left:8px;font-size:11px;">MOQ {comp["moq"]} {comp.get("moq_unite","")}</span>' if comp.get("moq") else ''}
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;">{comp['quantite']} {comp['unite']} · {fmt_eur_fn(comp['cout_unitaire'])}</div>
</div>""", unsafe_allow_html=True)
                else:
                    st.info("Aucun composant.")

                if can_fn("stock_write"):
                    st.markdown(f'<div class="section-title">Ajouter un composant</div>', unsafe_allow_html=True)
                    with st.form(f"add_comp_{pid}"):
                        ac1,ac2 = st.columns(2)
                        with ac1:
                            c_cat  = st.selectbox("Catégorie MP", COMP_CATEGORIES)
                            c_nom  = st.text_input("Nom exact de la matière")
                            c_ref  = st.text_input("Réf. stock")
                            c_four = st.text_input("Fournisseur")
                        with ac2:
                            c_qte  = st.number_input("Quantité / pièce", min_value=0.0, value=1.0)
                            c_unit = st.selectbox("Unité", COMP_UNITES)
                            c_cout = st.number_input("Coût unitaire (€)", min_value=0.0, value=0.0, step=0.01)
                            c_moq  = st.number_input("MOQ", min_value=0.0, value=0.0)
                            c_moq_u = st.selectbox("Unité MOQ", COMP_UNITES, key="moq_u")
                        c_notes = st.text_input("Notes")
                        if st.form_submit_button("➕ Ajouter"):
                            conn.execute("""INSERT INTO product_components
                                (product_id,categorie_comp,ref_stock,nom,nom_exact,
                                 quantite,unite,cout_unitaire,moq,moq_unite,fournisseur,notes)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (pid,c_cat,c_ref,c_nom,c_nom,c_qte,c_unit,c_cout,c_moq,c_moq_u,c_four,c_notes))
                            conn.commit(); st.rerun()

            with ft2:
                df_arch = pd.read_sql("SELECT * FROM product_archives WHERE product_id=?", conn, params=[pid])
                if not df_arch.empty:
                    for _, arch in df_arch.iterrows():
                        st.markdown(f"""
<div style="border-left:2px solid {EW_S};padding:8px 14px;margin:6px 0;">
  <div style="display:flex;gap:10px;align-items:baseline;">
    <span style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_B};">{arch.get('annee','')}</span>
    <span style="font-weight:500;font-size:13px;">{arch.get('nom_archive','')}</span>
    <span style="font-size:11px;color:{EW_B};">{arch.get('type_archive','')} · {arch.get('matiere','')} · {arch.get('lieu','')}</span>
  </div>
  {f'<div style="font-size:11px;color:{EW_B};margin-top:3px;">{arch["details"]}</div>' if arch.get("details") else ''}
</div>""", unsafe_allow_html=True)
                else:
                    st.info("Aucune archive.")

                if can_fn("stock_write"):
                    with st.form(f"add_arch_{pid}"):
                        aa1,aa2,aa3 = st.columns(3)
                        with aa1: a_annee = st.number_input("Année", min_value=1900, max_value=2100, value=1950)
                        with aa2: a_type  = st.selectbox("Type", ["Matière","Couleur","Forme","Technique","Référence visuelle","Autre"])
                        with aa3: a_mat   = st.text_input("Matière")
                        aa4,aa5 = st.columns(2)
                        with aa4: a_nom  = st.text_input("Nom de l'archive")
                        with aa5: a_lieu = st.text_input("Lieu / Source")
                        a_det = st.text_area("Détails", height=50)
                        if st.form_submit_button("➕ Ajouter"):
                            conn.execute("""INSERT INTO product_archives
                                (product_id,annee,type_archive,matiere,nom_archive,lieu,details)
                                VALUES (?,?,?,?,?,?,?)""",
                                (pid,a_annee,a_type,a_mat,a_nom,a_lieu,a_det))
                            conn.commit(); st.rerun()

            with ft3:
                if can_fn("products_delete"):
                    st.warning("Supprimer ce produit est irréversible.")
                    if st.button("🗑 Supprimer ce produit"):
                        for tbl in ["product_images","product_components","product_archives","product_costs"]:
                            conn.execute(f"DELETE FROM {tbl} WHERE product_id=?", (pid,))
                        conn.execute("DELETE FROM products WHERE id=?", (pid,))
                        conn.commit(); del st.session_state["product_view"]; st.rerun()

                imgs_list = get_images(conn, pid)
                if not imgs_list.empty and can_fn("stock_write"):
                    st.markdown("**Visuels**")
                    for _, img_row in imgs_list.iterrows():
                        ci1,ci2 = st.columns([4,1])
                        with ci1: st.write(img_row["nom_fichier"])
                        with ci2:
                            if st.button("🗑", key=f"del_img_{img_row['id']}"):
                                conn.execute("DELETE FROM product_images WHERE id=?", (img_row["id"],))
                                conn.commit(); st.rerun()


    # ── NOUVEAU PRODUIT ────────────────────────────────────────────────────────
    if tab_new is not None:
        with tab_new:
            st.markdown(f'<div class="section-title">Nouveau produit</div>', unsafe_allow_html=True)
            nc1,nc2,nc3 = st.columns(3)
            with nc1:
                n_ref   = st.text_input("SKU *", placeholder="EWSJACKET-001A")
                n_iref  = st.text_input("Réf. interne")
                n_nom   = st.text_input("Nom *")
                n_var   = st.text_input("Variant", placeholder="Chocolate Whipcord")
            with nc2:
                # Collection avec création inline
                coll_new_opts = COLLECTIONS_DYN + ["➕ Nouvelle collection..."]
                n_coll_sel = st.selectbox("Collection", coll_new_opts)
                if n_coll_sel == "➕ Nouvelle collection...":
                    n_coll = st.text_input("Nom de la nouvelle collection", placeholder="Chapter N°III — ...")
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
                        file_name=f"order_sheet_eastwood_AW26.pdf", mime="application/pdf",
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
                ft_opts = {f"{r['ref']} — {r['nom']} / {r.get('variant','')}": r["id"]
                           for _, r in df_exp_preview.iterrows()}
                sel_ft2 = st.selectbox("Produit", list(ft_opts.keys()), key="exp_ft_sel",
                                       label_visibility="collapsed")
                if st.button("📐 Générer Fiche Technique", key="gen_ft2"):
                    with st.spinner("Génération fiche..."):
                        pdf_b, err = generate_fiche_technique(conn, ft_opts[sel_ft2])
                    if err: st.error(f"Erreur : {err}")
                    elif pdf_b:
                        ref_slug = sel_ft2.split(" — ")[0].replace("/","_")
                        st.download_button("⬇ Télécharger Fiche", pdf_b,
                            file_name=f"fiche_{ref_slug}.pdf", mime="application/pdf",
                            key="dl_ft2")

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
            new_coll_name = st.text_input("Nom", placeholder="Chapter N°III — ...", key="cp_new_coll")
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
    DEVISES_COUT = ["EUR","JPY","USD","GBP","CNY"]

    with st.form(f"costs_finance_{sel_pid}"):
        all_inputs = {}
        for sect, fields in COST_SECTIONS.items():
            st.markdown(f'<div class="section-title">{sect}</div>', unsafe_allow_html=True)
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
