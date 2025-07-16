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
plt.style.use('bmh')

from calc_base_results import (
    capacities_opt_ing,
    df_electricity_generation,
    df_central_heat_generation,
    df_decentral_heat_generation
)

def plot_capacity_bar(
    etrago,
    title="Optimierte Kapaziäten mit vorhandenen Kapazitäten",
    filename="capacity_bar.png",
    output_folder="Base_results"
):
    """
    Erzeugt ein Balkendiagramm der Kapazitäten pro Carrier aus einem etrago-Objekt
    und speichert es als PNG.

    Parameter:
    ----------
    etrago : object
        Instanz der etrago-Klasse, die die Methode capacities_opt_ing() bereitstellt.
    title : str, optional
        Titel des Plots.
    filename : str, optional
        Dateiname der gespeicherten Grafik (z.B. 'capacity_bar.png').
    output_folder : str, optional
        Zielordner für den Plot.
    """
    # 1️⃣ DataFrame mit den Kapazitäten erzeugen
    df_caps = capacities_opt_ing(etrago)

    # 2️⃣ Daten für den Plot vorbereiten (Reihenfolge bleibt erhalten)
    carriers = df_caps["carrier"]
    capacities = df_caps["Capacity"]

    # 3️⃣ Plot erstellen
    plt.figure(figsize=(10, 6))
    bars = plt.barh(carriers, capacities, color="steelblue")

    # 4️⃣ Achsenbeschriftungen und Titel
    plt.xlabel("Capacity [MW]")
    plt.ylabel("Carrier")
    plt.title(title)

    # 5️⃣ Werte an die Balken schreiben
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                 f"{width:.2f}", va="center")

    plt.tight_layout()

    # 6️⃣ Ordner anlegen, falls nicht vorhanden
    os.makedirs(output_folder, exist_ok=True)

    # 7️⃣ Vollständiger Pfad
    filepath = os.path.join(output_folder, filename)

    # 8️⃣ Plot speichern
    plt.savefig(filepath, dpi=300)
    plt.close()

    print(f"Plot erfolgreich gespeichert unter: {filepath}")


import matplotlib.pyplot as plt
import os

import matplotlib.pyplot as plt
import os

def plot_electricity_generation_bar(
    etrago,
    title="Electricity Generation by Carrier",
    filename="electricity_generation_bar.png",
    output_folder="Base_results"
):
    """
    Plots electricity generation and import as horizontal bar chart.
    """

    # Create output folder if it does not exist
    os.makedirs(output_folder, exist_ok=True)

    # Get data
    df_generation = df_electricity_generation(etrago)

    # Convert to GWh
    df_generation["generation"] = df_generation["generation"] / 1e3

    # Sort descending
    df_sorted = df_generation.sort_values(by="generation", ascending=True)

    # Compute total for percentages
    total_generation = df_sorted["generation"].sum()

    # Initialize figure
    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot horizontal bars
    bars = ax.barh(
        df_sorted["carrier"],
        df_sorted["generation"],
        color="steelblue"
    )

    # Labels
    ax.set_xlabel("Stromerzeugung [GWh]")
    ax.set_ylabel("Technologie")
    ax.set_title(title)

    # Annotate bars with value and percentage
    for bar, value in zip(bars, df_sorted["generation"]):
        percent = (value / total_generation) * 100
        ax.text(
            value + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f} ({percent:.1f}%)",
            va="center",
            fontsize=9
        )

    plt.tight_layout()

    # Save plot
    save_path = os.path.join(output_folder, filename)
    plt.savefig(save_path, dpi=300)
    plt.close()

    print(f"Plot successfully saved to: {save_path}")


def plot_central_heat_generation_bar(
    etrago,
    title="Zentrale Wärmerversorgung je Technologie",
    filename="central_heat_generation_bar.png",
    output_folder="Base_results"
):
    """
    Plots central heat generation as horizontal bar chart.
    """

    # Create output folder if it does not exist
    os.makedirs(output_folder, exist_ok=True)

    # Get data
    df_generation = df_central_heat_generation(etrago)

    # Convert to GWh_th
    df_generation["generation_cH"] = df_generation["generation_cH"] / 1e3

    # Sort ascending for horizontal bar plot
    df_sorted = df_generation.sort_values(by="generation_cH", ascending=True)

    # Compute total for percentages
    total_generation = df_sorted["generation_cH"].sum()

    # Initialize figure
    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot horizontal bars
    bars = ax.barh(
        df_sorted["carrier"],
        df_sorted["generation_cH"],
        color="indianred"
    )

    ax.set_xlabel("Heat Generation [GWh_th]")
    ax.set_ylabel("Technologie")
    ax.set_title(title)

    # Annotate bars with value and percentage
    for bar, value in zip(bars, df_sorted["generation_cH"]):
        percent = (value / total_generation) * 100
        ax.text(
            value + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f} ({percent:.1f}%)",
            va="center",
            fontsize=9
        )

    plt.tight_layout()

    # Save figure
    save_path = os.path.join(output_folder, filename)
    plt.savefig(save_path, dpi=300)
    plt.close()

    print(f"Plot successfully saved to: {save_path}")


