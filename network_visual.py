import logging
import pypsa

from plot_comps import (
    create_bus_map,
    create_links_map,
    create_lines_map,
    create_buses_and_links_map,
    create_buses_links_lines_map
)

logger = logging.getLogger(__name__)

class Etrago1:
    """
    Erweiterte PyPSA-Netzklasse für Visualisierung, ähnlich wie Etrago.
    """

    def __init__(self, args, csv_folder=None, name=""):
        self.args = args
        self.name = name

        # PyPSA-Netzwerk laden
        self.network = pypsa.Network(csv_folder)
        self.network.args = args  # wichtig für die Kartenfunktionen
        # Methoden aus plot_comps_2 als eigene Methoden einbinden
        # self._register_visualisation_methods()

    # Add functions
    create_bus_map = create_bus_map

    create_links_map = create_links_map

    create_lines_map = create_lines_map

    create_buses_and_links_map = create_buses_and_links_map

    create_buses_links_lines_map = create_buses_links_lines_map