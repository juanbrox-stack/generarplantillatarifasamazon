import streamlit as st
import pandas as pd
import io

def procesar_tarifas(df_origen, pais_seleccionado):
    filas_finales = []
    
    # Lógica de prefijos según tu requerimiento
    # España: 0 y S0
    # Otros países: 0, S0 y Prefijo País (FR0, IT0, etc)
    prefijos_base = ["0", "S0"]
    
    for index, row in df_origen.iterrows():
        try:
            # --- AJUSTE DE COLUMNAS ---
            # SKU está en la columna A (índice 0)
            sku_raw = str(row[0]).strip()
            
            # El Precio está en la columna C (índice 2)
            # Limpiamos el valor por si trae símbolos de moneda o comas
            precio_val = str(row[2]).replace('€', '').replace(',', '.').strip()
            precio = float(precio_val)
            
            # Si el SKU es el nombre de la cabecera, saltamos
            if "SKU" in sku_raw.upper():
                continue

            # Cálculos de precios
            min_price = precio - 1
            max_price = precio + 1
            bus_price = precio - 1
            
            # Generar lista de prefijos para este SKU
            prefijos_a_procesar = prefijos_base.copy()
            if pais_seleccionado not in ["ES", "España"]:
                # Añadimos el prefijo del país (ej: FR0)
                prefijos_a_procesar.append(f"{pais_seleccionado}0")

            for pref in prefijos_a_procesar:
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
        except (ValueError, TypeError, KeyError):
            # Si la fila no tiene un número en la columna C, se ignora (cabeceras, vacíos)
            continue
            
    return pd.DataFrame(filas_finales)

# --- Interfaz de Streamlit ---
st.set_page_config(page_title="Generador de Tarifas v2", layout="centered")

st.title("📊 Adaptador de Tarifas (Columna A y C)")
st.markdown("Esta versión lee el **SKU de la Columna A** y el **Precio de la Columna C**.")

pais_label = st.selectbox("Selecciona el mercado destino:", ["España", "FR", "IT", "DE", "UK"])
codigo_pais = "ES" if pais_label == "España" else pais_label

archivo = st.file_uploader("Sube el archivo Price_Protection", type=["xlsx"])

if archivo:
    try:
        # Cargamos el Excel
        df_input = pd.read_excel(archivo, header=None)
        
        if st.button("🚀 Procesar Columnas A y C"):
            df_resultado = procesar_tarifas(df_input, codigo_pais)
            
            if not df_resultado.empty:
                st.success(f"¡Listo! Se han procesado {len(df_resultado)} filas.")
                st.dataframe(df_resultado.head(10))
                
                # Exportación limpia a Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_resultado.to_excel(writer, index=False, sheet_name='Plantilla')
                
                st.download_button(
                    label="📥 Descargar Excel para Marketplace",
                    data=output.getvalue(),
                    file_name=f"Tarifas_{codigo_pais}_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("No se detectaron precios válidos en la tercera columna (Columna C).")
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
