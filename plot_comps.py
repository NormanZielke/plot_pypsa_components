import os
import geopandas as gpd
from shapely.geometry import Point
import folium
import pandas as pd
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import io
from base64 import b64encode
import numpy as np
from shapely.affinity import translate

def create_bus_map(etrago):

    network = etrago.network
    args = etrago.args

    bussize = args.get("plot_settings", {}).get("bussize", 6)

    # === load NUTS-3 Shapefile ===
    nuts_3_map = args["nuts_3_map"]
    nuts = gpd.read_file(nuts_3_map)

    # === collect buses from network ===
    df = network.buses.copy()
    df["name"] = df.index

    # create GeoDataFrame for buses
    gdf_buses = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['x'], df['y']), crs="EPSG:4326")
    # transform gdf_buses into CRS of the NUTS-3 map
    gdf_buses = gdf_buses.to_crs(nuts.crs)

    # === select buses of interest area ===
    if args["plot_settings"]["plot_comps_of_interest"]:
        gdf_buses = find_interest_buses(etrago)
        # Move duplicates to avoid overlapping
        gdf_buses = apply_jitter_to_duplicate_buses(gdf_buses, epsg_m=3857, jitter_radius=500)

    # === initiate map ===
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # insert title # -> optional
    #title = f"{etrago.name} – Buskarte"
    #title_html = f"""
    #     <h3 align="center" style="font-size:20px"><b>{title}</b></h3>
    #"""
    #m.get_root().html.add_child(folium.Element(title_html))

    # === add NUTS-3 - regions ===
    folium.GeoJson(
        nuts,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # === colors by carrier ===
    carriers = network.buses['carrier'].unique()
    carrier_color_map, legend_order = get_carrier_color_map(carriers)

    # === plot buses ===
    for _, row in gdf_buses.iterrows():
        color = carrier_color_map[row['carrier']]
        popup_text = f"<b>Bus:</b> {row['name']}<br><b>Carrier:</b> {row['carrier']}"
        tooltip_text = f"{row['name']} ({row['carrier']})"
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=bussize,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=popup_text,
            tooltip=tooltip_text
        ).add_to(m)

    # === LayerControl & Legend ===
    folium.LayerControl().add_to(m)
    add_carrier_legend_to_map(m, carrier_color_map, legend_order)

    # === save busmap ===
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)

    if args["plot_settings"]["plot_comps_of_interest"]:
        directory = f"maps/maps_{area}/plot_of_interest"
        os.makedirs(directory, exist_ok=True)
        output_file = os.path.join(directory, f"buses_of_interest_map_{area}.html")
    else:
        output_file = os.path.join(directory, f"bus_map_{area}.html")

    m.save(output_file)
    print(f"✅ Interaktive Bus-Karte gespeichert unter: {output_file}")

def create_links_map(etrago):

    network = etrago.network
    args = etrago.args

    linkwidth = args.get("plot_settings", {}).get("linkwidth", 3)

    # load NUTS-3 Shapefile
    nuts_3_map = args["nuts_3_map"]
    nuts = gpd.read_file(nuts_3_map)

    if args["plot_settings"]["plot_comps_of_interest"]:
        # select buses and links of interest area
        links = find_links_connected_to_buses(etrago)
        # Load all buses that appear in these links
        used_buses = set(links['bus0']) | set(links['bus1'])

        all_buses = network.buses.copy()
        all_buses["name"] = all_buses.index
        filtered_buses = all_buses.loc[all_buses.index.isin(used_buses)]
        gdf_buses = gpd.GeoDataFrame(
            filtered_buses,
            geometry=gpd.points_from_xy(filtered_buses['x'], filtered_buses['y']),
            crs="EPSG:4326"
        )
        # transform bus_gdf into CRS of the NUTS-3 map
        gdf_buses = gdf_buses.to_crs(nuts.crs)
        # Move duplicates to avoid overlapping
        gdf_buses = apply_jitter_to_duplicate_buses(gdf_buses, epsg_m=3857, jitter_radius=500)

    else:
        # collect buses and links from network
        buses = network.buses.copy()
        buses["name"] = buses.index
        links = network.links.copy()
        gdf_buses = gpd.GeoDataFrame(buses, geometry=gpd.points_from_xy(buses['x'], buses['y']), crs="EPSG:4326")
        # transform bus_gdf into CRS of the NUTS-3 map
        gdf_buses = gdf_buses.to_crs(nuts.crs)

    # Assign bus name to coordinates and carrier
    bus_lookup = gdf_buses.set_index('name')[['geometry', 'carrier']]

    # === initiate map ===
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # add NUTS-3 - regions
    folium.GeoJson(
        nuts,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # colors by carrier
    carriers = links['carrier'].unique()
    carrier_color_map, legend_order = get_link_carrier_color_map(carriers)

    # plot links
    for _, row in links.iterrows():
        try:
            point0 = bus_lookup.loc[row['bus0'], 'geometry']
            point1 = bus_lookup.loc[row['bus1'], 'geometry']
            carrier = row['carrier']
            color = carrier_color_map.get(carrier, "gray")

            line = folium.PolyLine(
                locations=[[point0.y, point0.x], [point1.y, point1.x]],
                color=color,
                weight=linkwidth,
                opacity=0.8,
                tooltip=f"{row['bus0']} → {row['bus1']} ({carrier})"
            )
            line.add_to(m)
        except KeyError:
            continue  # Busname nicht gefunden – überspringen

    # === LayerControl & Legend ===
    folium.LayerControl().add_to(m)
    add_carrier_legend_to_map(m, carrier_color_map, legend_order)

    # === save links_map ===
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)

    if args["plot_settings"]["plot_comps_of_interest"]:
        directory = f"maps/maps_{area}/plot_of_interest"
        os.makedirs(directory, exist_ok=True)
        output_file = os.path.join(directory, f"links_interest_map_{area}.html")
    else:
        output_file = os.path.join(directory, f"links_map_{area}.html")

    m.save(output_file)
    print(f"✅ Interaktive Link-Karte gespeichert unter: {output_file}")

