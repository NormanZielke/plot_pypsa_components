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

def create_bus_map(etrago):

    network = etrago.network
    args = etrago.args

    bussize = args.get("plot_settings", {}).get("bussize", 6)
    interest_area = args["interest_area"]

    # === load NUTS-3 Shapefile ===
    nuts_3_map = args["nuts_3_map"]
    nuts = gpd.read_file(nuts_3_map)

    # collect buses from network
    df = network.buses.copy()
    df["name"] = df.index

    # create GeoDataFrame for buses
    gdf_buses = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['x'], df['y']), crs="EPSG:4326")

    gdf_buses = gdf_buses.to_crs(nuts.crs)

    # === extract buses of interest area ===
    if args["plot_settings"]["plot_comps_of_interest"]:
        # extract interest-area from shapefile
        nuts_interest = nuts[nuts["NUTS_NAME"].str.contains(interest_area, case=False)]
        # buses in interest area
        gdf_buses = gdf_buses[gdf_buses.geometry.within(nuts_interest.union_all())]

    # === initiate map ===
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # insert title # -> optional
    #title = f"{etrago.name} – Buskarte"
    #title_html = f"""
    #     <h3 align="center" style="font-size:20px"><b>{title}</b></h3>
    #"""
    #m.get_root().html.add_child(folium.Element(title_html))

    # insert country borders
    folium.GeoJson(
        nuts,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # colors by carrier
    carriers = gdf_buses['carrier'].unique()
    colors = ["red", "blue", "green", "orange", "purple", "brown", "darkblue", "black", "cadetblue", "deepskyblue"]
    carrier_color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(carriers)}

    # insert markers for buses
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

    folium.LayerControl().add_to(m)

    # create legend
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

    # save busmap
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

    geojson_file = args["nuts_3_map"]

    # Bus- und Linkdaten laden
    buses = network.buses.copy()
    buses["name"] = buses.index
    links = network.links.copy()

    # GeoDataFrame für Busse
    gdf_buses = gpd.GeoDataFrame(buses, geometry=gpd.points_from_xy(buses['x'], buses['y']), crs="EPSG:4326")
    gdf_countries = gpd.read_file(geojson_file)
    gdf_buses = gdf_buses.to_crs(gdf_countries.crs)

    # Busname zu Koordinaten und Carrier zuordnen
    bus_lookup = gdf_buses.set_index('name')[['geometry', 'carrier']]

    # Farben pro Carrier zuweisen
    carriers = gdf_buses['carrier'].unique()
    colors = ["red", "blue", "green", "orange", "purple", "brown", "darkblue", "black", "cadetblue", "deepskyblue"]
    carrier_color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(carriers)}

    # Interaktive Karte erstellen
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # GeoJSON mit NUTS-Regionen hinzufügen
    folium.GeoJson(
        gdf_countries,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # Linien für Links plotten
    for _, row in links.iterrows():
        try:
            point0 = bus_lookup.loc[row['bus0'], 'geometry']
            point1 = bus_lookup.loc[row['bus1'], 'geometry']
            carrier = bus_lookup.loc[row['bus0'], 'carrier']
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

    # Legende hinzufügen
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

    # save links_map
    area = args["interest_area"]
    directory = f"maps/maps_{area}"
    os.makedirs(directory, exist_ok=True)
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

    # === NUTS-3 Shapefile laden ===
    nuts_3_map = args["nuts_3_map"]
    nuts = gpd.read_file(nuts_3_map)

    # === interest-area extrahieren ===
    interest_area = nuts[nuts["NUTS_NAME"].str.contains(args["interest_area"], case=False)]

    # === Busse in GeoDataFrame umwandeln ===
    bus_gdf = gpd.GeoDataFrame(
        network.buses.copy(),
        geometry=gpd.points_from_xy(network.buses.x, network.buses.y),
        crs="EPSG:4326"  # Koordinatensystem sicherstellen (ggf. anpassen!)
    )

    # In CRS der NUTS-3-Karte transformieren
    bus_gdf = bus_gdf.to_crs(nuts.crs)

    # === buses in interest area ===
    buses_interest_area = bus_gdf[bus_gdf.geometry.within(interest_area.union_all())]

    # === 6. Ergebnis: Liste der Busnamen ===
    bus_list = buses_interest_area.index.tolist()

    return bus_list
