import os
import time
from pathlib import Path
from typing import Any, Dict

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("FLASK_API_URL", "http://localhost:8000").rstrip("/")
DATASET_PATH = os.getenv("APP_TRAIN_PATH") or str(
    Path(__file__).resolve().parents[2] / "application_train.csv"
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

.warning {
    color: #e67e22;
    font-weight: bold;
}
</style>
""",
    unsafe_allow_html=True,
)

ANALYSES: Dict[int, Dict[str, str]] = {
    1: {
        "title": "Age client et defaut",
        "description": "Analyse de l'age et du risque de defaut.",
        "interpretation": "Les clients plus jeunes peuvent presenter un risque legerement plus eleve.",
    },
    2: {
        "title": "Revenus et risque de defaut",
        "description": "Relation entre revenus et probabilite de defaut.",
        "interpretation": "Un revenu plus faible est souvent associe a un risque plus eleve.",
    },
    3: {
        "title": "Endettement et defaut",
        "description": "Analyse du taux d'endettement des clients.",
        "interpretation": "Un taux d'endettement eleve augmente le risque de defaut.",
    },
}


@st.cache_data(ttl=600, show_spinner=False)
def load_credit_analysis_data(
    analysis_type: int,
    min_credit: int,
    max_credit: int,
    min_income: int,
    status: str,
    income_type: str,
    property_status: str,
    education_level: str,
) -> Dict[str, Any]:
    """Recupere le graphique depuis l'API Flask."""
    url = f"{API_BASE_URL}/get_dataviz"
    params = {
        "analysis_type": analysis_type,
        "min_credit": min_credit,
        "max_credit": max_credit,
        "min_income": min_income,
        "path": DATASET_PATH,
        "status": status,
        "income_type": income_type,
        "property_status": property_status,
        "education_level": education_level,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return {"status": "success", "content": response.json(), "type": "json"}
        return {"status": "success", "content": response.text, "type": "html"}
    except requests.RequestException as exc:
        return {"status": "error", "content": str(exc), "type": "text"}


def display_plotly_chart(html_content: str):
    """Affiche un graphique Plotly en HTML."""
    st.components.v1.html(html_content, height=600, scrolling=True)


def display_key_metrics(analysis_type: int):
    """Metrices placeholder pour chaque analyse."""
    if analysis_type == 1:
        st.metric("Age median", "43 ans")
        st.metric("Age minimum risque", "25-34 ans")
        st.metric("Age maximum risque", "55-64 ans")
    elif analysis_type == 2:
        st.metric("Revenu moyen", "38 000")
        st.metric("Credit moyen", "22 500")
        st.metric("Ratio credit/revenu", "0.59")
    elif analysis_type == 3:
        st.metric("Probabilite de defaut", "12%")
        st.metric("Clients haut risque", "120")
        st.metric("Clients faible risque", "480")


def display_recommendations(analysis_type: int):
    """Affiche quelques recommandations statiques par analyse."""
    if analysis_type == 1:
        st.info("- Surveiller les clients 45-54 ans\n- Adapter les offres pour les jeunes adultes")
    elif analysis_type == 2:
        st.info("- Ajuster les limites de credit selon le revenu\n- Identifier les profils a haut risque")
    elif analysis_type == 3:
        st.info("- Prioriser le suivi des profils a forte probabilite de defaut\n- Proposer des plans de remboursement adaptes")


def display_active_filters(
    min_credit: int,
    max_credit: int,
    min_income: int,
    status: str,
    income_type: str,
    property_status: str,
    education_level: str,
):
    cols = st.columns(4)
    cols[0].markdown(f"**Credit min**: {min_credit}")
    cols[1].markdown(f"**Credit max**: {max_credit}")
    cols[2].markdown(f"**Revenu min**: {min_income}")
    cols[3].markdown(f"**Statut familial**: {status}")
    cols = st.columns(3)
    cols[0].markdown(f"**Type de revenu**: {income_type}")
    cols[1].markdown(f"**Statut propriete**: {property_status}")
    cols[2].markdown(f"**Niveau education**: {education_level}")


# =====================
# BARRE LATERALE
# =====================
with st.sidebar:
    st.markdown("### Analyse client")
    analysis_choice = st.selectbox(
        "Type d'analyse",
        options=list(ANALYSES.keys()),
        format_func=lambda x: f"{x} - {ANALYSES[x]['title']}",
    )

    min_credit = st.number_input("Montant minimum de credit", min_value=0, value=1000, step=500)
    max_credit = st.number_input("Montant maximum de credit", min_value=0, value=50000, step=500)
    min_income = st.number_input("Revenu minimum annuel", min_value=0, value=20000, step=1000)

    status_options = st.selectbox(
        "Statut familial",
        options=["Non specifie", "Celibataire", "Marie.e", "Divorce.e", "Veuf.ve", "Pacs"],
        index=0,
    )

    income_type = st.selectbox(
        "Type de revenu",
        options=["Non specifie", "Salaire", "Independant", "Retraite", "Fonctionnaire", "Autre"],
        index=0,
    )

    property_status = st.selectbox(
        "Statut propriete",
        options=["Non specifie", "Proprietaire", "Locataire", "Chez les parents", "Autre"],
        index=0,
    )

    education_level = st.selectbox(
        "Niveau d'education",
        options=["Non specifie", "Inferieur au Bac", "Bac", "Bac + 2", "Bac + 3", "Bac + 5", "Autre"],
        index=0,
    )

    load_data = st.button("Charger l'analyse")

    with st.expander("Aide"):
        st.markdown(
            """
        1. Choisissez le type d'analyse
        2. Ajustez les filtres
        3. Cliquez sur **Charger l'analyse** (les donnees viennent de l'API Flask)
        """
        )

# =====================
# CONTENU PRINCIPAL
# =====================
main_container = st.container()

with main_container:
    if not load_data:
        st.title("Bienvenue sur l'analyse client")
        st.write(
            "Cette page interroge l'API Flask (`/get_dataviz`) en utilisant le fichier "
            f"`application_train.csv` situe ici : `{DATASET_PATH}`."
        )

        st.subheader("Analyses disponibles")
        for key, val in ANALYSES.items():
            st.markdown(f"- **{key}. {val['title']}** : {val['description']}")
    else:
        analysis = ANALYSES[analysis_choice]
        st.header(analysis["title"])
        st.write(analysis["description"])

        display_active_filters(
            min_credit,
            max_credit,
            min_income,
            status_options,
            income_type,
            property_status,
            education_level,
        )

        progress_text = "Chargement des donnees depuis l'API..."
        progress_bar = st.progress(0, text=progress_text)
        for step in range(0, 101, 25):
            time.sleep(0.05)
            progress_bar.progress(step, text=progress_text)

        result = load_credit_analysis_data(
            analysis_type=analysis_choice,
            min_credit=min_credit,
            max_credit=max_credit,
            min_income=min_income,
            status=status_options,
            income_type=income_type,
            property_status=property_status,
            education_level=education_level,
        )

        if result["status"] == "success":
            if result["type"] == "html":
                display_plotly_chart(result["content"])
            else:
                st.json(result["content"])

            st.subheader("Metriques cles")
            display_key_metrics(analysis_choice)

            st.info(analysis["interpretation"])
            display_recommendations(analysis_choice)

            st.download_button(
                label="Telecharger un echantillon CSV",
                data="id;credit;income\nC001;10000;35000\nC002;15000;42000",
                file_name="analyse_client.csv",
                mime="text/csv",
            )
        else:
            st.error(f"Impossible de charger l'analyse : {result['content']}")
