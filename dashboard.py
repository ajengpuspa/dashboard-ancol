import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
from IPython.display import display
import altair as alt
import pandas as pd
from pathlib import Path
import base64
from utils import calculate_scores, get_value_counts_percentage, select_data, make_metric_card, altair_barh_percent, sentiment_card, load_archive, load_data, img_to_base64
import warnings
warnings.filterwarnings('ignore')

#header
st.set_page_config(page_title="CSI CLI NPS", page_icon=":bar_chart:", layout="wide")

st.markdown(
    """
    <style>
        body {
            background-color: white;
        }
        .stImage {
            display: block;
            margin-left: auto;
            margin-right: auto;
        }
    </style>
    """, unsafe_allow_html=True
)

#dropdown
years = ['Please select here', '2023', '2024', '2025']
events = ['Please select here', 'Lebaran', 'Libur Sekolah', "Low Season", 'Nataru']
units = ['Please select here', 'Ancol', 'Dufan', 'Atlantis', 'Sea World', 'Samudra', 'Jakarta Bird Land']

for key, default in [("selected_unit", "Please select here"),
                     ("selected_year", "Please select here"),
                     ("selected_event", "Please select here")]:
    if key not in st.session_state:
        st.session_state[key] = default

#title and logo
unit_logo_map = {
    "Ancol": "ancol.png",
    "Dufan": "dufan.png",
    "Atlantis": "atlantis.png",
    "Sea World": "seaworld.png",
    "Samudra": "samudra.png",
    "Jakarta Bird Land": "jbl.png"
}

logo_filename = unit_logo_map.get(st.session_state.selected_unit, "ancol.png")
title_suffix = f" {st.session_state.selected_unit}" if st.session_state.selected_unit != "Please select here" else ""

