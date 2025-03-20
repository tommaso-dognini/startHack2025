import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np
import geopandas as gpd
import json
import pydeck as pdk
import folium
from streamlit_folium import st_folium
import openai
openai.api_key = st.secrets["openai"]["api_key"]

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="Burkina Faso Rainfall", layout="wide", initial_sidebar_state="expanded")

# --- MENU LATERALE ---
st.sidebar.title("📊 Menu di Navigazione")
use_same_slider = st.sidebar.checkbox("Usa lo stesso slider per tutte le analisi", value=True)
page = st.sidebar.radio("Seleziona un'analisi:", ["Analisi delle Piogge", "Trend Annuali", "Analisi Stagionale", "Distribuzione Geografica", "Dati Grezzi", "Uso del Territorio", "OpenStreetMap", "Chat Bot"])

# --- CARICAMENTO E PREPARAZIONE DEI DATI ---
@st.cache_data
def load_data():
    df = pd.read_csv("bfa-rainfall-adm2-full.csv", parse_dates=["date"], low_memory=False)
    df = df.iloc[1:]  # Rimuove la prima riga se non serve
    df["date"] = pd.to_datetime(df["date"], errors="coerce")  # Converte la colonna in datetime
    df["rfh"] = pd.to_numeric(df["rfh"], errors="coerce")  # Converti a numerico
    return df

df = load_data()

# --- GESTIONE DELLE PAGES ---
if use_same_slider:
    min_date = df["date"].min()
    max_date = df["date"].max()
    start_date, end_date = st.sidebar.slider(
        "Seleziona il periodo di analisi:",
        min_value=min_date.date(),
        max_value=max_date.date(),
        value=(pd.to_datetime("2010-01-01").date(), pd.to_datetime("2020-12-31").date()),
        format="YYYY-MM-DD"
    )

