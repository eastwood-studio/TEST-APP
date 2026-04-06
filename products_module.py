# ══════════════════════════════════════════════════════════════════════════════
# MODULE PRODUITS v2
# Chapter I & II · 13 produits · catégories MP · MOQ · packaging · auto-sync
# ══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import sqlite3
import pandas as pd
import io
import base64
from datetime import date

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, Image as RLImage, HRFlowable,
                                    KeepTogether)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# ── Constantes ─────────────────────────────────────────────────────────────────
COLLECTIONS = [
    "Chapter N°II Souvenir",
    "Chapter N°I",
    "Archive",
]
STATUTS_PROD = ["Concept", "Développement", "Production", "Disponible", "Soldé", "Archive"]
CATEGORIES_PROD = ["Jacket", "Shirt", "Trouser", "Knitwear", "Accessory", "Other"]

# Catégories de composants (interface matières)
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

EW_VIOLET = "#7b506f"
EW_GREEN  = "#395f30"
EW_BROWN  = "#8a7968"
EW_BEIGE  = "#d9c8ae"
EW_SAND   = "#ede3d3"
EW_CREAM  = "#f5f0e8"


# ── Catalogue Chapter II — 13 produits ────────────────────────────────────────
PRODUCTS_SEED = [
    {
        "ref": "EWSJACKET-001A-CHO", "internal_ref": "EWSJACKET-001A",
        "nom": "Waterfowl Jacket", "variant": "Chocolate Whipcord",
        "categorie": "Jacket", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 134.02,
        "description": "Heavy-duty whipcord jacket inspired by vintage hunting garments. Features structured silhouette, reinforced construction and functional pockets. Designed as a durable everyday outerwear piece blending heritage and modern tailoring.",
        "matieres": "Whipcord cotton, heavy-duty fabric",
        "couleurs": "Chocolate", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSJACKET-001B-TOB", "internal_ref": "EWSJACKET-001B",
        "nom": "Waterfowl Jacket", "variant": "Tobacco Whipcord",
        "categorie": "Jacket", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 134.02,
        "description": "Structured whipcord jacket inspired by outdoor garments. Combines durability and refined cut with functional design and utilitarian pockets.",
        "matieres": "Whipcord cotton",
        "couleurs": "Tobacco", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSJACKET-001C-GRE", "internal_ref": "EWSJACKET-001C",
        "nom": "Waterfowl Jacket", "variant": "Greige Whipcord",
        "categorie": "Jacket", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 134.02,
        "description": "Heavy whipcord jacket with neutral greige tone. Inspired by archival field jackets with modern reinterpretation.",
        "matieres": "Whipcord cotton",
        "couleurs": "Greige", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSJACKET-001D-SND", "internal_ref": "EWSJACKET-001D",
        "nom": "Waterfowl Jacket", "variant": "Heavy Sand",
        "categorie": "Jacket", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 34.02,  # À vérifier
        "description": "Lightweight version of the Waterfowl jacket in sand tone. Maintains the silhouette with a softer structure.",
        "matieres": "Cotton blend",
        "couleurs": "Sand", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSJACKET-002A", "internal_ref": "EWSJACKET-002A",
        "nom": "Miura Jacket", "variant": "Standard",
        "categorie": "Jacket", "collection": "Chapter N°II Souvenir",
        "statut": "Développement", "cost_eur": 0,
        "description": "Technical-inspired jacket blending Japanese references and contemporary tailoring. Clean structure with functional details.",
        "matieres": "Technical fabric (to confirm)",
        "couleurs": "À compléter", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSJACKET-003A", "internal_ref": "EWSJACKET-003A",
        "nom": "Akagi Jacket", "variant": "Standard",
        "categorie": "Jacket", "collection": "Chapter N°II Souvenir",
        "statut": "Développement", "cost_eur": 0,
        "description": "Minimalist jacket influenced by Japanese aesthetics. Emphasis on structure, balance and material texture.",
        "matieres": "À compléter",
        "couleurs": "À compléter", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSSHIRT-001A-CBL", "internal_ref": "EWSSHIRT-001A",
        "nom": "Research Club Shirt", "variant": "Cloud Blue",
        "categorie": "Shirt", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 0,
        "description": "Lightweight shirt inspired by academic uniforms and vintage research garments. Relaxed fit with subtle detailing.",
        "matieres": "Cotton",
        "couleurs": "Cloud Blue", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSSHIRT-001B-PGR", "internal_ref": "EWSSHIRT-001B",
        "nom": "Research Club Shirt", "variant": "Pastel Green",
        "categorie": "Shirt", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 0,
        "description": "Soft-toned variation of the Research Club Shirt. Combines casual elegance with functional design.",
        "matieres": "Cotton",
        "couleurs": "Pastel Green", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSSHIRT-002A", "internal_ref": "EWSSHIRT-002A",
        "nom": "Lutèce Plage Shirt", "variant": "Standard",
        "categorie": "Shirt", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 0,
        "description": "Summer shirt inspired by Parisian seaside nostalgia. Light, breathable and relaxed silhouette.",
        "matieres": "Lightweight cotton",
        "couleurs": "À compléter", "tailles": "S, M, L, XL",
    },
    {
        "ref": "EWSACC-001A", "internal_ref": "EWSACC-001A",
        "nom": "Memory Wallet", "variant": "Standard",
        "categorie": "Accessory", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 0,
        "description": "Compact wallet designed with a minimalist approach. Focus on durability and everyday usability.",
        "matieres": "Leather (to confirm)",
        "couleurs": "À compléter", "tailles": "—",
    },
    {
        "ref": "EWSACC-002A", "internal_ref": "EWSACC-002A",
        "nom": "Souvenir Cap", "variant": "Version 1",
        "categorie": "Accessory", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 0,
        "description": "Classic cap featuring embroidered branding. Inspired by vintage souvenir items.",
        "matieres": "Cotton",
        "couleurs": "À compléter", "tailles": "One size",
    },
    {
        "ref": "EWSACC-002B", "internal_ref": "EWSACC-002B",
        "nom": "Souvenir Cap", "variant": "Version 2",
        "categorie": "Accessory", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 0,
        "description": "Alternative version of the Souvenir Cap with variation in embroidery and tone.",
        "matieres": "Cotton",
        "couleurs": "À compléter", "tailles": "One size",
    },
    {
        "ref": "EWSACC-003A", "internal_ref": "EWSACC-003A",
        "nom": "Paris Le Trésor Scarf", "variant": "Standard",
        "categorie": "Accessory", "collection": "Chapter N°II Souvenir",
        "statut": "Disponible", "cost_eur": 0,
        "description": "Artistic scarf inspired by Parisian heritage and symbolic elements. Designed as both accessory and collectible piece.",
        "matieres": "Silk (to confirm)",
        "couleurs": "Multicolor", "tailles": "One size",
    },
]


