"""
Nettoyage des données sur les allergies
===========================================================
Script de préparation et nettoyage des données
Gestion des erreurs, logs, vérification d'intégrité.
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path


# RAW files
allergies_filepath = "../data/allergies.csv"
allergens_filepath = "../data/allergens.csv"

# CLEAN files
allergies_clean_filepath = "../data/allergies_clean.csv"
allergies_clean_categories_filepath = "../data/allergies_clean_categories.csv"

# Dictionnaires utilitaires à la préparation des données
d_age_apparition = {
        9:"Non renseigné",
        0:"Aucun",
        1:"0 - 2 ans",
        2:"0 - 2 ans",
        3:"2 - 3 ans",
        4:"3 - 10 ans",
        5:"10 - 20 ans",
        6:"20 ans et plus"
}

d_traitement_actuel_da = {
        9:"Non renseigné",
        0:"Pas de traitement",
        1:"Autres",
        2:"Dermocorticoïdes",
        3:"Autres",
        4:"Autres",
        5:"Dupilumab",
        6:"Autres",
        7:"Autres"
}

d_facteurs = {
        9: "Non renseigné",
        0: "Aucun",
        1: "Effort/Activité sportive",
        2: "Autres",
        3: "Autres",
        4: "Moisissures",
        5: "Acariens",
        6: "Animaux : chat/chien",
        7: "Animaux : chat/chien",
        8: "Animaux : cheval/rongeur",
        10: "Animaux : cheval/rongeur",
        11: "Autres",
        12: "Autres"
}

d_traitement_rhinite = {
        9: "Non renseigné",
        0: "Aucun",
        1: "Anti-H1, voie locale",
        2: "Anti-H1 voie générale",
        3: "Anti-H1 + CS",
        4: "Anti-H1 + CS"

}

# Fonction utilitaire pour l'âge, découpé en 5 catégories
def age_to_categories(a: int) -> str:
    if a<10:
        return "0 à 10"
    elif a<20:
        return "10 à 20"
    elif a<40:
        return "20 à 40"
    elif a<60:
        return "40 à 60"
    else:
        return "60 à Plus"

# Fonction utilitaire pour la région (surtout pour les 5 régions qui ont très peu de patients)
def region_regroup(r: str) -> str:
    if r in ["regionE", "regionG", "regionH", "regionK", "regionN"]:
        # Si des régions ont moins de 12 patients (ou 12 tout juste), alors on regroupe.
        return "regionEGHKN"
    else:
        return r

# ---------------------------------------------------------------------------
# Logging - chaque execution crée un nouveau fichier de log
# ---------------------------------------------------------------------------

log_file = f"../data/prepare_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Nettoyage des données allergies
# ---------------------------------------------------------------------------

def clean_data_allergies(source: Path, dest: Path) -> bool:
    """
    Nettoyage des données allergies
    """

    logger.info(f"Nettoyage : {source.name}")

    df = pd.read_csv(filepath_or_buffer=source)

    # Dans certaines colonnes, parfois la réaction à l'allergène n'est pas saisie, 
    # on remplacera alors les valeurs nulles par zero.
    lst_col = []
    lst_col_replace_na = []
    r = df.shape[0]

    for c in df.columns:
        z = int(df[c].isna().sum())/r
        lst_col.append([z, c])
        if z >= 0.1:
            lst_col_replace_na.append(c)

    lst_col.sort(reverse=True)

    # Lorsque le test n'a pas de résultat saisi, on met par défaut 
    # zero (pour pas de réaction à l'allergène)
    df[lst_col_replace_na] = df[lst_col_replace_na].fillna(value=0)

    # Il reste très peu de valeurs nulles, on enlève les lignes correspondantes.

    df2 = df.dropna(axis=0, how="any")

    # Pas besoin de garder "__id", chaque patient possède déjà un identifiant que nous allons garder.
    # Nous n'allons pas regarder les détails au niveau du département. Il y a de toute façon une 
    # anonymisation des départements et régions.

    df2 = df2.drop(columns=["__id", "French_Residence_Department"])

    # Simple renommage de French_Region
    df2.rename(columns={"French_Region": "Region"}, inplace=True)

    # Attention : certaines régions ont seulement 12 patients ou moins, alors nous les regroupons
    df2["Region"] = df2["Region"].apply(lambda z: region_regroup(z))

    # Application de catégories sur l'âge :
    df2["Age"] = df2["Age"].apply(lambda z: age_to_categories(z))

    # Correctifs sur les colonnes Oui / Non (t / f) : les valeurs seront 1 ou 0.

    df2["Gender"] = df2["Gender"].apply(lambda z: int(1) if z=="t" else int(0))
    df2["Gender"] = df2["Gender"].astype("int64")

    df2["Sensitization"] = df2["Sensitization"].apply(lambda z: int(1) if z=="t" else int(0))
    df2["Sensitization"] = df2["Sensitization"].astype("int64")

    # Simplification de la colonne Rural_or_urban_area (1, 0, 9), on ne gardera que (1, 0) 
    # pour indicateur de Ruralité :
    
    df2["Rural_or_urban_area"] = df2["Rural_or_urban_area"].apply(lambda z: 1 if int(z)==1 else 0)
    df2.rename(columns={"Rural_or_urban_area": "Rural_area"}, inplace=True)

    # Simplification pour la colonne Treatment_of_athsma (1, 0, 9), on ne gardera que (1, 0) :
    df2["Treatment_of_athsma"] = df2["Treatment_of_athsma"].apply(lambda z: int(str(z).split(",")[0]))
    df2["Treatment_of_athsma"] = df2["Treatment_of_athsma"].apply(lambda z: 1 if ((z!=0) and (z!=9)) else 0)
    df2.rename(columns={"Treatment_of_athsma": "Treatment_of_asthma"}, inplace=True)

    # Simplification pour la colonne Skin_Symptoms (1, 0, 9), on ne gardera que (1, 0) :
    df2["Skin_Symptoms"] = df2["Skin_Symptoms"].apply(lambda z: 1 if z==1 else 0)

    # Correctifs sur les colonnes ayant 0, 1, 2, ..., N (catégories) :

    df2["Treatment_of_rhinitis"] = df2["Treatment_of_rhinitis"].apply(lambda z:int(z))

    df2["General_cofactors"] = df2["General_cofactors"].apply(lambda z: int(z.split(",")[0]) if type(z)!=int else z)

    df2["Treatment_of_atopic_dematitis"] = df2["Treatment_of_atopic_dematitis"].apply(lambda z: int(z.split(",")[0]) if type(z)!=int else z)

    df2["Age_of_onsets"] = df2["Age_of_onsets"].apply(lambda z: int(z.split(",")[0]) if type(z)!=int else z)

    # Application du dictionnaire : rhinite, facteurs et dermatite atopique et age d'apparition des symptômes
    df2["Treatment_of_rhinitis"] = df2["Treatment_of_rhinitis"].apply(lambda z: d_traitement_rhinite.get(z, z))

    df2["General_cofactors"] = df2["General_cofactors"].apply(lambda z: d_facteurs.get(z, z))

    df2["Treatment_of_atopic_dematitis"] = df2["Treatment_of_atopic_dematitis"].apply(lambda z: d_traitement_actuel_da.get(z, z))

    df2["Age_of_onsets"] = df2["Age_of_onsets"].apply(lambda z: d_age_apparition.get(z, z))

    # Les colonnes de tests biologiques ne devraient jamais être avec des valeurs négatives.
    columns_biological_tests = ['Act_d_1', 'Act_d_2', 'Act_d_5', 'Act_d_8', 'Aln_g_1', 'Alt_a_1', 'Alt_a_6', 'Amb_a_1', 'Ana_o_2', 
                                'Ani_s_1', 'Ani_s_3', 'Api_g_1', 'Api_m_1', 'Api_m_4', 'Ara_h_1', 'Ara_h_2', 'Ara_h_3', 'Ara_h_6',
                                'Ara_h_8', 'Ara_h_9', 'Art_v_1', 'Art_v_3', 'Asp_f_1', 'Asp_f_3', 'Asp_f_6', 'Ber_e_1', 'Bet_v_1',
                                'Bet_v_2', 'Bet_v_4', 'Bla_g_1', 'Bla_g_2', 'Bla_g_5', 'Bla_g_7', 'Blo_t_5', 'Bos_d_4', 'Bos_d_5',
                                'Bos_d_6', 'Bos_d_8', 'Bos_d_Lactoferrin', 'Can_f_1', 'Can_f_2', 'Can_f_3', 'Can_f_5', 'Che_a_1',
                                'Cla_h_8', 'Cor_a_1.0101', 'Cor_a_1.0401', 'Cor_a_8', 'Cor_a_9', 'Cry_j_1', 'Cup_a_1', 'Cyn_d_1',
                                'Der_f_1', 'Der_f_2', 'Der_p_1', 'Der_p_10', 'Der_p_2', 'Equ_c_1', 'Equ_c_3', 'Fag_e_2', 'Fel_d_1',
                                'Fel_d_2', 'Fel_d_4', 'Gad_c_1', 'Gal_d_1', 'Gal_d_2', 'Gal_d_3', 'Gal_d_5', 'Gly_m_4', 'Gly_m_5',
                                'Gly_m_6', 'Hev_b_1', 'Hev_b_3', 'Hev_b_5', 'Hev_b_6.01', 'Hev_b_8', 'Jug_r_1', 'Jug_r_2', 'Jug_r_3',
                                'Lep_d_2', 'Mal_d_1', 'Mer_a_1', 'Mus_m_1', 'MUXF3', 'Ole_e_1', 'Ole_e_7', 'Ole_e_9', 'Par_j_2', 'Pen_m_1',
                                'Pen_m_2', 'Pen_m_4', 'Phl_p_1', 'Phl_p_11', 'Phl_p_12', 'Phl_p_2', 'Phl_p_4', 'Phl_p_5', 'Phl_p_6', 'Phl_p_7',
                                'Pla_a_1', 'Pla_a_2', 'Pla_a_3', 'Pla_l_1', 'Pol_d_5', 'Pru_p_1', 'Pru_p_3', 'Sal_k_1', 'Ses_i_1', 'Tri_a_14',
                                'Tri_a_19.0101', 'Tri_a_aA_TI', 'Ves_v_5', 'Cor_a_14', 'Can_f_4', 'Hev_b_6', 'Der_p_23', 'Alpha-Gal', 'Ana_o_3',
                                'Can_f_6', 'Aca_m', 'Aca_s', 'Ach_d', 'Act_d_10', 'Ail_a', 'All_c', 'All_s', 'Aln_g_4', 'Ama_r', 'Amb_a', 'Amb_a_4',
                                'Ana_o', 'Api_g_2', 'Api_g_6', 'Api_m', 'Api_m_10', 'Ara_h_15', 'Arg_r_1', 'Art_v', 'Asp_f_4', 'Ave_s', 'Ber_e',
                                'Bet_v_6', 'Bla_g_4', 'Bla_g_9', 'Blo_t_10', 'Blo_t_21', 'Bos_d_2', 'Bos_d_meat', 'Bos_d_milk', 'Bro_pa', 'Cam_d',
                                'Can_f_Fd1', 'Can_f_male_urine', 'Can_s', 'Can_s_3', 'Cap_a', 'Cap_h_epithelia', 'Cap_h_milk', 'Car_c', 'Car_i',
                                'Car_p', 'Cav_p_1', 'Che_a', 'Che_q', 'Chi_spp.', 'Cic_a', 'Cit_s', 'Cla_h', 'Clu_h', 'Clu_h_1', 'Cor_a_1.0103',
                                'Cor_a_11', 'Cor_a_12_RUO', 'Cor_a_pollen', 'Cra_c_6', 'Cuc_m_2', 'Cuc_p', 'Cup_s', 'Cyn_d', 'Cyp_c_1', 'Dau_c',
                                'Dau_c_1', 'Der_p_11', 'Der_p_20', 'Der_p_21', 'Der_p_5', 'Der_p_7', 'Dol_spp', 'Equ_c_4', 'Equ_c_meat', 'Equ_c_milk',
                                'Fag_e', 'Fag_s_1', 'Fel_d_7', 'Fic_b', 'Fic_c', 'Fra_a_1+3', 'Fra_e', 'Fra_e_1', 'Gad_m', 'Gad_m_1', 'Gad_m_2+3',
                                'Gal_d_4', 'Gal_d_meat', 'Gal_d_white', 'Gal_d_yolk', 'Gly_d_2', 'Gly_m_8', 'Hel_a', 'Hev_b_11', 'Hev_b_6.02', 'Hom_g',
                                'Hom_s_LF', 'Hor_v', 'Jug_r_4', 'Jug_r_6', 'Jug_r_pollen', 'Jun_a', 'Len_c', 'Lit_s', 'Loc_m', 'Lol_p_1', 'Lol_spp.',
                                'Lup_a', 'Mac_i_2S_Albumin', 'Mac_inte', 'Mal_d_2', 'Mal_d_3', 'Mala_s_11', 'Mala_s_5', 'Mala_s_6', 'Man_i', 'Mel_g',
                                'Mes_a_1_RUO', 'Mor_r', 'Mus_a', 'Myt_e', 'Ole_e_7_RUO', 'Ori_v', 'Ory_c_1', 'Ory_c_2']
    
    for cbt in columns_biological_tests:
        df2[cbt] = df2[cbt].apply(lambda z: 0 if z<0 else z)

    # Fichier clean
    df2.to_csv(path_or_buf=dest, index=False)

    nb_rows = df2.shape[0]
    logger.info(f"  ✓ Nettoyé : {dest.name} ({nb_rows} rows)")

    return True

# ---------------------------------------------------------------------------
# Nettoyage des données allergies, avec des regroupements des colonnes d'analyses médicales
# ---------------------------------------------------------------------------

def clean_data_allergies_categories(source: Path, dest: Path) -> bool:
    """
    Nettoyage des données allergies
    """

    logger.info(f"Nettoyage : {source.name}")

    # ==========================================
    # 1. CHARGEMENT DES DONNÉES
    # ==========================================

    # Chargement du tableau principal (avec les patients et les scores d'IgE)
    # On spécifie le séparateur ';' propre à votre fichier
    
    df = pd.read_csv(filepath_or_buffer=source)

    # ==========================================
    # 2. CRÉATION DU MAPPING (ACRONYME -> CATÉGORIE)
    # ==========================================

    # /!\ ÉTAPE À ADAPTER SELON VOTRE DICTIONNAIRE /!\
    # Ici, nous créons manuellement un dictionnaire de correspondance basé sur les standards ISAC.
    # Etant donné qu'on ne pouvait lire automatiquement le fichier du dictionnaire, il est repris ici
    mapping_categories = {
        # POLLENS D'ARBRES
        'Aln_g_1': 'Pollens', 'Bet_v_1': 'Pollens', 'Bet_v_2': 'Pollens', 'Bet_v_4': 'Pollens',
        'Cup_a_1': 'Pollens', 'Ole_e_1': 'Pollens', 'Ole_e_7': 'Pollens', 'Ole_e_9': 'Pollens',
        'Cor_a_1.0101': 'Pollens', 'Cor_a_1.0401': 'Pollens',
        
        # GRAMINÉES ET HERBACÉES
        'Amb_a_1': 'Pollens', 'Art_v_1': 'Pollens', 'Art_v_3': 'Pollens',
        'Phl_p_1': 'Pollens', 'Phl_p_2': 'Pollens', 'Phl_p_4': 'Pollens', 'Phl_p_5': 'Pollens',
        'Phl_p_6': 'Pollens', 'Phl_p_7': 'Pollens', 'Phl_p_11': 'Pollens', 'Phl_p_12': 'Pollens',
        'Che_a_1': 'Pollens', 'Par_j_2': 'Pollens',

        # ALIMENTS (Fruits, Légumes, Graines)
        'Act_d_1': 'Aliments', 'Act_d_2': 'Aliments', 'Act_d_5': 'Aliments', 'Act_d_8': 'Aliments',
        'Ana_o_2': 'Aliments', 'Api_g_1': 'Aliments', 
        'Ara_h_1': 'Aliments', 'Ara_h_2': 'Aliments', 'Ara_h_3': 'Aliments', 'Ara_h_6': 'Aliments', 'Ara_h_8': 'Aliments', 'Ara_h_9': 'Aliments',
        'Ber_e_1': 'Aliments', 'Cor_a_8': 'Aliments', 'Cor_a_9': 'Aliments', 'Cor_a_14': 'Aliments',
        'Gly_m_4': 'Aliments', 'Gly_m_5': 'Aliments', 'Gly_m_6': 'Aliments',
        'Mal_d_1': 'Aliments', 'Pru_p_3': 'Aliments', 'Ses_i_1': 'Aliments', 'Sin_a_1': 'Aliments',
        
        # PRODUITS ANIMAUX (Lait, Œuf, Viande, Poisson)
        'Bos_d_4': 'Aliments', 'Bos_d_5': 'Aliments', 'Bos_d_6': 'Aliments', 'Bos_d_8': 'Aliments', 'Bos_d_Lactoferrin': 'Aliments',
        'Gal_d_1': 'Aliments', 'Gal_d_2': 'Aliments', 'Gal_d_3': 'Aliments', 'Gal_d_5': 'Aliments',
        'Gad_m_1': 'Aliments', 'Pen_m_1': 'Aliments', 'Pen_m_2': 'Aliments', 'Pen_m_4': 'Aliments',
        
        # ANIMAUX DOMESTIQUES
        'Can_f_1': 'Animaux', 'Can_f_2': 'Animaux', 'Can_f_3': 'Animaux', 'Can_f_5': 'Animaux', 'Can_f_6': 'Animaux',
        'Fel_d_1': 'Animaux', 'Fel_d_2': 'Animaux', 'Fel_d_4': 'Animaux', 'Fel_d_7': 'Animaux',
        'Equ_c_1': 'Animaux', 'Mus_m_1': 'Animaux',

        # ACARIENS ET BLATTES
        'Der_f_1': 'Acariens/Blattes', 'Der_f_2': 'Acariens/Blattes',
        'Der_p_1': 'Acariens/Blattes', 'Der_p_2': 'Acariens/Blattes', 'Der_p_10': 'Acariens/Blattes',
        'Bla_g_1': 'Acariens/Blattes', 'Bla_g_2': 'Acariens/Blattes', 'Bla_g_5': 'Acariens/Blattes', 'Bla_g_7': 'Acariens/Blattes',
        'Blo_t_5': 'Acariens/Blattes', 'Lep_d_2': 'Acariens/Blattes',

        # MOISISSURES, VENINS ET LATEX
        'Alt_a_1': 'Moisissures/Autres', 'Alt_a_6': 'Moisissures/Autres',
        'Asp_f_1': 'Moisissures/Autres', 'Asp_f_3': 'Moisissures/Autres', 'Asp_f_6': 'Moisissures/Autres',
        'Cla_h_8': 'Moisissures/Autres', 'Pen_c_3': 'Moisissures/Autres',
        'Api_m_1': 'Moisissures/Autres', 'Api_m_4': 'Moisissures/Autres',
        'Vesp_v_1': 'Moisissures/Autres', 'Vesp_v_5': 'Moisissures/Autres',
        'Hev_b_1': 'Moisissures/Autres', 'Hev_b_3': 'Moisissures/Autres', 'Hev_b_5': 'Moisissures/Autres', 'Hev_b_6.02': 'Moisissures/Autres',
        'Ani_s_1': 'Moisissures/Autres', 'Ani_s_3': 'Moisissures/Autres',
        'Hom_s_LF': 'Moisissures/Autres'
    }


    # ==========================================
    # 3. NETTOYAGE ET CONVERSION DES DONNÉES
    # ==========================================

    # Identification des colonnes de métadonnées des patients (à ne pas sommer)
    colonnes_metadonnees = [
        'Patient_ID', 'Chip_Type', 'Age', 'Gender', 'Blood_Month_sample',
        'Region', 'Rural_area',
        'Sensitization', 'Treatment_of_rhinitis', 'Treatment_of_asthma',
        'Age_of_onsets', 'Skin_Symptoms', 'General_cofactors', 'Treatment_of_atopic_dematitis'
    ]

    # Sélectionner uniquement les colonnes d'allergènes présentes dans le fichier principal
    colonnes_allergenes_presentes = [col for col in df.columns if col in mapping_categories]

    # Création d'une copie propre pour travailler
    df_clean = df.copy()

    # ==========================================
    # 4. AGRÉGATION PAR CATÉGORIE
    # ==========================================

    # Extraction des métadonnées des patients
    df_final = df_clean[colonnes_metadonnees].copy()

    # Groupement horizontal (axis=1) des allergènes par leur catégorie en calculant la SOMME ou la MOYENNE
    # (Vous pouvez remplacer .sum() par .max() si vous voulez le score maximal de la catégorie)
    df_categories_somme = df_clean[colonnes_allergenes_presentes].groupby(mapping_categories, axis=1).mean()

    # Fusion des métadonnées et des scores par grandes catégories
    df_resultat_complet = pd.concat([df_final, df_categories_somme], axis=1)


    # ==========================================
    # 5. EXPORT
    # ==========================================
    
    # Sauvegarde du nouveau tableau dans un fichier CSV bien propre
    df_resultat_complet.to_csv(dest, index=False)

    nb_rows = df_resultat_complet.shape[0]
    logger.info(f"  ✓ Nettoyé : {dest.name} ({nb_rows} rows)")

    return True


if __name__ == "__main__":
    clean_data_allergies(Path(allergies_filepath), Path(allergies_clean_filepath))
    clean_data_allergies_categories(Path(allergies_clean_filepath), Path(allergies_clean_categories_filepath))