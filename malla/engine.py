"""malla/engine.py — Motor de procesamiento de malla curricular"""
import re
import json
import warnings
import pandas as pd
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Mapa de áreas por prefijo de código ───────────────────────────
AREAS_MAP = {
    "FMMP": "Cs. Básicas",   "CFIS": "Cs. Básicas",
    "FMSP": "Cs. Básicas",   "QUIM": "Cs. Básicas",
    "PTEC": "Programación",  "CINF": "Computación",
    "TDFI": "Ing. Software", "ING":  "Form. General",
    "ACAD": "Form. General", "CEG":  "Form. General",
}

# Estimaciones para asignaturas sin dato histórico
ESTIMACIONES_DEFAULT = {
    "FMMP112": 62, "CFIS328": 72, "FMMP312": 58, "CFIS344": 68,
    "ING119":  88, "ING239":  91, "ING249":  92,
    "ACAD102": 94, "CEGHC11": 95, "QUIM090": 86, "CEGRS14": 96,
    "CINF100": 91, "TDFI103": 80,
    "CINF103": 65, "PTEC103": 83, "PTEC104": 79,
    "TDFI105": 72, "TDFI106": 84, "PTEC106": 83,
    "PTEC107": 81, "CINF107": 76, "CINF200": 82,
    "CINF111": 88, "CINF112": 88,
    "CINF113": 88, "CINF300": 92, "CINF400": 81,
}


def area_de(codigo: str) -> str:
    for prefijo, area in AREAS_MAP.items():
        if str(codigo).startswith(prefijo):
            return area
    return "General"


# ─────────────────────────────────────────────────────────────────
# Lectura de malla
# ─────────────────────────────────────────────────────────────────
def leer_malla(path) -> pd.DataFrame:
    """
    Lee el Excel de malla curricular.
    Estructura esperada:
      Fila 0  → encabezados (Semestre | Código | Asignatura | ... | CRÉD UNAB | PREREQ)
      Fila 1+ → datos con filas de grupo de semestre intercaladas
    Usa sheet_name=0 para evitar errores por nombre de hoja.
    """
    df = pd.read_excel(path, sheet_name=0, header=None)

    registros   = []
    sem_actual  = None
    fila_en_sem = 0

    for idx, row in df.iterrows():
        if idx == 0:
            continue  # encabezados

        codigo = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""

        # Fila de grupo de semestre
        if not codigo or codigo == "nan" or len(codigo) < 4 or not codigo[0].isalpha():
            s = re.search(r"(\d+)", str(row.iloc[0]))
            if s:
                sem_actual  = int(s.group(1))
                fila_en_sem = 0
            continue

        cred   = pd.to_numeric(row.iloc[9],  errors="coerce") if len(row) > 9  else 0
        prereq = str(row.iloc[10]).strip()   if len(row) > 10 and pd.notna(row.iloc[10]) else "—"
        if prereq == "nan":
            prereq = "—"

        registros.append({
            "semestre":       sem_actual,
            "fila":           fila_en_sem,
            "codigo":         codigo,
            "nombre":         str(row.iloc[2]).strip(),
            "creditos":       int(cred) if pd.notna(cred) else 0,
            "area":           area_de(codigo),
            "prerrequisitos": prereq,
        })
        fila_en_sem += 1

    if not registros:
        raise ValueError("No se encontraron asignaturas en el archivo de malla. "
                         "Verifica que el formato sea correcto.")

    return pd.DataFrame(registros)


