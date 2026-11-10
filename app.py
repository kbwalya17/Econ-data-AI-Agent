
"""
Econ AI Agent
Module: app.py

Streamlit interface for AI-powered economic research.

Features:
- Natural-language economic research questions
- Gemini-powered request interpretation
- World Bank and FRED data retrieval
- Python-computed economic statistics
- Interactive charts
- Downloadable Excel research reports
- Transparent data coverage and methodology
"""

import json
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from main import run_econ_agent
from excel import extract_analysis_table


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Econ AI Agent | Economic Intelligence",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1300px;
    }

    h1, h2, h3 {
        letter-spacing: -0.025em;
    }

    .hero {
        padding: 1.8rem 2rem;
        background: linear-gradient(
            120deg,
            #102b49 0%,
            #174a72 100%
        );
        border-radius: 14px;
        color: white;
        margin-bottom: 1.5rem;
    }

    .hero h1 {
        color: white;
        margin: 0;
        font-size: 2.3rem;
    }

    .hero p {
        color: #d9e7f4;
        margin-top: 0.6rem;
        margin-bottom: 0;
        font-size: 1rem;
    }

    .small-note {
        color: #64748b;
        font-size: 0.85rem;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,0.2);
        padding: 1rem;
        border-radius: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def get_result_table(analysis_result):
    """Convert analysis output into a displayable table."""

    if isinstance(analysis_result, pd.DataFrame):
        return analysis_result.copy()

    if isinstance(analysis_result, dict):
        return extract_analysis_table(analysis_result)

    return pd.DataFrame()


def make_chart(data, request):
    """
    Build an interactive chart from verified observations.

    Uses the underlying dataset, not AI-generated numbers.
    """

    if not isinstance(data, pd.DataFrame) or data.empty:
        return None

    required = {"Country", "Value", "Indicator"}

    if not required.issubset(data.columns):
        return None

    chart_data = data.copy()

    chart_data["Value"] = pd.to_numeric(
        chart_data["Value"],
        errors="coerce"
    )

    chart_data = chart_data.dropna(subset=["Value"])

    if chart_data.empty:
        return None

    analysis_type = request["analysis"]

    indicator = (
        chart_data["Indicator"].dropna().iloc[0]
        if chart_data["Indicator"].notna().any()
        else "Economic Indicator"
    )

    unit = (
        chart_data["Unit"].dropna().iloc[0]
        if "Unit" in chart_data.columns
        and chart_data["Unit"].notna().any()
        else ""
    )

    # --------------------------------------------------------
    # RANKINGS: HORIZONTAL BAR CHART
    # --------------------------------------------------------

    if analysis_type == "ranking":

        year = request["year"]

        ranking_data = chart_data[
            chart_data["Year"] == year
        ].copy()

        if ranking_data.empty:
            return None

        ascending = request.get("ascending", False)

        ranking_data = ranking_data.sort_values(
            "Value",
            ascending=ascending
        )

        top_n = request.get("top_n")

        if top_n is not None:
            ranking_data = ranking_data.head(top_n)

        fig = px.bar(
            ranking_data,
            x="Value",
            y="Country",
            orientation="h",
            title=f"{indicator.replace('_', ' ').title()} — {year}",
            labels={
                "Value": unit,
                "Country": "Country"
            },
            color="Value",
            color_continuous_scale="Blues",
        )

        fig.update_layout(
            yaxis={
                "categoryorder": "array",
                "categoryarray": ranking_data[
                    "Country"
                ].tolist()[::-1]
            },
            coloraxis_showscale=False,
        )

        return fig

    # --------------------------------------------------------
    # COUNTRY PROFILE: MULTIPLE INDICATORS
    # --------------------------------------------------------

    if analysis_type == "profile":

        # Different indicators have different units.
        # Never place all profile indicators on one
        # shared numerical axis.

        return None

    # --------------------------------------------------------
    # COMPARISONS AND TRENDS
    # --------------------------------------------------------

    x_axis = (
        "Date"
        if "Date" in chart_data.columns
        and chart_data["Date"].notna().any()
        else "Year"
    )

    if x_axis not in chart_data.columns:
        return None

    chart_data = chart_data.sort_values(x_axis)

    fig = px.line(
        chart_data,
        x=x_axis,
        y="Value",
        color="Country",
        markers=True,
        title=indicator.replace("_", " ").title(),
        labels={
            "Value": unit,
            "Country": "Country",
        },
    )

    fig.update_layout(
        hovermode="x unified",
        legend_title_text="Country",
    )

    return fig


