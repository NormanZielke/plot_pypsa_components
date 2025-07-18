import logging
import pandas as pd

from calc_results import (
    capacities_opt_techs_global,
    plot_capacity_bar_multiple
)

from network_visual import Etrago1

logger = logging.getLogger(__name__)

# set format for logging massages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

args = {
    # == INPUT ==
    "pypsa_network":"pypsa_results/2025-06-22_set35_base1", # path to pypsa results

    "nuts_3_map" : "germany-de-nuts-3-regions.geojson", # path to .geojson nuts-3 file
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

etrago = Etrago1(args, csv_folder = args["pypsa_network"])


# === create maps ===
etrago.create_maps()
#etrago.create_bus_map()
#etrago.create_links_map()
#etrago.create_lines_map()
#etrago.create_buses_and_links_map()
#etrago.create_buses_links_lines_map()
#logger.info("Maps successfully created.")


