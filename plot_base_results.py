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