def show_profile_charts(data):
    """
    Display separate charts for country profile indicators,
    preventing incompatible units from sharing an axis.
    """

    if not isinstance(data, pd.DataFrame):
        return

    if "Indicator" not in data.columns:
        return

    st.subheader("Indicator Trends")

    for indicator in data["Indicator"].dropna().unique():

        subset = data[
            data["Indicator"] == indicator
        ].copy()

        subset["Value"] = pd.to_numeric(
            subset["Value"],
            errors="coerce"
        )

        subset = subset.dropna(subset=["Value"])

        if subset.empty:
            continue

        x_axis = (
            "Date"
            if "Date" in subset.columns
            and subset["Date"].notna().any()
            else "Year"
        )

        unit = (
            subset["Unit"].dropna().iloc[0]
            if "Unit" in subset.columns
            and subset["Unit"].notna().any()
            else ""
        )

        fig = px.line(
            subset.sort_values(x_axis),
            x=x_axis,
            y="Value",
            markers=True,
            title=indicator.replace("_", " ").title(),
            labels={"Value": unit},
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )


def show_data_quality(data):
    """Display missingness and observation coverage."""

    if data.empty or "Value" not in data.columns:
        return

    total = len(data)
    available = int(data["Value"].notna().sum())
    missing = total - available

    coverage = (
        100 * available / total
        if total > 0
        else 0
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Observations", f"{total:,}")
    col2.metric("Available", f"{available:,}")
    col3.metric("Missing", f"{missing:,}")
    col4.metric("Coverage", f"{coverage:.1f}%")


# ============================================================
# 4. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🌍 Econ AI Agent")

    st.caption(
        "AI-powered descriptive economic intelligence"
    )

    st.divider()

    st.subheader("Research Capabilities")

    st.markdown(
        """
        **Economic Rankings**

        Rank selected countries using official indicators.

        **Country Comparisons**

        Compare economic performance across economies.

        **Historical Trends**

        Explore changes in economic indicators over time.

        **Country Profiles**

        Examine multiple indicators for one economy.
        """
    )

    st.divider()

    st.subheader("Data Sources")

    st.markdown(
        """
        - World Bank Open Data
        - Federal Reserve Economic Data (FRED)
        """
    )

    st.caption(
        "Gemini interprets questions and explains "
        "Python-computed results."
    )

    st.divider()

    st.subheader("Research Standards")

    st.caption(
        "No forecasting or causal inference. "
        "Missing observations are not silently filled. "
        "Data source and coverage are disclosed."
    )


# ============================================================
# 5. MAIN PAGE
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>Econ AI Agent</h1>
        <p>
            Ask economic questions. Explore official data.
            Generate research-ready analysis.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "### What would you like to investigate?"
)

st.caption(
    "Ask about economic rankings, country comparisons, "
    "historical trends, or country profiles."
)


# ============================================================
# 6. EXAMPLE QUESTIONS
# ============================================================

examples = [
    "Compare GDP growth in Zambia, Kenya, and Ghana between 2000 and 2024.",
    "How has unemployment changed in the United States from 2020 to 2024?",
    "Rank the United States, Canada, and Mexico by GDP growth in 2008.",
    "Show Zambia's economic profile from 2015 to 2024.",
]

selected_example = st.selectbox(
    "Try an example",
    options=["Write my own question"] + examples,
)

if "question_input" not in st.session_state:
    st.session_state.question_input = ""


def apply_example():
    """Populate the question box from the example selector."""

    if selected_example != "Write my own question":
        st.session_state.question_input = selected_example


