"""Ordena el CSV del SENAMHI en tablas horarias y diarias por estación.

Lee data/crudo/senamhi_calidad_aire_lima.csv, guarda las tablas en data/procesado/ y deja
en salidas/reporte_preparacion.json lo que se encontró al revisar el archivo.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CRUDO = RAIZ / "data" / "crudo" / "senamhi_calidad_aire_lima.csv"
PROCESADO = RAIZ / "data" / "procesado"
SALIDAS = RAIZ / "salidas"

CONTAMINANTES = {"PM10": "PM10", "PM2_5": "PM25", "NO2": "NO2"}  # nombre en el archivo -> nombre limpio
MIN_HORAS_DIA = 18
TILDES = {"Martin": "Martín", "Maria": "María", "Jesus": "Jesús"}  # el archivo crudo viene sin tildes


def nombre_estacion(codigo: str) -> str:
    """SAN_MARTIN_DE_PORRES -> San Martín de Porres (conectores en minúscula y tildes repuestas)."""
    palabras = codigo.replace("_", " ").title().split()
    menores = {"De", "Del", "La", "Las", "Los", "Y"}
    palabras = [p.lower() if i and p in menores else TILDES.get(p, p) for i, p in enumerate(palabras)]
    return " ".join(palabras)


def main() -> None:
    PROCESADO.mkdir(parents=True, exist_ok=True)
    SALIDAS.mkdir(parents=True, exist_ok=True)
    reporte = {"archivo_fuente": CRUDO.name}

    crudo = pd.read_csv(CRUDO, dtype={"ESTACION": str, "DISTRITO": str})
    reporte["filas_crudas"] = len(crudo)

    # FECHA (aaaammdd) y HORA (hhmmss) se juntan en una sola marca de tiempo
    fecha = pd.to_datetime(crudo["FECHA"].astype(str), format="%Y%m%d", errors="coerce")
    hora = pd.to_numeric(crudo["HORA"], errors="coerce") // 10000
    imposible = fecha.isna() | hora.isna() | ~hora.between(0, 23)
    reporte["fechas_u_horas_imposibles"] = int(imposible.sum())
    crudo = crudo.loc[~imposible].copy()
    crudo["fecha_hora"] = fecha[~imposible] + pd.to_timedelta(hora[~imposible], unit="h")

    for col in CONTAMINANTES:
        crudo[col] = pd.to_numeric(crudo[col], errors="coerce")
    reporte["negativos_anulados"] = {CONTAMINANTES[c]: int((crudo[c] < 0).sum()) for c in CONTAMINANTES}
    for col in CONTAMINANTES:
        crudo.loc[crudo[col] < 0, col] = np.nan

    # Horas-estación repetidas: las copias idénticas quedan en una; si difieren no se sabe cuál es la
    # correcta, así que se quitan todas y esa hora queda como faltante
    clave = ["ESTACION", "fecha_hora"]
    crudo = crudo.drop_duplicates(subset=clave + list(CONTAMINANTES))
    conflicto = crudo.duplicated(subset=clave, keep=False)
    reporte["horas_estacion_en_conflicto_anuladas"] = int(crudo.loc[conflicto, clave].drop_duplicates().shape[0])
    reporte["filas_en_conflicto_eliminadas"] = int(conflicto.sum())
    crudo = crudo.loc[~conflicto].rename(columns=CONTAMINANTES)

    estaciones = (
        crudo.groupby("ESTACION")
        .agg(distrito=("DISTRITO", "first"), lat=("LATITUD", "first"), lon=("LONGITUD", "first"),
             altitud_m=("ALTITUD", "first"), primer_registro=("fecha_hora", "min"),
             ultimo_registro=("fecha_hora", "max"))
        .reset_index()
        .rename(columns={"ESTACION": "codigo"})
    )
    estaciones["estacion"] = estaciones["codigo"].map(nombre_estacion)
    estaciones["distrito"] = estaciones["distrito"].map(nombre_estacion)
    estaciones = estaciones[["estacion", "codigo", "distrito", "lat", "lon", "altitud_m",
                             "primer_registro", "ultimo_registro"]]
    estaciones.to_csv(PROCESADO / "estaciones.csv", index=False)

    # Grilla horaria de todo el periodo, para que las horas sin registro cuenten como faltantes
    inicio = crudo["fecha_hora"].min().normalize()
    fin = crudo["fecha_hora"].max().normalize() + pd.Timedelta(hours=23)
    grilla = pd.date_range(inicio, fin, freq="h")
    nombres = dict(zip(estaciones["codigo"], estaciones["estacion"]))
    bloques = []
    for codigo, bloque in crudo.groupby("ESTACION"):
        bloque = bloque.set_index("fecha_hora")[list(CONTAMINANTES.values())].reindex(grilla)
        bloque.index.name = "fecha_hora"
        bloque.insert(0, "estacion", nombres[codigo])
        bloques.append(bloque.reset_index())
    horario = pd.concat(bloques, ignore_index=True)
    horario.to_parquet(PROCESADO / "horario.parquet", index=False)

    # Medias diarias, válidas solo con al menos 18 horas; el conteo de horas queda en la tabla
    horario["fecha"] = horario["fecha_hora"].dt.normalize()
    grupos = horario.groupby(["estacion", "fecha"])
    diario = grupos[list(CONTAMINANTES.values())].mean()
    conteo = grupos[list(CONTAMINANTES.values())].count()
    for c in CONTAMINANTES.values():
        diario[c] = diario[c].where(conteo[c] >= MIN_HORAS_DIA)
        diario[f"{c}_horas_validas"] = conteo[c]
    diario = diario.reset_index()
    # El análisis usa el parquet sin redondear (redondear antes puede pasar un valor al otro lado del límite)
    diario.to_parquet(PROCESADO / "diario.parquet", index=False)
    diario.round(2).to_csv(PROCESADO / "diario.csv", index=False)

    reporte.update({
        "periodo": [str(inicio), str(fin)],
        "estaciones": len(estaciones),
        "filas_horarias": len(horario),
        "horas_validas_pct": {c: round(100 * horario[c].notna().mean(), 1) for c in CONTAMINANTES.values()},
        "dias_validos_pct": {c: round(100 * diario[c].notna().mean(), 1) for c in CONTAMINANTES.values()},
    })
    texto = json.dumps(reporte, indent=2, ensure_ascii=False)
    (SALIDAS / "reporte_preparacion.json").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
