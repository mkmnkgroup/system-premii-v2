import streamlit as st
import pandas as pd

st.set_page_config(page_title="Ustawienia Harmonogramu", layout="wide")

# -----------------------------------------------------------------------------
# 1. INICJALIZACJA DANYCH W SESSION STATE (ładuje dane domyślne przy starcie)
# -----------------------------------------------------------------------------
if "nieobecnosci" not in st.session_state:
    st.session_state.nieobecnosci = pd.DataFrame({
        "Powód nieobecności": [
            "Urlop wypoczynkowy", 
            "L4 / Zwolnienie lekarskie", 
            "Urlop na żądanie", 
            "Opieka", 
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
# 2. WIDOK ZAKŁADEK USTAWIEŃ
# -----------------------------------------------------------------------------
st.title("⚙️ Karta Ustawień Harmonogramu")

tab_nieobecnosci, tab_grupy, tab_pracownicy = st.tabs([
    "🚫 Powody nieobecności", 
    "🕒 Grupy i godziny pracy", 
    "👥 Pracownicy"
])

# KARTA 1: Powody nieobecności
with tab_nieobecnosci:
    st.subheader("Lista powodów nieobecności")
    st.caption("Możesz edytować istniejące pozycje, dodawać nowe na dole tabeli lub usuwać wybrane wiersze.")
    
    st.session_state.nieobecnosci = st.data_editor(
        st.session_state.nieobecnosci,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_nieobecnosci"
    )

# KARTA 2: Lista Grup
with tab_grupy:
    st.subheader("Lista grup i czasy pracy")
    st.caption("Modyfikuj godziny, zmieniaj nazwy grup lub dodawaj nowe wiersze.")
    
    st.session_state.grupy = st.data_editor(
        st.session_state.grupy,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_grupy"
    )

# KARTA 3: Lista Pracowników
with tab_pracownicy:
    st.subheader("Lista pracowników i przypisania")
    st.caption("Kolumna 'Grupa' automatycznie podpowiada grupy zaktualizowane w poprzedniej zakładce.")
    
    # Dynamiczne pobranie dostępnych grup do listy rozwijanej w tabeli
    aktualne_grupy = st.session_state.grupy["Nazwa grupy"].dropna().unique().tolist()
    
    st.session_state.pracownicy = st.data_editor(
        st.session_state.pracownicy,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Grupa": st.column_config.SelectboxColumn(
                "Grupa",
                help="Wybierz grupę z listy",
                options=aktualne_grupy,
                required=True
            )
        },
        key="editor_pracownicy"
    )
