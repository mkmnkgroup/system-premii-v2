import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
import os
import pickle
import holidays
import plotly.express as px
from fpdf import FPDF
import tempfile
import io

# ==========================================
# KONFIGURACJA I CSS - V2
# ==========================================
st.set_page_config(page_title="System Rozliczania Harmonogramów v2", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div.stButton > button { border-radius: 5px; border: 1px solid #ddd; }
    div.stDataFrame { border-radius: 10px; }
    h1, h2, h3 { color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

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
        'ą':'a', 'ć':'c', 'ę':'e', 'ł':'l', 'ń':'n', 'ó':'o', 'ś':'s', 'ź':'z', 'ż':'z',
        'Ą':'A', 'Ć':'C', 'Ę':'E', 'Ł':'L', 'Ń':'N', 'Ó':'O', 'Ś':'S', 'Ź':'Z', 'Ż':'Z'
    }
    for k, v in replacements.items(): 
        text = str(text).replace(k, v)
    return text

def generate_pdf_slips(calc_df, period, indicator):
    pdf = FPDF()
    for idx, row in calc_df.iterrows():
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=remove_pl_chars(f"PASEK PREMIOWY v2 - {period}"), ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, txt=remove_pl_chars(f"Pracownik: {row['Pracownik']}"), ln=True)
        pdf.cell(200, 10, txt=remove_pl_chars(f"Stanowisko: {row['Stanowisko']}"), ln=True)
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        pdf.cell(200, 10, txt=remove_pl_chars(f"Wskaznik dzialu: {indicator*100:.2f}%"), ln=True)
        pdf.cell(200, 10, txt=remove_pl_chars(f"Liczba nieobecnosci: {row['Liczba nieobecności']}"), ln=True)
        pdf.cell(200, 10, txt=remove_pl_chars("Potracenia za nieobecnosci: BRAK (0%)"), ln=True)
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=remove_pl_chars(f"DO WYPLATY (NETTO): {row['Premia netto (PLN)']:.2f} PLN"), ln=True)
        
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(200, 10, txt=remove_pl_chars("Wygenerowano z Systemu Rozliczania Harmonogramow v2. Dokument wewnetrzny."), ln=True)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f: 
            data = f.read()
    os.remove(tmp.name)
    return data

def get_col_sum_flexible(df, possible_names):
    if df.empty:
        return 0.0
    for col in df.columns:
        if str(col).strip().lower() in [p.lower() for p in possible_names]:
            return float(pd.to_numeric(df[col], errors='coerce').fillna(0).sum())
    return 0.0

DEFAULT_ABSENCE_REASONS = [
    "Brak",
    "CHOROBOWE",
    "URLOP BEZPŁATNY",
    "URLOP WYPOCZYNKOWY",
    "WOLNE ZA SOBOTĘ",
    "ŚWIĘTO",
    "URLOP NA ŻĄDANIE",
    "PRACUJĄCA SOBOTA",
    "NIEOBECNOŚĆ NIEUSPRAWIEDLIWIONA",
    "KRWIODAWSTWO",
    "NIEOBECNOŚĆ USPRAWIEDLIWIONA",
    "ODEBRANE ZA ŚWIĘTO"
]

DEFAULT_GROUPS = [
    {"Nazwa grupy": "GRUPA 1", "Czas pracy": "06:00-14:00"},
    {"Nazwa grupy": "GRUPA 2", "Czas pracy": "08:00-16:00"},
    {"Nazwa grupy": "GRUPA 3", "Czas pracy": "11:00-19:00"},
    {"Nazwa grupy": "GRUPA 4", "Czas pracy": "08:00-16:00"},
    {"Nazwa grupy": "GRUPA 5", "Czas pracy": "08:00-16:00"},
    {"Nazwa grupy": "GRUPA 6", "Czas pracy": "11:00-19:00"},
    {"Nazwa grupy": "GRUPA 7", "Czas pracy": "08:00-17:00"}
]

