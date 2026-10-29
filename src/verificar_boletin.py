"""Compara las medias diarias de PM10 de febrero de 2018 con el boletín del SENAMHI de ese mes.

El diccionario de datos no dice las unidades; el boletín (www.senamhi.gob.pe/load/file/03201SENA-57.pdf)
da los máximos diarios en µg/m³, así que si coinciden, las unidades son las mismas.
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BOLETIN = {  # máximo diario de PM10 y día en que ocurrió, según el boletín
    "Carabayllo": {"maximo": 89.5, "dia": 24},
    "San Martín de Porres": {"maximo": 95.4, "dia": 13},
    "San Juan de Lurigancho": {"maximo": 106.1, "dia": 24, "dias_sobre_100": 2},
}

horario = pd.read_parquet(RAIZ / "data" / "procesado" / "horario.parquet")
febrero = horario[(horario["fecha_hora"] >= "2018-02-01") & (horario["fecha_hora"] < "2018-03-01")]
febrero = febrero.assign(fecha=febrero["fecha_hora"].dt.normalize())
diario = febrero.groupby(["estacion", "fecha"])["PM10"].agg(["mean", "count"]).reset_index()

filas = []
for estacion, ref in BOLETIN.items():
    d = diario[diario["estacion"] == estacion]
    mayor = d.loc[d["mean"].idxmax()]
    validos = d[d["count"] >= 18]
    filas.append({
        "estacion": estacion,
        "maximo_boletin": ref["maximo"], "dia_boletin": ref["dia"],
        "maximo_calculado": round(mayor["mean"], 1), "dia_calculado": mayor["fecha"].day,
        "horas_ese_dia": int(mayor["count"]),
        "dias_sobre_100_boletin": ref.get("dias_sobre_100"),
        "dias_sobre_100_calculado": int((validos["mean"] > 100).sum()),
    })
print(pd.DataFrame(filas).to_string(index=False))
