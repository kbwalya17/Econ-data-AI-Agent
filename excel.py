
"""
Econ AI Agent
Module: excel.py

Export economic research results to a formatted Excel workbook.

Workbook sheets:
1. Economic Data
2. Analysis Results
3. Data Quality
4. Methodology
5. AI Briefing (when provided)

Works with rankings, comparisons, trends, and profiles.
"""

from datetime import datetime, date
from io import BytesIO
from pathlib import Path
import json
import math

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from catalog import INDICATORS


# ============================================================
# 1. FORMATTING
# ============================================================

NAVY = "17365D"
BLUE = "DCEAF7"
WHITE = "FFFFFF"
DARK = "243447"
GRAY = "64748B"


def safe_excel_value(value):
    """Convert Python values into safe Excel cell values."""

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.to_pydatetime().replace(tzinfo=None)

    if isinstance(value, (datetime, date)):
        if isinstance(value, datetime) and value.tzinfo:
            return value.replace(tzinfo=None)
        return value

    if isinstance(value, (list, dict, tuple)):
        value = json.dumps(value, default=str)

    if hasattr(value, "item"):
        try:
            return safe_excel_value(value.item())
        except (TypeError, ValueError):
            pass

    if not isinstance(value, (str, bytes)):
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

    if isinstance(value, float) and not math.isfinite(value):
        return None

    if isinstance(value, str):
        # Prevent untrusted text from becoming Excel formulas.
        if value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")

    return value


def format_worksheet(ws, table=True):
    """Apply professional formatting to a worksheet."""

    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    for cell in ws[1]:
        cell.fill = PatternFill(
            "solid", fgColor=NAVY
        )
        cell.font = Font(
            bold=True,
            color=WHITE,
            size=11
        )
        cell.alignment = Alignment(
            vertical="center",
            wrap_text=True
        )

    ws.row_dimensions[1].height = 30

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(
                name="Aptos",
                size=10,
                color=DARK
            )

            cell.alignment = Alignment(
                vertical="center"
            )

            if isinstance(cell.value, float):
                cell.number_format = "#,##0.0000"

            elif isinstance(cell.value, datetime):
                cell.number_format = "yyyy-mm-dd"

    for column in ws.columns:
        letter = get_column_letter(column[0].column)

        max_length = max(
            (
                len(str(cell.value))
                if cell.value is not None else 0
            )
            for cell in column
        )

        ws.column_dimensions[letter].width = min(
            max(max_length + 3, 14),
            45
        )

    if table and ws.max_row > 1:
        table_name = (
            "Table" +
            "".join(c for c in ws.title if c.isalnum())
        )

        excel_table = Table(
            displayName=table_name,
            ref=f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"
        )

        excel_table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showRowStripes=True,
            showColumnStripes=False
        )

        ws.add_table(excel_table)


def dataframe_to_sheet(wb, sheet_name, df):
    """Write a DataFrame to a formatted worksheet."""

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"{sheet_name} must be a pandas DataFrame."
        )

    ws = wb.create_sheet(sheet_name)

    if len(df.columns) == 0:
        ws.append(["Information"])
        ws.append(["No columns available"])
        format_worksheet(ws, table=False)
        return ws

    ws.append([str(col) for col in df.columns])

    for record in df.itertuples(index=False, name=None):
        ws.append([
            safe_excel_value(value)
            for value in record
        ])

    format_worksheet(ws, table=True)

    return ws


# ============================================================
# 2. ANALYSIS RESULTS
# ============================================================

def extract_analysis_table(analysis_result):
    """
    Extract the main results table from the
    output of analytics.py.
    """

    if isinstance(analysis_result, pd.DataFrame):
        return analysis_result.copy()

    if not isinstance(analysis_result, dict):
        raise TypeError(
            "Analysis result must be a DataFrame or dictionary."
        )

    # Country ranking
    if "rankings" in analysis_result:
        return analysis_result["rankings"].copy()

    # Country profile
    if "profile" in analysis_result:
        return analysis_result["profile"].copy()

    # Historical trend: summary statistics
    if "first_value" in analysis_result:
        excluded = {"data"}

        summary = {
            key: value
            for key, value in analysis_result.items()
            if key not in excluded
        }

        return pd.DataFrame(
            list(summary.items()),
            columns=["Statistic", "Value"]
        )

    # Generic scalar results
    summary = {
        key: value
        for key, value in analysis_result.items()
        if not isinstance(value, pd.DataFrame)
    }

    return pd.DataFrame(
        list(summary.items()),
        columns=["Statistic", "Value"]
    )


