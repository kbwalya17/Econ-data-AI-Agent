
"""
Econ AI Agent
Module: analytics.py

Economic analysis engine.

Capabilities:
1. Country rankings
2. Country comparisons
3. Historical trend analysis
4. Country economic profiles

All calculations use observed data.
Missing observations are never imputed.
"""

import pandas as pd

from catalog import INDICATORS
from cleaning import clean_economic_data, get_available_data
from worldbank import fetch_worldbank_data


# ============================================================
# 1. COUNTRY RANKINGS
# ============================================================

def rank_countries(
    df,
    year,
    ascending=False,
    top_n=None
):
    """
    Rank countries by an economic indicator for a given year.

    Higher values rank first by default.
    Set ascending=True for lowest-value rankings.

    Missing values are excluded from ranking but reported.
    """

    data = clean_economic_data(df)

    year = int(year)

    selected = data.loc[
        data["Year"] == year
    ].copy()

    if selected.empty:
        raise ValueError(
            f"No observations found for {year}."
        )

    if selected["Indicator"].nunique() != 1:
        raise ValueError(
            "Rankings require exactly one indicator."
        )

    if selected["Country_Code"].duplicated().any():
        raise ValueError(
            "Multiple observations per country-year. "
            "Aggregate to an appropriate annual measure first."
        )

    missing = selected.loc[
        selected["Value"].isna(),
        ["Country", "Country_Code"]
    ].copy()

    available = get_available_data(selected)

    available = available.sort_values(
        ["Value", "Country"],
        ascending=[ascending, True]
    ).reset_index(drop=True)

    # Rank represents position in the sorted results.
    # Equal values receive the same statistical rank.
    available["Rank"] = (
        available["Value"]
        .rank(
            method="min",
            ascending=ascending
        )
        .astype(int)
    )

    total_available = len(available)

    if top_n is not None:
        top_n = int(top_n)

        if top_n < 1:
            raise ValueError("top_n must be positive.")

        available = available.head(top_n)

    rankings = available[
        [
            "Rank",
            "Country",
            "Country_Code",
            "Year",
            "Value",
            "Indicator",
            "Unit"
        ]
    ].copy()

    return {
        "rankings": rankings,
        "missing_countries": missing.reset_index(drop=True),
        "total_countries": len(selected),
        "countries_with_data": total_available,
        "countries_missing_data": len(missing),
        "year": year,
        "indicator": selected["Indicator"].iloc[0]
    }


# ============================================================
# 2. COUNTRY COMPARISONS
# ============================================================

def compare_countries(
    df,
    start_year=None,
    end_year=None
):
    """
    Compare countries using descriptive statistics.

    Reports mean, minimum, maximum, latest observation,
    and the number of available observations.

    Note: The mean is an arithmetic average of observed
    values, not a growth rate compounded over time.
    """

    data = clean_economic_data(df)

    if start_year is not None:
        data = data.loc[
            data["Year"] >= int(start_year)
        ]

    if end_year is not None:
        data = data.loc[
            data["Year"] <= int(end_year)
        ]

    if data.empty:
        raise ValueError(
            "No observations in the requested period."
        )

    if data["Indicator"].nunique() != 1:
        raise ValueError(
            "Comparisons require exactly one indicator."
        )

    # Avoid treating monthly and annual observations
    # as interchangeable.
    if data["Frequency"].nunique() != 1:
        raise ValueError(
            "Mixed data frequencies are not supported."
        )

    results = []

    for country_code, group in data.groupby(
        "Country_Code"
    ):

        group = group.sort_values("Date")
        valid = get_available_data(group)

        row = {
            "Country": group["Country"].iloc[0],
            "Country_Code": country_code,
            "Indicator": group["Indicator"].iloc[0],
            "Unit": group["Unit"].iloc[0],
            "Available_Observations": len(valid),
            "Missing_Observations": int(
                group["Value"].isna().sum()
            ),
            "Mean": valid["Value"].mean(),
            "Minimum": valid["Value"].min(),
            "Maximum": valid["Value"].max(),
            "Latest_Value": (
                valid["Value"].iloc[-1]
                if not valid.empty else float("nan")
            ),
            "Latest_Year": (
                int(valid["Year"].iloc[-1])
                if not valid.empty else None
            )
        }

        results.append(row)

    return (
        pd.DataFrame(results)
        .sort_values("Country")
        .reset_index(drop=True)
    )


# ============================================================
# 3. HISTORICAL TREND ANALYSIS
# ============================================================

