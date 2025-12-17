import os
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

# Chargement des variables d'environnement (.env a la racine du projet)
load_dotenv()

API_BASE_URL = os.getenv("FLASK_API_URL", "http://localhost:8000").rstrip("/")
DEFAULT_DATA_PATH = Path(
    os.getenv("APP_TRAIN_PATH")
    or Path(__file__).resolve().parents[2] / "application_train.csv"
)

st.set_page_config(
    page_title="Prediction de Defaut Client",
    page_icon=":shield:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>

:root {
    --bleu: #1f4fd8;
    --vert: #2ecc71;
    --gris-clair: #f2f4f8;
    --gris-texte: #444;
}

html, body {
    background-color: var(--gris-clair);
    color: var(--gris-texte);
    font-family: Arial, sans-serif;
}

section.main { padding: 20px; }
h1, h2, h3 { color: var(--bleu); }

.card {
    background-color: #111;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    box-shadow: #f9f9f9;
}

.success { color: var(--vert); font-weight: bold; }
.warning { color: #e67e22; font-weight: bold; }

.stButton > button {
    background-color: var(--bleu);
    color: white;
    border-radius: 6px;
    border: none;
    padding: 8px 15px;
}
.stButton > button:hover { background-color: #163bb5; }

.avatar {
    width: 50px;
    height: 50px;
    background-color: #dde5ff;
    border-radius: 50%;
    text-align: center;
    line-height: 50px;
    font-weight: bold;
    color: var(--bleu);
}

@media (max-width: 768px) { .card-value { font-size: 18px; } }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_client_dataset(csv_path: Path) -> pd.DataFrame:
    """Charge le CSV principal (mise en cache pour eviter les relectures)."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {csv_path}")

    usecols = [
        "SK_ID_CURR",
        "AMT_CREDIT",
        "AMT_INCOME_TOTAL",
        "DAYS_BIRTH",
        "NAME_FAMILY_STATUS",
        "NAME_EDUCATION_TYPE",
        "NAME_HOUSING_TYPE",
        "NAME_INCOME_TYPE",
    ]
    return pd.read_csv(csv_path, usecols=usecols)


def filter_dataset(
    df: pd.DataFrame,
    min_credit: int,
    max_credit: int,
    min_income: int,
    status: str,
    income_type: str,
    property_status: str,
    education_level: str,
) -> pd.DataFrame:
    """Deprecated: on cible un utilisateur unique, filtre non utilise."""
    return df


def risk_level(score: float) -> str:
    if score >= 0.7:
        return "Eleve"
    if score >= 0.4:
        return "Modere"
    return "Faible"


def build_client_snapshot(row: pd.Series) -> dict:
    """Formate les infos clefs du client pour l'affichage."""
    income = float(row.get("AMT_INCOME_TOTAL", 0) or 0)
    credit = float(row.get("AMT_CREDIT", 0) or 0)
    ratio = round(credit / income, 2) if income > 0 else None

    age_years = None
    days_birth = row.get("DAYS_BIRTH")
    if pd.notna(days_birth):
        age_years = int(abs(float(days_birth)) // 365)

    return {
        "client_id": int(row.get("SK_ID_CURR")),
        "label": f"Client {int(row.get('SK_ID_CURR'))}",
        "age": age_years,
        "income": income if income else None,
        "credit": credit if credit else None,
        "ratio": ratio,
        "family": row.get("NAME_FAMILY_STATUS"),
        "education": row.get("NAME_EDUCATION_TYPE"),
        "housing": row.get("NAME_HOUSING_TYPE"),
        "income_type": row.get("NAME_INCOME_TYPE"),
    }


def build_influence_factors(info: dict) -> Tuple[List[str], List[str]]:
    """Genere quelques facteurs d'influence simples a afficher."""
    positives: List[str] = []
    negatives: List[str] = []

    if info.get("ratio") is not None:
        if info["ratio"] < 0.4:
            positives.append("Ratio credit/revenu maitrise.")
        elif info["ratio"] > 1.0:
            negatives.append("Montant du credit superieur au revenu annuel.")

    if info.get("income") and info["income"] > 250000:
        positives.append("Revenu annuel eleve.")

    if info.get("housing"):
        positives.append(f"Logement: {info['housing']}")

    return positives, negatives


def compute_local_risk(row: pd.Series) -> dict:
    """Calcule un score simple si l'API est indisponible."""
    income = float(row.get("AMT_INCOME_TOTAL", 0) or 0)
    credit = float(row.get("AMT_CREDIT", 0) or 0)
    ratio = credit / income if income > 0 else 0.5
    score = min(max(ratio / 5.0, 0), 1)

    return {
        "risk_score": round(score, 3),
        "risk_level": risk_level(score),
        "recommendation": "Score calcule localement sur le ratio credit/revenu.",
        "source": "local",
    }


def fetch_prediction_from_api(
    client_id: int, row: pd.Series
) -> Tuple[dict, Optional[str]]:
    """Appelle l'API Flask pour le scoring, avec un fallback local."""
    url = f"{API_BASE_URL}/predict_default"
    try:
        response = requests.get(url, params={"client_id": client_id}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            score = float(data.get("probability_default", 0))
            return (
                {
                    "risk_score": score,
                    "risk_level": risk_level(score),
                    "recommendation": data.get(
                        "explanation", "Recommandation issue de l'API."
                    ),
                    "source": "api",
                },
                None,
            )

        payload = response.json() if response.content else {}
        error_msg = payload.get("error") or f"API status {response.status_code}"
    except requests.RequestException as exc:
        error_msg = f"API indisponible: {exc}"

    return compute_local_risk(row), error_msg


def get_client_row(
    client_id_input: str, df: Optional[pd.DataFrame] = None
) -> Tuple[Optional[pd.Series], Optional[str]]:
    """Recupere la ligne du client dans le CSV (filtre optionnel)."""
    try:
        client_id_int = int(client_id_input)
    except ValueError:
        return None, "L'ID client doit etre numerique."

    base_df = df if df is not None else load_client_dataset(DEFAULT_DATA_PATH)
    row = base_df[base_df["SK_ID_CURR"] == client_id_int]
    if row.empty:
        return None, "Client introuvable dans application_train.csv (ou filtre trop restrictif)."
    return row.iloc[0], None


def display_client_cards(info: dict):
    """Affiche quelques indicateurs cles."""
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Age", f"{info['age']} ans" if info["age"] else "N/A")
    col_b.metric("Revenu annuel", f"{info['income']:,.0f}" if info["income"] else "N/A")
    col_c.metric("Montant credit", f"{info['credit']:,.0f}" if info["credit"] else "N/A")

    col_d, col_e = st.columns(2)
    col_d.metric("Ratio credit/revenu", f"{info['ratio']}" if info["ratio"] else "N/A")
    col_e.metric("Type de revenu", info.get("income_type") or "Non renseigne")


# =====================
# BARRE LATERALE
# =====================
try:
    base_df = load_client_dataset(DEFAULT_DATA_PATH)
except FileNotFoundError as exc:
    base_df = None
    st.sidebar.error(str(exc))

with st.sidebar:
    st.markdown(
        """
    <div style="text-align:center; margin-bottom:20px;">
        <div style="
            width:60px;
            height:60px;
            background-color:#1f4fd8;
            color:white;
            border-radius:50%;
            line-height:60px;
            font-size:24px;
            font-weight:bold;
            margin:auto;">
            RB
        </div>
        <h2 style="margin-top:10px;">Risk Banking</h2>
    </div>
    """,
        unsafe_allow_html=True,
    )

    client_id_input = st.text_input("ID client", placeholder="Ex : 100002")
    analyse = st.button("Analyser le risque")

    with st.expander("Aide"):
        st.markdown(
            """
        **Comment utiliser l'application :**
        1. Saisissez l'ID du client (colonne SK_ID_CURR du CSV)
        2. Cliquez sur **Analyser le risque**
        3. L'API Flask est appelee pour le scoring, sinon fallback local
        """
        )

# =====================
# PAGE
# =====================
main_container = st.container()

with main_container:
    if not analyse:
        st.markdown("## Outil de prediction de defaut client")
        st.markdown(
            """
        Bienvenue sur **Risk Banking**, un outil d'aide a la decision destine
        aux conseillers bancaires.

        ### Objectif de l'outil
        - Evaluer le risque de defaut d'un client
        - Comprendre les facteurs influencant la decision
        - Proposer des actions adaptees au niveau de risque
        """
        )
        st.markdown(
            """
        ### Pour commencer
        1. Appliquez des filtres ou saisissez un **ID client**
        2. Cliquez sur **Analyser le risque**
        3. Consultez les resultats detailles
        """
        )
        st.info(
            "L'outil lit application_train.csv et appelle l'API Flask pour le scoring."
        )

with main_container:
    if analyse:
        target_id = (client_id_input or "").strip()
        if target_id == "":
            st.warning("Veuillez saisir ou selectionner un ID client numerique.")
        else:
            with st.spinner("Chargement des donnees client..."):
                row, err = get_client_row(target_id, df=base_df)

            if err:
                st.error(err)
            else:
                client_info = build_client_snapshot(row)

                with st.spinner("Appel a l'API de scoring..."):
                    prediction, api_error = fetch_prediction_from_api(
                        client_info["client_id"], row
                    )

                header = st.container()
                with header:
                    col1, col2 = st.columns([1, 4])

                    with col1:
                        st.markdown('<div class="avatar"></div>', unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"## {client_info['label']}")
                        st.markdown(f"**ID Client :** {client_info['client_id']}")
                        st.markdown(
                            f"**Famille :** {client_info.get('family') or 'Non renseigne'}"
                        )

                st.markdown("### Score de risque")
                risk_score = min(max(prediction["risk_score"], 0), 1)
                st.progress(risk_score)
                st.markdown(
                    f"**Niveau de risque :** "
                    f"<span class='warning'>{prediction['risk_level']}</span>",
                    unsafe_allow_html=True,
                )

                if api_error:
                    st.warning(api_error)

                st.markdown("### Recommandation")
                st.markdown(
                    f"<div class='card'>{prediction['recommendation']}</div>",
                    unsafe_allow_html=True,
                )

                st.markdown("### Profil client")
                display_client_cards(client_info)

                pos, neg = build_influence_factors(client_info)
                st.markdown("### Facteurs d'influence")
                col_pos, col_neg = st.columns(2)
                with col_pos:
                    st.markdown("**Points positifs**")
                    if pos:
                        for f in pos:
                            st.markdown(f"- {f}")
                    else:
                        st.markdown("- Aucun point positif identifie.")

                with col_neg:
                    st.markdown("**Points de vigilance**")
                    if neg:
                        for f in neg:
                            st.markdown(f"- {f}")
                    else:
                        st.markdown("- Aucun point de vigilance majeur.")

                st.markdown("### Actions")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.button("Telecharger le rapport")
                with col_b:
                    st.button("Envoyer par email")
                with col_c:
                    st.button("Archiver l'analyse")
