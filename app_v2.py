import io
import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# 1. KONFIGURACJA STRONY
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="System Harmonogramu Pracy",
    page_icon="📅",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. INICJALIZACJA BAZY DANYCH (SESSION STATE)
# -----------------------------------------------------------------------------
if "nieobecnosci" not in st.session_state:
    st.session_state.nieobecnosci = pd.DataFrame({
        "Powód nieobecności": [
            "Urlop wypoczynkowy",
            "L4 / Zwolnienie lekarskie",
            "Urlop na żądanie",
            "Opieka nad dzieckiem",
            "Nieobecność usprawiedliwiona"
        ]
    })

if "grupy" not in st.session_state:
    st.session_state.grupy = pd.DataFrame([
        {"Nazwa grupy": "GRUPA 1", "Czas pracy": "06:00-14:00"},
        {"Nazwa grupy": "GRUPA 2", "Czas pracy": "08:00-16:00"},
        {"Nazwa grupy": "GRUPA 3", "Czas pracy": "11:00-19:00"},
        {"Nazwa grupy": "GRUPA 4", "Czas pracy": "08:00-16:00"},
        {"Nazwa grupy": "GRUPA 5", "Czas pracy": "08:00-16:00"},
        {"Nazwa grupy": "GRUPA 6", "Czas pracy": "11:00-19:00"},
        {"Nazwa grupy": "GRUPA 7", "Czas pracy": "08:00-17:00"}
    ])

if "pracownicy" not in st.session_state:
    st.session_state.pracownicy = pd.DataFrame([
        {"Imię i nazwisko": "ADRIAN WRONA", "Grupa": "GRUPA 4", "Przedział dni pracujących": "WTOREK-SOBOTA", "Stanowisko": "MAGAZYNIER", "Funkcja": "1 SKANOWANIE"},
        {"Imię i nazwisko": "ANTON FEDOSOV", "Grupa": "GRUPA 3", "Przedział dni pracujących": "PONIEDZIAŁEK-PIĄTEK", "Stanowisko": "MAGAZYNIER", "Funkcja": "1 SKANOWANIE"},
        {"Imię i nazwisko": "JAKUB JANECZEK", "Grupa": "GRUPA 2", "Przedział dni pracujących": "PONIEDZIAŁEK-PIĄTEK", "Stanowisko": "BRYGADZISTA", "Funkcja": "2 SKANOWANIE"},
        {"Imię i nazwisko": "JAKUB RĘBACZ", "Grupa": "GRUPA 4", "Przedział dni pracujących": "WTOREK-SOBOTA", "Stanowisko": "MAGAZYNIER", "Funkcja": "1 SKANOWANIE"},
        {"Imię i nazwisko": "KYRYLO BZHEZITSKYI", "Grupa": "GRUPA 1", "Przedział dni pracujących": "WTOREK-SOBOTA", "Stanowisko": "BRYGADZISTA", "Funkcja": "1 SKANOWANIE"},
        {"Imię i nazwisko": "MACIEJ BORZĘCKI", "Grupa": "GRUPA 3", "Przedział dni pracujących": "WTOREK-SOBOTA", "Stanowisko": "MAGAZYNIER", "Funkcja": "1 SKANOWANIE"},
        {"Imię i nazwisko": "MICHAŁ KWIATKOWSKI", "Grupa": "GRUPA 7", "Przedział dni pracujących": "PONIEDZIAŁEK-PIĄTEK", "Stanowisko": "KIEROWNIK", "Funkcja": "KIEROWNIK"}
    ])

# -----------------------------------------------------------------------------
# 3. NAWIGACJA GŁÓWNA
# -----------------------------------------------------------------------------
st.title("📅 System Zarządzania Harmonogramem")

main_tab1, main_tab2, main_tab3 = st.tabs([
    "📋 Harmonogram Główny", 
    "📊 Statystyki i Raporty", 
    "⚙️ Ustawienia"
])

