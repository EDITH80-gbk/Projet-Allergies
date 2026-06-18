import os
import sqlite3
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Allergen Chip Challenge Dashboard", layout="wide"
)
st.title("📊 Tableau de Bord - Analyse des Allergies")

# --- CHARGEMENT DES DONNÉES ---
import os
from pathlib import Path

# Détermine le dossier racine du projet (projet-allergies)
BASE_DIR = Path(__file__).resolve().parent.parent

# Construit le chemin vers la base de données de manière propre
db_path = os.path.join(BASE_DIR, "data", "allergen_chip_challenge.db")

# Vérification de l'existence de la bdd pour éviter un crash
if not os.path.exists(db_path):
    st.error(
        f"Base de données introuvable au chemin : {os.path.abspath(db_path)}"
    )
    st.stop()


@st.cache_data
def load_data(path):
    conn = sqlite3.connect(path)
    df_local = pd.read_sql("Select * From allergies_categories", conn)
    conn.close()
    return df_local


df = load_data(db_path)

# --- CONFIGURATION ET PARAMÈTRES ---
colonnes_metadonnees = [
    "Patient_ID",
    "Chip_Type",
    "Age",
    "Gender",
    "Blood_Month_sample",
    "Region",
    "Rural_area",
    "Sensitization",
    "Treatment_of_rhinitis",
    "Treatment_of_asthma",
    "Age_of_onsets",
    "Skin_Symptoms",
    "General_cofactors",
    "Treatment_of_atopic_dematitis",
]
colonnes_familles = [
    "Pollens",
    "Aliments",
    "Acariens/Blattes",
    "Animaux",
    "Moisissures/Autres",
]

sns.set_theme(style="whitegrid")
plt.rcParams.update({"font.size": 11, "axes.labelsize": 12, "axes.titlesize": 14})

df_scores_categories = df.drop(columns=colonnes_metadonnees, errors="ignore")

# --- PRÉ-CALCULS DES KPIS ---
SEUIL_POSITIVITE = 0.35
df["nb_familles_positives"] = (df[colonnes_familles] >= SEUIL_POSITIVITE).sum(
    axis=1
)

SEUIL_POLY = 2
nb_patients_polysensibilises = (df["nb_familles_positives"] >= SEUIL_POLY).sum()
total_patients = len(df)
taux_polysensibilisation = (nb_patients_polysensibilises / total_patients) * 100

# --- AFFICHAGE DES TOP KPIS ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Patients Analysés", value=total_patients)
with col2:
    st.metric(
        label="Patients Polysensibilisés (>= 2 familles)",
        value=nb_patients_polysensibilises,
    )
with col3:
    st.metric(
        label="Taux de Polysensibilisation Globale",
        value=f"{taux_polysensibilisation:.2f}%",
    )

st.markdown("---")

# --- CRÉATION DES ONGLETS DE NAVIGATION ---
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📈 Prévalence & Distribution",
        "🧬 Co-Sensibilisation (ICM)",
        "🍕 Répartition Globale",
        "🌍 Analyses Démographiques",
    ]
)

# ==========================================
# ONGLET 1 : PRÉVALENCE & DISTRIBUTION
# ==========================================
with tab1:
    st.header("Analyse de la Prévalence et des taux d'IgE")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("Taux de Prévalence")
        seuil_positif_prev = 0.3
        prevalence = (df_scores_categories >= seuil_positif_prev).mean() * 100
        prevalence = prevalence.sort_values(ascending=False)

        fig1, ax1 = plt.subplots(figsize=(10, 6))
        colors = sns.color_palette("viridis", len(prevalence))
        bars = ax1.bar(
            prevalence.index,
            prevalence.values,
            color=colors,
            edgecolor="grey",
            alpha=0.85,
        )
        ax1.set_title(
            "Prévalence de la sensibilisation par catégorie d'allergènes\n(% de patients avec IgE ≥ 0.3 ISU)",
            pad=15,
            fontweight="bold",
        )
        ax1.set_ylabel("Pourcentage de patients (%)")
        ax1.set_xlabel("Catégories d'allergènes")
        ax1.set_ylim(0, 100)

        for bar in bars:
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 2,
                f"{height:.1f}%",
                ha="center",
                va="bottom",
                fontweight="bold",
            )
        plt.tight_layout()
        st.pyplot(fig1)

    with col_g2:
        st.subheader("Distribution des taux d'IgE")
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        df_long = df_scores_categories.melt(
            var_name="Catégorie", value_name="IgE Max (ISU)"
        )
        sns.boxplot(
            x="Catégorie",
            y="IgE Max (ISU)",
            data=df_long,
            palette="Set2",
            hue="Catégorie",
            ax=ax2,
            legend=False,
        )
        ax2.set_title(
            "Distribution et Intensité des taux d'IgE Maximaux",
            pad=15,
            fontweight="bold",
        )
        ax2.set_ylabel("Niveau d'IgE Spécifique Max (ISU)")
        ax2.set_xlabel("Catégories")
        ax2.set_yscale("symlog", linthresh=0.3)
        ax2.grid(True, which="both", ls="--", alpha=0.5)
        plt.tight_layout()
        st.pyplot(fig2)

