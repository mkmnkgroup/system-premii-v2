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

def generate_pdf_slips(calc_df, period, indicator, ot_df, pallet_df, pt_df, special_df):
    pdf = FPDF()
    for idx, row in calc_df.iterrows():
        emp_name = row['Pracownik']
        pdf.add_page()
        pdf.set_font("Arial", 'B', 15)
        pdf.cell(200, 8, txt=remove_pl_chars(f"PASEK PREMIOWY v2 - {period}"), ln=True, align='C')
        pdf.ln(4)
        
        pdf.set_font("Arial", '', 11)
        pdf.cell(200, 7, txt=remove_pl_chars(f"Pracownik: {emp_name}"), ln=True)
        pdf.cell(200, 7, txt=remove_pl_chars(f"Stanowisko: {row['Stanowisko']}"), ln=True)
        pdf.ln(2)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        
        # 1. Premia Główna
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 6, txt=remove_pl_chars("1. Premia Główna:"), ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(200, 5, txt=remove_pl_chars(f"   - Wskaźnik działu: {indicator*100:.2f}%"), ln=True)
        pdf.cell(200, 5, txt=remove_pl_chars(f"   - Liczba nieobecności: {row['Liczba nieobecności']} | Potrącenia: BRAK (0%)"), ln=True)
        main_bonus = row['Premia netto (PLN)']
        pdf.cell(200, 5, txt=remove_pl_chars(f"   - Kwota premii głównej: {main_bonus:.2f} PLN"), ln=True)
        pdf.ln(2)
        
        # 2. Nadgodziny
        ot_row = ot_df[ot_df['OSOBA'] == emp_name] if not ot_df.empty and 'OSOBA' in ot_df.columns else pd.DataFrame()
        ot_hours = ot_row['Suma Nadgodzin (h)'].values[0] if not ot_row.empty and 'Suma Nadgodzin (h)' in ot_row.columns else 0.0
        ot_amount = ot_row['Kwota za nadgodziny (PLN)'].values[0] if not ot_row.empty and 'Kwota za nadgodziny (PLN)' in ot_row.columns else 0.0
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 6, txt=remove_pl_chars("2. Nadgodziny:"), ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(200, 5, txt=remove_pl_chars(f"   - Liczba godzin: {ot_hours:.1f} h"), ln=True)
        pdf.cell(200, 5, txt=remove_pl_chars(f"   - Kwota za nadgodziny: {ot_amount:.2f} PLN"), ln=True)
        pdf.ln(2)
        
        # 3. Załadunki / Rozładunki
        pallet_row = pallet_df[pallet_df['Pracownik'] == emp_name] if not pallet_df.empty and 'Pracownik' in pallet_df.columns else pd.DataFrame()
        pallet_amount = pallet_row['Kwota za załadunki (PLN)'].values[0] if not pallet_row.empty and 'Kwota za załadunki (PLN)' in pallet_row.columns else 0.0
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 6, txt=remove_pl_chars("3. Załadunki / Rozładunki:"), ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(200, 5, txt=remove_pl_chars(f"   - Kwota: {pallet_amount:.2f} PLN"), ln=True)
        pdf.ln(2)
        
        # 4. Obsługa paleciaka
        pt_row = pt_df[pt_df['Pracownik'] == emp_name] if not pt_df.empty and 'Pracownik' in pt_df.columns else pd.DataFrame()
        pt_hours = pt_row['Ilość godzin'].values[0] if not pt_row.empty and 'Ilość godzin' in pt_row.columns else 0.0
        pt_amount = pt_row['Kwota (PLN)'].values[0] if not pt_row.empty and 'Kwota (PLN)' in pt_row.columns else 0.0
        
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 6, txt=remove_pl_chars("4. Obsługa paleciaka:"), ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(200, 5, txt=remove_pl_chars(f"   - Liczba godzin: {pt_hours:.1f} h"), ln=True)
        pdf.cell(200, 5, txt=remove_pl_chars(f"   - Kwota: {pt_amount:.2f} PLN"), ln=True)
        pdf.ln(2)
        
        # 5. Premia specjalna
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 6, txt=remove_pl_chars("5. Premia specjalna:"), ln=True)
        pdf.set_font("Arial", '', 10)
        special_sum = 0.0
        if not special_df.empty:
            emp_specials = special_df[special_df['Pracownik'].astype(str).str.strip().str.upper() == str(emp_name).strip().upper()]
            if not emp_specials.empty:
                for _, s_row in emp_specials.iterrows():
                    s_amount = float(s_row.get('Kwota netto premii', 0.0) or 0.0)
                    s_who = s_row.get('Kto przyznał', '-')
                    s_reason = s_row.get('Powód przyznania premii', '-')
                    special_sum += s_amount
                    pdf.cell(200, 5, txt=remove_pl_chars(f"   - Kwota: {s_amount:.2f} PLN | Przyznał: {s_who} | Powód: {s_reason}"), ln=True)
            else:
                pdf.cell(200, 5, txt=remove_pl_chars("   - Brak premii specjalnych"), ln=True)
        else:
            pdf.cell(200, 5, txt=remove_pl_chars("   - Brak premii specjalnych"), ln=True)
        pdf.ln(4)
        
        total_net = main_bonus + ot_amount + pallet_amount + pt_amount + special_sum
        
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Arial", 'B', 13)
        pdf.cell(200, 8, txt=remove_pl_chars(f"RAZEM DO WYPŁATY (NETTO): {total_net:.2f} PLN"), ln=True)
        
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(200, 6, txt=remove_pl_chars("Wygenerowano z Systemu Rozliczania Harmonogramów v2. Dokument wewnętrzny."), ln=True)
        
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
if 'special_bonuses_df' not in st.session_state:
    st.session_state.special_bonuses_df = pd.DataFrame(
        columns=["Pracownik", "Kwota netto premii", "Kto przyznał", "Powód przyznania premii"]
    )

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
        step_bonus_pct = 0.04 

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

        # Obliczenia odchyleń i procentów względem średniej rocznej
        dev_pcs = (cur_pcs - st.session_state.avg_pcs_12m) / st.session_state.avg_pcs_12m if st.session_state.avg_pcs_12m > 0 else 0.0
        dev_lines = (cur_lines - st.session_state.avg_lines_12m) / st.session_state.avg_lines_12m if st.session_state.avg_lines_12m > 0 else 0.0
        dev_weight = (cur_weight - st.session_state.avg_weight_12m) / st.session_state.avg_weight_12m if st.session_state.avg_weight_12m > 0 else 0.0
        
        indicator = (dev_pcs * w_pcs_frac + dev_lines * w_lines_frac + dev_weight * w_weight_frac)
        bonus_rate = indicator * (step_bonus_pct / 0.10) if indicator > 0 else 0.0
        max_bonus_per_emp = base_salary * bonus_rate

        # --- SEKCJA GŁÓWNA: Wyniki miesiąca w odniesieniu do średniej rocznej ---
        st.markdown("---")
        st.subheader("📌 Wyniki Bieżącego Miesiąca vs Średnia Roczna")
        st.caption("Poniższa tabela przedstawia zestawienie ilościowe oraz procentowe odchylenie od 12-miesięcznej bazy dla poszczególnych wskaźników produkcyjnych.")

        comparison_data = [
            {
                "Parametr produkcyjny": "Pozycje",
                "Wartość w miesiącu": f"{cur_lines:,.2f}".replace(",", " ").replace(".", ","),
                "Średnia roczna (baza)": f"{st.session_state.avg_lines_12m:,.2f}".replace(",", " ").replace(".", ","),
                "Różnica ilościowa": f"{(cur_lines - st.session_state.avg_lines_12m):+,.2f}".replace(",", " ").replace(".", ","),
                "Odchylenie procentowe (%)": f"{dev_lines * 100:+.2f}%".replace(".", ","),
                "Waga wskaźnika": f"{st.session_state.w_lines:.2f}%".replace(".", ",")
            },
            {
                "Parametr produkcyjny": "Sztuki",
                "Wartość w miesiącu": f"{cur_pcs:,.2f}".replace(",", " ").replace(".", ","),
                "Średnia roczna (baza)": f"{st.session_state.avg_pcs_12m:,.2f}".replace(",", " ").replace(".", ","),
                "Różnica ilościowa": f"{(cur_pcs - st.session_state.avg_pcs_12m):+,.2f}".replace(",", " ").replace(".", ","),
                "Odchylenie procentowe (%)": f"{dev_pcs * 100:+.2f}%".replace(".", ","),
                "Waga wskaźnika": f"{st.session_state.w_pcs:.2f}%".replace(".", ",")
            },
            {
                "Parametr produkcyjny": "Waga towaru",
                "Wartość w miesiącu": f"{cur_weight:,.2f} kg".replace(",", " ").replace(".", ","),
                "Średnia roczna (baza)": f"{st.session_state.avg_weight_12m:,.2f} kg".replace(",", " ").replace(".", ","),
                "Różnica ilościowa": f"{(cur_weight - st.session_state.avg_weight_12m):+,.2f} kg".replace(",", " ").replace(".", ","),
                "Odchylenie procentowe (%)": f"{dev_weight * 100:+.2f}%".replace(".", ","),
                "Waga wskaźnika": f"{st.session_state.w_weight:.2f}%".replace(".", ",")
            }
        ]
        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Wskaźnik Wykonania Działu", f"{indicator*100:.2f}%")
        col_m2.metric("Stawka Premii (proporcjonalna)", f"{bonus_rate*100:.2f}%")
        col_m3.metric("Faktyczna Premia na pracownika", f"{max_bonus_per_emp:.2f} PLN")
        st.markdown("---")

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

        st.subheader("Rozliczenie Premiowe Pracowników (v2)")
        st.dataframe(calc_df.style.format({
            "Premia netto (PLN)": "{:.2f} zł"
        }), use_container_width=True)

        st.markdown("---")
        st.subheader("⏱️ Zestawienie Nadgodzin Pracowników (Dzień po Dniu)")
        st.caption("Tabela przedstawia liczbę nadgodzin zarejestrowanych dla każdego pracownika w poszczególnych dniach miesiąca wraz z wyliczoną kwotą (wszystkie godziny zaokrąglone do 1 miejsca po przecinku).")
        
        overtime_pivot = pd.DataFrame()
        if not df_sched.empty and "NADGODZINY (godz.)" in df_sched.columns:
            overtime_pivot = df_sched.pivot_table(
                index=["OSOBA", "STANOWISKO"], 
                columns="DATA", 
                values="NADGODZINY (godz.)", 
                fill_value=0.0
            ).reset_index()
            
            date_cols = [c for c in overtime_pivot.columns if c not in ["OSOBA", "STANOWISKO"]]
            
            for col in date_cols:
                overtime_pivot[col] = pd.to_numeric(overtime_pivot[col], errors='coerce').fillna(0.0).round(1)
            
            overtime_pivot["Suma Nadgodzin (h)"] = overtime_pivot[date_cols].sum(axis=1).round(1)
            
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
            
            format_dict = {col: "{:.1f} h" for col in date_cols}
            format_dict["Suma Nadgodzin (h)"] = "{:.1f} h"
            format_dict["Kwota za nadgodziny (PLN)"] = "{:.2f} zł"
            
            st.dataframe(overtime_pivot.style.format(format_dict), use_container_width=True)
            
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
            initial_pallet_df = calc_df[["Pracownik", "Stanowisko"]].copy()
            num_w = len(initial_pallet_df)
            share_w = (total_pallet_amount / num_w) if num_w > 0 and total_pallet_amount > 0 else 0.0
            initial_pallet_df["Kwota za załadunki (PLN)"] = share_w
            st.session_state.pallet_employees_df = initial_pallet_df
            st.session_state.pallet_table_period = period_key

        num_workers_pallets = len(st.session_state.pallet_employees_df)
        share_per_worker_pallet = (total_pallet_amount / num_workers_pallets) if num_workers_pallets > 0 and total_pallet_amount > 0 else 0.0
        st.session_state.pallet_employees_df["Kwota za załadunki (PLN)"] = share_per_worker_pallet

        edited_pallet_df = st.data_editor(
            st.session_state.pallet_employees_df,
            num_rows="delete",
            use_container_width=True,
            column_config={
                "Kwota za załadunki (PLN)": st.column_config.NumberColumn(
                    "Kwota za załadunki (PLN)",
                    format="%.2f zł",
                    disabled=True
                )
            },
            key="editor_pallets_workers"
        )

        if not edited_pallet_df.equals(st.session_state.pallet_employees_df):
            st.session_state.pallet_employees_df = edited_pallet_df

        st.markdown("---")
        st.subheader("🚜 Obsługa paleciaka")
        st.caption("Wpisz liczbę godzin przejeżdżonych przez poszczególnych pracowników. Kwota z puli (z Ustawień) zostanie podzielona proporcjonalnie do przepracowanych godzin.")
        
        st.info(f"Pula do podziału na obsługę paleciaka: **{st.session_state.pallet_pool:.2f} zł**")

        if 'pallet_truck_period' not in st.session_state or st.session_state.get('pallet_truck_period') != period_key:
            initial_pt_data = calc_df[["Pracownik", "Stanowisko"]].copy()
            initial_pt_data["Ilość godzin"] = 0.0
            initial_pt_data["Kwota (PLN)"] = 0.0
            st.session_state.pallet_truck_employees_df = initial_pt_data
            st.session_state.pallet_truck_period = period_key

        total_pt_hours = st.session_state.pallet_truck_employees_df["Ilość godzin"].sum()
        total_pt_pool = st.session_state.pallet_pool

        def calc_pt_amount(row):
            if total_pt_hours > 0:
                return (row["Ilość godzin"] / total_pt_hours) * total_pt_pool
            return 0.0

        st.session_state.pallet_truck_employees_df["Kwota (PLN)"] = st.session_state.pallet_truck_employees_df.apply(calc_pt_amount, axis=1)

        edited_pt_df = st.data_editor(
            st.session_state.pallet_truck_employees_df,
            num_rows="delete",
            use_container_width=True,
            column_config={
                "Ilość godzin": st.column_config.NumberColumn(
                    "Ilość godzin",
                    format="%.1f h",
                    min_value=0.0,
                    step=0.5,
                    help="Wpisz liczbę przepracowanych godzin"
                ),
                "Kwota (PLN)": st.column_config.NumberColumn(
                    "Kwota (PLN)",
                    format="%.2f zł",
                    disabled=True
                )
            },
            key="editor_pallet_truck_workers"
        )

        if not edited_pt_df.equals(st.session_state.pallet_truck_employees_df):
            st.session_state.pallet_truck_employees_df = edited_pt_df

        st.markdown("---")
        st.subheader("🌟 Premia Specjalna")
        st.caption("Dodaj indywidualne premie specjalne dla pracowników za ten okres.")

        edited_special_df = st.data_editor(
            st.session_state.special_bonuses_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Pracownik": st.column_config.SelectboxColumn(
                    "Pracownik",
                    options=calc_df["Pracownik"].tolist() if not calc_df.empty else [],
                    required=True
                ),
                "Kwota netto premii": st.column_config.NumberColumn(
                    "Kwota netto premii",
                    format="%.2f zł",
                    min_value=0.0,
                    step=50.0
                )
            },
            key="editor_special_bonuses"
        )
        if not edited_special_df.equals(st.session_state.special_bonuses_df):
            st.session_state.special_bonuses_df = edited_special_df

        st.markdown("---")
        st.subheader("📥 Generowanie Pasków i Archiwizacja")
        
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("📄 Generuj Paski w PDF dla wszystkich", type="primary", use_container_width=True):
                pdf_data = generate_pdf_slips(
                    calc_df, period_key, indicator, 
                    overtime_pivot, st.session_state.pallet_employees_df, 
                    st.session_state.pallet_truck_employees_df, 
                    st.session_state.special_bonuses_df
                )
                st.download_button(
                    label="⬇️ Pobierz plik PDF z paskami",
                    data=pdf_data,
                    file_name=f"Paski_premiowe_{period_key.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        with col_act2:
            if st.button("💾 Zapisz okres do Archiwum", use_container_width=True):
                st.session_state.history_v2[period_key] = {
                    "calc_df": calc_df,
                    "schedule_df": df_sched,
                    "overtime_df": overtime_pivot,
                    "pallet_df": st.session_state.pallet_employees_df,
                    "pt_df": st.session_state.pallet_truck_employees_df,
                    "special_df": st.session_state.special_bonuses_df,
                    "indicator": indicator
                }
                save_archive(st.session_state.history_v2)
                st.success(f"Okres '{period_key}' został pomyślnie zarchiwizowany!")

# ==========================================
# ZAKŁADKA 3: DASHBOARD I WYKRESY
# ==========================================
with tab_dash:
    st.header("📊 Dashboard i Analiza Danych v2")
    if st.session_state.current_schedule_df.empty:
        st.warning("Najpierw wygeneruj harmonogram i uzupełnij dane w poprzednich zakładkach.")
    else:
        if 'current_calc_df' in st.session_state and not st.session_state.current_calc_df.empty:
            df_c = st.session_state.current_calc_df
            fig = px.bar(df_c, x="Pracownik", y="Premia netto (PLN)", color="Stanowisko", title="Wysokość premii netto dla pracowników")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Przejdź do zakładki Kalkulator Premii, aby wyliczyć dane do wykresów.")

# ==========================================
# ZAKŁADKA 4: ARCHIWUM HISTORYCZNE
# ==========================================
with tab_history:
    st.header("📁 Archiwum Historyczne v2")
    if not st.session_state.history_v2:
        st.info("Brak zarchiwizowanych okresów w bazie.")
    else:
        arch_periods = list(st.session_state.history_v2.keys())
        selected_arch = st.selectbox("Wybierz okres z archiwum:", arch_periods, key="select_arch_period")
        if selected_arch:
            arch_data = st.session_state.history_v2[selected_arch]
            st.subheader(f"Dane dla okresu: {selected_arch}")
            st.metric("Wskaźnik Działu", f"{arch_data.get('indicator', 0)*100:.2f}%")
            if "calc_df" in arch_data:
                st.dataframe(arch_data["calc_df"], use_container_width=True)

# ==========================================
# ZAKŁADKA 5: PORÓWNANIE WYNIKÓW
# ==========================================
with tab_comp:
    st.header("📈 Porównanie Wyników v2")
    if len(st.session_state.history_v2) < 2:
        st.info("Zapisz co najmniej dwa okresy w archiwum, aby móc je porównać.")
    else:
        p_list = list(st.session_state.history_v2.keys())
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p1 = st.selectbox("Okres 1:", p_list, index=0, key="comp_p1")
        with col_p2:
            p2 = st.selectbox("Okres 2:", p_list, index=min(1, len(p_list)-1), key="comp_p2")
        
        if p1 and p2:
            ind1 = st.session_state.history_v2[p1].get("indicator", 0) * 100
            ind2 = st.session_state.history_v2[p2].get("indicator", 0) * 100
            st.metric(f"Wskaźnik {p1}", f"{ind1:.2f}%")
            st.metric(f"Wskaźnik {p2}", f"{ind2:.2f}%", delta=f"{ind2 - ind1:.2f}%")

# ==========================================
# ZAKŁADKA 6: USTAWIENIA
# ==========================================
with tab_settings:
    st.header("⚙️ Ustawienia Systemu v2")
    st.subheader("Średnie 12-miesięczne (baza do wskaźnika)")
    st.session_state.avg_lines_12m = st.number_input("Średnia liczba pozycji 12m:", value=st.session_state.avg_lines_12m, key="set_avg_lines")
    st.session_state.w_lines = st.number_input("Waga pozycji (%):", value=st.session_state.w_lines, key="set_w_lines")
    
    st.session_state.avg_pcs_12m = st.number_input("Średnia sztuk 12m:", value=st.session_state.avg_pcs_12m, key="set_avg_pcs")
    st.session_state.w_pcs = st.number_input("Waga sztuk (%):", value=st.session_state.w_pcs, key="set_w_pcs")
    
    st.session_state.avg_weight_12m = st.number_input("Średnia waga 12m:", value=st.session_state.avg_weight_12m, key="set_avg_weight")
    st.session_state.w_weight = st.number_input("Waga wagi (%):", value=st.session_state.w_weight, key="set_w_weight")

    st.subheader("Stawki Nadgodzin i Palet")
    st.session_state.ot_kierownik = st.number_input("Nadgodziny Kierownik (zł/h):", value=st.session_state.ot_kierownik, key="set_ot_kier")
    st.session_state.ot_brygadzista = st.number_input("Nadgodziny Brygadzista (zł/h):", value=st.session_state.ot_brygadzista, key="set_ot_bryg")
    st.session_state.ot_magazynier = st.number_input("Nadgodziny Magazynier (zł/h):", value=st.session_state.ot_magazynier, key="set_ot_mag")
    st.session_state.rate_pallet = st.number_input("Stawka za paletę (zł):", value=st.session_state.rate_pallet, key="set_rate_pal")
    st.session_state.pallet_pool = st.number_input("Pula na obsługę paleciaka (zł):", value=st.session_state.pallet_pool, key="set_pal_pool")

    st.subheader("Zarządzanie Pracownikami i Grupami")
    st.session_state.employees_df = st.data_editor(st.session_state.employees_df, num_rows="dynamic", use_container_width=True, key="set_employees_editor")
    st.session_state.groups_df = st.data_editor(st.session_state.groups_df, num_rows="dynamic", use_container_width=True, key="set_groups_editor")