# -----------------------------------------------------------------------------
# TAB 1: HARMONOGRAM GŁÓWNY
# -----------------------------------------------------------------------------
with main_tab1:
    st.header("Podgląd Harmonogramu")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        wybrany_miesiac = st.date_input("Wybierz miesiąc/rok", value=datetime.date.today())
        st.info(f"Wybrany okres: **{wybrany_miesiac.strftime('%B %Y')}**")
    
    # Łączenie danych pracowników z informacją o godzinach grupy
    df_merged = st.session_state.pracownicy.merge(
        st.session_state.grupy, 
        left_on="Grupa", 
        right_on="Nazwa grupy", 
        how="left"
    ).drop(columns=["Nazwa grupy"], errors="ignore")
    
    st.subheader("Bieżąca obsada zespołu")
    st.dataframe(df_merged, use_container_width=True)

    # Funkcja generująca plik Excel do pobrania
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_merged.to_excel(writer, index=False, sheet_name="Harmonogram")
    
    st.download_button(
        label="📥 Pobierz Harmonogram (Excel)",
        data=output.getvalue(),
        file_name=f"harmonogram_{wybrany_miesiac.strftime('%Y_%m')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -----------------------------------------------------------------------------
# TAB 2: STATYSTYKI I RAPORTY
# -----------------------------------------------------------------------------
with main_tab2:
    st.header("Podsumowanie zespołu")
    
    if not st.session_state.pracownicy.empty:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Podział wg Stanowisk")
            fig_stanowiska = px.pie(
                st.session_state.pracownicy, 
                names="Stanowisko", 
                title="Struktura stanowisk"
            )
            st.plotly_chart(fig_stanowiska, use_container_width=True)
            
        with col_chart2:
            st.subheader("Liczebność Grup")
            fig_grupy = px.bar(
                st.session_state.pracownicy["Grupa"].value_counts().reset_index(),
                x="Grupa", 
                y="count",
                labels={"count": "Liczba pracowników", "Grupa": "Grupa"},
                title="Liczba osób w grupach"
            )
            st.plotly_chart(fig_grupy, use_container_width=True)
    else:
        st.warning("Brak danych o pracownikach do wyświetlenia statystyk.")

# -----------------------------------------------------------------------------
# TAB 3: KARTA USTAWIEŃ
# -----------------------------------------------------------------------------
with main_tab3:
    st.header("⚙️ Konfiguracja Modułów")
    
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "🚫 Powody nieobecności", 
        "🕒 Grupy i godziny pracy", 
        "👥 Pracownicy"
    ])

    # Sub-tab 1: Powody nieobecności
    with sub_tab1:
        st.subheader("Lista powodów nieobecności")
        st.caption("Dodawaj nowe pozycje na dole tabeli lub usuwaj zaznaczone wiersze klawiszem Delete.")
        
        st.session_state.nieobecnosci = st.data_editor(
            st.session_state.nieobecnosci,
            num_rows="dynamic",
            use_container_width=True,
            key="edytor_nieobecnosci"
        )

    # Sub-tab 2: Lista Grup
    with sub_tab2:
        st.subheader("Zarządzanie grupami i czasem pracy")
        st.caption("Zmiany nazw grup zostaną odzwierciedlone w liście wyboru dla pracowników.")
        
        st.session_state.grupy = st.data_editor(
            st.session_state.grupy,
            num_rows="dynamic",
            use_container_width=True,
            key="edytor_grupy"
        )

    # Sub-tab 3: Lista Pracowników
    with sub_tab3:
        st.subheader("Zarządzanie kadrami")
        st.caption("Przypisuj grupy, harmonogramy i funkcje do poszczególnych osób.")
        
        # Lista dostępnych grup do rozwijanego menu w tabeli
        opcje_grup = st.session_state.grupy["Nazwa grupy"].dropna().unique().tolist()
        
        st.session_state.pracownicy = st.data_editor(
            st.session_state.pracownicy,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Grupa": st.column_config.SelectboxColumn(
                    "Grupa",
                    help="Wybierz grupę z listy definiowalnej w zakładce obok",
                    options=opcje_grup,
                    required=True
                )
            },
            key="edytor_pracownicy"
        )