def analyze_trend(df, country_code):
    """
    Analyze the historical trend for one country.

    Calculates:
    - First and last available observations
    - Mean, minimum and maximum
    - Absolute change
    - Number of observations

    Does not claim causality or predict future values.
    """

    data = clean_economic_data(df)

    country_code = country_code.upper()

    selected = data.loc[
        data["Country_Code"] == country_code
    ].copy()

    if selected.empty:
        raise ValueError(
            f"No data for country: {country_code}"
        )

    if selected["Indicator"].nunique() != 1:
        raise ValueError(
            "Trend analysis requires one indicator."
        )

    selected = selected.sort_values("Date")

    valid = get_available_data(selected)

    if valid.empty:
        raise ValueError(
            "No available numeric observations."
        )

    first = valid.iloc[0]
    last = valid.iloc[-1]

    minimum = valid.loc[
        valid["Value"].idxmin()
    ]

    maximum = valid.loc[
        valid["Value"].idxmax()
    ]

    return {
        "country": first["Country"],
        "country_code": country_code,
        "indicator": first["Indicator"],
        "unit": first["Unit"],
        "first_year": int(first["Year"]),
        "first_value": float(first["Value"]),
        "last_year": int(last["Year"]),
        "last_value": float(last["Value"]),
        "absolute_change": float(
            last["Value"] - first["Value"]
        ),
        "mean": float(valid["Value"].mean()),
        "minimum": float(minimum["Value"]),
        "minimum_year": int(minimum["Year"]),
        "maximum": float(maximum["Value"]),
        "maximum_year": int(maximum["Year"]),
        "available_observations": len(valid),
        "missing_observations": int(
            selected["Value"].isna().sum()
        ),
        "data": selected.reset_index(drop=True)
    }


# ============================================================
# 4. COUNTRY ECONOMIC PROFILES
# ============================================================

def build_country_profile(
    country_code,
    indicators=None,
    start_year=2020,
    end_year=2024
):
    """
    Build a descriptive economic profile using World Bank.

    Each indicator reports its latest available observation,
    which may differ across indicators.
    """

    if indicators is None:
        indicators = [
            "gdp_growth",
            "gdp_per_capita",
            "inflation",
            "unemployment",
            "population",
            "life_expectancy",
            "manufacturing",
            "exports"
        ]

    profile_rows = []
    datasets = []

    for indicator in indicators:

        raw = fetch_worldbank_data(
            indicator=indicator,
            countries=[country_code],
            start_year=start_year,
            end_year=end_year
        )

        cleaned = clean_economic_data(raw)

        datasets.append(cleaned)

        valid = get_available_data(cleaned)

        if valid.empty:
            profile_rows.append({
                "Indicator": INDICATORS[indicator]["name"],
                "Indicator_Key": indicator,
                "Latest_Year": None,
                "Latest_Value": float("nan"),
                "Unit": INDICATORS[indicator]["unit"],
                "Available_Observations": 0
            })

            continue

        latest = valid.sort_values("Date").iloc[-1]

        profile_rows.append({
            "Indicator": INDICATORS[indicator]["name"],
            "Indicator_Key": indicator,
            "Latest_Year": int(latest["Year"]),
            "Latest_Value": float(latest["Value"]),
            "Unit": INDICATORS[indicator]["unit"],
            "Available_Observations": len(valid)
        })

    profile = pd.DataFrame(profile_rows)

    underlying_data = pd.concat(
        datasets,
        ignore_index=True
    )

    return {
        "country_code": country_code.upper(),
        "profile": profile,
        "underlying_data": underlying_data
    }


# ============================================================
# 5. SELF-TEST
# ============================================================

if __name__ == "__main__":

    print("\nECON AI AGENT — ANALYTICS TEST")

    # --------------------------------------------------------
    # TEST 1: GDP Growth Rankings, 2008
    # --------------------------------------------------------

    print("\nTEST 1: GDP Growth Rankings — 2008")

    growth = fetch_worldbank_data(
        indicator="gdp_growth",
        countries=["USA", "CAN", "MEX"],
        start_year=2008
    )

    rankings = rank_countries(
        growth,
        year=2008
    )

    print(
        rankings["rankings"].to_string(index=False)
    )

    print("\nMissing Countries:")
    print(
        rankings["missing_countries"].to_string(index=False)
    )

    # --------------------------------------------------------
    # TEST 2: Country Comparison
    # --------------------------------------------------------

    print("\nTEST 2: Zambia, Kenya, Ghana GDP Growth")

    comparison_data = fetch_worldbank_data(
        indicator="gdp_growth",
        countries=["ZMB", "KEN", "GHA"],
        start_year=2000,
        end_year=2024
    )

    comparison = compare_countries(
        comparison_data
    )

    print(
        comparison.to_string(index=False)
    )

    # --------------------------------------------------------
    # TEST 3: Zambia Historical Trend
    # --------------------------------------------------------

    print("\nTEST 3: Zambia GDP Growth Trend")

    trend = analyze_trend(
        comparison_data,
        country_code="ZMB"
    )

    for key, value in trend.items():
        if key != "data":
            print(f"{key}: {value}")

    # --------------------------------------------------------
    # TEST 4: Zambia Economic Profile
    # --------------------------------------------------------

    print("\nTEST 4: Zambia Economic Profile")

    profile = build_country_profile(
        country_code="ZMB",
        start_year=2020,
        end_year=2024
    )

    print(
        profile["profile"].to_string(index=False)
    )

    print("\nALL ANALYTICS TESTS COMPLETED")
