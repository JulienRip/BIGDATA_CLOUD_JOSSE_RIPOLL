import streamlit as st
import requests
from streamlit.components.v1 import html
import pandas as pd
import json
import os
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import time
from datetime import datetime


# Charger les variables d'environnement
load_dotenv()

st.set_page_config(
    page_title="Prédiction de Défaut Client",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>

/* =====================
   VARIABLES DE COULEURS
   ===================== */
:root {
    --bleu: #1f4fd8;
    --vert: #2ecc71;
    --gris-clair: #f2f4f8;
    --gris-texte: #444;
}

/* =====================
   STYLE GLOBAL
   ===================== */
html, body {
    background-color: var(--gris-clair);
    color: var(--gris-texte);
    font-family: Arial, sans-serif;
}

section.main {
    padding: 20px;
}

/* =====================
   TITRES
   ===================== */
h1, h2, h3 {
    color: var(--bleu);
}

/* =====================
   CARTES SIMPLES
   ===================== */
.card {
    background-color: white;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 15px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.card-title {
    font-weight: bold;
    margin-bottom: 5px;
}

.card-value {
    font-size: 20px;
}

/* =====================
   INDICATEURS
   ===================== */
.success {
    color: var(--vert);
    font-weight: bold;
}

.warning {
    color: #e67e22;
    font-weight: bold;
}

/* =====================
   BOUTONS
   ===================== */
.stButton > button {
    background-color: var(--bleu);
    color: white;
    border-radius: 6px;
    border: none;
    padding: 8px 15px;
}

.stButton > button:hover {
    background-color: #163bb5;
}

/* =====================
   AVATAR CLIENT 
   ===================== */
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

/* =====================
   RESPONSIVE SIMPLE
   ===================== */
@media (max-width: 768px) {
    .card-value {
        font-size: 18px;
    }
}

</style>
""", unsafe_allow_html=True)

# =====================
# BARRE LATERALE
# =====================
with st.sidebar:

    # Logo
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # Champ ID client
    client_id = st.text_input(
        "ID client",
        placeholder="Ex : C12345"
    )

    # Bouton d'action
    analyse = st.button("Analyser le risque")

    # Panneau d'aide rétractable
    with st.expander("Aide"):
        st.markdown("""
        **Comment utiliser l'application :**
        1. Saisissez l'ID du client dans le champ prévu
        2. Cliquez sur **Analyser le risque**
        3. Consultez les résultats sur le tableau de bord

        Assurez-vous que l'ID client est valide.
        """)

# =====================
# UTILISATION DANS LA PAGE
# =====================
if analyse:
    if client_id == "":
        st.warning("Veuillez saisir un ID client.")
    else:
        st.success(f"Analyse du risque pour le client **{client_id}** en cours...")

# =====================
# FONCTION POUR RECUPERATION INFOS CLIENT
# =====================

def get_client_personal_data(client_id):

    client = None

    try:
        # Connexion à MongoDB
        client = MongoClient(MONGODB_URI)

        # Accès à la base et à la collection -- qui n'existe pas
        db = client["risk_banking"]
        collection = db["clients"]

        # Requête sur la clé SK_CURR_ID
        result = collection.find_one({"SK_CURR_ID": client_id})

        if result is None:
            return None

        # Formatage des données retournées
        client_data = {
            "FirstName": result.get("FirstName", "Non renseigné"),
            "LastName": result.get("LastName", "Non renseigné"),
            "PhotoURL": result.get("PhotoURL", None)
        }

        return client_data

    except Exception as e:
        # erreur utile pour les logs
        raise Exception(f"Erreur MongoDB : {e}")

    finally:
        # Fermeture obligatoire de la connexion
        if client is not None:
            client.close()

# =====================
# PAGE
# =====================
main_container = st.container()

with main_container:
    if not analyse:
        st.markdown("## Outil de prédiction de défaut client")

        st.markdown("""
        Bienvenue sur **Risk Banking**, un outil d'aide à la décision destiné
        aux conseillers bancaires.

        ### Objectif de l'outil
        - Évaluer le risque de défaut d'un client
        - Comprendre les facteurs influençant la décision
        - Proposer des actions adaptées au niveau de risque
        """)

        st.markdown("""
        ### Pour commencer
        1. Saisissez l'**ID client** dans la barre latérale
        2. Cliquez sur **Analyser le risque**
        3. Consultez les résultats détaillés
        """)

        st.info("L'outil permet une analyse rapide, explicable et orientée décision.")

def predict_default_risk(client_id):
    """
    Fonction simulée de prédiction du risque de défaut
    """
    return {
        "risk_score": 0.72,
        "risk_level": "Élevé",
        "recommendation": "Risque important détecté. Surveillance renforcée recommandée.",
        "positive_factors": [
            "Ancienneté client élevée",
            "Historique de paiement stable"
        ],
        "negative_factors": [
            "Revenus faibles",
            "Taux d'endettement élevé"
        ]
    }

with main_container:
    if analyse and client_id != "":

        # =====================
        # APPELS AUX DONNEES
        # =====================
        client_data = get_client_personal_data(client_id)
        prediction = predict_default_risk(client_id)

        if client_data is None:
            st.error("Client introuvable.")
        else:
            # =====================
            # EN-TÊTE CLIENT
            # =====================
            header = st.container()
            with header:
                col1, col2 = st.columns([1, 4])

                with col1:
                    if client_data["PhotoURL"]:
                        st.image(client_data["PhotoURL"], width=120)
                    else:
                        st.markdown('<div class="avatar"></div>', unsafe_allow_html=True)

                with col2:
                    st.markdown(f"## {client_data['FirstName']} {client_data['LastName']}")
                    st.markdown(f"**ID Client :** {client_id}")

            # =====================
            # SCORE DE RISQUE (JAUGE SIMPLE)
            # =====================
            st.markdown("### Score de risque")

            risk_score = prediction["risk_score"]
            st.progress(risk_score)

            st.markdown(
                f"**Niveau de risque :** "
                f"<span class='warning'>{prediction['risk_level']}</span>",
                unsafe_allow_html=True
            )

            # =====================
            # RECOMMANDATION PRINCIPALE
            # =====================
            st.markdown("### Recommandation")
            st.markdown(
                f"<div class='card'>{prediction['recommendation']}</div>",
                unsafe_allow_html=True
            )

            # =====================
            # FACTEURS D'INFLUENCE
            # =====================
            st.markdown("### Facteurs d'influence")

            col_pos, col_neg = st.columns(2)

            with col_pos:
                st.markdown("**Facteurs positifs**")
                for f in prediction["positive_factors"]:
                    st.markdown(f"- ✅ {f}")

            with col_neg:
                st.markdown("**Facteurs négatifs**")
                for f in prediction["negative_factors"]:
                    st.markdown(f"- ❌ {f}")

            # =====================
            # ACTIONS RECOMMANDEES
            # =====================
            st.markdown("### Actions recommandées")

            st.markdown("""
            - Proposer un accompagnement personnalisé
            - Réévaluer la capacité de remboursement
            - Limiter l'exposition au risque
            """)

            # =====================
            # BOUTONS D'ACTION
            # =====================
            st.markdown("### Actions")

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.button("Télécharger le rapport")

            with col_b:
                st.button("Envoyer par email")

            with col_c:
                st.button("Archiver l'analyse")


