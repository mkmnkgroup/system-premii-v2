import calendar
from datetime import datetime
import io
import os
import pickle
from fpdf import FPDF
import holidays
import pandas as pd
import plotly.express as px
import streamlit as st
import tempfile

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

# Inicjalizacja stanów konfiguracyjnych
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
if "pallet_pool" not in st.session_state:
  st.session_state.pallet_pool = 600.0


# ==========================================
# FRAGMENT EDYTORYCZNY Z IMPORTEM NIEBECNOŚCI I AUTO-UZUPEŁNIANIEM
# ==========================================
@st.fragment
def schedule_editor_fragment():
  st.subheader("📥 Import Nieobecności z pliku Excel (Opcjonalnie)")
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
            emp_name_clean = str(emp_name).strip().upper()

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

  if not st.session_state.current_schedule_df.empty:
    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
      if st.button("⏱️ Uzupełnij godziny pracy", use_container_width=True):
        df_temp = st.session_state.current_schedule_df.copy()

        # 1. Nanieś importowane nieobecności
        if (
            not st.session_state.imported_absences_df.empty
            and "Pracownik" in st.session_state.imported_absences_df.columns
        ):
          abs_lookup = {}
          for (
              _,
              abs_row,
          ) in st.session_state.imported_absences_df.iterrows():
            emp_k = str(abs_row["Pracownik"]).strip().upper()
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
            emp_k = str(row["OSOBA"]).strip().upper()

            if (emp_k, day_num) in abs_lookup:
              return abs_lookup[(emp_k, day_num)]
            return row.get("NIEOBECNOŚĆ", "Brak")

          df_temp["NIEOBECNOŚĆ"] = df_temp.apply(apply_absences, axis=1)

        # 2. Uzupełnij godziny pracy w zależności od nieobecności i dni wolnych
        def fill_hours(row):
          absence = str(row.get("NIEOBECNOŚĆ", "Brak")).strip()
          status = str(row.get("DZIEŃ PRACUJĄCY/WOLNY", "")).strip()
          shift_time = str(row.get("CZAS ZMIANY", "")).strip()

          if absence not in ["Brak", "", "None", "nan"]:
            return "NIEOBECNY", "NIEOBECNY"

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
        st.success(
            "Pomyślnie naniesiono nieobecności oraz uzupełniono godziny pracy!"
        )
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

    dynamic_absence_options = (
        st.session_state.absence_codes_df["Rodzaj nieobecności"]
        .dropna()
        .unique()
        .tolist()
    )
    if "Brak" not in dynamic_absence_options:
      dynamic_absence_options = ["Brak"] + dynamic_absence_options

    def on_editor_change():
      if "schedule_editor" in st.session_state:
        edited_data = st.session_state["schedule_editor"]
        if isinstance(edited_data, dict):
          edited_df = st.session_state.current_schedule_df.copy()

          if "edited_rows" in edited_data:
            for row_idx, changes in edited_data["edited_rows"].items():
              for col_name, new_val in changes.items():
                edited_df.at[int(row_idx), col_name] = new_val

          mask_absent = ~edited_df["NIEOBECNOŚĆ"].isin(["Brak", ""])
          edited_df.loc[mask_absent, "GODZINA ROZPOCZĘCIA"] = "NIEOBECNY"
          edited_df.loc[mask_absent, "GODZINA ZAKOŃCZENIA"] = "NIEOBECNY"

          mask_free = edited_df["DZIEŃ PRACUJĄCY/WOLNY"].isin(
              ["Wolny", "Święto"]
          ) | (
              edited_df["CZAS ZMIANY"].astype(str).str.lower() == "wolne"
          )
          edited_df.loc[mask_free, "GODZINA ROZPOCZĘCIA"] = "Wolne"
          edited_df.loc[mask_free, "GODZINA ZAKOŃCZENIA"] = "Wolne"

          st.session_state.current_schedule_df = edited_df

    edited_df = st.data_editor(
        st.session_state.current_schedule_df,
        column_config={
            "NIEOBECNOŚĆ": st.column_config.SelectboxColumn(
                "NIEOBECNOŚĆ",
                options=dynamic_absence_options,
                required=True,
                help="Wybierz powód nieobecności",
            )
        },
        use_container_width=True,
        num_rows="fixed",
        key="schedule_editor",
        on_change=on_editor_change,
    )

    if isinstance(edited_df, pd.DataFrame):
      mask_absent = ~edited_df["NIEOBECNOŚĆ"].isin(["Brak", ""])
      edited_df.loc[mask_absent, "GODZINA ROZPOCZĘCIA"] = "NIEOBECNY"
      edited_df.loc[mask_absent, "GODZINA ZAKOŃCZENIA"] = "NIEOBECNY"

      mask_free = edited_df["DZIEŃ PRACUJĄCY/WOLNY"].isin(
          ["Wolny", "Święto"]
      ) | (edited_df["CZAS ZMIANY"].astype(str).str.lower() == "wolne")
      edited_df.loc[mask_free, "GODZINA ROZPOCZĘCIA"] = "Wolne"
      edited_df.loc[mask_free, "GODZINA ZAKOŃCZENIA"] = "Wolne"

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
    "Główny plik z produkcją (Sztuki, Pozycje przyjęte, Waga):",
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
      if (
          "BORZĘCKI" in str(row_emp["OSOBA"]).upper()
          or "MACIEJ" in str(row_emp["OSOBA"]).upper()
      ):
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

        # Nieobecność z pliku
        default_absence = "Brak"
        if (
            not st.session_state.imported_absences_df.empty
            and "Pracownik" in st.session_state.imported_absences_df.columns
        ):
          emp_upper = str(emp["OSOBA"]).strip().upper()
          match_abs = st.session_state.imported_absences_df[
              (
                  st.session_state.imported_absences_df["Pracownik"]
                  .astype(str)
                  .str.strip()
                  .str.upper()
                  == emp_upper
              )
              & (st.session_state.imported_absences_df["Dzień"] == day)
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
  st.header(
      "🧮 Kalkulator Premii v2 (Ciągłe wyliczanie proporcjonalne - 4% za każde"
      " 10%)"
  )

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
    cur_pcs, cur_lines, cur_weight = 0.0, 0.0, 0.0

    if not prod_df.empty:
      cur_pcs = get_col_sum_flexible(prod_df, ["Sztuki", "sztuka"])
      cur_lines = get_col_sum_flexible(prod_df, ["pozycje", "Pozycje"])
      cur_weight = get_col_sum_flexible(
          prod_df, ["Waga łączna", "Waga laczna", "Waga"]
      )

    dev_pcs = (
        (cur_pcs - st.session_state.avg_pcs_12m)
        / st.session_state.avg_pcs_12m
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
    bonus_rate = (
        indicator * (step_bonus_pct / 0.10) if indicator > 0 else 0.0
    )
    max_bonus_per_emp = base_salary * bonus_rate

    st.info(
        f"💡 Aktualna podstawa do wyliczenia premii wynosi: **{base_salary:,.2f}"
        " zł netto** (możesz ją zmodyfikować w zakładce *Ustawienia*)."
        .replace(",", " ")
        .replace(".", ",")
    )

    st.markdown("---")
    st.subheader("📌 Wyniki Bieżącego Miesiąca vs Średnia Roczna")
    comparison_data = [
        {
            "Parametr produkcyjny": "Pozycje",
            "Wartość w miesiącu": f"{cur_lines:,.2f}"
            .replace(",", " ")
            .replace(".", ","),
            "Średnia roczna (baza)": f"{st.session_state.avg_lines_12m:,.2f}"
            .replace(",", " ")
            .replace(".", ","),
            "Różnica ilościowa": f"{(cur_lines - st.session_state.avg_lines_12m):+,.2f}"
            .replace(",", " ")
            .replace(".", ","),
            "Odchylenie procentowe (%)": f"{dev_lines * 100:+.2f}%".replace(
                ".", ","
            ),
            "Waga wskaźnika": f"{st.session_state.w_lines:.2f}%".replace(
                ".", ","
            ),
        },
        {
            "Parametr produkcyjny": "Sztuki",
            "Wartość w miesiącu": f"{cur_pcs:,.2f}"
            .replace(",", " ")
            .replace(".", ","),
            "Średnia roczna (baza)": f"{st.session_state.avg_pcs_12m:,.2f}"
            .replace(",", " ")
            .replace(".", ","),
            "Różnica ilościowa": f"{(cur_pcs - st.session_state.avg_pcs_12m):+,.2f}"
            .replace(",", " ")
            .replace(".", ","),
            "Odchylenie procentowe (%)": f"{dev_pcs * 100:+.2f}%".replace(
                ".", ","
            ),
            "Waga wskaźnika": f"{st.session_state.w_pcs:.2f}%".replace(
                ".", ","
            ),
        },
        {
            "Parametr produkcyjny": "Waga towaru",
            "Wartość w miesiącu": f"{cur_weight:,.2f} kg"
            .replace(",", " ")
            .replace(".", ","),
            "Średnia roczna (baza)": f"{st.session_state.avg_weight_12m:,.2f} kg"
            .replace(",", " ")
            .replace(".", ","),
            "Różnica ilościowa": f"{(cur_weight - st.session_state.avg_weight_12m):+,.2f} kg"
            .replace(",", " ")
            .replace(".", ","),
            "Odchylenie procentowe (%)": f"{dev_weight * 100:+.2f}%".replace(
                ".", ","
            ),
            "Waga wskaźnika": f"{st.session_state.w_weight:.2f}%".replace(
                ".", ","
            ),
        },
    ]
    st.dataframe(
        pd.DataFrame(comparison_data), use_container_width=True, hide_index=True
    )

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Wskaźnik Wykonania Działu", f"{indicator*100:.2f}%")
    col_m2.metric("Stawka Premii (proporcjonalna)", f"{bonus_rate*100:.2f}%")
    col_m3.metric(
        "Faktyczna Premia na pracownika", f"{max_bonus_per_emp:.2f} PLN"
    )
    st.markdown("---")

    summary_list = []
    for name, group in df_sched.groupby("OSOBA"):
      dni_nieobecne = 0
      for _, row in group.iterrows():
        if row.get("DZIEŃ PRACUJĄCY/WOLNY") == "Pracujący" and row.get(
            "NIEOBECNOŚĆ", "Brak"
        ) not in ["Brak", ""]:
          dni_nieobecne += 1

      summary_list.append({
          "Pracownik": name,
          "Stanowisko": group["STANOWISKO"].iloc[0],
          "Liczba nieobecności": dni_nieobecne,
          "Premia netto (PLN)": max_bonus_per_emp,
      })

    calc_df = pd.DataFrame(summary_list)
    st.session_state.current_calc_df = calc_df
    st.session_state.current_indicator = indicator

    st.subheader("Rozliczenie Premiowe Pracowników (v2)")
    st.dataframe(
        calc_df.style.format({"Premia netto (PLN)": "{:.2f} zł"}),
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("⏱️ Zestawienie Nadgodzin Pracowników (Dzień po Dniu)")

    overtime_pivot = pd.DataFrame()
    if not df_sched.empty and "NADGODZINY (godz.)" in df_sched.columns:
      overtime_pivot = df_sched.pivot_table(
          index=["OSOBA", "STANOWISKO"],
          columns="DATA",
          values="NADGODZINY (godz.)",
          fill_value=0.0,
      ).reset_index()

      date_cols = [
          c for c in overtime_pivot.columns if c not in ["OSOBA", "STANOWISKO"]
      ]
      for col in date_cols:
        overtime_pivot[col] = (
            pd.to_numeric(overtime_pivot[col], errors="coerce")
            .fillna(0.0)
            .round(1)
        )

      overtime_pivot["Suma Nadgodzin (h)"] = overtime_pivot[date_cols].sum(
          axis=1
      ).round(1)

      def get_ot_rate(pos):
        p = str(pos).strip().upper()
        if "KIEROWNIK" in p:
          return st.session_state.ot_kierownik
        elif "BRYGADZISTA" in p:
          return st.session_state.ot_brygadzista
        else:
          return st.session_state.ot_magazynier

      overtime_pivot["Kwota za nadgodziny (PLN)"] = (
          overtime_pivot["Suma Nadgodzin (h)"]
          * overtime_pivot["STANOWISKO"].apply(get_ot_rate)
      )

      cols_order = [
          "OSOBA",
          "STANOWISKO",
          "Suma Nadgodzin (h)",
          "Kwota za nadgodziny (PLN)",
      ] + date_cols
      overtime_pivot = overtime_pivot[cols_order]

      format_dict = {col: "{:.1f} h" for col in date_cols}
      format_dict["Suma Nadgodzin (h)"] = "{:.1f} h"
      format_dict["Kwota za nadgodziny (PLN)"] = "{:.2f} zł"

      st.dataframe(
          overtime_pivot.style.format(format_dict), use_container_width=True
      )

# ==========================================
# ZAKŁADKA 3: DASHBOARD I WYKRESY
# ==========================================
with tab_dash:
  st.header("📊 Dashboard Analityczny")
  if (
      "current_calc_df" in st.session_state
      and not st.session_state.current_calc_df.empty
  ):
    df_c = st.session_state.current_calc_df
    fig = px.bar(
        df_c,
        x="Pracownik",
        y="Premia netto (PLN)",
        color="Stanowisko",
        title=f"Wypłaty premii netto dla pracowników – {period_key}",
        text_auto=".2f",
    )
    st.plotly_chart(fig, use_container_width=True)
  else:
    st.info(
        "Brak danych do wyświetlenia wykresów. Przejdź do kalkulatora premii."
    )

# ==========================================
# ZAKŁADKA 4: ARCHIWUM HISTORYCZNE
# ==========================================
with tab_history:
  st.header("📁 Archiwum Historyczne Rozliczeń")
  if st.session_state.history_v2:
    selected_archive = st.selectbox(
        "Wybierz okres z archiwum:", list(st.session_state.history_v2.keys())
    )
    if selected_archive:
      st.dataframe(
          st.session_state.history_v2[selected_archive], use_container_width=True
      )
  else:
    st.info("Brak zapisanych danych w archiwum.")

# ==========================================
# ZAKŁADKA 5: PORÓWNANIE WYNIKÓW
# ==========================================
with tab_comp:
  st.header("📈 Porównanie Wyników Miesięcznych")
  if st.session_state.history_v2:
    hist_keys = list(st.session_state.history_v2.keys())
    st.write(f"Dostępne okresy w archiwum: {', '.join(hist_keys)}")
  else:
    st.info(
        "Zapisz dane bieżącego miesiąca do archiwum, aby móc je porównywać."
    )

# ==========================================
# ZAKŁADKA 6: USTAWIENIA SYSTEMU
# ==========================================
with tab_settings:
  st.header("⚙️ Pełna Konfiguracja Systemu i Parametrów")
  st.caption(
      "W tym miejscu możesz dostosować wszystkie moduły, stawki, składy"
      " osobowe oraz definicje używane w całym systemie."
  )

  sub_t1, sub_t2, sub_t3, sub_t4, sub_t5, sub_t6 = st.tabs([
      "🔤 Oznaczenia Nieobecności",
      "👥 Skład Osobowy i Systemy",
      "🕒 Grafik i Zmiany Grup",
      "💰 Stawki Nadgodzin i Palety",
      "🎯 Parametry Premii i Wagi",
      "🎁 Premie Specjalne",
  ])

  # Sub-tab 1: Oznaczenia Nieobecności
  with sub_t1:
    st.subheader("Słownik Oznaczeń Nieobecności")
    edited_codes = st.data_editor(
        st.session_state.absence_codes_df,
        num_rows="dynamic",
        use_container_width=True,
        key="set_absence_editor",
    )
    if st.button("💾 Zapisz Słownik Nieobecności", key="btn_save_codes"):
      st.session_state.absence_codes_df = edited_codes
      st.success("Zapisano nowy słownik oznaczeń nieobecności!")

  # Sub-tab 2: Skład Osobowy
  with sub_t2:
    st.subheader("Lista Pracowników i Przypisanie do Grup")
    edited_emp = st.data_editor(
        st.session_state.employees_df,
        num_rows="dynamic",
        use_container_width=True,
        key="set_emp_editor",
    )
    if st.button("💾 Zapisz Skład Osobowy", key="btn_save_emp"):
      st.session_state.employees_df = edited_emp
      st.success("Lista pracowników została pomyślnie zaktualizowana!")

  # Sub-tab 3: Grafik Grup
  with sub_t3:
    st.subheader("Definicje Zmian i Czasu Pracy Grup")
    edited_groups = st.data_editor(
        st.session_state.groups_df,
        num_rows="dynamic",
        use_container_width=True,
        key="set_groups_editor",
    )
    if st.button("💾 Zapisz Konfigurację Grup", key="btn_save_groups"):
      st.session_state.groups_df = edited_groups
      st.success("Zapisano ustawienia czasu pracy grup!")

  # Sub-tab 4: Stawki Nadgodzin i Palet
  with sub_t4:
    st.subheader("Stawki Finansowe (Nadgodziny i Załadunki/Palety)")
    col_ot1, col_ot2 = st.columns(2)
    with col_ot1:
      st.markdown("**Stawki godzinowe za nadgodziny (zł/h):**")
      st.session_state.ot_kierownik = st.number_input(
          "Stawka - Kierownik (zł/h):",
          value=float(st.session_state.ot_kierownik),
          step=1.0,
      )
      st.session_state.ot_brygadzista = st.number_input(
          "Stawka - Brygadzista (zł/h):",
          value=float(st.session_state.ot_brygadzista),
          step=1.0,
      )
      st.session_state.ot_magazynier = st.number_input(
          "Stawka - Magazynier (zł/h):",
          value=float(st.session_state.ot_magazynier),
          step=1.0,
      )
    with col_ot2:
      st.markdown("**Stawki załadunkowe / Palety:**")
      st.session_state.rate_pallet = st.number_input(
          "Stawka za paletę / załadunek (zł):",
          value=float(st.session_state.rate_pallet),
          step=0.5,
      )
      st.session_state.pallet_pool = st.number_input(
          "Miesięczny budżet / pula paletowa (zł):",
          value=float(st.session_state.pallet_pool),
          step=50.0,
      )
    if st.button("💾 Zapisz Stawki Finansowe", key="btn_save_financial_rates"):
      st.success("Stawki za nadgodziny oraz palety zostały zaktualizowane!")

  # Sub-tab 5: Wskaźniki i Wagi
  with sub_t5:
    st.subheader("Parametry Produkcyjne, Wagi i Podstawa Premii")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
      st.markdown("**Baza Odniesienia (Średnie 12-miesięczne):**")
      st.session_state.base_bonus_salary = st.number_input(
          "Podstawa do wyliczenia premii (zł netto):",
          value=float(st.session_state.base_bonus_salary),
          step=100.0,
      )
      st.session_state.avg_pcs_12m = st.number_input(
          "Średnia roczna - Sztuki:",
          value=float(st.session_state.avg_pcs_12m),
          step=100.0,
      )
      st.session_state.avg_lines_12m = st.number_input(
          "Średnia roczna - Pozycje:",
          value=float(st.session_state.avg_lines_12m),
          step=100.0,
      )
      st.session_state.avg_weight_12m = st.number_input(
          "Średnia roczna - Waga towaru (kg):",
          value=float(st.session_state.avg_weight_12m),
          step=100.0,
      )
    with col_p2:
      st.markdown("**Wagi Poszczególnych Wskaźników (%):**")
      st.session_state.w_pcs = st.number_input(
          "Waga wskaźnika Sztuki (%):",
          value=float(st.session_state.w_pcs),
          step=0.1,
      )
      st.session_state.w_lines = st.number_input(
          "Waga wskaźnika Pozycje (%):",
          value=float(st.session_state.w_lines),
          step=0.1,
      )
      st.session_state.w_weight = st.number_input(
          "Waga wskaźnika Waga (%):",
          value=float(st.session_state.w_weight),
          step=0.1,
      )

      total_w = (
          st.session_state.w_pcs
          + st.session_state.w_lines
          + st.session_state.w_weight
      )
      if round(total_w, 2) != 100.0:
        st.warning(
            f"⚠️ Suma wag wynosi obecnie **{total_w:.2f}%** (zalecane: 100%)."
        )
      else:
        st.success("Suma wag wynosi dokładnie 100%.")

    if st.button("💾 Zapisz Parametry Produkcyjne", key="btn_save_prod_params"):
      st.success("Parametry produkcyjne i wagi wskaźników zostały zapisane!")

  # Sub-tab 6: Premie Specjalne
  with sub_t6:
    st.subheader("Zarządzanie Premiami Specjalnymi")
    edited_specials = st.data_editor(
        st.session_state.special_bonuses_df,
        num_rows="dynamic",
        use_container_width=True,
        key="set_specials_editor",
    )
    if st.button("💾 Zapisz Premie Specjalne", key="btn_save_specials"):
      st.session_state.special_bonuses_df = edited_specials
      st.success("Zapisano listę premii specjalnych!")
