"""Compara cada estación y año con el ECA para Aire y con las guías de la OMS de 2021.

Escribe salidas/resumen_anual.csv (una fila por estación, contaminante y año) y salidas/resumen.json.
Una media anual se reporta solo si al menos el 75 % de los días del año son válidos.
"""

import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PROCESADO = RAIZ / "data" / "procesado"
SALIDAS = RAIZ / "salidas"
MIN_COBERTURA_ANUAL = 0.75

# ECA para Aire, D.S. 003-2017-MINAM (contrastado con el texto publicado en El Peruano el 7 de junio de 2017)
ECA = {
    "PM10": {"24h": 100, "24h_permitidas": 7, "anual": 50},
    "PM25": {"24h": 50, "24h_permitidas": 7, "anual": 25},
    "NO2": {"1h": 200, "1h_permitidas": 24, "anual": 100},
}
# Guías de calidad del aire de la OMS de 2021 (los valores de 24 h son percentiles 99: 3 a 4 días al año)
OMS = {
    "PM10": {"24h": 45, "anual": 15},
    "PM25": {"24h": 15, "anual": 5},
    "NO2": {"24h": 25, "anual": 10},
}
CONTAMINANTES = list(ECA)


def main() -> None:
    SALIDAS.mkdir(parents=True, exist_ok=True)
    horario = pd.read_parquet(PROCESADO / "horario.parquet")
    diario = pd.read_parquet(PROCESADO / "diario.parquet")
    diario["anio"] = diario["fecha"].dt.year
    horario["anio"] = horario["fecha_hora"].dt.year

    filas = []
    for (estacion, anio), d in diario.groupby(["estacion", "anio"]):
        dias_en_registro = d["fecha"].nunique()
        dias_del_anio = 366 if pd.Timestamp(year=anio, month=12, day=31).dayofyear == 366 else 365
        h = horario[(horario["estacion"] == estacion) & (horario["anio"] == anio)]
        for c in CONTAMINANTES:
            validos = d[c].dropna()
            cobertura = len(validos) / dias_del_anio
            fila = {
                "estacion": estacion, "contaminante": c, "anio": anio,
                "dias_en_registro": dias_en_registro, "dias_validos": len(validos),
                "cobertura_pct": round(100 * cobertura, 1),
                "media_anual": round(validos.mean(), 1) if len(validos) else None,
                "media_reportable": bool(cobertura >= MIN_COBERTURA_ANUAL),
                "eca_anual": ECA[c]["anual"],
                "oms_anual": OMS[c]["anual"],
            }
            if "24h" in ECA[c]:
                fila["dias_sobre_eca_24h"] = int((validos > ECA[c]["24h"]).sum())
                fila["eca_24h_permitidas"] = ECA[c]["24h_permitidas"]
            if "1h" in ECA[c]:
                fila["horas_sobre_eca_1h"] = int((h[c] > ECA[c]["1h"]).sum())
                fila["eca_1h_permitidas"] = ECA[c]["1h_permitidas"]
            fila["dias_sobre_oms_24h"] = int((validos > OMS[c]["24h"]).sum())
            filas.append(fila)

    anual = pd.DataFrame(filas)
    anual.to_csv(SALIDAS / "resumen_anual.csv", index=False)

    rep = anual[anual["media_reportable"]]
    resumen = {
        "estaciones": int(anual["estacion"].nunique()),
        "anios": [int(anual["anio"].min()), int(anual["anio"].max())],
        "horas_estacion_con_datos": int(horario[CONTAMINANTES].notna().any(axis=1).sum()),
        "contaminantes": {},
    }
    for c in CONTAMINANTES:
        a = anual[anual["contaminante"] == c]
        r = rep[rep["contaminante"] == c]
        info = {
            "anios_estacion": int(len(a)),
            "anios_estacion_reportables": int(len(r)),
            "reportables_sobre_eca_anual": int((r["media_anual"] > ECA[c]["anual"]).sum()),
            "reportables_sobre_oms_anual": int((r["media_anual"] > OMS[c]["anual"]).sum()),
            "mayor_media_anual_reportable": None,
            "dias_sobre_oms_24h_total": int(a["dias_sobre_oms_24h"].sum()),
        }
        if len(r):
            top = r.loc[r["media_anual"].idxmax()]
            info["mayor_media_anual_reportable"] = {
                "estacion": top["estacion"], "anio": int(top["anio"]), "valor": float(top["media_anual"])}
        if "24h" in ECA[c]:
            info["dias_sobre_eca_24h_total"] = int(a["dias_sobre_eca_24h"].sum())
            info["anios_estacion_sobre_lo_permitido_24h"] = int((a["dias_sobre_eca_24h"] > ECA[c]["24h_permitidas"]).sum())
        if "1h" in ECA[c]:
            info["horas_sobre_eca_1h_total"] = int(a["horas_sobre_eca_1h"].sum())
            info["anios_estacion_sobre_lo_permitido_1h"] = int((a["horas_sobre_eca_1h"] > ECA[c]["1h_permitidas"]).sum())
        resumen["contaminantes"][c] = info

    texto = json.dumps(resumen, indent=2, ensure_ascii=False)
    (SALIDAS / "resumen.json").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
