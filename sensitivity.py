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
    "scenario_folder": "pypsa_results/sensitivity_runs",  # Ordner mit PyPSA-Szenarien
    "scenario_labels": ["base", "EL*2", "EL*3","EL*0.75","EL*0.5"],  # Legendenbeschriftung im Plot (Reihenfolge beachten!)
    "plot_label": "EL_Vergleich",  # Dateinamenspräfix für Plots
    "nuts_3_map": "germany-de-nuts-3-regions.geojson",
    "interest_area": "Ingolstadt",
    "network_clustering": {"n_clusters_AC": 30, "n_clusters_gas": 14},
    "name": "Ingolstadt_30_14",
    "plot_settings": {"plot_comps_of_interest": True, "bussize": 10, "linkwidth": 5, "linewidth": 3},
}


def load_scenario_paths(folder, labels):
    """Ordnet Dateinamen im Ordner den gegebenen Labels zu (alphabetisch sortiert)."""
    files = sorted(os.listdir(folder))
    if len(files) < len(labels):
        raise ValueError("Nicht genügend Dateien im Szenario-Ordner gefunden.")
    return [os.path.join(folder, f) for f in files[:len(labels)]]


def run_scenario_comparison(args):
    scenario_paths = load_scenario_paths(args["scenario_folder"], args["scenario_labels"])

    # Datenstrukturen für alle Technologien vorbereiten
    h2_list_1, h2_list_2, stores_list_1, stores_list_2, charger_list, bat_list = [], [], [], [], [], []

    for i, (label, path) in enumerate(zip(args["scenario_labels"], scenario_paths)):
        logger.info(f"Lade Szenario: {label} aus {path}")
        etrago = Etrago1(args, csv_folder=path)
        cap_opt, _ = capacities_opt(etrago, scn=label)
        df_H2_1, df_H2_2, df_stores_1, df_stores_2, df_charger, df_bat = capacities_opt_techs_global(cap_opt)

        # Szenarien-DataFrames sammeln
        h2_list_1.append(df_H2_1)
        h2_list_2.append(df_H2_2)
        stores_list_1.append(df_stores_1)
        stores_list_2.append(df_stores_2)
        charger_list.append(df_charger)
        bat_list.append(df_bat)

    # Alle Szenarien zu je einem DataFrame zusammenfassen
    df_H2_1 = pd.concat(h2_list_1, axis=1)
    df_H2_2 = pd.concat(h2_list_2, axis=1)
    df_stores_1 = pd.concat(stores_list_1, axis=1)
    df_stores_2 = pd.concat(stores_list_2, axis=1)
    df_charger_all = pd.concat(charger_list, axis=1)
    df_bat_all = pd.concat(bat_list, axis=1)

    # Spaltenbeschriftung zuweisen
    df_H2_1.columns = args["scenario_labels"]
    df_H2_2.columns = args["scenario_labels"]
    df_stores_1.columns = args["scenario_labels"]
    df_stores_2.columns = args["scenario_labels"]
    df_charger_all.columns = args["scenario_labels"]
    df_bat_all.columns = args["scenario_labels"]

    # Plotfarben: erstes Szenario grün, Rest Standard
    colors = ["green"] + [None] * (len(args["scenario_labels"]) - 1)

    # Barplots erstellen
    plot_capacity_bar_multiple(df_H2_1, filename=f"{args['plot_label']}_H2_1", title="EL & SMR")
    plot_capacity_bar_multiple(df_H2_2, filename=f"{args['plot_label']}_H2_2", title="Meathanisation & Fuell Cell")
    plot_capacity_bar_multiple(df_stores_1, filename=f"{args['plot_label']}_stores_1", title="Fernwärmespeicher")
    plot_capacity_bar_multiple(df_stores_2, filename=f"{args['plot_label']}_stores_2", title="rural_heat_store, H2-Store")
    plot_capacity_bar_multiple(df_charger_all, filename=f"{args['plot_label']}_charger", title="Charger")
    plot_capacity_bar_multiple(df_bat_all, filename=f"{args['plot_label']}_bat", title="Batteriespeicher")


if __name__ == "__main__":
    run_scenario_comparison(args)