DEFAULT_EMPLOYEES = [
    {"OSOBA": "ADRIAN WRONA", "GRUPA": "GRUPA 4", "SYSTEM": "WTOREK-SOBOTA", "STANOWISKO": "MAGAZYNIER", "FUNKCJA": "1 SKANOWANIE"},
    {"OSOBA": "ANTON FEDOSOV", "GRUPA": "GRUPA 3", "SYSTEM": "PONIEDZIAŁEK-PIĄTEK", "STANOWISKO": "MAGAZYNIER", "FUNKCJA": "1 SKANOWANIE"},
    {"OSOBA": "JAKUB JANECZEK", "GRUPA": "GRUPA 2", "SYSTEM": "PONIEDZIAŁEK-PIĄTEK", "STANOWISKO": "BRYGADZISTA", "FUNKCJA": "2 SKANOWANIE"},
    {"OSOBA": "JAKUB RĘBACZ", "GRUPA": "GRUPA 4", "SYSTEM": "WTOREK-SOBOTA", "STANOWISKO": "MAGAZYNIER", "FUNKCJA": "1 SKANOWANIE"},
    {"OSOBA": "KYRYLO BZHEZITSKYI", "GRUPA": "GRUPA 1", "SYSTEM": "WTOREK-SOBOTA", "STANOWISKO": "BRYGADZISTA", "FUNKCJA": "1 SKANOWANIE"},
    {"OSOBA": "MACIEJ BORZĘCKI", "GRUPA": "GRUPA 3", "SYSTEM": "WTOREK-SOBOTA", "STANOWISKO": "MAGAZYNIER", "FUNKCJA": "1 SKANOWANIE"},
    {"OSOBA": "MICHAŁ KWIATKOWSKI", "GRUPA": "GRUPA 7", "SYSTEM": "PONIEDZIAŁEK-PIĄTEK", "STANOWISKO": "KIEROWNIK", "FUNKCJA": "KIEROWNIK"},
    {"OSOBA": "VADZIM KARPUK", "GRUPA": "GRUPA 1", "SYSTEM": "WTOREK-SOBOTA", "STANOWISKO": "MAGAZYNIER", "FUNKCJA": "1 SKANOWANIE"},
    {"OSOBA": "WOJTEK SZYMAŃSKI", "GRUPA": "GRUPA 2", "SYSTEM": "PONIEDZIAŁEK-PIĄTEK", "STANOWISKO": "MAGAZYNIER", "FUNKCJA": "2 SKANOWANIE"}
]

# Stan sesji
if 'history_v2' not in st.session_state: 
    st.session_state.history_v2 = load_archive()
if 'current_schedule_df' not in st.session_state: 
    st.session_state.current_schedule_df = pd.DataFrame()
if 'absence_reasons' not in st.session_state: 
    st.session_state.absence_reasons = DEFAULT_ABSENCE_REASONS.copy()
if 'groups_df' not in st.session_state:
    st.session_state.groups_df = pd.DataFrame(DEFAULT_GROUPS)
if 'employees_df' not in st.session_state:
    st.session_state.employees_df = pd.DataFrame(DEFAULT_EMPLOYEES)

# Inicjalizacja stanów konfiguracyjnych w session_state
if 'avg_lines_12m' not in st.session_state: st.session_state.avg_lines_12m = 17322.50
if 'w_lines' not in st.session_state: st.session_state.w_lines = 42.86
if 'avg_pcs_12m' not in st.session_state: st.session_state.avg_pcs_12m = 58710.75
if 'w_pcs' not in st.session_state: st.session_state.w_pcs = 28.57
if 'avg_weight_12m' not in st.session_state: st.session_state.avg_weight_12m = 26417.42
if 'w_weight' not in st.session_state: st.session_state.w_weight = 28.57

if 'ot_kierownik' not in st.session_state: st.session_state.ot_kierownik = 35.0
if 'ot_brygadzista' not in st.session_state: st.session_state.ot_brygadzista = 30.0
if 'ot_magazynier' not in st.session_state: st.session_state.ot_magazynier = 25.0
if 'rate_pallet' not in st.session_state: st.session_state.rate_pallet = 10.0
if 'pallet_pool' not in st.session_state: st.session_state.pallet_pool = 600.0

