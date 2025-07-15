import logging
import os
import pandas as pd
import numpy as np



from network_visual import Etrago1

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

args = {
    # == INPUT ==
    "pypsa_network":"etrago_results/Base_scenarios/Base_scenario_1_test_2025-07-08", # path to pypsa results
    "results_folder":"results/Base_scenarios/Base_scenario_1_test_2025-07-08",

    "nuts_3_map" : "germany-de-nuts-3-regions.geojson", # path to .geojson nuts-3 file

    "time_horizon": slice("2011-01-15", "2011-02-15") , # define time horizon for timeseries plots
    # copied from etrago
    "interest_area" : ["Ingolstadt"],
    "network_clustering": {
        "n_clusters_AC": 30,
        "n_clusters_gas": 14,
    },
    "name" : "Ingolstadt_30_14",  # {interest_area}_{#AC_Buses}_{#CH_4_Buses}
    # Visualisation
    "plot_settings":{
        "plot_comps_of_interest": False, # plot only pypsa-components of interest ara
        "bussize": 10,
        "linkwidth": 5,
        "linewidth": 3,
    },
}

def calc_base_results(args):
    etrago = Etrago1(args, csv_folder = args["pypsa_network"])
    etrago.plot_capacity_bar(
        title="Optimierte Kapaziäten mit vorhandenen Kapazitäten",
        filename="capacity_bar.png",
        output_folder=args["results_folder"]
    )
    etrago.plot_electricity_generation_bar(
        title="Stromerversorgung je Technologie",
        filename="generation_bar.png",
        output_folder=args["results_folder"]
    )

    etrago.plot_central_heat_generation_bar(
        title="Zentrale Wärmerversorgung je Technologie",
        filename="central_heat_generation_bar.png",
        output_folder=args["results_folder"]
    )

    etrago.plot_decentral_heat_generation_bar(
        title="dezentrale Wärmerversorgung je Technologie",
        filename="decentral_heat_generation_bar.png",
        output_folder=args["results_folder"]
    )

    etrago.plot_central_heat_dispatch(
        time=args["time_horizon"],
        title="Dispatch Central Heat und Wärmeerzeuger",
        filename="central_heat_dispatch.png",
        output_folder=args["results_folder"]
    )

    return etrago


if __name__ == "__main__":
    etrago = calc_base_results(args)