# --- ANALISI DELLE PIOGGE ---
if page == "Analisi delle Piogge":
    st.title("📊 Rainfall Analysis in Burkina Faso")

    if not use_same_slider:
        min_date = df["date"].min()
        max_date = df["date"].max()
        start_date, end_date = st.slider(
            "Seleziona il periodo di analisi:",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(pd.to_datetime("2021-06-01").date(), pd.to_datetime("2022-06-01").date()),
            format="YYYY-MM-DD"
        )

    df_filtered = df[
        (df["date"] >= pd.to_datetime(start_date, format="%Y-%m-%d")) &
        (df["date"] <= pd.to_datetime(end_date, format="%Y-%m-%d"))
    ]

    # Aggregazione dei dati (somma della pioggia giornaliera)
    df_daily_sum = df_filtered.groupby("date")["rfh"].sum().reset_index()
    df_daily_sum = df_daily_sum.sort_values(by="date").reset_index(drop=True)

    # --- GRAFICO ---
    fig, ax = plt.subplots(figsize=(12, 6))

    # Linea principale del grafico
    ax.plot(df_daily_sum["date"], df_daily_sum["rfh"], marker='o', linestyle='-', color='b', linewidth=2, markersize=6, label='Rainfall')

    # Evidenzia Min e Max se ci sono dati
    if not df_daily_sum.empty:
        min_value = df_daily_sum["rfh"].min()
        max_value = df_daily_sum["rfh"].max()
        min_date = df_daily_sum.loc[df_daily_sum["rfh"].idxmin(), "date"]
        max_date = df_daily_sum.loc[df_daily_sum["rfh"].idxmax(), "date"]

        ax.scatter(min_date, min_value, color='red', s=100, label="Min Rainfall")
        ax.scatter(max_date, max_value, color='green', s=100, label="Max Rainfall")

        ax.text(min_date, min_value, f"Min: {min_value:.2f} mm", fontsize=10, verticalalignment='bottom', horizontalalignment='right', color='red', fontweight='bold')
        ax.text(max_date, max_value, f"Max: {max_value:.2f} mm", fontsize=10, verticalalignment='top', horizontalalignment='left', color='green', fontweight='bold')

    # --- GESTIONE DINAMICA DELLE ETICHETTE DELL'ASSE X ---
    date_range_days = (end_date - start_date).days  # Numero di giorni selezionati

    if date_range_days > 14600:  # Più di 40 anni → Ogni 10 anni
        locator = mdates.YearLocator(10)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 7300:  # Più di 20 anni → Ogni 5 anni
        locator = mdates.YearLocator(5)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 3650:  # Più di 10 anni → Ogni 2 anni
        locator = mdates.YearLocator(2)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 1825:  # Più di 5 anni → Ogni 1 anno
        locator = mdates.YearLocator(1)
        formatter = mdates.DateFormatter("%Y")
    elif date_range_days > 730:  # Più di 2 anni → Ogni 6 mesi
        locator = mdates.MonthLocator(interval=6)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 365:  # Più di 1 anno → Ogni 3 mesi
        locator = mdates.MonthLocator(interval=3)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 180:  # Più di 6 mesi → Ogni mese
        locator = mdates.MonthLocator(interval=1)
        formatter = mdates.DateFormatter("%Y-%m")
    elif date_range_days > 90:  # Più di 3 mesi → Ogni 15 giorni
        locator = mdates.DayLocator(interval=15)
        formatter = mdates.DateFormatter("%Y-%m-%d")
    elif date_range_days > 30:  # Più di 1 mese → Ogni settimana
        locator = mdates.DayLocator(interval=7)
        formatter = mdates.DateFormatter("%Y-%m-%d")
    else:  # Meno di un mese → Mostra ogni 3 giorni
        locator = mdates.DayLocator(interval=3)
        formatter = mdates.DateFormatter("%Y-%m-%d")

    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    plt.xticks(rotation=45)

    # Griglia e formattazione
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_title(f"Daily Rainfall from {start_date} to {end_date}", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Rainfall (mm)", fontsize=12)
    ax.legend()

    # --- VISUALIZZAZIONE STREAMLIT ---
    st.pyplot(fig)


    st.title("📈 Trend Annuali delle Piogge")

    if not use_same_slider:
        min_date = df["date"].min()
        max_date = df["date"].max()
        start_date, end_date = st.slider(
            "Seleziona il periodo di analisi:",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(pd.to_datetime("2010-01-01").date(), pd.to_datetime("2020-12-31").date()),
            format="YYYY-MM-DD"
        )

    df_filtered = df[
        (df["date"] >= pd.to_datetime(start_date, format="%Y-%m-%d")) &
        (df["date"] <= pd.to_datetime(end_date, format="%Y-%m-%d"))
    ]

    df_filtered["year"] = df_filtered["date"].dt.year
    df_annual_filtered = df_filtered.groupby("year")["rfh"].sum().reset_index()

    # Regressione lineare
    if not df_annual_filtered.empty:
        coeffs = np.polyfit(df_annual_filtered["year"], df_annual_filtered["rfh"], 1)
        trend_line = np.poly1d(coeffs)
        df_annual_filtered["trend"] = trend_line(df_annual_filtered["year"])

        # Trova il valore minimo e massimo delle precipitazioni annuali
        min_year = df_annual_filtered.loc[df_annual_filtered["rfh"].idxmin(), "year"]
        min_value = df_annual_filtered["rfh"].min()
        max_year = df_annual_filtered.loc[df_annual_filtered["rfh"].idxmax(), "year"]
        max_value = df_annual_filtered["rfh"].max()

        # Creazione dell'istogramma
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(df_annual_filtered["year"], df_annual_filtered["rfh"], color="b", alpha=0.7, label="Pioggia Totale")
        ax.plot(df_annual_filtered["year"], df_annual_filtered["trend"], color="r", linestyle="--", linewidth=2, label="Trend Lineare")

        # Punti minimo e massimo
        ax.scatter(min_year, min_value, color="green", s=100, label="Minimo")
        ax.scatter(max_year, max_value, color="red", s=100, label="Massimo")
        ax.text(min_year, min_value, f"Min: {min_value:.2f} mm", fontsize=10, verticalalignment="bottom", horizontalalignment="right", color="green", fontweight="bold")
        ax.text(max_year, max_value, f"Max: {max_value:.2f} mm", fontsize=10, verticalalignment="top", horizontalalignment="left", color="red", fontweight="bold")

        ax.set_xlabel("Anno", fontsize=12)
        ax.set_ylabel("Pioggia Totale (mm)", fontsize=12)
        ax.set_title(f"Trend Annuale delle Piogge ({start_date} - {end_date})", fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.7)

        # Mostra il grafico in Streamlit
        st.pyplot(fig)

# --- ANALISI STAGIONALE ---
if page == "Analisi Stagionale":
    st.title("🌦️ Analisi Stagionale delle Piogge")

    if not use_same_slider:
        min_date = df["date"].min()
        max_date = df["date"].max()
        start_date, end_date = st.slider(
            "Seleziona il periodo di analisi:",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(pd.to_datetime("2010-01-01").date(), pd.to_datetime("2020-12-31").date()),
            format="YYYY-MM-DD"
        )

    df_filtered = df[
        (df["date"] >= pd.to_datetime(start_date, format="%Y-%m-%d")) &
        (df["date"] <= pd.to_datetime(end_date, format="%Y-%m-%d"))
    ]

    df_filtered["year"] = df_filtered["date"].dt.year
    df_filtered["month"] = df_filtered["date"].dt.month
    df_seasonal = df_filtered.groupby(["year", "month"])["rfh"].sum().reset_index()

    # Aggiungi una checkbox per filtrare le annate
    filter_years = st.checkbox("Seleziona anni specifici", value=False)

    # Se la checkbox è attivata, mostra una multiselezione per scegliere gli anni
    selected_years = df_seasonal["year"].unique()
    if filter_years:
        selected_years = st.multiselect("Seleziona gli anni da visualizzare:", df_seasonal["year"].unique(), default=df_seasonal["year"].unique())

    # Filtra il dataframe df_seasonal in base agli anni selezionati
    df_seasonal_filtered = df_seasonal[df_seasonal["year"].isin(selected_years)]

    # Creare il grafico stagionale
    fig, ax = plt.subplots(figsize=(12, 6))

    # Raggruppa per mese e calcola la media delle precipitazioni
    df_monthly_avg = df_seasonal_filtered.groupby("month")["rfh"].mean().reset_index()

    ax.bar(df_monthly_avg["month"], df_monthly_avg["rfh"], color="b", alpha=0.7, label="Media Pioggia Mensile")

    ax.set_xlabel("Mese", fontsize=12)
    ax.set_ylabel("Pioggia Media (mm)", fontsize=12)
    ax.set_title(f"Pioggia Media Mensile ({start_date} - {end_date})", fontsize=14, fontweight="bold")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"])
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    # Mostra il grafico in Streamlit
    st.pyplot(fig)

    # Verificare la regolarità del trend stagionale
    fig, ax = plt.subplots(figsize=(12, 6))

    for year in df_seasonal_filtered["year"].unique():
        df_yearly = df_seasonal_filtered[df_seasonal_filtered["year"] == year]
        ax.plot(df_yearly["month"], df_yearly["rfh"], marker='o', linestyle='-', alpha=0.6, label=str(year))

    ax.set_xlabel("Mese", fontsize=12)
    ax.set_ylabel("Pioggia Totale (mm)", fontsize=12)
    ax.set_title(f"Trend Stagionale Anno per Anno ({start_date} - {end_date})", fontsize=14, fontweight="bold")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"])
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    # Mostra il grafico in Streamlit
    st.pyplot(fig)

if page == "Trend Annuali":
    st.title("🗺️ trend annuali")


elif page == "Distribuzione Geografica":
    st.title("🗺️ Distribuzione Geografica")
    st.write("Prossimamente: Visualizzazione della pioggia per regione.")

elif page == "Dati Grezzi":
    st.title("📜 Dati Grezzi")
    st.write("Anteprima del dataset caricato:")
    st.dataframe(df.head(20))

if page == "Uso del Territorio":
    st.title("🌍 Uso del Territorio in Burkina Faso")

    # Caricare il dataset
    file_path = "climate-change_bfa.csv"
    df = pd.read_csv(file_path)

    # Filtrare i dati del Burkina Faso
    df_burkina = df[df["Country Name"] == "Burkina Faso"]

    # Filtrare i tre indicatori principali
    agriculture = df_burkina[df_burkina["Indicator Name"] == "Agricultural land (% of land area)"]
    forest = df_burkina[df_burkina["Indicator Name"] == "Forest area (% of land area)"]
    arable = df_burkina[df_burkina["Indicator Name"] == "Arable land (% of land area)"]

    # Unire i tre dataset in base all'anno
    df_selected = pd.merge(agriculture[['Year', 'Value']], forest[['Year', 'Value']], on="Year", suffixes=('_agriculture', '_forest'))
    df_selected = pd.merge(df_selected, arable[['Year', 'Value']], on="Year")
    df_selected.rename(columns={"Value": "Value_arable"}, inplace=True)

    # Convertire i valori in numeri
    df_selected['Value_agriculture'] = pd.to_numeric(df_selected['Value_agriculture'], errors='coerce')
    df_selected['Value_forest'] = pd.to_numeric(df_selected['Value_forest'], errors='coerce')
    df_selected['Value_arable'] = pd.to_numeric(df_selected['Value_arable'], errors='coerce')

    # Convertire 'Year' in formato datetime
    df_selected['Year'] = pd.to_datetime(df_selected['Year'], format='%Y')

    # Ordinare i dati in ordine crescente di anno
    df_selected = df_selected.sort_values(by="Year", ascending=True)

    # Creare il grafico
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(df_selected['Year'], df_selected['Value_agriculture'], label="Superficie Agricola (%)", color="green", linewidth=2)
    ax.plot(df_selected['Year'], df_selected['Value_forest'], label="Superficie Forestale (%)", color="brown", linewidth=2, linestyle="dashed")
    ax.plot(df_selected['Year'], df_selected['Value_arable'], label="Terra Coltivabile (%)", color="blue", linewidth=2, linestyle="dotted")

    ax.set_xlabel("Anno")
    ax.set_ylabel("Percentuale della superficie totale")
    ax.set_title("Superficie Agricola, Forestale e Coltivabile in Burkina Faso")
    ax.legend()
    ax.grid(True)

    # Disabilitare la notazione scientifica
    ax.ticklabel_format(style='plain', axis='y')

    # Mostrare il grafico in Streamlit
    st.pyplot(fig)

    # Calcolare la matrice di correlazione e mostrarla in Streamlit
    correlation = df_selected[['Value_agriculture', 'Value_forest', 'Value_arable']].corr()
    st.write("### Matrice di correlazione tra Superficie Agricola, Forestale e Coltivabile:")
    st.dataframe(correlation)

elif page == "OpenStreetMap":
    st.title("Mappa stradale del Sahel")

    try:
        with open("geoBoundaries-BFA-ADM1.geojson") as f:
            geojson_data = json.load(f)
    except FileNotFoundError:
        st.error("File geoBoundaries-BFA-ADM1.geojson non trovato nella directory principale")
        st.stop()



    # Carica il file geojson delle strade del Burkina Faso
    roads_gdf = gpd.read_file("hotosm_bfa_roads_lines_geojson.geojson")

    # Se il CRS non è definito, impostalo (modifica l'EPSG se necessario)
    if roads_gdf.crs is None:
        roads_gdf = roads_gdf.set_crs("EPSG:4326")

    # Creiamo un GeoDataFrame dai confini della regione del Sahel (già caricato nella variabile geojson_data)
    region_gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])

    # Se anche il CRS della regione non è definito, impostalo
    if region_gdf.crs is None:
        region_gdf = region_gdf.set_crs("EPSG:4326")

    # Converti il sistema di coordinate delle strade in quello della regione (se necessario)
    roads_gdf = roads_gdf.to_crs(region_gdf.crs)

    # Unisci i confini della regione in un'unica geometria
    region_union = region_gdf.unary_union

    # Filtra le strade che intersecano i confini del Sahel
    roads_in_region = roads_gdf[roads_gdf.intersects(region_union)]

    # Calcola il centro della regione per centrare la mappa
    centroid = region_union.centroid
    map_center = [centroid.y, centroid.x]

    # Crea la mappa con Folium
    m = folium.Map(location=map_center, zoom_start=10)

    # Aggiungi il layer dei confini della regione con uno stile semi-trasparente
    folium.GeoJson(
        region_gdf,
        name="Confini Sahel",
        style_function=lambda feature: {
            'fillColor': '#0000ff',
            'color': '#0000ff',
            'weight': 2,
            'fillOpacity': 0.1
        }
    ).add_to(m)

    # Aggiungi il layer delle strade con uno stile in rosso
    folium.GeoJson(
        roads_in_region,
        name="Strade",
        style_function=lambda feature: {
            'color': 'red',
            'weight': 2
        }
    ).add_to(m)

    # Aggiungi il controllo dei layer alla mappa
    folium.LayerControl().add_to(m)

    # Renderizza la mappa in Streamlit
    st.title("Mappa delle strade del Sahel")
    st_folium(m, width=700, height=500)

