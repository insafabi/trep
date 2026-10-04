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
    "Sube la foto del certificado TREP y la IA extraerá los votos desglosados"
    " por Lista y Opción."
)

# Inicializar almacenamiento de actas en sesión
if "actas_trep" not in st.session_state:
  st.session_state.actas_trep = []

# --- PANEL LATERAL ---
with st.sidebar:
  st.header("📊 Consolidado General")
  if len(st.session_state.actas_trep) > 0:
    df_res = pd.DataFrame(st.session_state.actas_trep)
    st.metric("Registros Procesados", f"{len(df_res)}")
    st.metric(
        "Suma Total Votos",
        f"{int(df_res['Votos'].sum() if 'Votos' in df_res else 0):,}",
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
    st.subheader("2. Extracción Automática con IA (Listas y Opciones)")
    if st.button("🚀 Leer Votos por Opción", type="primary"):
      api_key_disponible = False
      if "GOOGLE_API_KEY" in st.secrets:
        api_key_disponible = True
      elif "api_key_input" in locals() and api_key_input:
        api_key_disponible = True

      if not api_key_disponible:
        st.error("Por favor, ingresa tu API Key en la barra lateral izquierda.")
      else:
        with st.spinner(
            "Leyendo número de mesa y desglosando votos por lista y opción..."
        ):
          try:
            model = genai.GenerativeModel("gemini-3.8-flash")
            prompt = (
                "Analiza detalladamente esta imagen de un Certificado de"
                " Resultados TREP de Paraguay. El certificado contiene una"
                " cuadrícula llamada LI/OPC donde se cruzan las Listas"
                " (filas: 1, 2, 3, 6, 7, 10, 16, 21, 300) y las Opciones"
                " (columnas numeradas del 1 al 24).\n"
                "Extrae el número de mesa (Nro_Mesa) y lista todos los"
                " registros detallados en formato de tabla o lista clara que"
                " contengan:\n"
                "- Nro_Mesa\n"
                "- Lista (ej: 1, 2, etc.)\n"
                "- Opcion (ej: 1, 2, 3...)\n"
                "- Votos (cantidad de votos para esa opción específica de esa"
                " lista)\n"
                "Incluye también los totales generales: BLC (blancos), NUL"
                " (nulos) y TOT (total general)."
            )

            response = model.generate_content([imagen, prompt])
            st.session_state.ia_resultado = response.text
            st.success("¡Lectura de opciones completada!")
          except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")

    # Formulario de confirmación y desglose
    if "ia_resultado" in st.session_state:
      st.markdown("### 📋 Datos detectados por la IA:")
      st.info(st.session_state.ia_resultado)

      with st.form("form_confirmar_trep_opciones"):
        st.markdown(
            "Ingresa o verifica el detalle por Lista y Opción a registrar en el"
            " consolidado:"
        )

        c_mesa = st.text_input("Nro de Mesa:", value="14")
        c_lista = st.selectbox(
            "Número de Lista:", [1, 2, 3, 6, 7, 10, 16, 21, 300]
        )
        c_opcion = st.number_input(
            "Opción (Candidato/Preferencia):", min_value=1, max_value=24, step=1, value=1
        )
        c_votos = st.number_input(
            "Cantidad de Votos:", min_value=0, step=1, value=10
        )

        btn_guardar_item = st.form_submit_button(
            "✅ Registrar Opción en Consolidado", type="primary"
        )

        if btn_guardar_item:
          st.session_state.actas_trep.append({
              "Mesa": c_mesa,
              "Lista": c_lista,
              "Opción": c_opcion,
              "Votos": c_votos,
              "Hora": pd.Timestamp.now().strftime("%H:%M:%S"),
          })
          st.success("¡Opción registrada con éxito!")
          # No borramos ia_resultado de inmediato para seguir cargando opciones de la misma acta si se desea
          st.rerun()

# --- TABLA Y DESCARGA DE EXCEL ---
st.markdown("---")
st.subheader("📋 Planilla Consolidada por Listas y Opciones")

if len(st.session_state.actas_trep) > 0:
  df_final = pd.DataFrame(st.session_state.actas_trep)
  st.dataframe(df_final, use_container_width=True, hide_index=True)


  def generar_excel_trep_opciones(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df.to_excel(writer, index=False, sheet_name="Detalle_Votos_Opciones")
      resumen = df.groupby(["Mesa", "Lista"])["Votos"].sum().reset_index()
      resumen.columns = ["Mesa", "Lista", "Total_Votos_Lista"]
      resumen.to_excel(writer, index=False, sheet_name="Resumen_Por_Lista")
    return output.getvalue()


  st.download_button(
      label="📥 Descargar Reporte Excel Consolidado (Con Opciones)",
      data=generar_excel_trep_opciones(df_final),
      file_name="consolidado_trep_opciones_elecciones.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
else:
  st.info("Sube una foto y registra las opciones para comenzar la consolidación.")