# ==========================================
# FRAGMENT EDYTORYCZNY
# ==========================================
@st.fragment
def schedule_editor_fragment():
    if not st.session_state.current_schedule_df.empty:
        col_btn1, col_btn2, _ = st.columns([1, 1, 2])
        with col_btn1:
            if st.button("⏱️ Uzupełnij godziny pracy", use_container_width=True):
                def fill_start(row):
                    if row["NIEOBECNOŚĆ"] != "Brak":
                        return "NIEOBECNY"
                    if row["DZIEŃ PRACUJĄCY/WOLNY"] in ["Wolny", "Święto"] or str(row["CZAS ZMIANY"]).strip().lower() == "wolne":
                        return "Wolne"
                    val_str = str(row["CZAS ZMIANY"]).strip()
                    if "-" in val_str and val_str.lower() != "wolne":
                        return val_str.split("-")[0].strip()
                    return ""

                def fill_end(row):
                    if row["NIEOBECNOŚĆ"] != "Brak":
                        return "NIEOBECNY"
                    if row["DZIEŃ PRACUJĄCY/WOLNY"] in ["Wolny", "Święto"] or str(row["CZAS ZMIANY"]).strip().lower() == "wolne":
                        return "Wolne"
                    val_str = str(row["CZAS ZMIANY"]).strip()
                    if "-" in val_str and val_str.lower() != "wolne":
                        return val_str.split("-")[1].strip()
                    return ""

                st.session_state.current_schedule_df["GODZINA ROZPOCZĘCIA"] = st.session_state.current_schedule_df.apply(fill_start, axis=1)
                st.session_state.current_schedule_df["GODZINA ZAKOŃCZENIA"] = st.session_state.current_schedule_df.apply(fill_end, axis=1)
                st.success("Automatycznie uzupełniono godziny pracy oraz nieobecności!")

        with col_btn2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                st.session_state.current_schedule_df.to_excel(writer, index=False, sheet_name='Harmonogram')
            buffer.seek(0)
            st.download_button(
                label="📥 Pobierz Harmonogram (Excel)",
                data=buffer,
                file_name="Harmonogram.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        def on_editor_change():
            if "schedule_editor" in st.session_state:
                edited_data = st.session_state["schedule_editor"]
                if isinstance(edited_data, dict):
                    edited_df = st.session_state.current_schedule_df.copy()
                    
                    if "edited_rows" in edited_data:
                        for row_idx, changes in edited_data["edited_rows"].items():
                            for col_name, new_val in changes.items():
                                edited_df.at[int(row_idx), col_name] = new_val
                    
                    mask_absent = edited_df["NIEOBECNOŚĆ"] != "Brak"
                    edited_df.loc[mask_absent, "GODZINA ROZPOCZĘCIA"] = "NIEOBECNY"
                    edited_df.loc[mask_absent, "GODZINA ZAKOŃCZENIA"] = "NIEOBECNY"

                    mask_free = edited_df["DZIEŃ PRACUJĄCY/WOLNY"].isin(["Wolny", "Święto"]) | (edited_df["CZAS ZMIANY"].astype(str).str.lower() == "wolne")
                    edited_df.loc[mask_free, "GODZINA ROZPOCZĘCIA"] = "Wolne"
                    edited_df.loc[mask_free, "GODZINA ZAKOŃCZENIA"] = "Wolne"

                    st.session_state.current_schedule_df = edited_df

        edited_df = st.data_editor(
            st.session_state.current_schedule_df,
            column_config={
                "NIEOBECNOŚĆ": st.column_config.SelectboxColumn(
                    "NIEOBECNOŚĆ",
                    options=st.session_state.absence_reasons,
                    required=True,
                    help="Wybierz powód nieobecności"
                )
            },
            use_container_width=True,
            num_rows="fixed",
            key="schedule_editor",
            on_change=on_editor_change
        )

        if isinstance(edited_df, pd.DataFrame):
            mask_absent = edited_df["NIEOBECNOŚĆ"] != "Brak"
            edited_df.loc[mask_absent, "GODZINA ROZPOCZĘCIA"] = "NIEOBECNY"
            edited_df.loc[mask_absent, "GODZINA ZAKOŃCZENIA"] = "NIEOBECNY"

            mask_free = edited_df["DZIEŃ PRACUJĄCY/WOLNY"].isin(["Wolny", "Święto"]) | (edited_df["CZAS ZMIANY"].astype(str).str.lower() == "wolne")
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
    "⚙️ Ustawienia"
])

PL_DAYS = {0: "poniedziałek", 1: "wtorek", 2: "środa", 3: "czwartek", 4: "piątek", 5: "sobota", 6: "niedziela"}

# Panel boczny - Ustawienia Okresu
st.sidebar.title("⚙️ Wersja v2")
st.sidebar.header("Ustawienia Okresu")
months_list = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]
gen_month_name = st.sidebar.selectbox("Miesiąc:", months_list, index=datetime.now().month - 1)
gen_month_idx = months_list.index(gen_month_name) + 1
gen_year = st.sidebar.number_input("Rok:", value=datetime.now().year, step=1)
period_key = f"{gen_month_name} {gen_year}"

