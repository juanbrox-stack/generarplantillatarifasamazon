import streamlit as st
import pandas as pd
import io

def procesar_tarifas(df_origen, pais):
    # Asumimos que Columna A es SKU y Columna B es Price (PVP)
    df_origen.columns = ['sku_original', 'price_base']
    
    filas_finales = []
    
    # Definir prefijos según el país seleccionado
    prefijos = ["0", "S0"]
    if pais != "ES":
        prefijos.extend([f"{pais}0", f"S{pais}0"])

    for index, row in df_origen.iterrows():
        sku_base = str(row['sku_original']).strip()
        # Limpiar el SKU si ya trae ceros o letras para estandarizarlo
        # (Dependiendo de tu origen, esto se puede ajustar)
        
        precio = float(row['price_base'])
        
        # Lógica de precios solicitada
        min_price = precio - 1
        max_price = precio + 1
        bus_price = precio - 1
        
        for pref in prefijos:
            # Crear la fila cumplimentando la plantilla
            nueva_fila = {
                "sku": f"{pref}{sku_base}",
                "price": precio,
                "minimum-seller-allowed-price": min_price,
                "maximum-seller-allowed-price": max_price,
                "quantity": "",
                "fulfillment-channel": "",
                "handling-time": "",
                "business-price": bus_price
            }
            filas_finales.append(nueva_fila)
            
    return pd.DataFrame(filas_finales)

# --- Interfaz de Streamlit ---
st.set_page_config(page_title="Generador de Tarifas", page_icon="📊")

st.title("🚀 Generador Automático de Tarifas")
st.markdown("""
Sube tu archivo Excel con dos columnas: **SKU** y **PVP**. 
La app generará automáticamente las duplicidades y los precios calculados.
""")

# Configuración
col1, col2 = st.columns(2)
with col1:
    pais_opcion = st.selectbox("Selecciona el destino:", ["España (ES)", "Francia (FR)", "Italia (IT)", "Alemania (DE)"])
    codigo_pais = pais_opcion.split("(")[1][:2]

with col2:
    archivo_subido = st.file_uploader("Cargar Excel de Origen", type=["xlsx"])

if archivo_subido:
    try:
        # Leer el Excel (sin cabeceras si es necesario, o especificando filas)
        df_input = pd.read_excel(archivo_subido, header=None)
        
        st.success("Archivo cargado correctamente")
        
        if st.button("Generar Plantilla Final"):
            df_resultado = procesar_tarifas(df_input, codigo_pais)
            
            # Mostrar vista previa
            st.subheader("Vista previa del resultado:")
            st.dataframe(df_resultado.head(10))
            
            # Convertir a Excel para descarga
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_resultado.to_excel(writer, index=False, sheet_name='Plantilla Tarifas')
            
            st.download_button(
                label="📥 Descargar Excel Procesado",
                data=output.getvalue(),
                file_name=f"Tarifas_{codigo_pais}_Final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")