def create_lines_map(etrago):

    network = etrago.network
    args = etrago.args
    linewidth = args.get("plot_settings", {}).get("linewidth", 3)
    geojson_file = args["nuts_3_map"]

    # Daten laden
    buses = network.buses.copy()
    buses["name"] = buses.index
    lines = network.lines.copy()

    gdf_buses = gpd.GeoDataFrame(buses, geometry=gpd.points_from_xy(buses['x'], buses['y']), crs="EPSG:4326")
    gdf_countries = gpd.read_file(geojson_file)
    gdf_buses = gdf_buses.to_crs(gdf_countries.crs)
    bus_lookup = gdf_buses.set_index('name')['geometry']

    # Farbskala vorbereiten
    norm = mcolors.Normalize(vmin=lines['s_max_pu'].min(), vmax=lines['s_max_pu'].max())
    cmap = cm.get_cmap('viridis')

    def s_max_pu_to_hex(s):
        rgba = cmap(norm(s))
        return mcolors.to_hex(rgba)

    # Karte initialisieren
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    folium.GeoJson(
        gdf_countries,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    for _, row in lines.iterrows():
        try:
            p0 = bus_lookup.loc[row['bus0']]
            p1 = bus_lookup.loc[row['bus1']]
            color = s_max_pu_to_hex(row['s_max_pu'])

            folium.PolyLine(
                locations=[[p0.y, p0.x], [p1.y, p1.x]],
                color=color,
                weight=linewidth,
                opacity=0.9,
                tooltip=f"{row['bus0']} → {row['bus1']}<br>s_max_pu: {row['s_max_pu']:.2f}"
            ).add_to(m)
        except KeyError:
            continue

    # Legende mit matplotlib-Farbskala einbetten
    fig, ax = plt.subplots(figsize=(4, 0.4))
    fig.subplots_adjust(bottom=0.5)

    cb1 = plt.colorbar(
        cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=ax,
        orientation='horizontal'
    )
    cb1.set_label('s_max_pu')

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    img_b64 = b64encode(img.read()).decode()

    legend_html = f"""
    <div style="position: fixed;
         bottom: 30px; left: 30px; width: 300px; height: auto;
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px;">
    <b>Farbskala: s_max_pu</b><br>
    <img src="data:image/png;base64,{img_b64}" style="width:100%;"/>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # save lines_map
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)
    output_file = os.path.join(directory, f"lines_map_{area}.html")

    m.save(output_file)
    print(f"✅ Interaktive Linien-Karte gespeichert unter: {output_file}")

def create_buses_and_links_map(etrago):

    network = etrago.network
    args = etrago.args
    bussize = args.get("plot_settings", {}).get("bussize", 6)
    linkwidth = args.get("plot_settings", {}).get("linkwidth", 3)
    geojson_file = args["nuts_3_map"]

    # Daten laden
    buses = network.buses.copy()
    buses["name"] = buses.index
    links = network.links.copy()

    # GeoDataFrame für Busse
    gdf_buses = gpd.GeoDataFrame(buses, geometry=gpd.points_from_xy(buses['x'], buses['y']), crs="EPSG:4326")
    # GeoDataFrame für GeoJSON
    gdf_countries = gpd.read_file(geojson_file)
    #
    gdf_buses = gdf_buses.to_crs(gdf_countries.crs)
    # Lookup für Buskoordinaten und Carrier
    bus_lookup = gdf_buses.set_index('name')[['geometry', 'carrier']]

    # --- Farben pro Carrier definieren ---
    carriers = gdf_buses['carrier'].unique()
    colors = ["red", "blue", "green", "orange", "purple", "brown", "darkblue", "black", "cadetblue", "deepskyblue"]
    carrier_color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(carriers)}

    # Interaktive Karte initialisieren
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # GeoJSON-Grenzen hinzufügen
    folium.GeoJson(
        gdf_countries,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # --- Busse als Punkte hinzufügen ---
    for _, row in gdf_buses.iterrows():
        color = carrier_color_map[row['carrier']]
        popup_text = f"<b>Bus:</b> {row['name']}<br><b>Carrier:</b> {row['carrier']}"
        tooltip_text = f"{row['name']} ({row['carrier']})"
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=bussize,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=popup_text,
            tooltip=tooltip_text
        ).add_to(m)

    # --- Links als Linien hinzufügen ---
    for _, row in links.iterrows():
        try:
            point0 = bus_lookup.loc[row['bus0'], 'geometry']
            point1 = bus_lookup.loc[row['bus1'], 'geometry']
            carrier = bus_lookup.loc[row['bus0'], 'carrier']
            color = carrier_color_map.get(carrier, "gray")
            folium.PolyLine(
                locations=[[point0.y, point0.x], [point1.y, point1.x]],
                color=color,
                weight=linkwidth,
                opacity=0.8,
                tooltip=f"{row['bus0']} → {row['bus1']} ({carrier})"
            ).add_to(m)
        except KeyError:
            continue

    # Legende
    legend_html = """
    <div style="position: fixed; 
         bottom: 30px; left: 30px; width: 200px; height: auto; 
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px;">
    <b>Carrier Legende</b><br>
    """
    for carrier, color in carrier_color_map.items():
        legend_html += f'<i style="background:{color};width:12px;height:12px;float:left;margin-right:8px;display:inline-block;"></i>{carrier}<br>'
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))

    # --- Layer Control ---
    folium.LayerControl().add_to(m)

    # --- Karte speichern ---
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)
    output_file = os.path.join(directory, f"buses_links_map_{area}.html")

    m.save(output_file)
    print(f"✅ Interaktive Bus+Link-Karte gespeichert unter: {output_file}")

def create_buses_links_lines_map(etrago):

    network = etrago.network
    args = etrago.args
    bussize = args.get("plot_settings", {}).get("bussize", 6)
    linkwidth = args.get("plot_settings", {}).get("linkwidth", 3)
    linewidth = args.get("plot_settings", {}).get("linewidth", 2)
    geojson_file = args["nuts_3_map"]

    # Daten
    buses = network.buses.copy()
    buses["name"] = buses.index
    links = network.links.copy()
    lines = network.lines.copy()

    # GeoDataFrame für Busse
    gdf_buses = gpd.GeoDataFrame(buses, geometry=gpd.points_from_xy(buses['x'], buses['y']), crs="EPSG:4326")
    # GeoDataFrame für GeoJSON
    gdf_countries = gpd.read_file(geojson_file)
    #
    gdf_buses = gdf_buses.to_crs(gdf_countries.crs)
    # Lookup für Buskoordinaten und Carrier
    bus_lookup = gdf_buses.set_index('name')[['geometry', 'carrier']]

    # Farbdefinitionen
    carriers = gdf_buses['carrier'].unique()
    colors = ["red", "blue", "green", "orange", "purple", "brown", "darkblue", "black", "cadetblue", "deepskyblue"]
    carrier_color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(carriers)}

    # Farbskala für s_max_pu
    norm = mcolors.Normalize(vmin=lines['s_max_pu'].min(), vmax=lines['s_max_pu'].max())
    cmap = cm.get_cmap('viridis')
    def s_max_pu_to_hex(s): return mcolors.to_hex(cmap(norm(s)))

    # Karte erstellen
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # GeoJSON hinzufügen
    folium.GeoJson(
        gdf_countries,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # Busse plotten
    for _, row in gdf_buses.iterrows():
        color = carrier_color_map[row['carrier']]
        popup_text = f"<b>Bus:</b> {row['name']}<br><b>Carrier:</b> {row['carrier']}"
        tooltip_text = f"{row['name']} ({row['carrier']})"
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=bussize,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=popup_text,
            tooltip=tooltip_text
        ).add_to(m)

    # Links plotten
    for _, row in links.iterrows():
        try:
            p0 = bus_lookup.loc[row['bus0'], 'geometry']
            p1 = bus_lookup.loc[row['bus1'], 'geometry']
            carrier = bus_lookup.loc[row['bus0'], 'carrier']
            color = carrier_color_map.get(carrier, "gray")
            folium.PolyLine(
                locations=[[p0.y, p0.x], [p1.y, p1.x]],
                color=color,
                weight=linkwidth,
                opacity=0.8,
                tooltip=f"{row['bus0']} → {row['bus1']} ({carrier})"
            ).add_to(m)
        except KeyError:
            continue

    # Lines plotten
    for _, row in lines.iterrows():
        try:
            p0 = bus_lookup.loc[row['bus0'], 'geometry']
            p1 = bus_lookup.loc[row['bus1'], 'geometry']
            color = s_max_pu_to_hex(row['s_max_pu'])
            folium.PolyLine(
                locations=[[p0.y, p0.x], [p1.y, p1.x]],
                color=color,
                weight=linewidth,
                opacity=0.9,
                tooltip=f"{row['bus0']} → {row['bus1']}<br>s_max_pu: {row['s_max_pu']:.2f}"
            ).add_to(m)
        except KeyError:
            continue

    # Legende: Carrier
    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; width: 200px; height: auto;
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px;">
    <b>Carrier Legende</b><br>
    """
    for carrier, color in carrier_color_map.items():
        legend_html += f'<i style="background:{color};width:12px;height:12px;float:left;margin-right:8px;display:inline-block;"></i>{carrier}<br>'
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))

    # Farbbalken für s_max_pu erzeugen
    fig, ax = plt.subplots(figsize=(4, 0.4))
    fig.subplots_adjust(bottom=0.5)
    cb1 = plt.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), cax=ax, orientation='horizontal')
    cb1.set_label('s_max_pu')
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    img_b64 = b64encode(img.read()).decode()

    colorbar_html = f"""
    <div style="position: fixed; bottom: 30px; left: 250px; width: 300px; height: auto;
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px;">
    <b>Lines: s_max_pu</b><br>
    <img src="data:image/png;base64,{img_b64}" style="width:100%;"/>
    </div>
    """
    m.get_root().html.add_child(folium.Element(colorbar_html))

    # --- Karte speichern ---
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)
    output_file = os.path.join(directory, f"buses_links_lines_map_{area}.html")

    m.save(output_file)
    print(f"✅ Interaktive Komplett-Karte gespeichert unter: {output_file}")

