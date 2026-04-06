# ══════════════════════════════════════════════════════════════════════════════
# MODULE PRODUITS — à intégrer dans app.py
# Tables : products, product_components, product_archives, product_images, product_costs
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
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


COLLECTIONS = ["SS26 — Été 2026", "FW26 — Hiver 2026", "SS25 — Été 2025", "FW25 — Hiver 2025", "Archive"]
STATUTS_PROD = ["Concept", "Développement", "Production", "Disponible", "Soldé", "Archive"]


def init_products_db(conn):
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ref TEXT UNIQUE NOT NULL,
        nom TEXT NOT NULL,
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
        created_at TEXT DEFAULT (datetime('now'))
    )""")

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
        ref_stock TEXT,
        nom TEXT,
        quantite REAL DEFAULT 0,
        unite TEXT DEFAULT 'Pièces',
        cout_unitaire REAL DEFAULT 0,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")

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

    c.execute("""CREATE TABLE IF NOT EXISTS product_costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER UNIQUE,
        -- SAMPLE
        cout_patronage REAL DEFAULT 0,
        cout_gradation REAL DEFAULT 0,
        cout_assemblage REAL DEFAULT 0,
        cout_production REAL DEFAULT 0,
        cout_mp1_sample REAL DEFAULT 0,
        cout_mp2_sample REAL DEFAULT 0,
        cout_compo1_sample REAL DEFAULT 0,
        cout_compo2_sample REAL DEFAULT 0,
        cout_log_sample REAL DEFAULT 0,
        cout_tax_sample REAL DEFAULT 0,
        -- MP & COMPO
        cout_mp_principale REAL DEFAULT 0,
        cout_mp_secondaire REAL DEFAULT 0,
        cout_jet_encre REAL DEFAULT 0,
        cout_lining REAL DEFAULT 0,
        cout_boutons REAL DEFAULT 0,
        cout_zip REAL DEFAULT 0,
        -- ÉTIQUETTES
        cout_etiq_textile REAL DEFAULT 0,
        cout_etiq_taille REAL DEFAULT 0,
        cout_etiq_compo REAL DEFAULT 0,
        cout_etiq_fab_fr REAL DEFAULT 0,
        cout_tag_numero REAL DEFAULT 0,
        -- PROD & RÉA
        cout_montage REAL DEFAULT 0,
        cout_broderie REAL DEFAULT 0,
        cout_coupe REAL DEFAULT 0,
        cout_print REAL DEFAULT 0,
        -- LOGISTIQUE
        cout_stockage REAL DEFAULT 0,
        cout_emballage REAL DEFAULT 0,
        cout_appro REAL DEFAULT 0,
        cout_douane REAL DEFAULT 0,
        -- PACKAGING
        cout_boite REAL DEFAULT 0,
        cout_sac REAL DEFAULT 0,
        cout_feuille_expl REAL DEFAULT 0,
        cout_lettre REAL DEFAULT 0,
        cout_enveloppe REAL DEFAULT 0,
        cout_stickers REAL DEFAULT 0,
        -- MARKETING
        cout_marketing REAL DEFAULT 0,
        -- PRIX CIBLES
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

    # Seed démo
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO products
            (ref,nom,collection,statut,description,matieres,couleurs,tailles,
             prix_retail_eur,prix_retail_jpy,prix_wholesale_fr,prix_wholesale_monde,prix_ff)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("MIRA-001","Veste Miura Jacket","SS25 — Été 2025","Disponible",
             "Veste mi-saison coupe droite en tissu SOLOTEX japonais. Inspiration architecture brutaliste japonaise des années 70.",
             "SOLOTEX Japon, Doublure acétate","Noir, Ivoire","XS, S, M, L",
             420.0, 69000.0, 210.0, 230.0, 180.0))
        c.execute("""INSERT INTO products
            (ref,nom,collection,statut,description,matieres,couleurs,tailles,
             prix_retail_eur,prix_retail_jpy,prix_wholesale_fr,prix_wholesale_monde,prix_ff)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("PANT-003","Pantalon Kibo","SS25 — Été 2025","Disponible",
             "Pantalon large taille haute, coupe inspirée du workwear japonais. Tissu sergé de coton.",
             "Sergé coton 220g","Noir, Kaki","XS, S, M, L, XL",
             310.0, 51000.0, 155.0, 170.0, 130.0))
        conn.commit()


def get_products(conn, collection=None, statut=None):
    q = "SELECT * FROM products WHERE 1=1"
    p = []
    if collection: q += " AND collection=?"; p.append(collection)
    if statut:     q += " AND statut=?";     p.append(statut)
    return pd.read_sql(q + " ORDER BY collection, nom", conn, params=p)


def get_product(conn, product_id):
    return pd.read_sql("SELECT * FROM products WHERE id=?", conn, params=[product_id])


def get_images(conn, product_id):
    return pd.read_sql("SELECT * FROM product_images WHERE product_id=? ORDER BY ordre", conn, params=[product_id])


def get_components(conn, product_id):
    return pd.read_sql("SELECT * FROM product_components WHERE product_id=?", conn, params=[product_id])


def get_archives(conn, product_id):
    return pd.read_sql("SELECT * FROM product_archives WHERE product_id=?", conn, params=[product_id])


def get_costs(conn, product_id):
    df = pd.read_sql("SELECT * FROM product_costs WHERE product_id=?", conn, params=[product_id])
    return df.iloc[0] if not df.empty else None


def fmt_eur(v):
    if v is None or v == 0: return "—"
    return f"{float(v):,.2f} €".replace(",", " ")


def fmt_jpy(v):
    if v is None or v == 0: return "—"
    return f"¥ {float(v):,.0f}"


# ── LINE SHEET PDF ─────────────────────────────────────────────────────────────
def generate_linesheet(conn, collection_filter=None):
    if not REPORTLAB_OK:
        return None, "reportlab non installé"

    buf = io.BytesIO()
    W, H = A4
    M = 15 * mm
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=M, rightMargin=M,
                            topMargin=M, bottomMargin=M)

    # Styles
    styles = getSampleStyleSheet()
    style_brand  = ParagraphStyle("brand",  fontName="Helvetica-Bold", fontSize=16,
                                  letterSpacing=4, spaceAfter=2, alignment=TA_CENTER)
    style_sub    = ParagraphStyle("sub",    fontName="Helvetica",      fontSize=7,
                                  letterSpacing=6, textColor=colors.HexColor("#888078"),
                                  spaceAfter=12, alignment=TA_CENTER)
    style_coll   = ParagraphStyle("coll",   fontName="Helvetica-Bold", fontSize=9,
                                  letterSpacing=2, spaceBefore=16, spaceAfter=6,
                                  textColor=colors.HexColor("#1a1a1a"))
    style_ref    = ParagraphStyle("ref",    fontName="Helvetica",      fontSize=7,
                                  textColor=colors.HexColor("#888078"), spaceAfter=2)
    style_nom    = ParagraphStyle("nom",    fontName="Helvetica-Bold", fontSize=10,
                                  spaceAfter=3)
    style_small  = ParagraphStyle("small",  fontName="Helvetica",      fontSize=7,
                                  textColor=colors.HexColor("#666058"), spaceAfter=2)
    style_price  = ParagraphStyle("price",  fontName="Helvetica-Bold", fontSize=8,
                                  textColor=colors.HexColor("#1a1a1a"))

    story = []

    # Header
    story.append(Paragraph("EASTWOOD STUDIO", style_brand))
    story.append(Paragraph("PARIS · LINE SHEET", style_sub))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1a1a1a")))
    story.append(Spacer(1, 6*mm))

    q = "SELECT * FROM products WHERE 1=1"
    params = []
    if collection_filter:
        q += " AND collection=?"; params.append(collection_filter)
    df_prods = pd.read_sql(q + " ORDER BY collection, nom", conn, params=params)

    if df_prods.empty:
        story.append(Paragraph("Aucun produit.", styles["Normal"]))
        doc.build(story)
        return buf.getvalue(), None

    # Grouper par collection
    for coll, grp in df_prods.groupby("collection"):
        story.append(Paragraph(coll.upper(), style_coll))
        story.append(HRFlowable(width="100%", thickness=0.3,
                                color=colors.HexColor("#e0dbd2")))
        story.append(Spacer(1, 3*mm))

        # 2 produits par ligne
        prods = list(grp.iterrows())
        for i in range(0, len(prods), 2):
            row_data = []
            for j in range(2):
                if i+j >= len(prods):
                    row_data.append("")
                    continue
                _, prod = prods[i+j]

                # Image produit
                imgs = pd.read_sql("SELECT data FROM product_images WHERE product_id=? ORDER BY ordre LIMIT 1",
                                   conn, params=[prod["id"]])
                cell_content = []
                if not imgs.empty and imgs.iloc[0]["data"] is not None:
                    try:
                        img_io = io.BytesIO(bytes(imgs.iloc[0]["data"]))
                        rl_img = RLImage(img_io, width=75*mm, height=75*mm)
                        rl_img.hAlign = "CENTER"
                        cell_content.append(rl_img)
                    except Exception:
                        cell_content.append(Paragraph("[visuel]", style_small))
                else:
                    # Placeholder gris
                    placeholder_tbl = Table([[""]], colWidths=[75*mm], rowHeights=[75*mm])
                    placeholder_tbl.setStyle(TableStyle([
                        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f0ece4")),
                        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#e0dbd2")),
                    ]))
                    cell_content.append(placeholder_tbl)

                cell_content.append(Spacer(1, 2*mm))
                cell_content.append(Paragraph(str(prod["ref"]), style_ref))
                cell_content.append(Paragraph(str(prod["nom"]), style_nom))
                if prod["description"]:
                    desc_short = str(prod["description"])[:120] + ("..." if len(str(prod["description"]))>120 else "")
                    cell_content.append(Paragraph(desc_short, style_small))
                if prod["matieres"]:
                    cell_content.append(Paragraph(f"Matières : {prod['matieres']}", style_small))
                if prod["tailles"]:
                    cell_content.append(Paragraph(f"Tailles : {prod['tailles']}", style_small))
                cell_content.append(Spacer(1, 2*mm))

                # Prix
                price_rows = []
                if prod["prix_retail_eur"]:
                    price_rows.append(f"Retail FR : {fmt_eur(prod['prix_retail_eur'])}")
                if prod["prix_retail_jpy"]:
                    price_rows.append(f"Retail JP : {fmt_jpy(prod['prix_retail_jpy'])}")
                if prod["prix_wholesale_fr"]:
                    price_rows.append(f"Wholesale : {fmt_eur(prod['prix_wholesale_fr'])}")
                for pr in price_rows:
                    cell_content.append(Paragraph(pr, style_price))

                row_data.append(cell_content)

            tbl = Table([row_data], colWidths=[(W - 2*M - 8*mm) / 2] * 2)
            tbl.setStyle(TableStyle([
                ("VALIGN",  (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 4*mm),
                ("RIGHTPADDING", (0,0), (-1,-1), 4*mm),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6*mm),
            ]))
            story.append(tbl)

        story.append(Spacer(1, 4*mm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#e0dbd2")))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f"EASTWOOD STUDIO · Paris · eastwood-studio.fr · {date.today().strftime('%B %Y')}",
        ParagraphStyle("footer", fontName="Helvetica", fontSize=6,
                       textColor=colors.HexColor("#aaa49a"), alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue(), None


# ── COST SHEET HELPERS ────────────────────────────────────────────────────────
COST_SECTIONS = {
    "Sample": [
        ("cout_patronage",    "Patronage"),
        ("cout_gradation",    "Gradation"),
        ("cout_assemblage",   "Assemblage"),
        ("cout_production",   "Production"),
        ("cout_mp1_sample",   "MP 1 sample"),
        ("cout_mp2_sample",   "MP 2 sample"),
        ("cout_compo1_sample","Compo 1 sample"),
        ("cout_compo2_sample","Compo 2 sample"),
        ("cout_log_sample",   "Frais logistiques sample"),
        ("cout_tax_sample",   "Tax sample"),
    ],
    "MP & Composants": [
        ("cout_mp_principale","MP principale"),
        ("cout_mp_secondaire","MP secondaire"),
        ("cout_jet_encre",    "Jet d'encre"),
        ("cout_lining",       "Lining"),
        ("cout_boutons",      "Boutons"),
        ("cout_zip",          "Zip"),
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
        ("cout_broderie", "Broderie"),
        ("cout_coupe",    "Coupe"),
        ("cout_print",    "Print allover"),
    ],
    "Logistique": [
        ("cout_stockage",  "Stockage"),
        ("cout_emballage", "Emballage / Préparation"),
        ("cout_appro",     "Approvisionnement"),
        ("cout_douane",    "Douane"),
    ],
    "Packaging": [
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

COST_SECTION_TOTALS = {
    "Sample":                ["cout_patronage","cout_gradation","cout_assemblage","cout_production",
                              "cout_mp1_sample","cout_mp2_sample","cout_compo1_sample","cout_compo2_sample",
                              "cout_log_sample","cout_tax_sample"],
    "MP & Composants":       ["cout_mp_principale","cout_mp_secondaire","cout_jet_encre",
                              "cout_lining","cout_boutons","cout_zip"],
    "Étiquettes":            ["cout_etiq_textile","cout_etiq_taille","cout_etiq_compo",
                              "cout_etiq_fab_fr","cout_tag_numero"],
    "Production & Réalisation": ["cout_montage","cout_broderie","cout_coupe","cout_print"],
    "Logistique":            ["cout_stockage","cout_emballage","cout_appro","cout_douane"],
    "Packaging":             ["cout_boite","cout_sac","cout_feuille_expl",
                              "cout_lettre","cout_enveloppe","cout_stickers"],
    "Marketing":             ["cout_marketing"],
}

def compute_cost_totals(row_dict):
    totals = {}
    grand = 0.0
    for section, keys in COST_SECTION_TOTALS.items():
        t = sum(float(row_dict.get(k, 0) or 0) for k in keys)
        totals[section] = t
        grand += t
    totals["TOTAL"] = grand
    return totals


# ══════════════════════════════════════════════════════════════════════════════
# PAGE PRODUITS — fonction principale appelée depuis app.py
# ══════════════════════════════════════════════════════════════════════════════
def page_produits(can_fn, DB_PATH, fmt_eur_fn, fmt_jpy_fn=None):
    """
    can_fn   : la fonction can() de l'app principale
    DB_PATH  : chemin vers la base SQLite
    fmt_eur_fn : formateur monétaire EUR
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_products_db(conn)

    if fmt_jpy_fn is None:
        fmt_jpy_fn = fmt_jpy

    st.markdown("### Produits & Collections")

    # Tabs
    _tabs = ["🗂 Catalogue"]
    if can_fn("stock_write"):
        _tabs += ["➕ Nouveau produit"]
    _tabs += ["📄 Line Sheet"]
    if can_fn("finance_write"):
        _tabs += ["💰 Coûts production"]

    tab_objs = st.tabs(_tabs)
    idx = 0
    tab_cat   = tab_objs[idx]; idx += 1
    tab_new   = tab_objs[idx] if can_fn("stock_write") else None
    if can_fn("stock_write"): idx += 1
    tab_ls    = tab_objs[idx]; idx += 1
    tab_costs = tab_objs[idx] if can_fn("finance_write") else None

    # ── CATALOGUE ──────────────────────────────────────────────────────────────
    with tab_cat:
        c1, c2 = st.columns(2)
        with c1:
            f_coll = st.selectbox("Collection", ["Toutes"] + COLLECTIONS, key="f_coll_cat")
        with c2:
            f_stat = st.selectbox("Statut", ["Tous"] + STATUTS_PROD, key="f_stat_cat")

        df_prods = get_products(
            conn,
            collection=None if f_coll == "Toutes" else f_coll,
            statut=None if f_stat == "Tous" else f_stat,
        )

        if df_prods.empty:
            st.info("Aucun produit dans cette sélection.")
        else:
            # Grouper par collection
            for coll_name, grp in df_prods.groupby("collection"):
                st.markdown(f'<div class="section-title">{coll_name}</div>',
                            unsafe_allow_html=True)
                cols = st.columns(3)
                for i, (_, prod) in enumerate(grp.iterrows()):
                    with cols[i % 3]:
                        # Image miniature
                        imgs = get_images(conn, prod["id"])
                        if not imgs.empty and imgs.iloc[0]["data"] is not None:
                            try:
                                img_bytes = bytes(imgs.iloc[0]["data"])
                                b64 = base64.b64encode(img_bytes).decode()
                                ext = (imgs.iloc[0]["nom_fichier"] or "img.jpg").split(".")[-1].lower()
                                mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                                st.markdown(f"""
<div style="aspect-ratio:3/4;background:#f0ece4;border-radius:4px;overflow:hidden;margin-bottom:8px;">
  <img src="data:{mime};base64,{b64}" style="width:100%;height:100%;object-fit:cover;"/>
</div>""", unsafe_allow_html=True)
                            except Exception:
                                st.markdown("""<div style="aspect-ratio:3/4;background:#f0ece4;border-radius:4px;display:flex;align-items:center;justify-content:center;margin-bottom:8px;"><span style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">VISUEL</span></div>""", unsafe_allow_html=True)
                        else:
                            st.markdown("""<div style="aspect-ratio:3/4;background:#f0ece4;border-radius:4px;display:flex;align-items:center;justify-content:center;margin-bottom:8px;"><span style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">VISUEL</span></div>""", unsafe_allow_html=True)

                        stat_c = {"Disponible":"#2d6a4f","Développement":"#c9800a",
                                  "Production":"#185FA5","Concept":"#888",
                                  "Soldé":"#c1440e","Archive":"#555"}.get(prod["statut"],"#888")
                        st.markdown(f"""
<div style="margin-bottom:12px;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">{prod['ref']}</div>
  <div style="font-size:14px;font-weight:500;color:#1a1a1a;margin:2px 0;">{prod['nom']}</div>
  <div style="font-family:'DM Mono',monospace;font-size:9px;color:{stat_c};">● {prod['statut']}</div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:#1a1a1a;margin-top:4px;">{fmt_eur_fn(prod['prix_retail_eur'])}</div>
</div>""", unsafe_allow_html=True)

                        if st.button("Voir fiche →", key=f"voir_{prod['id']}"):
                            st.session_state["product_view"] = prod["id"]
                            st.rerun()

        # ── FICHE PRODUIT ──────────────────────────────────────────────────────
        if "product_view" in st.session_state:
            pid = st.session_state["product_view"]
            df_p = get_product(conn, pid)
            if df_p.empty:
                del st.session_state["product_view"]
                st.rerun()
            prod = df_p.iloc[0]

            st.markdown("---")
            if st.button("← Retour au catalogue"):
                del st.session_state["product_view"]
                st.rerun()

            # Header fiche
            hc1, hc2 = st.columns([1, 2])

            with hc1:
                imgs = get_images(conn, pid)
                if not imgs.empty:
                    # Galerie images
                    img_idx = st.session_state.get(f"img_idx_{pid}", 0)
                    row_img = imgs.iloc[img_idx]
                    if row_img["data"] is not None:
                        try:
                            img_bytes = bytes(row_img["data"])
                            b64 = base64.b64encode(img_bytes).decode()
                            ext = (row_img["nom_fichier"] or "img.jpg").split(".")[-1].lower()
                            mime = "image/jpeg" if ext in ("jpg","jpeg") else f"image/{ext}"
                            st.markdown(f"""<div style="background:#f0ece4;border-radius:4px;overflow:hidden;">
<img src="data:{mime};base64,{b64}" style="width:100%;object-fit:contain;max-height:320px;"/></div>""", unsafe_allow_html=True)
                        except Exception:
                            st.info("Erreur affichage image.")

                    if len(imgs) > 1:
                        ic1, ic2 = st.columns(2)
                        with ic1:
                            if st.button("‹ Préc.", key=f"prev_{pid}") and img_idx > 0:
                                st.session_state[f"img_idx_{pid}"] = img_idx - 1; st.rerun()
                        with ic2:
                            if st.button("Suiv. ›", key=f"next_{pid}") and img_idx < len(imgs)-1:
                                st.session_state[f"img_idx_{pid}"] = img_idx + 1; st.rerun()
                else:
                    st.markdown("""<div style="aspect-ratio:3/4;background:#f0ece4;border-radius:4px;display:flex;align-items:center;justify-content:center;">
<span style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">AUCUN VISUEL</span></div>""", unsafe_allow_html=True)

                # Upload images
                if can_fn("stock_write"):
                    new_imgs = st.file_uploader("Ajouter des visuels",
                        accept_multiple_files=True, type=["png","jpg","jpeg","webp"],
                        key=f"img_up_{pid}")
                    if new_imgs and st.button("✓ Upload", key=f"img_save_{pid}"):
                        existing_count = len(imgs)
                        for k, f in enumerate(new_imgs):
                            conn.execute("""INSERT INTO product_images (product_id,nom_fichier,data,ordre)
                                VALUES (?,?,?,?)""", (pid, f.name, f.read(), existing_count + k))
                        conn.commit()
                        st.success(f"✓ {len(new_imgs)} visuel(s) ajouté(s)."); st.rerun()

            with hc2:
                st.markdown(f"""
<div style="margin-bottom:16px;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;letter-spacing:.15em;">{prod['ref']} · {prod['collection']}</div>
  <div style="font-size:24px;font-weight:500;color:#1a1a1a;margin:4px 0 8px;">{prod['nom']}</div>
</div>""", unsafe_allow_html=True)

                if can_fn("stock_write"):
                    with st.form(f"edit_prod_{pid}"):
                        ep1, ep2 = st.columns(2)
                        with ep1:
                            e_nom   = st.text_input("Nom", value=prod["nom"])
                            e_ref   = st.text_input("Réf.", value=prod["ref"])
                            e_coll  = st.selectbox("Collection", COLLECTIONS,
                                                   index=COLLECTIONS.index(prod["collection"]) if prod["collection"] in COLLECTIONS else 0)
                            e_stat  = st.selectbox("Statut", STATUTS_PROD,
                                                   index=STATUTS_PROD.index(prod["statut"]) if prod["statut"] in STATUTS_PROD else 0)
                        with ep2:
                            e_mat   = st.text_input("Matières", value=prod["matieres"] or "")
                            e_coul  = st.text_input("Couleurs", value=prod["couleurs"] or "")
                            e_tail  = st.text_input("Tailles", value=prod["tailles"] or "")
                        e_desc = st.text_area("Description", value=prod["description"] or "", height=88)
                        pp1, pp2, pp3, pp4, pp5 = st.columns(5)
                        with pp1: e_preu = st.number_input("Retail EUR", value=float(prod["prix_retail_eur"] or 0), min_value=0.0)
                        with pp2: e_prjp = st.number_input("Retail JPY", value=float(prod["prix_retail_jpy"] or 0), min_value=0.0)
                        with pp3: e_pwfr = st.number_input("Wholesale FR", value=float(prod["prix_wholesale_fr"] or 0), min_value=0.0)
                        with pp4: e_pwmo = st.number_input("Wholesale Monde", value=float(prod["prix_wholesale_monde"] or 0), min_value=0.0)
                        with pp5: e_pff  = st.number_input("F&F", value=float(prod["prix_ff"] or 0), min_value=0.0)

                        if st.form_submit_button("💾 Enregistrer"):
                            conn.execute("""UPDATE products SET nom=?,ref=?,collection=?,statut=?,description=?,
                                matieres=?,couleurs=?,tailles=?,
                                prix_retail_eur=?,prix_retail_jpy=?,prix_wholesale_fr=?,prix_wholesale_monde=?,prix_ff=?
                                WHERE id=?""",
                                (e_nom,e_ref,e_coll,e_stat,e_desc,e_mat,e_coul,e_tail,
                                 e_preu,e_prjp,e_pwfr,e_pwmo,e_pff,pid))
                            conn.commit()
                            st.success("✓ Produit mis à jour."); st.rerun()
                else:
                    # Vue lecture
                    for label, val in [("Description",prod["description"]),("Matières",prod["matieres"]),
                                       ("Couleurs",prod["couleurs"]),("Tailles",prod["tailles"])]:
                        if val:
                            st.write(f"**{label}** : {val}")
                    st.markdown(f"**Retail FR** : {fmt_eur_fn(prod['prix_retail_eur'])} · **Retail JP** : {fmt_jpy_fn(prod['prix_retail_jpy'])}")
                    st.markdown(f"**Wholesale FR** : {fmt_eur_fn(prod['prix_wholesale_fr'])} · **Wholesale Monde** : {fmt_eur_fn(prod['prix_wholesale_monde'])} · **F&F** : {fmt_eur_fn(prod['prix_ff'])}")

            # Onglets fiche
            st.markdown("---")
            ft1, ft2, ft3 = st.tabs(["🧵 Composants", "📚 Archives", "🗑 Gestion"])

            with ft1:
                df_comp = get_components(conn, pid)
                if not df_comp.empty:
                    total_mp = (df_comp["quantite"] * df_comp["cout_unitaire"]).sum()
                    st.dataframe(df_comp[["nom","ref_stock","quantite","unite","cout_unitaire"]].rename(columns={
                        "nom":"Composant","ref_stock":"Réf. stock","quantite":"Qté",
                        "unite":"Unité","cout_unitaire":"Coût unit. (€)"}),
                        use_container_width=True, hide_index=True)
                    st.markdown(f"**Total coût matières : {fmt_eur_fn(total_mp)}**")
                else:
                    st.info("Aucun composant enregistré.")

                if can_fn("stock_write"):
                    st.markdown('<div class="section-title">Ajouter un composant</div>', unsafe_allow_html=True)
                    with st.form(f"add_comp_{pid}"):
                        cc1,cc2,cc3,cc4,cc5 = st.columns(5)
                        with cc1: c_nom  = st.text_input("Composant")
                        with cc2: c_ref  = st.text_input("Réf. stock")
                        with cc3: c_qte  = st.number_input("Qté", min_value=0.0, value=1.0)
                        with cc4: c_unit = st.selectbox("Unité", ["Pièces","Mètre","Kg","Litre","Lot"])
                        with cc5: c_cout = st.number_input("Coût unit. (€)", min_value=0.0, value=0.0, step=0.01)
                        if st.form_submit_button("➕ Ajouter"):
                            conn.execute("""INSERT INTO product_components
                                (product_id,ref_stock,nom,quantite,unite,cout_unitaire)
                                VALUES (?,?,?,?,?,?)""", (pid,c_ref,c_nom,c_qte,c_unit,c_cout))
                            conn.commit(); st.rerun()

            with ft2:
                df_arch = get_archives(conn, pid)
                if not df_arch.empty:
                    for _, arch in df_arch.iterrows():
                        st.markdown(f"""
<div style="background:#f7f5f0;border:1px solid #e0dbd2;border-radius:4px;padding:10px 14px;margin:6px 0;">
  <div style="display:flex;gap:12px;align-items:baseline;">
    <span style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">{arch.get('annee','')}</span>
    <span style="font-weight:500;font-size:13px;">{arch.get('nom_archive','')}</span>
    <span style="font-size:11px;color:#888078;">{arch.get('type_archive','')} · {arch.get('matiere','')} · {arch.get('lieu','')}</span>
  </div>
  {f'<div style="font-size:12px;color:#aaa49a;margin-top:4px;">{arch["details"]}</div>' if arch.get("details") else ''}
</div>""", unsafe_allow_html=True)
                else:
                    st.info("Aucune archive enregistrée.")

                if can_fn("stock_write"):
                    st.markdown('<div class="section-title">Ajouter une archive</div>', unsafe_allow_html=True)
                    with st.form(f"add_arch_{pid}"):
                        ac1,ac2,ac3 = st.columns(3)
                        with ac1: a_annee = st.number_input("Année", min_value=1900, max_value=2100, value=2025)
                        with ac2: a_type  = st.selectbox("Type", ["Matière","Couleur","Forme","Technique","Référence visuelle","Autre"])
                        with ac3: a_mat   = st.text_input("Matière")
                        ac4,ac5 = st.columns(2)
                        with ac4: a_nom  = st.text_input("Nom de l'archive")
                        with ac5: a_lieu = st.text_input("Lieu / Source")
                        a_det = st.text_area("Détails", height=60)
                        if st.form_submit_button("➕ Ajouter"):
                            conn.execute("""INSERT INTO product_archives
                                (product_id,annee,type_archive,matiere,nom_archive,lieu,details)
                                VALUES (?,?,?,?,?,?,?)""", (pid,a_annee,a_type,a_mat,a_nom,a_lieu,a_det))
                            conn.commit(); st.rerun()

            with ft3:
                st.markdown('<div class="section-title">Gestion du produit</div>', unsafe_allow_html=True)
                if can_fn("products_delete"):
                    st.warning("⚠ Supprimer ce produit supprime aussi ses images, composants et archives.")
                    if st.button("🗑 Supprimer ce produit", type="secondary"):
                        for tbl in ["product_images","product_components","product_archives","product_costs"]:
                            conn.execute(f"DELETE FROM {tbl} WHERE product_id=?", (pid,))
                        conn.execute("DELETE FROM products WHERE id=?", (pid,))
                        conn.commit()
                        del st.session_state["product_view"]
                        st.success("Produit supprimé."); st.rerun()
                else:
                    st.info("Seul Jules peut supprimer un produit.")

                # Supprimer images individuellement
                if can_fn("stock_write"):
                    imgs2 = get_images(conn, pid)
                    if not imgs2.empty:
                        st.markdown("**Gérer les visuels**")
                        for _, img_row in imgs2.iterrows():
                            ic1, ic2 = st.columns([3,1])
                            with ic1: st.write(img_row["nom_fichier"])
                            with ic2:
                                if st.button("🗑", key=f"del_img_{img_row['id']}"):
                                    conn.execute("DELETE FROM product_images WHERE id=?", (img_row["id"],))
                                    conn.commit(); st.rerun()

    # ── NOUVEAU PRODUIT ────────────────────────────────────────────────────────
    if tab_new is not None:
        with tab_new:
            st.markdown('<div class="section-title">Nouveau produit</div>', unsafe_allow_html=True)
            nc1, nc2, nc3 = st.columns(3)
            with nc1:
                n_ref  = st.text_input("Référence SKU *", placeholder="MIRA-002")
                n_nom  = st.text_input("Nom *", placeholder="Veste Miura II")
                n_coll = st.selectbox("Collection", COLLECTIONS)
            with nc2:
                n_stat = st.selectbox("Statut", STATUTS_PROD)
                n_mat  = st.text_input("Matières", placeholder="Coton, Viscose")
                n_coul = st.text_input("Couleurs", placeholder="Noir, Ivoire")
            with nc3:
                n_tail = st.text_input("Tailles", placeholder="XS, S, M, L")
                n_preu = st.number_input("Retail EUR", min_value=0.0, value=0.0)
                n_prjp = st.number_input("Retail JPY", min_value=0.0, value=0.0)
            np1, np2 = st.columns(2)
            with np1: n_pwfr = st.number_input("Wholesale FR", min_value=0.0, value=0.0)
            with np2: n_pwmo = st.number_input("Wholesale Monde", min_value=0.0, value=0.0)
            n_desc = st.text_area("Description", height=80)

            if st.button("✓ Créer le produit"):
                if not n_ref or not n_nom:
                    st.error("Référence et nom obligatoires.")
                else:
                    try:
                        conn.execute("""INSERT INTO products
                            (ref,nom,collection,statut,description,matieres,couleurs,tailles,
                             prix_retail_eur,prix_retail_jpy,prix_wholesale_fr,prix_wholesale_monde)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (n_ref,n_nom,n_coll,n_stat,n_desc,n_mat,n_coul,n_tail,
                             n_preu,n_prjp,n_pwfr,n_pwmo))
                        conn.commit()
                        st.success("✓ Produit créé.")
                    except sqlite3.IntegrityError:
                        st.error("Cette référence existe déjà.")

    # ── LINE SHEET ─────────────────────────────────────────────────────────────
    with tab_ls:
        st.markdown('<div class="section-title">Génération line sheet</div>', unsafe_allow_html=True)

        ls_coll = st.selectbox("Collection", ["Toutes"] + COLLECTIONS, key="ls_coll")
        coll_arg = None if ls_coll == "Toutes" else ls_coll

        st.markdown("""
<div class="info-box">
Le line sheet est généré en format A4 — sobre, lisible, prêt pour les showrooms.
Il inclut les visuels produits, références, matières, tailles et grille de prix.
</div>""", unsafe_allow_html=True)

        if st.button("📄 Générer le line sheet PDF"):
            with st.spinner("Génération en cours..."):
                pdf_bytes, err = generate_linesheet(conn, coll_arg)
            if err:
                st.error(f"Erreur : {err}")
            elif pdf_bytes:
                fname = f"linesheet_eastwood_{ls_coll.split('—')[0].strip().replace(' ','_')}.pdf"
                st.download_button("⬇ Télécharger le line sheet",
                                   pdf_bytes, file_name=fname,
                                   mime="application/pdf")
                st.success("✓ Line sheet généré !")

        # Aperçu catalogue
        st.markdown('<div class="section-title">Aperçu catalogue</div>', unsafe_allow_html=True)
        df_ls = get_products(conn, collection=coll_arg)
        if df_ls.empty:
            st.info("Aucun produit dans cette sélection.")
        else:
            for _, p in df_ls.iterrows():
                st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
     border-bottom:1px solid #e8e4dc;padding:8px 0;">
  <div>
    <span style="font-family:'DM Mono',monospace;font-size:10px;color:#aaa49a;">{p['ref']}</span>
    <span style="font-size:14px;font-weight:500;margin-left:10px;">{p['nom']}</span>
    <span style="font-size:11px;color:#888078;margin-left:10px;">{p['collection']}</span>
  </div>
  <div style="font-family:'DM Mono',monospace;font-size:11px;color:#1a1a1a;text-align:right;">
    {fmt_eur_fn(p['prix_retail_eur'])} · {fmt_jpy_fn(p['prix_retail_jpy'])}
  </div>
</div>""", unsafe_allow_html=True)

    # ── COÛTS PRODUCTION (Jules only) ─────────────────────────────────────────
    if tab_costs is not None:
        with tab_costs:
            st.markdown('<div class="section-title">Coûts de production — confidentiel</div>',
                        unsafe_allow_html=True)

            df_all_p = get_products(conn)
            if df_all_p.empty:
                st.info("Aucun produit.")
            else:
                prod_options = {f"{r['ref']} — {r['nom']}": r["id"] for _, r in df_all_p.iterrows()}
                sel_prod_label = st.selectbox("Sélectionner un produit", list(prod_options.keys()))
                sel_pid = prod_options[sel_prod_label]

                costs_row = get_costs(conn, sel_pid)
                costs_dict = dict(costs_row) if costs_row is not None else {}

                with st.form(f"costs_form_{sel_pid}"):
                    all_inputs = {}

                    for section_name, fields in COST_SECTIONS.items():
                        st.markdown(f'<div class="section-title">{section_name}</div>',
                                    unsafe_allow_html=True)
                        n_cols = min(len(fields), 3)
                        cols = st.columns(n_cols)
                        for i, (key, label) in enumerate(fields):
                            with cols[i % n_cols]:
                                all_inputs[key] = st.number_input(
                                    label, min_value=0.0, step=0.01,
                                    value=float(costs_dict.get(key, 0) or 0),
                                    key=f"{key}_{sel_pid}"
                                )

                    st.markdown('<div class="section-title">Prix cibles</div>', unsafe_allow_html=True)
                    pc1,pc2,pc3,pc4 = st.columns(4)
                    with pc1: all_inputs["prix_vente_cible"]    = st.number_input("Prix vente cible",    min_value=0.0, value=float(costs_dict.get("prix_vente_cible",0) or 0))
                    with pc2: all_inputs["prix_vente_normalise"] = st.number_input("Prix vente normalisé",min_value=0.0, value=float(costs_dict.get("prix_vente_normalise",0) or 0))
                    with pc3: all_inputs["prix_reco_wholesale"]  = st.number_input("Reco Wholesale",      min_value=0.0, value=float(costs_dict.get("prix_reco_wholesale",0) or 0))
                    with pc4: all_inputs["prix_wholesale_japan"] = st.number_input("Wholesale Japon",     min_value=0.0, value=float(costs_dict.get("prix_wholesale_japan",0) or 0))
                    pc5,pc6,pc7,pc8 = st.columns(4)
                    with pc5: all_inputs["prix_rdm"]  = st.number_input("Prix RDM",    min_value=0.0, value=float(costs_dict.get("prix_rdm",0) or 0))
                    with pc6: all_inputs["srp_eu"]    = st.number_input("SRP EU",      min_value=0.0, value=float(costs_dict.get("srp_eu",0) or 0))
                    with pc7: all_inputs["srp_jpn"]   = st.number_input("SRP JPN (¥)", min_value=0.0, value=float(costs_dict.get("srp_jpn",0) or 0))
                    with pc8: all_inputs["srp_rdm"]   = st.number_input("SRP RDM",     min_value=0.0, value=float(costs_dict.get("srp_rdm",0) or 0))

                    if st.form_submit_button("💾 Enregistrer les coûts"):
                        all_inputs["product_id"] = sel_pid
                        cols_str = ", ".join(all_inputs.keys())
                        ph       = ", ".join(["?"] * len(all_inputs))
                        upd      = ", ".join(f"{k}=?" for k in all_inputs if k != "product_id")
                        conn.execute(
                            f"INSERT INTO product_costs ({cols_str}) VALUES ({ph}) "
                            f"ON CONFLICT(product_id) DO UPDATE SET {upd}",
                            list(all_inputs.values()) + [v for k,v in all_inputs.items() if k != "product_id"]
                        )
                        conn.commit()
                        st.success("✓ Coûts enregistrés.")
                        st.rerun()

                # Récap coûts
                if costs_row is not None:
                    st.markdown('<div class="section-title">Récapitulatif</div>', unsafe_allow_html=True)
                    totals = compute_cost_totals(dict(costs_row))
                    recap_cols = st.columns(len(totals))
                    for i, (sec, val) in enumerate(totals.items()):
                        with recap_cols[i]:
                            st.metric(sec, fmt_eur_fn(val))

                    prix_vente = float(costs_dict.get("prix_vente_cible", 0) or 0)
                    cout_total = totals["TOTAL"]
                    if prix_vente > 0 and cout_total > 0:
                        marge = ((prix_vente - cout_total) / prix_vente) * 100
                        marge_euro = prix_vente - cout_total
                        st.markdown(f"""
<div style="background:#f7f5f0;border:1px solid #e0dbd2;border-left:3px solid #1a1a1a;border-radius:2px;padding:16px 20px;margin-top:12px;">
  <div style="font-family:'DM Mono',monospace;font-size:10px;color:#888078;letter-spacing:.15em;text-transform:uppercase;">Estimation marge</div>
  <div style="font-family:'DM Mono',monospace;font-size:22px;font-weight:500;color:{'#2d6a4f' if marge>0 else '#c1440e'};margin:6px 0;">
    {marge:.1f}%
  </div>
  <div style="font-size:13px;color:#666058;">
    Prix vente : {fmt_eur_fn(prix_vente)} · Coût total : {fmt_eur_fn(cout_total)} · Marge brute : {fmt_eur_fn(marge_euro)}
  </div>
</div>""", unsafe_allow_html=True)

    conn.close()
