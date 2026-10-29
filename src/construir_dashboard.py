"""Arma index.html con Plotly a partir de las tablas de data/procesado/ y salidas/."""

import html
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

RAIZ = Path(__file__).resolve().parents[1]
PROCESADO = RAIZ / "data" / "procesado"
SALIDAS = RAIZ / "salidas"
PAGINA = RAIZ / "index.html"
SITIO = "https://cristhianbgf.github.io/calidad-aire-lima/"
REPO = "https://github.com/Cristhianbgf/calidad-aire-lima"
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"  # la versión que trae plotly 5.24.1
PLOTLY_ES = "https://cdn.plot.ly/plotly-locale-es-2.35.2.js"

CONTAMINANTES = ["PM10", "PM25", "NO2"]
ETIQUETA = {"PM10": "PM10", "PM25": "PM2.5", "NO2": "NO2"}
UNIDAD = "µg/m³"
ECA = {"PM10": {"24h": 100, "anual": 50}, "PM25": {"24h": 50, "anual": 25}, "NO2": {"1h": 200, "anual": 100}}
OMS = {"PM10": {"24h": 45, "anual": 15}, "PM25": {"24h": 15, "anual": 5}, "NO2": {"24h": 25, "anual": 10}}

TEXTO, TEXTO_2, TENUE, GRILLA, EJE, BLANCO = "#222222", "#555555", "#888888", "#e6e6e6", "#bbbbbb", "#ffffff"
# Okabe-Ito (apta para daltonismo) más un vino para la séptima estación
COLORES_ESTACION = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#882255"]
AZULES_MAPA = ["#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"]  # Blues de ColorBrewer sin los más claros
CONFIG = {"displaylogo": False, "responsive": True, "locale": "es",
          "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"]}


def diseno(alto, **extra):
    d = dict(
        height=alto, paper_bgcolor=BLANCO, plot_bgcolor=BLANCO, separators=". ",
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=13, color=TEXTO),
        margin=dict(l=12, r=12, t=12, b=12),
        hoverlabel=dict(bgcolor=BLANCO, bordercolor=EJE, font=dict(color=TEXTO, size=12)),
        xaxis=dict(gridcolor=GRILLA, linecolor=EJE, tickfont=dict(color=TEXTO_2), zeroline=False),
        yaxis=dict(gridcolor=GRILLA, linecolor=EJE, tickfont=dict(color=TEXTO_2), zeroline=False),
    )
    d.update(extra)
    return d


def lineas_limite(c, vertical=False):
    """Líneas del ECA de 24 h (si existe) y de la guía de 24 h de la OMS, con su rótulo."""
    lineas = []
    if "24h" in ECA[c]:
        lineas.append((ECA[c]["24h"], f"ECA 24 h · {ECA[c]['24h']}", TEXTO, "dash"))
    lineas.append((OMS[c]["24h"], f"OMS 24 h · {OMS[c]['24h']}", TENUE, "dot"))
    nota = dict(showarrow=False, font=dict(size=11, color=TEXTO_2), bgcolor="rgba(255,255,255,0.85)")
    if vertical:
        formas = [dict(type="line", yref="paper", y0=0, y1=1, xref="x", x0=v, x1=v,
                       line=dict(color=col, width=1.5, dash=d)) for v, _, col, d in lineas]
        # si hay dos, el rótulo del valor menor va a la izquierda para que no se encimen
        rotulos = [dict(yref="paper", y=1, yanchor="bottom", xref="x", x=v,
                        xanchor="right" if (len(lineas) == 2 and k == 1) else "left", text=t, **nota)
                   for k, (v, t, _, _) in enumerate(lineas)]
    else:
        formas = [dict(type="line", xref="paper", x0=0, x1=1, yref="y", y0=v, y1=v,
                       line=dict(color=col, width=1.5, dash=d)) for v, _, col, d in lineas]
        rotulos = [dict(xref="paper", x=1, xanchor="right", yref="y", y=v, yanchor="bottom",
                        text=f"{t} {UNIDAD}", **nota) for v, t, _, _ in lineas]
    return {"shapes": formas, "annotations": rotulos}