def create_maps(etrago):
    create_bus_map(etrago)
    create_links_map(etrago)
    create_lines_map(etrago)
    create_buses_and_links_map(etrago)
    create_buses_links_lines_map(etrago)

def find_interest_buses(etrago):
    network = etrago.network
    args = etrago.args

    # NUTS-3 Shapefile laden
    nuts_3_map = args["nuts_3_map"]
    nuts = gpd.read_file(nuts_3_map)

    # select interest area
    interest_area = nuts[nuts["NUTS_NAME"].str.contains(args["interest_area"], case=False)]

    # Busse in GeoDataFrame umwandeln
    bus_gdf = gpd.GeoDataFrame(
        network.buses.copy(),
        geometry=gpd.points_from_xy(network.buses.x, network.buses.y),
        crs="EPSG:4326"
    )

    # index als Spalte speichern
    bus_gdf["name"] = bus_gdf.index

    # transform bus_gdf into CRS of the NUTS-3 map
    bus_gdf = bus_gdf.to_crs(nuts.crs)

    # select buses in interest area
    buses_interest_area = bus_gdf[bus_gdf.geometry.within(interest_area.union_all())]

    # === 6. Ergebnis: Liste der Busnamen ===
    #bus_list = buses_interest_area.index.tolist()

    return buses_interest_area

