
"""
Econ AI Agent
Module: router.py

Select the appropriate economic data source
and retrieve observations for validated requests.

Routing principles:
- U.S.-only questions: FRED when supported.
- International comparisons: World Bank.
- Non-U.S. countries: World Bank.
- Economic profiles: World Bank.
- No silent substitution between incompatible series.
"""

from datetime import date

import pandas as pd

from catalog import INDICATORS
from econ_validators import validate_analysis_request
from worldbank import fetch_worldbank_data
from fred import fetch_fred_data
from cleaning import clean_economic_data


# 1. SOURCE SELECTION


def select_data_source(request):
    """
    Choose the data source for a validated request.

    Returns:
        "fred" or "worldbank"
    """

    analysis = request["analysis"]

    if analysis == "profile":
        return "worldbank"

    indicator = request["indicator"]
    metadata = INDICATORS[indicator]

    countries = request.get("countries")

    if countries is None:
        country = request.get("country")
        countries = [country] if country else []

    # U.S.-only analysis can use FRED.
    us_only = (
        len(countries) == 1
        and countries[0] == "USA"
    )

    if us_only and metadata.get("fred"):
        return "fred"

    if metadata.get("worldbank"):
        return "worldbank"

    raise ValueError(
        f"No suitable source for indicator '{indicator}' "
        "and the requested countries."
    )


# 2. FRED DATE HANDLING


def get_fred_dates(request):
    """
    Convert a requested year or year range into
    inclusive calendar dates.
    """

    if request["analysis"] == "ranking":
        start_year = request["year"]
        end_year = request["year"]
    else:
        start_year = request["start_year"]
        end_year = request["end_year"]

    return (
        f"{start_year}-01-01",
        f"{end_year}-12-31"
    )



# 3. DATA RETRIEVAL


def retrieve_economic_data(request):
    """
    Validate, route, retrieve, and clean economic data.

    Parameters
    ----------
    request : dict
        Structured economic analysis request.

    Returns
    -------
    dict
        Validated request, source, and cleaned dataset.

    Note:
        Profiles are handled separately because they
        require multiple indicators.
    """

    validated = validate_analysis_request(request)

    if validated["analysis"] == "profile":
        raise ValueError(
            "Profile requests use the multi-indicator "
            "profile builder in analytics.py."
        )

    source = select_data_source(validated)

    analysis = validated["analysis"]
    indicator = validated["indicator"]

    if analysis == "ranking":
        countries = validated["countries"]
        start_year = validated["year"]
        end_year = validated["year"]

    elif analysis == "comparison":
        countries = validated["countries"]
        start_year = validated["start_year"]
        end_year = validated["end_year"]

    elif analysis == "trend":
        countries = [validated["country"]]
        start_year = validated["start_year"]
        end_year = validated["end_year"]

    else:
        raise ValueError(
            f"Unsupported analysis: {analysis}"
        )

    if source == "worldbank":

        raw_data = fetch_worldbank_data(
            indicator=indicator,
            countries=countries,
            start_year=start_year,
            end_year=end_year
        )

    elif source == "fred":

        start_date, end_date = get_fred_dates(
            validated
        )

        raw_data = fetch_fred_data(
            indicator=indicator,
            start_date=start_date,
            end_date=end_date
        )

    else:
        raise ValueError(
            f"Unexpected data source: {source}"
        )

    cleaned = clean_economic_data(raw_data)

    return {
        "request": validated,
        "source": source,
        "data": cleaned,
        "observation_count": len(cleaned),
        "available_observations": int(
            cleaned["Value"].notna().sum()
        ),
        "missing_observations": int(
            cleaned["Value"].isna().sum()
        ),
    }


# 4. SELF-TEST


if __name__ == "__main__":

    print("\nECON AI AGENT — ROUTER TEST")


    # TEST 1: Zambia GDP Growth


    print("\nTEST 1: Zambia GDP Growth → World Bank")

    zambia_request = {
        "analysis": "trend",
        "indicator": "gdp_growth",
        "country": "Zambia",
        "start_year": 2015,
        "end_year": 2024,
    }

    zambia = retrieve_economic_data(
        zambia_request
    )

    print("Selected source:", zambia["source"])
    print(
        zambia["data"].tail(5).to_string(index=False)
    )


    # TEST 2: U.S. Unemployment


    print("\nTEST 2: U.S. Unemployment → FRED")

    us_request = {
        "analysis": "trend",
        "indicator": "unemployment",
        "country": "United States",
        "start_year": 2020,
        "end_year": 2024,
    }

    us = retrieve_economic_data(us_request)

    print("Selected source:", us["source"])
    print(
        us["data"].tail(5).to_string(index=False)
    )


    # TEST 3: Cross-Country Comparison


    print(
        "\nTEST 3: Zambia vs U.S. Inflation "
        "→ World Bank"
    )

    comparison_request = {
        "analysis": "comparison",
        "indicator": "inflation",
        "countries": ["Zambia", "United States"],
        "start_year": 2020,
        "end_year": 2024,
    }

    comparison = retrieve_economic_data(
        comparison_request
    )

    print("Selected source:", comparison["source"])
    print(
        comparison["data"].to_string(index=False)
    )


    # TEST 4: Explicit Country Ranking


    print(
        "\nTEST 4: North America GDP Growth "
        "Ranking → World Bank"
    )

    ranking_request = {
        "analysis": "ranking",
        "indicator": "gdp_growth",
        "countries": ["USA", "CAN", "MEX"],
        "year": 2008,
    }

    ranking = retrieve_economic_data(
        ranking_request
    )

    print("Selected source:", ranking["source"])
    print(
        ranking["data"].to_string(index=False)
    )

    print("\nALL ROUTER TESTS COMPLETED")
