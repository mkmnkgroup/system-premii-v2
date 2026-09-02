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
  """Sprowadza imię i nazwisko do alfabetycznej postaci wielkich liter."""
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
    if raw_text.endswith("```"):
      raw_text = raw_text[:-3]

    return json.loads(raw_text.strip())
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
if "kierownik_bonus_multiplier" not in st.session_state:
  st.session_state.kierownik_bonus_multiplier = 1.35  # NOWY PARAMETR
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
if "pallet_pool" not in st.session_state:
  st.session_state.pallet_pool = 600.0


# ==========================================
# FRAGMENT EDYTORYCZNY: IMPORTER NIEOBECNOŚCI + SKANER ZDJĘĆ
# ==========================================
@st.fragment
def schedule_editor_fragment():
  st.subheader("📥 1. Import Nieobecności z pliku Excel")
  with st.expander("Rozwiń panel importu pliku nieobecności"):
    uploaded_absence_file = st.file_uploader(
        "Wgraj plik Excel z nieobecnościami (np. Nieobecności za 08.2026.xlsx)",
        type=["xlsx", "xls"],
        key="absence_file_uploader",
    )
    if uploaded_absence_file is not None:
      try:
        raw_abs_df = pd.read_excel(uploaded_absence_file, header=None)
        st.success("Plik nieobecności wczytany pomyślnie!")
        if st.button("Przetwarzaj i zaimportuj nieobecności do pamięci"):
          imported_records = []
          abs_map = {}
          for _, row in st.session_state.absence_codes_df.iterrows():
            code = str(row["Oznaczenie"]).strip().upper()
            desc = str(row["Rodzaj nieobecności"]).strip()
            abs_map[code] = desc

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
                    except:
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
          st.success(
              f"Pomyślnie zaimportowano {len(imported_records)} wpisów"
              " nieobecności!"
          )
      except Exception as e:
        st.error(f"Błąd podczas parsowania pliku nieobecności: {e}")

    if not st.session_state.imported_absences_df.empty:
      st.markdown("**Podgląd zaimportowanych nieobecności:**")
      st.dataframe(
          st.session_state.imported_absences_df, use_container_width=True
      )

  st.markdown("---")

  st.subheader("📸 2. Skanowanie List Obecności ze Zdjęć (AI Vision)")
  with st.expander("Rozwiń panel skanowania zdjęć list obecności"):
    api_key_in = st.text_input(
        "Klucz API Google Gemini (wymagany do AI Vision):",
        value=st.session_state.gemini_api_key,
        type="password",
        help=(
            "Wklej swój klucz z Google AI Studio, aby odczytywać zdjęcia list"
            " obecności."
        ),
    )
    st.session_state.gemini_api_key = api_key_in

    uploaded_photos = st.file_uploader(
        "Wgrywaj zdjęcia list obecności z kolejnych dni:",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if uploaded_photos and st.button(
        "🔍 Przeanalizuj zdjęcia i nanieś faktyczne godziny oraz nadgodziny"
    ):
      if not api_key_in:
        st.error(
            "Wprowadź klucz API Google Gemini, aby aktywować moduł wizyjny."
        )
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
              except (ValueError, TypeError):
                ot_val = 0.0

              for idx, row in df_temp.iterrows():
                row_name_norm = normalize_name(row["OSOBA"])
                if row["DATA"] == p_date and row_name_norm == p_name_norm:
                  df_temp.at[idx, "FAKTYCZNIE WEJŚCIE"] = t_in
                  df_temp.at[idx, "FAKTYCZNIE WYJŚCIE"] = t_out
                  df_temp.at[idx, "NADGODZINY (godz.)"] = ot_val
                  total_extracted += 1

        st.session_state.current_schedule_df = df_temp
        st.success(
            f"Pomyślnie dopasowano i zaktualizowano {total_extracted} wpisów ze"
            " zdjęć!"
        )
        st.rerun()

  st.markdown("---")

  if not st.session_state.current_schedule_df.empty:
    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
      if st.button("⏱️ Uzupełnij planowane godziny", use_container_width=True):
        df_temp = st.session_state.current_schedule_df.copy()

        if (
            not st.session_state.imported_absences_df.empty
            and "Pracownik" in st.session_state.imported_absences_df.columns
        ):
          abs_lookup = {}
          for (
              _,
              abs_row,
          ) in st.session_state.imported_absences_df.iterrows():
            emp_k = normalize_name(abs_row["Pracownik"])
            try:
              day_k = int(abs_row["Dzień"])
            except:
              continue
            abs_lookup[(emp_k, day_k)] = abs_row["Opis"]

          def apply_absences(row):
            try:
              day_num = int(str(row["DATA"]).split(".")[0])
            except:
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
        st.success("Pomyślnie naniesiono planowane godziny pracy!")
        st.rerun()

    with col_btn2:
      buffer = io.BytesIO()
      with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        st.session_state.current_schedule_df.to_excel(
            writer, index=False, sheet_name="Harmonogram"
        )
      buffer.seek(0)
      st.download_button(
          label="📥 Pobierz Harmonogram (Excel)",
          data=buffer,
          file_name="Harmonogram.xlsx",
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

    # ==========================================
    # MODUŁ WERYFIKACJI BRAKUJĄCYCH PODPISÓW
    # ==========================================
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
          f' {len(missing_signatures)} nieprawidłowości!</strong><br>Poniżsi'
          " pracownicy mieli zaplanowany dzień pracujący, brak zarejestrowanego"
          " wniosku o nieobecność w pliku Excel oraz brak odczytanego wpisu z"
          " listy obecności na zdjęciu:</div>",
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
      st.success(
          "Wszystkie dni robocze posiadają udokumentowane pokrycie w podpisach"
          " lub zarejestrowanych nieobecnościach."
      )

    st.markdown("---")
    st.subheader("📋 Tabela Harmonogramu i Faktów")

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
                "FAKTYCZNIE WEJŚCIE (ze zdjęcia)"
            ),
            "FAKTYCZNIE WYJŚCIE": st.column_config.TextColumn(
                "FAKTYCZNIE WYJŚCIE (ze zdjęcia)"
            ),
            "NADGODZINY (godz.)": st.column_config.NumberColumn(
                "NADGODZINY (godz.)", min_value=0.0, max_value=24.0, step=0.5
            ),
        },
        use_container_width=True,
        num_rows="fixed",
        key="schedule_editor_main",
    )

    if isinstance(edited_df, pd.DataFrame):
      st.session_state.current_schedule_df = edited_df