# Panel boczny - Wgrywanie plików z produkcją
st.sidebar.markdown("---")
st.sidebar.header("📁 Wgrywanie Danych z Produkcji")
uploaded_month_file = st.sidebar.file_uploader("Główny plik z produkcją (Sztuki, Pozycje przyjęte, Waga):", type=["xlsx", "xls"])

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
            if "BORZĘCKI" in str(row_emp["OSOBA"]).upper() or "MACIEJ" in str(row_emp["OSOBA"]).upper():
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
                if "PONIEDZIAŁEK" in sys_val.upper() and day_name in ["sobota", "niedziela"]:
                    is_working_day = False
                elif "WTOREK" in sys_val.upper() and day_name in ["niedziela", "poniedziałek"]:
                    is_working_day = False
                if is_holiday:
                    is_working_day = False
                
                if is_working_day:
                    try:
                        g_num = int(str(maciej_emp["GRUPA"]).replace("GRUPA", "").strip())
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
                
                if "PONIEDZIAŁEK" in sys_val.upper() and day_name in ["sobota", "niedziela"]:
                    is_working_day = False
                elif "WTOREK" in sys_val.upper() and day_name in ["niedziela", "poniedziałek"]:
                    is_working_day = False
                if is_holiday:
                    is_working_day = False
                
                status_dzien = "Święto" if is_holiday else ("Pracujący" if is_working_day else "Wolny")
                
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
                    
                    matched_group_row = st.session_state.groups_df[st.session_state.groups_df["Nazwa grupy"].astype(str).str.strip().str.upper() == g_str.strip().upper()]
                    default_group_time = str(matched_group_row.iloc[0]["Czas pracy"]) if not matched_group_row.empty else "08:00-16:00"

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
                    "OSOBA": emp["OSOBA"],
                    "STANOWISKO": emp["STANOWISKO"],
                    "ZMIANA": shift_val if not is_holiday else "Święto",
                    "CZAS ZMIANY": czas_zmiany,
                    "DZIEŃ PRACUJĄCY/WOLNY": status_dzien,
                    "GODZINA ROZPOCZĘCIA": default_start_end,
                    "GODZINA ZAKOŃCZENIA": default_start_end,
                    "NIEOBECNOŚĆ": "Brak",
                    "NADGODZINY (godz.)": 0.0
                })
                
        st.session_state.current_schedule_df = pd.DataFrame(schedule_rows)
        st.success(f"Wygenerowano harmonogram v2 na {period_key} – rotują wyłącznie grupy 1, 2 i 3!")

    schedule_editor_fragment()

