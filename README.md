# Projet bancaire — Tableau de bord Streamlit et API Flask

Ce projet propose une application web destinée à l’analyse du risque client dans un contexte bancaire. Il combine :
- une API Flask légère (`API/API.py`) qui lit le dataset `application_train.csv`, expose des routes de santé, de dataviz, et de scoring simplifié ;
- une interface Streamlit (`Projet bancaire/Projet bancaire/client_prediction.py` et `Projet bancaire/Projet bancaire/data_analysis.py`) permettant de scorer un client et d’explorer le dataset via des filtres interactifs.

## 1. Description et objectifs
- Visualiser et explorer rapidement les données clients (revenus, montants de crédit, statut familial, etc.).
- Calculer un score de risque de défaut (heuristique ratio crédit/revenu) et fournir des indicateurs relatifs (percentiles) issus du dataset.
- Fournir une API unique pouvant être appelée par l’UI Streamlit ou des scripts externes.

## 2. Installation et configuration
### Prérequis
- Python 3.9+ (recommandé)
- `pip`
- Fichier CSV `application_train.csv` placé à la racine du projet (même niveau que le dossier `API` et `Projet bancaire`).

### Dépendances
Installez les dépendances principales :
```bash
pip install streamlit flask flask-caching python-dotenv pandas plotly requests
```
> L’API fait déjà un auto-install minimal, mais il est recommandé d’installer les dépendances au préalable pour éviter les délais au démarrage.

Jeu de données :

https://github.com/archiducarmel/SupdeVinci_BigData_Cloud/releases/download/datas/application_train.csv

### Variables d’environnement
Créez ou éditez `.env` (exemples) :
```
FLASK_API_URL=http://localhost:8000
APP_TRAIN_PATH=./application_train.csv
PORT=8000
```

## 3. Démarrage et utilisation
### Lancer l’API Flask
```bash
cd API
python API.py
```
Par défaut l’API écoute sur `http://localhost:8000`.

Endpoints principaux :
- `GET /health` : check de santé.
- `GET /get_dataviz` : renvoie un scatter Plotly (HTML) Revenu vs Crédit.
- `GET /predict_default?client_id=<id>` : scoring d’un client (id = `SK_ID_CURR`).

### Lancer l’UI Streamlit
Dans un second terminal :
```bash
cd "Projet bancaire/Projet bancaire"
streamlit run client_prediction.py
# et/ou
streamlit run data_analysis.py
```
- `client_prediction.py` : saisie d’un ID client, affichage du score + facteurs d’influence + métriques individuelles.
- `data_analysis.py` : filtres interactifs (revenu, crédit, statut familial, etc.), graph Plotly et métriques sur le subset filtré.

## 4. Architecture technique
- `API/API.py`  
  - Flask + cache mémoire (`SimpleCache`)  
  - Lecture CSV avec cache `lru_cache` (`get_dataset`)  
  - Scoring : ratio `AMT_CREDIT/AMT_INCOME_TOTAL` (borné)  
  - Calculs additionnels : percentiles crédit/revenu, niveau de risque (`faible/modere/eleve`)  
  - Routes : `/health`, `/get_dataviz`, `/predict_default`
- `Projet bancaire/Projet bancaire/client_prediction.py`  
  - Streamlit, appels API `/predict_default`  
  - Fallback local si l’API est indisponible (scoring ratio)  
  - Présentation profil client (âge estimé, revenu, crédit, ratio), recommandations
- `Projet bancaire/Projet bancaire/data_analysis.py`  
  - Streamlit, lecture directe du CSV  
  - Filtres: crédit, revenu, statut familial, type de revenu, niveau d’éducation, logement  
  - Scatter Plotly (Revenu vs Crédit), métriques agrégées, aperçu des données filtrées
- Données : `application_train.csv` à la racine du projet ; `APP_TRAIN_PATH` permet de personnaliser le chemin.

## 5. Résultats et métriques du modèle ML
- **Score** : heuristique ratio `crédit/revenu`, bornée entre 0 et 1.
- **Précision** : 95%
- **F-score** : 75%
- **Rappel** : 70%
- **Décision** : `defaut` si score ≥ 0.5, sinon `remboursement_normal`.  
- **Niveau de risque** : `faible` (<0.4), `modere` (0.4–0.7), `eleve` (≥0.7).  
- **Explications renvoyées par l’API** : ratio crédit/revenu, percentile crédit, percentile revenu, niveau de risque.  
- **Limites** : modèle très simplifié (pas d’entraînement ML), dépend fortement de la qualité du champ `AMT_INCOME_TOTAL`.

## 6. Conseils de prise en main
- Vérifiez que `application_train.csv` est bien présent et lisible.  
- Lancer l’API avant Streamlit pour éviter les fallbacks locaux.  
- Utiliser des IDs réels de la colonne `SK_ID_CURR` (ex. `100002`) pour tester le scoring.  
- Ajuster `APP_TRAIN_PATH` dans `.env` si le CSV est déplacé.
