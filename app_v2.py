import calendar
from datetime import datetime
import io
import json
import os
import pickle
import google.generativeai as genai
import holidays
import pandas as pd
import PIL.Image
import plotly.express as px
import streamlit as st

# ==========================================
# KONFIGURACJA I CSS
# ==========================================
st.set_page_config(
    page_title="System Rozliczania Harmonogramów v2",
    layout="wide",
    page_icon="📈",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa; }
    div.stButton > button { border-radius: 5px; border: 1px solid #ddd; }
    div.stDataFrame { border-radius: 10px; }
    h1, h2, h3 { color: #1e3a8a; }
    .alert-box { background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 12px; margin: 12px 0; border-radius: 6px; color: #991b1b; }
    .success-box { background-color: #d1fae5; border-left: 5px solid #10b981; padding: 12px; margin: 12px 0; border-radius: 6px; color: #065f46; }
    .pay-slip { background-color: #ffffff; border: 2px solid #1e3a8a; border-radius: 10px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .pay-slip-header { border-bottom: 2px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 15px; }
    @media print {
        .stApp header, .stApp footer, .stSidebar, div[data-testid="stToolbar"] { display: none !important; }
        .pay-slip { page-break-inside: avoid; border: 1px solid #000; box-shadow: none; }
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# FUNKCJE POMOCNICZE I OBSŁUGA PLIKÓW
# ==========================================
ARCHIVE_FILE = "archiwum_premii_v2.pkl"


def load_archive():
  if os.path.exists(ARCHIVE_FILE):
    try:
      with open(ARCHIVE_FILE, "rb") as f:
        return pickle.load(f)
    except Exception:
      return {}
  return {}


def save_archive(archive_data):
  with open(ARCHIVE_FILE, "wb") as f:
    pickle.dump(archive_data, f)


def normalize_name(name):
  """Sprowadza imię i nazwisko do alfabetycznej postaci wielkich liter."""
  if pd.isna(name) or not str(name).strip():
    return ""
  words = str(name).strip().upper().split()
  words.sort()
  return " ".join(words)


def get_col_sum_flexible(df, possible_names):
  if df.empty:
    return 0.0
  for col in df.columns:
    if str(col).strip().lower() in [p.lower() for p in possible_names]:
      return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())
  return 0.0


def parse_daily_production(prod_df, year, month_idx):
  """Parsuje plik produkcji i grupuje wartości (sztuki, pozycje, waga) na każdy dzień miesiąca."""
  days_in_month = calendar.monthrange(year, month_idx)[1]
  daily_map = {
      day: {"pcs": 0.0, "lines": 0.0, "weight": 0.0}
      for day in range(1, days_in_month + 1)
  }

  if not prod_df.empty:
    date_col, pcs_col, lines_col, weight_col = None, None, None, None

    for col in prod_df.columns:
      c_low = str(col).strip().lower()
      if not date_col and c_low in [
          "data",
          "date",
          "dzień",
          "dzien",
          "data przyjęcia",
          "data przyjecia",
      ]:
        date_col = col
      if not pcs_col and c_low in [
          "sztuki",
          "sztuka",
          "pcs",
          "ilość sztuk",
          "ilosc sztuk",
      ]:
        pcs_col = col
      if not lines_col and c_low in [
          "pozycje",
          "pozycja",
          "lines",
          "ilość pozycji",
          "ilosc pozycji",
      ]:
        lines_col = col
      if not weight_col and c_low in [
          "waga",
          "waga łączna",
          "waga laczna",
          "weight",
          "kg",
      ]:
        weight_col = col

    if date_col:
      for _, row in prod_df.iterrows():
        raw_date = row[date_col]
        if pd.isna(raw_date):
          continue
        try:
          dt = pd.to_datetime(raw_date, dayfirst=True, errors="coerce")
          if pd.notna(dt) and dt.year == year and dt.month == month_idx:
            d = dt.day
            p = (
                float(pd.to_numeric(row[pcs_col], errors="coerce"))
                if pcs_col and pd.notna(row[pcs_col])
                else 0.0
            )
            l = (
                float(pd.to_numeric(row[lines_col], errors="coerce"))
                if lines_col and pd.notna(row[lines_col])
                else 0.0
            )
            w = (
                float(pd.to_numeric(row[weight_col], errors="coerce"))
                if weight_col and pd.notna(row[weight_col])
                else 0.0
            )

            if d in daily_map:
              daily_map[d]["pcs"] += max(0.0, p)
              daily_map[d]["lines"] += max(0.0, l)
              daily_map[d]["weight"] += max(0.0, w)
        except Exception:
          pass

  return daily_map


def process_attendance_photo(image_file, api_key):
  """Odczytuje zdjęcie listy obecności z wykorzystaniem Gemini Vision AI."""
  try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    img = PIL.Image.open(image_file)

    prompt = """
        Przeanalizuj podane zdjęcie ręcznie wypisanej listy obecności.
        Zlokalizuj w tabeli dane:
        1. Datę dzienną (DD.MM.YYYY).
        2. Imię i Nazwisko pracownika.
        3. Faktyczną godzinę wejścia.
        4. Faktyczną godzinę wyjścia.
        5. Wartość z kolumny nadgodzin.

        Zwróć wynik WYŁĄCZNIE jako poprawny kod JSON (tablica obiektów):
        [
          {
            "data": "DD.MM.YYYY",
            "osoba": "IMIE NAZWISKO",
            "wejscie": "HH:MM",
            "wyjscie": "HH:MM",
            "nadgodziny": 0.0
          }
        ]
        """
    response = model.generate_content([img, prompt])
    raw_text = response.text.strip()

    if raw_text.startswith("```json"):
      raw_text = raw_text[7:]
    if raw_text.endswith("