def find_links_connected_to_buses(etrago):
    network = etrago.network

    # find buses in interst area
    gdf_buses_interest = find_interest_buses(etrago)
    buses_of_interest = gdf_buses_interest.index.tolist()

    # Links where bus0 or bus1 is in the area of interest
    links = network.links.copy()
    connected_links = links[
        (links["bus0"].isin(buses_of_interest)) |
        (links["bus1"].isin(buses_of_interest))
    ]

    return connected_links

def apply_jitter_to_duplicate_buses(gdf_buses, epsg_m=3857, jitter_radius=500):
    """
    Verschiebt Busse mit identischen Koordinaten leicht, damit sie in Karten
    (z. B. mit Folium) sichtbar bleiben und sich nicht überdecken.

    Parameters
    ----------
    gdf_buses : GeoDataFrame
        GeoDataFrame mit Bus-Geometrien.
    epsg_m : int
        Temporäres metrisches Koordinatensystem für Verschiebung (z. B. 3857 oder 25832).
    jitter_radius : float
        Verschiebungsradius in Metern (bzw. CRS-Einheit), Standard: 500m.

    Returns
    -------
    GeoDataFrame mit jittered geometries im ursprünglichen CRS.
    """

    original_crs = gdf_buses.crs
    gdf_proj = gdf_buses.to_crs(epsg=epsg_m)

    # Koordinaten als Tupel extrahieren
    coord_series = gdf_proj.geometry.apply(lambda g: (round(g.x, 1), round(g.y, 1)))
    coord_counts = coord_series.value_counts()

    # Koordinaten mit mehrfach belegten Punkten
    duplicate_coords = coord_counts[coord_counts > 1].index

    for coord in duplicate_coords:
        idxs = coord_series[coord_series == coord].index
        for i, idx in enumerate(idxs):
            angle = 2 * np.pi * i / len(idxs)
            dx = jitter_radius * np.cos(angle)
            dy = jitter_radius * np.sin(angle)
            gdf_proj.at[idx, 'geometry'] = translate(gdf_proj.at[idx, 'geometry'], xoff=dx, yoff=dy)

    # zurücktransformieren in ursprüngliches CRS
    return gdf_proj.to_crs(original_crs)

