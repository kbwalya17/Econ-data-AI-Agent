
"""
Econ AI Agent
Module: main.py

Connect natural-language understanding, data retrieval,
economic analysis, AI interpretation, and Excel export.

Python performs all numerical calculations.
Gemini interprets the question and explains the results.
"""

import json
from datetime import datetime

import pandas as pd

from agent import (
    parse_economic_question,
    explain_economic_results,
)
from analytics import (
    rank_countries,
    compare_countries,
    analyze_trend,
    build_country_profile,
)
from catalog import INDICATORS
from cleaning import clean_economic_data
from excel import create_excel_report
from router import retrieve_economic_data
from econ_validators import validate_dataset


# ============================================================
# 1. ANALYSIS EXECUTION
# ============================================================

def execute_analysis(request):
    """
    Execute a validated economic research request.

    Returns:
        source
        economic_data
        analysis_result
        notes
    """

    analysis_type = request["analysis"]
    notes = []

    # --------------------------------------------------------
    # COUNTRY ECONOMIC PROFILE
    # --------------------------------------------------------

    if analysis_type == "profile":

        result = build_country_profile(
            country_code=request["country"],
            indicators=request["indicators"],
            start_year=request["start_year"],
            end_year=request["end_year"],
        )

        economic_data = result["underlying_data"]
        analysis_result = result["profile"]

        notes.append(
            "Indicators may have different latest "
            "available observation years."
        )

        return {
            "source": "World Bank",
            "economic_data": economic_data,
            "analysis_result": analysis_result,
            "notes": notes,
        }

    # --------------------------------------------------------
    # OTHER ANALYSIS TYPES
    # --------------------------------------------------------

    # FRED's A191RL1 is quarterly annualized GDP growth.
    # Our current GDP growth analysis uses annual values.
    # For U.S.-only GDP growth questions, use World Bank
    # rather than incorrectly interpreting quarters as years.

    if (
        request["indicator"] == "gdp_growth"
        and request.get("country") == "USA"
    ):
        from worldbank import fetch_worldbank_data

        raw = fetch_worldbank_data(
            indicator="gdp_growth",
            countries=["USA"],
            start_year=request["start_year"],
            end_year=request["end_year"],
        )

        economic_data = clean_economic_data(raw)
        source = "World Bank"

        notes.append(
            "Annual World Bank GDP growth was used "
            "instead of FRED's quarterly annualized series."
        )

    else:
        retrieved = retrieve_economic_data(request)

        economic_data = retrieved["data"]
        source = retrieved["source"]

    # Require at least one usable observation.
    quality = validate_dataset(
        economic_data,
        require_values=True
    )

    if quality["missing_observations"] > 0:
        notes.append(
            f"{quality['missing_observations']} "
            "observations are missing."
        )

    # --------------------------------------------------------
    # RANKING
    # --------------------------------------------------------

    if analysis_type == "ranking":

        # Rankings currently require one observation
        # per country in the requested year.
        # This prevents monthly FRED values from
        # being ranked as annual observations.

        if source == "fred":
            raise ValueError(
                "Annual country rankings using monthly "
                "or quarterly FRED observations are not "
                "supported. Use World Bank annual data."
            )

        result = rank_countries(
            economic_data,
            year=request["year"],
            top_n=request.get("top_n"),
        )

        analysis_result = result

        if request.get("coverage") == "partial":
            notes.append(
                "This is a selected-country sample, "
                "not a comprehensive regional ranking."
            )

    # --------------------------------------------------------
    # COUNTRY COMPARISON
    # --------------------------------------------------------

    elif analysis_type == "comparison":

        analysis_result = compare_countries(
            economic_data,
            start_year=request["start_year"],
            end_year=request["end_year"],
        )

        notes.append(
            "Reported means are arithmetic averages "
            "of available observations."
        )

    # --------------------------------------------------------
    # HISTORICAL TREND
    # --------------------------------------------------------

    elif analysis_type == "trend":

        analysis_result = analyze_trend(
            economic_data,
            country_code=request["country"],
        )

        notes.append(
            "The absolute change is the difference "
            "between the first and last available "
            "indicator values."
        )

    else:
        raise ValueError(
            f"Unsupported analysis: {analysis_type}"
        )

    return {
        "source": source,
        "economic_data": economic_data,
        "analysis_result": analysis_result,
        "notes": notes,
    }


# ============================================================
# 2. PREPARE RESULTS FOR AI INTERPRETATION
# ============================================================

