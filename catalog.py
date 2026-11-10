
"""
Econ AI Agent
Module: catalog.py

Verified economic indicator definitions, country identifiers,
and geographic classifications.
"""

# ============================================================
# 1. ECONOMIC INDICATOR CATALOG
# ============================================================

INDICATORS = {
    "gdp_growth": {
        "name": "Real GDP Growth",
        "description": "Annual percentage growth of real GDP",
        "unit": "%",
        "worldbank": "NY.GDP.MKTP.KD.ZG",
        "fred": "A191RL1",
        "fred_frequency": "quarterly",
        "fred_note": "Quarterly annualized rate; not directly comparable with annual World Bank GDP growth.",
    },


    "gdp_per_capita": {
        "name": "GDP per capita (constant 2021 US$)",
        "worldbank": "NY.GDP.PCAP.KD",
        "fred": None,
        "unit": "constant 2021 US$",
    },

    "gdp": {
        "name": "GDP (current US$)",
        "worldbank": "NY.GDP.MKTP.CD",
        "fred": None,
        "unit": "current US$",
    },

    "real_gdp": {
      "name": "GDP (constant 2021 US$)",
       "worldbank": "NY.GDP.MKTP.KD",
       "fred": None,
       "unit": "constant 2021 US$",
    },

    "inflation": {
        "name": "Consumer Price Inflation",
        "description": "Annual inflation measured using consumer prices",
        "unit": "%",
        "worldbank": "FP.CPI.TOTL.ZG",
        "fred": "CPIAUCSL",
        "fred_transformation": "12-month percentage change",
    },

    "unemployment": {
        "name": "Unemployment Rate",
        "description": "Unemployment as a percentage of the labor force",
        "unit": "%",
        "worldbank": "SL.UEM.TOTL.ZS",
        "fred": "UNRATE",
    },

    "population": {
        "name": "Total Population",
        "description": "Total population",
        "unit": "people",
        "worldbank": "SP.POP.TOTL",
        "fred": "POP",
        "fred_note": "Monthly U.S. population estimate in thousands.",
    },

    "life_expectancy": {
        "name": "Life Expectancy at Birth",
        "description": "Life expectancy at birth, total",
        "unit": "years",
        "worldbank": "SP.DYN.LE00.IN",
        "fred": None,
    },

    "manufacturing": {
        "name": "Manufacturing Value Added",
        "description": "Manufacturing value added as a percentage of GDP",
        "unit": "% of GDP",
        "worldbank": "NV.IND.MANF.ZS",
        "fred": None,
    },

    "exports": {
        "name": "Exports of Goods and Services",
        "description": "Exports as a percentage of GDP",
        "unit": "% of GDP",
        "worldbank": "NE.EXP.GNFS.ZS",
        "fred": None,
    },

    "imports": {
        "name": "Imports of Goods and Services",
        "description": "Imports as a percentage of GDP",
        "unit": "% of GDP",
        "worldbank": "NE.IMP.GNFS.ZS",
        "fred": None,
    },

    "fed_funds_rate": {
        "name": "Federal Funds Rate",
        "description": "Monthly average effective federal funds rate",
        "unit": "%",
        "worldbank": None,
        "fred": "FEDFUNDS",
    },
}


# ============================================================
# 2. COUNTRY CATALOG
# ============================================================

# ISO alpha-3 country codes.
# This is a starter catalog, not an exhaustive global list.
# Later we will expand it using official country metadata.

