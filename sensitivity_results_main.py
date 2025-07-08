import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
from network_visual import Etrago1

from calc_base_results import (
    capacities_opt_ing,
    df_electricity_generation,
    df_central_heat_generation,
    df_decentral_heat_generation
)

from calc_results_sensitivity import (
    get_marginal_price_series
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Example configuration
args = {
    # CH4 - sensitivity
    #"pypsa_networks": "pypsa_results/Base_1/CH4_sensitivity/",  # Directory which contains results-folder
    #"results_folder": "results/Sensitivity_results/CH4_sensitivity", # Directory where results will be saved
    #"labels":[ "CH4 = 20 €/MWh","Base - CH4 = 41 €/MWh", "CH4 = 60 €/MWh", "CH4 = 80 €/MWh", "CH4 = 100 €/MWh"], # legend entries
    # CO2 - sensitivity
    "pypsa_networks": "etrago_results/Parameter_set_new/",  # Directory which contains results-folder
    "results_folder": "results/Sensitivity_results/Base_vergleich_new",  # Directory where results will be saved
    "labels": ["Base_1","Base_1a","Base_3c","Base_3d"],
    # legend entries

    "nuts_3_map": "germany-de-nuts-3-regions.geojson",
    "interest_area": ["Ingolstadt"],
    "network_clustering": {
        "n_clusters_AC": 30,
        "n_clusters_gas": 14,
    },
    "name": "Ingolstadt_30_14",
    "plot_settings": {
        "plot_comps_of_interest": False,
        "bussize": 10,
        "linkwidth": 5,
        "linewidth": 3,
    },
}


def load_etrago_objects(results_dir, labels, args):
    """
    Loads all PyPSA results in the given directory and creates Etrago1 objects.

    Parameters
    ----------
    results_dir : str
        Path to the directory containing subfolders with PyPSA results.
    labels : list of str
        Labels to assign to each scenario.
    args : dict
        Arguments for Etrago1.

    Returns
    -------
    list of Etrago1
    """
    subfolders = sorted([
        os.path.join(results_dir, d)
        for d in os.listdir(results_dir)
        if os.path.isdir(os.path.join(results_dir, d))
    ])

    if len(subfolders) != len(labels):
        raise ValueError(
            f"Number of subfolders ({len(subfolders)}) does not match number of labels ({len(labels)})."
        )

    etrago_list = []
    for folder, label in zip(subfolders, labels):
        logger.info(f"Loading scenario: {label} from {folder}")
        etrago = Etrago1(args, csv_folder=folder)
        etrago_list.append(etrago)

    return etrago_list


def collect_all_data(etrago_list):
    """
    Collects all relevant DataFrames for each scenario.

    Returns
    -------
    dict of DataFrames
        Keys: 'capacities', 'electricity', 'central_heat', 'decentral_heat'
    """
    capacities = []
    electricity = []
    central_heat = []
    decentral_heat = []

    for etrago in etrago_list:
        df_cap = capacities_opt_ing(etrago)
        df_el = df_electricity_generation(etrago)
        df_ch = df_central_heat_generation(etrago)
        df_dh = df_decentral_heat_generation(etrago)

        capacities.append(df_cap)
        electricity.append(df_el)
        central_heat.append(df_ch)
        decentral_heat.append(df_dh)

    return {
        "capacities": capacities,
        "electricity": electricity,
        "central_heat": central_heat,
        "decentral_heat": decentral_heat
    }


def merge_scenario_data(dataframes, value_column):
    """
    Merges a list of scenario DataFrames into a single DataFrame for plotting.

    Parameters
    ----------
    dataframes : list of pd.DataFrame
        One per scenario.
    value_column : str
        Column to merge (e.g., 'generation', 'Capacity').

    Returns
    -------
    pd.DataFrame
        Index: carrier, Columns: scenarios.
    """
    merged = None
    for idx, df in enumerate(dataframes):
        df_pivot = df.set_index("carrier")[[value_column]]
        df_pivot.columns = [f"scenario_{idx+1}"]
        if merged is None:
            merged = df_pivot
        else:
            merged = merged.join(df_pivot, how="outer")
    merged = merged.fillna(0)
    return merged


def plot_multibar(
    df,
    labels,
    title,
    xlabel,
    filename,
    output_folder,
    color="steelblue"
):
    """
    Plots a horizontal multibar chart comparing scenarios.

    Parameters
    ----------
    df : pd.DataFrame
        Index = carriers, columns = scenarios.
    labels : list of str
        Scenario labels.
    """
    os.makedirs(output_folder, exist_ok=True)

    carriers = df.index.tolist()
    n_scenarios = len(df.columns)
    bar_height = 0.8 / n_scenarios
    y = range(len(carriers))

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, scenario in enumerate(df.columns):
        values = df[scenario].values / 1e3  # Convert to GWh or GWh_th
        ax.barh(
            [pos + i * bar_height for pos in y],
            values,
            height=bar_height,
            label=labels[i]
        )

    ax.set_yticks([pos + bar_height * (n_scenarios / 2 - 0.5) for pos in y])
    ax.set_yticklabels(carriers)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Technologie")
    ax.set_title(title)
    handles, legend_labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], legend_labels[::-1])

    plt.tight_layout()

    save_path = os.path.join(output_folder, filename)
    plt.savefig(save_path, dpi=300)
    plt.close()

    print(f"Plot successfully saved to: {save_path}")

