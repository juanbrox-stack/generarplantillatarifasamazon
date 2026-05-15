import streamlit as st
import pandas as pd
import io

def procesar_tarifas(df_origen, pais_seleccionado):
    # 1. Identificar la fila de cabecera y limpiar datos
    # Buscamos la fila donde esté el SKU para empezar a leer desde ahí
    df_limpio = df_origen.copy()
    
    # En tu fichero, los datos reales parecen empezar después de las primeras filas de títulos
    # Buscamos la palabra 'SKU' o simplemente saltamos las filas no numéricas en el precio
    filas_finales = []
    
    # Definir prefijos según la lógica solicitada
    # España: 0 y S0
    # Otros: 0, S0 y [PAIS]0
    prefijos = ["0", "S0"]
    if pais_seleccionado not in ["ES", "España"]:
        prefijos.append(f"{pais_seleccionado}0")

    for index, row in df_limpio.iterrows():
        try:
            # Intentamos obtener el SKU (Columna A) y Precio (Columna B)
            sku_raw = str(row[0]).strip()
            precio_raw = str(row[1]).replace(',', '.') # Por si viene con comas
            
            # Si el precio no es un número (es una cabecera), saltamos la fila
            precio = float(precio_raw)
            
            # Lógica de precios
            min_price = precio - 1
            max_price = precio + 1
            bus_price = precio - 1 # Igual que el mínimo según instrucciones
            
            for pref in prefijos:
                filas_finales.append({
                    "sku": f"{pref}{sku_raw}",
                    "price": precio,
                    "minimum-seller-allowed-price": min_price,
                    "maximum-seller-allowed-price": max_price,
                    "quantity": "",
                    "fulfillment-channel": "",
                    "handling-time": "",
                    "business-price": bus_price
                })
        except (ValueError, TypeError):
            # Si no puede convertir a float, es una cabecera o fila vacía, la ignoramos
            continue
            
    return pd.DataFrame(filas_finales)

# --- Interfaz de Streamlit ---
st.set_page_config(page_title="Generador de Tarifas", layout="wide")

st.title("📦 Adaptador de Tarifas Marketplace")
st.info("Sube tu archivo Excel. El sistema ignorará las cabeceras de texto automáticamente.")

# Configuración de país
col_config, col_upload = st.columns([1, 2])

with col_config:
    pais_label = st.selectbox(
        "¿Para qué mercado es la tarifa?",
        ["España", "FR", "IT", "DE"]
    )
    codigo_pais = "ES" if pais_label == "España" else pais_label

with col_upload:
    archivo = st.file_uploader("Cargar archivo origen (Excel/CSV)", type=["xlsx", "csv"])

if archivo:
    try:
        # Leer archivo manejando si es CSV o Excel
        if archivo.name.endswith('.csv'):
            df_input = pd.read_csv(archivo, header=None)
        else:
            df_input = pd.read_excel(archivo, header=None)
        
        if st.button("🚀 Procesar y Generar Fichero"):
            df_resultado = procesar_tarifas(df_input, codigo_pais)
            
            if not df_resultado.empty:
                st.success(f"¡Hecho! Se han generado {len(df_resultado)} filas.")
                
                # Vista previa
                st.dataframe(df_resultado.head(10), use_container_width=True)
                
                # Preparar descarga en Excel (Formato valores, sin fórmulas)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_resultado.to_excel(writer, index=False, sheet_name='Template')
                
                st.download_button(
                    label="📥 Descargar Plantilla Cumplimentada",
                    data=output.getvalue(),
                    file_name=f"Plantilla_Tarifas_{codigo_pais}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("No se encontraron datos numéricos válidos en las dos primeras columnas.")
                
    except Exception as e:
        st.error(f"Error crítico: {e}")
