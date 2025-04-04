import os
import pypsa

from plot_comps import (
    create_bus_map,
    create_links_map,
    create_lines_map,
    create_buses_and_links_map,
    create_buses_links_lines_map,
)

args = {
    # INPUT
    "pypsa_network":"pypsa_results/results_ingolstadt", # path to pypsa results
    "nuts_3_map" : "germany-de-nuts-3-regions.geojson", # path to .geojson nuts 3 file
    # Visualisation
    "plot_settings":{
            "bussize": 10,
            "linkwidth": 5,
            "linewidth": 3,
    },
    # maps_export
    "maps_export":{ # save maps as .html /path/to/folder/bus_map_xxx.html
        "busmap":"maps/results_Ingolstadt/bus_map_Ingolstadt.html",
        "links" :"maps/results_Ingolstadt/links_map_Ingolstadt.html",
        "lines" :"maps/results_Ingolstadt/lines_map_Ingolstadt.html",
        "buses_links" : "maps/results_Ingolstadt/buses_links_map_Ingolstadt.html",
        "buses_links_lines" : "maps/results_Ingolstadt/buses_links_lines_map_Ingolstadt.html",
    },
}

# INPUT - DATA

n = pypsa.Network(args["pypsa_network"])
n.args = args

# create maps

create_bus_map(n)

create_links_map(n)

create_lines_map(n)

create_buses_and_links_map(n)

create_buses_links_lines_map(n)




