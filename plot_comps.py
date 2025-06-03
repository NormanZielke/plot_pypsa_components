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
    carriers = gdf_buses['carrier'].unique()
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

    # load NUTS-3 Shapefile
    nuts_3_map = args["nuts_3_map"]
    nuts = gpd.read_file(nuts_3_map)

    if args["plot_settings"]["plot_comps_of_interest"]:
        # === filter lines connected to interest area ===
        lines = network.lines.copy()
        buses_interest = find_interest_buses(etrago)
        bus_names = buses_interest.index.tolist()

        # select only lines where either bus0 or bus1 is in area
        lines = lines[
            lines['bus0'].isin(bus_names) |
            lines['bus1'].isin(bus_names)
            ]

        # build filtered bus dataframe for geometry
        all_buses = network.buses.copy()
        all_buses["name"] = all_buses.index
        used_buses = set(lines['bus0']) | set(lines['bus1'])
        filtered_buses = all_buses.loc[all_buses.index.isin(used_buses)]

        gdf_buses = gpd.GeoDataFrame(
            filtered_buses,
            geometry=gpd.points_from_xy(filtered_buses['x'], filtered_buses['y']),
            crs="EPSG:4326"
        )
        gdf_buses = gdf_buses.to_crs(nuts.crs)

    else:
        # === full network ===
        lines = network.lines.copy()
        buses = network.buses.copy()
        buses["name"] = buses.index
        gdf_buses = gpd.GeoDataFrame(buses, geometry=gpd.points_from_xy(buses['x'], buses['y']), crs="EPSG:4326")
        gdf_buses = gdf_buses.to_crs(nuts.crs)

    # === prepare bus lookup ===
    bus_lookup = gdf_buses.set_index('name')['geometry']

    # === color normalization (s_max_pu) ===
    norm = mcolors.Normalize(vmin= network.lines['s_max_pu'].min(),
                             vmax= network.lines['s_max_pu'].max())
    cmap = cm.get_cmap('viridis')

    def s_max_pu_to_hex(s):
        rgba = cmap(norm(s))
        return mcolors.to_hex(rgba)

    # === initiate map ===
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # === add NUTS-3 - regions ===
    folium.GeoJson(
        nuts,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # === plot lines ===
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

    # === add legend (colorbar image) ===
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

    # === save lines_map ===
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)

    if args["plot_settings"]["plot_comps_of_interest"]:
        directory = os.path.join(directory, "plot_of_interest")
        os.makedirs(directory, exist_ok=True)
        output_file = os.path.join(directory, f"lines_interest_map_{area}.html")
    else:
        output_file = os.path.join(directory, f"lines_map_{area}.html")

    m.save(output_file)
    print(f"✅ Interaktive Linien-Karte gespeichert unter: {output_file}")

