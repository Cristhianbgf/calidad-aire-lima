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
PLOTLY_SRI = "sha384-cCVCZkAjYNxaYKbM8lsArLznDF/SvMFr1jcZrvOpSTCa0W40ZAdLzHCEulnUa5i7"  # hash de integridad (SRI) de ese mismo archivo

CONTAMINANTES = ["PM10", "PM25", "NO2"]
ETIQUETA = {"PM10": "PM10", "PM25": "PM2.5", "NO2": "NO2"}
UNIDAD = "µg/m³"
ECA = {"PM10": {"24h": 100, "anual": 50}, "PM25": {"24h": 50, "anual": 25}, "NO2": {"1h": 200, "anual": 100}}
OMS = {"PM10": {"24h": 45, "anual": 15}, "PM25": {"24h": 15, "anual": 5}, "NO2": {"24h": 25, "anual": 10}}

TEXTO, TEXTO_2, TENUE, GRILLA, EJE, BLANCO = "#222222", "#555555", "#888888", "#e6e6e6", "#bbbbbb", "#ffffff"
# Okabe-Ito (apta para daltonismo) más un vino para la séptima estación
COLORES_ESTACION = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#882255"]
AZULES_MAPA = ["#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"]  # Blues de ColorBrewer sin los más claros
CONFIG = {"displaylogo": False, "responsive": True,
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
    lineas.append((OMS[c]["24h"], f"WHO 24 h · {OMS[c]['24h']}", TENUE, "dot"))
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
            hovertemplate="<b>%{text}</b> · %{customdata[0]}<br>" + f"{ETIQUETA[c]} mean 2015-2024: " +
                          "%{customdata[1]} " + UNIDAD + "<br>Days with valid data: %{customdata[2]} %<extra></extra>",
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
            hovertemplate="<b>%{y}</b> · %{x}<br>Annual mean: %{z:.1f} " + UNIDAD +
                          f"<br>Annual ECA: {limite} · WHO: {OMS[c]['anual']}" +
                          "<br>Days with valid data: %{customdata} %<extra></extra>"))
        fig.add_trace(go.Heatmap(
            z=debiles.notna().astype(float).where(debiles.notna()).values, x=anios, y=orden,
            colorscale=[[0, "#eeeeee"], [1, "#eeeeee"]], showscale=False, xgap=2, ygap=2,
            text=debiles.round(0).astype("Int64").astype(str).replace("<NA>", "").radd("(").add(")")
                        .replace("()", "").values,
            texttemplate="%{text}", textfont=dict(color=TENUE), customdata=cob.values, visible=(i == 0),
            hovertemplate="<b>%{y}</b> · %{x}<br>Indicative only: %{customdata} % valid days"
                          "<br>(an annual mean needs at least 75 %)<extra></extra>"))
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
        que = "Days above the 24 h ECA" if pm else "Hours above the 1 h ECA"
        fig.add_trace(go.Heatmap(
            z=z.values, x=anios, y=orden, colorscale="Oranges", zmin=0, xgap=2, ygap=2,
            text=z.values, texttemplate="%{text}", customdata=cob.values, visible=(i == 0),
            colorbar=dict(title=dict(text="days" if pm else "hours", font=dict(color=TEXTO_2)),
                          thickness=12, tickfont=dict(color=TEXTO_2)),
            hovertemplate="<b>%{y}</b> · %{x}<br>" + que + ": %{z}" + f" (allowed: {7 if pm else 24} per year)" +
                          "<br>Days with valid data: %{customdata} %<extra></extra>"))
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
            hovertemplate="%{x|%d %b %Y}<br>Daily mean: %{y} " + UNIDAD + "<extra></extra>"))
    fig.update_layout(**diseno(420), showlegend=False, hovermode="x", **lineas_limite(CONTAMINANTES[0]))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.07, bgcolor="#f2f2f2"),
                     rangeselector=dict(buttons=[dict(count=1, label="1 year", step="year", stepmode="backward"),
                                                 dict(count=3, label="3 years", step="year", stepmode="backward"),
                                                 dict(step="all", label="All")],
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
    fig.update_xaxes(title=dict(text=f"Daily mean ({UNIDAD})", font=dict(color=TEXTO_2)), rangemode="tozero")
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
    fig.update_xaxes(title=dict(text="Hour of day (local time, UTC-5)", font=dict(color=TEXTO_2)),
                     dtick=2, range=[-0.5, 23.5])
    fig.update_yaxes(title=dict(text=f"Mean ({UNIDAD})", font=dict(color=TEXTO_2)), rangemode="tozero")
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
            colorbar=dict(title=dict(text="% hours", font=dict(color=TEXTO_2)), thickness=12,
                          tickfont=dict(color=TEXTO_2)),
            hovertemplate="<b>%{y}</b> · %{x}<br>Hours with valid data: %{z} %<extra></extra>"))
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
            f'<td>{"reportable" if r.media_reportable else "indicative"}</td>'
            f'<td class="num">{int(corto)}</td><td class="num">{int(r.dias_sobre_oms_24h)}</td></tr>')

    C = resumen["contaminantes"]
    horas = f"{resumen['horas_estacion_con_datos']:,}".replace(",", " ")
    tarjetas = [
        ("Network", f"{resumen['estaciones']} stations", f"January 2015 to May 2024, with {horas} station-hours of data"),
        ("PM10", f"{C['PM10']['reportables_sobre_eca_anual']} of {C['PM10']['anios_estacion_reportables']}",
         f"station-years with enough data above the annual ECA ({ECA['PM10']['anual']} {UNIDAD})"),
        ("PM2.5", f"{C['PM25']['reportables_sobre_eca_anual']} of {C['PM25']['anios_estacion_reportables']}",
         f"station-years with enough data above the annual ECA ({ECA['PM25']['anual']} {UNIDAD})"),
        ("NO2", f"{C['NO2']['reportables_sobre_eca_anual']} of {C['NO2']['anios_estacion_reportables']}",
         f"above the annual ECA, although all {C['NO2']['reportables_sobre_oms_anual']} exceed the WHO guideline"),
    ]
    tarjetas_html = "".join(f'<div class="tarjeta"><div class="tarjeta-titulo">{k}</div><div class="tarjeta-valor">{v}</div>'
                            f'<div class="tarjeta-texto">{html.escape(d)}</div></div>' for k, v, d in tarjetas)
    opciones = "".join(f'<option value="{html.escape(est)}">{html.escape(est)}</option>' for est in orden)
    datos_js = json.dumps({"visibles": visibles, "lineas": lineas, "etiquetas": ETIQUETA, "eca": ECA},
                          ensure_ascii=False)

    pagina = PLANTILLA.format(
        plotly_cdn=PLOTLY_CDN, plotly_sri=PLOTLY_SRI, sitio=SITIO, repo=REPO, tarjetas=tarjetas_html,
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
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Air quality in Lima, 2015-2024</title>
<meta name="description" content="Dashboard of PM10, PM2.5 and NO2 from the seven SENAMHI automatic stations in Metropolitan Lima, compared with the Peruvian air quality standard (ECA) and the 2021 WHO guidelines.">
<meta property="og:type" content="website">
<meta property="og:title" content="Air quality in Metropolitan Lima, 2015-2024">
<meta property="og:description" content="PM10, PM2.5 and NO2 from the seven SENAMHI stations against the Peruvian air quality standard (ECA) and the WHO guidelines.">
<meta property="og:url" content="{sitio}">
<meta property="og:image" content="{sitio}figuras/compartir.png">
<meta name="twitter:card" content="summary_large_image">
<script src="{plotly_cdn}" integrity="{plotly_sri}" crossorigin="anonymous" charset="utf-8"></script>
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
<h1>Air quality in Metropolitan Lima, 2015-2024</h1>
<p class="entrada">Hourly PM10, PM2.5 and NO2 concentrations from the seven SENAMHI automatic stations,
compared with Peru's Environmental Quality Standard for Air (ECA, D.S. 003-2017-MINAM) and with the 2021 WHO
air quality guidelines. The ECA is the legal reference in Peru, while the WHO guidelines are a health reference
and are not binding.</p>

<div class="barra" role="toolbar" aria-label="Pollutant">
  <span>Pollutant</span>
  <div class="botones" id="contaminante">
    <button data-c="PM10" aria-pressed="true">PM10</button>
    <button data-c="PM25" aria-pressed="false">PM2.5</button>
    <button data-c="NO2" aria-pressed="false">NO2</button>
  </div>
</div>

<div class="tarjetas">{tarjetas}</div>

<div class="panel">
  <h2>Where is the air worst? Mean <span class="etiqueta"></span> by station</h2>
  <p class="nota">Mean of all valid daily means in the record. Larger, darker circles mean higher concentrations.</p>
  {fig_mapa}
</div>

<div class="dos-columnas">
  <div class="panel">
    <h2>Annual mean against the ECA</h2>
    <p class="nota">Red means the annual mean exceeds the ECA and blue that it is below. Grey values in
    brackets are indicative, because that year has less than 75 % of days with valid data.</p>
    {fig_anual}
  </div>
  <div class="panel">
    <h2 id="titulo-excedencias">Days above the 24-hour ECA</h2>
    <p class="nota" id="nota-excedencias">The ECA allows up to 7 days per year above the limit. In years with
    missing data, the count is a minimum.</p>
    {fig_excedencias}
  </div>
</div>

<div class="panel">
  <h2>Daily mean <span class="etiqueta"></span>, day by day</h2>
  <div class="control"><label for="estacion">Station</label><select id="estacion">{opciones}</select></div>
  {fig_serie}
</div>

<div class="dos-columnas">
  <div class="panel">
    <h2>How different are the stations?</h2>
    <p class="nota">Distribution of daily mean <span class="etiqueta"></span>. The box covers the middle half
    of the days and the inner line is the median.</p>
    {fig_cajas}
  </div>
  <div class="panel">
    <h2>At what time of day is it worst?</h2>
    <p class="nota">Mean <span class="etiqueta"></span> for each hour of the day, all years together.</p>
    {fig_ciclo}
  </div>
</div>

<div class="panel">
  <h2>How complete is the record?</h2>
  <p class="nota">Percentage of hours with a valid <span class="etiqueta"></span> value, by station and year (2024 covers January to May).</p>
  {fig_completitud}
</div>

<details>
  <summary>Annual summary table by station and year (<span class="etiqueta"></span>)</summary>
  <div class="tabla"><table>
    <thead><tr><th>Station</th><th>Year</th><th>Valid days (%)</th><th>Annual mean (µg/m³)</th><th>Annual mean</th>
    <th>Above the short-term ECA*</th><th>Days above WHO 24 h</th></tr></thead>
    <tbody>{filas_tabla}</tbody>
  </table></div>
  <p class="metodo">* Days above the 24-hour ECA for PM10 and PM2.5, and hours above the 1-hour ECA for NO2.
  You can download the <a href="data/procesado/diario.csv">daily means (CSV)</a> and the
  <a href="salidas/resumen_anual.csv">annual summary (CSV)</a>.</p>
</details>

<section class="metodo">
  <h2>Data and method</h2>
  <p>The data come from the dataset <i>Monitoreo de los contaminantes del aire en Lima Metropolitana</i> of Peru's
  National Meteorology and Hydrology Service (SENAMHI), published on the
  <a href="https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de">Plataforma Nacional de Datos Abiertos</a>
  (Peru's open data platform) under the Open Data Commons Attribution licence. They are validated hourly data up to 31 May 2024.</p>
  <p>The data dictionary does not state the units. The daily means computed here reproduce the daily PM10 maxima
  of SENAMHI's February 2018 bulletin for Lima, which are in µg/m³, so all values are read in that unit.</p>
  <p>No impossible dates or negative values were found. There were {n_conflicto} station-hours on 1 May 2024
  duplicated with different values, and they were set as missing.</p>
  <p>A daily mean requires at least 18 valid hours (75 %). An annual mean is only reported when at least 75 %
  of the days of the year are valid; otherwise it is shown as indicative.</p>
  <p>The ECA sets 100 µg/m³ over 24 hours for PM10, with up to 7 exceedances per year, and 50 µg/m³ as the annual
  mean. For PM2.5 it sets 50 µg/m³ over 24 hours, also with up to 7 exceedances per year, and 25 µg/m³ as the annual
  mean. For NO2 it sets 200 µg/m³ over 1 hour, with up to 24 exceedances per year, and 100 µg/m³ as the annual mean.
  The 2021 WHO guidelines are 45 and 15 µg/m³ for PM10, 15 and 5 µg/m³ for PM2.5, and 25 and 10 µg/m³ for NO2,
  over 24 hours and as the annual mean.</p>
  <p>These are ambient air monitoring stations, so the comparison describes the air breathed in each district and
  does not assess the compliance of any particular source. In the record, {pm10_sobre} station-years exceeded the
  24-hour PM10 ECA on more than the 7 days it allows and {pm25_sobre} did so for PM2.5, while the 1-hour NO2 ECA
  was exceeded in {no2_horas} hour in total.</p>
  <p>NO2 is the pollutant with the most gaps, and in incomplete years exceedance counts are minimums.
  The dataset does not include meteorology, so the effect of wind is not analysed.</p>
</section>

<footer>
  Made by Cristhian B. Gamarra Fuentes with Python, pandas and Plotly ·
  <a href="{repo}">code and data on GitHub</a> ·
  contains SENAMHI data (Open Data Commons Attribution licence).
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
  document.getElementById("titulo-excedencias").textContent = pm ? "Days above the 24-hour ECA" : "Hours above the 1-hour ECA";
  document.getElementById("nota-excedencias").textContent = pm
    ? "The ECA allows up to 7 days per year above the limit. In years with missing data, the count is a minimum."
    : "The ECA allows up to 24 hours per year above 200 µg/m³. In years with missing data, the count is a minimum.";
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
