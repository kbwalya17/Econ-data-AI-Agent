
"""
Econ AI Agent
Module: econ_validators.py

Validate economic analysis requests and datasets.

Goals:
- Reject unsupported indicators and countries.
- Validate years and geographic regions.
- Prevent incomplete regional rankings from being
  presented as comprehensive.
- Detect incompatible data and missing observations.
- Keep the AI from inventing unsupported parameters.
"""

from datetime import datetime
import re

import pandas as pd

from catalog import INDICATORS, COUNTRIES, REGIONS


# ============================================================
# 1. BASIC VALIDATION
# ============================================================

MIN_YEAR = 1960

# A future year may be valid for some forecasts, but
# this agent analyzes historical observations only.
MAX_YEAR = datetime.now().year

COUNTRY_CODE_TO_NAME = {
    code: name for name, code in COUNTRIES.items()
}


def validate_indicator(indicator, source=None):
    """
    Validate an indicator and optional data source.

    Returns the canonical indicator key.
    """

    if not isinstance(indicator, str):
        raise ValueError("Indicator must be a string.")

    key = indicator.strip().lower()

    if key not in INDICATORS:
        raise ValueError(
            f"Unsupported indicator: {indicator}. "
            f"Supported indicators: {list(INDICATORS)}"
        )

    if source is not None:
        source = source.strip().lower()

        if source not in {"worldbank", "fred"}:
            raise ValueError(
                "Source must be 'worldbank' or 'fred'."
            )

        if not INDICATORS[key].get(source):
            raise ValueError(
                f"Indicator '{key}' is not supported "
                f"by {source}."
            )

    return key


def validate_country(country):
    """
    Accept a supported country name or ISO3 code.

    Returns the canonical ISO3 code.
    """

    if not isinstance(country, str):
        raise ValueError("Country must be a string.")

    value = country.strip()

    if not value:
        raise ValueError("Country cannot be empty.")

    code = value.upper()

    if code in COUNTRY_CODE_TO_NAME:
        return code

    for name, iso3 in COUNTRIES.items():
        if name.lower() == value.lower():
            return iso3

    raise ValueError(
        f"Unsupported country: {country}. "
        "Country catalog expansion is required "
        "for countries not currently listed."
    )


def validate_countries(countries):
    """
    Validate a list of countries and remove duplicates
    while preserving their original order.
    """

    if isinstance(countries, str):
        countries = [countries]

    if not isinstance(countries, (list, tuple)):
        raise ValueError(
            "Countries must be a list or a string."
        )

    if not countries:
        raise ValueError(
            "At least one country is required."
        )

    result = []

    for country in countries:
        code = validate_country(country)

        if code not in result:
            result.append(code)

    return result


def validate_year(year):
    """Validate a historical observation year."""

    if isinstance(year, bool):
        raise ValueError("Year must be an integer.")

    try:
        year_int = int(year)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid year: {year}"
        ) from None

    # Reject strings such as "2020.5".
    if str(year).strip() != str(year_int):
        raise ValueError(
            f"Year must be a whole number: {year}"
        )

    if not MIN_YEAR <= year_int <= MAX_YEAR:
        raise ValueError(
            f"Year must be between "
            f"{MIN_YEAR} and {MAX_YEAR}."
        )

    return year_int


def validate_year_range(start_year, end_year):
    """Validate the requested historical period."""

    start = validate_year(start_year)
    end = validate_year(end_year)

    if start > end:
        raise ValueError(
            "Start year cannot exceed end year."
        )

    return start, end


# ============================================================
# 2. REGION VALIDATION
# ============================================================

# Our current region catalog is curated and incomplete.
# Until we introduce complete geographic metadata,
# all catalog regions must be treated as partial samples.

REGION_COVERAGE = {
    region: "partial"
    for region in REGIONS
}


