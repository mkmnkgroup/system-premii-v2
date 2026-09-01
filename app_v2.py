import streamlit as st
import pandas as pd
import io

# ---------------------------------------------------------
# 1. Konfiguracja strony
# ---------------------------------------------------------
st.set_page_config(
    page_title="System Premii v2",
    page_icon="📊",
    layout="wide"
)

st.title("📊 System Rozliczania Premii v2")
st.markdown("---")

# ---------------------------------------------------------
# 2. Inicjalizacja stanj sesji (Session State)
# ---------------------------------------------------------
if "forklift_df" not in st.session_state:
    st.session_state["forklift_df"] = None

if "summary_df" not in st.session_state:
    st.session_state["summary_df"] = None

# ---------------------------------------------------------
# 3. Pasek boczny - Wgrywanie danych
# ---------------------------------------------------------
st.sidebar.header("📂 Import Danych")

uploaded_file = st.sidebar.file_content = st.sidebar.file_uploader(
    "Wgraj plik z danymi (Excel lub CSV)",
    type=["xlsx", "xls", "csv"]
)

stk_rate = st.sidebar.number_input("Stawka bazowa za roboczogodzinę (PLN)", value=25.0, step=0.5)
bonus_target = st.sidebar.number_input("Cel wydajności (%)", value=100.0, step=5.0)

# ---------------------------------------------------------
# 4. Przetwarzanie i ładowanie pliku
# ---------------------------------------------------------
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        st.session_state["forklift_df"] = df
        st.sidebar.success("Plik wczytano pomyślnie!")
    except Exception as e:
        st.sidebar.error(f"Błąd podczas wczytywania pliku: {e}")

# ---------------------------------------------------------
# 5. Główna logika aplikacji
# ---------------------------------------------------------
# Poniższy warunek sprawdza obecność ramki danych w session_state (poprawna składnia):
if "forklift_df" in st.session_state and st.session_state["forklift_df"] is not None:
    
    df = st.session_state["forklift_df"]

    st.subheader("📋 Podgląd wczytanych danych")
    st.dataframe(df.head(10), use_container_width=True)

    st.markdown("---")
    st.subheader("⚙️ Kalkulacja Premii")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Liczba rekordów", value=len(df))
    with col2:
        st.metric(label="Stawka bazowa", value=f"{stk_rate} PLN/h")
    with col3:
        st.metric(label="Docelowa wydajność", value=f"{bonus_target}%")

    # Przykładowe wyliczenia (dostosuj kolumny do struktury swoich danych)
    # Sprawdzamy czy wymagane kolumny istnieją w df
    required_cols = ["Pracownik", "Godziny", "Wykonanie_%"]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.warning(f"Brakujące kolumny w pliku do automatycznego przeliczenia: {missing_cols}")
        st.info("Poniżej dostępny jest tryb edycji/mapowania danych.")
    else:
        # Kalkulacja premii
        calc_df = df.copy()
        
        # Wyliczenie premii uzależnione od przekroczenia celu
        calc_df["Premia_%"] = calc_df["Wykonanie_%"].apply(
            lambda x: max(0.0, (x - bonus_target) * 0.5) if x >= bonus_target else 0.0
        )
        calc_df["Kwota_Premia"] = (calc_df["Godziny"] * stk_rate) * (calc_df["Premia_%"] / 100.0)
        calc_df["Wynagrodzenie_Total"] = (calc_df["Godziny"] * stk_rate) + calc_df["Kwota_Premia"]

        st.session_state["summary_df"] = calc_df

        st.subheader("🏆 Wyniki przeliczenia premii")
        st.dataframe(
            calc_df[["Pracownik", "Godziny", "Wykonanie_%", "Premia_%", "Kwota_Premia", "Wynagrodzenie_Total"]],
            use_container_width=True
        )

        # ---------------------------------------------------------
        # 6. Eksport danych
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("📥 Eksport Wyników")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            calc_df.to_excel(writer, index=False, sheet_name='Premie')
        
        st.download_button(
            label="📄 Pobierz raport w Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name="raport_premii_v2.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👆 Wgraj plik z danymi w panelu bocznym po lewej stronie, aby rozpocząć wyliczanie premii.")