# ==========================================
# ONGLET 2 : MATRICE DE CO-SENSIBILISATION
# ==========================================
with tab2:
    st.header("Matrice de Co-sensibilisation Moléculaire (ICM)")

    icm_matrix = df[colonnes_familles].corr(method="spearman")

    col_mat1, col_mat2 = st.columns([1, 2])

    with col_mat1:
        st.write("### Valeurs de la matrice (Spearman rho)")
        st.dataframe(icm_matrix.round(2), use_container_width=True)

    with col_mat2:
        fig3, ax3 = plt.subplots(figsize=(8, 7))
        masque = np.triu(np.ones_like(icm_matrix, dtype=bool))

        sns.heatmap(
            icm_matrix,
            mask=masque,
            annot=True,  # Activé ici car il n'y a que 5 familles de définies dans votre liste
            fmt=".2f",
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            square=True,
            linewidths=0.5,
            cbar_kws={"label": "Force de l'Indice (Spearman rho)"},
            ax=ax3,
        )
        ax3.set_title(
            "Heatmap de l'Indice de Co-sensibilisation",
            fontsize=14,
            fontweight="bold",
            pad=15,
        )
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        st.pyplot(fig3)

# ==========================================
# ONGLET 3 : CAMEMBERT GLOBAL
# ==========================================
with tab3:
    st.header("Proportion de la Polysensibilisation")

    fig4, ax4 = plt.subplots(figsize=(6, 5))
    labels_poly = [
        f"Polysensibilisés\n({nb_patients_polysensibilises} patients)",
        "Mono ou Non-sensibilisés",
    ]
    sizes_poly = [taux_polysensibilisation, 100 - taux_polysensibilisation]
    colors_poly = ["#e74c3c", "#bdc3c7"]

    ax4.pie(
        sizes_poly,
        labels=labels_poly,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors_poly,
        explode=(0.05, 0),
        textprops={"fontsize": 11, "weight": "bold"},
    )
    ax4.set_title(
        "Taux de Polysensibilisation\n(Sur l'ensemble de la cohorte)",
        fontsize=13,
        pad=20,
        weight="bold",
    )
    plt.tight_layout()
    st.pyplot(fig4)

# ==========================================
# ONGLET 4 : DEMOGRAPHIE (AGE & GEOGRAPHIE)
# ==========================================
with tab4:
    st.header("Analyses Démographiques de la Polysensibilisation")

    df_analyse = df.copy()
    df_analyse["Est_Polysensibilise"] = df_analyse["nb_familles_positives"] >= 2

    kpi_age = (
        df_analyse.groupby("Age", observed=False)["Est_Polysensibilise"].mean()
        * 100
    )
    kpi_geo = (
        df_analyse.groupby("Region")["Est_Polysensibilise"].mean() * 100
    ).sort_values(ascending=False)

    top_geo = kpi_geo.head(5)
    bottom_geo = kpi_geo.tail(5)

    # Graphique Âge
    st.subheader("Taux de Polysensibilisation par Âge")
    fig5, ax5 = plt.subplots(figsize=(10, 4))
    sns.barplot(
        x=kpi_age.index, y=kpi_age.values, ax=ax5, palette="Blues_r", hue=kpi_age.index, legend=False
    )
    ax5.set_ylabel("Pourcentage (%)")
    ax5.set_xlabel("Tranche d'âge")
    for i, v in enumerate(kpi_age.values):
        ax5.text(i, v + 1, f"{v:.1f}%", ha="center", weight="bold")
    st.pyplot(fig5)

    # Graphiques Géographie Côte-à-Côte
    st.subheader("Impact Géographique")
    col_geo1, col_geo2 = st.columns(2)

    with col_geo1:
        fig6, ax6 = plt.subplots(figsize=(8, 5))
        sns.barplot(
            x=top_geo.index, y=top_geo.values, ax=ax6, palette="Oranges_r", hue=top_geo.index, legend=False
        )
        ax6.set_title("Top 5 des Régions les plus Touchées", weight="bold")
        ax6.set_ylabel("Taux (%)")
        plt.xticks(rotation=30, ha="right")
        for i, v in enumerate(top_geo.values):
            ax6.text(i, v + 1, f"{v:.1f}%", ha="center", weight="bold")
        st.pyplot(fig6)

    with col_geo2:
        fig7, ax7 = plt.subplots(figsize=(8, 5))
        sns.barplot(
            x=bottom_geo.index, y=bottom_geo.values, ax=ax7, palette="GnBu_r", hue=bottom_geo.index, legend=False
        )
        ax7.set_title("Top 5 des Régions les moins Touchées", weight="bold")
        ax7.set_ylabel("Taux (%)")
        plt.xticks(rotation=30, ha="right")
        for i, v in enumerate(bottom_geo.values):
            ax7.text(i, v + 1, f"{v:.1f}%", ha="center", weight="bold")
        st.pyplot(fig7)