elif page == "Chat Bot":
    st.title("🤖 Chat Bot AI")
    st.write("Questo chatbot integra le API di OpenAI e utilizza un riepilogo dei dati già caricati per rispondere alle tue domande.")

    # Funzione per creare un riepilogo dei dati (modifica a piacere)
    def get_data_summary():
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        summary = f"Il dataset copre le date dal {min_date} al {max_date}. Analizza le precipitazioni giornaliere nel Burkina Faso."
        return summary

    data_summary = get_data_summary()

    # Gestione della cronologia della chat
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    # Input utente
    user_input = st.text_input("Scrivi il tuo messaggio:")

    if st.button("Invia"):
        if user_input:
            # Costruisci il prompt includendo il riepilogo dei dati
            prompt = f"Ho i seguenti dati: {data_summary}. {user_input}"

            # Chiamata alle API di OpenAI
            import openai
            # Assicurati di avere impostato la chiave API (ad esempio, tramite l'ambiente OPENAI_API_KEY)
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Sei un assistente esperto in analisi dei dati relativi alle precipitazioni in Burkina Faso."},
                        {"role": "user", "content": prompt}
                    ]
                )
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"Errore durante la chiamata all'API: {e}"

            st.session_state['chat_history'].append({"role": "user", "content": user_input})
            st.session_state['chat_history'].append({"role": "bot", "content": answer})
            st.experimental_rerun()

    # Visualizza la cronologia della chat
    for msg in st.session_state['chat_history']:
        if msg['role'] == "user":
            st.markdown(f"**Utente:** {msg['content']}")
        else:
            st.markdown(f"**Bot:** {msg['content']}")