def validate_region(region):
    """
    Validate a region name.

    Returns its canonical key and country list.
    """

    if not isinstance(region, str):
        raise ValueError("Region must be a string.")

    key = (
        region.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    if key not in REGIONS:
        raise ValueError(
            f"Unsupported region: {region}. "
            f"Available regions: {list(REGIONS)}"
        )

    countries = validate_countries(REGIONS[key])

    return {
        "region": key,
        "countries": countries,
        "coverage": REGION_COVERAGE[key],
        "country_count": len(countries),
    }


def validate_region_ranking(region, comprehensive=False):
    """
    Check whether a regional ranking can be performed.

    comprehensive=True means the user expects every
    eligible country in the region to be considered.

    Our current catalog cannot satisfy that requirement.
    """

    result = validate_region(region)

    if comprehensive and result["coverage"] != "complete":
        raise ValueError(
            f"Cannot produce a comprehensive ranking "
            f"for '{region}'. The current catalog contains "
            f"only {result['country_count']} selected "
            "countries. Complete geographic metadata "
            "is required."
        )

    return result


# ============================================================
# 3. ANALYSIS REQUEST VALIDATION
# ============================================================

SUPPORTED_ANALYSES = {
    "ranking",
    "comparison",
    "trend",
    "profile",
}


def validate_analysis_request(request):
    """
    Validate a structured economic analysis request.

    Expected examples:

    {
        "analysis": "ranking",
        "indicator": "gdp_growth",
        "region": "north_america",
        "year": 2008,
        "comprehensive": False
    }

    {
        "analysis": "comparison",
        "indicator": "inflation",
        "countries": ["Zambia", "Kenya"],
        "start_year": 2000,
        "end_year": 2024
    }
    """

    if not isinstance(request, dict):
        raise ValueError(
            "Analysis request must be a dictionary."
        )

    analysis = request.get("analysis")

    if not isinstance(analysis, str):
        raise ValueError(
            "Analysis type is required."
        )

    analysis = analysis.strip().lower()

    if analysis not in SUPPORTED_ANALYSES:
        raise ValueError(
            f"Unsupported analysis: {analysis}"
        )

    validated = {"analysis": analysis}

    if analysis != "profile":
        validated["indicator"] = validate_indicator(
            request.get("indicator")
        )

    if analysis == "ranking":

        validated["year"] = validate_year(
            request.get("year")
        )

        if "region" in request and "countries" in request:
            raise ValueError(
                "Specify either region or countries, "
                "not both."
            )

        if "region" in request:
            comprehensive = request.get(
                "comprehensive", True
            )

            if not isinstance(comprehensive, bool):
                raise ValueError(
                    "comprehensive must be true or false."
                )

            region_info = validate_region_ranking(
                request["region"],
                comprehensive=comprehensive
            )

            validated.update(region_info)
            validated["comprehensive"] = comprehensive

        elif "countries" in request:
            validated["countries"] = validate_countries(
                request["countries"]
            )
            validated["comprehensive"] = False

        else:
            raise ValueError(
                "Ranking requires region or countries."
            )

        top_n = request.get("top_n")

        if top_n is not None:
            if isinstance(top_n, bool):
                raise ValueError(
                    "top_n must be a positive integer."
                )

            try:
                top_n_int = int(top_n)
            except (TypeError, ValueError):
                raise ValueError(
                    "top_n must be a positive integer."
                ) from None

            if (
                str(top_n).strip() != str(top_n_int)
                or top_n_int < 1
            ):
                raise ValueError(
                    "top_n must be a positive integer."
                )

            validated["top_n"] = top_n_int

    elif analysis == "comparison":

        validated["countries"] = validate_countries(
            request.get("countries")
        )

        start, end = validate_year_range(
            request.get("start_year"),
            request.get("end_year")
        )

        validated["start_year"] = start
        validated["end_year"] = end

    elif analysis == "trend":

        validated["country"] = validate_country(
            request.get("country")
        )

        start, end = validate_year_range(
            request.get("start_year"),
            request.get("end_year")
        )

        validated["start_year"] = start
        validated["end_year"] = end

    elif analysis == "profile":

        validated["country"] = validate_country(
            request.get("country")
        )

        indicators = request.get(
            "indicators",
            [
                "gdp_growth",
                "gdp_per_capita",
                "inflation",
                "unemployment",
                "population",
            ]
        )

        if not isinstance(indicators, list) or not indicators:
            raise ValueError(
                "Profile indicators must be a nonempty list."
            )

        validated["indicators"] = list(dict.fromkeys(
            validate_indicator(ind, source="worldbank")
            for ind in indicators
        ))

        start, end = validate_year_range(
            request.get("start_year"),
            request.get("end_year")
        )

        validated["start_year"] = start
        validated["end_year"] = end

    return validated


# ============================================================
# 4. DATASET VALIDATION
# ============================================================

def validate_dataset(df, require_values=True):
    """
    Check the integrity of a retrieved dataset.

    Missing observations are allowed and reported,
    not automatically replaced.
    """

    if not isinstance(df, pd.DataFrame):
        raise ValueError(
            "Dataset must be a pandas DataFrame."
        )

    if df.empty:
        raise ValueError(
            "Dataset is empty."
        )

    required_columns = {
        "Country",
        "Country_Code",
        "Value",
        "Indicator",
        "Source",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing dataset columns: "
            f"{sorted(missing_columns)}"
        )

    values = pd.to_numeric(
        df["Value"],
        errors="coerce"
    )

    available = int(values.notna().sum())
    missing = int(values.isna().sum())

    if require_values and available == 0:
        raise ValueError(
            "Dataset contains no available numeric observations."
        )

    return {
        "valid": True,
        "total_observations": len(df),
        "available_observations": available,
        "missing_observations": missing,
        "coverage_percentage": round(
            100 * available / len(df), 2
        ),
        "indicators": sorted(
            df["Indicator"].dropna().unique().tolist()
        ),
        "sources": sorted(
            df["Source"].dropna().unique().tolist()
        ),
    }


# ============================================================
# 5. SELF-TEST
# ============================================================

if __name__ == "__main__":

    print("\nECON AI AGENT — VALIDATORS TEST")

    print("\nTEST 1: Indicator")
    print(validate_indicator("gdp_growth", "worldbank"))

    print("\nTEST 2: Country")
    print(validate_country("Zambia"))
    print(validate_country("USA"))

    print("\nTEST 3: Year Range")
    print(validate_year_range(2000, 2024))

    print("\nTEST 4: Explicit Country Ranking")

    ranking = validate_analysis_request({
        "analysis": "ranking",
        "indicator": "gdp_growth",
        "countries": ["USA", "Canada", "Mexico"],
        "year": 2008,
    })

    print(ranking)

    print("\nTEST 5: Incomplete Regional Ranking")

    try:
        validate_analysis_request({
            "analysis": "ranking",
            "indicator": "gdp_growth",
            "region": "africa",
            "year": 2008,
        })
    except ValueError as error:
        print("Correctly rejected:", error)

    print("\nTEST 6: Clearly Labeled Regional Sample")

    sample = validate_analysis_request({
        "analysis": "ranking",
        "indicator": "gdp_growth",
        "region": "africa",
        "year": 2008,
        "comprehensive": False,
    })

    print(sample)

    print("\nTEST 7: Country Comparison")

    comparison = validate_analysis_request({
        "analysis": "comparison",
        "indicator": "inflation",
        "countries": ["Zambia", "Kenya", "Ghana"],
        "start_year": 2000,
        "end_year": 2024,
    })

    print(comparison)

    print("\nTEST 8: Dataset Integrity")

    sample_df = pd.DataFrame({
        "Country": ["Zambia", "Kenya", "Ghana"],
        "Country_Code": ["ZMB", "KEN", "GHA"],
        "Value": [4.5, None, 3.2],
        "Indicator": ["gdp_growth"] * 3,
        "Source": ["World Bank"] * 3,
    })

    print(validate_dataset(sample_df))

    print("\nALL VALIDATOR TESTS COMPLETED")
