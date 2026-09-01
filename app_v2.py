import io
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Generator Harmonogramu z Importem Nieobecności",
    layout="wide",
)

st.title("📅 Generator Harmonogramu i Zarządzanie Nieobecnościami")

# Inicjalizacja stanu sesji dla ustawień i danych
if "absence_codes" not in st.session_state:
  st.session_state.absence_codes = {
      "Z": "URLOP NA ŻĄDANIE",
      "W": "URLOP WYPOCZYNKOWY WYKORZYSTANY",
      "NO": "NIEOBECNY",
      "B": "URLOP BEZPŁATNY",
      "N": "NIEOBECNOŚĆ NIEUSPRAWIEDLIWIONA",
      "H": "CHOROBOWE",
      "K": "KRWIODAWSTWO",
      "SW": "SIŁA WYŻSZA",
      "NU": "NIEOBECNOŚĆ USPRAWIEDLIWIONA",
      "OŚ": "ODEBRANE ZA ŚWIĘTO",
  }

if "employees" not in st.session_state:
  st.session_state.employees = [
      "Kwiatkowski Michał",
      "Janeczek Jakub",
      "Szymański Wojciech",
      "Adrian Wrona",
      "Brzezicki Cyryl",
      "Fedosov Anton",
      "Maciej Borzęcki",
      "Jakub Rębacz",
      "Vadzim Karpuk",
  ]

if "schedule_data" not in st.session_state:
  st.session_state.schedule_data = pd.DataFrame()

tabs = st.tabs(["⚙️ Ustawienia Oznaczeń", "📅 Generator Harmonogramu"])

# ================= TAB 1: USTAWIENIA =================
with tabs[0]:
  st.header("Ustawienia Oznaczeń Nieobecności")
  st.markdown(
      "Tutaj możesz zdefiniować lub zmodyfikować symbole nieobecności używane"
      " w systemie oraz ich opisy."
  )

  # Edycja słownika w formie tabeli/formularza
  codes_df = pd.DataFrame(
      list(st.session_state.absence_codes.items()),
      columns=["Oznaczenie", "Rodzaj nieobecności"],
  )

  edited_codes_df = st.data_editor(
      codes_df, num_rows="dynamic", key="codes_editor"
  )

  if st.button("Zapisz ustawienia oznaczeń"):
    new_dict = {}
    for idx, row in edited_codes_df.iterrows():
      if pd.notna(row["Oznaczenie"]) and str(row["Oznaczenie"]).strip() != "":
        new_dict[str(row["Oznaczenie"]).strip().upper()] = row[
            "Rodzaj nieobecności"
        ]
    st.session_state.absence_codes = new_dict
    st.success("Zaktualizowano słownik oznaczeń nieobecności!")

# ================= TAB 2: GENERATOR HARMONOGRAMU =================
with tabs[1]:
  st.header("Generator Harmonogramu & Import Nieobecności")

  col1, col2 = st.columns([1, 1])

  with col1:
    st.subheader("1. Import pliku nieobecności (Excel)")
    uploaded_file = st.file_uploader(
        "Wgraj plik Excel z nieobecnościami (np. Niobecności za 08.2026.xlsx)",
        type=["xlsx", "xls"],
    )

    selected_month = st.selectbox(
        "Wybierz miesiąc harmonogramu",
        ["Sierpień 2026", "Wrzesień 2026", "Październik 2026"],
    )
    days_in_month = (
        31
        if "Sierpień" in selected_month or "Październik" in selected_month
        else 30
    )

    if uploaded_file is not None:
      try:
        # Wczytaj plik bez nagłówków, aby precyzyjnie zlokalizować strukturę
        raw_df = pd.read_excel(uploaded_file, header=None)
        st.success("Plik wczytany pomyślnie!")

        if st.button("Przetwarzaj i zaimportuj nieobecności"):
          imported_records = []
          # Iteracja po wierszach od wiersza 2 (wzór pliku)
          for r in range(2, len(raw_df)):
            emp_name = raw_df.iloc[r, 0]
            if (
                pd.isna(emp_name)
                or str(emp_name).strip() == ""
                or str(emp_name).strip() == "Pracownik"
            ):
              continue

            emp_name_clean = str(emp_name).strip()
            if emp_name_clean not in st.session_state.employees:
              st.session_state.employees.append(emp_name_clean)

            # Sprawdź kolumny od 1 do końca (dni miesiąca)
            for c in range(1, raw_df.shape[1]):
              cell_val = raw_df.iloc[r, c]
              if pd.notna(cell_val):
                code = str(cell_val).strip().upper()
                if code in st.session_state.absence_codes:
                  day_val = None
                  for test_r in [1, 2]:
                    header_val = raw_df.iloc[test_r, c]
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
                      "Opis": st.session_state.absence_codes[code],
                  })

          st.session_state.imported_absences_df = pd.DataFrame(
              imported_records
          )
          st.success(
              f"Pomyślnie zaimportowano {len(imported_records)} wpisów"
              f" nieobecności dla {len(st.session_state.employees)}"
              " pracowników!"
          )
      except Exception as e:
        st.error(f"Błąd podczas parsowania pliku: {e}")

  with col2:
    st.subheader("2. Podgląd zaimportowanych nieobecności")
    if (
        "imported_absences_df" in st.session_state
        and not st.session_state.imported_absences_df.empty
    ):
      st.dataframe(
          st.session_state.imported_absences_df, use_container_width=True
      )
    else:
      st.info(
          "Brak zaimportowanych danych. Wgraj plik i kliknij przycisk importu po"
          " lewej stronie."
      )

  st.markdown("---")
  st.subheader(
      "3. Wygenerowany Harmonogram Pracy (z uwzględnieniem nieobecności)"
  )

  if st.button("🚀 Generuj Harmonogram Miesięczny"):
    days = list(range(1, 32))
    schedule_matrix = {
        emp: {d: "Praca" for d in days} for emp in st.session_state.employees
    }

    if (
        "imported_absences_df" in st.session_state
        and not st.session_state.imported_absences_df.empty
    ):
      for _, row in st.session_state.imported_absences_df.iterrows():
        emp = row["Pracownik"]
        day = int(row["Dzień"])
        code = row["Oznaczenie"]
        if emp in schedule_matrix and day in schedule_matrix[emp]:
          schedule_matrix[emp][day] = f"[{code}]"

    sch_df = pd.DataFrame.from_dict(schedule_matrix, orient="index")
    sch_df.columns = [str(d) for d in days]

    st.session_state.final_schedule = sch_df
    st.success("Harmonogram został wygenerowany pomyślnie!")

  if "final_schedule" in st.session_state:
    st.dataframe(st.session_state.final_schedule, use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      st.session_state.final_schedule.to_excel(writer, sheet_name="Harmonogram")
    processed_data = output.getvalue()

    st.download_button(
        label="📥 Pobierz wygenerowany harmonogram (Excel)",
        data=processed_data,
        file_name="Wygenerowany_Harmonogram_08_2026.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
