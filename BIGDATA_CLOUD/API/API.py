"""
- TP : API Flask - Middleware entre Streamlit et Databricks (version locale simplifiée).
- Routes attendues : /health, /get_dataviz, /predict_default.
- Objectif pédagogique : montrer un middleware Flask avec cache, dataviz, et scoring simple.
- Cette version garde les consignes lisibles tout en restant autonome (pas d’appels Databricks).

Flask API middleware (simple, self-contained).
- /health           : liveness check
- /get_dataviz      : renvoie un graphique Plotly HTML basé sur un dataset local
- /predict_default  : calcule une probabilité de défaut très simplifiée

Ce fichier est volontairement minimal et compréhensible. Les appels Databricks
ont été remplacés par des fonctions locales pour éviter tout secret et faciliter
les tests.
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from functools import lru_cache, wraps
from typing import Any, Dict, Optional

# Auto-install des dépendances pour garantir les imports
import subprocess
import sys

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "flask", "flask-caching", "python-dotenv", "pandas", "plotly"],
    check=False,
)

import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response
from flask_caching import Cache

load_dotenv()


# --------------------------------------------------------------------------- #
# Flask + cache
# --------------------------------------------------------------------------- #
app = Flask(__name__)
app.config.from_mapping(
    {
        "DEBUG": True,
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 900,  # 15 min
    }
)
cache = Cache(app)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def api_error_handler(func):
    """Decorateur simple pour uniformiser les erreurs JSON."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - garde-fou global
            app.logger.exception("API error")
            return jsonify({"error": str(exc)}), 500

    return wrapper


def load_dataset(path: str) -> pd.DataFrame:
    """Charge un CSV local ou renvoie un DataFrame vide si absent."""
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


@lru_cache(maxsize=4)
def get_dataset(path: str) -> pd.DataFrame:
    """Cache basique pour le CSV principal afin d'eviter les relectures."""
    return load_dataset(path)


def build_simple_plot(df: pd.DataFrame) -> str:
    """Construit une figure Plotly HTML basique."""
    if df.empty or not {"AMT_CREDIT", "AMT_INCOME_TOTAL"}.issubset(df.columns):
        fig = px.scatter(x=[0], y=[0], title="Dataset vide ou colonnes manquantes")
    else:
        fig = px.scatter(
            df,
            x="AMT_INCOME_TOTAL",
            y="AMT_CREDIT",
            title="Montant de crédit vs revenu",
            labels={"AMT_INCOME_TOTAL": "Revenu", "AMT_CREDIT": "Crédit"},
        )
    return fig.to_html(include_plotlyjs="cdn", full_html=True)


def simple_risk_score(row: pd.Series) -> float:
    """Score très simplifié : ratio crédit/revenu, borné entre 0 et 1."""
    credit = float(row.get("AMT_CREDIT", 0) or 0)
    income = float(row.get("AMT_INCOME_TOTAL", 0) or 0)
    if income <= 0:
        return 0.5  # inconnu => neutre
    ratio = min(credit / income, 5.0)  # borne pour éviter l’explosion
    return round(min(ratio / 5.0, 1.0), 3)


def compute_percentile(series: pd.Series, value: float) -> Optional[float]:
    """Calcule un percentile approximatif d'une valeur dans une série."""
    if series is None or series.empty:
        return None
    try:
        pct = (series < value).mean() * 100
        return round(float(pct), 1)
    except Exception:
        return None


def format_prediction(row: pd.Series, score: float, df: pd.DataFrame) -> Dict[str, Any]:
    """Formate la prédiction en exploitant les données du CSV application_train."""
    decision = "defaut" if score >= 0.5 else "remboursement_normal"
    client_id = row.get("SK_ID_CURR", "inconnu")
    try:
        client_id = int(client_id)
    except Exception:
        client_id = str(client_id)

    credit = float(row.get("AMT_CREDIT", 0) or 0)
    income = float(row.get("AMT_INCOME_TOTAL", 0) or 0)
    ratio = round(credit / income, 3) if income > 0 else None

    pct_credit = compute_percentile(df.get("AMT_CREDIT"), credit)
    pct_income = compute_percentile(df.get("AMT_INCOME_TOTAL"), income)
    risk_level = "eleve" if score >= 0.7 else "modere" if score >= 0.4 else "faible"

    explanation_parts = [
        f"Ratio credit/revenu = {ratio}" if ratio is not None else "Ratio non calculable",
        f"Credit percentile ~ {pct_credit}%" if pct_credit is not None else "Percentile credit indisponible",
        f"Revenu percentile ~ {pct_income}%" if pct_income is not None else "Percentile revenu indisponible",
    ]

    return {
        "client_id": client_id,
        "probability_default": float(score),
        "prediction": str(decision),
        "risk_level": risk_level,
        "ratio_credit_income": ratio,
        "credit_percentile": pct_credit,
        "income_percentile": pct_income,
        "explanation": " | ".join(explanation_parts),
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200


@app.route("/get_dataviz", methods=["GET"])
@cache.cached(timeout=600, query_string=True)
@api_error_handler
def get_dataviz():
    """
    Génère un scatter Plotly basé sur un CSV local (application_train.csv).
    Query params optionnels:
      - path: chemin vers le CSV (sinon application_train.csv à la racine du projet)
    """
    csv_path = request.args.get("path", os.path.join(os.path.dirname(__file__), "..", "application_train.csv"))
    df = get_dataset(csv_path)
    html = build_simple_plot(df)
    return Response(html, mimetype="text/html")


@app.route("/predict_default", methods=["GET"])
@cache.cached(timeout=300, query_string=True)
@api_error_handler
def predict_default():
    """
    Calcule une probabilité de défaut sur un client sélectionné.
    Query params:
      - client_id: identifiant dans le CSV
      - path: chemin vers le CSV (sinon application_train.csv à la racine du projet)
    """
    client_id = request.args.get("client_id", type=int)
    csv_path = request.args.get("path", os.path.join(os.path.dirname(__file__), "..", "application_train.csv"))
    df = get_dataset(csv_path)

    if df.empty:
        return jsonify({"error": "Dataset introuvable ou vide"}), 400
    if client_id is None:
        return jsonify({"error": "Paramètre client_id requis"}), 400

    row = df[df["SK_ID_CURR"] == client_id]
    if row.empty:
        return jsonify({"error": f"Client {client_id} introuvable"}), 404

    row = row.iloc[0]
    score = simple_risk_score(row)
    result = format_prediction(row, score, df)
    return jsonify(result), 200


# --------------------------------------------------------------------------- #
# Entrée CLI
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
