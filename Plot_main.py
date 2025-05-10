import logging
import pandas as pd

from calc_results import (
    capacities_opt_techs_global,
    plot_capacity_bar_multiple
)

from network_visual import Etrago1

logger = logging.getLogger(__name__)

# set format for logging massages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

args = {
    # == INPUT ==
    "pypsa_network":"pypsa_results/2025-04-18_etrago_test_set4_appl.log", # path to pypsa results
    "pypsa_network2":"pypsa_results/2025-05-03_etrago_test_set6_CH4_100", # path to pypsa results
    "pypsa_network3":"pypsa_results/2025-05-03_etrago_test_set8_CH4_150", # path to pypsa results
    "pypsa_network4":"pypsa_results/2025-05-03_etrago_test_set8_EL_mul_2", # path to pypsa results
    "pypsa_network5":"pypsa_results/2025-05-04_etrago_test_set9_EL_mul_3", # path to pypsa results

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
        "plot_comps_of_interest": True, # plot only pypsa-components of interest ara
        "bussize": 10,
        "linkwidth": 5,
        "linewidth": 3,
    },
}

etrago = Etrago1(args, csv_folder = args["pypsa_network"])
etrago2 = Etrago1(args, csv_folder = args["pypsa_network2"])
etrago3 = Etrago1(args, csv_folder = args["pypsa_network3"])
etrago4 = Etrago1(args, csv_folder = args["pypsa_network4"])
etrago5 = Etrago1(args, csv_folder = args["pypsa_network5"])

# === create maps ===
#etrago.create_maps()
#etrago.create_bus_map()
#etrago.create_links_map()
#etrago.create_lines_map()
#etrago.create_buses_and_links_map()
#etrago.create_buses_links_lines_map()
#logger.info("Maps successfully created.")

# === bar plots ===

#  CH4 - sensitivity

# capacities_opt base_scn

capacities_opt1, capacities_ing_opt1 = etrago.capacities_opt()

df_capacities_opt_H21, df_capacities_opt_stores1, df_capacities_opt_charger1, df_capacities_opt_bat1 = capacities_opt_techs_global(capacities_opt1)

#print(df_capacities_opt_H2)
#print(df_capacities_opt_stores)
#print(df_capacities_opt_charger)
#print(df_capacities_opt_bat)

# capacities_opt CH_4 = 100

capacities_opt2, capacities_ing_opt2 = etrago2.capacities_opt(scn="CH4_100")

df_capacities_opt_H22, df_capacities_opt_stores2, df_capacities_opt_charger2, df_capacities_opt_bat2 = capacities_opt_techs_global(capacities_opt2)

# capacities_opt CH_4 = 150

capacities_opt3, capacities_ing_opt3 = etrago3.capacities_opt(scn="CH4_150")

df_capacities_opt_H23, df_capacities_opt_stores3, df_capacities_opt_charger3, df_capacities_opt_bat3 = capacities_opt_techs_global(capacities_opt3)

# summarize

capacities_opt = pd.concat([capacities_opt1, capacities_opt2, capacities_opt3], axis=1)
df_capacities_opt_H2 = pd.concat([df_capacities_opt_H21, df_capacities_opt_H22, df_capacities_opt_H23], axis=1)
df_capacities_opt_stores = pd.concat([df_capacities_opt_stores1, df_capacities_opt_stores2, df_capacities_opt_stores3], axis=1)
df_capacities_opt_charger = pd.concat([df_capacities_opt_charger1, df_capacities_opt_charger2, df_capacities_opt_charger3], axis=1)
df_capacities_opt_bat = pd.concat([df_capacities_opt_bat1, df_capacities_opt_bat2, df_capacities_opt_bat3], axis=1)


plot_capacity_bar_multiple(df_capacities_opt_H2, filename= "CH4_Vergleich_H2")
plot_capacity_bar_multiple(df_capacities_opt_stores, filename= "CH4_Vergleich_stores")
plot_capacity_bar_multiple(df_capacities_opt_charger, filename= "CH4_Vergleich_charger")
plot_capacity_bar_multiple(df_capacities_opt_bat, filename= "CH4_Vergleich_bat")




# Electrolyser - sensitivity

# capacities_opt EL  *=2

capacities_opt4, capacities_ing_opt4 = etrago4.capacities_opt(scn="EL_mul_2")

df_capacities_opt_H24, df_capacities_opt_stores4, df_capacities_opt_charger4, df_capacities_opt_bat4 = capacities_opt_techs_global(capacities_opt4)

# capacities_opt EL  *=3

capacities_opt5, capacities_ing_opt5 = etrago5.capacities_opt(scn="EL_mul_3")

df_capacities_opt_H25, df_capacities_opt_stores5, df_capacities_opt_charger5, df_capacities_opt_bat5 = capacities_opt_techs_global(capacities_opt5)

# summarize

capacities_opt = pd.concat([capacities_opt1, capacities_opt4, capacities_opt5], axis=1)
df_capacities_opt_H2_EL = pd.concat([df_capacities_opt_H21, df_capacities_opt_H24, df_capacities_opt_H25], axis=1)
df_capacities_opt_stores_EL = pd.concat([df_capacities_opt_stores1, df_capacities_opt_stores4, df_capacities_opt_stores5], axis=1)
df_capacities_opt_charger_EL = pd.concat([df_capacities_opt_charger1, df_capacities_opt_charger4, df_capacities_opt_charger5], axis=1)
df_capacities_opt_bat_EL = pd.concat([df_capacities_opt_bat1, df_capacities_opt_bat4, df_capacities_opt_bat5], axis=1)

plot_capacity_bar_multiple(df_capacities_opt_H2_EL, filename= "EL_Vergleich_H2")
plot_capacity_bar_multiple(df_capacities_opt_stores_EL, filename= "EL_Vergleich_stores")
plot_capacity_bar_multiple(df_capacities_opt_charger_EL, filename= "EL_Vergleich_charger")
plot_capacity_bar_multiple(df_capacities_opt_bat_EL, filename= "EL_Vergleich_bat")

