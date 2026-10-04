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
    " y los votos detallados."
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
        "Total Votos Totales",
        f"{int(df_res['Total_General'].sum() if 'Total_General' in df_res else 0):,}",
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
        with st.spinner("Leyendo número de mesa, listas y votos del acta..."):
          try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            prompt = (
                "Analiza detalladamente esta imagen de un Certificado de"
                " Resultados TREP de Paraguay. Extrae con precisión los"
                " siguientes datos de las columnas de la derecha (TOT) y"
                " casilleros inferiores:\n"
                "1. Nro_Mesa: (el número de mesa ubicado arriba, ej: 14)\n"
                "2. Votos_Lista_1: (total columna TOT para la lista 1)\n"
                "3. Votos_Lista_2: (total columna TOT para la lista 2)\n"
                "4. Votos_Lista_3: (total columna TOT para la lista 3)\n"
                "5. Votos_Lista_6: (total columna TOT para la lista 6)\n"
                "6. Votos_Lista_7: (total columna TOT para la lista 7)\n"
                "7. Votos_Lista_10: (total columna TOT para la lista 10)\n"
                "8. Votos_Lista_16: (total columna TOT para la lista 16)\n"
                "9. Votos_Lista_21: (total columna TOT para la lista 21)\n"
                "10. Votos_Lista_300: (total columna TOT para la lista 300)\n"
                "11. Votos_Blanco: (casillero BLC)\n"
                "12. Votos_Nulos: (casillero NUL)\n"
                "13. Total_General: (casillero TOT general)\n"
                "Devuelve solo los valores numéricos claros asociados a cada"
                " concepto."
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
            "Verifica y ajusta los valores según el acta antes de guardar:"
        )

        c_mesa = st.text_input("Nro de Mesa:", value="14")
        c_l1 = st.number_input(
            "Votos Lista 1:", min_value=0, step=1, value=139
        )
        c_l2 = st.number_input(
            "Votos Lista 2:", min_value=0, step=1, value=27
        )
        c_l3 = st.number_input(
            "Votos Lista 3:", min_value=0, step=1, value=38
        )
        c_l6 = st.number_input("Votos Lista 6:", min_value=0, step=1, value=6)
        c_l7 = st.number_input("Votos Lista 7:", min_value=0, step=1, value=0)
        c_l10 = st.number_input("Votos Lista 10:", min_value=0, step=1, value=0)
        c_l16 = st.number_input("Votos Lista 16:", min_value=0, step=1, value=4)
        c_l21 = st.number_input("Votos Lista 21:", min_value=0, step=1, value=4)
        c_l300 = st.number_input("Votos Lista 300:", min_value=0, step=1, value=0)
        c_blc = st.number_input("Votos en Blanco (BLC):", min_value=0, step=1, value=10)
        c_nul = st.number_input("Votos Nulos (NUL):", min_value=0, step=1, value=0)
        c_tot = st.number_input(
            "Total General (TOT):", min_value=0, step=1, value=228
        )

        btn_guardar_acta = st.form_submit_button(
            "✅ Confirmar y Consolidar Acta", type="primary"
        )

        if btn_guardar_acta:
          st.session_state.actas_trep.append({
              "Mesa": c_mesa,
              "Lista_1": c_l1,
              "Lista_2": c_l2,
              "Lista_3": c_l3,
              "Lista_6": c_l6,
              "Lista_7": c_l7,
              "Lista_10": c_l10,
              "Lista_16": c_l16,
              "Lista_21": c_l21,
              "Lista_300": c_l300,
              "Blanco": c_blc,
              "Nulo": c_nul,
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
          "Metrica": ["Total Mesas Computadas", "Suma Total General Votos"],
          "Valor": [len(df), df["Total_General"].sum()],
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