# ============================================================
# 3. DATA QUALITY
# ============================================================

def create_data_quality_table(df):
    """
    Report observation coverage by country and indicator.

    Missing values remain missing.
    """

    required = {
        "Country",
        "Indicator",
        "Value"
    }

    if not required.issubset(df.columns):
        raise ValueError(
            "Economic data must contain Country, "
            "Indicator, and Value columns."
        )

    data = df.copy()

    data["Value"] = pd.to_numeric(
        data["Value"],
        errors="coerce"
    )

    quality = (
        data.groupby(
            ["Country", "Indicator"],
            dropna=False
        )
        .agg(
            Total_Observations=("Value", "size"),
            Available_Observations=(
                "Value",
                lambda x: int(x.notna().sum())
            ),
            Missing_Observations=(
                "Value",
                lambda x: int(x.isna().sum())
            )
        )
        .reset_index()
    )

    quality["Coverage_Percent"] = (
        100 *
        quality["Available_Observations"] /
        quality["Total_Observations"]
    ).round(2)

    return quality


# ============================================================
# 4. METHODOLOGY
# ============================================================

def create_methodology_table(
    question,
    request,
    source,
    economic_data
):
    """Document the source and analytical definitions."""

    rows = [
        ("Research Question", question),
        ("Data Source", source),
        ("Exported At", datetime.now().isoformat(
            timespec="seconds"
        )),
        ("Analysis Type", request.get("analysis", "Unknown")),
        ("Requested Parameters", json.dumps(
            request,
            default=str
        )),
        ("Missing Data Treatment",
         "Missing observations are retained; "
         "calculations exclude missing numeric values."),
        ("Source Note",
         "World Bank Indicators API or FRED, "
         "as specified in the Data Source field."),
    ]

    indicators = (
        economic_data["Indicator"]
        .dropna()
        .unique()
        .tolist()
    )

    for indicator in indicators:
        metadata = INDICATORS.get(indicator, {})

        rows.append((
            f"Indicator: {indicator}",
            metadata.get("name", indicator)
        ))

        rows.append((
            f"Unit: {indicator}",
            metadata.get("unit", "Not specified")
        ))

        if source.lower() == "fred":
            code = metadata.get("fred")
        else:
            code = metadata.get("worldbank")

        rows.append((
            f"Source Code: {indicator}",
            code or "Not specified"
        ))

        if source.lower() == "fred":
            if indicator == "inflation":
                rows.append((
                    "Inflation Transformation",
                    "12-month percentage change in CPIAUCSL"
                ))

            note = metadata.get("fred_note")
            if note:
                rows.append((
                    f"Series Note: {indicator}",
                    note
                ))

    if request.get("coverage") == "partial":
        rows.append((
            "Geographic Coverage",
            "Selected-country sample only; "
            "not a comprehensive regional ranking."
        ))

    if request.get("analysis") == "ranking":
        rows.append((
            "Ranking Method",
            "Observed indicator values sorted; "
            "equal values share the same rank."
        ))

    if request.get("analysis") == "comparison":
        rows.append((
            "Comparison Method",
            "Descriptive statistics of available "
            "observations. Means are arithmetic averages."
        ))

    if request.get("analysis") == "trend":
        rows.append((
            "Trend Method",
            "Descriptive statistics and difference "
            "between first and last available values."
        ))

    return pd.DataFrame(
        rows,
        columns=["Field", "Description"]
    )


# ============================================================
# 5. GENERATE EXCEL WORKBOOK
# ============================================================

