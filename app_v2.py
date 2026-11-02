import base64
import calendar
from datetime import datetime
import io
import json
import os
import pickle
import re
from github import Github, GithubException
import google.generativeai as genai
import holidays
import pandas as pd
import PIL.Image
import plotly.express as px
import streamlit as st

# ==========================================
# KONFIGURACJA I STYLIZACJA CSS
# ==========================================
st.set_page_config(
    page_title="System Rozliczania Harmonogramów v2.6",
    layout="wide",
    page_icon="📈",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa; }
    div.stButton > button { border-radius: 6px; border: 1px solid #cbd5e1; font-weight: 500; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #1e3a8a; }
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
# OBSŁUGA ARCHIWUM I USTAWIENI PRZEZ GITHUB / DYSK
# ==========================================
ARCHIVE_FILE = "archiwum_premii_v2.pkl"
SETTINGS_FILE = "settings_v2.json"


def get_github_repo():
  try:
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["GITHUB_REPO"]
    g = Github(token)
    return g.get_repo(repo_name)
  except Exception:
    return None


def load_archive():
  repo = get_github_repo()
  if not repo:
    if os.path.exists(ARCHIVE_FILE):
      try:
        with open(ARCHIVE_FILE, "rb") as f:
          return pickle.load(f)
      except Exception:
        return {}
    return {}

  try:
    file_content = repo.get_contents(ARCHIVE_FILE)
    decoded_data = base64.b64decode(file_content.content)
    return pickle.loads(decoded_data)
  except GithubException as e:
    if e.status == 404:
      return {}
    else:
      return {}
  except Exception:
    return {}


def save_archive(archive_data):
  try:
    with open(ARCHIVE_FILE, "wb") as f:
      pickle.dump(archive_data, f)
  except Exception:
    pass

  repo = get_github_repo()
  if not repo:
    return

  pickled_data = pickle.dumps(archive_data)
  encoded_data = base64.b64encode(pickled_data).decode("utf-8")
  commit_message = "Automatyczna aktualizacja archiwum premii z Streamlit"

  try:
    try:
      file = repo.get_contents(ARCHIVE_FILE)
      repo.update_file(
          path=ARCHIVE_FILE,
          message=commit_message,
          content=encoded_data,
          sha=file.sha,
      )
    except GithubException as e:
      if e.status == 404:
        repo.create_file(
            path=ARCHIVE_FILE, message=commit_message, content=encoded_data
        )
      else:
        raise e
  except Exception as e:
    st.error(f"Nie udało się zapisać archiwum na GitHub: {e}")


def load_persistent_settings():
  if os.path.exists(SETTINGS_FILE):
    try:
      with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_persistent_settings(settings_dict):
  try:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
      json.dump(settings_dict, f, ensure_ascii=False, indent=4)
  except Exception as e:
    st.error(f"Błąd zapisu ustawień: {e}")


def normalize_name(name):
  if pd.isna(name) or not str(name).strip():
    return ""
  words = str(name).strip().upper().split()
  words.sort()
  return " ".join(words)


def get_col_sum_flexible(df, possible_names):
  if df.empty:
    return 0.0
  low_possible = [p.lower() for p in possible_names]
  for col in df.columns:
    if str(col).strip().lower() in low_possible:
      return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())
  return 0.0


@st.cache_data(show_spinner=False)
def load_excel_cached(file_bytes, filename):
  ext = filename.split(".")[-1].lower()
  return pd.read_excel(
      io.BytesIO(file_bytes), engine="xlrd" if ext == "xls" else "openpyxl"
  )


@st.cache_data(show_spinner=False)
def parse_daily_production_cached(prod_df, year, month_idx):
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

    match = re.search(r"\[.*\]", raw_text, re.DOTALL)
    if match:
      raw_text = match.group(0)

    return json.loads(raw_text)
  except Exception as e:
    st.error(f"Błąd analizy obrazu AI ({image_file.name}): {e}")
    return []


