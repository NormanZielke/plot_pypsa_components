import logging
import os
import pandas as pd
import numpy as np

from calc_results import capacities_opt, capacities_opt_techs_global, plot_capacity_bar_multiple
from network_visual import Etrago1

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# === USER INPUT ===
args = {
    "scenario_folder": "pypsa_results/set27",  # Ordner mit PyPSA-Szenarien

    #"scenario_labels": ["EL*0.5","EL*0.75","base","EL*2","EL*3"],
    #"scenario_labels": ["base","CH4_100","CH4_150"],
    #scenario_labels": ["SMR*0.5","SMR*0.75","base","SMR*2","SMR*3"],
    #"scenario_labels": ["Batterie*0.5","Batterie*0.75","base","Batterie*2","Batterie*3"],  Legendenbeschriftung im Plot
    "scenario_labels": ["base_1", "base"],

    #"plot_label": "EL_Vergleich",  # Präfix für Plot-Dateien
    #"plot_label": "CH4_Vergleich",
    #"plot_label": "SMR_Vergleich",
    #"plot_label": "Batterie_Vergleich",
    "plot_label": "Base_Vergleich",

    "nuts_3_map": "germany-de-nuts-3-regions.geojson",
    "interest_area": "Ingolstadt",
    "network_clustering": {"n_clusters_AC": 30, "n_clusters_gas": 14},
    "name": "Ingolstadt_30_14",
    "plot_settings": {"plot_comps_of_interest": True,
                      "bussize": 10,
                      "linkwidth": 5,
                      "linewidth": 3},
}


def load_scenario_paths(folder, labels):
    files = sorted(os.listdir(folder))
    if len(files) < len(labels):
        raise ValueError("Nicht genügend Dateien im Szenario-Ordner gefunden.")
    return [os.path.join(folder, f) for f in files[:len(labels)]]


def run_scenario_comparison(args):
    scenario_paths = load_scenario_paths(args["scenario_folder"], args["scenario_labels"])

    # Datenstrukturen für globale Technologien
    h2_list_1, h2_list_2, stores_list_1, stores_list_2, charger_list, bat_list = [], [], [], [], [], []
    # Datenstrukturen für Ingolstadt-spezifische Technologien
    ing_stores_1, ing_stores_2, ing_charger_list, ing_bat_list = [], [], [], []

    for label, path in zip(args["scenario_labels"], scenario_paths):
        logger.info(f"Lade Szenario: {label} aus {path}")
        etrago = Etrago1(args, csv_folder=path)
        cap_opt, cap_ing_opt = capacities_opt(etrago, scn=label)

        # Globale Aufteilung
        df_H2_1, df_H2_2, df_stores_1, df_stores_2, df_charger, df_bat = capacities_opt_techs_global(cap_opt)
        h2_list_1.append(df_H2_1)
        h2_list_2.append(df_H2_2)
        stores_list_1.append(df_stores_1)
        stores_list_2.append(df_stores_2)
        charger_list.append(df_charger)
        bat_list.append(df_bat)

        # Ingolstadt-Aufteilung (nur wenn Einträge vorhanden)
        df_H2_1_i, df_H2_2_i, df_stores_1_i, df_stores_2_i, df_charger_i, df_bat_i = capacities_opt_techs_global(cap_ing_opt)
        ing_stores_1.append(df_stores_1_i)
        ing_stores_2.append(df_stores_2_i)
        ing_charger_list.append(df_charger_i)
        ing_bat_list.append(df_bat_i)

    # === Zusammenführen global ===
    def concat_and_label(dfs):
        df = pd.concat(dfs, axis=1)
        df.columns = args["scenario_labels"]
        return df

    df_H2_1 = concat_and_label(h2_list_1)
    df_H2_2 = concat_and_label(h2_list_2)
    df_stores_1 = concat_and_label(stores_list_1)
    df_stores_2 = concat_and_label(stores_list_2)
    df_charger_all = concat_and_label(charger_list)
    df_bat_all = concat_and_label(bat_list)

    # === Zusammenführen Ingolstadt ===
    df_ing_stores_1 = concat_and_label(ing_stores_1)
    df_ing_stores_2 = concat_and_label(ing_stores_2)
    df_ing_charger = concat_and_label(ing_charger_list)
    df_ing_bat = concat_and_label(ing_bat_list)


    # === Reihenfolge der Charger korrigieren ===
    #charger_order = ["central_heat_store_charger", "central_heat_store_discharger",
    #                 "rural_heat_store_charger", "rural_heat_store_discharger"]
    #df_charger_all = df_charger_all.loc[[c for c in charger_order if c in df_charger_all.index]]
    #df_ing_charger = df_ing_charger.loc[[c for c in charger_order if c in df_ing_charger.index]]

    # === Globale Plots ===
    plot_capacity_bar_multiple(df_H2_1, filename=f"{args['plot_label']}_H2_1", title="Methanisierung und Brennstoffzelle")
    plot_capacity_bar_multiple(df_H2_2, filename=f"{args['plot_label']}_H2_2", title="Elektrolyse & SMR")
    plot_capacity_bar_multiple(df_stores_1, filename=f"{args['plot_label']}_stores_1", title="Zentrale Wärmespeicher")
    plot_capacity_bar_multiple(df_stores_2, filename=f"{args['plot_label']}_stores_2", title="rural_heat_store & H2")
    plot_capacity_bar_multiple(df_charger_all, filename=f"{args['plot_label']}_charger", title="Charger")
    plot_capacity_bar_multiple(df_bat_all, filename=f"{args['plot_label']}_bat", title="Batteriespeicher")

    # === Lokale Plots (Ingolstadt) ===
    plot_capacity_bar_multiple(df_ing_stores_1, filename=f"{args['plot_label']}_ing_stores_1", title="Ingolstadt: Zentrale Wärmespeicher")
    plot_capacity_bar_multiple(df_ing_stores_2, filename=f"{args['plot_label']}_ing_stores_2", title="Ingolstadt: rural_heat_store")
    plot_capacity_bar_multiple(df_ing_charger, filename=f"{args['plot_label']}_ing_charger", title="Ingolstadt: Charger")
    plot_capacity_bar_multiple(df_ing_bat, filename=f"{args['plot_label']}_ing_bat", title="Ingolstadt: Batteriespeicher")




if __name__ == "__main__":
    run_scenario_comparison(args)
