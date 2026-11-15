
"""
Econ AI Agent
Module: fred.py

Retrieve U.S. economic time-series data from the
Federal Reserve Bank of St. Louis (FRED).

Missing observations are preserved.
"""

import os

import pandas as pd
import requests
from dotenv import load_dotenv

from catalog import INDICATORS


load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")

BASE_URL = (
    "https://api.stlouisfed.org/fred/"
    "series/observations"
)


def fetch_fred_data(
    indicator,
    start_date,
    end_date=None
):
    """
    Retrieve a supported U.S. economic indicator.

    Parameters
    ----------
    indicator : str
        Indicator key defined in catalog.py.

    start_date : str
        First observation date, YYYY-MM-DD.

    end_date : str, optional
        Last observation date, YYYY-MM-DD.

    Returns
    -------
    pandas.DataFrame
        Country, Country_Code, Date, Value,
        Indicator, Unit, Source
    """

    if indicator not in INDICATORS:
        raise ValueError(
            f"Unsupported indicator: {indicator}"
        )

    indicator_info = INDICATORS[indicator]
    series_id = indicator_info.get("fred")

    if not series_id:
        raise ValueError(
            f"{indicator} is not available from FRED."
        )

    if not FRED_API_KEY:
        raise ValueError(
            "FRED_API_KEY is missing from your .env file."
        )

    start = pd.Timestamp(start_date)

    if end_date is None:
        end = pd.Timestamp.today().normalize()
    else:
        end = pd.Timestamp(end_date)

    if start > end:
        raise ValueError(
            "start_date cannot exceed end_date."
        )

    response = requests.get(
        BASE_URL,
        params={
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "observation_start": start.strftime("%Y-%m-%d"),
            "observation_end": end.strftime("%Y-%m-%d")
        },
        timeout=30
    )

    response.raise_for_status()

    payload = response.json()
    observations = payload.get("observations", [])

    rows = []

    for observation in observations:
        rows.append({
            "Country": "United States",
            "Country_Code": "USA",
            "Date": observation["date"],
            "Value": observation.get("value"),
            "Indicator": indicator,
            "Unit": indicator_info["unit"],
            "Source": "FRED",
            "Series_ID": series_id
        })

    df = pd.DataFrame(
        rows,
        columns=[
            "Country",
            "Country_Code",
            "Date",
            "Value",
            "Indicator",
            "Unit",
            "Source",
            "Series_ID"
        ]
    )

    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"])
        df["Value"] = pd.to_numeric(
            df["Value"],
            errors="coerce"
        )


    if indicator == "inflation" and not df.empty:

        # Retrieve an extra 12 months of CPI history
        # before the requested start date so the first
        # requested year's inflation can be calculated.
        earlier_start = (
            start - pd.DateOffset(months=12)
        )

        earlier_response = requests.get(
            BASE_URL,
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "observation_start": earlier_start.strftime(
                    "%Y-%m-%d"
                ),
                "observation_end": end.strftime("%Y-%m-%d")
            },
            timeout=30
        )

        earlier_response.raise_for_status()

        earlier_observations = (
            earlier_response.json()
            .get("observations", [])
        )

        inflation_df = pd.DataFrame(
            earlier_observations
        )

        if not inflation_df.empty:
            inflation_df["Date"] = pd.to_datetime(
                inflation_df["date"]
            )

            inflation_df["CPI"] = pd.to_numeric(
                inflation_df["value"],
                errors="coerce"
            )

            inflation_df = inflation_df.sort_values(
                "Date"
            )

            inflation_df["Value"] = (
                inflation_df["CPI"]
                .pct_change(
                    periods=12,
                    fill_method=None
                ) * 100
            )

            df = inflation_df[
                inflation_df["Date"].between(start, end)
            ][["Date", "Value"]].copy()

            df["Country"] = "United States"
            df["Country_Code"] = "USA"
            df["Indicator"] = indicator
            df["Unit"] = "%"
            df["Source"] = "FRED"
            df["Series_ID"] = series_id

    return (
        df[
            [
                "Country",
                "Country_Code",
                "Date",
                "Value",
                "Indicator",
                "Unit",
                "Source",
                "Series_ID"
            ]
        ]
        .sort_values("Date")
        .reset_index(drop=True)
    )


def get_fred_data_quality_report(df):
    """Summarize observation coverage."""

    total = len(df)
    available = int(df["Value"].notna().sum())
    missing = total - available

    return {
        "total_observations": total,
        "available_observations": available,
        "missing_observations": missing,
        "coverage_percentage": (
            round(100 * available / total, 2)
            if total else 0
        ),
        "first_observation": (
            str(df["Date"].min().date())
            if total else None
        ),
        "last_observation": (
            str(df["Date"].max().date())
            if total else None
        )
    }

# SELF-TEST


if __name__ == "__main__":

    print("\nECON AI AGENT — FRED TEST")

    print("\nTEST 1: U.S. Unemployment Rate")

    unemployment = fetch_fred_data(
        indicator="unemployment",
        start_date="2020-01-01",
        end_date="2024-12-31"
    )

    print(
        unemployment.tail(10).to_string(index=False)
    )

    print("\nData Quality:")
    print(get_fred_data_quality_report(unemployment))

    print("\nTEST 2: U.S. Inflation Rate")

    inflation = fetch_fred_data(
        indicator="inflation",
        start_date="2020-01-01",
        end_date="2024-12-31"
    )

    print(
        inflation.tail(10).to_string(index=False)
    )

    print("\nData Quality:")
    print(get_fred_data_quality_report(inflation))

    print("\nTEST 3: Federal Funds Rate")

    fed_funds = fetch_fred_data(
        indicator="fed_funds_rate",
        start_date="2023-01-01",
        end_date="2024-12-31"
    )

    print(
        fed_funds.tail(10).to_string(index=False)
    )

    print("\nData Quality:")
    print(get_fred_data_quality_report(fed_funds))
