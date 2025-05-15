from pathlib import Path
import base64
import pandas as pd
import altair as alt
import requests
import io
import streamlit as st
import urllib.parse

def calculate_scores(df):
    result = {
        "CSI Score (%)": None,
        "CLI Score (%)": None,
        "CES Score (%)": None,
        "NPS Score (%)": None,
        "Score 0-6 (Detractor) (%)": None,
        "Score 7-8 (Passive) (%)": None,
        "Score 9-10 (Promoter) (%)": None,
        }
    
    if "CSI" in df.columns:
        df_csi = df["CSI"].dropna()
        if not df_csi.empty:
            csi_counts = df_csi.value_counts()
            total_rows = len(df_csi)
            csi_proportion = csi_counts / total_rows
            sum_5_4 = csi_proportion.get(5, 0) + csi_proportion.get(4, 0)
            result["CSI Score (%)"] = round(sum_5_4 * 100, 1)

    if "CLI" in df.columns:
        df_cli = df["CLI"].dropna()
        if not df_cli.empty:
            avg_cli = df_cli.mean()
            result["CLI Score (%)"] = round((avg_cli - 1) / 9 * 100, 1)

    if "CES" in df.columns:
        df_ces = df["CES"].dropna()
        if not df_ces.empty:
            ces_counts = df_ces.value_counts()
            total_rows = len(df_ces)
            ces_proportion = ces_counts / total_rows
            sum_5_4 = ces_proportion.get(5, 0) + ces_proportion.get(4, 0)
            result["CES Score (%)"] = round(sum_5_4 * 100, 1)

    if "NPS" in df.columns:
        df_nps = df["NPS"].dropna()
        if not df_nps.empty:
            nps_counts = df_nps.value_counts()
            total_rows = len(df_nps)
            nps_proportion = nps_counts / total_rows

            sum_0_6 = sum(nps_proportion.get(i, 0) for i in range(0, 7)) * 100  # Detractor
            sum_7_8 = sum(nps_proportion.get(i, 0) for i in range(7, 9)) * 100  # Passive
            sum_9_10 = sum(nps_proportion.get(i, 0) for i in range(9, 11)) * 100  # Promoter

            result["Score 0-6 (Detractor) (%)"] = round(sum_0_6, 1)
            result["Score 7-8 (Passive) (%)"] = round(sum_7_8, 1)
            result["Score 9-10 (Promoter) (%)"] = round(sum_9_10, 1)
            result["NPS Score (%)"] = round(sum_9_10 - sum_0_6, 1)

    return result

def get_value_counts_percentage(df, column_name):
    counts = df[column_name].value_counts(dropna=False)
    percentages = counts / counts.sum() * 100

    result2 = pd.DataFrame({
        'Jumlah': counts,
        'Persentase (%)': percentages.round(2)
    })
    return result2  
        
def select_data(df, tahun, event, unit, n_sebelumnya=4):
    tahun = int(tahun)
    event = str(event)
    unit = str(unit)

    match_idx = df[
        (df["Tahun"] == tahun) &
        (df["Event"] == event) &
        (df["Unit"] == unit)
    ].index

    if not match_idx.empty:
        idx = match_idx[0]
        start_idx = max(0, idx - n_sebelumnya)
        return df.iloc[start_idx:idx + 1].copy()
    else:
        return pd.DataFrame()
def make_metric_card(title, value, delta=None, icon="📊", color="#2a9d8f", big=False):
    delta_color = "gray"
    if delta is not None:
        delta_color = "green" if delta > 0 else "red" if delta < 0 else "gray"
        delta = f"{delta:+.2f}"
    else:
        delta = "N/A"

    font_size = "40px" if big else "28px"

    html = f"""
    <div style="
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    ">
        <div style="font-size: 26px;">{icon}</div>
        <div style="font-weight: bold; font-size: 20px; margin-top: 5px;">{title}</div>
        <div style="font-size: {font_size}; color: {color}; margin: 5px 0;">{value}</div>
        {f'<div style="font-size: 14px; color: {delta_color};">Δ {delta}</div>' if not big else ''}
    </div>
    """
    return html

def altair_barh_percent(df, column):
    value_counts = df[column].value_counts(dropna=False)
    percentages = (value_counts / value_counts.sum() * 100).round(2)

    # Siapkan dataframe untuk Altair
    plot_df = percentages.reset_index()
    plot_df.columns = ['Kategori', 'Persentase (%)']
    plot_df['Label'] = plot_df['Persentase (%)'].astype(str) + '%'

    chart = alt.Chart(plot_df).mark_bar().encode(
        x=alt.X('Persentase (%):Q', axis=None),
        y=alt.Y('Kategori:N', sort='-x', axis=alt.Axis(title=None, labelLimit=200, labelAlign='right')),
        color=alt.value('#2B7CD1'),
        tooltip=['Kategori:N', 'Persentase (%):Q']
    ).properties(
        width=250,
        height=400
    )

    # Tambahkan label di bar
    text = alt.Chart(plot_df).mark_text(
        align="left",
        baseline="middle",
        dx=3,
        color="grey"
    ).encode(
        x='Persentase (%):Q',
        y=alt.Y('Kategori:N', sort='-x'),
        text='Label:N'
    )

    return chart + text

def sentiment_card(color, label, count, percentage):
    return f"""
    <div style='
        background-color: #ffffff;
        border-left: 6px solid {color};
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05);
        text-align: center;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    '>
        <div style='margin-bottom: 4px; font-weight: 600; color: {color}; font-size: 18px;'>{label}</div>
        <div style='font-size: 28px; font-weight: bold; color: #2d3436;'>{count}</div>
        <div style='font-size: 14px; color: gray;'>{percentage:.1%}</div>
    </div>
    """

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwnXc7ooKicgCnTHzzU7Xv4AHNr-CUTGWDvhlKqN6suij1tbsyl6brkqT0jILxRJjMyeQ/exec"

@st.cache_data
def fetch_from_gas(file_type, year=None, event=None, unit=None):
    params = {"file": file_type}
    if year: params["year"] = year
    if event: params["event"] = event
    if unit: params["unit"] = unit

    url = SCRIPT_URL + "?" + urllib.parse.urlencode(params)
    response = requests.get(url)
    if response.ok and "File not found" not in response.text:
        return base64.b64decode(response.text)
    return None

@st.cache_data
def load_archive():
    bytes_data = fetch_from_gas("archive")
    if bytes_data:
        excel_data = pd.ExcelFile(io.BytesIO(bytes_data))
        df1 = pd.read_excel(excel_data, sheet_name="Sheet1")
        df2 = pd.read_excel(excel_data, sheet_name="Sheet2")
        return df1, df2
    return None, None

@st.cache_data
def load_data(year, event, unit):
    bytes_data = fetch_from_gas("data", year=year, event=event)
    if bytes_data:
        df = pd.read_excel(io.BytesIO(bytes_data), sheet_name=unit)
        return df
    return None

def img_to_base64(path):
                img_bytes = Path(path).read_bytes()
                encoded = base64.b64encode(img_bytes).decode()
                return f"data:image/png;base64,{encoded}"
