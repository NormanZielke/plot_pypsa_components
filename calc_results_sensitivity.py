


def get_marginal_price_series(etrago, bus_id):
    """
    Returns the marginal price time series for a given bus.

    Parameters
    ----------
    etrago : Etrago1
    bus_id : str

    Returns
    -------
    pd.Series
    """
    return etrago.network.buses_t.marginal_price[bus_id]