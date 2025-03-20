import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

# --- CONFIGURAZIONE DELLA PAGINA ---
st.set_page_config(page_title="Burkina Faso Rainfall", layout="wide")

# --- CARICAMENTO E PREPARAZIONE DEI DATI ---
@st.cache_data
def load_data():
    df = pd.read_csv("bfa-rainfall-adm2-full.csv", parse_dates=["date"], low_memory=False)
    df = df.iloc[1:]  # Rimuove la prima riga se non serve
    df["rfh"] = pd.to_numeric(df["rfh"], errors="coerce")  # Converti a numerico
    return df

df = load_data()

# --- INTERFACCIA UTENTE ---
st.title("📊 Rainfall Analysis in Burkina Faso")
st.write("Seleziona l'intervallo di date per analizzare la pioggia giornaliera.")

# Correggi il problema convertendo esplicitamente la colonna 'date'
min_date = pd.to_datetime(df["date"]).min()
max_date = pd.to_datetime(df["date"]).max()

# Usa solo .date() se il valore non è NaT
start_date, end_date = st.slider(
    "Seleziona il periodo di analisi:",
    min_value=min_date.date() if not pd.isnull(min_date) else pd.to_datetime("2000-01-01").date(),
    max_value=max_date.date() if not pd.isnull(max_date) else pd.to_datetime("2023-12-31").date(),
    value=(pd.to_datetime("2021-06-01").date(), pd.to_datetime("2022-06-01").date()),
    format="YYYY-MM-DD"
)
# --- FILTRAGGIO DEI DATI ---
# Assicurati che la colonna 'date' sia in formato datetime
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df_filtered = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]

# Aggregazione dei dati (somma della pioggia giornaliera)
df_daily_sum = df_filtered.groupby("date")["rfh"].sum().reset_index()
df_daily_sum = df_daily_sum.sort_values(by="date").reset_index(drop=True)

# 1. Analisi delle Tendenze Temporali (Media Mobile)
df_daily_sum["rolling_30d"] = df_daily_sum["rfh"].rolling(window=30).mean()

# 3. Confronto Anno su Anno
df_daily_sum["year"] = df_daily_sum["date"].dt.year
df_annual = df_daily_sum.groupby("year")["rfh"].sum().reset_index()

# 4. Analisi di Periodi di Siccità
df_daily_sum["dry_days"] = df_daily_sum["rfh"] == 0
df_daily_sum["consecutive_dry"] = df_daily_sum["dry_days"].cumsum() - df_daily_sum["dry_days"].cumsum().where(~df_daily_sum["dry_days"]).ffill().fillna(0)

# 5. Previsioni di Pioggia con ARIMA
if len(df_daily_sum["rfh"].dropna()) > 100:  # Controllo per evitare errori con pochi dati
    model = ARIMA(df_daily_sum["rfh"].dropna(), order=(5,1,0))
    model_fit = model.fit()
    forecast = model_fit.forecast(steps=30)
    forecast_dates = pd.date_range(start=df_daily_sum["date"].iloc[-1], periods=30, freq="D")


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


# --- GRAFICO Confronto Anno su Anno ---
fig, ax2 = plt.subplots(figsize=(12, 6))
ax2.bar(df_annual["year"], df_annual["rfh"], color="skyblue")
ax2.set_title("Annual Rainfall Comparison")
ax2.set_xlabel("Year")
ax2.set_ylabel("Total Rainfall (mm)")
ax2.grid(axis="y", linestyle="--", alpha=0.7)
st.pyplot(fig)

# --- GRAFICO Periodi di Siccità ---
fig, ax3 = plt.subplots(figsize=(12, 6))
ax3.plot(df_daily_sum["date"], df_daily_sum["consecutive_dry"], label="Consecutive Dry Days", color="orange")
ax3.set_title("Consecutive Dry Days Over Time")
ax3.set_xlabel("Date")
ax3.set_ylabel("Consecutive Dry Days")
ax3.legend()
ax3.grid(True)
st.pyplot(fig)

# --- GRAFICO Previsioni con ARIMA ---
if "forecast" in locals():
    fig, ax4 = plt.subplots(figsize=(12, 6))
    ax4.plot(df_daily_sum["date"], df_daily_sum["rfh"], label="Observed", color="blue")
    ax4.plot(forecast_dates, forecast, label="Forecast", color="red", linestyle="dashed")
    ax4.set_title("Rainfall Forecast (Next 30 Days)")
    ax4.set_xlabel("Date")
    ax4.set_ylabel("Rainfall (mm)")
    ax4.legend()
    ax4.grid(True)
    st.pyplot(fig)


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