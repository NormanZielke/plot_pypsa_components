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

from plot_comps import(
    find_interest_buses,
    find_links_connected_to_buses
)


def capacities_opt_ing(self):
    """
    Filter Optimized Capacities fpr interest area
    """
    # filter for links capacities
    connected_links = self.find_links_connected_to_buses()
    waste_list = ["central_waste_CHP", "central_waste_CHP_heat"]
    #links_cap = connected_links[
    #    (connected_links.p_nom_extendable == True) | (connected_links.carrier.isin(waste_list))
    #    ]
    links_cap = connected_links[
        (connected_links.p_nom_extendable == True) |
        (connected_links.carrier.isin(waste_list))]
    df_caps = links_cap[["carrier", "p_nom_opt"]].copy()
    df_caps = df_caps[~df_caps.carrier.isin([
        "rural_heat_store_charger",
        "rural_heat_store_discharger",
        "central_heat_store_charger",
        "central_heat_store_discharger"
    ])
    ]
    df_caps = df_caps.reset_index(drop=True)
    #waste_index = df_caps[df_caps.carrier.isin(waste_list)].index
    #df_caps.loc[waste_index, "p_nom_opt"] = 0
    df_caps = df_caps.rename(columns={"p_nom_opt": "Capacity"})

    # filter generators
    buses_ing = self.find_interest_buses()
    bus_list = buses_ing.index.to_list()
    gens_ing = self.network.generators[self.network.generators.bus.isin(bus_list)]
    gens_ing = gens_ing[(gens_ing.carrier != "load shedding") & (gens_ing.p_nom_extendable == True)]
    gens_caps = gens_ing[["carrier", "p_nom_opt"]].reset_index(drop=True)
    gens_caps = gens_caps.rename(columns={"p_nom_opt": "Capacity"})

    # filter batteries
    batteries_ing = self.network.storage_units[self.network.storage_units.bus.isin(bus_list)]
    batteries_caps = batteries_ing[["carrier", "p_nom_opt"]].reset_index(drop=True)
    batteries_caps = batteries_caps.rename(columns={"p_nom_opt": "Capacity"})

    # filter stores
    stores_ing = self.network.stores[self.network.stores.bus.isin(bus_list)]
    stores_ing = stores_ing[stores_ing.e_nom_extendable == True]
    stores_caps = stores_ing[["carrier", "e_nom_opt"]].reset_index(drop=True)
    stores_caps = stores_caps.rename(columns={"e_nom_opt": "Capacity"})

    # add generators to df_caps
    df_caps = pd.concat([df_caps, gens_caps, batteries_caps, stores_caps], ignore_index=True)

    return df_caps


def df_electricity_generation(etrago):
    """
    Returns electricity generation and import by carrier (links, generators, batteries, lines).

    Parameters
    ----------
    etrago : Etrago object
        Contains the PyPSA network and helper functions.

    Returns
    -------
    pd.DataFrame
        Columns: 'carrier', 'generation'
    """

    # Select relevant buses
    buses_ing = etrago.find_interest_buses()
    bus_list = buses_ing.index.to_list()
    bus_AC_id = buses_ing[buses_ing.carrier == "AC"].index.to_list()

    # Links (electricity)
    connected_links = etrago.find_links_connected_to_buses()
    waste_list = ["central_waste_CHP", "central_waste_CHP_heat"]

    links_cap = connected_links[
        (connected_links.p_nom_extendable == True) |
        (connected_links.carrier.isin(waste_list))
    ]
    links_cap = links_cap[
        ~links_cap.carrier.isin([
            "rural_heat_store_charger",
            "rural_heat_store_discharger",
            "central_heat_store_charger",
            "central_heat_store_discharger"
        ])
    ]
    links_cap_elec = links_cap[
        links_cap.bus1.isin(bus_AC_id)
    ]

    links_dispatch = (
        etrago.network.links_t.p1[links_cap_elec.index]
        .sum(axis=0)
        * (-1)
    )

    df_links = pd.DataFrame({
        "carrier": links_cap_elec.carrier,
        "generation": links_dispatch
    })

    # Generators (electricity)
    gens_all = etrago.network.generators[
        etrago.network.generators.bus.isin(bus_list)
    ]
    gens_elec = gens_all[
        (gens_all.bus.isin(bus_AC_id)) &
        (gens_all.carrier != "load shedding") &
        (gens_all.p_nom_extendable == True)
    ]

    gens_dispatch = (
        etrago.network.generators_t.p[gens_elec.index]
        .sum(axis=0)
    )

    df_gens = pd.DataFrame({
        "carrier": gens_elec.carrier,
        "generation": gens_dispatch
    })

    # Batteries (discharge)
    batteries_ing = etrago.network.storage_units[
        etrago.network.storage_units.bus.isin(bus_list)
    ]
    batteries_list = batteries_ing.index.to_list()
    battery_dispatch = etrago.network.storage_units_t.p.loc[:, batteries_list]
    battery_generation = battery_dispatch[
        battery_dispatch[batteries_list] > 0
    ].sum()

    df_battery = pd.DataFrame({
        "carrier": ["battery_discharge"],
        "generation": [battery_generation.sum()]
    })

    # Lines (electricity import)
    lines = etrago.network.lines
    lines_ing = lines[
        lines['bus0'].isin(bus_list) | lines['bus1'].isin(bus_list)
    ]
    lines_list = lines_ing.index.tolist()
    lines_dispatch = etrago.network.lines_t.p0.loc[:, lines_list]
    electricity_import = (
        lines_dispatch[lines_dispatch < 0]
        .sum()
        * (-1)
    )
    total_import = electricity_import.sum()
    df_import = pd.DataFrame({
        "carrier": ["Stromimport"],
        "generation": [total_import]
    })

    # Combine all sources
    df_combined = pd.concat(
        [df_links, df_gens, df_battery, df_import],
        axis=0
    )

    df_grouped = (
        df_combined
        .groupby("carrier")
        .sum()
        .reset_index()
    )

    return df_grouped


