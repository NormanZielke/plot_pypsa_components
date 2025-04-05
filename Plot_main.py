import logging

from network_visual import Etrago1

logger = logging.getLogger(__name__)

# set format for logging massages 
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

args = {
    # INPUT
    "pypsa_network":"pypsa_results/results_ingolstadt", # path to pypsa results
    "nuts_3_map" : "germany-de-nuts-3-regions.geojson", # path to .geojson nuts-3 file
    # Visualisation
    "plot_settings":{
            "bussize": 10,
            "linkwidth": 5,
            "linewidth": 3,
    },
    # maps_export
    "maps_export":{ # save maps as .html /path/to/folder/bus_map_xxx.html
        "busmap":"maps/maps_Ingolstadt/bus_map_Ingolstadt.html",
        "links" :"maps/maps_Ingolstadt/links_map_Ingolstadt.html",
        "lines" :"maps/maps_Ingolstadt/lines_map_Ingolstadt.html",
        "buses_links" : "maps/maps_Ingolstadt/buses_links_map_Ingolstadt.html",
        "buses_links_lines" : "maps/maps_Ingolstadt/buses_links_lines_map_Ingolstadt.html",
    },
}

etrago = Etrago1(args, csv_folder = args["pypsa_network"])

# create maps

etrago.create_bus_map()

etrago.create_links_map()

etrago.create_lines_map()

etrago.create_buses_and_links_map()

etrago.create_buses_links_lines_map()

logger.info("Maps successfully created.")


