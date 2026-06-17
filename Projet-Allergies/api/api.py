"""
API de diffusion des données sur les allergies, extraits de la base SQLite
Contrôle de clés d'API, gestion des erreurs, logs, vérifications
"""

from fastapi import FastAPI, HTTPException, Depends, Security, Query
from fastapi.security.api_key import APIKeyHeader
import sqlite3
from contextlib import contextmanager

from pydantic import BaseModel, Field

# Exporter quoi : les données de allergies_clean_categories
# Colonnes : Patient_ID,Chip_Type,Age,Gender,Blood_Month_sample,Region,Urban_area,Sensitization,Treatment_of_rhinitis,Treatment_of_asthma,
# Age_of_onsets,Skin_Symptoms,General_cofactors,Treatment_of_atopic_dematitis,Acariens/Blattes,Aliments,Animaux,Moisissures/Autres,Pollens
# Comment lancer : "fastapi dev api.py" (ne pas lancer la commande "python api.py")

class Patient(BaseModel):
    # Patient_ID is not integer (for example: FHB0015)
    Patient_ID: str
    Chip_Type: str
    Age: str
    Gender: int
    Blood_Month_sample: float
    Region: str
    Rural_area: int
    Sensitization: int
    Treatment_of_rhinitis: str
    Treatment_of_asthma: int
    Age_of_onsets: str
    Skin_Symptoms: int
    General_cofactors: str
    Treatment_of_atopic_dematitis: str
    # Acariens/Blattes field name is handled (slash in it)
    Acariens_Blattes: float = Field(alias="Acariens/Blattes")
    Aliments: float
    Animaux: float
    # Moisissures/Autres field name is handled (slash in it)
    Moisissures_Autres: float = Field(alias="Moisissures/Autres")
    Pollens: float


import pandas as pd
import json
import csv
import os

def load_patients_from_db(filepath: str = "../data/allergen_chip_challenge.db"):
    # On va lire les données allergies directement depuis la table dans la base de données :
    conn = sqlite3.connect(filepath)

    p = pd.read_sql("Select * From allergies_categories", conn)
    conn.close()
    return p.to_dict(orient="records")

# Load all PATIENTS at startup
patients = load_patients_from_db()

# API Key and API Key Name:
API_KEY = "the-value-is-in-a-hidden-file"
API_KEY_NAME = "X-API-Key"

def load_config(config_path: str = "../secrets/config.json"):
    """Load parameters from a JSON file safely."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{config_path}' not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: File '{config_path}' contains invalid JSON.")
        return {}

# Getting genuine value for API KEY:
conf = load_config()
API_KEY = conf.get("API_KEY_VALUE")

# Here is the API
app = FastAPI()

# Adding security to this API
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Vérifie la clé API. Lève HTTP 403 si invalide ou absente."""
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Clé API invalide ou manquante. Passez votre clé dans le header X-API-Key.",
        )
    return api_key


@contextmanager
def get_db():
    """Gestionnaire de contexte pour la connexion SQLite."""
    conn = sqlite3.connect("../data/allergen_chip_challenge.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def query_db(sql: str, params: tuple = ()) -> list[dict]:
    """Exécute une requête et retourne une liste de dicts."""
    with get_db() as conn:
        df = pd.read_sql(sql, conn, params=params)
    return df.to_dict(orient="records")

@app.get("/")
async def root():
    return {"message": "Welcome to the Data API!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Data API"}

from typing import List, Optional

# On a ajouté les arguments "response_model=" aux fonctions suivantes : ça contrôle les données par rapport au modèle
# On a ajouté, après le "response_model", des arguments "summary" et "description" : but = pour expliquer la fonctionnalité (via DOCS)
# On a ajouté, après "description", l'argument "dependencies" pour indiquer la fonction qui va vérifier la clé API.

@app.get("/patients", response_model=dict,
            summary="Get all patients",
        description="Retrieve a list of all patients. Optionally filter by Region using a query parameter.",
        dependencies=[Depends(verify_api_key)])
async def get_all_patients(region: Optional[str] = None):
    if region:
        filtered_patients = [p for p in patients if p["Region"].lower() == region.lower()]
        return {"patients": filtered_patients, "count": len(filtered_patients)}
    return {"patients": patients, "count": len(patients)}

# Sans gestion d'erreur, si on fait un GET sur un produit qui n'existe pas, on obtient "INTERNAL SERVER ERROR" :
# On a besoin de HTTP-Exception pour gérer cette erreur.
# On remplace le return par un RAISE.


@app.get("/patients/{patient_id}", response_model=Patient,
            summary="Get one patient",
            description="Retrieve one patient by his ID.",
            dependencies=[Depends(verify_api_key)])
async def get_patient(patient_id: str):
    # Keep in mind that the patient ID is string value.
    for patient in patients:
        if patient["Patient_ID"] == patient_id:
            return patient
    raise HTTPException(status_code=404, detail="Patient not found")


@app.get(
    "/stats/regions",
    tags=["Statistiques par région"],
    summary="Statistiques par région",
    dependencies=[Depends(verify_api_key)],
)
def get_stats_regions(region= Query(default=None, description="Filtrer par region")):
    """Statistiques agrégées"""
    condition = "WHERE region = ?" if region else ""
    params = (region,) if region else ()

    requete_region = query_db(f"""
    SELECT
    a.Region,
    COUNT(*) as nb_patients,
    AVG(a.Sensitization)*100 as pourcentage_de_sensibilises
    FROM allergies_categories a
    {condition}
    GROUP BY region
    """, params)

    return requete_region