# ─────────────────────────────────────────────────────────────────
# Lectura de actas
# ─────────────────────────────────────────────────────────────────
def leer_actas(path) -> pd.DataFrame:
    """
    Lee el Excel de actas/proyección.
    Estructura esperada:
      Fila 0 → título
      Fila 1 → subtítulo
      Fila 2 → encabezados reales  (header=2)
    Columnas clave: Código | %reprobación XXXXXX
    """
    df = pd.read_excel(path, sheet_name=0, header=2)
    df.columns = df.columns.str.strip().str.replace("\n", " ")

    # Detectar columnas de reprobación por contenido
    cols_rep = [c for c in df.columns if "reprob" in str(c).lower()]
    col510   = next((c for c in cols_rep if "202510" in str(c)), None)
    col410   = next((c for c in cols_rep if "202410" in str(c)), None)

    # Si no hay columnas con periodo específico, usar las primeras dos de reprobación
    if not col510 and len(cols_rep) >= 1:
        col510 = cols_rep[0]
    if not col410 and len(cols_rep) >= 2:
        col410 = cols_rep[1]

    # Columna de código
    col_cod = next((c for c in df.columns if "digo" in str(c)), df.columns[1])

    # Filtrar filas válidas
    df = df[pd.notna(df[col_cod])].copy()
    df[col_cod] = df[col_cod].astype(str).str.strip()
    df = df[df[col_cod].str.len() >= 4].copy()
    df = df[~df[col_cod].str.contains("Semestre|°|Código", na=False)].copy()
    df = df[df[col_cod].str[0].str.isalpha()].copy()

    registros = []
    for _, row in df.iterrows():
        cod  = row[col_cod]
        r510 = pd.to_numeric(row.get(col510), errors="coerce") if col510 else None
        r410 = pd.to_numeric(row.get(col410), errors="coerce") if col410 else None

        if pd.notna(r510) and pd.notna(r410):
            pct    = round(100 - (r510 + r410) / 2, 1)
            fuente = f"Prom {col510}/{col410}"
            est    = False
        elif pd.notna(r510):
            pct    = round(100 - r510, 1)
            fuente = f"{col510} · {r510:.1f}% reprob."
            est    = False
        elif pd.notna(r410):
            pct    = round(100 - r410, 1)
            fuente = f"{col410} · {r410:.1f}% reprob."
            est    = False
        else:
            pct    = None
            fuente = "Sin datos históricos"
            est    = True

        registros.append({"codigo": cod, "pct_aprob": pct,
                          "fuente": fuente, "es_estimado": est})

    if not registros:
        raise ValueError("No se encontraron registros de actas válidos.")

    return pd.DataFrame(registros)


# ─────────────────────────────────────────────────────────────────
# Procesamiento completo
# ─────────────────────────────────────────────────────────────────
def procesar(path_malla, path_actas,
             estimaciones: dict = None) -> dict:
    """
    Orquesta la lectura, unión y cálculo.
    Retorna un dict con: df, estadisticas, js_data, n_criticas, pct_promedio
    """
    if estimaciones is None:
        estimaciones = ESTIMACIONES_DEFAULT

    df_malla = leer_malla(path_malla)
    df_actas  = leer_actas(path_actas)

    df = df_malla.merge(df_actas, on="codigo", how="left")

    # Completar sin datos
    for idx, row in df.iterrows():
        if pd.isna(row.get("pct_aprob")):
            val = estimaciones.get(row["codigo"], 80.0)
            df.at[idx, "pct_aprob"]   = float(val)
            df.at[idx, "fuente"]      = "Estimado contextual"
            df.at[idx, "es_estimado"] = True

    df["pct_aprob"]   = df["pct_aprob"].astype(float)
    df["es_estimado"] = df["es_estimado"].fillna(False).astype(bool)

    df_real    = df[~df["es_estimado"]]
    n_criticas = int((df_real["pct_aprob"] < 55).sum())
    pct_prom   = round(float(df_real["pct_aprob"].mean()), 1) if len(df_real) else 0

    js_data = [
        {
            "sem":      int(r.semestre),
            "fila":     int(r.fila),
            "nombre":   str(r.nombre),
            "codigo":   str(r.codigo),
            "pct":      float(round(r.pct_aprob, 1)),
            "area":     str(r.area),
            "creditos": int(r.creditos),
            "prereq":   str(r.prerrequisitos),
            "fuente":   str(r.fuente),
            "estimado": bool(r.es_estimado),
        }
        for r in df.itertuples()
    ]

    return {
        "df":           df,
        "js_data":      js_data,
        "n_asignaturas": len(df),
        "n_con_datos":  int(len(df_real)),
        "n_criticas":   n_criticas,
        "pct_promedio": pct_prom,
    }