def plot_decentral_heat_generation_bar(
    etrago,
    title="Decentral Heat Generation by Carrier",
    filename="decentral_heat_generation_bar.png",
    output_folder="Base_results"
):
    """
    Plots decentral heat generation as horizontal bar chart.
    """

    # Create output folder if it does not exist
    os.makedirs(output_folder, exist_ok=True)

    # Get data
    df_generation = df_decentral_heat_generation(etrago)

    # Convert to GWh_th
    df_generation["generation_dH"] = df_generation["generation_dH"] / 1e3

    # Sort ascending for horizontal bar plot
    df_sorted = df_generation.sort_values(by="generation_dH", ascending=True)

    # Compute total for percentages
    total_generation = df_sorted["generation_dH"].sum()

    # Initialize figure
    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot horizontal bars
    bars = ax.barh(
        df_sorted["carrier"],
        df_sorted["generation_dH"],
        color="darkorange"
    )

    ax.set_xlabel("Heat Generation [GWh_th]")
    ax.set_ylabel("Technologie")
    ax.set_title(title)

    # Annotate bars with value and percentage
    for bar, value in zip(bars, df_sorted["generation_dH"]):
        percent = (value / total_generation) * 100
        ax.text(
            value + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f} ({percent:.1f}%)",
            va="center",
            fontsize=9
        )

    plt.tight_layout()

    # Save figure
    save_path = os.path.join(output_folder, filename)
    plt.savefig(save_path, dpi=300)
    plt.close()

    print(f"Plot successfully saved to: {save_path}")


def plot_central_heat_dispatch(
    etrago,
    time=None,
    title="Dispatch Central Heat und Wärmeerzeuger",
    filename="central_heat_dispatch.png",
    output_folder="Base_results"
):
    """
    Plots central heat dispatch by carrier in the interest area as stacked area plot
    and overlays the central heat load. Includes charging of heat storage units.

    Args:
        etrago: Etrago instance with loaded PyPSA network
        time (str or slice, optional): Time slice for plotting (e.g. '2015-07') or slice("2011-05-01", "2011-05-31")
        title (str, optional): Title of the plot
        filename (str, optional): Filename for saving the plot (will be extended by time tag)
        output_folder (str, optional): Output folder for saving the file
    """
    # get buses of interest area
    buses_interest = etrago.find_interest_buses()
    bus_list = buses_interest.index.to_list()

    # get load time series of interest area
    loads_interest = etrago.network.loads[etrago.network.loads.bus.isin(bus_list)]
    loads_int_ts = etrago.network.loads_t.p_set.loc[:, loads_interest.index]

    # get bus id of central heat buses
    cH_index = buses_interest[buses_interest.carrier == "central_heat"].index

    # get links connected to interest buses
    connected_links = etrago.find_links_connected_to_interest_buses()

    # links that dispatch into central_heat network
    links_on_cH = connected_links[
        ((connected_links.bus1.isin(cH_index)) & (connected_links.p_nom_extendable == True)) |
        (connected_links.carrier == "central_waste_CHP_heat")
    ]
    links_on_cH_ts = etrago.network.links_t.p1[links_on_cH.index] * (-1)

    # links that charge from central_heat network (e.g. storage)
    links_from_cH = connected_links[(connected_links.bus0.isin(cH_index))]
    links_from_cH_ts = etrago.network.links_t.p0[links_from_cH.index] * (-1)

    # apply time filter if given
    if time is not None:
        loads_int_ts = loads_int_ts.loc[time]
        links_on_cH_ts = links_on_cH_ts.loc[time]
        links_from_cH_ts = links_from_cH_ts.loc[time]

    # map carrier names
    carriers_on_cH = pd.Series(links_on_cH["carrier"].to_dict())
    carriers_from_cH = pd.Series(links_from_cH["carrier"].to_dict())

    # group dispatch and storage charging by carrier
    grouped_on_cH = links_on_cH_ts.T.groupby(carriers_on_cH).sum().T
    grouped_from_cH = links_from_cH_ts.T.groupby(carriers_from_cH).sum().T

    # combine both sources
    carrier_grouped = pd.concat([grouped_on_cH, grouped_from_cH], axis=1)

    # remove carriers with no dispatch
    nonzero_carriers = carrier_grouped.columns[(carrier_grouped != 0).any()]
    carrier_grouped = carrier_grouped[nonzero_carriers]

    # get central_heat load
    selected_columns = [col for col in loads_int_ts.columns if str(col).endswith("central_heat")]
    if not selected_columns:
        raise ValueError("No 'central_heat' column found in load time series.")
    column_to_plot = selected_columns[0]
    central_heat_ts = loads_int_ts[column_to_plot]
    central_heat_ts = central_heat_ts.reindex(carrier_grouped.index).fillna(0)

    # extend filename with time info
    if time is not None:
        if isinstance(time, slice):
            start = str(time.start)[:10] if time.start else "start"
            end = str(time.stop)[:10] if time.stop else "end"
            time_tag = f"{start}_to_{end}"
        else:
            time_tag = str(time).replace(" ", "_")
        filename = filename.replace(".png", f"_{time_tag}.png")

    # plot setup
    fig, ax = plt.subplots(figsize=(14, 7))
    carrier_grouped.plot.area(ax=ax, linewidth=0, alpha=0.6)
    central_heat_ts.plot(ax=ax, color="black", linewidth=2, label="Central Heat Load")

    ax.set_xlabel("Datum")
    ax.set_ylabel("Leistung / Wärmefluss [MW]")
    ax.set_title(title)
    ax.legend(title="Carrier / Load")
    ax.grid(True)
    plt.tight_layout()

    # save plot
    os.makedirs(output_folder, exist_ok=True)
    filepath = os.path.join(output_folder, filename)
    plt.savefig(filepath, dpi=300)
    plt.close()

    print(f"Plot erfolgreich gespeichert unter: {filepath}")



