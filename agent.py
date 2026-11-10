
"""
Econ AI Agent
Module: agent.py

Gemini-powered natural language interface.

Responsibilities:
1. Interpret economic research questions.
2. Produce structured analysis requests.
3. Validate requests using the Python validator.
4. Explain verified economic analysis results.

Gemini does not retrieve data or calculate statistics.
"""

import json
import os
import re

import pandas as pd
from dotenv import load_dotenv
from google import genai

from catalog import INDICATORS, COUNTRIES, REGIONS
from econ_validators import validate_analysis_request


# ============================================================
# 1. GEMINI CONFIGURATION
# ============================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# This model worked in our earlier prototype.
MODEL_NAME = "gemini-3.5-flash-lite"


def get_gemini_client():
    """Create a Gemini client using the environment API key."""

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is missing from your .env file."
        )

    return genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# 2. NATURAL LANGUAGE QUESTION PARSING
# ============================================================

def parse_economic_question(question):
    """
    Convert a natural-language question into a
    validated structured economic analysis request.

    Returns a dictionary accepted by econ_validators.py.
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please provide an economic question.")

    client = get_gemini_client()

    indicator_options = {
        key: value["name"]
        for key, value in INDICATORS.items()
    }

    prompt = f"""
You are an economic research query parser.

Your task is to translate the user's question into
ONE structured JSON object.

You do NOT answer the economic question.
You do NOT retrieve data.
You do NOT invent countries, indicators, or years.

SUPPORTED ANALYSIS TYPES:
- ranking
- comparison
- trend
- profile

SUPPORTED INDICATORS:
{json.dumps(indicator_options, indent=2)}

SUPPORTED COUNTRIES:
{json.dumps(COUNTRIES, indent=2)}

SUPPORTED REGIONS:
{json.dumps(list(REGIONS.keys()))}

IMPORTANT GEOGRAPHIC RULE:
Our regional country lists are currently incomplete.

For a question requesting all countries in a region,
use the "region" field and set "comprehensive": true.

For a question explicitly asking about a selected
sample of countries, use the "countries" field.

Never silently turn a comprehensive regional question
into a selected-country ranking.

REQUEST FORMATS:

Ranking:
{{
  "analysis": "ranking",
  "indicator": "gdp_growth",
  "countries": ["USA", "CAN", "MEX"],
  "year": 2008,
  "top_n": 3
}}

Regional ranking:
{{
  "analysis": "ranking",
  "indicator": "gdp_growth",
  "region": "africa",
  "year": 2008,
  "comprehensive": true
}}

Comparison:
{{
  "analysis": "comparison",
  "indicator": "inflation",
  "countries": ["Zambia", "Kenya"],
  "start_year": 2000,
  "end_year": 2024
}}

Trend:
{{
  "analysis": "trend",
  "indicator": "gdp_growth",
  "country": "Zambia",
  "start_year": 2000,
  "end_year": 2024
}}

Profile:
{{
  "analysis": "profile",
  "country": "Zambia",
  "indicators": [
    "gdp_growth",
    "inflation",
    "unemployment",
    "population"
  ],
  "start_year": 2020,
  "end_year": 2024
}}

RULES:
1. Return ONLY valid JSON.
2. Do not include markdown formatting.
3. Use only supported indicator keys.
4. Use only supported countries.
5. Do not invent dates or geographic coverage.
6. If the question is ambiguous, return:
   {{"error": "A short clarification question"}}
7. If the question cannot be answered with the
   supported analysis types, return:
   {{"error": "Explanation of unsupported request"}}
8. Do not add unsupported parameters.
9. Use the user's requested years exactly.
10. Do not assume a year or period if none is supplied.

USER QUESTION:
{question}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    text = (response.text or "").strip()

    # Remove optional markdown code fences.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(r"\s*```$", "", text).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Gemini returned invalid JSON. "
            f"Response: {text[:500]}"
        ) from error

    if not isinstance(parsed, dict):
        raise ValueError(
            "Gemini must return a JSON object."
        )

    if "error" in parsed:
        raise ValueError(str(parsed["error"]))

    # Python is the final authority on valid requests.
    return validate_analysis_request(parsed)


# ============================================================
# 3. PREPARE VERIFIED RESULTS FOR GEMINI
# ============================================================