# ─────────────────────────────────────────────────────────────────
# Generación del HTML
# ─────────────────────────────────────────────────────────────────
def generar_html(resultado: dict, carrera, periodo: str) -> str:
    """Genera el HTML completo del dashboard a partir del resultado de procesar()."""

    df       = resultado["df"]
    js_data  = resultado["js_data"]
    N_SEMS   = int(df["semestre"].max())
    MAX_FILA = int(df["fila"].max())
    FECHA    = datetime.now().strftime("%d/%m/%Y %H:%M")
    DATA_JS  = json.dumps(js_data, ensure_ascii=False)

    VV = carrera.umbral_verde
    VA = carrera.umbral_amarillo
    VN = carrera.umbral_naranjo

    df_real  = df[~df["es_estimado"]]
    criticas = df_real[df_real["pct_aprob"] < VA].sort_values("pct_aprob")
    risk_html = " &nbsp;·&nbsp; ".join(
        f'{r.nombre} <strong>{r.codigo}</strong> ({r.pct_aprob}%)'
        for r in criticas.itertuples()
    ) or "Ninguna asignatura crítica con datos reales."

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Estrés de Malla — {carrera.nombre}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.31.0/dist/tabler-icons.min.css">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
:root{{--bg:#fff;--bg2:#f5f5f3;--bg3:#eeede9;--t1:#1a1a18;--t2:#5a5a56;--t3:#9a9a94;
      --b1:rgba(0,0,0,.18);--b2:rgba(0,0,0,.10);--b3:rgba(0,0,0,.06);--r:8px;--rl:12px;}}
@media(prefers-color-scheme:dark){{:root{{--bg:#1c1c1a;--bg2:#252523;--bg3:#2e2e2b;
  --t1:#e8e8e2;--t2:#a0a09a;--t3:#606060;
  --b1:rgba(255,255,255,.18);--b2:rgba(255,255,255,.10);--b3:rgba(255,255,255,.06);}}}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
      background:var(--bg3);color:var(--t1);min-height:100vh;}}
.hdr{{background:var(--bg);border-bottom:.5px solid var(--b2);
      padding:16px 22px 13px;position:sticky;top:0;z-index:100;}}
