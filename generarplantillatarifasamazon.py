import streamlit as st
import pandas as pd
import io

def procesar_tarifas(df_origen, pais_seleccionado):
    filas_finales = []
    
    dict_paises = {
        "España": "ES",
        "Francia": "FR",
        "Italia": "IT",
        "Alemania": "DE",
        "Reino Unido": "UK"
    }
    
    prefijo_pais = dict_paises.get(pais_seleccionado, "ES")

    for index, row in df_origen.iterrows():
        try:
            # SKU en Columna A, Precio en Columna C
            sku_input = str(row[0]).strip()
            precio_val = str(row[2]).replace('€', '').replace(',', '.').strip()
            
            if not sku_input or sku_input.upper() == "SKU" or precio_val == "nan":
                continue
                
            precio = float(precio_val)

            # --- LÓGICA DE FORMATEO DE SKU BASE ---
            # Si el SKU empieza por un dígito, añadimos el 0. Si no, lo dejamos igual.
            if sku_input[0].isdigit():
                sku_base = f"0{sku_input}"
            else:
                sku_base = sku_input

            # --- GENERACIÓN DE CLONES ---
            # 1. El SKU formateado (01245 o A90)
            # 2. El SKU con "S" (S01245 o SA90)
            lista_skus_generar = [sku_base, f"S{sku_base}"]
            
            # 3. El SKU con prefijo de país (FR01245 o FRA90) - Solo si no es España
            if prefijo_pais != "ES":
                lista_skus_generar.append(f"{prefijo_pais}{sku_base}")

            # Precios
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
        except (ValueError, TypeError, IndexError):
            continue
            
    return pd.DataFrame(filas_finales)

# --- Interfaz Streamlit ---
st.set_page_config(page_title="Generador de Tarifas v4", layout="centered")

st.title("📊 Generador de Tarifas Inteligente")
st.markdown("""
**Reglas aplicadas:**
* Si el SKU es numérico (1245) → Se convierte en **01245**.
* Si el SKU tiene letras (A90) → Se queda como **A90**.
* Se generan clones con **S** y con **Letras de País**.
""")

pais_label = st.selectbox("Mercado destino:", ["España", "Francia", "Italia", "Alemania", "Reino Unido"])

archivo = st.file_uploader("Cargar Price_Protection.xlsx", type=["xlsx"])

if archivo:
    try:
        df_input = pd.read_excel(archivo, header=None)
        
        if st.button("🚀 Procesar y Descargar"):
            df_resultado = procesar_tarifas(df_input, pais_label)
            
            if not df_resultado.empty:
                st.success(f"¡Hecho! {len(df_resultado)} filas generadas.")
                st.dataframe(df_resultado.head(15))
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_resultado.to_excel(writer, index=False, sheet_name='Plantilla')
                
                st.download_button(
                    label="📥 Descargar Excel",
                    data=output.getvalue(),
                    file_name=f"Tarifas_{pais_label}_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    except Exception as e:
        st.error(f"Error: {e}")