def prepare_briefing_results(execution):
    """
    Construct a concise, verified numerical payload
    for Gemini.

    Full underlying observations remain available
    separately for the Excel workbook.
    """

    result = execution["analysis_result"]

    if isinstance(result, pd.DataFrame):
        summary = result

    elif isinstance(result, dict):

        summary = {
            key: value
            for key, value in result.items()
            if key != "data"
        }

    else:
        summary = result

    data = execution["economic_data"]

    return {
        "analysis": summary,
        "data_quality": {
            "total_observations": len(data),
            "available_observations": int(
                data["Value"].notna().sum()
            ),
            "missing_observations": int(
                data["Value"].isna().sum()
            ),
        },
        "notes": execution["notes"],
    }


# ============================================================
# 3. MAIN ECONOMIC RESEARCH PIPELINE
# ============================================================

def run_econ_agent(
    question,
    generate_briefing=True,
    generate_excel=True,
):
    """
    Run the complete Econ AI Agent pipeline.

    Parameters
    ----------
    question : str
        User's natural-language economic question.

    generate_briefing : bool
        Whether Gemini should explain the results.

    generate_excel : bool
        Whether to create a downloadable Excel workbook.

    Returns
    -------
    dict
        Original question
        Validated request
        Data source
        Economic data
        Analysis results
        AI briefing
        Excel bytes
        Notes
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError(
            "Please enter an economic research question."
        )

    question = question.strip()

    # STEP 1: Interpret and validate the question.
    request = parse_economic_question(question)

    # STEP 2: Retrieve data and calculate results.
    execution = execute_analysis(request)

    source = execution["source"]
    economic_data = execution["economic_data"]
    analysis_result = execution["analysis_result"]
    notes = execution["notes"]

    # STEP 3: Explain verified results.
    briefing = None

    if generate_briefing:

        briefing_payload = prepare_briefing_results(
            execution
        )

        briefing = explain_economic_results(
            question=question,
            analysis_result=briefing_payload,
            source=source,
            request=request,
        )

    # STEP 4: Generate the Excel report.
    excel_bytes = None

    if generate_excel:

        excel_bytes = create_excel_report(
            question=question,
            request=request,
            economic_data=economic_data,
            analysis_result=analysis_result,
            source=source,
            ai_briefing=briefing,
        )

    return {
        "question": question,
        "request": request,
        "source": source,
        "economic_data": economic_data,
        "analysis_result": analysis_result,
        "briefing": briefing,
        "excel_bytes": excel_bytes,
        "notes": notes,
        "generated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }


# ============================================================
# 4. DISPLAY RESULTS IN THE TERMINAL
# ============================================================

def display_results(result):
    """Display the research output in the terminal."""

    print("\n" + "=" * 65)
    print("ECON AI AGENT — ECONOMIC RESEARCH REPORT")
    print("=" * 65)

    print("\nQUESTION:")
    print(result["question"])

    print("\nVALIDATED REQUEST:")
    print(json.dumps(
        result["request"],
        indent=2
    ))

    print("\nDATA SOURCE:")
    print(result["source"])

    print("\nANALYSIS RESULTS:")

    analysis = result["analysis_result"]

    if isinstance(analysis, pd.DataFrame):
        print(analysis.to_string(index=False))

    elif isinstance(analysis, dict):

        if "rankings" in analysis:
            print(
                analysis["rankings"].to_string(
                    index=False
                )
            )

            print("\nCountries missing data:")
            print(
                analysis["missing_countries"].to_string(
                    index=False
                )
            )

        elif "data" in analysis:
            for key, value in analysis.items():
                if key != "data":
                    print(f"{key}: {value}")

        else:
            print(analysis)

    if result["briefing"]:
        print("\nAI ECONOMIC BRIEFING:")
        print(result["briefing"])

    if result["notes"]:
        print("\nRESEARCH NOTES:")
        for note in result["notes"]:
            print("-", note)

    print("\n" + "=" * 65)


# ============================================================
# 5. SELF-TEST
# ============================================================

if __name__ == "__main__":

    print("\nECON AI AGENT — INTEGRATION TEST")

    question = (
        "Compare GDP growth in Zambia, Kenya, "
        "and Ghana between 2000 and 2024."
    )

    print("\nRunning research question:")
    print(question)

    result = run_econ_agent(
        question=question,
        generate_briefing=True,
        generate_excel=True,
    )

    display_results(result)

    # Save the generated workbook for inspection.
    if result["excel_bytes"]:

        output_file = "econ_ai_research_report.xlsx"

        with open(output_file, "wb") as file:
            file.write(result["excel_bytes"])

        print("\nExcel report saved:")
        print(output_file)

    print("\nALL INTEGRATION TESTS COMPLETED")