def create_buses_and_links_map(etrago):

    network = etrago.network
    args = etrago.args

    bussize = args.get("plot_settings", {}).get("bussize", 6)
    linkwidth = args.get("plot_settings", {}).get("linkwidth", 3)

    # === load NUTS-3 Shapefile ===
    nuts_3_map = args["nuts_3_map"]
    nuts = gpd.read_file(nuts_3_map)

    if args["plot_settings"]["plot_comps_of_interest"]:
        # Determine interest area buses directly
        gdf_buses_interest = find_interest_buses(etrago)

        # Left with at least one of these buses
        links = find_links_connected_to_buses(etrago)
        linked_buses = set(links['bus0']) | set(links['bus1'])

        # ALL buses that appear in links (for coordinates/lookup)
        all_buses = network.buses.copy()
        all_buses["name"] = all_buses.index
        buses_for_lookup = all_buses.loc[all_buses.index.isin(linked_buses)]

        gdf_buses_lookup = gpd.GeoDataFrame(
            buses_for_lookup,
            geometry=gpd.points_from_xy(buses_for_lookup['x'], buses_for_lookup['y']),
            crs="EPSG:4326"
        ).to_crs(nuts.crs)

        # Combine interest buses and lookup buses
        gdf_buses = pd.concat([gdf_buses_interest, gdf_buses_lookup])
        gdf_buses = gdf_buses[~gdf_buses.index.duplicated(keep='first')]

        # Move duplicates to avoid overlapping
        gdf_buses = apply_jitter_to_duplicate_buses(gdf_buses, epsg_m=3857, jitter_radius=500)
    else:
        # === load all buses and links ===
        buses = network.buses.copy()
        buses["name"] = buses.index
        gdf_buses = gpd.GeoDataFrame(buses, geometry=gpd.points_from_xy(buses['x'], buses['y']), crs="EPSG:4326").to_crs(nuts.crs)
        links = network.links.copy()

    # === create lookup for bus coordinates and carrier ===
    bus_lookup = gdf_buses.set_index('name')[['geometry', 'carrier']]

    # === initiate map ===
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # === add NUTS-3 - regions ===
    folium.GeoJson(
        nuts,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # === carrier colormaps ===
    carriers_buses = gdf_buses['carrier'].unique()
    carrier_color_map_buses, legend_order_buses = get_carrier_color_map(carriers_buses)

    carriers_links = links['carrier'].unique()
    carrier_color_map_links, legend_order_links = get_link_carrier_color_map(carriers_links)

    # === plot buses ===
    for _, row in gdf_buses.iterrows():
        color = carrier_color_map_buses.get(row['carrier'], "gray")
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

    # === plot links ===
    for _, row in links.iterrows():
        try:
            point0 = bus_lookup.loc[row['bus0'], 'geometry']
            point1 = bus_lookup.loc[row['bus1'], 'geometry']
            carrier = row['carrier']
            color = carrier_color_map_links.get(carrier, "gray")

            folium.PolyLine(
                locations=[[point0.y, point0.x], [point1.y, point1.x]],
                color=color,
                weight=linkwidth,
                opacity=0.8,
                tooltip=f"{row['bus0']} → {row['bus1']} ({carrier})"
            ).add_to(m)
        except KeyError:
            continue

    # === LayerControl & Legend ===
    folium.LayerControl().add_to(m)
    # separate Legende für Busse
    add_carrier_legend_to_map(m, carrier_color_map_buses, legend_order_buses, position="bottomleft", title="Bus-Carrier")

    # separate Legende für Links
    add_carrier_legend_to_map(m, carrier_color_map_links, legend_order_links, position="bottomright", title="Link-Carrier")

    # === save map ===
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)

    if args["plot_settings"]["plot_comps_of_interest"]:
        directory = f"{directory}/plot_of_interest"
        os.makedirs(directory, exist_ok=True)
        output_file = os.path.join(directory, f"buses_links_interest_map_{area}.html")
    else:
        output_file = os.path.join(directory, f"buses_links_map_{area}.html")

    m.save(output_file)
    print(f"✅ Interaktive Buses+Links-Karte gespeichert unter: {output_file}")

