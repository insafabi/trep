from io import BytesIO
import json
import google.generativeai as genai
import pandas as pd
from PIL import Image
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Lector de Actas TREP por Opciones - IA", page_icon="🗳️", layout="wide"
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

st.title("🗳️ Lector Automático de Certificados TREP (Desglose por Opciones)")
st.markdown(
    "Sube la foto del certificado TREP, la IA extraerá todas las opciones de"
    " cada lista de forma masiva y consolidará el reporte."
)

# Inicializar almacenamiento de actas/opciones en sesión
if "actas_opciones" not in st.session_state:
  st.session_state.actas_opciones = []

# --- PANEL LATERAL ---
with st.sidebar:
  st.header("📊 Consolidado General")
  if len(st.session_state.actas_opciones) > 0:
    df_res = pd.DataFrame(st.session_state.actas_opciones)
    st.metric("Registros (Listas/Opciones)", f"{len(df_res):,}")
    st.metric(
        "Suma Total de Votos",
        f"{int(df_res['Votos'].sum() if 'Votos' in df_res else 0):,}",
    )

    if st.button("🗑️ Reiniciar Todo", type="primary"):
      st.session_state.actas_opciones = []
      st.rerun()
  else:
    st.info("Sin registros procesados aún.")

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
    st.subheader("2. Extracción Masiva de Opciones con IA")
    if st.button("🚀 Leer Todas las Listas y Opciones", type="primary"):
      api_key_disponible = False
      if "GOOGLE_API_KEY" in st.secrets:
        api_key_disponible = True
      elif "api_key_input" in locals() and api_key_input:
        api_key_disponible = True

      if not api_key_disponible:
        st.error("Por favor, ingresa tu API Key en la barra lateral izquierda.")
      else:
        with st.spinner(
            "Extrayendo la mesa y el detalle de cada opción por lista..."
        ):
          try:
            model = genai.GenerativeModel("gemini-3.8-flash")
            prompt = (
                "Analiza detalladamente esta imagen de un Certificado de"
                " Resultados TREP de Paraguay. Identifica el número de mesa"
                " (Nro_Mesa) y recorre toda la cuadrícula de preferencias"
                " (LI/OPC). Extrae cada combinación de Lista, Opción y la"
                " cantidad de Votos registrados.\n"
                "Devuelve la respuesta EXCLUSIVAMENTE en formato JSON de lista"
                " de objetos, sin texto adicional ni bloques de markdown"
                " extra, siguiendo exactamente esta estructura de ejemplo:\n"
                "[\n"
                '  {"Nro_Mesa": "14", "Lista": "1", "Opc": 1, "Votos": 12},\n'
                '  {"Nro_Mesa": "14", "Lista": "1", "Opc": 2, "Votos": 5},\n'
                '  {"Nro_Mesa": "14", "Lista": "2", "Opc": 1, "Votos": 8}\n'
                "]"
            )

            response = model.generate_content([imagen, prompt])
            texto_limpio = (
                response.text.replace("```json", "")
                .replace("```", "")
                .strip()
            )
            lista_datos = json.loads(texto_limpio)
            st.session_state.opciones_extraidas = lista_datos
            st.success(
                "¡Lectura de opciones completada con éxito! Revisa abajo para"
                " consolidar."
            )
          except Exception as e:
            st.error(
                f"No se pudo interpretar automáticamente la respuesta como JSON"
                f" estructurado. Error: {e}"
            )
            # Guardamos texto bruto por si acaso para revisión visual
            st.session_state.texto_ia_crudo = response.text

    # Si la IA trajo los datos segmentados, permitimos confirmarlos y agregarlos al consolidado
    if "opciones_extraidas" in st.session_state:
      st.markdown("### 📋 Vista Previa de Opciones Detectadas:")
      df_previo = pd.DataFrame(st.session_state.opciones_extraidas)
      st.dataframe(df_previo, use_container_width=True, hide_index=True)

      if st.button(
          "✅ Consolidar Todas estas Opciones al Excel", type="primary"
      ):
        for item in st.session_state.opciones_extraidas:
          st.session_state.actas_opciones.append({
              "Mesa": str(item.get("Nro_Mesa", "S/N")),
              "Lista": str(item.get("Lista", "")),
              "Opción": int(item.get("Opc", 0)),
              "Votos": int(item.get("Votos", 0)),
              "Hora": pd.Timestamp.now().strftime("%H:%M:%S"),
          })
        st.success(
            "¡Todas las opciones fueron agregadas al consolidado general!"
        )
        del st.session_state.opciones_extraidas
        st.rerun()

    elif "texto_ia_crudo" in st.session_state:
      st.warning(
          "Resultado en texto bruto devuelto por la IA debido a un fallo de"
          " formato:"
      )
      st.text(st.session_state.texto_ia_crudo)

# --- TABLA Y DESCARGA DE EXCEL ---
st.markdown("---")
st.subheader("📋 Planilla Consolidada por Listas y Opciones")

if len(st.session_state.actas_opciones) > 0:
  df_final = pd.DataFrame(st.session_state.actas_opciones)
  st.dataframe(df_final, use_container_width=True, hide_index=True)


  def generar_excel_segmentado(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      # Hoja 1: Detalle completo por opción
      df.to_excel(writer, index=False, sheet_name="Detalle_Opciones")
      # Hoja 2: Resumen agrupado por Mesa y Lista
      resumen_lista = (
          df.groupby(["Mesa", "Lista"])["Votos"].sum().reset_index()
      )
      resumen_lista.columns = ["Mesa", "Lista", "Total_Votos_Lista"]
      resumen_lista.to_excel(writer, index=False, sheet_name="Resumen_Por_Lista")
    return output.getvalue()


  st.download_button(
      label="📥 Descargar Reporte Excel Consolidado (Segmentado)",
      data=generar_excel_segmentado(df_final),
      file_name="consolidado_trep_segmentado_por_opcion.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
else:
  st.info(
      "Sube una foto y presiona 'Leer Todas las Listas y Opciones' para"
      " comenzar."
  )