def tabla_estacion_anio(a, col, orden, anios):
    return a.pivot(index="estacion", columns="anio", values=col).reindex(orden)[anios]


def main() -> None:
    estaciones = pd.read_csv(PROCESADO / "estaciones.csv").sort_values("lat", ascending=False)  # de norte a sur
    orden = estaciones["estacion"].tolist()
    color = dict(zip(orden, COLORES_ESTACION))
    diario = pd.read_parquet(PROCESADO / "diario.parquet")
    horario = pd.read_parquet(PROCESADO / "horario.parquet")
    anual = pd.read_csv(SALIDAS / "resumen_anual.csv")
    resumen = json.loads((SALIDAS / "resumen.json").read_text(encoding="utf-8"))
    reporte = json.loads((SALIDAS / "reporte_preparacion.json").read_text(encoding="utf-8"))
    anios = sorted(anual["anio"].unique())

    figuras, visibles, lineas = {}, {}, {}

    # Mapa con la media de todo el periodo
    fig = go.Figure()
    media = diario.groupby("estacion")[CONTAMINANTES].mean()
    cobertura = diario.groupby("estacion")[CONTAMINANTES].apply(lambda d: d.notna().mean() * 100)
    e = estaciones.set_index("estacion")
    for i, c in enumerate(CONTAMINANTES):
        v = media.loc[orden, c]
        tamano = 14 + 22 * (v - v.min()) / (v.max() - v.min())
        # círculo gris debajo para que cada marcador tenga borde
        fig.add_trace(go.Scattermap(
            lat=e.loc[orden, "lat"], lon=e.loc[orden, "lon"], mode="markers", hoverinfo="skip",
            marker=dict(size=tamano + 4, color=TEXTO_2), visible=(i == 0), showlegend=False))
        fig.add_trace(go.Scattermap(
            lat=e.loc[orden, "lat"], lon=e.loc[orden, "lon"], mode="markers+text",
            text=orden, textposition="top right", textfont=dict(size=12, color=TEXTO),
            marker=dict(size=tamano, color=v, colorscale=AZULES_MAPA, showscale=True,
                        colorbar=dict(title=dict(text=UNIDAD, font=dict(color=TEXTO_2)), thickness=12,
                                      len=0.6, tickfont=dict(color=TEXTO_2))),
            customdata=list(zip(e.loc[orden, "distrito"], v.round(1), cobertura.loc[orden, c].round(0))),
            hovertemplate="<b>%{text}</b> · %{customdata[0]}<br>" + f"Media de {ETIQUETA[c]} 2015-2024: " +
                          "%{customdata[1]} " + UNIDAD + "<br>Días con datos válidos: %{customdata[2]} %<extra></extra>",
            visible=(i == 0), name=ETIQUETA[c]))
    fig.update_layout(**diseno(460), showlegend=False,
                      map=dict(style="carto-positron", zoom=9.7,
                               center=dict(lat=float(e["lat"].mean()), lon=float(e["lon"].mean()) + 0.02)))
    figuras["mapa"] = fig
    visibles["mapa"] = {c: [q == c for q in CONTAMINANTES for _ in range(2)] for c in CONTAMINANTES}

    # Medias anuales: azul bajo el ECA y rojo sobre él; en gris las que no tienen 75 % de días
    fig = go.Figure()
    for i, c in enumerate(CONTAMINANTES):
        a = anual[anual["contaminante"] == c]
        medias = tabla_estacion_anio(a, "media_anual", orden, anios)
        ok = tabla_estacion_anio(a, "media_reportable", orden, anios).astype(bool)
        cob = tabla_estacion_anio(a, "cobertura_pct", orden, anios)
        buenas, debiles = medias.where(ok), medias.where(~ok)
        limite = ECA[c]["anual"]
        fig.add_trace(go.Heatmap(
            z=buenas.values, x=anios, y=orden, colorscale="RdBu_r", zmin=0, zmax=2 * limite,  # el ECA queda al centro
            text=buenas.round(0).astype("Int64").astype(str).replace("<NA>", "").values, texttemplate="%{text}",
            customdata=cob.values, xgap=2, ygap=2, visible=(i == 0),
            colorbar=dict(title=dict(text=UNIDAD, font=dict(color=TEXTO_2)), thickness=12, tickfont=dict(color=TEXTO_2),
                          tickvals=[0, limite, 2 * limite], ticktext=["0", f"ECA {limite}", f"≥ {2 * limite}"]),
            hovertemplate="<b>%{y}</b> · %{x}<br>Media anual: %{z:.1f} " + UNIDAD +
                          f"<br>ECA anual: {limite} · OMS: {OMS[c]['anual']}" +
                          "<br>Días con datos válidos: %{customdata} %<extra></extra>"))
        fig.add_trace(go.Heatmap(
            z=debiles.notna().astype(float).where(debiles.notna()).values, x=anios, y=orden,
            colorscale=[[0, "#eeeeee"], [1, "#eeeeee"]], showscale=False, xgap=2, ygap=2,
            text=debiles.round(0).astype("Int64").astype(str).replace("<NA>", "").radd("(").add(")")
                        .replace("()", "").values,
            texttemplate="%{text}", textfont=dict(color=TENUE), customdata=cob.values, visible=(i == 0),
            hovertemplate="<b>%{y}</b> · %{x}<br>Solo indicativa: %{customdata} % de días válidos"
                          "<br>(una media anual necesita al menos 75 %)<extra></extra>"))
    fig.update_layout(**diseno(360))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(dtick=1, side="top")
    figuras["anual"] = fig
    visibles["anual"] = {c: [q == c for q in CONTAMINANTES for _ in range(2)] for c in CONTAMINANTES}

    # Días sobre el ECA de 24 h (PM10 y PM2.5) u horas sobre el de 1 h (NO2)
    fig = go.Figure()
    for i, c in enumerate(CONTAMINANTES):
        a = anual[anual["contaminante"] == c]
        pm = "24h" in ECA[c]
        z = tabla_estacion_anio(a, "dias_sobre_eca_24h" if pm else "horas_sobre_eca_1h", orden, anios)
        cob = tabla_estacion_anio(a, "cobertura_pct", orden, anios)
        que = "Días sobre el ECA de 24 h" if pm else "Horas sobre el ECA de 1 h"
        fig.add_trace(go.Heatmap(
            z=z.values, x=anios, y=orden, colorscale="Oranges", zmin=0, xgap=2, ygap=2,
            text=z.values, texttemplate="%{text}", customdata=cob.values, visible=(i == 0),
            colorbar=dict(title=dict(text="días" if pm else "horas", font=dict(color=TEXTO_2)),
                          thickness=12, tickfont=dict(color=TEXTO_2)),
            hovertemplate="<b>%{y}</b> · %{x}<br>" + que + ": %{z}" + f" (permitidas: {7 if pm else 24} al año)" +
                          "<br>Días con datos válidos: %{customdata} %<extra></extra>"))
    fig.update_layout(**diseno(360))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(dtick=1, side="top")
    figuras["excedencias"] = fig
    visibles["excedencias"] = {c: [q == c for q in CONTAMINANTES] for c in CONTAMINANTES}

    # Serie diaria: una estación y un contaminante a la vez
    fig = go.Figure()
    combinaciones = [(est, c) for c in CONTAMINANTES for est in orden]
    for est, c in combinaciones:
        d = diario[diario["estacion"] == est]
        fig.add_trace(go.Scatter(
            x=d["fecha"], y=d[c].round(1), mode="lines", line=dict(width=1.5, color=color[est]),
            name=f"{est} · {ETIQUETA[c]}", visible=(est == orden[0] and c == CONTAMINANTES[0]), connectgaps=False,
            hovertemplate="%{x|%d %b %Y}<br>Media diaria: %{y} " + UNIDAD + "<extra></extra>"))
    fig.update_layout(**diseno(420), showlegend=False, hovermode="x", **lineas_limite(CONTAMINANTES[0]))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.07, bgcolor="#f2f2f2"),
                     rangeselector=dict(buttons=[dict(count=1, label="1 año", step="year", stepmode="backward"),
                                                 dict(count=3, label="3 años", step="year", stepmode="backward"),
                                                 dict(step="all", label="Todo")],
                                        bgcolor="#f2f2f2", activecolor="#dddddd", font=dict(color=TEXTO)))
    fig.update_yaxes(title=dict(text=UNIDAD, font=dict(color=TEXTO_2)), rangemode="tozero")
    figuras["serie"] = fig
    visibles["serie"] = {f"{est}|{c}": [k == (est, c) for k in combinaciones] for est, c in combinaciones}
    lineas["serie"] = {c: lineas_limite(c) for c in CONTAMINANTES}

    # Cajas horizontales de las medias diarias, para que se lean los nombres de las estaciones
    fig = go.Figure()
    for i, c in enumerate(CONTAMINANTES):
        d = diario[["estacion", c]].dropna()
        fig.add_trace(go.Box(
            y=d["estacion"], x=d[c].round(1), orientation="h", boxpoints=False, visible=(i == 0), name=ETIQUETA[c],
            marker_color=COLORES_ESTACION[0], line=dict(width=1.5), fillcolor="rgba(0,114,178,0.18)",
            hoverinfo="x"))
    fig.update_layout(**diseno(400), showlegend=False, **lineas_limite(CONTAMINANTES[0], vertical=True))
    fig.update_yaxes(categoryorder="array", categoryarray=orden[::-1])
    fig.update_xaxes(title=dict(text=f"Media diaria ({UNIDAD})", font=dict(color=TEXTO_2)), rangemode="tozero")
    figuras["cajas"] = fig
    visibles["cajas"] = {c: [q == c for q in CONTAMINANTES] for c in CONTAMINANTES}
    lineas["cajas"] = {c: lineas_limite(c, vertical=True) for c in CONTAMINANTES}

    # Ciclo diario por estación
    horario["hora"] = horario["fecha_hora"].dt.hour
    ciclo = horario.groupby(["estacion", "hora"])[CONTAMINANTES].mean().round(1).reset_index()
    fig = go.Figure()
    for i, c in enumerate(CONTAMINANTES):
        for est in orden:
            h = ciclo[ciclo["estacion"] == est]
            fig.add_trace(go.Scatter(
                x=h["hora"], y=h[c], mode="lines+markers", name=est, legendgroup=est, showlegend=(i == 0),
                line=dict(width=2, color=color[est]), marker=dict(size=6), visible=(i == 0),
                hovertemplate=est + ": %{y} " + UNIDAD + "<extra></extra>"))
    fig.update_layout(**diseno(420), hovermode="x unified",
                      legend=dict(orientation="h", y=-0.18, font=dict(color=TEXTO_2)))
    fig.update_xaxes(title=dict(text="Hora del día (hora local, UTC-5)", font=dict(color=TEXTO_2)),
                     dtick=2, range=[-0.5, 23.5])
    fig.update_yaxes(title=dict(text=f"Media ({UNIDAD})", font=dict(color=TEXTO_2)), rangemode="tozero")
    figuras["ciclo"] = fig
    visibles["ciclo"] = {c: [q == c for q in CONTAMINANTES for _ in orden] for c in CONTAMINANTES}

    # Porcentaje de horas con dato válido por estación y año
    horario["anio"] = horario["fecha_hora"].dt.year
    comp = horario.groupby(["estacion", "anio"])[CONTAMINANTES].apply(lambda d: d.notna().mean() * 100).round(0)
    fig = go.Figure()
    for i, c in enumerate(CONTAMINANTES):
        z = comp[c].unstack().reindex(orden)[anios]
        fig.add_trace(go.Heatmap(
            z=z.values, x=anios, y=orden, colorscale="Blues", zmin=0, zmax=100, xgap=2, ygap=2,
            text=z.values, texttemplate="%{text}", visible=(i == 0),
            colorbar=dict(title=dict(text="% horas", font=dict(color=TEXTO_2)), thickness=12,
                          tickfont=dict(color=TEXTO_2)),
            hovertemplate="<b>%{y}</b> · %{x}<br>Horas con datos válidos: %{z} %<extra></extra>"))
    fig.update_layout(**diseno(340))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(dtick=1, side="top")
    figuras["completitud"] = fig
    visibles["completitud"] = {c: [q == c for q in CONTAMINANTES] for c in CONTAMINANTES}

    bloques = {k: f.to_html(full_html=False, include_plotlyjs=False, div_id=f"fig-{k}", config=CONFIG)
               for k, f in figuras.items()}

    filas = []
    for r in anual.sort_values(["contaminante", "estacion", "anio"]).itertuples():
        corto = r.dias_sobre_eca_24h if pd.notna(getattr(r, "dias_sobre_eca_24h", None)) else r.horas_sobre_eca_1h
        filas.append(
            f'<tr data-contaminante="{r.contaminante}"><td>{html.escape(r.estacion)}</td><td>{r.anio}</td>'
            f'<td class="num">{r.cobertura_pct:.0f}</td>'
            f'<td class="num">{"" if pd.isna(r.media_anual) else f"{r.media_anual:.1f}"}</td>'
            f'<td>{"reportable" if r.media_reportable else "indicativa"}</td>'
            f'<td class="num">{int(corto)}</td><td class="num">{int(r.dias_sobre_oms_24h)}</td></tr>')

    C = resumen["contaminantes"]
    horas = f"{resumen['horas_estacion_con_datos']:,}".replace(",", " ")
    tarjetas = [
        ("Red", f"{resumen['estaciones']} estaciones", f"De enero de 2015 a mayo de 2024, con {horas} horas-estación con datos"),
        ("PM10", f"{C['PM10']['reportables_sobre_eca_anual']} de {C['PM10']['anios_estacion_reportables']}",
         f"años-estación con datos suficientes sobre el ECA anual ({ECA['PM10']['anual']} {UNIDAD})"),
        ("PM2.5", f"{C['PM25']['reportables_sobre_eca_anual']} de {C['PM25']['anios_estacion_reportables']}",
         f"años-estación con datos suficientes sobre el ECA anual ({ECA['PM25']['anual']} {UNIDAD})"),
        ("NO2", f"{C['NO2']['reportables_sobre_eca_anual']} de {C['NO2']['anios_estacion_reportables']}",
         f"sobre el ECA anual, aunque los {C['NO2']['reportables_sobre_oms_anual']} superan la guía de la OMS"),
    ]
    tarjetas_html = "".join(f'<div class="tarjeta"><div class="tarjeta-titulo">{k}</div><div class="tarjeta-valor">{v}</div>'
                            f'<div class="tarjeta-texto">{html.escape(d)}</div></div>' for k, v, d in tarjetas)
    opciones = "".join(f'<option value="{html.escape(est)}">{html.escape(est)}</option>' for est in orden)
    datos_js = json.dumps({"visibles": visibles, "lineas": lineas, "etiquetas": ETIQUETA, "eca": ECA},
                          ensure_ascii=False)

    pagina = PLANTILLA.format(
        plotly_cdn=PLOTLY_CDN, plotly_es=PLOTLY_ES, sitio=SITIO, repo=REPO, tarjetas=tarjetas_html,
        opciones=opciones, filas_tabla="".join(filas), datos_js=datos_js,
        **{f"fig_{k}": v for k, v in bloques.items()},
        n_conflicto=reporte["horas_estacion_en_conflicto_anuladas"],
        pm10_sobre=C["PM10"]["anios_estacion_sobre_lo_permitido_24h"],
        pm25_sobre=C["PM25"]["anios_estacion_sobre_lo_permitido_24h"],
        no2_horas=C["NO2"]["horas_sobre_eca_1h_total"],
    )
    PAGINA.write_text(pagina, encoding="utf-8")
    print(f"ok: {PAGINA} ({PAGINA.stat().st_size / 1e6:.1f} MB)")


PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Calidad del aire en Lima, 2015-2024</title>
<meta name="description" content="Dashboard de PM10, PM2.5 y NO2 de las siete estaciones automáticas del SENAMHI en Lima Metropolitana, comparados con el ECA para Aire y las guías de la OMS de 2021.">
<meta property="og:type" content="website">
<meta property="og:title" content="Calidad del aire en Lima Metropolitana, 2015-2024">
<meta property="og:description" content="PM10, PM2.5 y NO2 de las siete estaciones del SENAMHI frente al ECA para Aire y las guías de la OMS.">
<meta property="og:url" content="{sitio}">
<meta property="og:image" content="{sitio}figuras/compartir.png">
<meta name="twitter:card" content="summary_large_image">
<script src="{plotly_cdn}" charset="utf-8"></script>
<script src="{plotly_es}" charset="utf-8"></script>
<style>
:root {{
  color-scheme: light;
  --fondo: #f5f5f5; --panel: #ffffff; --texto: #222222; --texto-2: #555555; --tenue: #888888;
  --linea: #e6e6e6; --borde: #dddddd; --enlace: #0072B2;
}}
* {{ box-sizing: border-box; }}
html, body {{ background: var(--fondo); }}
body {{ margin: 0; color: var(--texto); font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 32px 16px 48px; }}
h1 {{ font-size: 30px; line-height: 1.2; margin: 0 0 8px; }}
h2 {{ font-size: 20px; margin: 0 0 4px; }}
p {{ margin: 0 0 12px; }}
a {{ color: var(--enlace); }}
.entrada {{ color: var(--texto-2); max-width: 760px; font-size: 17px; }}
.barra {{ position: sticky; top: 0; z-index: 10; background: var(--fondo); border-bottom: 1px solid var(--borde);
  padding: 10px 0; margin: 20px 0 24px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
.barra span {{ color: var(--texto-2); font-size: 14px; }}
.botones {{ display: inline-flex; border: 1px solid var(--borde); border-radius: 6px; overflow: hidden; }}
.botones button {{ font: inherit; font-size: 14px; border: 0; background: var(--panel); color: var(--texto);
  padding: 6px 16px; cursor: pointer; }}
.botones button + button {{ border-left: 1px solid var(--borde); }}
.botones button[aria-pressed="true"] {{ background: var(--texto); color: #fff; }}
.tarjetas {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 8px; }}
.tarjeta {{ background: var(--panel); border: 1px solid var(--borde); border-radius: 8px; padding: 14px 16px; }}
.tarjeta-titulo {{ color: var(--texto-2); font-size: 13px; }}
.tarjeta-valor {{ font-size: 26px; font-weight: 600; margin: 2px 0; }}
.tarjeta-texto {{ color: var(--texto-2); font-size: 13px; line-height: 1.4; }}
.panel {{ background: var(--panel); border: 1px solid var(--borde); border-radius: 8px; padding: 18px 18px 8px; margin: 16px 0; }}
.nota {{ color: var(--texto-2); font-size: 14px; }}
.dos-columnas {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.dos-columnas .panel {{ margin: 0; }}
select {{ font: inherit; font-size: 14px; padding: 5px 8px; border: 1px solid var(--borde);
  border-radius: 6px; background: var(--panel); color: var(--texto); }}
.control {{ display: flex; gap: 8px; align-items: center; margin: 6px 0 4px; color: var(--texto-2); font-size: 14px; }}
details {{ margin: 16px 0; }}
summary {{ cursor: pointer; font-weight: 600; }}
.tabla {{ max-height: 420px; overflow: auto; border: 1px solid var(--borde); border-radius: 6px; margin-top: 10px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; background: var(--panel); }}
th, td {{ padding: 6px 10px; border-bottom: 1px solid var(--linea); text-align: left; white-space: nowrap; }}
th {{ position: sticky; top: 0; background: #f0f0f0; color: var(--texto-2); font-weight: 600; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.metodo {{ color: var(--texto-2); font-size: 15px; max-width: 860px; }}
.metodo h2 {{ color: var(--texto); margin-top: 28px; }}
footer {{ border-top: 1px solid var(--borde); margin-top: 32px; padding-top: 16px; color: var(--tenue); font-size: 14px; }}
@media (max-width: 860px) {{
  .tarjetas {{ grid-template-columns: 1fr 1fr; }}
  .dos-columnas {{ grid-template-columns: 1fr; }}
  h1 {{ font-size: 25px; }}
}}
</style>
</head>
<body>
<main>
<h1>Calidad del aire en Lima Metropolitana, 2015-2024</h1>
<p class="entrada">Concentraciones horarias de PM10, PM2.5 y NO2 de las siete estaciones automáticas del SENAMHI,
comparadas con el Estándar de Calidad Ambiental para Aire (ECA, D.S. 003-2017-MINAM) y con las guías de calidad
del aire de la OMS de 2021. El ECA es la referencia legal en el Perú, mientras que las guías de la OMS son una
referencia de salud y no son vinculantes.</p>

<div class="barra" role="toolbar" aria-label="Contaminante">
  <span>Contaminante</span>
  <div class="botones" id="contaminante">
    <button data-c="PM10" aria-pressed="true">PM10</button>
    <button data-c="PM25" aria-pressed="false">PM2.5</button>
    <button data-c="NO2" aria-pressed="false">NO2</button>
  </div>
</div>

<div class="tarjetas">{tarjetas}</div>

<div class="panel">
  <h2>¿Dónde es peor el aire? Media de <span class="etiqueta"></span> por estación</h2>
  <p class="nota">Media de las medias diarias válidas de todo el registro. Los círculos más grandes y oscuros indican concentraciones más altas.</p>
  {fig_mapa}
</div>

<div class="dos-columnas">
  <div class="panel">
    <h2>Media anual frente al ECA</h2>
    <p class="nota">El rojo indica que la media anual supera el ECA y el azul, que está por debajo. Los valores grises
    entre paréntesis son indicativos, porque ese año tiene menos del 75 % de días con datos válidos.</p>
    {fig_anual}
  </div>
  <div class="panel">
    <h2 id="titulo-excedencias">Días sobre el ECA de 24 horas</h2>
    <p class="nota" id="nota-excedencias">El ECA permite hasta 7 días al año por encima del límite. En los años con
    datos faltantes, el conteo es un mínimo.</p>
    {fig_excedencias}
  </div>
</div>

<div class="panel">
  <h2>Media diaria de <span class="etiqueta"></span>, día por día</h2>
  <div class="control"><label for="estacion">Estación</label><select id="estacion">{opciones}</select></div>
  {fig_serie}
</div>

<div class="dos-columnas">
  <div class="panel">
    <h2>¿Qué tan distintas son las estaciones?</h2>
    <p class="nota">Distribución de las medias diarias de <span class="etiqueta"></span>. La caja abarca la mitad central
    de los días y la línea interior es la mediana.</p>
    {fig_cajas}
  </div>
  <div class="panel">
    <h2>¿A qué hora del día es peor?</h2>
    <p class="nota">Media de <span class="etiqueta"></span> para cada hora del día, con todos los años juntos.</p>
    {fig_ciclo}
  </div>
</div>

<div class="panel">
  <h2>¿Qué tan completo es el registro?</h2>
  <p class="nota">Porcentaje de horas con un valor válido de <span class="etiqueta"></span>, por estación y año (2024 cubre de enero a mayo).</p>
  {fig_completitud}
</div>

<details>
  <summary>Tabla del resumen anual por estación y año (<span class="etiqueta"></span>)</summary>
  <div class="tabla"><table>
    <thead><tr><th>Estación</th><th>Año</th><th>Días válidos (%)</th><th>Media anual (µg/m³)</th><th>Media anual</th>
    <th>Sobre el ECA de corto plazo*</th><th>Días sobre la OMS 24 h</th></tr></thead>
    <tbody>{filas_tabla}</tbody>
  </table></div>
  <p class="metodo">* Días sobre el ECA de 24 horas para PM10 y PM2.5, y horas sobre el ECA de 1 hora para NO2.
  Se pueden descargar las <a href="data/procesado/diario.csv">medias diarias (CSV)</a> y el
  <a href="salidas/resumen_anual.csv">resumen anual (CSV)</a>.</p>
</details>

<section class="metodo">
  <h2>Datos y método</h2>
  <p>Los datos provienen del conjunto <i>Monitoreo de los contaminantes del aire en Lima Metropolitana</i> del Servicio
  Nacional de Meteorología e Hidrología del Perú (SENAMHI), publicado en la
  <a href="https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de">Plataforma Nacional de Datos Abiertos</a>
  con licencia Open Data Commons Attribution. Son datos horarios validados, con corte al 31 de mayo de 2024.</p>
  <p>El diccionario de datos no indica las unidades. Las medias diarias calculadas aquí reproducen los máximos diarios
  de PM10 del boletín del SENAMHI de febrero de 2018 para Lima, que están en µg/m³, por lo que todos los valores se
  leen en esa unidad.</p>
  <p>No se encontraron fechas imposibles ni valores negativos. Hubo {n_conflicto} horas-estación del 1 de mayo de 2024
  repetidas con valores distintos, y se dejaron como faltantes.</p>
  <p>Una media diaria exige al menos 18 horas válidas (75 %). Una media anual solo se reporta cuando al menos el 75 %
  de los días del año son válidos; en otro caso se muestra como indicativa.</p>
  <p>El ECA fija para el PM10 100 µg/m³ en 24 horas, con hasta 7 excedencias al año, y 50 µg/m³ como media anual.
  Para el PM2.5 fija 50 µg/m³ en 24 horas, también con hasta 7 excedencias al año, y 25 µg/m³ como media anual.
  Para el NO2 fija 200 µg/m³ en 1 hora, con hasta 24 excedencias al año, y 100 µg/m³ como media anual. Las guías
  de la OMS de 2021 son 45 y 15 µg/m³ para el PM10, 15 y 5 µg/m³ para el PM2.5, y 25 y 10 µg/m³ para el NO2, en
  24 horas y como media anual.</p>
  <p>Son estaciones de vigilancia del aire ambiente, así que la comparación describe el aire que se respira en cada
  distrito y no evalúa el cumplimiento de ninguna fuente en particular. En el registro, {pm10_sobre} años-estación
  superaron el ECA de 24 horas de PM10 más de los 7 días que permite y {pm25_sobre} lo hicieron con el PM2.5,
  mientras que el ECA de 1 hora de NO2 se superó en {no2_horas} hora en total.</p>
  <p>El NO2 es el contaminante con más vacíos y, en los años incompletos, los conteos de excedencias son mínimos.
  El conjunto de datos no incluye meteorología, así que no se analiza el efecto del viento.</p>
</section>

<footer>
  Elaborado por Cristhian B. Gamarra Fuentes con Python, pandas y Plotly ·
  <a href="{repo}">código y datos en GitHub</a> ·
  contiene datos del SENAMHI (licencia Open Data Commons Attribution).
</footer>
</main>

<script>
const DATOS = {datos_js};
let contaminante = "PM10";

function elegirContaminante(c, inicial = false) {{
  contaminante = c;
  document.querySelectorAll("#contaminante button").forEach(b => b.setAttribute("aria-pressed", b.dataset.c === c));
  document.querySelectorAll(".etiqueta").forEach(el => el.textContent = DATOS.etiquetas[c]);
  // al cargar, las figuras ya muestran PM10 y el mapa aún no termina de cargar su estilo
  if (!inicial) {{
    for (const id of ["mapa", "anual", "excedencias", "cajas", "ciclo", "completitud"]) {{
      Plotly.restyle("fig-" + id, {{visible: DATOS.visibles[id][c]}}).catch(() => {{}});
    }}
  }}
  Plotly.relayout("fig-cajas", DATOS.lineas.cajas[c]);
  const pm = "24h" in DATOS.eca[c];
  document.getElementById("titulo-excedencias").textContent = pm ? "Días sobre el ECA de 24 horas" : "Horas sobre el ECA de 1 hora";
  document.getElementById("nota-excedencias").textContent = pm
    ? "El ECA permite hasta 7 días al año por encima del límite. En los años con datos faltantes, el conteo es un mínimo."
    : "El ECA permite hasta 24 horas al año por encima de 200 µg/m³. En los años con datos faltantes, el conteo es un mínimo.";
  document.querySelectorAll("tbody tr").forEach(tr => tr.hidden = tr.dataset.contaminante !== c);
  elegirEstacion(document.getElementById("estacion").value);
}}

function elegirEstacion(est) {{
  Plotly.restyle("fig-serie", {{visible: DATOS.visibles.serie[est + "|" + contaminante]}});
  Plotly.relayout("fig-serie", DATOS.lineas.serie[contaminante]);
}}

document.querySelectorAll("#contaminante button").forEach(b => b.addEventListener("click", () => elegirContaminante(b.dataset.c)));
document.getElementById("estacion").addEventListener("change", ev => elegirEstacion(ev.target.value));
window.addEventListener("load", () => elegirContaminante("PM10", true));
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