def create_buses_links_lines_map(etrago):

    network = etrago.network
    args = etrago.args

    bussize = args.get("plot_settings", {}).get("bussize", 6)
    linkwidth = args.get("plot_settings", {}).get("linkwidth", 3)
    linewidth = args.get("plot_settings", {}).get("linewidth", 3)

    # === load NUTS-3 Shapefile ===
    nuts_3_map = args["nuts_3_map"]
    nuts = gpd.read_file(nuts_3_map)

    if args["plot_settings"]["plot_comps_of_interest"]:
        # === Interest-Area-Busse direkt ermitteln ===
        gdf_buses_interest = find_interest_buses(etrago)

        # === Links & Lines mit mindestens einem Bus in Region ===
        links = find_links_connected_to_buses(etrago)
        lines = network.lines.copy()
        buses_interest_names = gdf_buses_interest.index.tolist()
        lines = lines[
            lines['bus0'].isin(buses_interest_names) |
            lines['bus1'].isin(buses_interest_names)
        ]

        # === ALLE verbundenen Busse (für Koordinaten- und Farbanzeige) ===
        all_buses = network.buses.copy()
        all_buses["name"] = all_buses.index
        buses_used = set(links['bus0']) | set(links['bus1']) | set(lines['bus0']) | set(lines['bus1'])
        buses_for_lookup = all_buses.loc[all_buses.index.isin(buses_used)]

        gdf_buses_lookup = gpd.GeoDataFrame(
            buses_for_lookup,
            geometry=gpd.points_from_xy(buses_for_lookup['x'], buses_for_lookup['y']),
            crs="EPSG:4326"
        ).to_crs(nuts.crs)

        # === Combine Interest-Busse und alle benötigten Busse ===
        gdf_buses = pd.concat([gdf_buses_interest, gdf_buses_lookup])
        gdf_buses = gdf_buses[~gdf_buses.index.duplicated(keep='first')]

        # === Jittering nur für Interest-Busse anwenden ===
        gdf_buses = apply_jitter_to_duplicate_buses(gdf_buses, epsg_m=3857, jitter_radius=500)

    else:
        # === vollständiges Netz laden ===
        links = network.links.copy()
        lines = network.lines.copy()
        buses = network.buses.copy()
        buses["name"] = buses.index
        gdf_buses = gpd.GeoDataFrame(
            buses,
            geometry=gpd.points_from_xy(buses['x'], buses['y']),
            crs="EPSG:4326"
        ).to_crs(nuts.crs)

    # === Lookup für Buskoordinaten + Carrier ===
    bus_lookup = gdf_buses.set_index('name')[['geometry', 'carrier']]

    # === Farbskala für Linienintensität (basierend auf dem vollständigen Netz) ===
    vmin = network.lines['s_max_pu'].min()
    vmax = network.lines['s_max_pu'].max()
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap('viridis')

    def s_max_pu_to_hex(s):
        rgba = cmap(norm(s))
        return mcolors.to_hex(rgba)

    # === Karte initialisieren ===
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # === NUTS-3-Grenzen hinzufügen ===
    folium.GeoJson(
        nuts,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # === Farbzuordnung für Carrier ===
    carriers_buses = gdf_buses['carrier'].unique()
    carrier_color_map_buses, legend_order_buses = get_carrier_color_map(carriers_buses)

    carriers_links = links['carrier'].unique()
    carrier_color_map_links, legend_order_links = get_link_carrier_color_map(carriers_links)

    # === Busse plotten ===
    for _, row in gdf_buses.iterrows():
        color = carrier_color_map_buses.get(row['carrier'], "gray")
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

    # === Links plotten ===
    for _, row in links.iterrows():
        try:
            point0 = bus_lookup.loc[row['bus0'], 'geometry']
            point1 = bus_lookup.loc[row['bus1'], 'geometry']
            carrier = row['carrier']
            color = carrier_color_map_links.get(carrier, "gray")

            folium.PolyLine(
                locations=[[point0.y, point0.x], [point1.y, point1.x]],
                color=color,
                weight=linkwidth,
                opacity=0.8,
                tooltip=f"{row['bus0']} → {row['bus1']} ({carrier})"
            ).add_to(m)
        except KeyError:
            continue

    # === Lines plotten (farblich nach s_max_pu) ===
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

    # === LayerControl + getrennte Legenden ===
    folium.LayerControl().add_to(m)

    add_carrier_legend_to_map(m, carrier_color_map_buses, legend_order_buses, position="bottomleft", title="Bus-Carrier")
    add_carrier_legend_to_map(m, carrier_color_map_links, legend_order_links, position="bottomright", title="Link-Carrier")

    # === Farblegende für s_max_pu ===
    fig, ax = plt.subplots(figsize=(4, 0.4))
    fig.subplots_adjust(bottom=0.5)
    cb1 = plt.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), cax=ax, orientation='horizontal')
    cb1.set_label('s_max_pu')

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    img_b64 = b64encode(img.read()).decode()

    legend_html = f"""
    <div style="position: fixed;
         bottom: 30px; left: 300px; width: 300px; height: auto;
         background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
         padding: 10px;">
    <b>Lines: s_max_pu</b><br>
    <img src="data:image/png;base64,{img_b64}" style="width:100%;"/>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # === save map ===
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)

    if args["plot_settings"]["plot_comps_of_interest"]:
        directory = f"{directory}/plot_of_interest"
        os.makedirs(directory, exist_ok=True)
        output_file = os.path.join(directory, f"buses_links_lines_interest_map_{area}.html")
    else:
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
    """
    Identifiziere alle Busse innerhalb von Regionen, deren Name
    in args["interest_area"] als Teilstring vorkommt.

    args["interest_area"] ist eine Liste von Namensfragmenten.
    """
    n = etrago.network.copy()
    args = etrago.args

    # GeoJSON einlesen
    nuts = gpd.read_file(args["nuts_3_map"])
    nuts["NUTS_NAME"] = nuts["NUTS_NAME"].str.strip()

    # Matchen über str.contains für alle Einträge in args["interest_area"]
    area_filter = args["interest_area"]
    mask = nuts["NUTS_NAME"].apply(lambda name: any(area.lower() in name.lower() for area in area_filter))
    interest_area = nuts[mask]

    if interest_area.empty:
        raise ValueError(f"Keine Region mit Teilstrings {area_filter} in GeoJSON gefunden.")

    # Busse zu GeoDataFrame
    buses = gpd.GeoDataFrame(
        n.buses.copy(),
        geometry=gpd.points_from_xy(n.buses.x, n.buses.y),
        crs="EPSG:4326"
    )

    # index als Spalte speichern
    buses["name"] = buses.index

    # CRS-Anpassung
    buses = buses.to_crs(interest_area.crs)

    # Leere Geometrien ausschließen
    interest_area = interest_area[~interest_area.geometry.is_empty & interest_area.geometry.notnull()]

    # Räumlicher Schnitt
    buses_in_area = buses[buses.geometry.within(interest_area.unary_union)]

    # print(f"{len(buses_in_area)} Busse in {area_filter} gefunden.")

    return buses_in_area

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

    # Liste der tatsächlich im Plot vorkommenden Carrier
    carriers_used = set(carriers)

    # Farbzuordnung nur für verwendete Carrier
    color_map = {carrier: predefined_colors.get(carrier, "gray") for carrier in carriers_used}

    # Geordnete Anzeige nur für verwendete Carrier
    legend_order = [c for c in predefined_colors if c in carriers_used] + \
                   [c for c in carriers_used if c not in predefined_colors]

    return color_map, legend_order

def get_link_carrier_color_map(carriers):
    """
    Gibt eine Farbzuordnung für Carrier in den Links zurück.
    Unbekannte Carrier werden mit 'gray' dargestellt.
    """
    predefined_colors = {
        'dsm': 'black',
        'central_heat_pump': 'purple',
        'central_resistive_heater': 'darkred',
        'rural_heat_pump': 'peru',
        'power_to_H2': 'mediumblue',  # Wasserstofferzeugung aus Strom
        'BEV_charger': 'deepskyblue',
        'DC': 'teal',  # Gleichstromverbindungen
        'OCGT': 'darkslategray',  # Open Cycle Gas Turbine
        'CH4': 'green',  # Methan
        'H2_to_power': 'slateblue',  # Rückverstromung von H2
        'central_heat_store_charger': 'lightcoral',
        'rural_heat_store_charger': 'burlywood',
        'central_heat_store_discharger': 'indianred',
        'rural_heat_store_discharger': 'saddlebrown',
        'central_gas_CHP': 'orange',
        'industrial_gas_CHP': 'forestgreen',
        'central_gas_CHP_heat': 'darkorange',
        'central_gas_boiler': 'brown',
        'CH4_to_H2': 'darkcyan',  # Methan-Reformierung
        'H2_to_CH4': 'goldenrod'  # Methanisierung
    }

    # nur tatsächlich genutzte Carrier berücksichtigen
    used_carriers = set(carriers)

    # Farbzuweisung nur für diese
    color_map = {carrier: predefined_colors.get(carrier, "gray") for carrier in used_carriers}

    # geordnete Anzeige in der Legende
    legend_order = [c for c in predefined_colors if c in used_carriers] + \
                   [c for c in used_carriers if c not in predefined_colors]

    return color_map, legend_order

    #ordered_carriers = list(predefined_colors.keys())

    #full_map = {carrier: predefined_colors.get(carrier, "gray") for carrier in carriers}
    #full_ordered = ordered_carriers + [c for c in carriers if c not in ordered_carriers]

    #return full_map, full_ordered

def add_carrier_legend_to_map(m, carrier_color_map, legend_order, position="bottomleft", title="Carrier Legende"):
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
    # CSS-Positionierung
    positions = {
        "bottomleft": "bottom: 30px; left: 30px;",
        "bottomright": "bottom: 30px; right: 30px;",
        "topleft": "top: 30px; left: 30px;",
        "topright": "top: 30px; right: 30px;"
    }

    location = positions.get(position, "bottom: 30px; left: 30px;")

    legend_html = f"""
    <div style="position: fixed; {location} width: 250px; height: auto;
         background-color: white; border:2px solid grey; z-index:9999; 
         font-size:14px; padding: 10px; line-height: 1.5;">
    <b>{title}</b><br>
    """

    for carrier in legend_order:
        if carrier in carrier_color_map:
            color = carrier_color_map[carrier]
            legend_html += (
                f'<div style="margin-bottom:4px;">'
                f'<span style="display:inline-block;width:16px;height:16px;'
                f'background:{color};margin-right:10px;border:1px solid #333;"></span>'
                f'{carrier}</div>'
            )

    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))
