import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sqlite3
import seaborn as sns
import streamlit as st
import os

# Dans le fichier BRUT, il y a 4,271 lignes. On a nettoyé ce fichier.
# Dans le fichier CLEAN, il y a 4,145 lignes.
db_path = "../data/allergen_chip_challenge.db"

# On va lire les données allergies directement depuis la table dans la base de données :
conn = sqlite3.connect(db_path)

df = pd.read_sql("Select * From allergies_categories", conn)
conn.close()

print("Current directory :", os.getcwd())
print("Database path :", db_path)

# Identification des colonnes de métadonnées des patients (à ne pas sommer)
colonnes_metadonnees = [
    'Patient_ID', 'Chip_Type', 'Age', 'Gender', 'Blood_Month_sample', 'Region', 'Rural_area', 
    'Sensitization', 'Treatment_of_rhinitis', 'Treatment_of_asthma', 'Age_of_onsets', 'Skin_Symptoms', 
    'General_cofactors', 'Treatment_of_atopic_dematitis'
]

sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 14})


# --- Graphique 1 : Taux de Prévalence --- KPI 1

df_scores_categories = df.drop(columns=colonnes_metadonnees)
seuil_positif = 0.3
prevalence = (df_scores_categories >= seuil_positif).mean() * 100
prevalence = prevalence.sort_values(ascending=False)

plt.figure(figsize=(10, 6))
colors = sns.color_palette("viridis", len(prevalence))
bars = plt.bar(prevalence.index, prevalence.values, color=colors, edgecolor='grey', alpha=0.85)

# Habillage du graphique
plt.title("Prévalence de la sensibilisation par catégorie d'allergènes\n(% de patients avec IgE ≥ 0.3 ISU)", pad=15, fontweight='bold')
plt.ylabel("Pourcentage de patients (%)")
plt.xlabel("Catégories d'allergènes")
plt.ylim(0, 100)

# Ajout des étiquettes de valeurs sur chaque barre
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 2, f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.show() 


# --- Graphique 2 : Distribution des taux d'IgE ---

plt.figure(figsize=(10, 6))
df_long = df_scores_categories.melt(var_name="Catégorie", value_name="IgE Max (ISU)")
sns.boxplot(x="Catégorie", y="IgE Max (ISU)", data=df_long, palette="Set2", hue="Catégorie")

plt.title("Distribution et Intensité des taux d'IgE Maximaux par Catégorie", pad=15, fontweight='bold')
plt.ylabel("Niveau d'IgE Spécifique Max (ISU)")
plt.xlabel("Catégories")
plt.yscale('symlog', linthresh=0.3)
plt.grid(True, which="both", ls="--", alpha=0.5)

plt.tight_layout()
plt.show()


# 1. IDENTIFICATION DU TOP 10 DES ALLERGÈNES LES PLUS PRÉVALENTS
# ==============================================================================
SEUIL_POSITIVITE = 0.30

# On isole le nom des 10 allergènes les plus fréquents
top_10_allergenes = prevalence.nlargest(10).index.tolist()

# ==============================================================================
# 2. CALCUL DE LA MATRICE DE CORRÉLATION (SPEARMAN)
# ==============================================================================
# On filtre le DataFrame pour ne garder que nos 10 colonnes cibles
df_top_10 = df_scores_categories[top_10_allergenes]

# 1. Sélection automatique de toutes les colonnes de familles (qui commencent par 'Score_')
colonnes_familles = ['Pollens', 'Aliments', 'Acariens/Blattes', 'Animaux', 'Moisissures/Autres']

# Seuil de positivité biologique (standard en allergologie moléculaire)
SEUIL_POSITIVITE = 0.35

# ==============================================================================
# KPI 2 : CALCUL DU TAUX DE POLYSENSIBILISATION (TPS)
# ==============================================================================

# Pour chaque patient (ligne), on compte combien de familles dépassent le seuil de 0.35
df["nb_familles_positives"] = (
    df[colonnes_familles] >= SEUIL_POSITIVITE
).sum(axis=1)

# En allergologie moléculaire, on parle de polysensibilisation dès qu'il y a >= 2 familles positives
SEUIL_POLY = 2
nb_patients_polysensibilises = (
    df["nb_familles_positives"] >= SEUIL_POLY
).sum()
total_patients = len(df)

taux_polysensibilisation = (nb_patients_polysensibilises / total_patients) * 100

# Affichage du KPI
print("=" * 60)
print(f"📊 KPI : TAUX DE POLYSENSIBILISATION DES FAMILLES")
print("=" * 60)
print(f"Nombre total de patients analysés : {total_patients}")
print(
    f"Patients positifs à au moins {SEUIL_POLY} familles différentes : {nb_patients_polysensibilises}"
)
print(
    f"➡️ Taux de Polysensibilisation Globale : {taux_polysensibilisation:.2f}%\n"
)


# ==============================================================================
# KPI 3 : CALCUL ET AFFICHAGE DE L'INDICE DE CO-SENSIBILISATION (ICM)
# ==============================================================================

# L'Indice de Co-sensibilisation Moléculaire (ICM) correspond à la matrice de
# corrélation de Spearman entre nos familles (adaptée aux distributions d'IgE)
icm_matrix = df[colonnes_familles].corr(method="spearman")

print("=" * 60)
print(f"🧬 MATRICE DE CO-SENSIBILISATION (ICM)")
print("=" * 60)
print(
    icm_matrix.round(2).to_string()
)  # Affichage textuel propre dans la console