# ==========================================
# ZAKŁADKI GŁÓWNE
# ==========================================
tab_gen, tab_calc, tab_dash, tab_history, tab_comp, tab_settings = st.tabs([
    "📋 Generator Harmonogramu",
    "🧮 Kalkulator Premii",
    "📊 Dashboard i Wykresy",
    "📁 Archiwum Historyczne",
    "📈 Porównanie Wyników",
    "⚙️ Ustawienia Systemu",
])

PL_DAYS = {
    0: "poniedziałek",
    1: "wtorek",
    2: "środa",
    3: "czwartek",
    4: "piątek",
    5: "sobota",
    6: "niedziela",
}

# Panel boczny - Ustawienia Okresu
st.sidebar.title("⚙️ Wersja v2")
st.sidebar.header("Ustawienia Okresu")
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

# Panel boczny - Wgrywanie plików z produkcją
st.sidebar.markdown("---")
st.sidebar.header("📁 Wgrywanie Danych z Produkcji")
uploaded_month_file = st.sidebar.file_uploader(
    "Główny plik z produkcją (Sztuki, Pozycje, Waga, Palety):",
    type=["xlsx", "xls"],
)

# ==========================================
# ZAKŁADKA 1: HARMONOGRAM
# ==========================================
with tab_gen:
  if st.sidebar.button("🚀 Generuj harmonogram", type="primary"):
    days_in_month = calendar.monthrange(gen_year, gen_month_idx)[1]
    pl_holidays = holidays.Poland(years=gen_year)

    maciej_early_days = set()
    maciej_emp = None
    for _, row_emp in st.session_state.employees_df.iterrows():
      norm_emp_name = normalize_name(row_emp["OSOBA"])
      if "BORZECKI" in norm_emp_name or "MACIEJ" in norm_emp_name:
        maciej_emp = row_emp
        break

    if maciej_emp is not None:
      for day in range(1, days_in_month + 1):
        date_obj = datetime(gen_year, gen_month_idx, day)
        day_name = PL_DAYS[date_obj.weekday()]
        week_num = date_obj.isocalendar()[1]
        is_holiday = date_obj in pl_holidays

        is_working_day = True
        sys_val = str(maciej_emp["SYSTEM"])
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
                str(maciej_emp["GRUPA"]).replace("GRUPA", "").strip()
            )
          except:
            g_num = 1
          shift_rotation = ((week_num - 1 + (g_num - 1)) % 3) + 1
          if shift_rotation == 1:
            maciej_early_days.add(date_obj.strftime("%d.%m.%Y"))

    schedule_rows = []

    for day in range(1, days_in_month + 1):
      date_obj = datetime(gen_year, gen_month_idx, day)
      date_str = date_obj.strftime("%d.%m.%Y")
      day_name = PL_DAYS[date_obj.weekday()]
      week_num = date_obj.isocalendar()[1]
      is_holiday = date_obj in pl_holidays

      for _, emp in st.session_state.employees_df.iterrows():
        is_working_day = True
        sys_val = str(emp["SYSTEM"])

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
          g_str = str(emp["GRUPA"])
          try:
            g_num = int(g_str.replace("GRUPA", "").strip())
          except:
            g_num = 1

          matched_group_row = st.session_state.groups_df[
              st.session_state.groups_df["Nazwa grupy"]
              .astype(str)
              .str.strip()
              .str.upper()
              == g_str.strip().upper()
          ]
          default_group_time = (
              str(matched_group_row.iloc[0]["Czas pracy"])
              if not matched_group_row.empty
              else "08:00-16:00"
          )

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

        # Dopasowywanie nieobecności
        default_absence = "Brak"
        if (
            not st.session_state.imported_absences_df.empty
            and "Pracownik" in st.session_state.imported_absences_df.columns
        ):
          emp_norm = normalize_name(emp["OSOBA"])
          df_abs = st.session_state.imported_absences_df.copy()
          df_abs["norm_emp"] = df_abs["Pracownik"].apply(normalize_name)
          match_abs = df_abs[
              (df_abs["norm_emp"] == emp_norm) & (df_abs["Dzień"] == day)
          ]
          if not match_abs.empty:
            code_found = match_abs.iloc[0]["Oznaczenie"]
            code_row = st.session_state.absence_codes_df[
                st.session_state.absence_codes_df["Oznaczenie"]
                .astype(str)
                .str.strip()
                .str.upper()
                == str(code_found).strip().upper()
            ]
            if not code_row.empty:
              default_absence = code_row.iloc[0]["Rodzaj nieobecności"]

        schedule_rows.append({
            "DATA": date_str,
            "DZIEŃ TYGODNIA": day_name,
            "OSOBA": emp["OSOBA"],
            "STANOWISKO": emp["STANOWISKO"],
            "ZMIANA": shift_val if not is_holiday else "Święto",
            "CZAS ZMIANY": czas_zmiany,
            "DZIEŃ PRACUJĄCY/WOLNY": status_dzien,
            "GODZINA ROZPOCZĘCIA": default_start_end,
            "GODZINA ZAKOŃCZENIA": default_start_end,
            "FAKTYCZNIE WEJŚCIE": "",
            "FAKTYCZNIE WYJŚCIE": "",
            "NIEOBECNOŚĆ": default_absence,
            "NADGODZINY (godz.)": 0.0,
        })

    st.session_state.current_schedule_df = pd.DataFrame(schedule_rows)
    st.success(f"Wygenerowano harmonogram v2 na {period_key}!")

  schedule_editor_fragment()

