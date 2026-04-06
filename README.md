# EASTWOOD — Application de gestion
## Guide de déploiement rapide (sans coder)

---

### OPTION 1 — Streamlit Cloud (recommandé, gratuit, accessible partout)

**Étape 1 — Créer un compte GitHub (si pas déjà fait)**
→ https://github.com → "Sign up"

**Étape 2 — Créer un nouveau dépôt GitHub**
→ Clic "+" en haut à droite → "New repository"
→ Nom : `eastwood-gestion`
→ Visibilité : Private ✓
→ Clic "Create repository"

**Étape 3 — Uploader les 3 fichiers**
Depuis la page du dépôt → "Add file" → "Upload files"
Glisser-déposer :
- `app.py`
- `requirements.txt`
- `README.md` (ce fichier)

**Étape 4 — Déployer sur Streamlit Cloud**
→ https://share.streamlit.io → "Sign in with GitHub"
→ "New app"
→ Repository : `eastwood-gestion`
→ Branch : `main`
→ Main file path : `app.py`
→ Clic "Deploy!"

L'application sera accessible en 2-3 minutes à une URL du type :
`https://eastwood-gestion-XXXXX.streamlit.app`

---

### OPTION 2 — En local sur ton ordi (Mac)

**Prérequis : installer Python**
→ https://www.python.org/downloads/ → télécharger Python 3.11+

**Dans le Terminal (Applications → Utilitaires → Terminal) :**
```bash
# Installer les dépendances
pip install streamlit pandas openpyxl

# Lancer l'application (depuis le dossier contenant app.py)
cd ~/Desktop/eastwood-gestion
streamlit run app.py
```
L'application s'ouvre automatiquement dans ton navigateur.

---

### Structure des fichiers

```
eastwood-gestion/
├── app.py              → L'application complète
├── requirements.txt    → Dépendances Python
├── README.md           → Ce guide
└── eastwood.db         → Base de données (créée automatiquement au 1er lancement)
```

---

### Fonctionnalités incluses

| Module | Ce que ça fait |
|---|---|
| 📊 Dashboard | KPIs (CA, charges, résultat, TVA due), graphiques, alertes stock |
| 💳 Transactions | Historique filtrables, saisie avec TVA auto-suggérée, export Excel |
| 📦 Commandes | Suivi avec checklist de production par commande |
| 🗃️ Stock | Inventaire par type, valeur totale, alertes réassort |
| 📋 TVA & Comptabilité | TVA par trimestre, compte de résultat, bilan simplifié |
| 👤 Contacts | Fournisseurs, ateliers, clients, prestataires |

---

### Règles TVA intégrées (loi française)

| Opération | Règle appliquée |
|---|---|
| Vente en France | TVA **collectée** 20% |
| Achat fournisseur FR | TVA **déductible** 20% |
| Achat hors UE / intracommunautaire | TVA **autoliquidée** |
| Frais bancaires, INPI, frais perso | **Aucune** TVA |

---

### Prochaines étapes (roadmap)

- [ ] OCR automatique des factures (via Google Vision API)
- [ ] Connexion Revolut Business API
- [ ] Sync Google Sheets bidirectionnelle
- [ ] Génération PDF déclarations TVA CA3
- [ ] Multi-utilisateurs avec authentification

---

*Développé pour Eastwood Paris · 2025*