def init_products_db(conn):
    c = conn.cursor()

    # Table produits enrichie
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
        prix_retail_eur REAL DEFAULT 0,
        prix_retail_jpy REAL DEFAULT 0,
        prix_wholesale_fr REAL DEFAULT 0,
        prix_wholesale_monde REAL DEFAULT 0,
        prix_ff REAL DEFAULT 0,
        cost_eur REAL DEFAULT 0,
        a_verifier INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Migration silencieuse colonnes manquantes
    existing_cols = [r[1] for r in c.execute("PRAGMA table_info(products)").fetchall()]
    for col, defn in [
        ("internal_ref",       "TEXT"),
        ("variant",            "TEXT"),
        ("categorie",          "TEXT"),
        ("cost_eur",           "REAL DEFAULT 0"),
        ("a_verifier",         "INTEGER DEFAULT 0"),
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

    # Composants enrichis avec catégorie MP et MOQ
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

    # Migration composants
    existing_comp = [r[1] for r in c.execute("PRAGMA table_info(product_components)").fetchall()]
    for col, defn in [
        ("categorie_comp", "TEXT DEFAULT 'MP Principale (Main Fabric)'"),
        ("nom_exact",      "TEXT"),
        ("moq",            "REAL DEFAULT 0"),
        ("moq_unite",      "TEXT DEFAULT 'Mètre'"),
        ("fournisseur",    "TEXT"),
        ("notes",          "TEXT"),
    ]:
        if col not in existing_comp:
            try: c.execute(f"ALTER TABLE product_components ADD COLUMN {col} {defn}")
            except Exception: pass

    c.execute("""CREATE TABLE IF NOT EXISTS product_archives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        annee INTEGER,
        type_archive TEXT,
        matiere TEXT,
        nom_archive TEXT,
        lieu TEXT,
        details TEXT,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")

    # Table coûts enrichie : MP1/2/3 sample, Compo1/2/3 sample, packaging section
    c.execute("""CREATE TABLE IF NOT EXISTS product_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER UNIQUE,
        cout_patronage REAL DEFAULT 0,
        cout_gradation REAL DEFAULT 0,
        cout_assemblage REAL DEFAULT 0,
        cout_production REAL DEFAULT 0,
        cout_mp1_sample REAL DEFAULT 0,
        cout_mp2_sample REAL DEFAULT 0,
        cout_mp3_sample REAL DEFAULT 0,
        cout_compo1_sample REAL DEFAULT 0,
        cout_compo2_sample REAL DEFAULT 0,
        cout_compo3_sample REAL DEFAULT 0,
        cout_log_sample REAL DEFAULT 0,
        cout_mp_principale REAL DEFAULT 0,
        cout_mp_secondaire REAL DEFAULT 0,
        cout_lining REAL DEFAULT 0,
        cout_zip REAL DEFAULT 0,
        cout_boutons REAL DEFAULT 0,
        cout_broderie_principale REAL DEFAULT 0,
        cout_broderie_secondaire REAL DEFAULT 0,
        cout_patch REAL DEFAULT 0,
        cout_print REAL DEFAULT 0,
        cout_etiq_textile REAL DEFAULT 0,
        cout_etiq_taille REAL DEFAULT 0,
        cout_etiq_compo REAL DEFAULT 0,
        cout_etiq_fab_fr REAL DEFAULT 0,
        cout_tag_numero REAL DEFAULT 0,
        cout_montage REAL DEFAULT 0,
        cout_coupe REAL DEFAULT 0,
        cout_finition REAL DEFAULT 0,
        cout_stockage REAL DEFAULT 0,
        cout_emballage REAL DEFAULT 0,
        cout_appro REAL DEFAULT 0,
        cout_douane REAL DEFAULT 0,
        cout_boite REAL DEFAULT 0,
        cout_sac REAL DEFAULT 0,
        cout_feuille_expl REAL DEFAULT 0,
        cout_lettre REAL DEFAULT 0,
        cout_enveloppe REAL DEFAULT 0,
        cout_stickers REAL DEFAULT 0,
        cout_marketing REAL DEFAULT 0,
        prix_vente_cible REAL DEFAULT 0,
        prix_vente_normalise REAL DEFAULT 0,
        prix_reco_wholesale REAL DEFAULT 0,
        prix_wholesale_japan REAL DEFAULT 0,
        prix_rdm REAL DEFAULT 0,
        srp_eu REAL DEFAULT 0,
        srp_jpn REAL DEFAULT 0,
        srp_rdm REAL DEFAULT 0,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")

    # Seed produits si vide
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        for p in PRODUCTS_SEED:
            c.execute("""INSERT OR IGNORE INTO products
                (ref, internal_ref, nom, variant, categorie, collection, statut,
                 description, matieres, couleurs, tailles, cost_eur)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (p["ref"], p["internal_ref"], p["nom"], p["variant"],
                 p["categorie"], p["collection"], p["statut"],
                 p["description"], p["matieres"], p["couleurs"],
                 p["tailles"], p["cost_eur"]))
        conn.commit()


def get_products(conn, collection=None, statut=None, categorie=None):
    q = "SELECT * FROM products WHERE 1=1"
    p = []
    if collection: q += " AND collection=?"; p.append(collection)
    if statut:     q += " AND statut=?";     p.append(statut)
    if categorie:  q += " AND categorie=?";  p.append(categorie)
    return pd.read_sql(q + " ORDER BY collection, categorie, nom", conn, params=p)


def get_product(conn, pid):
    return pd.read_sql("SELECT * FROM products WHERE id=?", conn, params=[pid])


def get_images(conn, pid):
    return pd.read_sql("SELECT * FROM product_images WHERE product_id=? ORDER BY ordre",
                       conn, params=[pid])


def get_components(conn, pid):
    return pd.read_sql(
        "SELECT * FROM product_components WHERE product_id=? ORDER BY categorie_comp, id",
        conn, params=[pid])


def get_archives(conn, pid):
    return pd.read_sql("SELECT * FROM product_archives WHERE product_id=?",
                       conn, params=[pid])


def get_costs(conn, pid):
    df = pd.read_sql("SELECT * FROM product_costs WHERE product_id=?", conn, params=[pid])
    return df.iloc[0] if not df.empty else None


def fmt_eur(v):
    if v is None or (isinstance(v, float) and v == 0): return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


def fmt_jpy(v):
    if v is None or v == 0: return "—"
    return f"¥ {float(v):,.0f}"


# ── Auto-sync commande → stock → opérations ──────────────────────────────────
def sync_from_commande(conn, ref_article, qte, client_nom, client_prenom,
                       client_email, client_tel, client_adresse, prix_ttc,
                       plateforme, num_commande):
    """
    Quand une commande est enregistrée :
    1. Diminue le stock produit fini
    2. Diminue le stock des MP selon la nomenclature produit
    3. Crée automatiquement le contact client si non existant
    4. Crée une transaction de vente
    """
    try:
        # 1. Diminuer stock produit fini
        conn.execute("""UPDATE stock SET
            qte_vendue = qte_vendue + ?,
            qte_stock  = MAX(0, qte_stock - ?)
            WHERE ref=?""", (qte, qte, ref_article))

        # 2. Diminuer stock MP selon nomenclature
        prod = conn.execute(
            "SELECT id FROM products WHERE ref=?", (ref_article,)).fetchone()
        if prod:
            comps = conn.execute(
                "SELECT ref_stock, quantite FROM product_components WHERE product_id=?",
                (prod[0],)).fetchall()
            for ref_mp, qte_mp in comps:
                if ref_mp:
                    needed = float(qte_mp) * float(qte)
                    conn.execute("""UPDATE stock SET
                        qte_utilisee = qte_utilisee + ?,
                        qte_stock    = MAX(0, qte_stock - ?)
                        WHERE ref=?""", (needed, needed, ref_mp))

        # 3. Créer contact client si email non existant
        if client_email:
            existing = conn.execute(
                "SELECT id FROM contacts WHERE email=?", (client_email,)).fetchone()
            if not existing:
                nom_complet = f"{client_prenom} {client_nom}".strip()
                conn.execute("""INSERT INTO contacts
                    (type_contact, sous_type, nom, email, telephone,
                     adresse, importance, notes)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    ("Client", "Ponctuel", nom_complet, client_email,
                     client_tel, client_adresse, "Normal",
                     f"Client depuis commande {num_commande} via {plateforme}"))

        # 4. Transaction de vente automatique
        from datetime import date as dt_date
        today = dt_date.today()
        conn.execute("""INSERT INTO transactions
            (annee,mois,date_op,ref_produit,info_process,description,
             categorie,type_op,quantite,unite,prix_unitaire,type_tva,
             total_ht,total_ttc,tva,devise,taux_change,montant_original,
             payeur,beneficiaire,source,info_complementaire)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (today.year, today.month, str(today),
             ref_article, "Vente produit", f"Commande {num_commande} — {client_prenom} {client_nom}",
             "Facture", "Vente", qte, "Article",
             round(prix_ttc / 1.2 / qte, 2) if qte > 0 else 0,
             "Collectée",
             round(prix_ttc / 1.2, 2), prix_ttc,
             round(prix_ttc - prix_ttc / 1.2, 2),
             "EUR", 1.0, round(prix_ttc / 1.2, 2),
             f"{client_prenom} {client_nom}", "Eastwood Studio",
             plateforme, f"N°{num_commande}"))

        conn.commit()
    except Exception as e:
        pass  # Sync silencieuse — ne bloque pas la commande


# ── LINE SHEET PDF amélioré ────────────────────────────────────────────────────
def generate_linesheet(conn, collection_filter=None):
    if not REPORTLAB_OK:
        return None, "reportlab non installé"

    buf = io.BytesIO()
    W, H = A4
    M = 12 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=M, rightMargin=M,
                            topMargin=M, bottomMargin=10*mm)

    # ── Styles Eastwood ────────────────────────────────────────────────────────
    EW_V = colors.HexColor("#7b506f")
    EW_B = colors.HexColor("#8a7968")
    EW_S = colors.HexColor("#ede3d3")
    EW_K = colors.HexColor("#1a1a1a")
    EW_C = colors.HexColor("#f5f0e8")

    s_brand = ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=18,
                              textColor=EW_K, letterSpacing=5,
                              spaceAfter=2, alignment=TA_CENTER)
    s_sub   = ParagraphStyle("sub",   fontName="Helvetica", fontSize=7,
                              textColor=EW_B, letterSpacing=8,
                              spaceAfter=8, alignment=TA_CENTER)
    s_coll  = ParagraphStyle("coll",  fontName="Helvetica-Bold", fontSize=8,
                              textColor=EW_V, letterSpacing=3,
                              spaceBefore=10, spaceAfter=4)
    s_ref   = ParagraphStyle("ref",   fontName="Helvetica", fontSize=6.5,
                              textColor=EW_B, spaceAfter=1)
    s_nom   = ParagraphStyle("nom",   fontName="Helvetica-Bold", fontSize=9,
                              textColor=EW_K, spaceAfter=2)
    s_var   = ParagraphStyle("var",   fontName="Helvetica-Oblique", fontSize=7.5,
                              textColor=EW_B, spaceAfter=3)
    s_desc  = ParagraphStyle("desc",  fontName="Helvetica", fontSize=7,
                              textColor=EW_B, spaceAfter=3, leading=10)
    s_price = ParagraphStyle("price", fontName="Helvetica-Bold", fontSize=7.5,
                              textColor=EW_K)
    s_small = ParagraphStyle("small", fontName="Helvetica", fontSize=6.5,
                              textColor=EW_B)
    s_foot  = ParagraphStyle("foot",  fontName="Helvetica", fontSize=6,
                              textColor=EW_B, alignment=TA_CENTER)

    story = []

    # ── En-tête ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("EASTWOOD STUDIO", s_brand))
    story.append(Paragraph("PARIS · LINE SHEET · S/S 2026", s_sub))

    hr_style = TableStyle([
        ("LINEABOVE", (0,0), (-1,0), 0.8, EW_K),
        ("LINEBELOW", (0,0), (-1,0), 0.3, EW_S),
    ])

    story.append(HRFlowable(width="100%", thickness=0.8, color=EW_K))
    story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S, spaceAfter=6))

    # ── Info sheet ─────────────────────────────────────────────────────────────
    info_data = [[
        Paragraph(f"Date : {date.today().strftime('%B %Y')}", s_small),
        Paragraph("Confidential — For trade use only", s_small),
        Paragraph("eastwood-studio.fr", s_small),
    ]]
    info_tbl = Table(info_data, colWidths=[(W-2*M)/3]*3)
    info_tbl.setStyle(TableStyle([
        ("ALIGN",  (0,0), (0,-1), "LEFT"),
        ("ALIGN",  (1,0), (1,-1), "CENTER"),
        ("ALIGN",  (2,0), (2,-1), "RIGHT"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 4*mm))

    # ── Produits ───────────────────────────────────────────────────────────────
    q = "SELECT * FROM products WHERE 1=1"
    params = []
    if collection_filter:
        q += " AND collection=?"; params.append(collection_filter)
    df_prods = pd.read_sql(q + " ORDER BY collection, categorie, nom", conn, params=params)

    if df_prods.empty:
        story.append(Paragraph("Aucun produit.", s_desc))
        doc.build(story)
        return buf.getvalue(), None

    IMG_W = 68*mm
    IMG_H = 85*mm
    COL_W = (W - 2*M - 6*mm) / 2

    for coll_name, grp in df_prods.groupby("collection", sort=False):
        story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S))
        story.append(Paragraph(coll_name.upper(), s_coll))
        story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S, spaceAfter=4))

        prods = list(grp.iterrows())
        for i in range(0, len(prods), 2):
            row_cells = []
            for j in range(2):
                if i + j >= len(prods):
                    row_cells.append("")
                    continue

                _, prod = prods[i + j]
                cell = []

                # Image
                imgs = pd.read_sql(
                    "SELECT data FROM product_images WHERE product_id=? ORDER BY ordre LIMIT 1",
                    conn, params=[prod["id"]])
                if not imgs.empty and imgs.iloc[0]["data"] is not None:
                    try:
                        img_io = io.BytesIO(bytes(imgs.iloc[0]["data"]))
                        rl_img = RLImage(img_io, width=IMG_W, height=IMG_H,
                                         kind="proportional")
                        rl_img.hAlign = "LEFT"
                        cell.append(rl_img)
                    except Exception:
                        placeholder = Table([[""]], colWidths=[IMG_W], rowHeights=[IMG_H])
                        placeholder.setStyle(TableStyle([
                            ("BACKGROUND", (0,0), (-1,-1), EW_C),
                            ("BOX", (0,0), (-1,-1), 0.3, EW_S),
                        ]))
                        cell.append(placeholder)
                else:
                    placeholder = Table([[""]], colWidths=[IMG_W], rowHeights=[IMG_H])
                    placeholder.setStyle(TableStyle([
                        ("BACKGROUND", (0,0), (-1,-1), EW_C),
                        ("BOX", (0,0), (-1,-1), 0.3, EW_S),
                    ]))
                    cell.append(placeholder)

                cell.append(Spacer(1, 2*mm))

                # Infos produit
                ref_str = prod.get("ref","")
                if prod.get("internal_ref"):
                    ref_str += f"  ·  {prod['internal_ref']}"
                cell.append(Paragraph(ref_str, s_ref))
                cell.append(Paragraph(str(prod["nom"]), s_nom))
                if prod.get("variant"):
                    cell.append(Paragraph(str(prod["variant"]), s_var))

                if prod.get("description"):
                    desc = str(prod["description"])[:130]
                    if len(str(prod["description"])) > 130: desc += "..."
                    cell.append(Paragraph(desc, s_desc))

                # Matières & tailles
                details = []
                if prod.get("matieres"):
                    details.append(f"Materials : {prod['matieres']}")
                if prod.get("tailles"):
                    details.append(f"Sizes : {prod['tailles']}")
                for d in details:
                    cell.append(Paragraph(d, s_small))

                cell.append(Spacer(1, 2*mm))

                # Prix — grille propre
                price_rows = []
                if prod.get("prix_retail_eur"):
                    price_rows.append(["Retail (FR)", fmt_eur(prod["prix_retail_eur"])])
                if prod.get("prix_retail_jpy"):
                    price_rows.append(["Retail (JP)", fmt_jpy(prod["prix_retail_jpy"])])
                if prod.get("prix_wholesale_fr"):
                    price_rows.append(["Wholesale", fmt_eur(prod["prix_wholesale_fr"])])
                if prod.get("cost_eur") and float(prod.get("cost_eur",0) or 0) > 0:
                    cost_str = fmt_eur(prod["cost_eur"])
                    if prod.get("a_verifier"): cost_str += " ⚠"
                    price_rows.append(["Cost", cost_str])

                if price_rows:
                    price_tbl = Table(
                        [[Paragraph(r[0], s_small), Paragraph(r[1], s_price)]
                         for r in price_rows],
                        colWidths=[IMG_W * 0.45, IMG_W * 0.55]
                    )
                    price_tbl.setStyle(TableStyle([
                        ("ALIGN",          (1,0), (1,-1), "RIGHT"),
                        ("TOPPADDING",     (0,0), (-1,-1), 1),
                        ("BOTTOMPADDING",  (0,0), (-1,-1), 1),
                        ("LINEBELOW",      (0,-1), (-1,-1), 0.3, EW_S),
                    ]))
                    cell.append(price_tbl)

                row_cells.append(cell)

            tbl = Table([row_cells], colWidths=[COL_W, COL_W])
            tbl.setStyle(TableStyle([
                ("VALIGN",         (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING",    (0,0), (-1,-1), 3*mm),
                ("RIGHTPADDING",   (0,0), (-1,-1), 3*mm),
                ("BOTTOMPADDING",  (0,0), (-1,-1), 6*mm),
                ("TOPPADDING",     (0,0), (-1,-1), 2*mm),
                ("LINEBEFORE",     (1,0), (1,-1), 0.3, EW_S),
            ]))
            story.append(KeepTogether(tbl))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.3, color=EW_S))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"EASTWOOD STUDIO  ·  Paris, France  ·  eastwood-studio.fr  ·  "
        f"Generated {date.today().strftime('%d %B %Y')}  ·  "
        f"Confidential — Not for distribution",
        s_foot))

    doc.build(story)
    return buf.getvalue(), None


# ── Section coûts ──────────────────────────────────────────────────────────────
COST_SECTIONS = {
    "Développement sample": [
        ("cout_patronage",    "Patronage"),
        ("cout_gradation",    "Gradation"),
        ("cout_assemblage",   "Assemblage"),
        ("cout_production",   "Production"),
        ("cout_mp1_sample",   "MP 1 — sample"),
        ("cout_mp2_sample",   "MP 2 — sample"),
        ("cout_mp3_sample",   "MP 3 — sample"),
        ("cout_compo1_sample","Composant 1 — sample"),
        ("cout_compo2_sample","Composant 2 — sample"),
        ("cout_compo3_sample","Composant 3 — sample"),
        ("cout_log_sample",   "Logistique sample"),
    ],
    "MP & Composants": [
        ("cout_mp_principale",      "MP Principale (Main Fabric)"),
        ("cout_mp_secondaire",      "MP Secondaire"),
        ("cout_lining",             "Doublure (Lining)"),
        ("cout_zip",                "Zips"),
        ("cout_boutons",            "Boutons"),
        ("cout_broderie_principale","Broderie principale"),
        ("cout_broderie_secondaire","Broderie secondaire"),
        ("cout_patch",              "Patchs"),
        ("cout_print",              "Prints / Sérigraphie"),
    ],
    "Étiquettes": [
        ("cout_etiq_textile", "Étiquette textile"),
        ("cout_etiq_taille",  "Étiquette taille"),
        ("cout_etiq_compo",   "Étiquette composition"),
        ("cout_etiq_fab_fr",  "Étiquette 'Confection française'"),
        ("cout_tag_numero",   "Tag numéro + détails"),
    ],
    "Production & Réalisation": [
        ("cout_montage",  "Montage"),
        ("cout_coupe",    "Coupe"),
        ("cout_finition", "Finition"),
    ],
    "Logistique": [
        ("cout_stockage",  "Stockage"),
        ("cout_emballage", "Emballage / Préparation"),
        ("cout_appro",     "Approvisionnement"),
        ("cout_douane",    "Douane"),
    ],
    "Packaging & Accessoires produit": [
        ("cout_boite",       "Boîte"),
        ("cout_sac",         "Sac"),
        ("cout_feuille_expl","Feuille explicative"),
        ("cout_lettre",      "Lettre postale"),
        ("cout_enveloppe",   "Enveloppe"),
        ("cout_stickers",    "Stickers"),
    ],
    "Marketing": [
        ("cout_marketing", "Marketing"),
    ],
}

SECTION_TOTALS = {k: [f[0] for f in v] for k, v in COST_SECTIONS.items()}


def compute_cost_totals(row_dict):
    totals = {}
    grand = 0.0
    for section, keys in SECTION_TOTALS.items():
        t = sum(float(row_dict.get(k, 0) or 0) for k in keys)
        totals[section] = t
        grand += t
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
    if can_fn("stock_write"):
        _tabs.append("➕ Nouveau produit")
    _tabs.append("📄 Line Sheet")
    if can_fn("finance_write"):
        _tabs.append("💰 Coûts production")

    tab_objs = st.tabs(_tabs)
    idx = 0
    tab_cat  = tab_objs[idx]; idx += 1
    tab_new  = tab_objs[idx] if can_fn("stock_write") else None
    if can_fn("stock_write"): idx += 1
    tab_ls   = tab_objs[idx]; idx += 1
    tab_costs = tab_objs[idx] if can_fn("finance_write") else None

    # ── CATALOGUE ──────────────────────────────────────────────────────────────
    with tab_cat:
        c1, c2, c3 = st.columns(3)
        with c1:
            f_coll = st.selectbox("Collection", ["Toutes"] + COLLECTIONS, key="pcat_coll")
        with c2:
            f_stat = st.selectbox("Statut", ["Tous"] + STATUTS_PROD, key="pcat_stat")
        with c3:
            f_cat_p = st.selectbox("Catégorie", ["Toutes"] + CATEGORIES_PROD, key="pcat_cat")

        df_prods = get_products(
            conn,
            collection=None if f_coll == "Toutes" else f_coll,
            statut=None if f_stat == "Tous" else f_stat,
            categorie=None if f_cat_p == "Toutes" else f_cat_p,
        )

        if df_prods.empty:
            st.info("Aucun produit dans cette sélection.")
        else:
            for coll_name, grp in df_prods.groupby("collection", sort=False):
                st.markdown(
                    f'<div class="section-title">{coll_name}</div>',
                    unsafe_allow_html=True)
                cols = st.columns(4)
                for i, (_, prod) in enumerate(grp.iterrows()):
                    with cols[i % 4]:
                        imgs = get_images(conn, prod["id"])
                        if not imgs.empty and imgs.iloc[0]["data"] is not None:
                            try:
                                b64 = base64.b64encode(bytes(imgs.iloc[0]["data"])).decode()
                                ext = (imgs.iloc[0]["nom_fichier"] or "img.jpg").split(".")[-1].lower()
                                mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                                st.markdown(f"""
<div style="aspect-ratio:3/4;background:{EW_CREAM};overflow:hidden;margin-bottom:6px;">
  <img src="data:{mime};base64,{b64}" style="width:100%;height:100%;object-fit:cover;"/>
</div>""", unsafe_allow_html=True)
                            except Exception:
                                st.markdown(f'<div style="aspect-ratio:3/4;background:{EW_CREAM};display:flex;align-items:center;justify-content:center;margin-bottom:6px;"><span style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_BROWN};">VISUEL</span></div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="aspect-ratio:3/4;background:{EW_CREAM};display:flex;align-items:center;justify-content:center;margin-bottom:6px;"><span style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_BROWN};">VISUEL</span></div>', unsafe_allow_html=True)

                        stat_c = {
                            "Disponible":"#395f30","Développement":"#c9800a",
                            "Production":"#7b506f","Concept":"#888",
                            "Soldé":"#c1440e","Archive":"#555"
                        }.get(prod.get("statut",""),"#888")
                        av = " ⚠" if prod.get("a_verifier") else ""
                        st.markdown(f"""
<div style="margin-bottom:10px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_BROWN};">{prod.get('ref','')}</div>
  <div style="font-size:13px;font-weight:500;color:#1a1a1a;margin:1px 0;">{prod['nom']}</div>
  {f'<div style="font-size:11px;color:{EW_BROWN};font-style:italic;">{prod["variant"]}</div>' if prod.get("variant") else ''}
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{stat_c};">● {prod.get('statut','')}</div>
  {f'<div style="font-family:\'DM Mono\',monospace;font-size:11px;color:#1a1a1a;margin-top:3px;">{fmt_eur_fn(prod["prix_retail_eur"])}{av}</div>' if prod.get("prix_retail_eur") else ''}
</div>""", unsafe_allow_html=True)

                        if st.button("Voir →", key=f"voir_{prod['id']}"):
                            st.session_state["product_view"] = prod["id"]
                            st.rerun()

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
                            b64 = base64.b64encode(bytes(row_img["data"])).decode()
                            ext = (row_img["nom_fichier"] or "img.jpg").split(".")[-1].lower()
                            mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                            st.markdown(f'<div style="background:{EW_CREAM};overflow:hidden;"><img src="data:{mime};base64,{b64}" style="width:100%;object-fit:contain;max-height:300px;"/></div>', unsafe_allow_html=True)
                        except Exception: pass

                    if len(imgs) > 1:
                        nc1, nc2 = st.columns(2)
                        with nc1:
                            if st.button("‹", key=f"prev_{pid}") and img_idx > 0:
                                st.session_state[f"img_idx_{pid}"] = img_idx - 1; st.rerun()
                        with nc2:
                            if st.button("›", key=f"next_{pid}") and img_idx < len(imgs)-1:
                                st.session_state[f"img_idx_{pid}"] = img_idx + 1; st.rerun()
                else:
                    st.markdown(f'<div style="aspect-ratio:3/4;background:{EW_CREAM};display:flex;align-items:center;justify-content:center;"><span style="font-family:\'DM Mono\',monospace;font-size:9px;color:{EW_BROWN};">AUCUN VISUEL</span></div>', unsafe_allow_html=True)

                if can_fn("stock_write"):
                    new_imgs = st.file_uploader("Ajouter visuels",
                        accept_multiple_files=True, type=["png","jpg","jpeg","webp"],
                        key=f"img_up_{pid}")
                    if new_imgs and st.button("✓ Upload", key=f"img_save_{pid}"):
                        for k, f in enumerate(new_imgs):
                            conn.execute("""INSERT INTO product_images
                                (product_id,nom_fichier,data,ordre) VALUES (?,?,?,?)""",
                                (pid, f.name, f.read(), len(imgs) + k))
                        conn.commit()
                        st.success(f"✓ {len(new_imgs)} visuel(s) ajouté(s)."); st.rerun()

            with hc2:
                av_badge = ' <span style="background:#fdf6ec;color:#c9800a;font-family:\'DM Mono\',monospace;font-size:9px;padding:2px 6px;">⚠ COÛT À VÉRIFIER</span>' if prod.get("a_verifier") else ""
                st.markdown(f"""
<div style="margin-bottom:14px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_BROWN};letter-spacing:.12em;">
    {prod.get('ref','')} · {prod.get('collection','')}
  </div>
  <div style="font-size:22px;font-weight:500;color:#1a1a1a;margin:4px 0 2px;">
    {prod['nom']}{f' <span style="font-size:16px;font-style:italic;color:{EW_BROWN};">{prod["variant"]}</span>' if prod.get("variant") else ''}
  </div>
  {av_badge}
</div>""", unsafe_allow_html=True)

                if can_fn("stock_write"):
                    with st.form(f"edit_prod_{pid}"):
                        ep1, ep2 = st.columns(2)
                        with ep1:
                            e_nom  = st.text_input("Nom", value=prod.get("nom",""))
                            e_var  = st.text_input("Variant", value=prod.get("variant","") or "")
                            e_ref  = st.text_input("SKU", value=prod.get("ref",""))
                            e_iref = st.text_input("Réf. interne", value=prod.get("internal_ref","") or "")
                            e_coll = st.selectbox("Collection", COLLECTIONS,
                                index=COLLECTIONS.index(prod["collection"]) if prod.get("collection") in COLLECTIONS else 0)
                            e_stat = st.selectbox("Statut", STATUTS_PROD,
                                index=STATUTS_PROD.index(prod["statut"]) if prod.get("statut") in STATUTS_PROD else 0)
                            e_cat  = st.selectbox("Catégorie", CATEGORIES_PROD,
                                index=CATEGORIES_PROD.index(prod["categorie"]) if prod.get("categorie") in CATEGORIES_PROD else 0)
                        with ep2:
                            e_mat  = st.text_input("Matières", value=prod.get("matieres","") or "")
                            e_coul = st.text_input("Couleurs", value=prod.get("couleurs","") or "")
                            e_tail = st.text_input("Tailles", value=prod.get("tailles","") or "")
                            e_cost = st.number_input("Coût EUR", value=float(prod.get("cost_eur",0) or 0), min_value=0.0)
                            e_av   = st.checkbox("⚠ Coût à vérifier", value=bool(prod.get("a_verifier",0)))
                        e_desc = st.text_area("Description", value=prod.get("description","") or "", height=80)
                        pp1,pp2,pp3,pp4,pp5 = st.columns(5)
                        with pp1: e_preu = st.number_input("Retail EUR", value=float(prod.get("prix_retail_eur",0) or 0), min_value=0.0)
                        with pp2: e_prjp = st.number_input("Retail JPY", value=float(prod.get("prix_retail_jpy",0) or 0), min_value=0.0)
                        with pp3: e_pwfr = st.number_input("Wholesale FR", value=float(prod.get("prix_wholesale_fr",0) or 0), min_value=0.0)
                        with pp4: e_pwmo = st.number_input("Wholesale Monde", value=float(prod.get("prix_wholesale_monde",0) or 0), min_value=0.0)
                        with pp5: e_pff  = st.number_input("F&F", value=float(prod.get("prix_ff",0) or 0), min_value=0.0)

                        if st.form_submit_button("💾 Enregistrer"):
                            conn.execute("""UPDATE products SET
                                nom=?,variant=?,ref=?,internal_ref=?,collection=?,statut=?,categorie=?,
                                description=?,matieres=?,couleurs=?,tailles=?,cost_eur=?,a_verifier=?,
                                prix_retail_eur=?,prix_retail_jpy=?,prix_wholesale_fr=?,prix_wholesale_monde=?,prix_ff=?
                                WHERE id=?""",
                                (e_nom,e_var,e_ref,e_iref,e_coll,e_stat,e_cat,
                                 e_desc,e_mat,e_coul,e_tail,e_cost,int(e_av),
                                 e_preu,e_prjp,e_pwfr,e_pwmo,e_pff,pid))
                            conn.commit()
                            st.success("✓ Mis à jour."); st.rerun()
                else:
                    for lbl, key in [("Description","description"),("Matières","matieres"),
                                     ("Couleurs","couleurs"),("Tailles","tailles")]:
                        if prod.get(key):
                            st.write(f"**{lbl}** : {prod[key]}")
                    st.markdown(f"**Retail FR** : {fmt_eur_fn(prod.get('prix_retail_eur'))} · **Retail JP** : {fmt_jpy_fn(prod.get('prix_retail_jpy'))}")

            # Sous-onglets fiche
            st.markdown("---")
            ft1, ft2, ft3, ft4 = st.tabs(["🧵 Composition", "📚 Archives", "📦 Packaging", "🗑 Gestion"])

            with ft1:
                df_comp = get_components(conn, pid)

                if not df_comp.empty:
                    # Grouper par catégorie
                    for cat_c, grp_c in df_comp.groupby("categorie_comp", sort=False):
                        total_cat = (grp_c["quantite"] * grp_c["cout_unitaire"]).sum()
                        st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.15em;
     text-transform:uppercase;color:{EW_VIOLET};border-bottom:1px solid {EW_SAND};
     padding-bottom:4px;margin:12px 0 8px;">
  {cat_c} · {fmt_eur_fn(total_cat)}
</div>""", unsafe_allow_html=True)
                        for _, comp in grp_c.iterrows():
                            st.markdown(f"""
<div style="display:flex;justify-content:space-between;padding:4px 0;
     border-bottom:1px solid #f0ece4;font-size:12px;">
  <div>
    <span style="font-weight:500;">{comp.get('nom_exact') or comp.get('nom','')}</span>
    {f'<span style="color:{EW_BROWN};margin-left:8px;font-size:11px;">{comp["ref_stock"]}</span>' if comp.get("ref_stock") else ''}
    {f'<span style="color:{EW_BROWN};margin-left:8px;font-size:11px;">MOQ : {comp["moq"]} {comp.get("moq_unite","")}</span>' if comp.get("moq") else ''}
    {f'<span style="color:{EW_BROWN};margin-left:8px;font-size:11px;">Fournisseur : {comp["fournisseur"]}</span>' if comp.get("fournisseur") else ''}
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:#1a1a1a;white-space:nowrap;">
    {comp['quantite']} {comp['unite']} · {fmt_eur_fn(comp['cout_unitaire'])}
  </div>
</div>""", unsafe_allow_html=True)

                    total_mp = (df_comp["quantite"] * df_comp["cout_unitaire"]).sum()
                    st.markdown(f"""
<div style="font-family:'DM Mono',monospace;font-size:11px;font-weight:500;
     margin-top:12px;color:#1a1a1a;">Total composition : {fmt_eur_fn(total_mp)}</div>""",
                        unsafe_allow_html=True)
                else:
                    st.info("Aucun composant enregistré.")

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
                df_arch = get_archives(conn, pid)
                if not df_arch.empty:
                    for _, arch in df_arch.iterrows():
                        st.markdown(f"""
<div style="border-left:2px solid {EW_SAND};padding:8px 14px;margin:6px 0;">
  <div style="display:flex;gap:10px;align-items:baseline;">
    <span style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_BROWN};">{arch.get('annee','')}</span>
    <span style="font-weight:500;font-size:13px;">{arch.get('nom_archive','')}</span>
    <span style="font-size:11px;color:{EW_BROWN};">{arch.get('type_archive','')} · {arch.get('matiere','')} · {arch.get('lieu','')}</span>
  </div>
  {f'<div style="font-size:11px;color:{EW_BROWN};margin-top:3px;">{arch["details"]}</div>' if arch.get("details") else ''}
</div>""", unsafe_allow_html=True)
                else:
                    st.info("Aucune archive.")

                if can_fn("stock_write"):
                    with st.form(f"add_arch_{pid}"):
                        aa1,aa2,aa3 = st.columns(3)
                        with aa1: a_annee = st.number_input("Année", min_value=1900, max_value=2100, value=2025)
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
                st.markdown(f'<div class="section-title">Packaging & Accessoires produit</div>', unsafe_allow_html=True)
                # Filtrer les composants packaging
                df_pack = get_components(conn, pid)
                df_pack = df_pack[df_pack["categorie_comp"] == "Packaging & Accessoires produit"] if not df_pack.empty else df_pack
                if not df_pack.empty:
                    for _, p in df_pack.iterrows():
                        st.markdown(f"""
<div style="display:flex;justify-content:space-between;padding:6px 0;
     border-bottom:1px solid {EW_SAND};font-size:12px;">
  <span style="font-weight:500;">{p.get('nom_exact') or p.get('nom','')}</span>
  <span style="font-family:'DM Mono',monospace;font-size:11px;">{p['quantite']} {p['unite']} · {fmt_eur_fn(p['cout_unitaire'])}</span>
</div>""", unsafe_allow_html=True)
                else:
                    st.info("Aucun packaging enregistré. Ajoutez-en via l'onglet Composition avec la catégorie 'Packaging & Accessoires produit'.")

            with ft4:
                st.markdown(f'<div class="section-title">Gestion</div>', unsafe_allow_html=True)
                if can_fn("products_delete"):
                    st.warning("Supprimer ce produit supprime aussi images, composants et archives.")
                    if st.button("🗑 Supprimer ce produit"):
                        for tbl in ["product_images","product_components","product_archives","product_costs"]:
                            conn.execute(f"DELETE FROM {tbl} WHERE product_id=?", (pid,))
                        conn.execute("DELETE FROM products WHERE id=?", (pid,))
                        conn.commit()
                        del st.session_state["product_view"]
                        st.success("Supprimé."); st.rerun()
                else:
                    st.info("Seul Jules peut supprimer un produit.")

                if can_fn("stock_write"):
                    imgs2 = get_images(conn, pid)
                    if not imgs2.empty:
                        st.markdown("**Gérer les visuels**")
                        for _, img_row in imgs2.iterrows():
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
                n_ref  = st.text_input("SKU *", placeholder="EWSJACKET-001A-CHO")
                n_iref = st.text_input("Réf. interne", placeholder="EWSJACKET-001A")
                n_nom  = st.text_input("Nom *", placeholder="Waterfowl Jacket")
                n_var  = st.text_input("Variant", placeholder="Chocolate Whipcord")
            with nc2:
                n_coll = st.selectbox("Collection", COLLECTIONS)
                n_cat  = st.selectbox("Catégorie", CATEGORIES_PROD)
                n_stat = st.selectbox("Statut", STATUTS_PROD)
                n_cost = st.number_input("Coût EUR", min_value=0.0, value=0.0)
            with nc3:
                n_mat  = st.text_input("Matières")
                n_coul = st.text_input("Couleurs")
                n_tail = st.text_input("Tailles", placeholder="S, M, L, XL")
                n_av   = st.checkbox("⚠ Coût à vérifier")
            n_desc = st.text_area("Description", height=70)
            np1,np2,np3 = st.columns(3)
            with np1: n_preu = st.number_input("Retail EUR", min_value=0.0, value=0.0)
            with np2: n_pwfr = st.number_input("Wholesale FR", min_value=0.0, value=0.0)
            with np3: n_pff  = st.number_input("F&F", min_value=0.0, value=0.0)

            if st.button("✓ Créer le produit"):
                if not n_ref or not n_nom:
                    st.error("SKU et nom obligatoires.")
                else:
                    try:
                        conn.execute("""INSERT INTO products
                            (ref,internal_ref,nom,variant,categorie,collection,statut,
                             description,matieres,couleurs,tailles,cost_eur,a_verifier,
                             prix_retail_eur,prix_wholesale_fr,prix_ff)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (n_ref,n_iref,n_nom,n_var,n_cat,n_coll,n_stat,
                             n_desc,n_mat,n_coul,n_tail,n_cost,int(n_av),
                             n_preu,n_pwfr,n_pff))
                        conn.commit()
                        st.success(f"✓ Produit {n_ref} créé.")
                    except sqlite3.IntegrityError:
                        st.error("Ce SKU existe déjà.")

    # ── LINE SHEET ─────────────────────────────────────────────────────────────
    with tab_ls:
        st.markdown(f'<div class="section-title">Génération line sheet</div>', unsafe_allow_html=True)
        ls_coll = st.selectbox("Collection", ["Toutes"] + COLLECTIONS, key="ls_coll")
        coll_arg = None if ls_coll == "Toutes" else ls_coll

        st.markdown("""
<div class="info-box">
Format A4 · Sobre · 2 produits par ligne · Prêt showroom
</div>""", unsafe_allow_html=True)

        if st.button("📄 Générer le line sheet PDF"):
            with st.spinner("Génération en cours..."):
                pdf_bytes, err = generate_linesheet(conn, coll_arg)
            if err:
                st.error(f"Erreur : {err}")
            elif pdf_bytes:
                fname = f"linesheet_eastwood_{(ls_coll or 'all').replace(' ','_').replace('°','')}.pdf"
                st.download_button("⬇ Télécharger", pdf_bytes,
                                   file_name=fname, mime="application/pdf")
                st.success("✓ Line sheet généré !")

        # Aperçu liste
        df_ls = get_products(conn, collection=coll_arg)
        if not df_ls.empty:
            st.markdown(f'<div class="section-title">Aperçu ({len(df_ls)} produits)</div>', unsafe_allow_html=True)
            for _, p in df_ls.iterrows():
                av = " ⚠" if p.get("a_verifier") else ""
                st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
     border-bottom:1px solid {EW_SAND};padding:7px 0;">
  <div>
    <span style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_BROWN};">{p['ref']}</span>
    <span style="font-size:13px;font-weight:500;margin-left:10px;">{p['nom']}</span>
    {f'<span style="font-size:11px;color:{EW_BROWN};font-style:italic;margin-left:6px;">{p["variant"]}</span>' if p.get("variant") else ''}
    <span style="font-size:11px;color:{EW_BROWN};margin-left:8px;">{p.get('collection','')}</span>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;text-align:right;">
    {fmt_eur_fn(p.get('prix_retail_eur'))}{av}
  </div>
</div>""", unsafe_allow_html=True)

    # ── COÛTS (Jules only) ─────────────────────────────────────────────────────
    if tab_costs is not None:
        with tab_costs:
            st.markdown(f'<div class="section-title">Coûts de production — confidentiel</div>', unsafe_allow_html=True)
            df_all_p = get_products(conn)
            if df_all_p.empty:
                st.info("Aucun produit.")
            else:
                prod_opts = {f"{r['ref']} — {r['nom']}{' / '+r['variant'] if r.get('variant') else ''}": r["id"]
                             for _, r in df_all_p.iterrows()}
                sel_label = st.selectbox("Produit", list(prod_opts.keys()))
                sel_pid   = prod_opts[sel_label]

                costs_row  = get_costs(conn, sel_pid)
                costs_dict = dict(costs_row) if costs_row is not None else {}

                with st.form(f"costs_{sel_pid}"):
                    all_inputs = {}
                    for sect, fields in COST_SECTIONS.items():
                        st.markdown(f'<div class="section-title">{sect}</div>', unsafe_allow_html=True)
                        n = min(len(fields), 3)
                        cols = st.columns(n)
                        for i, (key, label) in enumerate(fields):
                            with cols[i % n]:
                                all_inputs[key] = st.number_input(
                                    label, min_value=0.0, step=0.01,
                                    value=float(costs_dict.get(key, 0) or 0),
                                    key=f"{key}_{sel_pid}")

                    st.markdown(f'<div class="section-title">Prix cibles</div>', unsafe_allow_html=True)
                    pc1,pc2,pc3,pc4 = st.columns(4)
                    with pc1: all_inputs["prix_vente_cible"]    = st.number_input("Prix vente cible",    min_value=0.0, value=float(costs_dict.get("prix_vente_cible",0) or 0))
                    with pc2: all_inputs["prix_vente_normalise"] = st.number_input("Prix normalisé",      min_value=0.0, value=float(costs_dict.get("prix_vente_normalise",0) or 0))
                    with pc3: all_inputs["prix_reco_wholesale"]  = st.number_input("Reco Wholesale",      min_value=0.0, value=float(costs_dict.get("prix_reco_wholesale",0) or 0))
                    with pc4: all_inputs["prix_wholesale_japan"] = st.number_input("Wholesale Japon",     min_value=0.0, value=float(costs_dict.get("prix_wholesale_japan",0) or 0))
                    pc5,pc6,pc7,pc8 = st.columns(4)
                    with pc5: all_inputs["prix_rdm"]  = st.number_input("Prix RDM",  min_value=0.0, value=float(costs_dict.get("prix_rdm",0) or 0))
                    with pc6: all_inputs["srp_eu"]    = st.number_input("SRP EU",    min_value=0.0, value=float(costs_dict.get("srp_eu",0) or 0))
                    with pc7: all_inputs["srp_jpn"]   = st.number_input("SRP JPN ¥", min_value=0.0, value=float(costs_dict.get("srp_jpn",0) or 0))
                    with pc8: all_inputs["srp_rdm"]   = st.number_input("SRP RDM",   min_value=0.0, value=float(costs_dict.get("srp_rdm",0) or 0))

                    if st.form_submit_button("💾 Enregistrer les coûts"):
                        all_inputs["product_id"] = sel_pid
                        cols_str = ", ".join(all_inputs.keys())
                        ph       = ", ".join(["?"] * len(all_inputs))
                        upd      = ", ".join(f"{k}=?" for k in all_inputs if k != "product_id")
                        conn.execute(
                            f"INSERT INTO product_costs ({cols_str}) VALUES ({ph}) "
                            f"ON CONFLICT(product_id) DO UPDATE SET {upd}",
                            list(all_inputs.values()) +
                            [v for k, v in all_inputs.items() if k != "product_id"])
                        conn.commit()
                        st.success("✓ Coûts enregistrés."); st.rerun()

                # Récap
                if costs_row is not None:
                    st.markdown(f'<div class="section-title">Récapitulatif</div>', unsafe_allow_html=True)
                    totals = compute_cost_totals(dict(costs_row))
                    recap_cols = st.columns(len(totals))
                    for i, (sec, val) in enumerate(totals.items()):
                        with recap_cols[i]:
                            st.metric(sec[:14], fmt_eur_fn(val))

                    pv = float(costs_dict.get("prix_vente_cible",0) or 0)
                    ct = totals["TOTAL"]
                    if pv > 0 and ct > 0:
                        marge = ((pv - ct) / pv) * 100
                        color = EW_GREEN if marge > 0 else "#c1440e"
                        st.markdown(f"""
<div style="background:#fff;border:1px solid {EW_SAND};border-left:3px solid {EW_VIOLET};
     padding:16px 20px;margin-top:12px;">
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{EW_BROWN};
              text-transform:uppercase;letter-spacing:.15em;">Estimation marge</div>
  <div style="font-family:'DM Mono',monospace;font-size:24px;font-weight:500;
              color:{color};margin:6px 0;">{marge:.1f}%</div>
  <div style="font-size:12px;color:{EW_BROWN};">
    Prix vente : {fmt_eur_fn(pv)} · Coût total : {fmt_eur_fn(ct)} · Marge brute : {fmt_eur_fn(pv - ct)}
  </div>
</div>""", unsafe_allow_html=True)

    conn.close()