# ==========================================
# ZAKŁADKA 2: KALKULATOR PREMII
# ==========================================
with tab_calc:
  st.header("🧮 Rozliczenie Premiowe i Wynagrodzeń Dodatkowych")

  if st.session_state.current_schedule_df.empty:
    st.warning("Najpierw wygeneruj harmonogram w pierwszej zakładce!")
  else:
    base_salary = st.session_state.base_bonus_salary
    step_bonus_pct = 0.04

    w_pcs_frac = st.session_state.w_pcs / 100.0
    w_lines_frac = st.session_state.w_lines / 100.0
    w_weight_frac = st.session_state.w_weight / 100.0

    prod_df = pd.DataFrame()
    if uploaded_month_file is not None:
      ext = uploaded_month_file.name.split(".")[-1].lower()
      prod_df = pd.read_excel(
          uploaded_month_file,
          engine="xlrd" if ext == "xls" else "openpyxl",
      )

    df_sched = st.session_state.current_schedule_df
    cur_pcs, cur_lines, cur_weight, cur_pallets = 0.0, 0.0, 0.0, 0.0

    if not prod_df.empty:
      cur_pcs = get_col_sum_flexible(prod_df, ["Sztuki", "sztuka"])
      cur_lines = get_col_sum_flexible(prod_df, ["pozycje", "Pozycje"])
      cur_weight = get_col_sum_flexible(
          prod_df, ["Waga łączna", "Waga laczna", "Waga"]
      )
      cur_pallets = get_col_sum_flexible(
          prod_df,
          ["Palety", "Liczba palet", "Załadunki", "Paleciaki", "Paleta"],
      )

    dev_pcs = (
        (cur_pcs - st.session_state.avg_pcs_12m) / st.session_state.avg_pcs_12m
        if st.session_state.avg_pcs_12m > 0
        else 0.0
    )
    dev_lines = (
        (cur_lines - st.session_state.avg_lines_12m)
        / st.session_state.avg_lines_12m
        if st.session_state.avg_lines_12m > 0
        else 0.0
    )
    dev_weight = (
        (cur_weight - st.session_state.avg_weight_12m)
        / st.session_state.avg_weight_12m
        if st.session_state.avg_weight_12m > 0
        else 0.0
    )

    indicator = (
        dev_pcs * w_pcs_frac
        + dev_lines * w_lines_frac
        + dev_weight * w_weight_frac
    )
    bonus_rate = indicator * (step_bonus_pct / 0.10) if indicator > 0 else 0.0
    max_bonus_per_emp = base_salary * bonus_rate

    st.info(
        f"💡 Podstawa premiowa wynosi: **{base_salary:,.2f} zł netto** | Mnożnik"
        " dla Kierownika:"
        f" **{st.session_state.kierownik_bonus_multiplier:.2f}x**"
        .replace(",", " ")
        .replace(".", ",")
    )

    st.markdown("---")
    st.subheader("📌 1. Wyniki Produkcyjne i Wskaźnik Wydajności")
    comparison_data = [
        {
            "Parametr produkcyjny": "Pozycje",
            "Wartość w miesiącu": f"{cur_lines:,.2f}".replace(",", " ").replace(
                ".", ","
            ),
            "Średnia roczna (baza)": (
                f"{st.session_state.avg_lines_12m:,.2f}".replace(
                    ",", " "
                ).replace(".", ",")
            ),
            "Różnica ilościowa": (
                f"{(cur_lines - st.session_state.avg_lines_12m):+,.2f}".replace(
                    ",", " "
                ).replace(".", ",")
            ),
            "Odchylenie procentowe (%)": f"{dev_lines * 100:+.2f}%".replace(
                ".", ","
            ),
            "Waga wskaźnika": f"{st.session_state.w_lines:.2f}%".replace(
                ".", ","
            ),
        },
        {
            "Parametr produkcyjny": "Sztuki",
            "Wartość w miesiącu": f"{cur_pcs:,.2f}".replace(",", " ").replace(
                ".", ","
            ),
            "Średnia roczna (baza)": (
                f"{st.session_state.avg_pcs_12m:,.2f}".replace(
                    ",", " "
                ).replace(".", ",")
            ),
            "Różnica ilościowa": (
                f"{(cur_pcs - st.session_state.avg_pcs_12m):+,.2f}".replace(
                    ",", " "
                ).replace(".", ",")
            ),
            "Odchylenie procentowe (%)": f"{dev_pcs * 100:+.2f}%".replace(
                ".", ","
            ),
            "Waga wskaźnika": f"{st.session_state.w_pcs:.2f}%".replace(
                ".", ","
            ),
        },
        {
            "Parametr produkcyjny": "Waga towaru",
            "Wartość w miesiącu": f"{cur_weight:,.2f} kg".replace(
                ",", " "
            ).replace(".", ","),
            "Średnia roczna (baza)": (
                f"{st.session_state.avg_weight_12m:,.2f} kg".replace(
                    ",", " "
                ).replace(".", ",")
            ),
            "Różnica ilościowa": (
                f"{(cur_weight - st.session_state.avg_weight_12m):+,.2f}"
                " kg".replace(",", " ").replace(".", ",")
            ),
            "Odchylenie procentowe (%)": f"{dev_weight * 100:+.2f}%".replace(
                ".", ","
            ),
            "Waga wskaźnika": f"{st.session_state.w_weight:.2f}%".replace(
                ".", ","
            ),
        },
    ]
    st.dataframe(
        pd.DataFrame(comparison_data),
        use_container_width=True,
        hide_index=True,
    )

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
      st.metric(
          label="Zbiorczy Wskaźnik Wydajności",
          value=f"{indicator * 100:+.2f}%".replace(".", ","),
      )
    with col_m2:
      st.metric(
          label="Należna Stawka Premii (%)",
          value=f"{bonus_rate * 100:.2f}%".replace(".", ","),
      )
    with col_m3:
      st.metric(
          label="Maks. Premia Bazowa (Magazynier)",
          value=f"{max_bonus_per_emp:,.2f} zł".replace(",", " ").replace(
              ".", ","
          ),
      )

    st.markdown("---")
    st.subheader("👥 2. Szczegółowe Rozliczenie Pracowników")

    emp_summary = []
    unique_emps = (
        st.session_state.employees_df["OSOBA"].dropna().unique().tolist()
    )

    for emp_name in unique_emps:
      emp_df = df_sched[
          df_sched["OSOBA"].str.strip().str.upper()
          == str(emp_name).strip().upper()
      ]
      emp_info = st.session_state.employees_df[
          st.session_state.employees_df["OSOBA"] == emp_name
      ].iloc[0]

      position = emp_info.get("STANOWISKO", "MAGAZYNIER")
      func = emp_info.get("FUNKCJA", "")

      # Liczba dni przepracowanych i nieobecności
      days_worked = len(
          emp_df[
              (emp_df["DZIEŃ PRACUJĄCY/WOLNY"] == "Pracujący")
              & (emp_df["NIEOBECNOŚĆ"].isin(["Brak", "", "None"]))
          ]
      )
      absent_days = len(
          emp_df[~emp_df["NIEOBECNOŚĆ"].isin(["Brak", "", "None"])]
      )
      total_ot = emp_df["NADGODZINY (godz.)"].sum()

      # Wyliczenie stawki nadgodzinowej zależnej od stanowiska
      ot_rate = st.session_state.ot_magazynier
      if "KIEROWNIK" in str(position).upper():
        ot_rate = st.session_state.ot_kierownik
      elif "BRYGADZISTA" in str(position).upper():
        ot_rate = st.session_state.ot_brygadzista

      ot_pay = total_ot * ot_rate

      # Wyliczenie proporcjonalnej premii bazowej
      scheduled_work_days = len(
          emp_df[emp_df["DZIEŃ PRACUJĄCY/WOLNY"] == "Pracujący"]
      )
      attendance_ratio = (
          (days_worked / scheduled_work_days)
          if scheduled_work_days > 0
          else 0.0
      )
      calculated_bonus = max_bonus_per_emp * attendance_ratio

      # ==========================================
      # LOGIKA MNOŻNIKA DLA KIEROWNIKA MAGAZYNU
      # ==========================================
      is_kierownik = (
          "KIEROWNIK" in str(position).upper()
          or "KIEROWNIK" in str(func).upper()
      )
      if is_kierownik:
        calculated_bonus *= st.session_state.kierownik_bonus_multiplier

      # Dopasowanie premii specjalnych
      spec_bonus_val = 0.0
      if not st.session_state.special_bonuses_df.empty:
        matched_spec = st.session_state.special_bonuses_df[
            st.session_state.special_bonuses_df["Pracownik"].apply(
                normalize_name
            )
            == normalize_name(emp_name)
        ]
        spec_bonus_val = matched_spec["Kwota netto premii"].sum()

      total_payout = calculated_bonus + ot_pay + spec_bonus_val

      emp_summary.append({
          "Pracownik": emp_name,
          "Stanowisko": position,
          "Dni przepracowane": days_worked,
          "Dni nieobecności": absent_days,
          "Nadgodziny (godz.)": total_ot,
          "Wynagrodzenie za nadgodziny (zł)": round(ot_pay, 2),
          "Wyliczona premia (zł)": round(calculated_bonus, 2),
          "Premie specjalne (zł)": round(spec_bonus_val, 2),
          "ŁĄCZNA PREMIA / DODATKI (zł)": round(total_payout, 2),
      })

    summary_df = pd.DataFrame(emp_summary)
    st.dataframe(summary_df, use_container_width=True)

    # Zapis do archiwum
    if st.button("💾 Zapisz rozliczenie do Archiwum Historycznego"):
      st.session_state.history_v2[period_key] = {
          "summary": summary_df,
          "schedule": df_sched,
          "metrics": {
              "pcs": cur_pcs,
              "lines": cur_lines,
              "weight": cur_weight,
              "indicator": indicator,
              "bonus_rate": bonus_rate,
          },
      }
      save_archive(st.session_state.history_v2)
      st.success(f"Pomyślnie zarchiwizowano rozliczenie za okres {period_key}!")