# --- TRACÉ DE LA HEATMAP POUR VISUALISER L'ICM ---
# Optionnel : Ajustez la taille si vous avez beaucoup de molécules (ex: 18, 14)
plt.figure(figsize=(12, 12))

# Masque pour cacher la moitié supérieure diagonale
masque = np.triu(np.ones_like(icm_matrix, dtype=bool))

sns.heatmap(
    icm_matrix,
    mask=masque,  # Cache la partie supérieure redondante
    annot=False,  # <-- CONSEIL : Mis à False car vous avez près de 100 allergènes, les chiffres se chevaucheraient !
    fmt=".2f",
    cmap="coolwarm",  # Échelle de couleur Bleu (faible) à Rouge (fort)
    vmin=-1,  # <-- RECOMMANDATION : Spearman va de -1 à 1 (les corrélations négatives sont possibles et intéressantes)
    vmax=1,
    square=True,
    linewidths=0.1,  # Plus fin pour fluidifier l'affichage de nombreuses lignes
    cbar_kws={"label": "Force de l'Indice (Spearman rho)"},
)

plt.title(
    "Indice de Co-sensibilisation Moléculaire (ICM) entre Familles",
    fontsize=14,
    fontweight="bold",
    pad=15,
)
plt.xticks(rotation=90, ha="right", fontsize=8)  # Rotation à 90° recommandée pour vos ~100 labels
plt.yticks(fontsize=8)
plt.tight_layout()
plt.show()

sns.set_theme(style="whitegrid")
    
# Création du camembert
fig = plt.figure(figsize=(8, 6))  # Taille ajustée pour un graphique unique (plus harmonieux)

# 2. Calcul des données pour le camembert
taux_poly = (nb_patients_polysensibilises / total_patients) * 100
labels_poly = [
    f"Polysensibilisés\n({nb_patients_polysensibilises} patients)",  # Version dynamique plus propre
    "Mono ou Non-sensibilisés",
]
sizes_poly = [taux_poly, 100 - taux_poly]
colors_poly = ["#e74c3c", "#bdc3c7"]  # Rouge pour le risque, gris pour le reste

# 3. Tracé du diagramme en camembert
plt.pie(
    sizes_poly,
    labels=labels_poly,
    autopct="%1.1f%%",
    startangle=90,
    colors=colors_poly,
    explode=(0.05, 0),
    textprops={"fontsize": 12, "weight": "bold"},
)

# Affichage du titre
plt.title(
    "Taux de Polysensibilisation\n(Sur l'ensemble de la cohorte)",
    fontsize=14,
    pad=20,
    weight="bold",
)

# 4. Affichage du graphique final
plt.tight_layout()  # Permet d'éviter que les labels ou le titre soient coupés
plt.show()

df_analyse = df.copy()

SEUIL_POSITIVITE = 0.3
nb_familles_positives = (
    df_analyse[colonnes_familles] >= SEUIL_POSITIVITE
).sum(axis=1)

# Un patient est polysensibilisé (True/1) s'il a au moins 2 molécules positives
df_analyse["Est_Polysensibilise"] = nb_familles_positives >= 2

# --- CLASSIFICATION PAR ÂGE ---

# CORRECTION : On fait la moyenne de notre indicateur "Est_Polysensibilise"
kpi_age = (
    df_analyse.groupby("Age", observed=False)["Est_Polysensibilise"].mean()
    * 100
)

# CORRECTION : Idem pour la géographie, on suit le taux de polysensibilisation
kpi_geo = (
    df_analyse.groupby("Region")["Est_Polysensibilise"].mean() * 100
).sort_values(ascending=False)
top_geo = kpi_geo.head(5)
bottom_geo = kpi_geo.tail(5)

# ==============================================================================
# GÉNÉRATION DE LA VISUALISATION (3 sous-graphiques)
# ==============================================================================
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(20, 6))

# Graphique 1 : Tranches d'âge
sns.barplot(x=kpi_age.index, y=kpi_age.values, ax=ax1, palette="Blues_r")
ax1.set_title("Taux de Polysensibilisation par Âge", weight="bold", pad=10)
ax1.set_ylabel("Pourcentage (%)")
ax1.set_xlabel("Tranche d'âge")
for i, v in enumerate(kpi_age.values):
    ax1.text(i, v + 1, f"{v:.1f}%", ha="center", weight="bold")

# Graphique 2 : Géographie TOP
sns.barplot(x=top_geo.index, y=top_geo.values, ax=ax2, palette="Oranges_r")
ax2.set_title("Top 5 des Régions les plus Touchées", weight="bold", pad=10)
ax2.set_ylabel("Taux de Polysensibilisation (%)")
ax2.set_xlabel("Région")
for i, v in enumerate(top_geo.values):
    ax2.text(i, v + 1, f"{v:.1f}%", ha="center", weight="bold")

# Graphique 3 : Géographie TOP-moins (Bottom)
sns.barplot(x=bottom_geo.index, y=bottom_geo.values, ax=ax3, palette="Oranges_r")
ax3.set_title("Top 5 des Régions les moins Touchées", weight="bold", pad=10)
ax3.set_ylabel("Taux de Polysensibilisation (%)")
ax3.set_xlabel("Région")
for i, v in enumerate(bottom_geo.values):
    ax3.text(i, v + 1, f"{v:.1f}%", ha="center", weight="bold")


plt.tight_layout()
plt.show()