# ==========================================
# DOMYŚLNE DANE SYSTEMOWE I WCZYTANIE ZAPISANYCH
# ==========================================
saved_settings = load_persistent_settings()

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
        "UPRAWNIENIA UDT": True,
    },
    {
        "OSOBA": "ANTON FEDOSOV",
        "GRUPA": "GRUPA 3",
        "SYSTEM": "PONIEDZIAŁEK-PIĄTEK",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
        "UPRAWNIENIA UDT": False,
    },
    {
        "OSOBA": "JAKUB JANECZEK",
        "GRUPA": "GRUPA 2",
        "SYSTEM": "PONIEDZIAŁEK-PIĄTEK",
        "STANOWISKO": "BRYGADZISTA",
        "FUNKCJA": "2 SKANOWANIE",
        "UPRAWNIENIA UDT": False,
    },
    {
        "OSOBA": "JAKUB RĘBACZ",
        "GRUPA": "GRUPA 4",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
        "UPRAWNIENIA UDT": False,
    },
    {
        "OSOBA": "KYRYLO BZHEZITSKYI",
        "GRUPA": "GRUPA 1",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "BRYGADZISTA",
        "FUNKCJA": "1 SKANOWANIE",
        "UPRAWNIENIA UDT": True,
    },
    {
        "OSOBA": "MACIEJ BORZĘCKI",
        "GRUPA": "GRUPA 3",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
        "UPRAWNIENIA UDT": False,
    },
    {
        "OSOBA": "MICHAŁ KWIATKOWSKI",
        "GRUPA": "GRUPA 7",
        "SYSTEM": "PONIEDZIAŁEK-PIĄTEK",
        "STANOWISKO": "KIEROWNIK",
        "FUNKCJA": "KIEROWNIK",
        "UPRAWNIENIA UDT": False,
    },
    {
        "OSOBA": "VADZIM KARPUK",
        "GRUPA": "GRUPA 1",
        "SYSTEM": "WTOREK-SOBOTA",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "1 SKANOWANIE",
        "UPRAWNIENIA UDT": True,
    },
    {
        "OSOBA": "WOJTEK SZYMAŃSKI",
        "GRUPA": "GRUPA 2",
        "SYSTEM": "PONIEDZIAŁEK-PIĄTEK",
        "STANOWISKO": "MAGAZYNIER",
        "FUNKCJA": "2 SKANOWANIE",
        "UPRAWNIENIA UDT": False,
    },
]

PL_DAYS = {
    0: "poniedziałek",
    1: "wtorek",
    2: "środa",
    3: "czwartek",
    4: "piątek",
    5: "sobota",
    6: "niedziela",
}

# Inicjalizacja Stanu Sesji (z uwzględnieniem zapisanych ustawień)
if "history_v2" not in st.session_state:
  st.session_state.history_v2 = load_archive()
if "current_schedule_df" not in st.session_state:
  st.session_state.current_schedule_df = pd.DataFrame()
if "absence_codes_df" not in st.session_state:
  st.session_state.absence_codes_df = pd.DataFrame(DEFAULT_ABSENCE_CODES)
if "groups_df" not in st.session_state:
  st.session_state.groups_df = pd.DataFrame(DEFAULT_GROUPS)

if "employees_df" not in st.session_state:
  if "employees_df" in saved_settings:
    st.session_state.employees_df = pd.DataFrame(saved_settings["employees_df"])
  else:
    st.session_state.employees_df = pd.DataFrame(DEFAULT_EMPLOYEES)

if "special_bonuses_df" not in st.session_state:
  st.session_state.special_bonuses_df = pd.DataFrame(
      columns=[
          "Pracownik",
          "Kwota netto premii",
          "Powód przyznania premii",
          "Kto przyznał",
      ]
  )
if "forklift_hours_df" not in st.session_state:
  current_emps_list = st.session_state.employees_df["OSOBA"].tolist()
  st.session_state.forklift_hours_df = pd.DataFrame(
      [{"OSOBA": name, "CZAS WÓZKA (godz.)": 0.0} for name in current_emps_list]
  )
if "imported_absences_df" not in st.session_state:
  st.session_state.imported_absences_df = pd.DataFrame()
if "gemini_api_key" not in st.session_state:
  st.session_state.gemini_api_key = ""

# Parametry z zapisanych ustawień lub domyślne
if "base_bonus_salary" not in st.session_state:
  st.session_state.base_bonus_salary = saved_settings.get(
      "base_bonus_salary", 4300.0
  )
if "kierownik_bonus_multiplier" not in st.session_state:
  st.session_state.kierownik_bonus_multiplier = saved_settings.get(
      "kierownik_bonus_multiplier", 1.35
  )
if "forklift_pool" not in st.session_state:
  st.session_state.forklift_pool = saved_settings.get("forklift_pool", 600.0)
if "rate_pallet" not in st.session_state:
  st.session_state.rate_pallet = saved_settings.get("rate_pallet", 10.0)