# ==========================================
# ZAKŁADKA 3: DASHBOARD I WYKRESY
# ==========================================
with tab_dash:
  st.header("📊 Dashboard Analityczny")
  if period_key in st.session_state.history_v2:
    data_hist = st.session_state.history_v2[period_key]
    sum_df = data_hist["summary"]

    col_d1, col_d2 = st.columns(2)
    with col_d1:
      fig_payout = px.bar(
          sum_df,
          x="Pracownik",
          y="ŁĄCZNA PREMIA / DODATKI (zł)",
          title="Łączne wypłaty dodatkowe wg pracowników",
          color="Stanowisko",
          text_auto=True,
      )
      st.plotly_chart(fig_payout, use_container_width=True)

    with col_d2:
      fig_ot = px.pie(
          sum_df,
          names="Pracownik",
          values="Nadgodziny (godz.)",
          title="Udział nadgodzin w zespole",
      )
      st.plotly_chart(fig_ot, use_container_width=True)
  else:
    st.info(
        "Zapisz rozliczenie do archiwum w zakładce Kalkulator Premii, aby"
        " wyświetlić wykresy dla tego okresu."
    )

# ==========================================
# ZAKŁADKA 4: ARCHIWUM HISTORYCZNE
# ==========================================
with tab_history:
  st.header("📁 Archiwum Zapisanych Rozliczeń")
  if st.session_state.history_v2:
    selected_period = st.selectbox(
        "Wybierz okres z archiwum:", list(st.session_state.history_v2.keys())
    )
    if selected_period:
      st.subheader(f"Rozliczenie dla: {selected_period}")
      st.dataframe(
          st.session_state.history_v2[selected_period]["summary"],
          use_container_width=True,
      )
  else:
    st.info("Brak zapisanych okresów w archiwum.")