def plot_marginal_price_comparison(
    price_series_list,
    labels,
    title="Marginal Electricity Price Comparison (Daily Average)",
    ylabel="Price [€/MWh]",
    filename="marginal_price_comparison.png",
    output_folder="Sensitivity_results"
):
    """
    Plots daily average marginal price time series for multiple scenarios.
    """
    import os

    os.makedirs(output_folder, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 5))

    for series, label in zip(price_series_list, labels):
        # Resample to daily averages
        daily_avg = series.resample("D").mean()
        ax.plot(daily_avg.index, daily_avg.values, label=label)

    ax.set_xlabel("Time (Daily Average)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()

    save_path = os.path.join(output_folder, filename)
    plt.savefig(save_path, dpi=300)
    plt.close()

    print(f"Plot successfully saved to: {save_path}")


if __name__ == "__main__":

    # Sensitivity setup
    results_dir = args["pypsa_networks"]
    labels = args["labels"]

    etrago_list = load_etrago_objects(results_dir, labels, args)
    data = collect_all_data(etrago_list)

    output_folder = args["results_folder"]

    # Capacities
    df_caps = merge_scenario_data(data["capacities"], "Capacity")
    plot_multibar(
        df_caps,
        labels,
        title="Optimierte Kapazitäten je Technologie",
        xlabel="Capacity [GW]",
        filename="capacity_sensitivity.png",
        output_folder=output_folder
    )

    # Electricity generation
    df_elec = merge_scenario_data(data["electricity"], "generation")
    plot_multibar(
        df_elec,
        labels,
        title="Stromversorgung je Technologie",
        xlabel="Stromversorgung [GWh]",
        filename="electricity_sensitivity.png",
        output_folder=output_folder
    )

    # Central heat
    df_ch = merge_scenario_data(data["central_heat"], "generation_cH")
    plot_multibar(
        df_ch,
        labels,
        title="Zentrale Wärmeerzeugung je Technologie",
        xlabel="Wärmeerzeugung [GWh_th]",
        filename="central_heat_sensitivity.png",
        output_folder=output_folder
    )

    # Decentral heat
    df_dh = merge_scenario_data(data["decentral_heat"], "generation_dH")
    plot_multibar(
        df_dh,
        labels,
        title="Dezentrale Wärmeerzeugung je Technologie",
        xlabel="Wärmeerzeugung [GWh_th]",
        filename="decentral_heat_sensitivity.png",
        output_folder=output_folder
    )

    # Example bus_id
    bus_id = "16"

    # Get time series for all scenarios
    price_series_list = [get_marginal_price_series(e, bus_id) for e in etrago_list]

    # marginal_prices
    plot_marginal_price_comparison(
        price_series_list,
        labels,
        title="Strompreis Zeitreihen",
        ylabel="Strompreis [€/MWh]",
        filename="marginal_price_comparison.png",
        output_folder=output_folder
    )