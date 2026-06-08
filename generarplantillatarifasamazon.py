import streamlit as st
import pandas as pd
import io
import re


# ---------------------------------------------------------------------------
# Configuración de países
# ---------------------------------------------------------------------------
# col_precio_override: None = usar detección automática / columna manual
#                      int  = índice fijo de columna (0-based) en el Excel
# moneda_extra: símbolo(s) adicionales a limpiar del precio
PAISES_CONFIG = {
    "España":       {"prefijo": "ES",  "col_precio_override": None, "moneda_extra": ""},
    "Francia":      {"prefijo": "FR",  "col_precio_override": None, "moneda_extra": ""},
    "Italia":       {"prefijo": "IT",  "col_precio_override": None, "moneda_extra": ""},
    "Alemania":     {"prefijo": "DE",  "col_precio_override": None, "moneda_extra": ""},
    "Reino Unido":  {"prefijo": "UK",  "col_precio_override": None, "moneda_extra": "£"},
    "Holanda":      {"prefijo": "NL",  "col_precio_override": None, "moneda_extra": ""},
    "Bélgica":      {"prefijo": "BE",  "col_precio_override": None, "moneda_extra": ""},
    "Polonia":      {"prefijo": "PL",  "col_precio_override": 8,    "moneda_extra": "PLN"},  # col I (índice 8)
    "Suecia":       {"prefijo": "SE",  "col_precio_override": 8,    "moneda_extra": "SEK"},  # col I (índice 8)
}

LISTA_PAISES = list(PAISES_CONFIG.keys())


# ---------------------------------------------------------------------------
# Detección automática de columnas
# ---------------------------------------------------------------------------
def detectar_columnas(df_raw):
    """
    Detecta la fila de cabecera y las columnas de SKU y precio.
    Devuelve (df_limpio, col_sku, col_precio).
    """
    palabras_sku = {
        "sku", "cod", "codigo", "código", "ref", "referencia",
        "article", "articulo", "artículo", "item"
    }
    palabras_precio = {
        "precio", "price", "pvp", "coste", "cost",
        "tarifa", "importe", "valor"
    }

    fila_cabecera = None
    col_sku = None
    col_precio = None

    for i in range(min(10, len(df_raw))):
        fila = df_raw.iloc[i]
        candidatos_sku = []
        candidatos_precio = []
        for j, val in enumerate(fila):
            texto = str(val).lower().strip()
            if any(p in texto for p in palabras_sku):
                candidatos_sku.append(j)
            if any(p in texto for p in palabras_precio):
                candidatos_precio.append(j)

        if candidatos_sku or candidatos_precio:
            fila_cabecera = i
            col_sku = candidatos_sku[0] if candidatos_sku else 0
            col_precio = candidatos_precio[0] if candidatos_precio else 1
            break

    if fila_cabecera is not None:
        df_limpio = df_raw.iloc[fila_cabecera + 1:].reset_index(drop=True)
        st.info(
            f"✅ Cabecera detectada en la fila {fila_cabecera + 1} "
            f"— SKU en columna {col_sku + 1}, Precio en columna {col_precio + 1}"
        )
    else:
        df_limpio = df_raw.copy().reset_index(drop=True)
        col_sku = 0
        col_precio = 1
        st.info("ℹ️ Sin cabecera reconocida — se usará columna A para SKU y columna B para precio")

    return df_limpio, col_sku, col_precio


# ---------------------------------------------------------------------------
# Limpieza de precios
# ---------------------------------------------------------------------------
def limpiar_precio(valor, moneda_extra=""):
    """Limpia un valor de precio eliminando símbolos de moneda y normalizando decimales."""
    texto = str(valor).strip()

    # Eliminar símbolos de moneda conocidos + cualquier extra del país
    simbolos = r'[€$£\s]'
    if moneda_extra:
        # Escapar caracteres especiales del símbolo extra
        extra_esc = re.escape(moneda_extra)
        texto = re.sub(extra_esc, '', texto, flags=re.IGNORECASE)
    texto = re.sub(simbolos, '', texto)

    # 1.234,56 → 1234.56
    if re.match(r'^\d{1,3}(\.\d{3})+(,\d+)?$', texto):
        texto = texto.replace('.', '').replace(',', '.')
    else:
        texto = texto.replace(',', '.')

    return float(texto)