def get_carrier_color_map(carriers):
    """
    Returns a consistent color assignment for known carriers.
    """
    predefined_colors = {
        "AC": "red",
        "CH4": "green",
        "H2_grid": "deepskyblue",
        "H2_saltcavern": "orange",
        "Li_ion": "cadetblue",
        "central_heat": "darkred",
        "central_heat_store": "lightcoral",
        "dsm": "black",
        "rural_heat": "peru",
        "rural_heat_store": "darkorange"
    }

    # Alle bekannten Carrier in fester Reihenfolge
    ordered_carriers = list(predefined_colors.keys())

    # Rückgabe: alle bekannten + evtl. unbekannte Carrier (in beliebiger Reihenfolge)
    complete_carrier_set = list(carriers)
    full_map = {carrier: predefined_colors.get(carrier, "gray") for carrier in complete_carrier_set}

    # Reihenfolge in der Legende: bekannte zuerst (in Wunschreihenfolge), danach evtl. unbekannte
    full_ordered = ordered_carriers + [c for c in complete_carrier_set if c not in ordered_carriers]

    return full_map, full_ordered

def get_link_carrier_color_map(carriers):
    """
    Gibt eine Farbzuordnung für Carrier in den Links zurück.
    Unbekannte Carrier werden mit 'gray' dargestellt.
    """
    predefined_colors = {
        'BEV_charger': 'deepskyblue',
        'central_gas_CHP': 'orange',
        'central_gas_CHP_heat': 'darkorange',
        'central_gas_boiler': 'brown',
        'central_heat_pump': 'purple',
        'central_heat_store_charger': 'lightcoral',
        'central_heat_store_discharger': 'indianred',
        'central_resistive_heater': 'darkred',
        'dsm': 'black',
        'industrial_gas_CHP': 'green',
        'rural_heat_pump': 'peru',
        'rural_heat_store_charger': 'burlywood',
        'rural_heat_store_discharger': 'saddlebrown'
    }

    ordered_carriers = list(predefined_colors.keys())

    full_map = {carrier: predefined_colors.get(carrier, "gray") for carrier in carriers}
    full_ordered = ordered_carriers + [c for c in carriers if c not in ordered_carriers]

    return full_map, full_ordered

def add_carrier_legend_to_map(m, carrier_color_map, legend_order):
    """
    Adds a color-coded legend to the map based on the carrier_color_map.

    Parameters
    ----------
    m : folium.Map
        The map to which the legend is added.
    carrier_color_map : dict
        Dictionary with carrier names as keys and colors as values.
    legend_order : list
        Sequence of carriers for display in the legend.
    """

    legend_html = """
        <div style="position: fixed; 
             bottom: 30px; left: 30px; width: 200px; height: auto; 
             background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
             padding: 10px;">
        <b>Carrier Legende</b><br>
    """

    for carrier in legend_order:
        if carrier in carrier_color_map:
            color = carrier_color_map[carrier]
            legend_html += (
                f'<i style="background:{color};width:12px;height:12px;float:left;'
                f'margin-right:8px;display:inline-block;"></i>{carrier}<br>'
            )

    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))
