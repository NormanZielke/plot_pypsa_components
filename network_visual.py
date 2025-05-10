import logging
import pypsa

from plot_comps import (
    create_bus_map,
    create_links_map,
    create_lines_map,
    create_buses_and_links_map,
    create_buses_links_lines_map,
    create_maps,
    find_interest_buses,
    find_links_connected_to_buses
)
from calc_results import (
    capacities_opt,
    capacities_opt_techs_global
)

logger = logging.getLogger(__name__)

class Etrago1:

    def __init__(self, args, csv_folder=None):
        self.args = args
        self.name = args["name"] # To DO compose of args -> {interest_area}_{#AC_Buses}_{#CH_4_Buses}

        # PyPSA-Netzwerk laden
        self.network = pypsa.Network(csv_folder)

    # Add functions
    create_bus_map = create_bus_map

    create_links_map = create_links_map

    create_lines_map = create_lines_map

    create_buses_and_links_map = create_buses_and_links_map

    create_buses_links_lines_map = create_buses_links_lines_map

    create_maps = create_maps

    find_interest_buses = find_interest_buses

    find_links_connected_to_buses = find_links_connected_to_buses

    capacities_opt = capacities_opt

    capacities_opt_techs_global = capacities_opt_techs_global
