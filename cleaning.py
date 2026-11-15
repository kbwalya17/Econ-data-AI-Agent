
"""
Econ AI Agent
Module: cleaning.py

Clean and standardize economic datasets retrieved from
World Bank and FRED.

Principles:
- Never invent missing observations.
- Never silently interpolate or forward-fill data.
- Preserve source information.
- Keep annual and monthly observations distinguishable.
"""

import pandas as pd


STANDARD_COLUMNS = [
    "Country",
    "Country_Code",
    "Date",
    "Year",
    "Value",
    "Indicator",
    "Unit",
    "Source",
    "Series_ID",
]


def clean_economic_data(df):
    """
    Standardize World Bank or FRED data.

    Returns a cleaned DataFrame with consistent columns.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    if df.empty:
        raise ValueError("Cannot clean an empty dataset.")

    data = df.copy()

    required = {
        "Country",
        "Country_Code",
        "Value",
        "Indicator",
        "Source",
    }

    missing_columns = required - set(data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if "Date" not in data.columns and "Year" not in data.columns:
        raise ValueError(
            "Dataset must contain either Date or Year."
        )

    # Convert economic observations to numeric values.
    # Non-numeric entries become NaN, not zero.
    data["Value"] = pd.to_numeric(
        data["Value"],
        errors="coerce"
    )

    # Standardize country identifiers.
    data["Country_Code"] = (
        data["Country_Code"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    
    if "Date" not in data.columns:
        data["Year"] = pd.to_numeric(
            data["Year"],
            errors="raise"
        ).astype(int)

        data["Date"] = pd.to_datetime(
            data["Year"].astype(str) + "-01-01"
        )

        data["Frequency"] = "Annual"

    else:
        data["Date"] = pd.to_datetime(
            data["Date"],
            errors="raise"
        )

        data["Year"] = data["Date"].dt.year

        
        data["Frequency"] = "Time Series"


    for column in STANDARD_COLUMNS:
        if column not in data.columns:
            data[column] = pd.NA

    # Flag missing economic observations.
    data["Missing"] = data["Value"].isna()

    # Removes duplicate observations only when identical
    
    duplicate_keys = [
        "Country_Code",
        "Date",
        "Indicator",
        "Source",
    ]

    duplicates = data.duplicated(
        subset=duplicate_keys,
        keep=False
    )

    if duplicates.any():
        duplicate_rows = data.loc[duplicates]

        conflicting = (
            duplicate_rows
            .groupby(duplicate_keys, dropna=False)["Value"]
            .nunique(dropna=False)
        )

        if (conflicting > 1).any():
            raise ValueError(
                "Conflicting duplicate economic observations detected."
            )

        data = data.drop_duplicates(
            subset=duplicate_keys,
            keep="first"
        )

    output_columns = STANDARD_COLUMNS + [
        "Frequency",
        "Missing",
    ]

    return (
        data[output_columns]
        .sort_values(
            ["Country_Code", "Indicator", "Date"]
        )
        .reset_index(drop=True)
    )


def summarize_missing_data(df):
    """
    Report missing observations by country and indicator.
    """

    required = {
        "Country",
        "Indicator",
        "Value",
    }

    if not required.issubset(df.columns):
        raise ValueError(
            "Dataset is missing required columns."
        )

    summary = (
        df.groupby(
            ["Country", "Indicator"],
            dropna=False
        )
        .agg(
            Total_Observations=("Value", "size"),
            Available_Observations=(
                "Value",
                lambda x: x.notna().sum()
            ),
            Missing_Observations=(
                "Value",
                lambda x: x.isna().sum()
            ),
        )
        .reset_index()
    )

    summary["Coverage_Percent"] = (
        summary["Available_Observations"]
        / summary["Total_Observations"]
        * 100
    ).round(2)

    return summary


def get_available_data(df):
    """
    Return observations with actual numeric values.

    Use this for calculations, while retaining the
    original cleaned dataset for data-quality reports.
    """

    return df.loc[
        df["Value"].notna()
    ].copy()



# SELF-TEST


if __name__ == "__main__":

    from worldbank import fetch_worldbank_data
    from fred import fetch_fred_data

    print("\nECON AI AGENT — CLEANING TEST")

   
    # TEST 1: World Bank annual data
    

    print("\nTEST 1: World Bank GDP Growth")

    wb_raw = fetch_worldbank_data(
        indicator="gdp_growth",
        countries=["ZMB", "KEN", "GHA"],
        start_year=2000,
        end_year=2024
    )

    wb_clean = clean_economic_data(wb_raw)

    print(
        wb_clean.tail(10).to_string(index=False)
    )

    print("\nMissing Data Report:")
    print(
        summarize_missing_data(wb_clean).to_string(index=False)
    )

 
    # TEST 2: FRED monthly data


    print("\nTEST 2: FRED Unemployment")

    fred_raw = fetch_fred_data(
        indicator="unemployment",
        start_date="2023-01-01",
        end_date="2024-12-31"
    )

    fred_clean = clean_economic_data(fred_raw)

    print(
        fred_clean.tail(10).to_string(index=False)
    )

    print("\nMissing Data Report:")
    print(
        summarize_missing_data(fred_clean).to_string(index=False)
    )

    print("\nALL CLEANING TESTS COMPLETED")