if "avg_lines_12m" not in st.session_state:
  st.session_state.avg_lines_12m = saved_settings.get(
      "avg_lines_12m", 17322.50
  )
if "w_lines" not in st.session_state:
  st.session_state.w_lines = saved_settings.get("w_lines", 42.86)
if "avg_pcs_12m" not in st.session_state:
  st.session_state.avg_pcs_12m = saved_settings.get("avg_pcs_12m", 58710.75)
if "w_pcs" not in st.session_state:
  st.session_state.w_pcs = saved_settings.get("w_pcs", 28.57)
if "avg_weight_12m" not in st.session_state:
  st.session_state.avg_weight_12m = saved_settings.get(
      "avg_weight_12m", 26417.42
  )
if "w_weight" not in st.session_state:
  st.session_state.w_weight = saved_settings.get("w_weight", 28.57)

if "ot_kierownik" not in st.session_state:
  st.session_state.ot_kierownik = saved_settings.get("ot_kierownik", 35.0)
if "ot_brygadzista" not in st.session_state:
  st.session_state.ot_brygadzista = saved_settings.get("ot_brygadzista", 30.0)
if "ot_magazynier" not in st.session_state:
  st.session_state.ot_magazynier = saved_settings.get("ot_magazynier", 25.0)


# ==========================================
# GENEROWANIE HARMONOGRAMU
# ==========================================
@st.cache_data(show_spinner=False)
def generate_schedule_cached(year, month_idx, emp_tuples, groups_tuples):
  days_in_month = calendar.monthrange(year, month_idx)[1]
  pl_holidays = holidays.Poland(years=year)

  maciej_early_days = set()
  maciej_emp = None

  for emp in emp_tuples:
    norm_emp_name = normalize_name(emp.get("OSOBA", ""))
    if "BORZECKI" in norm_emp_name or "MACIEJ" in norm_emp_name:
      maciej_emp = emp
      break

  if maciej_emp is not None:
    for day in range(1, days_in_month + 1):
      date_obj = datetime(year, month_idx, day)
      day_name = PL_DAYS[date_obj.weekday()]
      week_num = date_obj.isocalendar()[1]
      is_holiday = date_obj in pl_holidays

      is_working_day = True
      sys_val = str(maciej_emp.get("SYSTEM", ""))
      if "PONIEDZIAŁEK" in sys_val.upper() and day_name in [
          "sobota",
          "niedziela",
      ]:
        is_working_day = False
      elif "WTOREK" in sys_val.upper() and day_name in [
          "niedziela",
          "poniedziałek",
      ]:
        is_working_day = False
      if is_holiday:
        is_working_day = False

      if is_working_day:
        try:
          g_num = int(
              str(maciej_emp.get("GRUPA", "")).replace("GRUPA", "").strip()
          )
        except Exception:
          g_num = 1
        shift_rotation = ((week_num - 1 + (g_num - 1)) % 3) + 1
        if shift_rotation == 1:
          maciej_early_days.add(date_obj.strftime("%d.%m.%Y"))

  schedule_rows = []

  for day in range(1, days_in_month + 1):
    date_obj = datetime(year, month_idx, day)
    date_str = date_obj.strftime("%d.%m.%Y")
    day_name = PL_DAYS[date_obj.weekday()]
    week_num = date_obj.isocalendar()[1]
    is_holiday = date_obj in pl_holidays

    for emp in emp_tuples:
      is_working_day = True
      sys_val = str(emp.get("SYSTEM", ""))

      if "PONIEDZIAŁEK" in sys_val.upper() and day_name in [
          "sobota",
          "niedziela",
      ]:
        is_working_day = False
      elif "WTOREK" in sys_val.upper() and day_name in [
          "niedziela",
          "poniedziałek",
      ]:
        is_working_day = False
      if is_holiday:
        is_working_day = False

      status_dzien = (
          "Święto"
          if is_holiday
          else ("Pracujący" if is_working_day else "Wolny")
      )

      if not is_working_day:
        czas_zmiany = "Wolne"
        shift_val = "Wolne"
        default_start_end = "Wolne"
      else:
        default_start_end = ""
        g_str = str(emp.get("GRUPA", ""))
        try:
          g_num = int(g_str.replace("GRUPA", "").strip())
        except Exception:
          g_num = 1

        default_group_time = "08:00-16:00"
        for g_row in groups_tuples:
          if (
              str(g_row.get("Nazwa grupy", "")).strip().upper()
              == g_str.strip().upper()
          ):
            default_group_time = str(g_row.get("Czas pracy", "08:00-16:00"))
            break

        if g_num in [1, 2, 3]:
          shift_rotation = ((week_num - 1 + (g_num - 1)) % 3) + 1
          shift_val = shift_rotation
          if shift_rotation == 1:
            czas_zmiany = "06:00-14:00"
          elif shift_rotation == 2:
            czas_zmiany = "08:00-16:00"
          else:
            czas_zmiany = "11:00-19:00"
        else:
          czas_zmiany = default_group_time
          shift_val = g_num

        if g_num == 8:
          if date_str in maciej_early_days:
            czas_zmiany = "06:00-14:00"
            shift_val = 1
          else:
            czas_zmiany = "07:30-15:30"
            shift_val = 8

        if day_name == "poniedziałek":
          czas_zmiany = "08:00-17:00"
        elif day_name == "sobota":
          czas_zmiany = "08:00-16:00"

      schedule_rows.append({
          "DATA": date_str,
          "DZIEŃ TYGODNIA": day_name,
          "OSOBA": emp.get("OSOBA", ""),
          "STANOWISKO": emp.get("STANOWISKO", ""),
          "ZMIANA": shift_val if not is_holiday else "Święto",
          "CZAS ZMIANY": czas_zmiany,
          "DZIEŃ PRACUJĄCY/WOLNY": status_dzien,
          "GODZINA ROZPOCZĘCIA": default_start_end,
          "GODZINA ZAKOŃCZENIA": default_start_end,
          "FAKTYCZNIE WEJŚCIE": "",
          "FAKTYCZNIE WYJŚCIE": "",
          "NIEOBECNOŚĆ": "Brak",
          "NADGODZINY (godz.)": 0.0,
      })

  return pd.DataFrame(schedule_rows)