# ==========================================
# ZAKŁADKA 5: PORÓWNANIE WYNIKÓW
# ==========================================
with tab_comp:
  st.header("📈 Porównanie Okresów Historycznych")
  if len(st.session_state.history_v2) >= 2:
    periods = list(st.session_state.history_v2.keys())
    p1, p2 = st.columns(2)
    with p1:
      period_a = st.selectbox("Wybierz pierwszy okres:", periods, index=0)
    with p2:
      period_b = st.selectbox(
          "Wybierz drugi okres:", periods, index=min(1, len(periods) - 1)
      )

    if period_a and period_b:
      df_a = st.session_state.history_v2[period_a]["summary"]
      df_b = st.session_state.history_v2[period_b]["summary"]

      comp_df = pd.merge(
          df_a[["Pracownik", "ŁĄCZNA PREMIA / DODATKI (zł)"]],
          df_b[["Pracownik", "ŁĄCZNA PREMIA / DODATKI (zł)"]],
          on="Pracownik",
          suffixes=(f" ({period_a})", f" ({period_b})"),
      )
      st.dataframe(comp_df, use_container_width=True)
  else:
    st.info(
        "Wymagane są co najmniej 2 zapisane okresy w archiwum, aby wykonać"
        " porównanie."
    )

# ==========================================
# ZAKŁADKA 6: USTAWIENIA SYSTEMU
# ==========================================
with tab_settings:
  st.header("⚙️ Ustawienia Parametrów i Stałych Systemowych")

  col_set1, col_set2 = st.columns(2)

  with col_set1:
    st.subheader("💰 Podstawa Premiowa i Mnożniki")
    st.session_state.base_bonus_salary = st.number_input(
        "Podstawa premii (zł netto):",
        value=float(st.session_state.base_bonus_salary),
        step=100.0,
    )

    # DEDYKOWANE POLE USTAWIEŃ MNOŻNIKA DLA KIEROWNIKA
    st.session_state.kierownik_bonus_multiplier = st.number_input(
        "Mnożnik premii dla Kierownika Magazynu:",
        value=float(st.session_state.kierownik_bonus_multiplier),
        step=0.05,
        format="%.2f",
        help=(
            "Premia wyliczona dla Kierownika zostanie pomnożona przez ten"
            " wskaźnik (domyślnie 1.35)."
        ),
    )

    st.subheader("⏱️ Stawki za Nadgodziny (zł/godz.)")
    st.session_state.ot_kierownik = st.number_input(
        "Kierownik:", value=float(st.session_state.ot_kierownik), step=5.0
    )
    st.session_state.ot_brygadzista = st.number_input(
        "Brygadzista:", value=float(st.session_state.ot_brygadzista), step=5.0
    )
    st.session_state.ot_magazynier = st.number_input(
        "Magazynier:", value=float(st.session_state.ot_magazynier), step=5.0
    )

  with col_set2:
    st.subheader("📊 Baza Roczna i Wagi Wskaźników")
    st.session_state.avg_pcs_12m = st.number_input(
        "Średnia roczna - Sztuki:",
        value=float(st.session_state.avg_pcs_12m),
        step=1000.0,
    )
    st.session_state.w_pcs = st.number_input(
        "Waga - Sztuki (%):", value=float(st.session_state.w_pcs), step=1.0
    )

    st.session_state.avg_lines_12m = st.number_input(
        "Średnia roczna - Pozycje:",
        value=float(st.session_state.avg_lines_12m),
        step=500.0,
    )
    st.session_state.w_lines = st.number_input(
        "Waga - Pozycje (%):", value=float(st.session_state.w_lines), step=1.0
    )

    st.session_state.avg_weight_12m = st.number_input(
        "Średnia roczna - Waga (kg):",
        value=float(st.session_state.avg_weight_12m),
        step=1000.0,
    )
    st.session_state.w_weight = st.number_input(
        "Waga - Waga (%):", value=float(st.session_state.w_weight), step=1.0
    )

  st.markdown("---")
  st.subheader("👥 Lista Pracowników i Zespołów")
  edited_employees = st.data_editor(
      st.session_state.employees_df,
      use_container_width=True,
      num_rows="dynamic",
      key="settings_employees_editor",
  )
  if isinstance(edited_employees, pd.DataFrame):
    st.session_state.employees_df = edited_employees
