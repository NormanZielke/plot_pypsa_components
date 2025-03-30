from plot_comps import (
    create_bus_map,
    create_links_map,
    create_lines_map,
    create_buses_and_links_map,
    create_buses_links_lines_map
)

# path input_data
geojson_file = "germany-de-nuts-3-regions.geojson"

#cities = ["Ingolstadt", "Kassel", "Bocholt"]
cities = ["Ingolstadt"]
#cities = ["network"]

# plot settings

args = {"bussize": 10,
        "linkwidth": 5,
        "linewidth": 3
        }

for city in cities:
    print(f"➤ Erzeuge Karten für: {city}")
    # Eingabepfade
    #base_path = "csv/network"

    base_path = f"csv/Simulation_{city}"
    buses = f"{base_path}/buses.csv"
    links = f"{base_path}/links.csv"
    lines = f"{base_path}/lines.csv"

    # Ausgabepfade
    output_file_buses = f"maps/Simulation_{city}/bus_map_{city}.html"
    output_file_links = f"maps/Simulation_{city}/links_map_{city}.html"
    output_file_lines = f"maps/Simulation_{city}/lines_map_{city}.html"
    output_file_buses_and_links = f"maps/Simulation_{city}/buses_and_links_map_{city}.html"
    output_file_buses_links_lines = f"maps/Simulation_{city}/buses_links_lines_map_{city}.html"

    # create maps
    create_bus_map(buses_csv = buses,
                   geojson_file = geojson_file,
                   output_file = output_file_buses,
                   args = args)

    create_links_map(buses_csv = buses,
                     links_csv = links,
                     geojson_file = geojson_file,
                     output_file = output_file_links,
                     args = args)

    create_lines_map(buses_csv = buses,
                     lines_csv = lines,
                     geojson_file = geojson_file,
                     output_file = output_file_lines,
                     args = args)

    create_buses_and_links_map(buses_csv = buses,
                               links_csv = links,
                               geojson_file = geojson_file,
                               output_file = output_file_buses_and_links,
                               args = args)

    create_buses_links_lines_map(buses_csv = buses,
                                 links_csv = links,
                                 lines_csv = lines,
                                 geojson_file = geojson_file,
                                 output_file = output_file_buses_links_lines,
                                 args = args)

print("✅ Alle Karten wurden erstellt.")
