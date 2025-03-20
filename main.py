import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet

# Parametri
CSV_PATH = '/mnt/data/bfa-rainfall-adm2-full.csv'
TARGET_COLUMN = 'rfh'  # Precipitazioni ogni 10 giorni

# Caricamento del dataset
df = pd.read_csv(CSV_PATH)

# Assicuriamoci che ci sia una colonna con la data
if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date'])
elif 'year' in df.columns and 'dekad' in df.columns:
    # Creazione di una colonna data a partire da "year" e "dekad"
    def dekad_to_date(row):
        month = (row['dekad'] - 1) // 3 + 1
        day = ((row['dekad'] - 1) % 3) * 10 + 1
        return pd.Timestamp(year=int(row['year']), month=int(month), day=int(day))

    df['date'] = df.apply(dekad_to_date, axis=1)
else:
    raise ValueError("Il dataset non contiene 'date' né 'year' e 'dekad'.")

# Selezioniamo un'area geografica (ad esempio il primo 'Pcode' disponibile)
if 'Pcode' in df.columns:
    pcode_value = df['Pcode'].unique()[0]
    df_unit = df[df['Pcode'] == pcode_value].copy()
    print(f"Analizzando dati per Pcode: {pcode_value}")
else:
    df_unit = df.copy()

# Selezioniamo solo le colonne necessarie
df_unit = df_unit[['date', TARGET_COLUMN]].dropna()
df_unit.columns = ['ds', 'y']  # Prophet richiede colonne con nomi specifici

# Creazione del modello Prophet
model = Prophet(daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=True)
model.fit(df_unit)

# Creazione di un DataFrame per la previsione
future = model.make_future_dataframe(periods=365, freq='D')  # Previsione per 1 anno
forecast = model.predict(future)

# Visualizzazione della previsione
fig = model.plot(forecast)
plt.title("Previsione delle precipitazioni con Facebook Prophet")
plt.xlabel("Data")
plt.ylabel("Precipitazione (mm)")
plt.show()
