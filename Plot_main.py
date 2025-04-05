import logging

from network_visual import Etrago1

logger = logging.getLogger(__name__)

# set format for logging massages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

args = {
    # == INPUT ==
    "pypsa_network":"pypsa_results/results_ingolstadt", # path to pypsa results
    "nuts_3_map" : "germany-de-nuts-3-regions.geojson", # path to .geojson nuts-3 file
    # copied from etrago
    "interest_area" : "Ingolstadt",
    "network_clustering": {
        "n_clusters_AC": 30,
        "n_clusters_gas": 14,
    },
    "name" : "Ingolstadt_30_14",  # {interest_area}_{#AC_Buses}_{#CH_4_Buses}
    # Visualisation
    "plot_settings":{
        "plot_comps_of_interest": False,
        "bussize": 10,
        "linkwidth": 5,
        "linewidth": 3,
    },
}

etrago = Etrago1(args, csv_folder = args["pypsa_network"])

# create maps

#etrago.create_bus_map()
#etrago.create_links_map()
#etrago.create_lines_map()
#etrago.create_buses_and_links_map()
#etrago.create_buses_links_lines_map()

etrago.create_maps()

logger.info("Maps successfully created.")

interest_buses = etrago.find_interest_buses()

print(interest_buses)
print(len(interest_buses))

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


