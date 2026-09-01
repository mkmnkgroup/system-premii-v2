import calendar
from datetime import datetime
import io
import json
import os
import pickle
import re
from fpdf import FPDF
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


def process_attendance_photo(image_file, api_key):
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
        5. Wartość z kolumny przeznaczonej na NADGODZINY.

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

    clean_text = re.sub(
        r"^`{3}(json)?|`{3}$", "", raw_text, flags=re.IGNORECASE
    ).strip()

    return json.loads(clean_text)
  except Exception as e:
    st.error(f"Błąd analizy obrazu AI ({image_file.name}): {e}")
    return []


# ==========================================
# DOMYŚLNE DANE KONFIGURACYJNE
# ==========================================
DEFAULT_ABSENCE_CODES = [
    {"Oznaczenie": "Brak", "Rodzaj nieobecności": "Brak"},
    {"Oznaczenie": "Z", "Rodzaj nieobecności": "URLOP NA ŻĄDANIE"},
    {
        "Oznaczenie": "W",
        "Rodzaj nieobecności": "URLOP WYPOCZYNKOWY WYKORZYSTANY",
    },
    {"Oznaczenie": "NO", "Rodzaj nieobecności": "NIEOBECNY"},
    {"Oznaczenie": "B", "Rodzaj nieobecności": "URLOP BEZPŁATNY"},
    {"Oznaczenie": "1", "Rodzaj nieobecności": "AKTUALNIE POTWIERDZONY"},
    {"Oznaczenie": "N", "Rodzaj nieobecności": "NIEOBECNOŚĆ NIEUSPRAWIEDLIWIONA"},
    {"Oznaczenie": "H", "Rodzaj nieobecności": "CHOROBOWE"},
    {"Oznaczenie": "K", "Rodzaj nieobecności": "KRWIODAWSTWO"},
    {"Oznaczenie": "SW", "Rodzaj nieobecności": "SIŁA WYŻSZA"},
    {"Oznaczenie": "NU", "Rodzaj nieobecności": "NIEOBECNOŚĆ USPRAWIEDLIWIONA"},
    {"Oznaczenie": "OŚ", "Rodzaj nieobecności": "ODEBRANE ZA ŚWIĘTO"},
]

DEFAULT_GROUPS = [
    {"Nazwa grupy": "GRUPA 1", "Czas pracy": "06:00-14:00"},
    {"Nazwa grupy": "GRUPA 2", "Czas pracy": "08:00-16:00"},
    {"Nazwa grupy": "GRUPA 3", "Czas pracy": "11:00-19:00"},
    {"Nazwa grupy": "GRUPA 4", "Czas pracy": "08:00-16:00"},
    {"Nazwa grupy": "GRUPA 5", "Czas pracy": "08:00-16:00"},
    {"Nazwa grupy": "GRUPA 6", "Czas pracy": "11:00-19:00"},
    {"Nazwa grupy": "GRUPA 7", "Czas pracy": "08:00-17:00"},
]

DEFAULT_EMPLOYEES = [
    {
        "OSOBA": "ADRIAN WRONA",
        "GRUPA": "GRUPA 4",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
    },
    {
        "OSOBA": "ANTON FEDOSOV",
        "GRUPA": "GRUPA 3",
        "SYSTEM": "PONIEDZIAŁEK-PIĄTEK",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
    },
    {
        "OSOBA": "JAKUB JANECZEK",
        "GRUPA": "GRUPA 2",
        "SYSTEM": "PONIEDZIAŁEK-PIĄTEK",
        "STANOWISKO": "BRYGADZISTA",
        "FUNKCJA": "2 SKANOWANIE",
    },
    {
        "OSOBA": "JAKUB RĘBACZ",
        "GRUPA": "GRUPA 4",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
    },
    {
        "OSOBA": "KYRYLO BZHEZITSKYI",
        "GRUPA": "GRUPA 1",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "BRYGADZISTA",
        "FUNKCJA": "1 SKANOWANIE",
    },
    {
        "OSOBA": "MACIEJ BORZĘCKI",
        "GRUPA": "GRUPA 3",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
    },
    {
        "OSOBA": "MICHAŁ KWIATKOWSKI",
        "GRUPA": "GRUPA 7",
        "SYSTEM": "PONIEDZIAŁEK-PIĄTEK",
        "STANOWISKO": "KIEROWNIK",
        "FUNKCJA": "KIEROWNIK",
    },
    {
        "OSOBA": "VADZIM KARPUK",
        "GRUPA": "GRUPA 1",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
    },
    {
        "OSOBA": "WOJTEK SZYMAŃSKI",
        "GRUPA": "GRUPA 2",
        "SYSTEM": "PONIEDZIAŁEK-PIĄTEK",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "2 SKANOWANIE",
    },
]

# Stan sesji
if "history_v2" not in st.session_state:
  st.session_state.history_v2 = load_archive()
if "current_schedule_df" not in st.session_state:
  st.session_state.current_schedule_df = pd.DataFrame()
if "absence_codes_df" not in st.session_state:
  st.session_state.absence_codes_df = pd.DataFrame(DEFAULT_ABSENCE_CODES)
if "groups_df" not in st.session_state:
  st.session_state.groups_df = pd.DataFrame(DEFAULT_GROUPS)
if "employees_df" not in st.session_state:
  st.session_state.employees_df = pd.DataFrame(DEFAULT_EMPLOYEES)
if "special_bonuses_df" not in st.session_state:
  st.session_state.special_bonuses_df = pd.DataFrame(
      columns=[
          "Pracownik",
          "Kwota netto premii",
          "Kto przyznał",
          "Powód przyznania premii",
      ]
  )
if "imported_absences_df" not in st.session_state:
  st.session_state.imported_absences_df = pd.DataFrame()
if "gemini_api_key" not in st.session_state:
  st.session_state.gemini_api_key = ""

# Parametry wyliczeniowe
if "base_bonus_salary" not in st.session_state:
  st.session_state.base_bonus_salary = 4300.0
if "avg_lines_12m" not in st.session_state:
  st.session_state.avg_lines_12m = 17322.50
if "w_lines" not in st.session_state:
  st.session_state.w_lines = 42.86
if "avg_pcs_12m" not in st.session_state:
  st.session_state.avg_pcs_12m = 58710.75
if "w_pcs" not in st.session_state:
  st.session_state.w_pcs = 28.57
if "avg_weight_12m" not in st.session_state:
  st.session_state.avg_weight_12m = 26417.42
if "w_weight" not in st.session_state:
  st.session_state.w_weight = 28.57

if "ot_kierownik" not in st.session_state:
  st.session_state.ot_kierownik = 35.0
if "ot_brygadzista" not in st.session_state:
  st.session_state.ot_brygadzista = 30.0
if "ot_magazynier" not in st.session_state:
  st.session_state.ot_magazynier = 25.0
if "rate_pallet" not in st.session_state:
  st.session_state.rate_pallet = 10.0
if "forklift_pool" not in st.session_state:
  st.session_state.forklift_pool = 600.0

# Domyślne tabele dynamiczne w kalkulatorze
if "pallet_emp_df" not in st.session_state:
  st.session_state.pallet_emp_df = pd.DataFrame(
      [{"Pracownik": emp["OSOBA"]} for emp in DEFAULT_EMPLOYEES]
  )
if "forklift_df"
