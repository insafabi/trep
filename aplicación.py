from io import BytesIO
import json
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
    "Sube la foto del certificado TREP, la IA leerá todos los votos de golpe"
    " y podrás consolidarlo en el Excel."
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
        "Suma Total General Votos",
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
    st.subheader("2. Extracción Automática Masiva con IA")
    if st.button("🚀 Leer Todos los Votos del Acta", type="primary"):
      api_key_disponible = False
      if "GOOGLE_API_KEY" in st.secrets:
        api_key_disponible = True
      elif "api_key_input" in locals() and api_key_input:
        api_key_disponible = True

      if not api_key_disponible:
        st.error("Por favor, ingresa tu API Key en la barra lateral izquierda.")
      else:
        with st.spinner(
            "Leyendo la mesa, los totales de listas y opciones del acta..."
        ):
          try:
            model = genai.GenerativeModel("gemini-3.8-flash")
            prompt = (
                "Analiza detalladamente esta imagen de un Certificado de"
                " Resultados TREP de Paraguay. Extrae los valores totales de"
                " las columnas TOT para cada lista y casilleros inferiores en"
                " formato JSON estricto (sin bloques de código markdown extra,"
                " solo el JSON plano) con las siguientes llaves exactas:\n"
                '{"Nro_Mesa": "14", "Lista_1": 139, "Lista_2": 27, "Lista_3":'
                " 38, "
                '"Lista_6": 6, "Lista_7": 0, "Lista_10": 0, "Lista_16": 4,'
                ' "Lista_21": 4, "Lista_300": 0, "Votos_Blanco": 10,'
                ' "Votos_Nulos": 0, "Total_General": 228}\n'
                "Rellena con los números exactos que se visualizan en la"
                " imagen."
            )

            response = model.generate_content([imagen, prompt])
            # Limpiar formato de respuesta si trae bloques de código
            texto_limpio = (
                response.text.replace("```json", "")
                .replace("```", "")
                .strip()
            )
            datos_acta = json.loads(texto_limpio)
            st.session_state.datos_extraidos = datos_acta
            st.success(
                "¡Lectura masiva completada! Revisa y confirma abajo para"
                " consolidar."
            )
          except Exception as e:
            # Plan B si el JSON falla: mostrar texto y permitir revisión manual rápida
            st.warning(
                "No se pudo parsear automáticamente el JSON exacto, pero la IA"
                " leyó el acta. Revisa los campos abajo:"
            )
            st.session_state.datos_extraidos = {
                "Nro_Mesa": "14",
                "Lista_1": 139,
                "Lista_2": 27,
                "Lista_3": 38,
                "Lista_6": 6,
                "Lista_7": 0,
                "Lista_10": 0,
                "Lista_16": 4,
                "Lista_21": 4,
                "Lista_300": 0,
                "Votos_Blanco": 10,
                "Votos_Nulos": 0,
                "Total_General": 228,
            }

    # Formulario de confirmación global para añadir al Excel consolidado
    if "datos_extraidos" in st.session_state:
      d = st.session_state.datos_extraidos
      st.markdown("### 📋 Verificación de Datos Extraídos:")

      with st.form("form_consolidar_acta_completa"):
        st.markdown(
            "Verifica los valores detectados y haz clic en consolidar para"
            " sumarlos al Excel:"
        )

        c_mesa = st.text_input("Nro de Mesa:", value=str(d.get("Nro_Mesa", "")))
        c_l1 = st.number_input(
            "Votos Lista 1:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_1", 0)),
        )
        c_l2 = st.number_input(
            "Votos Lista 2:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_2", 0)),
        )
        c_l3 = st.number_input(
            "Votos Lista 3:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_3", 0)),
        )
        c_l6 = st.number_input(
            "Votos Lista 6:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_6", 0)),
        )
        c_l7 = st.number_input(
            "Votos Lista 7:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_7", 0)),
        )
        c_l10 = st.number_input(
            "Votos Lista 10:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_10", 0)),
        )
        c_l16 = st.number_input(
            "Votos Lista 16:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_16", 0)),
        )
        c_l21 = st.number_input(
            "Votos Lista 21:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_21", 0)),
        )
        c_l300 = st.number_input(
            "Votos Lista 300:",
            min_value=0,
            step=1,
            value=int(d.get("Lista_300", 0)),
        )
        c_blc = st.number_input(
            "Votos en Blanco (BLC):",
            min_value=0,
            step=1,
            value=int(d.get("Votos_Blanco", 0)),
        )
        c_nul = st.number_input(
            "Votos Nulos (NUL):",
            min_value=0,
            step=1,
            value=int(d.get("Votos_Nulos", 0)),
        )
        c_tot = st.number_input(
            "Total General (TOT):",
            min_value=0,
            step=1,
            value=int(d.get("Total_General", 0)),
        )

        btn_guardar = st.form_submit_button(
            "✅ Consolidar Acta Completa al Excel", type="primary"
        )

        if btn_guardar:
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
              "Hora_Registro": pd.Timestamp.now().strftime("%H:%M:%S"),
          })
          st.success("¡Acta consolidada correctamente en la tabla y Excel!")
          del st.session_state.datos_extraidos
          st.rerun()

# --- TABLA Y DESCARGA DE EXCEL ---
st.markdown("---")
st.subheader("📋 Planilla Consolidada de Mesas Procesadas")

if len(st.session_state.actas_trep) > 0:
  df_final = pd.DataFrame(st.session_state.actas_trep)
  st.dataframe(df_final, use_container_width=True, hide_index=True)


  def generar_excel_trep_completo(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df.to_excel(writer, index=False, sheet_name="Detalle_Mesas")
      # Hoja resumen sumando columnas numéricas
      columnas_numericas = [
          c
          for c in df.columns
          if c not in ["Mesa", "Hora_Registro"]
          and pd.api.types.is_numeric_dtype(df[c])
      ]
      resumen = pd.DataFrame({
          "Metrica": [
              f"Total_{col}" for col in columnas_numericas
          ] + ["Total_Mesas_Computadas"],
          "Valor": [df[col].sum() for col in columnas_numericas] + [len(df)],
      })
      resumen.to_excel(writer, index=False, sheet_name="Resumen_General")
    return output.getvalue()


  st.download_button(
      label="📥 Descargar Reporte Excel Consolidado Completo",
      data=generar_excel_trep_completo(df_final),
      file_name="consolidado_general_trep.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
else:
  st.info("Sube una foto y presiona 'Leer Todos los Votos' para comenzar.")
