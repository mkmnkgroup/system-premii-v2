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

# ==========================================
# KONFIGURACJA I STYL INDUSTRIAL/CORPORATE
# ==========================================
st.set_page_config(
    page_title="System Rozliczania Harmonogramów", 
    layout="wide", 
    page_icon="🏗️"
)

st.markdown("""
    <style>
    /* Główny motyw – czyste tło i nowoczesna czcionka */
    .stApp { 
        background-color: #f8f9fa; 
        font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Nagłówki */
    h1, h2, h3 { 
        color: #111827; 
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    /* Panel boczny (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 2px solid #ffb703;
    }
    
    /* Pasek górny / akcenty nawigacyjne (Styl paska z projektu) */
    .industrial-header {
        background-color: #111827;
        color: #ffffff;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        border-bottom: 4px solid #ffb703;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Przyciski standardowe */
    div.stButton > button { 
        border-radius: 6px; 
        border: 1px solid #d1d5db; 
        background-color: #ffffff;
        color: #111827;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        border-color: #ffb703;
        color: #b45309;
        background-color: #fffbeb;
    }
    
    /* Główny przycisk (Primary - Industrial Yellow) */
    button[kind="primary"] {
        background-color: #ffb703 !important;
        color: #111827 !important;
        border: none !important;
        font-weight: 700 !important;
    }
    button[kind="primary"]:hover {
        background-color: #f59e0b !important;
    }

    /* Tabele i dataframe */
    div.stDataFrame { 
        border-radius: 8px; 
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        background-color: white;
    }
    
    /* Zakładki (Tabs w stylu żółtego paska menu) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #111827;
        padding: 8px 12px;
        border-radius: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: 4px;
        background-color: transparent;
        border: none;
        color: #d1d5db;
        font-weight: 600;
        padding: 0 16px;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(255, 183, 3, 0.2);
        color: #ffffff;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffb703 !important;
        color: #111827 !important;
        font-weight: 700 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNKCJE POMOCNICZE
# ==========================================
ARCHIVE_FILE = "archiwum_premii.pkl"

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
        text = text.replace(k, v)
    return text

def generate_pdf_slips(calc_df, period, indicator):
    pdf = FPDF()
    for idx, row in calc_df.iterrows():
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=remove_pl_chars(f"PASEK PREMIOWY - {period}"), ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", '', 12)
        pdf.cell(200, 10, txt=remove_pl_chars(f"Pracownik: {row['Pracownik']}"), ln=True)
        pdf.cell(200, 10, txt=remove_pl_chars(f"Stanowisko: {row['Stanowisko']}"), ln=True)
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        pdf.cell(200, 10, txt=remove_pl_chars(f"Wskaznik wypracowany przez dzial: {indicator*100:.2f}%"), ln=True)
        pdf.cell(200, 10, txt=remove_pl_chars(f"Dni nieobecnosci w harmonogramie: {row['Liczba nieobecności']}"), ln=True)
        pdf.cell(200, 10, txt=remove_pl_chars(f"Potracenie za nieobecnosci (z urobku): {row['Potrącenie finansowe (%)']:.2f}%"), ln=True)
        pdf.cell(200, 10, txt=remove_pl_chars(f"Indywidualny wskaznik do premii: {row['Wskaźnik do premii (%)']:.2f}%"), ln=True)
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt=remove_pl_chars(f"DO WYPLATY (NETTO): {row['Premia netto (PLN)']:.2f} PLN"), ln=True)
        
        pdf.ln(20)
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(200, 10, txt=remove_pl_chars("Wygenerowano z Systemu Rozliczania Harmonogramow. Dokument wewnetrzny."), ln=True)
        
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

# Stan sesji
if 'history' not in st.session_state: 
    st.session_state.history = load_archive()
if 'current_schedule_df' not in st.session_state: 
    st.session_state.current_schedule_df = pd.DataFrame()
if 'absence_reasons' not in st.session_state: 
    st.session_state.absence_reasons = DEFAULT_ABSENCE_REASONS.copy()

# ==========================================
# FRAGMENT EDYTORSKI
# ==========================================
@st.fragment
def schedule_editor_fragment():
    if not st.session_state.current_schedule_df.empty:
        col_btn, _ = st.columns([1, 3])
        with col_btn:
            if st.button("⏱️ Uzupełnij godziny pracy", use_container_width=True):
                def fill_start(row):
                    if row["NIEOBECNOŚĆ"] != "Brak":
                        return "NIEOBECNY"
                    val_str = str(row["CZAS ZMIANY"]).strip()
                    if "-" in val_str and val_str != "Wolne":
                        return val_str.split("-")[0].strip()
                    return ""

                def fill_end(row):
                    if row["NIEOBECNOŚĆ"] != "Brak":
                        return "NIEOBECNY"
                    val_str = str(row["CZAS ZMIANY"]).strip()
                    if "-" in val_str and val_str != "Wolne":
                        return val_str.split("-")[1].strip()
                    return ""

                st.session_state.current_schedule_df["GODZINA ROZPOCZĘCIA"] = st.session_state.current_schedule_df.apply(fill_start, axis=1)
                st.session_state.current_schedule_df["GODZINA ZAKOŃCZENIA"] = st.session_state.current_schedule_df.apply(fill_end, axis=1)
                st.success("Automatycznie uzupełniono godziny pracy oraz nieobecności!")

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
            key="schedule_editor"
        )

        mask_absent = edited_df["NIEOBECNOŚĆ"] != "Brak"
        edited_df.loc[mask_absent, "GODZINA ROZPOCZĘCIA"] = "NIEOBECNY"
        edited_df.loc[mask_absent, "GODZINA ZAKOŃCZENIA"] = "NIEOBECNY"

        def restore_start(row):
            if row["NIEOBECNOŚĆ"] == "Brak" and row["GODZINA ROZPOCZĘCIA"] == "NIEOBECNY":
                val_str = str(row["CZAS ZMIANY"]).strip()
                if "-" in val_str and val_str != "Wolne":
                    return val_str.split("-")[0].strip()
                return ""
            return row["GODZINA ROZPOCZĘCIA"]

        def restore_end(row):
            if row["NIEOBECNOŚĆ"] == "Brak" and row["GODZINA ZAKOŃCZENIA"] == "NIEOBECNY":
                val_str = str(row["CZAS ZMIANY"]).strip()
                if "-" in val_str and val_str != "Wolne":
                    return val_str.split("-")[1].strip()
                return ""
            return row["GODZINA ZAKOŃCZENIA"]

        edited_df["GODZINA ROZPOCZĘCIA"] = edited_df.apply(restore_start, axis=1)
        edited_df["GODZINA ZAKOŃCZENIA"] = edited_df.apply(restore_end, axis=1)

        st.session_state.current_schedule_df = edited_df

# ==========================================
# PANEL BOCZNY (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Konfiguracja Okresu")
    months_list = ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"]
    gen_month_name = st.selectbox("Miesiąc rozliczeniowy:", months_list, index=datetime.now().month - 1)
    gen_month_idx = months_list.index(gen_month_name) + 1
    gen_year = st.number_input("Rok:", value=datetime.now().year, step=1)
    period_key = f"{gen_month_name} {gen_year}"

    st.markdown("---")
    st.markdown("### 📁 Dane Produkcyjne")
    uploaded_month_file = st.file_uploader("1. Główny plik z produkcją:", type=["xlsx", "xls"])
    uploaded_packed_file = st.file_uploader("2. Plik z pozycjami spakowanymi:", type=["xlsx", "xls"])

    st.markdown("---")
    with st.expander("⚖️ Wagi i Średnie 12M", expanded=False):
        avg_lines_12m = st.number_input("Średnia 12M (Pozycje przyjęte):", value=23883.83, step=100.0, format="%.2f")
        w_lines = st.number_input("Waga % (Pozycje przyjęte):", value=34.29, step=0.01, format="%.2f")

        avg_packed_12m = st.number_input("Średnia 12M (Pozycje spakowane):", value=23883.83, step=100.0, format="%.2f")
        w_packed = st.number_input("Waga % (Pozycje spakowane):", value=8.57, step=0.01, format="%.2f")

        avg_pcs_12m = st.number_input("Średnia 12M (Sztuki):", value=82217.25, step=100.0, format="%.2f")
        w_pcs = st.number_input("Waga % (Sztuki):", value=28.57, step=0.01, format="%.2f")

        avg_weight_12m = st.number_input("Średnia 12M (Waga łączna):", value=35726.91, step=100.0, format="%.2f")
        w_weight = st.number_input("Waga % (Waga łączna):", value=28.57, step=0.01, format="%.2f")

        total_w = w_pcs + w_lines + w_weight + w_packed
        st.caption(f"Suma wag: **{total_w:.2f}%**")

    st.markdown("---")
    st.markdown("### ➕ Słownik nieobecności")
    new_reason_input = st.text_input("Nowy powód:")
    if st.button("Dodaj powód", use_container_width=True):
        if new_reason_input and new_reason_input.strip():
            reason_clean = new_reason_input.strip()
            if reason_clean not in st.session_state.absence_reasons:
                st.session_state.absence_reasons.append(reason_clean)
                st.success(f"Dodano: {reason_clean}")
                st.rerun()

# ==========================================
# ZAKŁADKI GŁÓWNE
# ==========================================
tab_gen, tab_calc, tab_dash, tab_emp, tab_history = st.tabs([
    "📋 Generator Harmonogramu", 
    "🧮 Kalkulator i Statystyki", 
    "📊 Dashboard i Wykresy", 
    "👤 Karta Pracownika", 
    "📁 Archiwum Historyczne"
])

BASE_EMPLOYEES = [
    {"OSOBA": "ADRIAN WRONA", "STANOWISKO": "MAGAZYNIER", "GRUPA": 4, "SYSTEM": "WTOREK-SOBOTA"},
    {"OSOBA": "ANTON FEDOSOV", "STANOWISKO": "MAGAZYNIER", "GRUPA": 8, "SYSTEM": "PONIEDZIAŁEK-PIĄTEK"},
    {"OSOBA": "JAKUB JANECZEK", "STANOWISKO": "BRYGADZISTA", "GRUPA": 2, "SYSTEM": "PONIEDZIAŁEK-PIĄTEK"},
    {"OSOBA": "JAKUB RĘBACZ", "STANOWISKO": "MAGAZYNIER", "GRUPA": 4, "SYSTEM": "WTOREK-SOBOTA"},
    {"OSOBA": "KYRYLO BZHEZITSKYI", "STANOWISKO": "BRYGADZISTA", "GRUPA": 1, "SYSTEM": "WTOREK-SOBOTA"},
    {"OSOBA": "MACIEJ BORZĘCKI", "STANOWISKO": "MAGAZYNIER", "GRUPA": 3, "SYSTEM": "WTOREK-SOBOTA"},
    {"OSOBA": "MICHAŁ KWIATKOWSKI", "STANOWISKO": "KIEROWNIK", "GRUPA": 7, "SYSTEM": "PONIEDZIAŁEK-PIĄTEK"},
    {"OSOBA": "VADZIM KARPUK", "STANOWISKO": "MAGAZYNIER", "GRUPA": 1, "SYSTEM": "WTOREK-SOBOTA"},
    {"OSOBA": "WOJTEK SZYMAŃSKI", "STANOWISKO": "MAGAZYNIER", "GRUPA": 2, "SYSTEM": "PONIEDZIAŁEK-PIĄTEK"}
]

PL_DAYS = {0: "poniedziałek", 1: "wtorek", 2: "środa", 3: "czwartek", 4: "piątek", 5: "sobota", 6: "niedziela"}

# ==========================================
# ZAKŁADKA 1: HARMONOGRAM
# ==========================================
with tab_gen:
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("Harmonogram Pracy i Zarządzanie Nieobecnościami")
        st.markdown("Skonfiguruj parametry w panelu bocznym i wygeneruj harmonogram na wybrany miesiąc.")
    with col_t2:
        if st.button("🚀 Generuj harmonogram", type="primary", use_container_width=True):
            days_in_month = calendar.monthrange(gen_year, gen_month_idx)[1]
            pl_holidays = holidays.Poland(years=gen_year)
            
            maciej_early_days = set()
            maciej_emp = next((e for e in BASE_EMPLOYEES if e["OSOBA"] == "MACIEJ BORZĘCKI"), None)
            
            if maciej_emp:
                for day in range(1, days_in_month + 1):
                    date_obj = datetime(gen_year, gen_month_idx, day)
                    day_name = PL_DAYS[date_obj.weekday()]
                    week_num = date_obj.isocalendar()[1]
                    is_holiday = date_obj in pl_holidays
                    
                    is_working_day = True
                    if maciej_emp["SYSTEM"] == "PONIEDZIAŁEK-PIĄTEK" and day_name in ["sobota", "niedziela"]:
                        is_working_day = False
                    elif maciej_emp["SYSTEM"] == "WTOREK-SOBOTA" and day_name in ["niedziela", "poniedziałek"]:
                        is_working_day = False
                    if is_holiday:
                        is_working_day = False
                    
                    if is_working_day:
                        shift_rotation = ((week_num - 1 + (maciej_emp["GRUPA"] - 1)) % 4) + 1
                        if shift_rotation == 1:
                            maciej_early_days.add(date_obj.strftime("%d.%m.%Y"))

            schedule_rows = []
            
            for day in range(1, days_in_month + 1):
                date_obj = datetime(gen_year, gen_month_idx, day)
                date_str = date_obj.strftime("%d.%m.%Y")
                day_name = PL_DAYS[date_obj.weekday()]
                week_num = date_obj.isocalendar()[1]
                is_holiday = date_obj in pl_holidays
                
                for emp in BASE_EMPLOYEES:
                    is_working_day = True
                    
                    if emp["SYSTEM"] == "PONIEDZIAŁEK-PIĄTEK" and day_name in ["sobota", "niedziela"]:
                        is_working_day = False
                    elif emp["SYSTEM"] == "WTOREK-SOBOTA" and day_name in ["niedziela", "poniedziałek"]:
                        is_working_day = False
                    if is_holiday:
                        is_working_day = False
                    
                    status_dzien = "Święto" if is_holiday else ("Pracujący" if is_working_day else "Wolny")
                    
                    if not is_working_day:
                        czas_zmiany = "Wolne"
                        shift_val = "Wolne"
                    else:
                        g = emp["GRUPA"]
                        if g == 4:
                            czas_zmiany = "08:00-16:00"
                            shift_val = 4
                        elif g == 7:
                            czas_zmiany = "08:00-17:00"
                            shift_val = 7
                        elif g == 8:
                            if date_str in maciej_early_days:
                                czas_zmiany = "06:00-14:00"
                                shift_val = 1
                            else:
                                czas_zmiany = "07:30-15:30"
                                shift_val = 8
                        else:
                            shift_rotation = ((week_num - 1 + (g - 1)) % 4) + 1
                            shift_val = shift_rotation
                            if shift_rotation == 1:
                                czas_zmiany = "06:00-14:00"
                            elif shift_rotation == 2:
                                czas_zmiany = "08:00-16:00"
                            elif shift_rotation == 3:
                                czas_zmiany = "11:00-19:00"
                            else:
                                czas_zmiany = "08:00-17:00"

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
                        "GODZINA ROZPOCZĘCIA": "",
                        "GODZINA ZAKOŃCZENIA": "",
                        "NIEOBECNOŚĆ": "Brak",
                        "NADGODZINY (godz.)": 0.0
                    })
                    
            st.session_state.current_schedule_df = pd.DataFrame(schedule_rows)
            st.success(f"Wygenerowano harmonogram na {period_key}!")

    st.markdown("---")
    schedule_editor_fragment()

# ==========================================
# ZAKŁADKA 2: KALKULATOR PREMII & STATYSTYKI
# ==========================================
with tab_calc:
    st.subheader("🧮 Kalkulator Premii i Podsumowanie Działu")
    
    if st.session_state.current_schedule_df.empty:
        st.info("Najpierw wygeneruj harmonogram w zakładce 'Generator Harmonogramu'.")
    else:
        base_salary, step_bonus_pct = 4300.0, 0.04

        w_pcs_frac = w_pcs / 100.0
        w_lines_frac = w_lines / 100.0
        w_weight_frac = w_weight / 100.0
        w_packed_frac = w_packed / 100.0

        prod_df = pd.DataFrame()
        if uploaded_month_file is not None:
            ext = uploaded_month_file.name.split('.')[-1].lower()
            try:
                raw_prod_df = pd.read_excel(uploaded_month_file, engine='xlrd' if ext == 'xls' else 'openpyxl')
                
                with st.expander("⚙️ Mapowanie kolumn pliku produkcyjnego", expanded=False):
                    cols = list(raw_prod_df.columns)
                    def find_default(keywords):
                        for col in cols:
                            if any(k.lower() in str(col).lower() for k in keywords):
                                return col
                        return cols[0] if cols else None
                    
                    col_date_default = find_default(['data', 'date'])
                    col_pcs_default = find_default(['sztuk', 'sztuki', 'pcs', 'ilość'])
                    col_lines_default = find_default(['pozycje', 'linie', 'lines'])
                    col_weight_default = find_default(['waga łączna', 'waga całkowita', 'waga', 'weight', 'kg'])
                    col_packed_default = find_default(['spakowane', 'paczki', 'packed'])
                    
                    map_col1, map_col2, map_col3, map_col4, map_col5 = st.columns(5)
                    with map_col1:
                        sel_date = st.selectbox("Data", cols, index=cols.index(col_date_default) if col_date_default in cols else 0, key="map_date")
                    with map_col2:
                        sel_pcs = st.selectbox("Sztuki", cols, index=cols.index(col_pcs_default) if col_pcs_default in cols else 0, key="map_pcs")
                    with map_col3:
                        sel_lines = st.selectbox("Pozycje", cols, index=cols.index(col_lines_default) if col_lines_default in cols else 0, key="map_lines")
                    with map_col4:
                        sel_weight = st.selectbox("Waga", cols, index=cols.index(col_weight_default) if col_weight_default in cols else 0, key="map_weight")
                    with map_col5:
                        sel_packed = st.selectbox("Spakowane", cols, index=cols.index(col_packed_default) if col_packed_default in cols else 0, key="map_packed")
                
                prod_df = raw_prod_df.rename(columns={
                    sel_date: 'Data',
                    sel_pcs: 'Sztuki',
                    sel_lines: 'Pozycje',
                    sel_weight: 'Waga',
                    sel_packed: 'Spakowane'
                })
            except Exception as e:
                st.error(f"Błąd podczas wczytywania pliku produkcyjnego: {e}")

        packed_df = pd.DataFrame()
        if uploaded_packed_file is not None:
            ext_pk = uploaded_packed_file.name.split('.')[-1].lower()
            try:
                packed_df = pd.read_excel(uploaded_packed_file, engine='xlrd' if ext_pk == 'xls' else 'openpyxl')
            except:
                pass

        df_sched = st.session_state.current_schedule_df
        days_in_month_count = calendar.monthrange(gen_year, gen_month_idx)[1]
        
        daily_avg_pcs = avg_pcs_12m / days_in_month_count if days_in_month_count > 0 else 0.0
        daily_avg_lines = avg_lines_12m / days_in_month_count if days_in_month_count > 0 else 0.0
        daily_avg_weight = avg_weight_12m / days_in_month_count if days_in_month_count > 0 else 0.0
        daily_avg_packed = avg_packed_12m / days_in_month_count if days_in_month_count > 0 else 0.0

        cur_pcs, cur_lines, cur_weight, cur_packed = 0.0, 0.0, 0.0, 0.0

        if not prod_df.empty:
            cur_pcs = get_col_sum_flexible(prod_df, ['Sztuki'])
            cur_lines = get_col_sum_flexible(prod_df, ['Pozycje'])
            cur_weight = get_col_sum_flexible(prod_df, ['Waga'])

        if not packed_df.empty:
            cur_packed = get_col_sum_flexible(packed_df, ['Spakowane', 'spakowane', 'Paczki'])
        elif not prod_df.empty:
            cur_packed = get_col_sum_flexible(prod_df, ['Spakowane'])

        daily_prod_map = {}

        if not prod_df.empty and 'Data' in prod_df.columns:
            prod_df['Data_parsed'] = pd.to_datetime(prod_df['Data'], dayfirst=True, errors='coerce')
            for date_val, group in prod_df.groupby('Data_parsed'):
                if pd.isna(date_val): continue
                d_pcs = get_col_sum_flexible(group, ['Sztuki'])
                d_lines = get_col_sum_flexible(group, ['Pozycje'])
                d_weight = get_col_sum_flexible(group, ['Waga'])
                d_packed = get_col_sum_flexible(group, ['Spakowane'])
                daily_prod_map[date_val.strftime('%d.%m.%Y')] = {
                    'pcs': d_pcs, 'lines': d_lines, 'weight': d_weight, 'packed': d_packed
                }

        if not packed_df.empty:
            date_col_packed = 'Data' if 'Data' in packed_df.columns else ('data' if 'data' in packed_df.columns else None)
            if date_col_packed:
                packed_df['Data_parsed'] = pd.to_datetime(packed_df[date_col_packed], dayfirst=True, errors='coerce')
                for date_val, group in packed_df.groupby('Data_parsed'):
                    if pd.isna(date_val): continue
                    d_key = date_val.strftime('%d.%m.%Y')
                    d_packed = get_col_sum_flexible(group, ['Spakowane', 'spakowane', 'Paczki'])
                    if d_key not in daily_prod_map:
                        daily_prod_map[d_key] = {'pcs': 0.0, 'lines': 0.0, 'weight': 0.0, 'packed': d_packed}
                    else:
                        daily_prod_map[d_key]['packed'] = d_packed

        daily_staff_map = {}
        for date_str, group in df_sched.groupby("DATA"):
            working_mask = (group["NIEOBECNOŚĆ"] == "Brak") & (
                (group["DZIEŃ PRACUJĄCY/WOLNY"] == "Pracujący") | (pd.to_numeric(group["NADGODZINY (godz.)"], errors='coerce').fillna(0) > 0)
            )
            n_working = working_mask.sum()
            absent_mask = group["NIEOBECNOŚĆ"] != "Brak"
            n_absent = absent_mask.sum()
            overtime_sum = pd.to_numeric(group["NADGODZINY (godz.)"], errors='coerce').fillna(0).sum()
            work_hours = (n_working * 8.0) + overtime_sum
            
            daily_staff_map[str(date_str).strip()] = {
                "working_emp": n_working,
                "absent_emp": n_absent,
                "overtime": overtime_sum,
                "work_hours": work_hours
            }

        daily_prod_summary = []
        full_daily_stats = []
        all_month_dates = sorted(list(set(df_sched["DATA"].tolist())))

        for d_str in all_month_dates:
            vals = daily_prod_map.get(d_str, {'pcs': 0.0, 'lines': 0.0, 'weight': 0.0, 'packed': 0.0})
            staff = daily_staff_map.get(d_str, {'working_emp': 0, 'absent_emp': 0, 'overtime': 0.0, 'work_hours': 0.0})

            d_pcs, d_lines, d_weight, d_packed = vals['pcs'], vals['lines'], vals['weight'], vals['packed']
            n_emp = staff['working_emp']
            n_absent = staff['absent_emp']
            n_overtime = staff['overtime']
            n_hours = staff['work_hours']

            dev_d_pcs = (d_pcs - daily_avg_pcs) / daily_avg_pcs if daily_avg_pcs > 0 else 0.0
            dev_d_lines = (d_lines - daily_avg_lines) / daily_avg_lines if daily_avg_lines > 0 else 0.0
            dev_d_weight = (d_weight - daily_avg_weight) / daily_avg_weight if daily_avg_weight > 0 else 0.0
            dev_d_packed = (d_packed - daily_avg_packed) / daily_avg_packed if daily_avg_packed > 0 else 0.0

            ind_day = (dev_d_pcs * w_pcs_frac + dev_d_lines * w_lines_frac + dev_d_weight * w_weight_frac + dev_d_packed * w_packed_frac)

            day_share = 0.0
            if cur_pcs > 0: day_share += (d_pcs / cur_pcs) * w_pcs_frac
            if cur_lines > 0: day_share += (d_lines / cur_lines) * w_lines_frac
            if cur_weight > 0: day_share += (d_weight / cur_weight) * w_weight_frac
            if cur_packed > 0: day_share += (d_packed / cur_packed) * w_packed_frac

            daily_prod_summary.append({
                "DATA": d_str,
                "Wskaźnik Dnia (%)": ind_day * 100,
                "Udział_ułamek": day_share
            })

            pcs_per_emp = d_pcs / n_emp if n_emp > 0 else 0.0
            lines_per_emp = d_lines / n_emp if n_emp > 0 else 0.0
            weight_per_emp = d_weight / n_emp if n_emp > 0 else 0.0
            packed_per_emp = d_packed / n_emp if n_emp > 0 else 0.0

            full_daily_stats.append({
                "Data": d_str,
                "Osoby pracujące": n_emp,
                "Osoby nieobecne": n_absent,
                "Nadgodziny (h)": n_overtime,
                "Pozycje": d_lines,
                "Sztuki": d_pcs,
                "Waga łączna (kg)": d_weight,
                "Spakowane": d_packed,
                "Pozycje / os.": lines_per_emp,
                "Sztuki / os.": pcs_per_emp,
                "Waga łączna / os.": weight_per_emp,
                "Spakowane / os.": packed_per_emp,
                "Udział w miesiącu (%)": day_share * 100
            })

        daily_ind_df = pd.DataFrame(daily_prod_summary)
        daily_stats_df = pd.DataFrame(full_daily_stats)

        st.session_state.current_daily_df = daily_ind_df
        st.session_state.current_daily_stats_df = daily_stats_df

        daily_shares_dict = {row["DATA"]: row["Udział_ułamek"] for row in daily_prod_summary}

        dev_pcs = (cur_pcs - avg_pcs_12m)/avg_pcs_12m if avg_pcs_12m>0 else 0.0
        dev_lines = (cur_lines - avg_lines_12m)/avg_lines_12m if avg_lines_12m>0 else 0.0
        dev_weight = (cur_weight - avg_weight_12m)/avg_weight_12m if avg_weight_12m>0 else 0.0
        dev_packed = (cur_packed - avg_packed_12m)/avg_packed_12m if avg_packed_12m>0 else 0.0
        
        indicator = (dev_pcs * w_pcs_frac + dev_lines * w_lines_frac + dev_weight * w_weight_frac + dev_packed * w_packed_frac)
        full_steps = max(0, int(indicator // 0.10)) if indicator > 0 else 0
        bonus_rate = full_steps * step_bonus_pct
        max_bonus_per_emp = base_salary * bonus_rate

        summary_list = []
        for name, group in df_sched.groupby("OSOBA"):
            dni_nieobecne = 0
            potracenie_ułamek = 0.0
            for _, row in group.iterrows():
                if row.get("DZIEŃ PRACUJĄCY/WOLNY") == "Pracujący" and row.get("NIEOBECNOŚĆ", "Brak") != "Brak":
                    dni_nieobecne += 1
                    potracenie_ułamek += daily_shares_dict.get(str(row["DATA"]).strip(), 0.0)

            wsk_obecnosci = max(0.0, 1.0 - potracenie_ułamek)
            summary_list.append({
                "Pracownik": name,
                "Stanowisko": group["STANOWISKO"].iloc[0],
                "Liczba nieobecności": dni_nieobecne,
                "Potrącenie finansowe (%)": potracenie_ułamek * 100,
                "Wskaźnik do premii (%)": wsk_obecnosci * 100,
                "Premia netto (PLN)": wsk_obecnosci * max_bonus_per_emp
            })
            
        calc_df = pd.DataFrame(summary_list)
        st.session_state.current_calc_df = calc_df
        st.session_state.current_indicator = indicator

        st.metric(label="Wyliczony Wskaźnik Działu", value=f"{indicator*100:.2f}%")
        
        st.dataframe(calc_df.style.format({
            "Potrącenie finansowe (%)": "{:.2f}%", 
            "Wskaźnik do premii (%)": "{:.2f}%", 
            "Premia netto (PLN)": "{:.2f} zł"
        }), use_container_width=True)

        colA, colB = st.columns(2)
        with colA:
            if st.button("💾 Zapisz do archiwum", type="primary", use_container_width=True):
                st.session_state.history[period_key] = {
                    "df": calc_df.copy(), 
                    "schedule_df": df_sched.copy(), 
                    "daily_df": daily_ind_df.copy(), 
                    "daily_stats_df": daily_stats_df.copy(),
                    "indicator": indicator
                }
                save_archive(st.session_state.history)
                st.success("Zapisano dane do archiwum!")
        with colB:
            if not calc_df.empty:
                pdf_bytes = generate_pdf_slips(calc_df, period_key, indicator)
                st.download_button(
                    label="📄 Pobierz paski premiowe (PDF)", 
                    data=pdf_bytes, 
                    file_name=f"Paski_Premiowe_{period_key}.pdf", 
                    mime="application/pdf",
                    use_container_width=True
                )

# ==========================================
# ZAKŁADKA 3: DASHBOARD + ANALIZA NADGODZIN
# ==========================================
with tab_dash:
    st.subheader("📊 Dashboard Analityczny")
    tab_m, tab_t, tab_ot = st.tabs(["Obecny Miesiąc", "Trendy Historyczne", "Tabela Efektywności i Nadgodzin"])
    
    with tab_m:
        if 'current_daily_df' in st.session_state and not st.session_state.current_daily_df.empty:
            fig1 = px.bar(st.session_state.current_daily_df, x="DATA", y="Wskaźnik Dnia (%)", title="Dzienny Wskaźnik Wykonania Urobku", text_auto='.2f')
            fig1.update_layout(plot_bgcolor='white', paper_bgcolor='white')
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Brak danych bieżącego miesiąca. Wgraj pliki i przejdź przez kalkulator.")

    with tab_t:
        if st.session_state.history:
            hist_rows = []
            for period, data in st.session_state.history.items():
                ind = data.get("indicator", 0.0)
                hist_rows.append({"Okres": period, "Wskaźnik Działu (%)": ind * 100})
            hist_df = pd.DataFrame(hist_rows)
            if not hist_df.empty:
                fig_hist = px.line(hist_df, x="Okres", y="Wskaźnik Działu (%)", markers=True, title="Trend Wskaźnika Działu w Czasie")
                fig_hist.update_layout(plot_bgcolor='white', paper_bgcolor='white')
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("Brak wystarczających danych historycznych.")
        else:
            st.info("Brak zapisanych okresów w archiwum.")

    with tab_ot:
        st.markdown("### Szczegółowe zestawienie dzienne")
        if 'current_daily_stats_df' in st.session_state and not st.session_state.current_daily_stats_df.empty:
            df_ot_stats = st.session_state.current_daily_stats_df
            st.dataframe(
                df_ot_stats[[
                    "Data", "Osoby pracujące", "Osoby nieobecne", "Nadgodziny (h)", 
                    "Pozycje", "Sztuki", "Waga łączna (kg)", "Spakowane", 
                    "Pozycje / os.", "Sztuki / os.", "Waga łączna / os.", "Spakowane / os.", "Udział w miesiącu (%)"
                ]].style.format({
                    "Nadgodziny (h)": "{:.1f}", "Pozycje": "{:,.0f}", "Sztuki": "{:,.0f}",
                    "Waga łączna (kg)": "{:,.2f}", "Spakowane": "{:,.0f}", "Pozycje / os.": "{:,.1f}",
                    "Sztuki / os.": "{:,.1f}", "Waga łączna / os.": "{:,.2f}", "Spakowane / os.": "{:,.1f}",
                    "Udział w miesiącu (%)": "{:.2f}%"
                }),
                use_container_width=True
            )
        else:
            st.info("Brak danych statystycznych.")

# ==========================================
# ZAKŁADKA 4: KARTA PRACOWNIKA
# ==========================================
with tab_emp:
    st.subheader("👤 Karta Indywidualna Pracownika")
    if st.session_state.current_schedule_df.empty:
        st.info("Najpierw wygeneruj harmonogram.")
    else:
        all_emps = sorted(st.session_state.current_schedule_df["OSOBA"].unique().tolist())
        selected_emp = st.selectbox("Wybierz pracownika z listy:", all_emps, key="select_emp_card")
        
        emp_sched = st.session_state.current_schedule_df[st.session_state.current_schedule_df["OSOBA"] == selected_emp]
        emp_position = emp_sched["STANOWISKO"].iloc[0] if not emp_sched.empty else ""
        
        st.markdown(f"### Pracownik: **{selected_emp}** | *{emp_position}*")
        
        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
        total_days_worked = ((emp_sched["DZIEŃ PRACUJĄCY/WOLNY"] == "Pracujący") & (emp_sched["NIEOBECNOŚĆ"] == "Brak")).sum()
        total_absences = (emp_sched["NIEOBECNOŚĆ"] != "Brak").sum()
        total_overtime = pd.to_numeric(emp_sched["NADGODZINY (godz.)"], errors='coerce').fillna(0).sum()
        
        with col_e1:
            st.metric("Dni pracujące", int(total_days_worked))
        with col_e2:
            st.metric("Nieobecności", int(total_absences))
        with col_e3:
            st.metric("Nadgodziny (h)", f"{total_overtime:.1f}")
            
        if 'current_calc_df' in st.session_state and not st.session_state.current_calc_df.empty:
            emp_calc = st.session_state.current_calc_df[st.session_state.current_calc_df["Pracownik"] == selected_emp]
            if not emp_calc.empty:
                net_bonus = emp_calc["Premia netto (PLN)"].values[0]
                penalty_pct = emp_calc["Potrącenie finansowe (%)"].values[0]
                with col_e4:
                    st.metric("Premia netto", f"{net_bonus:.2f} PLN", delta=f"-{penalty_pct:.2f}% potrącenia" if penalty_pct > 0 else "Pełna premia")
        
        st.markdown("---")
        st.markdown("#### Harmonogram miesiąca")
        st.dataframe(
            emp_sched[["DATA", "DZIEŃ TYGODNIA", "ZMIANA", "CZAS ZMIANY", "DZIEŃ PRACUJĄCY/WOLNY", "NIEOBECNOŚĆ", "NADGODZINY (godz.)"]],
            use_container_width=True
        )

# ==========================================
# ZAKŁADKA 5: ARCHIWUM HISTORYCZNE
# ==========================================
with tab_history:
    st.subheader("📁 Archiwum Okresów Rozliczeniowych")
    if not st.session_state.history:
        st.info("Brak zapisanych okresów w archiwum.")
    else:
        archive_periods = list(st.session_state.history.keys())
        selected_period = st.selectbox("Wybierz okres archiwalny:", archive_periods, key="select_history_period")
        
        period_data = st.session_state.history[selected_period]
        
        col_h1, _ = st.columns([1, 3])
        with col_h1:
            st.metric("Wyliczony Wskaźnik Działu", f"{period_data.get('indicator', 0.0)*100:.2f}%")
        
        st.markdown("#### Zestawienie premiowe")
        arch_calc_df = period_data.get("df", pd.DataFrame())
        if not arch_calc_df.empty:
            st.dataframe(arch_calc_df.style.format({
                "Potrącenie finansowe (%)": "{:.2f}%",
                "Wskaźnik do premii (%)": "{:.2f}%",
                "Premia netto (PLN)": "{:.2f} zł"
            }), use_container_width=True)
            
            pdf_arch_bytes = generate_pdf_slips(arch_calc_df, selected_period, period_data.get('indicator', 0.0))
            st.download_button(
                label=f"📄 Pobierz paski premiowe (PDF) - {selected_period}",
                data=pdf_arch_bytes,
                file_name=f"Paski_Premiowe_{selected_period}.pdf",
                mime="application/pdf",
                key=f"download_arch_{selected_period}"
            )
            
        st.markdown("---")
        st.markdown("#### Harmonogram archiwalny")
        arch_sched_df = period_data.get("schedule_df", pd.DataFrame())
        if not arch_sched_df.empty:
            st.dataframe(arch_sched_df, use_container_width=True)