# ==========================================
# ZAKŁADKA 2: KALKULATOR PREMII
# ==========================================
with tab_calc:
    st.header("🧮 Kalkulator Premii v2 (Ciągłe wyliczanie proporcjonalne - 4% za każde 10%)")
    
    if st.session_state.current_schedule_df.empty:
        st.warning("Najpierw wygeneruj harmonogram w pierwszej zakładce!")
    else:
        base_salary = 4300.0
        step_bonus_pct = 0.04  # 4% premii bazowej za każde 10%

        w_pcs_frac = st.session_state.w_pcs / 100.0
        w_lines_frac = st.session_state.w_lines / 100.0
        w_weight_frac = st.session_state.w_weight / 100.0

        prod_df = pd.DataFrame()
        if uploaded_month_file is not None:
            ext = uploaded_month_file.name.split('.')[-1].lower()
            prod_df = pd.read_excel(uploaded_month_file, engine='xlrd' if ext == 'xls' else 'openpyxl')

        df_sched = st.session_state.current_schedule_df

        cur_pcs, cur_lines, cur_weight = 0.0, 0.0, 0.0

        if not prod_df.empty:
            cur_pcs = get_col_sum_flexible(prod_df, ['Sztuki', 'sztuka'])
            cur_lines = get_col_sum_flexible(prod_df, ['pozycje', 'Pozycje'])
            cur_weight = get_col_sum_flexible(prod_df, ['Waga łączna', 'Waga laczna', 'Waga'])

        dev_pcs = (cur_pcs - st.session_state.avg_pcs_12m) / st.session_state.avg_pcs_12m if st.session_state.avg_pcs_12m > 0 else 0.0
        dev_lines = (cur_lines - st.session_state.avg_lines_12m) / st.session_state.avg_lines_12m if st.session_state.avg_lines_12m > 0 else 0.0
        dev_weight = (cur_weight - st.session_state.avg_weight_12m) / st.session_state.avg_weight_12m if st.session_state.avg_weight_12m > 0 else 0.0
        
        indicator = (dev_pcs * w_pcs_frac + dev_lines * w_lines_frac + dev_weight * w_weight_frac)
        
        bonus_rate = indicator * (step_bonus_pct / 0.10) if indicator > 0 else 0.0
        max_bonus_per_emp = base_salary * bonus_rate

        summary_list = []
        for name, group in df_sched.groupby("OSOBA"):
            dni_nieobecne = 0
            for _, row in group.iterrows():
                if row.get("DZIEŃ PRACUJĄCY/WOLNY") == "Pracujący" and row.get("NIEOBECNOŚĆ", "Brak") != "Brak":
                    dni_nieobecne += 1

            summary_list.append({
                "Pracownik": name,
                "Stanowisko": group["STANOWISKO"].iloc[0],
                "Liczba nieobecności": dni_nieobecne,
                "Premia netto (PLN)": max_bonus_per_emp
            })
            
        calc_df = pd.DataFrame(summary_list)
        st.session_state.current_calc_df = calc_df
        st.session_state.current_indicator = indicator

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Wskaźnik Wykonania Działu", f"{indicator*100:.2f}%")
        col_m2.metric("Stawka Premii (proporcjonalna)", f"{bonus_rate*100:.2f}%")
        col_m3.metric("Premia na pracownika", f"{max_bonus_per_emp:.2f} PLN")

        st.subheader("Rozliczenie Premiowe Pracowników (v2)")
        st.dataframe(calc_df.style.format({
            "Premia netto (PLN)": "{:.2f} zł"
        }), use_container_width=True)

        st.markdown("---")
        st.subheader("⏱️ Zestawienie Nadgodzin Pracowników (Dzień po Dniu)")
        st.caption("Tabela przedstawia liczbę nadgodzin zarejestrowanych dla każdego pracownika w poszczególnych dniach miesiąca wraz z wyliczoną kwotą.")
        
        if not df_sched.empty and "NADGODZINY (godz.)" in df_sched.columns:
            overtime_pivot = df_sched.pivot_table(
                index=["OSOBA", "STANOWISKO"], 
                columns="DATA", 
                values="NADGODZINY (godz.)", 
                fill_value=0.0
            ).reset_index()
            
            date_cols = [c for c in overtime_pivot.columns if c not in ["OSOBA", "STANOWISKO"]]
            
            overtime_pivot["Suma Nadgodzin (h)"] = overtime_pivot[date_cols].sum(axis=1)
            
            def get_ot_rate(pos):
                p = str(pos).strip().upper()
                if "KIEROWNIK" in p:
                    return st.session_state.ot_kierownik
                elif "BRYGADZISTA" in p:
                    return st.session_state.ot_brygadzista
                else:
                    return st.session_state.ot_magazynier
            
            overtime_pivot["Kwota za nadgodziny (PLN)"] = overtime_pivot["Suma Nadgodzin (h)"] * overtime_pivot["STANOWISKO"].apply(get_ot_rate)
            
            cols_order = ["OSOBA", "STANOWISKO", "Suma Nadgodzin (h)", "Kwota za nadgodziny (PLN)"] + date_cols
            overtime_pivot = overtime_pivot[cols_order]
            
            st.dataframe(overtime_pivot.style.format({
                "Suma Nadgodzin (h)": "{:.2f} h",
                "Kwota za nadgodziny (PLN)": "{:.2f} zł"
            }), use_container_width=True)
            
            buffer_ot = io.BytesIO()
            with pd.ExcelWriter(buffer_ot, engine='openpyxl') as writer:
                overtime_pivot.to_excel(writer, index=False, sheet_name='Nadgodziny')
            buffer_ot.seek(0)
            st.download_button(
                label="📥 Pobierz Tabelę Nadgodzin (Excel)",
                data=buffer_ot,
                file_name=f"Nadgodziny_{period_key}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.markdown("---")
        st.subheader("📦 Załadunki / Rozładunki")
        st.caption("Wpisz całkowitą liczbę palet załadowanych/rozładowanych w miesiącu. Kwota zostanie wyliczona na podstawie stawki z ustawień i proporcjonalnie podzielona na pracowników w tabeli poniżej.")
        
        total_pallets_month = st.number_input(
            "Ilość palet załadowanych/rozładowanych w danym miesiącu:", 
            value=0.0, 
            step=10.0, 
            format="%.1f",
            key="input_total_pallets_month"
        )
        
        total_pallet_amount = total_pallets_month * st.session_state.rate_pallet
        st.info(f"Całkowita kwota za palety do podziału: **{total_pallet_amount:.2f} zł** (Stawka jednostkowa: {st.session_state.rate_pallet:.2f} zł/paleta)")

        if 'pallet_table_period' not in st.session_state or st.session_state.get('pallet_table_period') != period_key:
            st.session_state.pallet_employees_df = calc_df[["Pracownik", "Stanowisko"]].copy()
            st.session_state.pallet_table_period = period_key

        edited_pallet_df = st.data_editor(
            st.session_state.pallet_employees_df,
            num_rows="delete",
            use_container_width=True,
            key="editor_pallets_workers"
        )
        st.session_state.pallet_employees_df = edited_pallet_df

        num_workers_pallets = len(edited_pallet_df)
        share_per_worker_pallet = (total_pallet_amount / num_workers_pallets) if num_workers_pallets > 0 and total_pallet_amount > 0 else 0.0

        edited_pallet_df["Kwota za załadunki (PLN)"] = share_per_worker_pallet

        st.subheader("Rozliczenie załadunków/rozładunków na pracowników")
        st.dataframe(edited_pallet_df.style.format({
            "Kwota za załadunki (PLN)": "{:.2f} zł"
        }), use_container_width=True)

        st.markdown("---")
        st.subheader("🚜 Obsługa paleciaka")
        st.caption("Wpisz liczbę godzin przejeżdżonych przez poszczególnych pracowników. Kwota z puli (z Ustawień) zostanie podzielona proporcjonalnie do przepracowanych godzin.")
        
        st.info(f"Pula do podziału na obsługę paleciaka: **{st.session_state.pallet_pool:.2f} zł**")

        if 'pallet_truck_period' not in st.session_state or st.session_state.get('pallet_truck_period') != period_key:
            initial_pt_data = calc_df[["Pracownik", "Stanowisko"]].copy()
            initial_pt_data["Ilość godzin"] = 0.0
            st.session_state.pallet_truck_employees_df = initial_pt_data
            st.session_state.pallet_truck_period = period_key

        edited_pt_df = st.data_editor(
            st.session_state.pallet_truck_employees_df,
            num_rows="delete",
            use_container_width=True,
            column_config={
                "Ilość godzin": st.column_config.NumberColumn(
                    "Ilość godzin",
                    min_value=0.0,
                    step=1.0,
                    format="%.1f"
                )
            },
            key="editor_pallet_truck_workers"
        )
        st.session_state.pallet_truck_employees_df = edited_pt_df

        total_pt_hours = edited_pt_df["Ilość godzin"].sum()
        total_pt_pool = st.session_state.pallet_pool

        def calc_pt_amount(row):
            if total_pt_hours > 0:
                return (row["Ilość godzin"] / total_pt_hours) * total_pt_pool
            return 0.0

        edited_pt_df["Kwota (PLN)"] = edited_pt_df.apply(calc_pt_amount, axis=1)

        st.markdown(f"**Suma godzin wszystkich pracowników:** {total_pt_hours:.1f} h")
        st.subheader("Rozliczenie obsługi paleciaka na pracowników")
        st.dataframe(edited_pt_df.style.format({
            "Ilość godzin": "{:.1f} h",
            "Kwota (PLN)": "{:.2f} zł"
        }), use_container_width=True)

        st.markdown("---")
        colA, colB = st.columns(2)
        with colA:
            if st.button("💾 Zapisz do archiwum (v2)", type="primary"):
                st.session_state.history_v2[period_key] = {
                    "df": calc_df.copy(), 
                    "schedule_df": df_sched.copy(),
                    "indicator": indicator,
                    "bonus_per_emp": max_bonus_per_emp,
                    "actual_pcs": cur_pcs,
                    "actual_lines": cur_lines,
                    "actual_weight": cur_weight,
                    "base_pcs": st.session_state.avg_pcs_12m,
                    "base_lines": st.session_state.avg_lines_12m,
                    "base_weight": st.session_state.avg_weight_12m
                }
                save_archive(st.session_state.history_v2)
                st.success("Zapisano dane v2 do archiwum wraz z parametrami porównawczymi!")
        with colB:
            if not calc_df.empty:
                pdf_bytes = generate_pdf_slips(calc_df, period_key, indicator)
                st.download_button(
                    label="📄 Pobierz paski premiowe (PDF v2)", 
                    data=pdf_bytes, 
                    file_name=f"Paski_Premiowe_v2_{period_key}.pdf", 
                    mime="application/pdf"
                )

# ==========================================
# ZAKŁADKA 3: DASHBOARD I WYKRESY
# ==========================================
with tab_dash:
    st.header("📊 Dashboard Analityczny v2")
    if st.session_state.history_v2:
        hist_data = [{"Miesiąc": k, "Wskaźnik (%)": v["indicator"] * 100, "Premia (PLN)": v.get("bonus_per_emp", 0.0)} for k, v in st.session_state.history_v2.items()]
        df_trend = pd.DataFrame(hist_data)
        fig = px.line(df_trend, x="Miesiąc", y="Wskaźnik (%)", markers=True, title="Historia Wskaźnika Premiowego Działu (v2)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Brak zapisanych miesięcy w archiwum v2. Wygeneruj i zapisz miesiąc, aby wyświetlić trendy.")

# ==========================================
# ZAKŁADKA 4: ARCHIWUM
# ==========================================
with tab_history:
    st.header("📁 Archiwum Historyczne v2")
    if st.session_state.history_v2:
        selected_hist = st.selectbox("Wybierz miesiąc z bazy v2:", list(st.session_state.history_v2.keys()))
        hist_data = st.session_state.history_v2[selected_hist]
        st.dataframe(hist_data["df"].style.format({"Premia netto (PLN)": "{:.2f} zł"}), use_container_width=True)
    else:
        st.info("Brak wpisów w archiwum v2.")

# ==========================================
# ZAKŁADKA 5: PORÓWNANIE WYNIKÓW
# ==========================================
with tab_comp:
    st.header("📈 Porównanie Parametrów i Wyników (Miesiąc do Miesiąca)")
    st.markdown("Ta zakładka przedstawia zestawienie celów (bazowych średnich 12M) w stosunku do faktycznie osiągniętych wyników produkcyjnych we wszystkich zapisanych miesiącach.")

    if st.session_state.history_v2:
        comp_rows = []
        for m_key, m_data in st.session_state.history_v2.items():
            if "actual_pcs" in m_data:
                comp_rows.append({
                    "Miesiąc": m_key,
                    "Cel Sztuki": m_data["base_pcs"],
                    "Wynik Sztuki": m_data["actual_pcs"],
                    "Cel Pozycje": m_data["base_lines"],
                    "Wynik Pozycje": m_data["actual_lines"],
                    "Cel Waga": m_data["base_weight"],
                    "Wynik Waga": m_data["actual_weight"],
                    "Wskaźnik Działu (%)": m_data["indicator"] * 100
                })
        
        if comp_rows:
            df_comp = pd.DataFrame(comp_rows)
            st.subheader("Tabela Porównawcza Zestawienia Celów i Wyników")
            st.dataframe(df_comp.style.format({
                "Cel Sztuki": "{:,.2f}",
                "Wynik Sztuki": "{:,.2f}",
                "Cel Pozycje": "{:,.2f}",
                "Wynik Pozycje": "{:,.2f}",
                "Cel Waga": "{:,.2f}",
                "Wynik Waga": "{:,.2f}",
                "Wskaźnik Działu (%)": "{:.2f}%"
            }), use_container_width=True)
            
            st.markdown("---")
            st.subheader("Wykres Porównawczy (Cel vs Wynik)")
            selected_param = st.selectbox("Wybierz parametr do analizy graficznej:", ["Sztuki", "Pozycje", "Waga łączna"])
            
            if selected_param == "Sztuki":
                fig_comp = px.bar(df_comp, x="Miesiąc", y=["Cel Sztuki", "Wynik Sztuki"], barmode="group", title="Porównanie: Cel (12M) vs Wynik Rzeczywisty – Sztuki")
            elif selected_param == "Pozycje":
                fig_comp = px.bar(df_comp, x="Miesiąc", y=["Cel Pozycje", "Wynik Pozycje"], barmode="group", title="Porównanie: Cel (12M) vs Wynik Rzeczywisty – Pozycje przyjęte")
            else:
                fig_comp = px.bar(df_comp, x="Miesiąc", y=["Cel Waga", "Wynik Waga"], barmode="group", title="Porównanie: Cel (12M) vs Wynik Rzeczywisty – Waga łączna")
                
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.info("Zapisz bieżący miesiąc z wgranym plikiem produkcyjnym w zakładce *Kalkulator Premii*, aby zasilić tę tablicę porównawczą.")
    else:
        st.info("Brak zapisanych danych w archiwum v2. Wygeneruj i zapisz co najmniej jeden miesiąc.")

# ==========================================
# ZAKŁADKA 6: USTAWIENIA (GŁÓWNA)
# ==========================================
with tab_settings:
    st.header("⚙️ Ustawienia i Konfiguracja Systemu")

    set_sub_tab1, set_sub_tab2, set_sub_tab3 = st.tabs([
        "📋 Konfiguracja i Ustawienia Harmonogramu", 
        "💰 Konfiguracja premii głównej", 
        "➕ Konfiguracje innych dodatków Premii"
    ])

    # 1. Konfiguracja i Ustawienia Harmonogramu
    with set_sub_tab1:
        set_tab1, set_tab2, set_tab3 = st.tabs([
            "🚫 Powody nieobecności", 
            "🕒 Grupy i Czas Pracy", 
            "👥 Lista Pracowników"
        ])

        with set_tab1:
            st.subheader("Modyfikacja powodów nieobecności")
            st.caption("Dodawaj nowe pozycje bezpośrednio w tabeli, edytuj istniejące lub usuwaj zaznaczone wiersze.")
            
            df_reasons_editable = pd.DataFrame({"Powód nieobecności": st.session_state.absence_reasons})
            edited_reasons_df = st.data_editor(
                df_reasons_editable,
                num_rows="dynamic",
                use_container_width=True,
                key="editor_absence_reasons"
            )
            if not edited_reasons_df.empty:
                st.session_state.absence_reasons = edited_reasons_df["Powód nieobecności"].dropna().astype(str).tolist()

        with set_tab2:
            st.subheader("Modyfikacja grup oraz godzin pracy")
            st.caption("Możesz zmieniać nazwy grup, godziny pracy lub dodawać nowe wiersze.")
            
            edited_groups_df = st.data_editor(
                st.session_state.groups_df,
                num_rows="dynamic",
                use_container_width=True,
                key="editor_groups"
            )
            st.session_state.groups_df = edited_groups_df

        with set_tab3:
            st.subheader("Modyfikacja pracowników, grup i stanowisk")
            st.caption("Zarządzaj zespołem, przypisuj grupy, przedziały dni pracujących (system), stanowiska i funkcje.")
            
            available_group_names = st.session_state.groups_df["Nazwa grupy"].dropna().astype(str).tolist()
            
            edited_employees_df = st.data_editor(
                st.session_state.employees_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "GRUPA": st.column_config.SelectboxColumn(
                        "GRUPA",
                        options=available_group_names,
                        required=True,
                        help="Wybierz przypisaną grupę"
                    ),
                    "SYSTEM": st.column_config.SelectboxColumn(
                        "SYSTEM",
                        options=["PONIEDZIAŁEK-PIĄTEK", "WTOREK-SOBOTA"],
                        required=True,
                        help="Wybierz przedział dni pracujących"
                    )
                },
                key="editor_employees"
            )
            st.session_state.employees_df = edited_employees_df

    # 2. Konfiguracja premii głównej
    with set_sub_tab2:
        st.subheader("Konfiguracja premii głównej")
        st.caption("Parametry oraz wagi do wyliczania premii głównej.")

        st.session_state.avg_lines_12m = st.number_input("Średnia 12M (Pozycje przyjęte):", value=st.session_state.avg_lines_12m, step=100.0, format="%.2f", key="input_avg_lines")
        st.session_state.w_lines = st.number_input("Waga % (Pozycje przyjęte):", value=st.session_state.w_lines, step=0.01, format="%.2f", key="input_w_lines")

        st.session_state.avg_pcs_12m = st.number_input("Średnia 12M (Sztuki):", value=st.session_state.avg_pcs_12m, step=100.0, format="%.2f", key="input_avg_pcs")
        st.session_state.w_pcs = st.number_input("Waga % (Sztuki):", value=st.session_state.w_pcs, step=0.01, format="%.2f", key="input_w_pcs")

        st.session_state.avg_weight_12m = st.number_input("Średnia 12M (Waga łączna):", value=st.session_state.avg_weight_12m, step=100.0, format="%.2f", key="input_avg_weight")
        st.session_state.w_weight = st.number_input("Waga % (Waga łączna):", value=st.session_state.w_weight, step=0.01, format="%.2f", key="input_w_weight")

        total_w = st.session_state.w_pcs + st.session_state.w_lines + st.session_state.w_weight
        st.caption(f"Suma wag: **{total_w:.2f}%**")

    # 3. Konfiguracje innych dodatków Premii
    with set_sub_tab3:
        st.subheader("Konfiguracje innych dodatków Premii")
        st.markdown("Określ stawki oraz pule budżetowe dla dodatkowych elementów wynagrodzenia.")

        st.markdown("### Nadgodziny")
        st.session_state.ot_kierownik = st.number_input("Stawka za nadgodziny kierownik (zł/h):", value=st.session_state.ot_kierownik, step=1.0, format="%.2f", key="input_ot_kierownik")
        st.session_state.ot_brygadzista = st.number_input("Stawka za nadgodziny brygadzista (zł/h):", value=st.session_state.ot_brygadzista, step=1.0, format="%.2f", key="input_ot_brygadzista")
        st.session_state.ot_magazynier = st.number_input("Stawka za nadgodziny magazynier (zł/h):", value=st.session_state.ot_magazynier, step=1.0, format="%.2f", key="input_ot_magazynier")

        st.markdown("### Załadunki / Rozładunki")
        st.session_state.rate_pallet = st.number_input("Stawka za paletę (zł netto):", value=st.session_state.rate_pallet, step=0.5, format="%.2f", key="input_rate_pallet")

        st.markdown("### Obsługa paleciaka")
        st.session_state.pallet_pool = st.number_input("Pula do podziału (zł netto):", value=st.session_state.pallet_pool, step=50.0, format="%.2f", key="input_pallet_pool")