# ---------------------------------------------------------------------------
# Procesado principal
# ---------------------------------------------------------------------------
def procesar_tarifas(df_origen, pais_seleccionado, col_sku, col_precio):
    filas_finales = []
    config = PAISES_CONFIG[pais_seleccionado]
    prefijo_pais = config["prefijo"]
    moneda_extra = config["moneda_extra"]
    errores = []

    for index, row in df_origen.iterrows():
        try:
            sku_input = str(row.iloc[col_sku]).strip()
            precio_raw = row.iloc[col_precio]

            # Ignorar filas vacías o residuos de cabecera
            if not sku_input or sku_input.lower() in ("nan", "sku", "cod", "referencia", ""):
                continue
            if str(precio_raw).lower() in ("nan", "", "precio", "price", "pvp"):
                continue

            precio = limpiar_precio(precio_raw, moneda_extra)

            # --- FORMATEO DE SKU BASE (5 dígitos con ceros a la izquierda) ---
            if sku_input.isdigit():
                sku_base = sku_input.zfill(5)
            else:
                sku_base = sku_input

            # --- GENERACIÓN DE VARIANTES ---
            lista_skus_generar = [sku_base, f"S{sku_base}"]
            if prefijo_pais != "ES":
                lista_skus_generar.append(f"{prefijo_pais}{sku_base}")

            min_price  = round(precio - 1, 2)
            max_price  = round(precio + 1, 2)
            bus_price  = round(precio - 1, 2)

            for sku_final in lista_skus_generar:
                filas_finales.append({
                    "sku":                             sku_final,
                    "price":                           precio,
                    "minimum-seller-allowed-price":    min_price,
                    "maximum-seller-allowed-price":    max_price,
                    "quantity":                        "",
                    "fulfillment-channel":             "",
                    "handling-time":                   "",
                    "business-price":                  bus_price,
                })

        except (ValueError, TypeError, IndexError) as e:
            errores.append(f"Fila {index + 1}: {e}")
            continue

    if errores:
        with st.expander(f"⚠️ {len(errores)} filas con error (haz clic para ver)"):
            for err in errores:
                st.text(err)

    return pd.DataFrame(filas_finales)


# ---------------------------------------------------------------------------
# Interfaz Streamlit
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Generador de Tarifas Amazon", layout="centered")

st.title("📊 Generador de Tarifas Amazon")
st.markdown("""
**Funcionamiento automático:**
- El archivo puede tener cualquier cabecera o ninguna
- Se detecta automáticamente la columna de SKU y la de precio
- **Polonia y Suecia** usan siempre la columna I (precio local PLN/SEK)
- **Holanda y Bélgica** usan el mismo PVPR en € que España
- SKU numérico (1245) → **01245** · SKU alfanumérico (A90) → **A90**
- Se generan variantes con prefijo **S** y con las **iniciales del país**
""")

pais_label = st.selectbox("Mercado destino:", LISTA_PAISES)

config_pais = PAISES_CONFIG[pais_label]

archivo = st.file_uploader("Cargar fichero de tarifas (.xlsx)", type=["xlsx"])

if archivo:
    try:
        df_raw = pd.read_excel(archivo, header=None)
        st.markdown(f"**Previsualización del fichero cargado** ({len(df_raw)} filas totales):")
        st.dataframe(df_raw.head(8), use_container_width=True)

        df_datos, col_sku, col_precio_auto = detectar_columnas(df_raw)

        # Si el país tiene columna de precio fija, usarla; si no, usar la detectada
        col_precio_fijo = config_pais["col_precio_override"]
        col_precio = col_precio_fijo if col_precio_fijo is not None else col_precio_auto

        if col_precio_fijo is not None:
            st.info(
                f"ℹ️ **{pais_label}**: precio tomado de columna {col_precio + 1} "
                f"({chr(65 + col_precio)}) — {config_pais['moneda_extra']}"
            )

        # Ajuste manual (siempre disponible)
        with st.expander("⚙️ Ajustar columnas manualmente (opcional)"):
            num_cols = df_raw.shape[1]
            opciones = [f"Columna {i + 1} ({chr(65 + i)})" for i in range(num_cols)]
            col_sku_manual    = st.selectbox("Columna del SKU:",    opciones, index=col_sku)
            col_precio_manual = st.selectbox("Columna del precio:", opciones, index=min(col_precio, len(opciones) - 1))
            col_sku    = opciones.index(col_sku_manual)
            col_precio = opciones.index(col_precio_manual)

        if st.button("🚀 Procesar y Descargar"):
            df_resultado = procesar_tarifas(df_datos, pais_label, col_sku, col_precio)

            if not df_resultado.empty:
                st.success(f"✅ ¡Hecho! {len(df_resultado)} filas generadas para **{pais_label}**.")
                st.dataframe(df_resultado.head(15), use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df_resultado.to_excel(writer, index=False, sheet_name="Plantilla")

                st.download_button(
                    label="📥 Descargar Excel",
                    data=output.getvalue(),
                    file_name=f"Tarifas_{pais_label}_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.warning("No se generaron filas. Revisa que el fichero tenga datos válidos.")

    except Exception as e:
        st.error(f"Error al procesar el fichero: {e}")