def df_central_heat_generation(etrago):
    """
    Returns central heat generation by carrier.

    Parameters
    ----------
    etrago : Etrago object
        Contains the PyPSA network and helper functions.

    Returns
    -------
    pd.DataFrame
        Columns: 'carrier', 'generation_cH'
    """

    # Select relevant buses
    buses_ing = etrago.find_interest_buses()
    #bus_list = buses_ing.index.to_list()
    bus_central_heat_id = buses_ing[buses_ing.carrier == "central_heat"].index.to_list()

    # Links connected to central heat buses
    connected_links = etrago.find_links_connected_to_buses()
    links_cap = connected_links[
        connected_links.bus1.isin(bus_central_heat_id)
    ]

    # Filter links
    links_cap_ch = links_cap[
        (
            (links_cap.p_nom_extendable == True)
        ) |
        (links_cap.carrier == "central_waste_CHP_heat")
    ]

    # Dispatch sum (negative = generation)
    links_dispatch = (
        etrago.network.links_t.p1[links_cap_ch.index]
        .sum(axis=0)
        * (-1)
    )

    # Build DataFrame
    df_heat = pd.DataFrame({
        "carrier": links_cap_ch.carrier,
        "generation_cH": links_dispatch
    })

    # Group by carrier
    df_grouped = (
        df_heat
        .groupby("carrier")
        .sum()
        .reset_index()
    )

    return df_grouped


def df_decentral_heat_generation(etrago):
    """
    Returns decentral heat generation by carrier (links + generators).

    Parameters
    ----------
    etrago : Etrago object
        Contains the PyPSA network and helper functions.

    Returns
    -------
    pd.DataFrame
        Columns: 'carrier', 'generation_dH'
    """

    # Select relevant buses
    buses_ing = etrago.find_interest_buses()
    bus_rural_heat_id = buses_ing[buses_ing.carrier == "rural_heat"].index.to_list()

    # Links connected to decentral heat buses
    connected_links = etrago.find_links_connected_to_buses()
    links_dH = connected_links[
        (connected_links.bus1.isin(bus_rural_heat_id)) &
        (connected_links.p_nom_extendable == True)
    ]

    # Dispatch Links
    links_dispatch = (
        etrago.network.links_t.p1[links_dH.index]
        .sum(axis=0)
        * (-1)
    )

    df_links = pd.DataFrame({
        "carrier": links_dH.carrier,
        "generation_dH": links_dispatch
    })

    # Generators connected to decentral heat buses
    gens_all = etrago.network.generators[
        etrago.network.generators.bus.isin(bus_rural_heat_id)
    ]

    gens_dH = gens_all[
        (gens_all.carrier != "load shedding") &
        (gens_all.p_nom_extendable == True)
    ]

    # Dispatch Generators
    gens_dispatch = (
        etrago.network.generators_t.p[gens_dH.index]
        .sum(axis=0)
    )

    df_gens = pd.DataFrame({
        "carrier": gens_dH.carrier,
        "generation_dH": gens_dispatch
    })

    # Combine Links + Generators
    df_combined = pd.concat([df_links, df_gens], axis=0)

    # Group by carrier
    df_grouped = (
        df_combined
        .groupby("carrier")
        .sum()
        .reset_index()
    )

    return df_grouped