def generate_schedule(year, month_idx):
  emp_tuples = tuple(st.session_state.employees_df.to_dict("records"))
  groups_tuples = tuple(st.session_state.groups_df.to_dict("records"))
  return generate_schedule_cached(year, month_idx, emp_tuples, groups_tuples)


# ==========================================
# GŁÓWNA LOGIKA KALKULATORA WYNAGRODZEŃ
# ==========================================
def calculate_payroll(
    df_sched,
    employees_df,
    max_bonus_per_emp,
    forklift_hours_df,
    total_forklift_hours,
    pallet_pay_per_selected_emp,
    selected_pallet_emps,
    daily_work_pct_map,
    special_bonuses_df,
    include_absence_deduction=False,
):
  emp_summary = []
  emp_details_map = {}
  unique_emps = employees_df["OSOBA"].dropna().unique().tolist()

  fk_dict = dict(
      zip(
          forklift_hours_df["OSOBA"],
          pd.to_numeric(
              forklift_hours_df["CZAS WÓZKA (godz.)"], errors="coerce"
          ).fillna(0.0),
      )
  )

  for emp_name in unique_emps:
    emp_df = df_sched[
        df_sched["OSOBA"].str.strip().str.upper()
        == str(emp_name).strip().upper()
    ]
    emp_info_matches = employees_df[employees_df["OSOBA"] == emp_name]
    emp_info = emp_info_matches.iloc[0] if not emp_info_matches.empty else {}

    position = emp_info.get("STANOWISKO", "MAGAZYNIER")
    func = emp_info.get("FUNKCJA", "")
    emp_forklift_hours = float(fk_dict.get(emp_name, 0.0))

    days_worked = len(
        emp_df[
            (emp_df["DZIEŃ PRACUJĄCY/WOLNY"] == "Pracujący")
            & (emp_df["NIEOBECNOŚĆ"].isin(["Brak", "", "None"]))
        ]
    )
    absent_rows = emp_df[~emp_df["NIEOBECNOŚĆ"].isin(["Brak", "", "None"])]
    absent_days = len(absent_rows)
    total_ot = emp_df["NADGODZINY (godz.)"].sum()

    ot_rate = st.session_state.ot_magazynier
    if "KIEROWNIK" in str(position).upper():
      ot_rate = st.session_state.ot_kierownik
    elif "BRYGADZISTA" in str(position).upper():
      ot_rate = st.session_state.ot_brygadzista

    ot_pay = total_ot * ot_rate
    scheduled_work_days = len(
        emp_df[emp_df["DZIEŃ PRACUJĄCY/WOLNY"] == "Pracujący"]
    )
    attendance_ratio = (
        (days_worked / scheduled_work_days) if scheduled_work_days > 0 else 0.0
    )

    if include_absence_deduction:
      deduction_pct = (1.0 - attendance_ratio) * 100.0
      effective_ratio = attendance_ratio
    else:
      deduction_pct = 0.0
      effective_ratio = 1.0

    base_emp_bonus = max_bonus_per_emp
    if "KIEROWNIK" in str(position).upper() or "KIEROWNIK" in str(func).upper():
      base_emp_bonus *= st.session_state.kierownik_bonus_multiplier

    calculated_bonus = base_emp_bonus * effective_ratio

    emp_forklift_pct = (
        (emp_forklift_hours / total_forklift_hours * 100.0)
        if total_forklift_hours > 0
        else 0.0
    )
    forklift_pay = (
        (st.session_state.forklift_pool * (emp_forklift_pct / 100.0))
        if total_forklift_hours > 0
        else 0.0
    )
    pallet_pay = (
        pallet_pay_per_selected_emp if emp_name in selected_pallet_emps else 0.0
    )

    spec_bonus_val = 0.0
    spec_reasons_list = []
    if (
        not special_bonuses_df.empty
        and "Pracownik" in special_bonuses_df.columns
    ):
      spec_df = special_bonuses_df.copy()
      spec_df["Kwota netto premii"] = pd.to_numeric(
          spec_df["Kwota netto premii"], errors="coerce"
      ).fillna(0.0)
      matched_spec = spec_df[
          spec_df["Pracownik"].apply(normalize_name) == normalize_name(emp_name)
      ]
      spec_bonus_val = matched_spec["Kwota netto premii"].sum()
      for _, s_row in matched_spec.iterrows():
        r_txt = str(s_row.get("Powód przyznania premii", "")).strip()
        k_txt = str(s_row.get("Kto przyznał", "")).strip()
        q_val = float(s_row.get("Kwota netto premii", 0.0))
        if q_val > 0:
          spec_reasons_list.append(
              f"{q_val:,.2f} zł — {r_txt}"
              + (f" (przyznał: {k_txt})" if k_txt else "")
          )

    total_payout = (
        calculated_bonus + ot_pay + spec_bonus_val + forklift_pay + pallet_pay
    )

    absences_list = []
    for _, abs_r in absent_rows.iterrows():
      try:
        day_n = int(str(abs_r["DATA"]).split(".")[0])
      except Exception:
        day_n = 1
      day_work_pct = daily_work_pct_map.get(day_n, 0.0)

      absences_list.append({
          "Data": abs_r["DATA"],
          "Dzień tygodnia": abs_r["DZIEŃ TYGODNIA"],
          "Rodzaj nieobecności": abs_r["NIEOBECNOŚĆ"],
          "Udział pracy w miesiącu (%)": day_work_pct,
      })

    emp_summary.append({
        "Pracownik": emp_name,
        "Stanowisko": position,
        "Dni przepracowane": days_worked,
        "Dni nieobecności": absent_days,
        "% Potrącenia": deduction_pct,
        "Czas wózka (h)": emp_forklift_hours,
        "% Udział wózek": emp_forklift_pct,
        "Dodatek Wózek (zł)": forklift_pay,
        "Dodatek Palety (zł)": pallet_pay,
        "Nadgodziny (godz.)": total_ot,
        "Nadgodziny (zł)": ot_pay,
        "Premia (zł)": calculated_bonus,
        "Premia Specjalna (zł)": spec_bonus_val,
        "ŁĄCZNA PREMIA / DODATKI (zł)": total_payout,
    })

    emp_details_map[emp_name] = {
        "position": position,
        "emp_forklift_hours": emp_forklift_hours,
        "emp_forklift_pct": emp_forklift_pct,
        "forklift_pay": forklift_pay,
        "pallet_pay": pallet_pay,
        "days_worked": days_worked,
        "scheduled_days": scheduled_work_days,
        "absent_days": absent_days,
        "deduction_pct": deduction_pct,
        "base_emp_bonus": base_emp_bonus,
        "calculated_bonus": calculated_bonus,
        "total_ot": total_ot,
        "ot_pay": ot_pay,
        "spec_bonus_val": spec_bonus_val,
        "spec_reasons_list": spec_reasons_list,
        "total_payout": total_payout,
        "absences_table": pd.DataFrame(absences_list),
    }

  return pd.DataFrame(emp_summary), emp_details_map