img_path = Path(__file__).parent / "img" / logo_filename
with open(img_path, "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

st.markdown(
    f"""
    <div style="text-align: center;">
        <img src="data:image/png;base64,{img_base64}" width="250"/>
        <h1 style="margin-top: 10px;">Dashboard CSI, CLI, & NPS{title_suffix}</h1>
    </div>
    """,
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)
with col1:
    st.selectbox('Choose Year', years, index=years.index(st.session_state.selected_year), key="selected_year")
with col2:
    st.selectbox('Choose Event', events, index=events.index(st.session_state.selected_event), key="selected_event")
with col3:
    st.selectbox('Choose Unit', units, index=units.index(st.session_state.selected_unit), key="selected_unit")

if (
    st.session_state.selected_year != 'Please select here' and
    st.session_state.selected_event != 'Please select here' and
    st.session_state.selected_unit != 'Please select here'
):
    with st.spinner('Updating Report...'):
        df = load_data(
        st.session_state.selected_year,
        st.session_state.selected_event,
        st.session_state.selected_unit
    )
        if df is not None:
            result = calculate_scores(df)
            selected_year = int(st.session_state.selected_year)
            previous_year = selected_year - 1
            selected_event = st.session_state.selected_event
            selected_unit = st.session_state.selected_unit

            df1, df2 = load_archive()
            previous_row = df1[
                (df1['Tahun'] == previous_year) &
                (df1['Event'] == selected_event) &
                (df1['Unit'] == selected_unit)
            ]

            def safe_delta(current, previous):
                return current - previous if current is not None and previous is not None else None

            if not previous_row.empty:
                delta_csi = safe_delta(result.get("CSI Score (%)"), previous_row.iloc[0].get("CSI"))
                delta_cli = safe_delta(result.get("CLI Score (%)"), previous_row.iloc[0].get("CLI"))
                delta_nps = safe_delta(result.get("NPS Score (%)"), previous_row.iloc[0].get("NPS"))
            else:
                delta_csi = delta_cli = delta_nps = None

            def format_score(val):
                return f"{val:.2f}" if val is not None else "-"

            csi_display = format_score(result.get("CSI Score (%)"))
            cli_display = format_score(result.get("CLI Score (%)"))
            nps_display = format_score(result.get("NPS Score (%)"))

            col4, col5, col6, col7 = st.columns((1, 1, 1, 1))
            with col4:
                total_resp = int(df["CSI"].count())
                st.markdown(make_metric_card("Total Respondent", total_resp, icon="👥", color="#4e5b6e", big=True), unsafe_allow_html=True)

            with col5:
                st.markdown(make_metric_card("CSI Score", csi_display, delta=delta_csi, icon="🤩", color="#4e5b6e"), unsafe_allow_html=True)

            with col6:
                st.markdown(make_metric_card("CLI Score", cli_display, delta=delta_cli, icon="⭐️", color="#4e5b6e"), unsafe_allow_html=True)

            with col7:
                st.markdown(make_metric_card("NPS Score", nps_display, delta=delta_nps, icon="🗣️", color="#4e5b6e"), unsafe_allow_html=True)

            st.write("")
            target_columns = {
                'Domisili': "📍 Domisili",
                'Usia': "👤 Usia",
                'Companions': "🧑‍🧑‍🧒 Companions"
            }

            available_columns = [(col, label) for col, label in target_columns.items() if col in df.columns]
            if available_columns:
                cols = st.columns(len(available_columns), gap="medium")

                for i, (col_name, label) in enumerate(available_columns):
                    with cols[i]:
                        st.markdown(f"<h3 style='text-align: center;'>{label}</h3>", unsafe_allow_html=True)
                        chart = altair_barh_percent(df, col_name)
                        st.altair_chart(chart, use_container_width=True)

            g4, g5 = st.columns((1,1), gap="medium")
            with g4:
                df2_filtered = select_data(df1, selected_year, selected_event, selected_unit)

                for col in ["CSI", "CLI", "NPS"]:
                    df2_filtered[col] = pd.to_numeric(df2_filtered[col], errors='coerce')

                df2_filtered["Event_Year"] = df2_filtered["Event"].astype(str) + " " + df2_filtered["Tahun"].astype(str)

                df_long = pd.melt(df2_filtered,
                                id_vars=["Event_Year", "Tahun", "Event"],
                                value_vars=["CSI", "CLI", "NPS"],
                                var_name="Metric",
                                value_name="Score")

                color_scale = alt.Scale(
                    domain=["CSI", "CLI", "NPS"],
                    range=["#1f77b4", "#ff7f0e", "#98c379"]
                )

                # base chart
                base = alt.Chart(df_long).encode(
                    x=alt.X("Event_Year:N", title="", sort=df2_filtered["Event_Year"].tolist(),
                            axis=alt.Axis(labelAngle=0))
                )

                # line CSI & CLI
                line = base.transform_filter(
                    alt.FieldOneOfPredicate(field="Metric", oneOf=["CSI", "CLI"])
                ).mark_line(point=True).encode(
                    y=alt.Y("Score:Q", title="Score (%)"),
                    color=alt.Color("Metric:N", scale=color_scale, legend=alt.Legend(title="Metric", orient="bottom")),
                    tooltip=["Tahun", "Event", "Metric", "Score"]
                )

                # bar NPS
                bar = base.transform_filter(
                    alt.datum.Metric == "NPS"
                ).mark_bar(size=40).encode(
                    y="Score:Q",
                    color=alt.Color("Metric:N", scale=color_scale, legend=None),
                    tooltip=["Tahun", "Event", "Metric", "Score"]
                )

                # text
                text_csi = base.transform_filter(
                    alt.datum.Metric == "CSI"
                ).mark_text(align='center', dy=-15, color="#1f77b4").encode(
                    y="Score:Q",
                    text="Score:Q"
                )

                text_cli = base.transform_filter(
                    alt.datum.Metric == "CLI"
                ).mark_text(align='center', dy=15, color="#ff7f0e").encode(
                    y="Score:Q",
                    text="Score:Q"
                )

                text_nps = base.transform_filter(
                    alt.datum.Metric == "NPS"
                ).mark_text(align='center', dy=-5, color="black").encode(
                    y="Score:Q",
                    text="Score:Q"
                )

                # combine
                chart = alt.layer(bar, line, text_csi, text_cli, text_nps).properties(
                    title=alt.TitleParams(
                        text=f"CSI/CLI/NPS - {selected_unit}",
                        fontSize=20,         
                        anchor='middle'      
                    ),
                    width=550,
                    height=350
                )

                st.altair_chart(chart, use_container_width=True)
                img_base64 = img_to_base64(Path(__file__).parent / "img" / "combo.png")
                st.markdown(
                    f"<div style='text-align:center;'><img src='{img_base64}' width='200'></div>",
                    unsafe_allow_html=True
                )

            with g5:
                df_filtered = select_data(df2, selected_year, selected_event, selected_unit)
                
                for col in ["Detractor", "Passive", "Promoter", "NPS"]:
                    df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

                df_filtered["Event_Year"] = df_filtered["Event"].astype(str) + " " + df_filtered["Tahun"].astype(str)
                df_filtered = df_filtered.sort_values(by=["Tahun", "Event"], ascending=[False, False]).reset_index(drop=True)
                df_filtered["Index"] = df_filtered.index

                nps_long = df_filtered.melt(
                    id_vars=["Event_Year", "Index"],
                    value_vars=["Detractor", "Passive", "Promoter"],
                    var_name="Kategori",
                    value_name="Persentase"
                )

                color_scale = alt.Scale(
                    domain=["Detractor", "Passive", "Promoter"],
                    range=["#EA4335", "#FFD966", "#73B855"]
                )

                bar = alt.Chart(nps_long).mark_bar().encode(
                    y=alt.Y("Event_Year:N", title="", axis=alt.Axis(labelAngle=0, grid=False),
                            sort=alt.EncodingSortField(field="Index", order="descending")),
                    x=alt.X("Persentase:Q", stack="zero", title=None, scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color("Kategori:N", scale=color_scale, legend=None),
                    tooltip=["Event_Year", "Kategori", "Persentase"]
                )

                # Label dalam bar (< 5)
                bar_text_outside = alt.Chart(nps_long[nps_long["Persentase"] < 5]).mark_text(
                    align='center',
                    baseline='middle',
                    color='#393737',
                    fontSize=11
                ).encode(
                    y=alt.Y("Event_Year:N", sort=alt.EncodingSortField(field="Index", order="descending")),
                    x=alt.X("Persentase:Q", stack="center"),
                    text=alt.Text("Persentase:Q", format=".1f")
                )

                # Label di luar bar (>= 5)
                bar_text_inside = alt.Chart(nps_long[nps_long["Persentase"] >= 5]).mark_text(
                    align='right',
                    baseline='middle',
                    dx=-5,
                    color='#393737',
                    fontSize=11
                ).encode(
                    y=alt.Y("Event_Year:N", sort=alt.EncodingSortField(field="Index", order="descending")),
                    x=alt.X("Persentase:Q", stack="zero"),
                    text=alt.Text("Persentase:Q", format=".1f")
                )

                final_chart = (bar + bar_text_inside + bar_text_outside).properties(
                    width=550,
                    height=350,
                    title=alt.TitleParams(
                        text=f"Distribusi NPS - {selected_unit}",
                        fontSize=20,
                        anchor='middle'
                    )
                ).configure_axis(
                    labelFontSize=12,
                    titleFontSize=14,
                    grid=False
                )

                st.altair_chart(final_chart, use_container_width=True)
                img_base64 = img_to_base64(Path(__file__).parent / "img" / "nps.png")
                st.markdown(
                    f"<div style='text-align:center;'><img src='{img_base64}' width='200'></div>",
                    unsafe_allow_html=True
                )

            st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>📊 Sentimen</h3>", unsafe_allow_html=True)
            col8, col9, col10 = st.columns(3, gap="large")
            sentiment_counts = df['Sentiment'].value_counts()
            total = len(df['Sentiment'].dropna())
            pos = sentiment_counts.get('Positive', 0)
            neu = sentiment_counts.get('Neutral', 0)
            neg = sentiment_counts.get('Negative', 0)

            with col8:
                st.markdown(sentiment_card("#00B894", "Positive", pos, pos/total), unsafe_allow_html=True)
            with col9:
                st.markdown(sentiment_card("#0984E3", "Neutral", neu, neu/total), unsafe_allow_html=True)
            with col10:
                st.markdown(sentiment_card("#D63031", "Negative", neg, neg/total), unsafe_allow_html=True)

            st.markdown("<h4 style='margin-top: 20px;'>📝 Detail Alasan</h4>", unsafe_allow_html=True)
            if 'Alasan' in df.columns:
                df['Alasan'] = df['Alasan'].astype(str) 
                st.dataframe(df[['Alasan']], use_container_width=True)
            else:
                st.warning("Kolom 'Alasan' tidak ditemukan dalam data.")
        else:
            st.error('Please select valid options for Year, Event, and Unit.')