if selected_example != "Write my own question":

    st.button(
        "Use this example",
        on_click=apply_example,
    )


# ============================================================
# 7. QUESTION INPUT
# ============================================================

with st.form("research_form"):

    question = st.text_area(
        "Economic research question",
        key="question_input",
        placeholder=(
            "e.g. Compare inflation in Zambia and Kenya "
            "between 2000 and 2024."
        ),
        height=115,
    )

    submitted = st.form_submit_button(
        "Analyze Economic Data",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# 8. RUN RESEARCH PIPELINE
# ============================================================

if submitted:

    if not question.strip():

        st.warning(
            "Please enter an economic research question."
        )

    else:

        with st.spinner(
            "Interpreting your question, retrieving "
            "official data, and preparing the analysis..."
        ):

            try:

                result = run_econ_agent(
                    question=question,
                    generate_briefing=True,
                    generate_excel=True,
                )

                st.session_state.research_result = result

            except Exception as error:

                st.session_state.research_result = None

                st.error(
                    "The analysis could not be completed."
                )

                st.info(str(error))


# ============================================================
# 9. DISPLAY RESEARCH RESULTS
# ============================================================

result = st.session_state.get("research_result")

if result is not None:

    st.divider()

    st.header("Economic Research Results")

    st.markdown(
        f"**Research question:** {result['question']}"
    )

    request = result["request"]
    data = result["economic_data"]
    analysis_result = result["analysis_result"]

    # --------------------------------------------------------
    # SOURCE INFORMATION
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Data Source",
        result["source"]
    )

    col2.metric(
        "Analysis",
        request["analysis"].title()
    )

    col3.metric(
        "Countries",
        data["Country_Code"].nunique()
    )

    # --------------------------------------------------------
    # AI BRIEFING
    # --------------------------------------------------------

    st.subheader("Economic Briefing")

    if result["briefing"]:
        st.markdown(result["briefing"])
    else:
        st.info("No AI briefing was generated.")

    # --------------------------------------------------------
    # ANALYSIS RESULTS
    # --------------------------------------------------------

    st.subheader("Statistical Results")

    table = get_result_table(analysis_result)

    if not table.empty:

        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No summary table is available "
            "for this analysis."
        )

    # --------------------------------------------------------
    # CHARTS
    # --------------------------------------------------------

    if request["analysis"] == "profile":

        show_profile_charts(data)

    else:

        chart = make_chart(data, request)

        if chart is not None:

            st.subheader("Economic Data Visualization")

            st.plotly_chart(
                chart,
                use_container_width=True,
            )

    # --------------------------------------------------------
    # DATA QUALITY
    # --------------------------------------------------------

    st.subheader("Data Coverage")

    show_data_quality(data)

    # --------------------------------------------------------
    # METHODOLOGY AND RAW DATA
    # --------------------------------------------------------

    with st.expander(
        "View Underlying Economic Data"
    ):

        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True,
        )

    with st.expander(
        "Methodology and Research Notes"
    ):

        st.markdown(
            f"**Source:** {result['source']}"
        )

        st.markdown(
            f"**Analysis:** {request['analysis']}"
        )

        st.markdown(
            "**Validated request:**"
        )

        st.json(request)

        if result["notes"]:

            for note in result["notes"]:
                st.markdown(f"- {note}")

        st.caption(
            "All numerical statistics are computed "
            "in Python. Gemini provides a narrative "
            "interpretation of those results."
        )

    # --------------------------------------------------------
    # EXCEL DOWNLOAD
    # --------------------------------------------------------

    st.subheader("Download Research Report")

    if result["excel_bytes"]:

        st.download_button(
            label="Download Excel Research Report",
            data=result["excel_bytes"],
            file_name="econ_ai_research_report.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

        st.caption(
            "Includes economic observations, "
            "statistical results, data quality, "
            "methodology, and the AI briefing."
        )


# ============================================================
# 10. FOOTER
# ============================================================

st.divider()

st.caption(
    "Econ AI Agent | Economic data: World Bank & FRED | "
    "AI interpretation: Google Gemini | "
    "Descriptive research only"
)