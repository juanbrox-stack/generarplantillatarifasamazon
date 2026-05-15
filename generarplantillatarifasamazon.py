import streamlit as st
import pandas as pd
import io

def procesar_tarifas(df_origen, pais_seleccionado):
    filas_finales = []
    
    # Mapeo de códigos de país para los prefijos
    dict_paises = {
        "España": "ES",
        "Francia": "FR",
        "Italia": "IT",
        "Alemania": "DE",
        "Reino Unido": "UK"
    }
    
    prefijo_pais = dict_paises.get(pais_seleccionado, pais_seleccionado)

    for index, row in df_origen.iterrows():
        try:
            # SKU en Columna A (índice 0), Precio en Columna C (índice 2)
            sku_raw = str(row[0]).strip()
            precio_val = str(row[2]).replace('€', '').replace(',', '.').strip()
            
            # Saltamos filas vacías o cabeceras
            if not sku_raw or sku_raw.upper() == "SKU" or precio_val == "nan":
                continue
                
            precio = float(precio_val)

            # --- NUEVA LÓGICA DE PREFIJOS ---
            # 1. El SKU tal cual (ej. A90)
            # 2. El SKU con "S" delante (ej. SA90)
            # 3. El SKU con el prefijo del PAÍS delante (ej. FRA90) - Solo si no es España
            
            lista_skus_generar = [sku_raw, f"S{sku_raw}"]
            
            if prefijo_pais != "ES":
                lista_skus_generar.append(f"{prefijo_pais}{sku_raw}")

            # Cálculos de precios (se mantienen según tu instrucción original)
            min_price = precio - 1
            max_price = precio + 1
            bus_price = precio - 1
            
            for sku_final in lista_skus_generar:
                filas_finales.append({
                    "sku": sku_final,
                    "price": precio,
                    "minimum-seller-allowed-price": min_price,
                    "maximum-seller-allowed-price": max_price,
                    "quantity": "",
                    "fulfillment-channel": "",
                    "handling-time": "",
                    "business-price": bus_price
                })
        except (ValueError, TypeError):
            continue
            
    return pd.DataFrame(filas_finales)

# --- Interfaz de Streamlit ---
st.set_page_config(page_title="Generador de Tarifas v3", layout="centered")

st.title("📊 Adaptador de Tarifas SKU Especiales")
st.markdown("Configurado para SKUs tipo: **A90**, **SA90**, **FRA90**.")

pais_label = st.selectbox("Selecciona el mercado destino:", ["España", "Francia", "Italia", "Alemania", "Reino Unido"])

archivo = st.file_uploader("Sube el archivo Excel (Price_Protection)", type=["xlsx"])

if archivo:
    try:
        df_input = pd.read_excel(archivo, header=None)
        
        if st.button("🚀 Generar Fichero"):
            df_resultado = procesar_tarifas(df_input, pais_label)
            
            if not df_resultado.empty:
                st.success(f"¡Procesado! Generadas {len(df_resultado)} líneas.")
                st.dataframe(df_resultado.head(15))
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_resultado.to_excel(writer, index=False, sheet_name='Plantilla')
                
                st.download_button(
                    label="📥 Descargar Excel Final",
                    data=output.getvalue(),
                    file_name=f"Tarifas_{pais_label}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("No se encontraron datos válidos. Revisa que el precio esté en la columna C.")
    except Exception as e:
        st.error(f"Error técnico: {e}")