def make_json_safe(value):
    """
    Convert pandas and NumPy values into JSON-safe
    objects for Gemini.

    Missing numeric values become null.
    """

    if isinstance(value, pd.DataFrame):
        return [
            make_json_safe(row)
            for row in value.to_dict(orient="records")
        ]

    if isinstance(value, pd.Series):
        return make_json_safe(value.to_dict())

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, pd.Timedelta):
        return str(value)

    # Handle NumPy scalar types.
    if hasattr(value, "item"):
        try:
            return make_json_safe(value.item())
        except (ValueError, TypeError):
            pass

    if isinstance(value, float):
        if pd.isna(value):
            return None
        return value

    if isinstance(value, (int, str, bool)):
        return value

    if pd.isna(value):
        return None

    return str(value)


# ============================================================
# 4. GROUNDED ECONOMIC INTERPRETATION
# ============================================================

def explain_economic_results(
    question,
    analysis_result,
    source,
    request=None
):
    """
    Explain verified economic statistics in plain English.

    The result must already have been calculated by Python.
    Gemini is prohibited from introducing new statistics.
    """

    client = get_gemini_client()

    verified_result = make_json_safe(
        analysis_result
    )

    verified_request = make_json_safe(
        request or {}
    )

    prompt = f"""
You are an economic research assistant.

Write a clear, natural, professional explanation of
the verified economic analysis provided below.

The numerical results have already been calculated
using Python and official economic data.

STRICT RULES:
1. Use ONLY the supplied numerical results.
2. Never invent economic statistics.
3. Never invent countries, observation years, or rankings.
4. Never calculate new statistics yourself.
5. Never describe correlation as causation.
6. Do not invent explanations for economic changes.
7. Clearly acknowledge missing observations.
8. Explain the units and time period.
9. Distinguish annual and monthly observations.
10. Do not claim the data are more recent than supplied.
11. If geographic coverage is incomplete, explicitly
    state that the results cover only the selected sample.
12. Avoid exaggerated or overly confident language.
13. Write like a careful economic research analyst.
14. Do not include information unsupported by the results.

USER QUESTION:
{question}

VALIDATED REQUEST:
{json.dumps(verified_request, indent=2)}

DATA SOURCE:
{source}

VERIFIED ANALYSIS RESULTS:
{json.dumps(verified_result, indent=2, allow_nan=False)}

Write a concise economic briefing with:
- A direct answer
- Important numerical findings
- Relevant qualifications about the data
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    explanation = (response.text or "").strip()

    if not explanation:
        raise ValueError(
            "Gemini returned an empty explanation."
        )

    return explanation


# ============================================================
# 5. SELF-TEST
# ============================================================

if __name__ == "__main__":

    print("\nECON AI AGENT — GEMINI TEST")

    # --------------------------------------------------------
    # TEST 1: Parse a ranking question
    # --------------------------------------------------------

    print("\nTEST 1: Natural Language Ranking")

    question_1 = (
        "Rank the United States, Canada, and Mexico "
        "by GDP growth in 2008."
    )

    parsed_1 = parse_economic_question(
        question_1
    )

    print(json.dumps(parsed_1, indent=2))

    # --------------------------------------------------------
    # TEST 2: Parse a comparison question
    # --------------------------------------------------------

    print("\nTEST 2: Country Comparison")

    question_2 = (
        "Compare inflation in Zambia and Kenya "
        "between 2000 and 2024."
    )

    parsed_2 = parse_economic_question(
        question_2
    )

    print(json.dumps(parsed_2, indent=2))

    # --------------------------------------------------------
    # TEST 3: Grounded economic explanation
    # --------------------------------------------------------

    print("\nTEST 3: Grounded Interpretation")

    # Illustrative test values, NOT actual economic data.
    sample_results = {
        "test_data_only": True,
        "indicator": "gdp_growth",
        "year": 2008,
        "unit": "%",
        "rankings": [
            {"country": "A", "value": 2.5, "rank": 1},
            {"country": "B", "value": 1.2, "rank": 2},
            {"country": "C", "value": -0.5, "rank": 3},
        ],
        "missing_countries": [],
    }

    explanation = explain_economic_results(
        question="Explain this illustrative GDP growth ranking.",
        analysis_result=sample_results,
        source="Synthetic test data — not World Bank",
        request={
            "analysis": "ranking",
            "indicator": "gdp_growth",
            "year": 2008,
            "countries": ["A", "B", "C"]
        }
    )

    print(explanation)

    print("\nALL GEMINI TESTS COMPLETED")
