from plot_comps import (
    create_bus_map,
    create_links_map,
    create_lines_map,
    create_buses_and_links_map,
)

# path input_data
geojson_file = "germany-de-nuts-3-regions.geojson"
#cities = ["Ingolstadt", "Kassel", "Bocholt"]
cities = ["Ingolstadt"]
#cities = ["network"]
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
    output_file_links_and_buses = f"maps/Simulation_{city}/links_and_buses_map_{city}.html"

    # create maps
    create_bus_map(buses, geojson_file, output_file_buses)

    create_links_map(buses, links, geojson_file, output_file_links)

    create_lines_map(buses, lines, geojson_file, output_file_lines)

    create_buses_and_links_map(buses, links, geojson_file, output_file_links_and_buses)

print("✅ Alle Karten wurden erstellt.")