def create_excel_report(
    question,
    request,
    economic_data,
    analysis_result,
    source,
    ai_briefing=None,
    output_path=None
):
    """
    Generate an Excel workbook.

    Parameters
    ----------
    question : str
        Original user question.

    request : dict
        Validated structured request.

    economic_data : DataFrame
        Underlying observations used for analysis.

    analysis_result : DataFrame or dict
        Python-computed analysis results.

    source : str
        World Bank or FRED.

    ai_briefing : str, optional
        Gemini's interpretation.

    output_path : str or Path, optional
        If supplied, save workbook to disk.

    Returns
    -------
    bytes
        Excel workbook content, suitable for
        Streamlit's download button.
    """

    if not isinstance(economic_data, pd.DataFrame):
        raise TypeError(
            "economic_data must be a pandas DataFrame."
        )

    if economic_data.empty:
        raise ValueError(
            "Cannot export an empty economic dataset."
        )

    wb = Workbook()

    # Remove the default empty worksheet.
    wb.remove(wb.active)

    # 1. Underlying economic observations
    dataframe_to_sheet(
        wb,
        "Economic Data",
        economic_data
    )

    # 2. Calculated analysis results
    results_table = extract_analysis_table(
        analysis_result
    )

    dataframe_to_sheet(
        wb,
        "Analysis Results",
        results_table
    )

    # 3. Data quality and missingness
    quality_table = create_data_quality_table(
        economic_data
    )

    dataframe_to_sheet(
        wb,
        "Data Quality",
        quality_table
    )

    # 4. Research methodology
    methodology_table = create_methodology_table(
        question,
        request,
        source,
        economic_data
    )

    dataframe_to_sheet(
        wb,
        "Methodology",
        methodology_table
    )

    # 5. Optional AI interpretation
    if ai_briefing:
        ws = wb.create_sheet("AI Briefing")

        ws.append(["Economic Research Briefing"])
        ws.append([safe_excel_value(ai_briefing)])

        format_worksheet(ws, table=False)

        ws.column_dimensions["A"].width = 100
        ws["A2"].alignment = Alignment(
            wrap_text=True,
            vertical="top"
        )
        ws.row_dimensions[2].height = 300

    # Save to memory, then optionally to disk.
    buffer = BytesIO()
    wb.save(buffer)

    excel_bytes = buffer.getvalue()

    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        path.write_bytes(excel_bytes)

    return excel_bytes


# ============================================================
# 6. SELF-TEST
# ============================================================

if __name__ == "__main__":

    print("\nECON AI AGENT — EXCEL TEST")

    # Synthetic test observations.
    # No API call is needed for this test.
    test_data = pd.DataFrame({
        "Country": [
            "Zambia", "Zambia",
            "Kenya", "Kenya",
            "Ghana", "Ghana"
        ],
        "Country_Code": [
            "ZMB", "ZMB",
            "KEN", "KEN",
            "GHA", "GHA"
        ],
        "Year": [
            2022, 2023,
            2022, 2023,
            2022, 2023
        ],
        "Value": [
            5.2, 4.8,
            4.1, 5.7,
            None, 3.4
        ],
        "Indicator": ["gdp_growth"] * 6,
        "Unit": ["%"] * 6,
        "Source": ["World Bank"] * 6
    })

    test_results = pd.DataFrame({
        "Country": ["Kenya", "Zambia", "Ghana"],
        "Mean": [4.9, 5.0, 3.4],
        "Available_Observations": [2, 2, 1]
    })

    output = "econ_ai_test_report.xlsx"

    create_excel_report(
        question=(
            "Compare GDP growth in Zambia, Kenya "
            "and Ghana from 2022 to 2023."
        ),
        request={
            "analysis": "comparison",
            "indicator": "gdp_growth",
            "countries": ["ZMB", "KEN", "GHA"],
            "start_year": 2022,
            "end_year": 2023
        },
        economic_data=test_data,
        analysis_result=test_results,
        source="World Bank",
        ai_briefing=(
            "Illustrative test data only. "
            "These figures are not official observations."
        ),
        output_path=output
    )

    # Verify the generated workbook can be opened.
    check = load_workbook(
        output,
        read_only=True
    )

    print("\nWorkbook created:", output)
    print("Worksheets:", check.sheetnames)

    assert len(check.sheetnames) == 5
    assert check["Economic Data"].max_row == 7
    assert check["Data Quality"].max_row == 4

    check.close()

    print("\nALL EXCEL TESTS COMPLETED")