.hdr h1{{font-size:16px;font-weight:600;}}
.hdr p{{font-size:11px;color:var(--t2);margin-top:2px;}}
.legend{{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px;}}
.leg{{display:flex;align-items:center;gap:4px;font-size:10px;color:var(--t2);}}
.leg-dot{{width:10px;height:10px;border-radius:2px;flex-shrink:0;}}
.leg-stripe{{width:10px;height:10px;border-radius:2px;border:.5px solid #999;opacity:.7;
  background:repeating-linear-gradient(135deg,#ccc 0,#ccc 1.5px,transparent 1.5px,transparent 4px);}}
.main{{padding:16px 16px 40px;max-width:1500px;margin:0 auto;}}
.filters{{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:11px;}}
.fbtn{{font-size:10.5px;border:.5px solid var(--b2);border-radius:20px;padding:3px 11px;
       cursor:pointer;background:transparent;color:var(--t2);font-family:inherit;}}
.fbtn.active,.fbtn:hover{{background:#e6f0fb;color:#1a5fa5;border-color:#a8ccf0;}}
.gw{{background:var(--bg);border-radius:var(--rl);border:.5px solid var(--b2);
     padding:13px;overflow-x:auto;}}
.grid{{display:grid;gap:3px;}}
.sh{{font-size:9.5px;font-weight:600;color:var(--t2);text-align:center;
     padding:3px 2px 6px;border-bottom:1.5px solid var(--b2);}}
.sh span{{display:block;font-size:8px;font-weight:400;opacity:.55;}}
.al{{font-size:7.5px;color:var(--t3);writing-mode:vertical-rl;transform:rotate(180deg);
     display:flex;align-items:center;justify-content:center;border-right:2px solid var(--b3);}}
.cell{{border-radius:5px;padding:4px 5px;cursor:pointer;border:.5px solid transparent;
       transition:transform .1s,box-shadow .1s;min-height:62px;display:flex;
       flex-direction:column;justify-content:space-between;position:relative;}}
.cell:hover{{transform:scale(1.07);z-index:20;box-shadow:0 4px 18px rgba(0,0,0,.15);}}
.cell.empty{{background:transparent!important;border-color:transparent!important;
             cursor:default;min-height:62px;}}
.cell.empty:hover{{transform:none;box-shadow:none;}}
.cn{{font-size:8px;font-weight:600;line-height:1.3;}}
.cc{{font-size:7.5px;opacity:.6;margin-top:1px;font-family:monospace;}}
.cb{{display:flex;align-items:center;margin-top:3px;}}
.cp{{font-size:10px;font-weight:700;}}
.bb{{height:3px;border-radius:2px;flex:1;margin-left:4px;}}
.bf{{height:3px;border-radius:2px;}}
.ed{{position:absolute;top:3px;right:3px;width:6px;height:6px;
     border-radius:50%;background:#999;opacity:.55;}}
#tt{{position:fixed;background:var(--bg);border:.5px solid var(--b1);border-radius:10px;
     padding:10px 13px;font-size:11px;pointer-events:none;z-index:9999;max-width:248px;
     box-shadow:0 6px 24px rgba(0,0,0,.17);display:none;}}
.tn{{font-weight:600;font-size:12.5px;color:var(--t1);margin-bottom:5px;line-height:1.3;}}
.tr{{display:flex;justify-content:space-between;gap:8px;color:var(--t2);margin-top:2px;font-size:10.5px;}}
.tv{{color:var(--t1);font-weight:500;text-align:right;max-width:145px;line-height:1.3;}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin-top:13px;}}
@media(max-width:700px){{.stats{{grid-template-columns:repeat(2,1fr);}}}}
.stat{{background:var(--bg);border:.5px solid var(--b2);border-radius:var(--r);padding:11px 13px;}}
.sl{{font-size:10px;color:var(--t2);font-weight:500;}}
.sv{{font-size:26px;font-weight:700;color:var(--t1);margin-top:3px;letter-spacing:-1px;}}
.ss{{font-size:9.5px;color:var(--t3);margin-top:2px;}}
.st{{font-size:10.5px;font-weight:600;color:var(--t2);
     text-transform:uppercase;letter-spacing:.5px;margin:15px 0 7px;}}
.sg{{display:grid;grid-template-columns:repeat(2,1fr);gap:4px 18px;}}
.sr{{display:flex;align-items:center;gap:7px;}}
.sl2{{font-size:10px;color:var(--t2);width:58px;flex-shrink:0;}}
.sb{{flex:1;height:9px;background:var(--bg2);border-radius:4px;overflow:hidden;}}
.sf{{height:9px;border-radius:4px;}}
.sp{{font-size:10px;font-weight:700;width:36px;text-align:right;flex-shrink:0;}}
.rb{{margin-top:12px;padding:9px 13px;border-radius:var(--r);border:.5px solid #f0a09a;
     background:#fdecea;font-size:11px;color:#7f1d1d;
     display:flex;align-items:flex-start;gap:7px;line-height:1.5;}}
.ib{{margin-top:7px;padding:7px 13px;border-radius:var(--r);border:.5px solid var(--b2);
     background:var(--bg2);font-size:10.5px;color:var(--t2);
     display:flex;align-items:flex-start;gap:7px;line-height:1.5;}}
@media(prefers-color-scheme:dark){{.rb{{border-color:#7a1515;background:#3d0a0a;color:#f28585;}}}}
.ft{{text-align:center;font-size:10px;color:var(--t3);margin-top:26px;padding-bottom:14px;}}
</style>
</head>
<body>
<div id="tt"></div>
<div class="hdr">
  <h1>{carrera.nombre} — {carrera.codigo} · Estrés de Malla</h1>
  <p>{carrera.campus} · Período {periodo} · Generado el {FECHA}</p>
  <div class="legend">
    <div class="leg"><div class="leg-dot" style="background:#2a9d5c"></div>≥ {VV}% sin riesgo</div>
    <div class="leg"><div class="leg-dot" style="background:#f4a922"></div>{VA}–{VV-1}% moderado</div>
    <div class="leg"><div class="leg-dot" style="background:#e8693a"></div>{VN}–{VA-1}% alto</div>
    <div class="leg"><div class="leg-dot" style="background:#c0392b"></div>&lt; {VN}% crítico</div>
    <div class="leg"><div class="leg-stripe"></div>sin dato histórico</div>
  </div>
</div>
<div class="main">
  <div class="filters" id="filters"></div>
  <div class="gw"><div class="grid" id="grid"></div></div>
  <div class="stats" id="stats"></div>
  <div class="st">Promedio de aprobación por semestre</div>
  <div class="gw" style="padding:12px 14px"><div class="sg" id="ssem"></div></div>
  <div class="rb">
    <i class="ti ti-alert-triangle" style="font-size:15px;flex-shrink:0;margin-top:1px"></i>
    <span><strong>{len(criticas)} asignaturas con datos reales y aprobación &lt; {VA}%</strong>
    — cuellos de botella que afectan titulación oportuna:<br>
    <span style="margin-top:3px;display:inline-block">{risk_html}</span></span>
  </div>
  <div class="ib">
    <i class="ti ti-info-circle" style="font-size:14px;flex-shrink:0;margin-top:1px"></i>
    <span>Asignaturas con punto gris ● = sin historial de reprobación.
    Valores son estimaciones contextuales. Actualizar al subir actas reales.</span>
  </div>
  <div class="ft">{carrera.nombre} · {carrera.campus} · {FECHA}</div>
</div>
<script>
const DATA={DATA_JS};
const VV={VV},VA={VA},VN={VN},NS={N_SEMS},MF={MAX_FILA};
const DK=matchMedia('(prefers-color-scheme:dark)').matches;
function gc(p){{
  if(DK){{
    if(p>=VV)return{{bg:"#0d3320",tx:"#6fcf97",br:"#27ae60",bd:"#1a6641"}};
    if(p>=VA)return{{bg:"#3d2a00",tx:"#f6c142",br:"#f4a922",bd:"#7a5a00"}};
    if(p>=VN)return{{bg:"#3d1400",tx:"#f4976c",br:"#e8693a",bd:"#8a3010"}};
    return{{bg:"#3d0a0a",tx:"#f28585",br:"#c0392b",bd:"#7a1515"}};
  }}
  if(p>=VV)return{{bg:"#e6f4ec",tx:"#1a5e35",br:"#2a9d5c",bd:"#a8d5b8"}};
  if(p>=VA)return{{bg:"#fef7e6",tx:"#7a4f00",br:"#f4a922",bd:"#f5d080"}};
  if(p>=VN)return{{bg:"#fdf0eb",tx:"#7a2e10",br:"#e8693a",bd:"#f0b89a"}};
  return{{bg:"#fdecea",tx:"#7f1d1d",br:"#c0392b",bd:"#f0a09a"}};
}}
const g=document.getElementById('grid');
g.style.gridTemplateColumns='36px '+Array(NS).fill('minmax(88px,1fr)').join(' ');
g.style.minWidth=Math.max(800,NS*100)+'px';
g.appendChild(document.createElement('div'));
for(let s=1;s<=NS;s++){{
  const h=document.createElement('div');h.className='sh';
  h.innerHTML=`S${{s}}<span>Semestre ${{s}}</span>`;g.appendChild(h);
}}
for(let f=0;f<=MF;f++){{
  const ri=DATA.filter(d=>d.fila===f);
  const al=document.createElement('div');al.className='al';
  if(ri.length){{al.textContent=ri[0].area;al.style.color='#888';al.style.fontSize='7.5px';}}
  g.appendChild(al);
  for(let s=1;s<=NS;s++){{
    const item=DATA.find(d=>d.sem===s&&d.fila===f);
    const cell=document.createElement('div');
    if(!item){{cell.className='cell empty';}}
    else{{
      const c=gc(item.pct);
      cell.className='cell';cell.style.background=c.bg;cell.style.borderColor=c.bd;
      cell.dataset.code=item.codigo;cell.dataset.area=item.area;
      if(item.estimado)cell.style.backgroundImage=
        'repeating-linear-gradient(135deg,rgba(0,0,0,.03) 0,rgba(0,0,0,.03) 2px,transparent 2px,transparent 8px)';
      cell.innerHTML=`
        ${{item.estimado?'<div class="ed"></div>':''}}
        <div><div class="cn" style="color:${{c.tx}}">${{item.nombre}}</div>
        <div class="cc" style="color:${{c.tx}}">${{item.codigo}}</div></div>
        <div class="cb"><span class="cp" style="color:${{c.tx}}">${{item.pct}}%</span>
        <div class="bb" style="background:${{c.bd}}55">
          <div class="bf" style="width:${{item.pct}}%;background:${{c.br}}"></div>
        </div></div>`;
      cell.addEventListener('mouseenter',e=>ts(e,item,c));
      cell.addEventListener('mousemove',tm);
      cell.addEventListener('mouseleave',th);
    }}
    g.appendChild(cell);
  }}
}}
const tt=document.getElementById('tt');
function ts(e,d,c){{
  const rk=d.pct>=VV?'Sin riesgo':d.pct>=VA?'Moderado':d.pct>=VN?'Alto':'⚠ Crítico';
  const im=d.pct<VN?'Bloquea titulación':d.pct<VA?'Retrasa progresión':d.pct<VV?'Observar':'—';
  tt.innerHTML=`<div class="tn">${{d.nombre}}</div>
    <div class="tr"><span>Código</span><span class="tv" style="font-family:monospace">${{d.codigo}}</span></div>
    <div class="tr"><span>Semestre</span><span class="tv">${{d.sem}}°</span></div>
    <div class="tr"><span>Área</span><span class="tv">${{d.area}}</span></div>
    <div class="tr"><span>Créditos</span><span class="tv">${{d.creditos}}</span></div>
    <div class="tr"><span>Aprobación</span>
      <span class="tv" style="color:${{c.br}};font-weight:700">
        ${{d.pct}}% <span style="opacity:.7">(${{(100-d.pct).toFixed(1)}}% reprob.)</span></span></div>
    <div class="tr"><span>Fuente</span><span class="tv">${{d.fuente}}</span></div>
    <div class="tr"><span>Riesgo</span><span class="tv" style="color:${{c.br}}">${{rk}}</span></div>
    <div class="tr"><span>Impacto</span><span class="tv">${{im}}</span></div>
    <div class="tr"><span>Prerrequisitos</span><span class="tv">${{d.prereq}}</span></div>`;
  tt.style.display='block';tm(e);
}}
function tm(e){{
  let x=e.clientX+14,y=e.clientY+14;
  if(x+255>window.innerWidth)x=e.clientX-255;
  if(y+265>window.innerHeight)y=e.clientY-265;
  tt.style.left=x+'px';tt.style.top=y+'px';
}}
function th(){{tt.style.display='none';}}
const areas=[...new Set(DATA.map(d=>d.area))];
const fe=document.getElementById('filters');
['Todas','Solo reales','Solo estimados',...areas].forEach((lb,i)=>{{
  const b=document.createElement('button');
  b.className='fbtn'+(i===0?' active':'');b.textContent=lb;
  b.addEventListener('click',()=>{{
    document.querySelectorAll('.fbtn').forEach(x=>x.classList.remove('active'));
    b.classList.add('active');
    document.querySelectorAll('.cell:not(.empty)').forEach(cell=>{{
      const it=DATA.find(d=>d.codigo===cell.dataset.code);
      if(!it){{cell.style.opacity='1';return;}}
      if(i===0)cell.style.opacity='1';
      else if(i===1)cell.style.opacity=it.estimado?'0.1':'1';
      else if(i===2)cell.style.opacity=it.estimado?'1':'0.1';
      else cell.style.opacity=it.area===lb?'1':'0.1';
    }});
  }});
  fe.appendChild(b);
}});
const rd=DATA.filter(d=>!d.estimado);
const av=rd.length?(rd.reduce((a,b)=>a+b.pct,0)/rd.length).toFixed(1):0;
const cr=rd.filter(d=>d.pct<VN),ri=rd.filter(d=>d.pct<VA);
const lw=rd.reduce((a,b)=>a.pct<b.pct?a:b,rd[0]||{{}});
document.getElementById('stats').innerHTML=`
  <div class="stat"><div class="sl">Aprobación promedio real</div>
    <div class="sv">${{av}}%</div><div class="ss">${{rd.length}} asignaturas con datos</div></div>
  <div class="stat"><div class="sl">Asignaturas críticas</div>
    <div class="sv" style="color:#c0392b">${{cr.length}}</div>
    <div class="ss">aprobación &lt; ${{VN}}%</div></div>
  <div class="stat"><div class="sl">En zona de riesgo</div>
    <div class="sv" style="color:#e8693a">${{ri.length}}</div>
    <div class="ss">aprobación &lt; ${{VA}}%</div></div>
  <div class="stat"><div class="sl">Mayor reprobación</div>
    <div class="sv" style="font-size:11px;line-height:1.3;margin-top:5px">${{lw.nombre||'—'}}</div>
    <div class="ss">${{lw.pct||0}}% · S${{lw.sem||'?'}}</div></div>`;
const se=document.getElementById('ssem');
for(let s=1;s<=NS;s++){{
  const sd=DATA.filter(d=>d.sem===s);if(!sd.length)continue;
  const av2=sd.reduce((a,b)=>a+b.pct,0)/sd.length;
  const c=gc(av2);const row=document.createElement('div');row.className='sr';
  row.innerHTML=`<span class="sl2">S${{s}}° sem.</span>
    <div class="sb"><div class="sf" style="width:${{av2.toFixed(0)}}%;background:${{c.br}}"></div></div>
    <span class="sp" style="color:${{c.br}}">${{av2.toFixed(0)}}%</span>`;
  se.appendChild(row);
}}
</script>
</body></html>"""
