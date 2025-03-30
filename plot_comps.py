import folium
import pandas as pd
import geopandas as gpd
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import io
from base64 import b64encode

def create_bus_map(csv_file: str, geojson_file: str, output_file: str = "bus_map_interactive.html"):
    """
    :param csv_file: buses.csv
    :param geojson_file: shape.file
    :param output_file: bus_map_interactive.html
    :return: create  bus_map_interactive.html
    """
    # --- Daten laden ---
    df = pd.read_csv(csv_file)
    gdf_buses = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['x'], df['y']), crs="EPSG:4326")
    gdf_countries = gpd.read_file(geojson_file)

    # --- Karte erstellen ---
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # --- GeoJSON hinzufügen ---
    folium.GeoJson(
        gdf_countries,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # --- Farben pro Carrier definieren ---
    carriers = gdf_buses['carrier'].unique()
    colors = ["red", "blue", "green", "orange", "purple", "brown", "darkblue", "black", "cadetblue", "deepskyblue"]
    carrier_color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(carriers)}

    # --- Marker hinzufügen ---
    for _, row in gdf_buses.iterrows():
        popup_text = f"<b>Bus:</b> {row['name']}<br><b>Carrier:</b> {row['carrier']}"
        tooltip_text = f"{row['name']} ({row['carrier']})"
        color = carrier_color_map[row['carrier']]

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=popup_text,
            tooltip=tooltip_text
        ).add_to(m)

    # --- Legende als HTML-Overlay hinzufügen ---
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

    # --- Speichern ---
    m.save(output_file)
    print(f"Interaktive Karte gespeichert unter: {output_file}")

