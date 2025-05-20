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
import pypsa

from plot_comps import(
    find_interest_buses,
    find_links_connected_to_buses
)

#path_to_results = "pypsa_results/2025-04-18_etrago_test_set4_appl.log"

def capacities_opt(etrago,scn = "Base_scn"):
    network = etrago.network.copy()

    # === optimized links ===
    # optimized links - global
    links_opt = network.links[network.links.p_nom_extendable == True]
    links_opt_cap = links_opt.groupby("carrier")["p_nom_opt"].sum().rename(scn)

    # optimized links - interest
    connected_links = find_links_connected_to_buses(etrago)
    connected_links_optimized = connected_links[connected_links.p_nom_extendable == True]
    links_ing_opt_cap = connected_links_optimized.groupby("carrier")["p_nom_opt"].sum().rename(scn)

    # === optimized stores ===
    # optimized stores - global
    stores_opt = network.stores[network.stores.e_nom_extendable == True]
    stores_opt_cap = stores_opt.groupby("carrier")["e_nom_opt"].sum().rename(scn)

    # optimized stores - interest
    buses_interest_area = find_interest_buses(etrago)
    bus_list = buses_interest_area.index.tolist()
    stores_ing = network.stores[network.stores["bus"].isin(bus_list)]
    stores_ing_opt = stores_ing[stores_ing.e_nom_extendable == True]
    stores_ing_opt_cap = stores_ing_opt.groupby("carrier")["e_nom_opt"].sum().rename(scn)

    # === optimized storage_units ===
    # optimized storage_units - global
    storage_units_opt = network.storage_units[network.storage_units.p_nom_extendable == True]
    storage_units_opt_cap = storage_units_opt.groupby("carrier")["p_nom_opt"].sum().rename(scn)
    # optimized storage_units - interest
    storage_units_ing_opt = storage_units_opt[storage_units_opt.bus.isin(bus_list)]
    storage_units_ing_opt_cap = storage_units_ing_opt.groupby("carrier")["p_nom_opt"].sum().rename(scn)

    # === collect capacities ===
    capacities_opt = pd.concat([links_opt_cap, stores_opt_cap, storage_units_opt_cap], axis=0)
    capacities_ing_opt = pd.concat([links_ing_opt_cap, stores_ing_opt_cap, storage_units_ing_opt_cap], axis=0)

    return capacities_opt, capacities_ing_opt

def capacities_opt_techs_global(capacities_opt):

    # Technologies
    H2_techs_1 = ["H2_to_CH4", "H2_to_power"]
    H2_techs_2 = ["power_to_H2", "CH4_to_H2"]
    stores_tech_1 = ["central_heat_store"]
    stores_tech_2 = ["rural_heat_store", "H2_overground", "H2_underground"]
    charger = ["central_heat_store_charger", "central_heat_store_discharger", "rural_heat_store_charger",
               "rural_heat_store_discharger"]
    storage_u = ["battery"]

    df_capacities_opt = pd.DataFrame(capacities_opt)

    df_capacities_opt_H2_1 = df_capacities_opt.loc[df_capacities_opt.index.isin(H2_techs_1)]
    df_capacities_opt_H2_2 = df_capacities_opt.loc[df_capacities_opt.index.isin(H2_techs_2)]
    df_capacities_opt_stores_1 = df_capacities_opt.loc[df_capacities_opt.index.isin(stores_tech_1)]
    df_capacities_opt_stores_2 = df_capacities_opt.loc[df_capacities_opt.index.isin(stores_tech_2)]
    df_capacities_opt_charger = df_capacities_opt.loc[df_capacities_opt.index.isin(charger)]
    df_capacities_opt_bat = df_capacities_opt.loc[df_capacities_opt.index.isin(storage_u)]

    return (df_capacities_opt_H2_1,
            df_capacities_opt_H2_2,
            df_capacities_opt_stores_1,
            df_capacities_opt_stores_2,
            df_capacities_opt_charger,
            df_capacities_opt_bat)

def plot_capacity_bar_multiple(df, filename="capacity_comparison", bar_width=0.15, sort=False,
                                title="Optimierte Kapazitäten je Komponente",
                                ylabel="Capacity [MW or MWh]",
                                folder="plots", dpi=300):
    """
    Erstellt einen gruppierten Barplot aus einem DataFrame mit mehreren Szenarien je carrier
    und speichert das Bild als PNG unter dem angegebenen Dateinamen.

    Parameter:
    -----------
    df : pd.DataFrame
        DataFrame mit Index als Carrier und mehreren Spalten als Szenarien.
    filename : str
        Dateiname ohne Pfad und Endung. Z.B. "Vergleich_CH4" -> wird zu "plots/Vergleich_CH4.png".
    bar_width : float
        Breite der einzelnen Balken (Standard: 0.2).
    sort : bool
        Ob nach Gesamtwert je Carrier sortiert werden soll (Standard: True).
    title : str
        Titel des Plots.
    ylabel : str
        Beschriftung der y-Achse.
    folder : str
        Zielordner, in dem der Plot gespeichert wird (Standard: "plots").
    dpi : int
        Auflösung der PNG-Datei.
    """
    # Sortierung nach Gesamtwert, wenn gewünscht
    if sort:
        df = df.loc[df.sum(axis=1).sort_values(ascending=False).index]

    scenarios = df.columns
    carriers = df.index
    x = np.arange(len(carriers))  # Positionen der carrier auf x-Achse

    fig, ax = plt.subplots(figsize=(6, 8))

    # Farben aus colormap
    cmap = plt.get_cmap("tab10")
    colors = [cmap(i) for i in range(len(scenarios))]

    # Balken zeichnen
    for i, scenario in enumerate(scenarios):
        offset = (i - len(scenarios) / 2) * bar_width + bar_width / 2
        ax.bar(x + offset, df[scenario], width=bar_width, label=scenario, color=colors[i])

    # Achsenbeschriftung
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(carriers, rotation=45, ha='right')
    ax.legend(title="Szenario", loc="lower right")

    plt.tight_layout()
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Speicherpfad erzeugen
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, f"{filename}.png")

    # Speichern und schließen
    plt.savefig(save_path, dpi=dpi)
    plt.close()

    print(f"Plot gespeichert unter: {save_path}")