# ==========================================
# PASEK BOCZNY
# ==========================================
st.sidebar.title("⚙️ Nawigacja")
st.sidebar.header("Okres Rozliczeniowy")
months_list = [
    "Styczeń",
    "Luty",
    "Marzec",
    "Kwiecień",
    "Maj",
    "Czerwiec",
    "Lipiec",
    "Sierpień",
    "Wrzesień",
    "Październik",
    "Listopad",
    "Grudzień",
]
gen_month_name = st.sidebar.selectbox(
    "Miesiąc:", months_list, index=datetime.now().month - 1
)
gen_month_idx = months_list.index(gen_month_name) + 1
gen_year = st.sidebar.number_input("Rok:", value=datetime.now().year, step=1)
period_key = f"{gen_month_name} {gen_year}"

if st.sidebar.button("🚀 Wygeneruj Harmonogram", type="primary"):
  st.session_state.current_schedule_df = generate_schedule(
      gen_year, gen_month_idx
  )
  st.sidebar.success(f"Wygenerowano na {period_key}!")

st.sidebar.markdown("---")
st.sidebar.header("📁 Plik Produkcji")
uploaded_month_file = st.sidebar.file_uploader(
    "Wgraj raport produkcji (Excel):", type=["xlsx", "xls"]
)

if st.session_state.current_schedule_df.empty:
  st.session_state.current_schedule_df = generate_schedule(
      gen_year, gen_month_idx
  )

