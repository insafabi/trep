from io import BytesIO
import google.generativeai as genai
import pandas as pd
from PIL import Image
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Lector de Actas TREP - IA", page_icon="🗳️", layout="wide"
)

# Configurar la API de Gemini mediante la barra lateral o secretos
if "GOOGLE_API_KEY" in st.secrets:
  genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
  api_key_input = st.sidebar.text_input(
      "Ingresa tu Google API Key:", type="password"
  )
  if api_key_input:
    genai.configure(api_key=api_key_input)

st.title("🗳️ Lector Automático de Certificados TREP con IA")
st.markdown(
    "Sube la foto del certificado TREP y la IA extraerá los datos de la mesa"
    " y los votos por agrupación."
)

# Inicializar almacenamiento de actas en sesión
if "actas_trep" not in st.session_state:
  st.session_state.actas_trep = []

# --- PANEL LATERAL ---
with st.sidebar:
  st.header("📊 Consolidado General")
  if len(st.session_state.actas_trep) > 0:
    df_res = pd.DataFrame(st.session_state.actas_trep)
    st.metric("Mesas Procesadas", f"{len(df_res)}")
    st.metric(
        "Total Votos Lista 2",
        f"{int(df_res['Votos_Lista_2'].sum() if 'Votos_Lista_2' in df_res else 0):,}",
    )

    if st.button("🗑️ Reiniciar Todo", type="primary"):
      st.session_state.actas_trep = []
      st.rerun()
  else:
    st.info("Sin actas procesadas aún.")

# --- INTERFAZ PRINCIPAL ---
st.subheader("1. Subir o Tomar Foto del Acta TREP")
archivo_foto = st.file_uploader(
    "Selecciona la foto del certificado TREP", type=["jpg", "jpeg", "png"]
)

if archivo_foto is not None:
  imagen = Image.open(archivo_foto)

  col1, col2 = st.columns(2)
  with col1:
    st.image(imagen, caption="Certificado TREP Cargado", use_column_width=True)

  with col2:
    st.subheader("2. Extracción Automática con IA")
    if st.button("🚀 Leer Datos del Acta", type="primary"):
      # Comprobar si hay API key configurada
      api_key_disponible = False
      if "GOOGLE_API_KEY" in st.secrets:
        api_key_disponible = True
      elif "api_key_input" in locals() and api_key_input:
        api_key_disponible = True

      if not api_key_disponible:
        st.error("Por favor, ingresa tu API Key en la barra lateral izquierda.")
      else:
        with st.spinner("Leyendo números, mesa y votos del acta..."):
          try:
            # Modelo actualizado de Gemini
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = (
                "Analiza esta imagen de un Certificado de Resultados TREP de"
                " Paraguay. Extrae estrictamente los siguientes valores en"
                " formato de texto clave-valor: 1. Nro_Mesa: (el número de"
                " mesa, ej: 13) 2. Votos_Lista_2: (los votos de HONOR"
                " COLORADO o lista 2) 3. Votos_Lista_7: (los votos de FUERZA Y"
                " CAUSA REPUBLICANA o lista 7) 4. Votos_Blanco: (votos en blanco"
                " / BLC) 5. Votos_Nulos: (votos nulos / NUL) 6. Total_General:"
                " (TOT)"
            )

            response = model.generate_content([imagen, prompt])
            st.session_state.ia_resultado = response.text
            st.success("¡Lectura de acta completada!")
          except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")

    # Formulario de confirmación con los datos extraídos
    if "ia_resultado" in st.session_state:
      st.markdown("### 📋 Datos detectados por la IA:")
      st.info(st.session_state.ia_resultado)

      with st.form("form_confirmar_trep"):
        st.markdown(
            "Verifica y ajusta los valores si es necesario antes de guardar:"
        )
        c_mesa = st.text_input("Nro de Mesa:", value="13")
        c_l2 = st.number_input(
            "Votos Lista 2 (Honor Colorado):", min_value=0, step=1, value=116
        )
        c_l7 = st.number_input(
            "Votos Lista 7:", min_value=0, step=1, value=44
        )
        c_blc = st.number_input(
            "Votos en Blanco (BLC):", min_value=0, step=1, value=4
        )
        c_nul = st.number_input(
            "Votos Nulos (NUL):", min_value=0, step=1, value=0
        )
        c_tot = st.number_input(
            "Total General (TOT):", min_value=0, step=1, value=166
        )

        btn_guardar_acta = st.form_submit_button(
            "✅ Confirmar y Consolidar Acta", type="primary"
        )

        if btn_guardar_acta:
          st.session_state.actas_trep.append({
              "Mesa": c_mesa,
              "Votos_Lista_2": c_l2,
              "Votos_Lista_7": c_l7,
              "Votos_Blanco": c_blc,
              "Votos_Nulos": c_nul,
              "Total_General": c_tot,
              "Hora": pd.Timestamp.now().strftime("%H:%M:%S"),
          })
          st.success("¡Acta consolidada con éxito!")
          del st.session_state.ia_resultado
          st.rerun()

# --- TABLA Y DESCARGA DE EXCEL ---
st.markdown("---")
st.subheader("📋 Planilla Consolidada de Mesas Procesadas")

if len(st.session_state.actas_trep) > 0:
  df_final = pd.DataFrame(st.session_state.actas_trep)
  st.dataframe(df_final, use_container_width=True, hide_index=True)


  def generar_excel_trep(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df.to_excel(writer, index=False, sheet_name="Detalle_Mesas")
      resumen = pd.DataFrame({
          "Metrica": [
              "Total Mesas Computadas",
              "Total Votos Lista 2",
              "Total Votos Lista 7",
              "Total Blancos",
              "Total Nulos",
          ],
          "Valor": [
              len(df),
              df["Votos_Lista_2"].sum(),
              df["Votos_Lista_7"].sum(),
              df["Votos_Blanco"].sum(),
              df["Votos_Nulos"].sum(),
          ],
      })
      resumen.to_excel(writer, index=False, sheet_name="Resumen_General")
    return output.getvalue()


  st.download_button(
      label="📥 Descargar Reporte Excel Consolidado",
      data=generar_excel_trep(df_final),
      file_name="consolidado_trep_elecciones.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
else:
  st.info("Sube la foto de un certificado TREP para comenzar el registro.")
