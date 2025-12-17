import os
from pathlib import Path
from typing import Tuple

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DATASET_PATH = Path(
    os.getenv("APP_TRAIN_PATH")
    or Path(__file__).resolve().parents[2] / "application_train.csv"
)

st.set_page_config(
    page_title="Analyse Donnees Client",
    page_icon=":bar_chart:",
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

.card {
    background-color: white;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.warning { color: #e67e22; font-weight: bold; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_dataset(path: Path) -> pd.DataFrame:
    """Charge le CSV application_train."""
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def compute_ranges(df: pd.DataFrame) -> Tuple[int, int, int, int]:
    """Bornes min/max pour sliders."""
    credit_min, credit_max = int(df["AMT_CREDIT"].min()), int(df["AMT_CREDIT"].max())
    income_min, income_max = int(df["AMT_INCOME_TOTAL"].min()), int(df["AMT_INCOME_TOTAL"].max())
    return credit_min, credit_max, income_min, income_max


def filter_df(
    df: pd.DataFrame,
    credit_range: Tuple[int, int],
    income_range: Tuple[int, int],
    family_status: str,
    income_type: str,
    education: str,
    housing: str,
) -> pd.DataFrame:
    out = df[
        (df["AMT_CREDIT"] >= credit_range[0])
        & (df["AMT_CREDIT"] <= credit_range[1])
        & (df["AMT_INCOME_TOTAL"] >= income_range[0])
        & (df["AMT_INCOME_TOTAL"] <= income_range[1])
    ]
    if family_status != "Tous":
        out = out[out["NAME_FAMILY_STATUS"] == family_status]
    if income_type != "Tous":
        out = out[out["NAME_INCOME_TYPE"] == income_type]
    if education != "Tous":
        out = out[out["NAME_EDUCATION_TYPE"] == education]
    if housing != "Tous":
        out = out[out["NAME_HOUSING_TYPE"] == housing]
    return out


def plot_credit_income(df: pd.DataFrame):
    if df.empty:
        st.warning("Aucune donnée pour ces filtres.")
        return
    color = "TARGET" if "TARGET" in df.columns else None
    fig = px.scatter(
        df.sample(min(len(df), 5000), random_state=42),
        x="AMT_INCOME_TOTAL",
        y="AMT_CREDIT",
        color=color,
        labels={"AMT_INCOME_TOTAL": "Revenu", "AMT_CREDIT": "Crédit", "TARGET": "Défaut"},
        title="Montant du crédit vs revenu (échantillon)",
    )
    st.plotly_chart(fig, use_container_width=True)


def display_metrics(df: pd.DataFrame):
    total = len(df)
    avg_credit = df["AMT_CREDIT"].mean() if total else 0
    avg_income = df["AMT_INCOME_TOTAL"].mean() if total else 0
    ratio = (df["AMT_CREDIT"] / df["AMT_INCOME_TOTAL"]).mean() if total else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Clients filtrés", total)
    col2.metric("Crédit moyen", f"{avg_credit:,.0f}")
    col3.metric("Ratio crédit/revenu moyen", f"{ratio:.2f}")
    col4, col5 = st.columns(2)
    col4.metric("Revenu moyen", f"{avg_income:,.0f}")
    if "TARGET" in df.columns:
        default_rate = df["TARGET"].mean() * 100
        col5.metric("Taux de défaut", f"{default_rate:.1f}%")


# Chargement dataset
try:
    df_base = load_dataset(DATASET_PATH)
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

credit_min, credit_max, income_min, income_max = compute_ranges(df_base)

# Sidebar filtres
with st.sidebar:
    st.markdown("### Filtres")
    credit_range = st.slider(
        "Montant du crédit",
        min_value=credit_min,
        max_value=credit_max,
        value=(credit_min, min(credit_max, credit_min + 500000)),
        step=5000,
    )
    income_range = st.slider(
        "Revenu total",
        min_value=income_min,
        max_value=income_max,
        value=(income_min, min(income_max, income_min + 300000)),
        step=5000,
    )

    family_options = ["Tous"] + sorted(df_base["NAME_FAMILY_STATUS"].dropna().unique().tolist())
    income_options = ["Tous"] + sorted(df_base["NAME_INCOME_TYPE"].dropna().unique().tolist())
    education_options = ["Tous"] + sorted(df_base["NAME_EDUCATION_TYPE"].dropna().unique().tolist())
    housing_options = ["Tous"] + sorted(df_base["NAME_HOUSING_TYPE"].dropna().unique().tolist())

    family_status = st.selectbox("Statut familial", options=family_options)
    income_type = st.selectbox("Type de revenu", options=income_options)
    education = st.selectbox("Niveau d'éducation", options=education_options)
    housing = st.selectbox("Type de logement", options=housing_options)

    load_data = st.button("Appliquer les filtres")

# Contenu principal
st.title("Analyse de Données Crédit")

if not load_data:
    st.info(
        "Appliquez des filtres dans la barre latérale puis cliquez sur **Appliquer les filtres** "
        "pour explorer le fichier application_train.csv."
    )
else:
    filtered_df = filter_df(
        df_base,
        credit_range=credit_range,
        income_range=income_range,
        family_status=family_status,
        income_type=income_type,
        education=education,
        housing=housing,
    )

    st.markdown(
        f"**Clients correspondants : {len(filtered_df)}** — crédits entre {credit_range[0]:,.0f} "
        f"et {credit_range[1]:,.0f}, revenus entre {income_range[0]:,.0f} et {income_range[1]:,.0f}."
    )

    display_metrics(filtered_df)
    plot_credit_income(filtered_df)

    st.markdown("### Aperçu des données filtrées")
    st.dataframe(filtered_df[["SK_ID_CURR", "AMT_CREDIT", "AMT_INCOME_TOTAL", "NAME_FAMILY_STATUS"]].head(20))
