import calendar
from datetime import datetime
import io
import json
import os
import pickle
from fpdf import FPDF
import google.generativeai as genai
import holidays
import pandas as pd
import PIL.Image
import plotly.express as px
import streamlit as st

# ==========================================
# KONFIGURACJA I CSS - V2
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
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# FUNKCJE POMOCNICZE
# ==========================================
ARCHIVE_FILE = "archiwum_premii_v2.pkl"


def load_archive():
  if os.path.exists(ARCHIVE_FILE):
    try:
      with open(ARCHIVE_FILE, "rb") as f:
        return pickle.load(f)
    except:
      return {}
  return {}


def save_archive(archive_data):
  with open(ARCHIVE_FILE, "wb") as f:
    pickle.dump(archive_data, f)


def normalize_name(name):
  """Sprowadza imię i nazwisko do alfabetycznej postaci wielkich liter.

  Dzięki temu 'JAN KOWALSKI' oraz 'KOWALSKI JAN' są identycznie dopasowywane.
  """
  if pd.isna(name) or not str(name).strip():
    return ""
  words = str(name).strip().upper().split()
  words.sort()
  return " ".join(words)


def remove_pl_chars(text):
  replacements = {
      "ą": "a",
      "ć": "c",
      "ę": "e",
      "ł": "l",
      "ń": "n",
      "ó": "o",
      "ś": "s",
      "ź": "z",
      "ż": "z",
      "Ą": "A",
      "Ć": "C",
      "Ę": "E",
      "Ł": "L",
      "Ń": "N",
      "Ó": "O",
      "Ś": "S",
      "Ź": "Z",
      "Ż": "Z",
  }
  for k, v in replacements.items():
    text = str(text).replace(k, v)
  return text


def get_col_sum_flexible(df, possible_names):
  if df.empty:
    return 0.0
  for col in df.columns:
    if str(col).strip().lower() in [p.lower() for p in possible_names]:
      return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())
  return 0.0


def process_attendance_photo(image_file, api_key):
  """Odczytuje zdjęcie listy obecności z wykorzystaniem Gemini Vision AI."""
  try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    img = PIL.Image.open(image_file)

    prompt = """
        Przeanalizuj podane zdjęcie ręcznie wypisanej listy obecności.
        Zlokalizuj w tabeli dane:
        1. Datę dzienną.
        2. Imię i Nazwisko pracownika.
        3. Faktyczną godzinę wejścia (rozpoczęcia pracy).
        4. Faktyczną godzinę wyjścia (zakończenia pracy).
        5. Wartość z kolumny przeznaczonej na NADGODZINY (np. "Nadgodziny", "Nadg.", "Godziny dodatkowe").

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