COUNTRIES = {
    # North America
    "United States": "USA",
    "Canada": "CAN",
    "Mexico": "MEX",

    # Central America
    "Belize": "BLZ",
    "Costa Rica": "CRI",
    "El Salvador": "SLV",
    "Guatemala": "GTM",
    "Honduras": "HND",
    "Nicaragua": "NIC",
    "Panama": "PAN",

    # Caribbean
    "Bahamas": "BHS",
    "Barbados": "BRB",
    "Cuba": "CUB",
    "Dominican Republic": "DOM",
    "Haiti": "HTI",
    "Jamaica": "JAM",
    "Trinidad and Tobago": "TTO",

    # Africa
    "Zambia": "ZMB",
    "Zimbabwe": "ZWE",
    "Botswana": "BWA",
    "South Africa": "ZAF",
    "Namibia": "NAM",
    "Kenya": "KEN",
    "Uganda": "UGA",
    "Tanzania": "TZA",
    "Rwanda": "RWA",
    "Ghana": "GHA",
    "Nigeria": "NGA",
    "Ethiopia": "ETH",
    "Egypt": "EGY",
    "Morocco": "MAR",
    "Senegal": "SEN",

    # Europe
    "United Kingdom": "GBR",
    "Germany": "DEU",
    "France": "FRA",
    "Italy": "ITA",
    "Spain": "ESP",
    "Switzerland": "CHE",

    # Asia
    "China": "CHN",
    "India": "IND",
    "Japan": "JPN",
    "South Korea": "KOR",
    "Indonesia": "IDN",
    "Singapore": "SGP",

    # South America
    "Brazil": "BRA",
    "Argentina": "ARG",
    "Chile": "CHL",
    "Colombia": "COL",
    "Peru": "PER",

    # Oceania
    "Australia": "AUS",
    "New Zealand": "NZL",
}


# ============================================================
# 3. GEOGRAPHIC REGIONS
# ============================================================

# Explicit country groupings for the MVP.
# These are curated lists, not complete geographic coverage.
# We must not present rankings as exhaustive until we load
# a complete country classification.

REGIONS = {
    "north_america": [
        "USA", "CAN", "MEX"
    ],

    "central_america": [
        "BLZ", "CRI", "SLV", "GTM",
        "HND", "NIC", "PAN"
    ],

    "caribbean": [
        "BHS", "BRB", "CUB", "DOM",
        "HTI", "JAM", "TTO"
    ],

    "africa": [
        "ZMB", "ZWE", "BWA", "ZAF", "NAM",
        "KEN", "UGA", "TZA", "RWA", "GHA",
        "NGA", "ETH", "EGY", "MAR", "SEN"
    ],

    "europe": [
        "GBR", "DEU", "FRA", "ITA", "ESP", "CHE"
    ],

    "asia": [
        "CHN", "IND", "JPN", "KOR", "IDN", "SGP"
    ],

    "south_america": [
        "BRA", "ARG", "CHL", "COL", "PER"
    ],

    "oceania": [
        "AUS", "NZL"
    ],
}


# ============================================================
# 4. LOOKUP FUNCTIONS
# ============================================================

def get_indicator(indicator_key):
    """Return the metadata for a supported economic indicator."""

    key = indicator_key.strip().lower()

    if key not in INDICATORS:
        raise ValueError(
            f"Unsupported indicator: {indicator_key}. "
            f"Available indicators: {list(INDICATORS.keys())}"
        )

    return INDICATORS[key]


def get_country_code(country_name):
    """Convert a supported country name to its ISO3 code."""

    for name, code in COUNTRIES.items():
        if name.lower() == country_name.strip().lower():
            return code

    raise ValueError(f"Country not found: {country_name}")


def get_country_name(country_code):
    """Convert an ISO3 code to a country name."""

    code = country_code.strip().upper()

    for name, iso_code in COUNTRIES.items():
        if iso_code == code:
            return name

    raise ValueError(f"Country code not found: {country_code}")


def get_region_countries(region_name):
    """Return ISO3 country codes in a supported region."""

    key = region_name.strip().lower().replace(" ", "_")

    if key not in REGIONS:
        raise ValueError(
            f"Unsupported region: {region_name}. "
            f"Available regions: {list(REGIONS.keys())}"
        )

    return REGIONS[key]


def list_indicators():
    """Return all supported economic indicator names."""

    return {
        key: value["name"]
        for key, value in INDICATORS.items()
    }


# ============================================================
# 5. BASIC SELF-TEST
# ============================================================

if __name__ == "__main__":

    print("ECON AI AGENT — CATALOG TEST")

    print("\nGDP Growth Indicator:")
    print(get_indicator("gdp_growth"))

    print("\nZambia ISO3 Code:")
    print(get_country_code("Zambia"))

    print("\nUnited States Country Name:")
    print(get_country_name("USA"))

    print("\nNorth America:")
    print(get_region_countries("north_america"))

    print("\nSupported Indicators:")
    print(list_indicators())