# ==========================================
# ZAKŁADKI
# ==========================================
tab_gen, tab_calc, tab_dash, tab_history, tab_comp, tab_settings = st.tabs([
    "📋 Harmonogram i Skaner",
    "🧮 Kalkulator Premii",
    "📊 Dashboard i Wykresy",
    "📁 Archiwum Historyczne",
    "📈 Porównanie Wyników",
    "⚙️ Ustawienia Systemu",
])

# ==========================================
# ZAKŁADKA 1: HARMONOGRAM I SKANER
# ==========================================
with tab_gen:
  st.header("📋 Harmonogram Czasu Pracy i Rejestracja Obecności")

  col_action1, col_action2, _ = st.columns([1.5, 1.5, 2])
  with col_action1:
    if st.button("🔄 Wygeneruj ponownie Harmonogram"):
      st.session_state.current_schedule_df = generate_schedule(
          gen_year, gen_month_idx
      )
      st.success("Wygenerowano harmonogram!")
      st.rerun()

  with col_action2:
    uploaded_schedule_excel = st.file_uploader(
        "Wgraj gotowy plik z Harmonogramem:",
        type=["xlsx", "xls"],
        key="direct_schedule_uploader",
    )
    if uploaded_schedule_excel is not None:
      try:
        loaded_df = load_excel_cached(
            uploaded_schedule_excel.getvalue(), uploaded_schedule_excel.name
        )
        st.session_state.current_schedule_df = loaded_df
        st.success("Wczytano harmonogram z pliku!")
      except Exception as e:
        st.error(f"Błąd odczytu pliku: {e}")

  st.markdown("---")

  with st.expander("📥 1. Import Nieobecności z pliku Excel"):
    uploaded_absence_file = st.file_uploader(
        "Wgraj plik Excel z nieobecnościami",
        type=["xlsx", "xls"],
        key="absence_file_uploader",
    )
    if uploaded_absence_file is not None:
      try:
        raw_abs_df = load_excel_cached(
            uploaded_absence_file.getvalue(), uploaded_absence_file.name
        )
        if st.button("Zaimportuj nieobecności"):
          imported_records = []
          abs_map = {
              str(row["Oznaczenie"]).strip().upper(): str(
                  row["Rodzaj nieobecności"]
              ).strip()
              for _, row in st.session_state.absence_codes_df.iterrows()
          }

          for r in range(2, len(raw_abs_df)):
            emp_name = raw_abs_df.iloc[r, 0]
            if (
                pd.isna(emp_name)
                or str(emp_name).strip() == ""
                or str(emp_name).strip().lower() == "pracownik"
            ):
              continue
            emp_name_clean = str(emp_name).strip()

            for c in range(1, raw_abs_df.shape[1]):
              cell_val = raw_abs_df.iloc[r, c]
              if pd.notna(cell_val):
                code = str(cell_val).strip().upper()
                if code in abs_map and code != "BRAK":
                  day_val = None
                  for test_r in [1, 2]:
                    header_val = raw_abs_df.iloc[test_r, c]
                    try:
                      if (
                          pd.notna(header_val)
                          and int(float(header_val)) in range(1, 32)
                      ):
                        day_val = int(float(header_val))
                        break
                    except Exception:
                      pass
                  if day_val is None:
                    day_val = c

                  imported_records.append({
                      "Pracownik": emp_name_clean,
                      "Dzień": day_val,
                      "Oznaczenie": code,
                      "Opis": abs_map[code],
                  })

          st.session_state.imported_absences_df = pd.DataFrame(
              imported_records
          )
          st.success(f"Zaimportowano {len(imported_records)} wpisów!")
      except Exception as e:
        st.error(f"Błąd parsowania pliku nieobecności: {e}")

    if not st.session_state.imported_absences_df.empty:
      st.dataframe(
          st.session_state.imported_absences_df, use_container_width=True
      )

  with st.expander(
      "📸 2. Skanowanie List Obecności ze Zdjęć (AI Vision Gemini)"
  ):
    api_key_in = st.text_input(
        "Klucz API Google Gemini:",
        value=st.session_state.gemini_api_key,
        type="password",
    )
    st.session_state.gemini_api_key = api_key_in

    uploaded_photos = st.file_uploader(
        "Wgrywaj zdjęcia list obecności:",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if uploaded_photos and st.button(
        "🔍 Przeanalizuj zdjęcia i zaktualizuj godziny"
    ):
      if not api_key_in:
        st.error("Wprowadź klucz API Google Gemini.")
      else:
        df_temp = st.session_state.current_schedule_df.copy()
        if "FAKTYCZNIE WEJŚCIE" not in df_temp.columns:
          df_temp["FAKTYCZNIE WEJŚCIE"] = ""
        if "FAKTYCZNIE WYJŚCIE" not in df_temp.columns:
          df_temp["FAKTYCZNIE WYJŚCIE"] = ""

        total_extracted = 0
        for photo in uploaded_photos:
          with st.spinner(f"Analizowanie pliku {photo.name}..."):
            records = process_attendance_photo(photo, api_key_in)
            for rec in records:
              p_date = str(rec.get("data", "")).strip()
              p_name_norm = normalize_name(rec.get("osoba", ""))
              t_in = str(rec.get("wejscie", "")).strip()
              t_out = str(rec.get("wyjscie", "")).strip()
              try:
                ot_val = float(rec.get("nadgodziny", 0.0))
              except Exception:
                ot_val = 0.0

              for idx, row in df_temp.iterrows():
                row_name_norm = normalize_name(row["OSOBA"])
                if row["DATA"] == p_date and row_name_norm == p_name_norm:
                  df_temp.at[idx, "FAKTYCZNIE WEJŚCIE"] = t_in
                  df_temp.at[idx, "FAKTYCZNIE WYJŚCIE"] = t_out
                  df_temp.at[idx, "NADGODZINY (godz.)"] = ot_val
                  total_extracted += 1

        st.session_state.current_schedule_df = df_temp
        st.success(f"Dopasowano i zaktualizowano {total_extracted} wpisów!")
        st.rerun()

  st.markdown("---")
  col_b1, col_b2, _ = st.columns([1.5, 1.5, 2])
  with col_b1:
    if st.button("⏱️ Uzupełnij planowane godziny", use_container_width=True):
      df_temp = st.session_state.current_schedule_df.copy()

      if (
          not st.session_state.imported_absences_df.empty
          and "Pracownik" in st.session_state.imported_absences_df.columns
      ):
        abs_lookup = {}
        for _, abs_row in st.session_state.imported_absences_df.iterrows():
          emp_k = normalize_name(abs_row["Pracownik"])
          try:
            day_k = int(abs_row["Dzień"])
          except Exception:
            continue
          abs_lookup[(emp_k, day_k)] = abs_row["Opis"]

        def apply_absences(row):
          try:
            day_num = int(str(row["DATA"]).split(".")[0])
          except Exception:
            day_num = None
          emp_k = normalize_name(row["OSOBA"])
          if (emp_k, day_num) in abs_lookup:
            return abs_lookup[(emp_k, day_num)]
          return row.get("NIEOBECNOŚĆ", "Brak")

        df_temp["NIEOBECNOŚĆ"] = df_temp.apply(apply_absences, axis=1)

      def fill_hours(row):
        absence = str(row.get("NIEOBECNOŚĆ", "Brak")).strip()
        status = str(row.get("DZIEŃ PRACUJĄCY/WOLNY", "")).strip()
        shift_time = str(row.get("CZAS ZMIANY", "")).strip()

        if absence not in ["Brak", "", "None", "nan"]:
          return "NIEOBECNY", "NIEOBECNOŚĆ"
        if status in ["Wolny", "Święto"] or shift_time.lower() == "wolne":
          return "Wolne", "Wolne"
        if "-" in shift_time:
          parts = shift_time.split("-")
          return parts[0].strip(), parts[1].strip()
        return "", ""

      hours_res = df_temp.apply(fill_hours, axis=1)
      df_temp["GODZINA ROZPOCZĘCIA"] = [h[0] for h in hours_res]
      df_temp["GODZINA ZAKOŃCZENIA"] = [h[1] for h in hours_res]

      st.session_state.current_schedule_df = df_temp
      st.success("Naniesiono planowane godziny!")
      st.rerun()

  with col_b2:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
      st.session_state.current_schedule_df.to_excel(
          writer, index=False, sheet_name="Harmonogram"
      )
    buffer.seek(0)
    st.download_button(
        label="📥 Pobierz Harmonogram (Excel)",
        data=buffer,
        file_name=f"Harmonogram_{period_key.replace(' ', '_')}.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        use_container_width=True,
    )

  df_curr = st.session_state.current_schedule_df.copy()
  if "FAKTYCZNIE WEJŚCIE" not in df_curr.columns:
    df_curr["FAKTYCZNIE WEJŚCIE"] = ""
  if "FAKTYCZNIE WYJŚCIE" not in df_curr.columns:
    df_curr["FAKTYCZNIE WYJŚCIE"] = ""

  st.markdown("---")
  st.subheader("⚠️ Weryfikacja Obecności i Brakujących Podpisów")

  missing_signatures = df_curr[
      (df_curr["DZIEŃ PRACUJĄCY/WOLNY"] == "Pracujący")
      & (df_curr["NIEOBECNOŚĆ"].isin(["Brak", "", "None"]))
      & (
          (df_curr["FAKTYCZNIE WEJŚCIE"] == "")
          | (df_curr["FAKTYCZNIE WEJŚCIE"].isna())
      )
  ]

  if not missing_signatures.empty:
    st.markdown(
        f'<div class="alert-box"><strong>Wykryto'
        f' {len(missing_signatures)} brakujących podpisów na listach!</strong></div>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        missing_signatures[[
            "DATA",
            "DZIEŃ TYGODNIA",
            "OSOBA",
            "STANOWISKO",
            "CZAS ZMIANY",
            "NIEOBECNOŚĆ",
        ]],
        use_container_width=True,
    )
  else:
    st.markdown(
        '<div class="success-box"><strong>Wszystko w porządku!</strong>'
        " Wszystkie dni robocze mają pokrycie w podpisach.</div>",
        unsafe_allow_html=True,
    )

  st.markdown("---")
  st.subheader(f"📋 Tabela Harmonogramu ({period_key})")

  dynamic_absence_options = (
      st.session_state.absence_codes_df["Rodzaj nieobecności"]
      .dropna()
      .unique()
      .tolist()
  )
  if "Brak" not in dynamic_absence_options:
    dynamic_absence_options = ["Brak"] + dynamic_absence_options

  edited_df = st.data_editor(
      df_curr,
      column_config={
          "NIEOBECNOŚĆ": st.column_config.SelectboxColumn(
              "NIEOBECNOŚĆ",
              options=dynamic_absence_options,
              required=True,
          ),
          "FAKTYCZNIE WEJŚCIE": st.column_config.TextColumn(
              "FAKTYCZNIE WEJŚCIE"
          ),
          "FAKTYCZNIE WYJŚCIE": st.column_config.TextColumn(
              "FAKTYCZNIE WYJŚCIE"
          ),
          "NADGODZINY (godz.)": st.column_config.NumberColumn(
              "NADGODZINY (godz.)", min_value=0.0, max_value=24.0, step=0.5
          ),
      },
      use_container_width=True,
      num_rows="fixed",
      key="main_schedule_table_editor",
  )

  if isinstance(edited_df, pd.DataFrame):
    st.session_state.current_schedule_df = edited_df

# ==========================================
# ZAKŁADKA 2: KALKULATOR PREMII
# ==========================================
with tab_calc:
  st.header("🧮 Rozliczenie Premiowe i Wynagrodzeń Dodatkowych")

  if st.session_state.current_schedule_df.empty:
    st.warning(
        "Najpierw wygeneruj lub wgraj harmonogram w pierwszej zakładce!"
    )
  else:
    base_salary = st.session_state.base_bonus_salary
