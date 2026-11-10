
"""
Econ AI Agent
Module: worldbank.py

Retrieve official economic indicator observations
from the World Bank Indicators API.

Missing values are preserved.
"""

import requests
import pandas as pd

from catalog import INDICATORS, COUNTRIES, REGIONS


BASE_URL = "https://api.worldbank.org/v2"

COUNTRY_CODES = {
    code: name for name, code in COUNTRIES.items()
}


def fetch_worldbank_data(
    indicator,
    countries,
    start_year,
    end_year=None
):
    """
    Retrieve World Bank economic data.

    Parameters
    ----------
    indicator : str
        Indicator key from catalog.py.

    countries : list[str]
        List of ISO3 country codes.

    start_year : int
        First year to retrieve.

    end_year : int, optional
        Final year to retrieve.

    Returns
    -------
    pandas.DataFrame
        Country, Country_Code, Year, Value,
        Indicator, Unit, Source
    """

    if indicator not in INDICATORS:
        raise ValueError(
            f"Unsupported indicator: {indicator}"
        )

    indicator_info = INDICATORS[indicator]
    wb_code = indicator_info.get("worldbank")

    if not wb_code:
        raise ValueError(
            f"{indicator} is not available from World Bank."
        )

    if isinstance(countries, str):
        countries = [countries]

    countries = [
        code.strip().upper() for code in countries
    ]

    if not countries:
        raise ValueError("At least one country is required.")

    if any(code not in COUNTRY_CODES for code in countries):
        invalid = [
            code for code in countries
            if code not in COUNTRY_CODES
        ]
        raise ValueError(
            f"Unsupported country codes: {invalid}"
        )

    start_year = int(start_year)

    if end_year is None:
        end_year = start_year

    end_year = int(end_year)

    if start_year > end_year:
        raise ValueError(
            "start_year cannot exceed end_year."
        )

    country_string = ";".join(countries)

    url = (
        f"{BASE_URL}/country/{country_string}"
        f"/indicator/{wb_code}"
    )

    all_records = []
    page = 1

    while True:

        response = requests.get(
            url,
            params={
                "format": "json",
                "date": f"{start_year}:{end_year}",
                "per_page": 1000,
                "page": page
            },
            timeout=30
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError(
                f"Unexpected World Bank response: {payload}"
            )

        metadata, observations = payload

        all_records.extend(observations or [])

        total_pages = int(metadata.get("pages", 1))

        if page >= total_pages:
            break

        page += 1

    rows = []

    for item in all_records:

        code = item.get("countryiso3code")

        if code not in countries:
            continue

        rows.append({
            "Country": COUNTRY_CODES[code],
            "Country_Code": code,
            "Year": int(item["date"]),
            "Value": item.get("value"),
            "Indicator": indicator,
            "Unit": indicator_info["unit"],
            "Source": "World Bank"
        })

    df = pd.DataFrame(
        rows,
        columns=[
            "Country",
            "Country_Code",
            "Year",
            "Value",
            "Indicator",
            "Unit",
            "Source"
        ]
    )

    if not df.empty:
        df["Value"] = pd.to_numeric(
            df["Value"], errors="coerce"
        )

    # Construct the complete country-year grid.
    # This ensures missing observations remain visible.
    grid = pd.MultiIndex.from_product(
        [countries, range(start_year, end_year + 1)],
        names=["Country_Code", "Year"]
    ).to_frame(index=False)

    df = grid.merge(
        df,
        on=["Country_Code", "Year"],
        how="left",
        validate="one_to_one"
    )

    df["Country"] = df["Country_Code"].map(
        COUNTRY_CODES
    )

    df["Indicator"] = indicator
    df["Unit"] = indicator_info["unit"]
    df["Source"] = "World Bank"

    return (
        df[
            [
                "Country",
                "Country_Code",
                "Year",
                "Value",
                "Indicator",
                "Unit",
                "Source"
            ]
        ]
        .sort_values(["Country", "Year"])
        .reset_index(drop=True)
    )


def fetch_region_data(
    indicator,
    region,
    start_year,
    end_year=None
):
    """
    Retrieve data for countries in a catalog region.

    Note: catalog.py currently contains curated,
    incomplete regional lists.
    """

    key = region.strip().lower().replace(" ", "_")

    if key not in REGIONS:
        raise ValueError(f"Unknown region: {region}")

    return fetch_worldbank_data(
        indicator=indicator,
        countries=REGIONS[key],
        start_year=start_year,
        end_year=end_year
    )


def get_data_quality_report(df):
    """
    Summarize missing observations and data coverage.
    """

    total = len(df)
    available = int(df["Value"].notna().sum())
    missing = total - available

    report = {
        "total_observations": total,
        "available_observations": available,
        "missing_observations": missing,
        "coverage_percentage": (
            round(100 * available / total, 2)
            if total else 0
        ),
        "countries": int(df["Country_Code"].nunique()),
        "start_year": (
            int(df["Year"].min()) if total else None
        ),
        "end_year": (
            int(df["Year"].max()) if total else None
        )
    }

    return report


# ============================================================
# SELF-TEST
# ============================================================

if __name__ == "__main__":

    print("\nECON AI AGENT — WORLD BANK TEST")

    # Test 1: Zambia GDP growth, 2000–2024
    print("\nTEST 1: Zambia GDP Growth")

    zambia = fetch_worldbank_data(
        indicator="gdp_growth",
        countries=["ZMB"],
        start_year=2000,
        end_year=2024
    )

    print(zambia.tail(10).to_string(index=False))

    print("\nData Quality:")
    print(get_data_quality_report(zambia))

    # Test 2: North America GDP growth, 2008
    print("\nTEST 2: North America GDP Growth — 2008")

    north_america = fetch_region_data(
        indicator="gdp_growth",
        region="north_america",
        start_year=2008
    )

    print(
        north_america[
            ["Country", "Year", "Value"]
        ].to_string(index=False)
    )

    print("\nData Quality:")
    print(get_data_quality_report(north_america))