def create_links_map(buses_csv: str, links_csv: str, geojson_file: str, output_file: str = "links_map_interactive.html"):
    """
    :param buses_csv:
    :param links_csv:
    :param geojson_file:
    :param output_file:
    :return:
    """
    # Bus- und Linkdaten laden
    buses_df = pd.read_csv(buses_csv)
    links_df = pd.read_csv(links_csv)

    # GeoDataFrame für Busse erzeugen
    gdf_buses = gpd.GeoDataFrame(
        buses_df,
        geometry=gpd.points_from_xy(buses_df['x'], buses_df['y']),
        crs="EPSG:4326"
    )

    # Busname zu Koordinaten und Carrier zuordnen
    bus_lookup = gdf_buses.set_index('name')[['geometry', 'carrier']]

    # Farben pro Carrier zuweisen
    carriers = gdf_buses['carrier'].unique()
    colors = ["red", "blue", "green", "orange", "purple", "brown", "darkblue", "black", "cadetblue", "deepskyblue"]
    carrier_color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(carriers)}

    # Interaktive Karte erstellen
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # GeoJSON mit NUTS-Regionen hinzufügen
    gdf_countries = gpd.read_file(geojson_file)
    folium.GeoJson(
        gdf_countries,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # Linien für Links plotten
    for _, row in links_df.iterrows():
        try:
            point0 = bus_lookup.loc[row['bus0'], 'geometry']
            point1 = bus_lookup.loc[row['bus1'], 'geometry']
            carrier = bus_lookup.loc[row['bus0'], 'carrier']
            color = carrier_color_map.get(carrier, "gray")

            line = folium.PolyLine(
                locations=[[point0.y, point0.x], [point1.y, point1.x]],
                color=color,
                weight=3,
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

    # Karte speichern
    m.save(output_file)
    print(f"✅ Interaktive Link-Karte gespeichert unter: {output_file}")

def create_lines_map(buses_csv: str, lines_csv: str, geojson_file: str, output_file: str = "lines_map_interactive.html"):
    # Bus- und Liniendaten laden
    buses_df = pd.read_csv(buses_csv)
    lines_df = pd.read_csv(lines_csv)

    # GeoDataFrame für Busse erzeugen
    gdf_buses = gpd.GeoDataFrame(
        buses_df,
        geometry=gpd.points_from_xy(buses_df['x'], buses_df['y']),
        crs="EPSG:4326"
    )

    # Mapping von Busnamen zu Geometrie
    bus_lookup = gdf_buses.set_index('name')['geometry']

    # Farbskala vorbereiten
    norm = mcolors.Normalize(vmin=lines_df['s_max_pu'].min(), vmax=lines_df['s_max_pu'].max())
    cmap = cm.get_cmap('viridis')

    def s_max_pu_to_hex(s):
        rgba = cmap(norm(s))
        return mcolors.to_hex(rgba)

    # Interaktive Karte
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # GeoJSON hinzufügen
    gdf_countries = gpd.read_file(geojson_file)
    folium.GeoJson(
        gdf_countries,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # Linien zeichnen
    for _, row in lines_df.iterrows():
        try:
            point0 = bus_lookup.loc[row['bus0']]
            point1 = bus_lookup.loc[row['bus1']]
            color = s_max_pu_to_hex(row['s_max_pu'])

            folium.PolyLine(
                locations=[[point0.y, point0.x], [point1.y, point1.x]],
                color=color,
                weight=3,
                opacity=0.8,
                tooltip=f"{row['bus0']} → {row['bus1']}<br>s_max_pu: {row['s_max_pu']:.2f}"
            ).add_to(m)
        except KeyError:
            continue

    # Legende als Farbbalken mit matplotlib erzeugen
    fig, ax = plt.subplots(figsize=(4, 0.4))
    fig.subplots_adjust(bottom=0.5)

    cb1 = plt.colorbar(
        cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=ax,
        orientation='horizontal'
    )
    cb1.set_label('s_max_pu')

    # Grafik als Base64-Bild einbetten
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

    # Speichern
    m.save(output_file)
    print(f"✅ Interaktive Linien-Karte mit Farbverlauf & Legende gespeichert unter: {output_file}")


def create_buses_and_links_map(buses_csv: str, links_csv: str, geojson_file: str, output_file: str = "buses_links_map.html"):
    # --- Daten laden ---
    df = pd.read_csv(buses_csv)
    links_df = pd.read_csv(links_csv)

    # GeoDataFrame für Busse
    gdf_buses = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['x'], df['y']), crs="EPSG:4326")

    # GeoDataFrame für GeoJSON
    gdf_countries = gpd.read_file(geojson_file)

    # Lookup für Buskoordinaten und Carrier
    bus_lookup = gdf_buses.set_index('name')[['geometry', 'carrier']]

    # Interaktive Karte initialisieren
    m = folium.Map(location=[gdf_buses.geometry.y.mean(), gdf_buses.geometry.x.mean()], zoom_start=7)

    # GeoJSON-Grenzen hinzufügen
    folium.GeoJson(
        gdf_countries,
        name="NUTS-3 Regions",
        tooltip=folium.GeoJsonTooltip(fields=["NUTS_NAME"], aliases=["Region: "]),
        style_function=lambda x: {"fillColor": "gray", "color": "black", "weight": 1, "fillOpacity": 0.2}
    ).add_to(m)

    # --- Farben pro Carrier definieren ---
    carriers = gdf_buses['carrier'].unique()
    colors = ["red", "blue", "green", "orange", "purple", "brown", "darkblue", "black", "cadetblue","deepskyblue"]
    carrier_color_map = {carrier: colors[i % len(colors)] for i, carrier in enumerate(carriers)}

    # --- Busse als Punkte hinzufügen ---
    for _, row in gdf_buses.iterrows():
        popup_text = f"<b>Bus:</b> {row['name']}<br><b>Carrier:</b> {row['carrier']}"
        tooltip_text = f"{row['name']} ({row['carrier']})"
        color = carrier_color_map[row['carrier']]

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=popup_text,
            tooltip=tooltip_text
        ).add_to(m)

    # --- Links als Linien hinzufügen ---
    for _, row in links_df.iterrows():
        try:
            point0 = bus_lookup.loc[row['bus0'], 'geometry']
            point1 = bus_lookup.loc[row['bus1'], 'geometry']
            carrier = bus_lookup.loc[row['bus0'], 'carrier']
            color = carrier_color_map.get(carrier, "gray")

            folium.PolyLine(
                locations=[[point0.y, point0.x], [point1.y, point1.x]],
                color=color,
                weight=3,
                opacity=0.8,
                tooltip=f"{row['bus0']} → {row['bus1']} ({carrier})"
            ).add_to(m)
        except KeyError:
            continue  # falls ein Busname fehlt

    # --- Legende hinzufügen ---
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
    m.save(output_file)
    print(f"✅ Interaktive Karte mit Bussen und Links gespeichert unter: {output_file}")
