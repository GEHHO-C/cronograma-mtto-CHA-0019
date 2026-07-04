"""
Cronograma de mantenimiento - Streamlit
========================================
AJUSTA LA SECCIÓN "CONFIGURACIÓN" con tus datos reales.
"""

import sqlite3
import datetime as dt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cronograma de mantenimiento", layout="wide")

# =========================================================
# CONFIGURACIÓN
# =========================================================
DB             = "CHA-0019-YA.db"
TABLA          = "Tabla1"
YEAR           = 2026
COL_TECNICA    = "Técnica de Mantenimiento"
COL_PLAN       = "Plan SAP"
COL_ACTIVIDAD  = "Actividad"
COL_FRECUENCIA = "FRECUENCIA PROG"   # en días
COL_EQUIPO     = "EQUIPO"
SECCION        = "Chancado"

USUARIOS = {
    "admin":   {"password": "mtto2026", "rol": "editor"},
    "viewer1": {"password": "ver123",   "rol": "viewer"},
    "viewer2": {"password": "ver123",   "rol": "viewer"},
}

UMBRAL_VERDE   = 10
UMBRAL_NARANJA = 20
MESES = ["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SET","OCT","NOV","DIC"]
DOW   = ["L","MA","MI","J","V","S","D"]
C_PEND    = "#4a90d9"
C_VERDE   = "#cdeede"
C_NARANJA = "#f5a623"
C_ROJO    = "#e23b3b"
C_HEADER  = "#1f6f8b"
C_MES     = "#3a8fb0"

# =========================================================
# LOGIN
# =========================================================
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.usuario   = ""
        st.session_state.rol       = ""
    if not st.session_state.logged_in:
        st.title("🔐 Cronograma de mantenimiento")
        st.markdown("---")
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.subheader("Iniciar sesión")
            user = st.text_input("Usuario")
            pwd  = st.text_input("Contraseña", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                if user in USUARIOS and USUARIOS[user]["password"] == pwd:
                    st.session_state.logged_in = True
                    st.session_state.usuario   = user
                    st.session_state.rol       = USUARIOS[user]["rol"]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
        st.stop()

check_login()
es_editor = (st.session_state.rol == "editor")

# =========================================================
# BD
# =========================================================
@st.cache_resource
def get_conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS ejecuciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_actividad INTEGER, fecha_programada TEXT,
        fecha_ejecucion TEXT, comentario TEXT)""")
    c.commit()
    return c

conn = get_conn()

@st.cache_data(ttl=0)
def load_df():
    # Usar sqlite3 nativo para máxima compatibilidad con Python 3.14+
    cur = conn.execute(f"SELECT rowid AS rowid, * FROM {TABLA}")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    data = [dict(zip(cols, row)) for row in rows]
    d = pd.DataFrame(data)
    # Leer fecha base directamente de la columna "Ultimo Mtto" de la BD.
    # Si una fila no tiene fecha, se usa el 1 de enero del año como fallback.
    if "Ultimo Mtto" in d.columns:
        d["fecha_base"] = pd.to_datetime(d["Ultimo Mtto"], errors="coerce")
        d["fecha_base"] = d["fecha_base"].fillna(pd.Timestamp(YEAR, 1, 1))
    else:
        d["fecha_base"] = pd.Timestamp(YEAR, 1, 1)
    return d

df = load_df()

def get_equipo_nombre():
    try:
        cols = {c.upper(): c for c in df.columns}
        col  = cols.get(COL_EQUIPO.upper())
        if not col: return "Equipo"
        v = df[col].iloc[0]
        return str(v).strip() if v else "Equipo"
    except: return "Equipo"

EQUIPO_NOMBRE = get_equipo_nombre()

# =========================================================
# LÓGICA DE PROGRAMACIÓN
# =========================================================
def get_ejecuciones():
    cur = conn.execute("SELECT * FROM ejecuciones")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    if not rows:
        return pd.DataFrame(columns=["id","id_actividad","fecha_programada",
                                     "fecha_ejecucion","comentario"])
    e = pd.DataFrame([dict(zip(cols, row)) for row in rows])
    e["fecha_programada"] = pd.to_datetime(e["fecha_programada"], errors="coerce")
    e["fecha_ejecucion"]  = pd.to_datetime(e["fecha_ejecucion"],  errors="coerce")
    return e

def semaforo_color(pct):
    if pct is None: return None
    if pct <= UMBRAL_VERDE:   return C_VERDE
    if pct <= UMBRAL_NARANJA: return C_NARANJA
    return C_ROJO

def generar_programacion(hoy):
    ejec_all = get_ejecuciones()
    prog_rows, resumen = [], {}
    year_start = pd.Timestamp(YEAR, 1, 1)
    limite     = pd.Timestamp(YEAR + 1, 12, 31)
    HOY        = pd.Timestamp(hoy)

    for _, row in df.iterrows():
        freq = int(row[COL_FRECUENCIA]); rid = row.get("rowid", row.get("id", 0))
        base = pd.Timestamp(row["fecha_base"])
        ea   = ejec_all[ejec_all["id_actividad"] == rid].copy() if not ejec_all.empty else pd.DataFrame()
        bef  = max(base, ea["fecha_ejecucion"].max()) if not ea.empty else base

        # ── EJECUCIONES REGISTRADAS POR EL USUARIO ───────────────
        hist = []
        if not ea.empty:
            for _, ej in ea.iterrows():
                fp = pd.Timestamp(ej["fecha_programada"])
                fe = pd.Timestamp(ej["fecha_ejecucion"])
                dp = abs((fe - fp).days)
                hist.append({"id_actividad": rid, "fecha_programada": fp,
                             "estado": "ejecutado", "fecha_ejecucion": fe,
                             "comentario": ej["comentario"],
                             "desvio_pct": (dp / freq * 100) if freq else 0})

        # ── RETROCESO: último mtto + X anteriores hasta enero ──────
        # Incluye la fecha base (último mtto real) como ejecutada,
        # y retrocede iterativamente hasta cubrir desde enero.
        # Todas aparecen en verde con comentario "Ejecutado correctamente".
        retro = []

        # Agregar la fecha base misma (último mtto) como ejecutada
        if bef.year == YEAR:
            retro.append({
                "id_actividad": rid,
                "fecha_programada": bef,
                "estado": "ejecutado",
                "fecha_ejecucion": bef,
                "comentario": "Ejecutado correctamente",
                "desvio_pct": 0.0,
            })

        # Retroceder iterativamente desde la base hasta enero
        cur_retro = bef
        s = 0
        while s < 500:
            cur_retro = cur_retro - pd.Timedelta(days=freq)
            if cur_retro < year_start:
                break
            ya_en_hist = any(
                abs((h["fecha_programada"] - cur_retro).days) <= 3
                for h in hist
            )
            if not ya_en_hist:
                retro.append({
                    "id_actividad": rid,
                    "fecha_programada": cur_retro,
                    "estado": "ejecutado",
                    "fecha_ejecucion": cur_retro,
                    "comentario": "Ejecutado correctamente",
                    "desvio_pct": 0.0,
                })
            s += 1

        # ── EVENTOS FUTUROS: desde bef + freq hacia adelante ─────
        fut = []; cur = bef + pd.Timedelta(days=freq); s = 0
        while cur <= limite and s < 500:
            fut.append({"id_actividad": rid, "fecha_programada": cur,
                        "estado": "vencido" if cur < HOY else "programado",
                        "fecha_ejecucion": None, "comentario": None, "desvio_pct": None})
            cur += pd.Timedelta(days=freq); s += 1

        todos = sorted(hist + retro + fut, key=lambda e: e["fecha_programada"])
        pf    = [e for e in fut if e["estado"] != "ejecutado"]
        prox  = pf[0] if pf else (fut[0] if fut else None)

        for e in todos:
            e["es_ultima"] = (prox is not None and e["fecha_programada"] == prox["fecha_programada"])
            if e["fecha_programada"].year == YEAR or (
                    e["fecha_ejecucion"] is not None and e["fecha_ejecucion"].year == YEAR):
                prog_rows.append(e)

        resumen[rid] = {"ultimo_mtto": bef, "proxima": prox}

    return (pd.DataFrame(prog_rows) if prog_rows else pd.DataFrame()), resumen

def registrar_ejecucion(id_act, fp, fe, com):
    conn.execute(
        "INSERT INTO ejecuciones (id_actividad,fecha_programada,fecha_ejecucion,comentario)"
        " VALUES (?,?,?,?)",
        (int(id_act), fp.strftime("%Y-%m-%d"), fe.strftime("%Y-%m-%d"), com))
    conn.commit()

def deshacer_ultima():
    r = conn.execute(
        "SELECT id FROM ejecuciones ORDER BY fecha_ejecucion DESC, id DESC LIMIT 1"
    ).fetchone()
    if r:
        conn.execute("DELETE FROM ejecuciones WHERE id = ?", (r[0],))
        conn.commit(); return True
    return False

def generar_semanas():
    ini = dt.date(YEAR, 1, 1); off = (ini.weekday() - 3) % 7; ini -= dt.timedelta(days=off)
    sems = []; fin = dt.date(YEAR, 12, 31); cur = ini
    while True:
        s = [cur + dt.timedelta(days=i) for i in range(7)]
        if any(d.year == YEAR for d in s): sems.append(s)
        if s[-1] > fin: break
        cur += dt.timedelta(days=7)
    return sems

SEMANAS = generar_semanas()

# =========================================================
# SESSION STATE
# =========================================================
for k, v in {"vista": "anual", "mes_idx": 0, "modal_rid": None,
             "modal_fp": None, "modal_com": "", "hoy": dt.date.today()}.items():
    if k not in st.session_state: st.session_state[k] = v

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    rol_label = "✏️ Editor" if es_editor else "👁️ Solo lectura"
    st.markdown(f"👤 **{st.session_state.usuario}** ({rol_label})")
    if st.button("Cerrar sesión"):
        st.session_state.logged_in = False
        st.session_state.usuario   = ""
        st.session_state.rol       = ""
        st.rerun()
    st.markdown("---")
    hoy_input = st.date_input("📅 Fecha actual del sistema", value=dt.date.today())
    st.session_state.hoy = hoy_input
    st.markdown("---")
    st.markdown("**Leyenda**")
    for color, desc in [
        (C_PEND,    "Programado pendiente"),
        (C_VERDE,   "Ejecutado (≤10% desvío)"),
        (C_NARANJA, "Advertencia (10–20% desvío)"),
        (C_ROJO,    "Vencido / >20% desvío"),
    ]:
        st.markdown(
            f'<span style="background:{color};padding:2px 12px;border-radius:3px;">'
            f'&nbsp;</span>&nbsp;{desc}', unsafe_allow_html=True)

prog_df, resumen = generar_programacion(hoy_input)

# =========================================================
# HELPERS HTML
# =========================================================
def th(t, bg=C_HEADER, fg="#fff", rs=1, cs=1, w="", extra=""):
    r = f' rowspan="{rs}"' if rs > 1 else ""
    c = f' colspan="{cs}"' if cs > 1 else ""
    mw = f"min-width:{w};" if w else ""
    return (f'<th{r}{c} style="background:{bg};color:{fg};border:1px solid #555;'
            f'padding:5px 7px;text-align:center;{mw}{extra}">{t}</th>')

def td(t, bg="#fff", fg="#000", bold=False, w="", borde="1px solid #ccc", extra=""):
    fw = "bold" if bold else "normal"
    mw = f"min-width:{w};" if w else ""
    return (f'<td style="background:{bg};color:{fg};border:{borde};'
            f'padding:4px 7px;text-align:center;font-weight:{fw};{mw}{extra}">{t}</td>')

# =========================================================
# MODAL DE REGISTRO
# =========================================================
if st.session_state.modal_rid is not None and es_editor:
    rid_m    = st.session_state.modal_rid
    fp_m     = st.session_state.modal_fp
    act_name = df.loc[df["rowid"] == rid_m, COL_ACTIVIDAD].iloc[0]
    freq_m   = int(df.loc[df["rowid"] == rid_m, COL_FRECUENCIA].iloc[0])

    prev = conn.execute(
        "SELECT fecha_ejecucion, comentario FROM ejecuciones "
        "WHERE id_actividad=? AND ABS(JULIANDAY(fecha_programada)-JULIANDAY(?))<=5 "
        "ORDER BY id DESC LIMIT 1",
        (int(rid_m), fp_m.strftime("%Y-%m-%d"))).fetchone()

    st.info(f"📋 **{act_name}** | Programado: **{fp_m.strftime('%d/%m/%Y')}** | Frecuencia: {freq_m} días")
    if prev:
        st.warning(f"⚠️ Registro previo: ejecutado el **{prev[0]}** · *{prev[1] or '(sin comentario)'}*")

    with st.form("form_ejec", clear_on_submit=True):
        cf, cc = st.columns([1, 2])
        with cf: fecha_ejec = st.date_input("📅 Fecha de ejecución real", value=fp_m.date())
        with cc: comentario = st.text_area("💬 Comentario", value=st.session_state.modal_com, height=80)
        b1, b2 = st.columns(2)
        guardar  = b1.form_submit_button("💾 Guardar", type="primary", use_container_width=True)
        cancelar = b2.form_submit_button("✖ Cancelar", use_container_width=True)

    if guardar:
        registrar_ejecucion(rid_m, fp_m, pd.Timestamp(fecha_ejec), comentario)
        st.success("✅ Ejecución registrada.")
        st.session_state.modal_rid = None; st.rerun()
    if cancelar:
        st.session_state.modal_rid = None; st.rerun()
    st.divider()

# =========================================================
# ENCABEZADO COMÚN
# =========================================================
def encabezado(subtitulo):
    st.markdown(f"""
    <div style="background:{C_HEADER};padding:14px 20px;border-radius:8px;margin-bottom:8px;">
      <div style="color:#b8d8ea;font-size:11px;letter-spacing:1px;text-transform:uppercase;">
        Equipo: <strong style="color:#fff;">{EQUIPO_NOMBRE}</strong>
        &nbsp;·&nbsp; Sección {SECCION}
      </div>
      <div style="color:#fff;font-size:19px;font-weight:700;margin-top:3px;">{subtitulo}</div>
    </div>""", unsafe_allow_html=True)

# =========================================================
# VISTA ANUAL
# =========================================================
if st.session_state.vista == "anual":
    encabezado(f"📅 Cronograma de mantenimiento — Anual {YEAR}")

    # Botones de mes (nativos Streamlit, siempre funcionan)
    cols_m = st.columns(12)
    for i, mes in enumerate(MESES):
        with cols_m[i]:
            bg_btn = C_MES
            if st.button(mes, key=f"m_{i}", use_container_width=True,
                         help=f"Ver programación semanal de {mes}"):
                st.session_state.vista   = "semanal"
                st.session_state.mes_idx = i
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabla anual HTML (visual)
    html = ['<div style="overflow-x:auto;font-size:12px;">',
            '<table style="border-collapse:collapse;width:100%;">']
    html.append('<tr>')
    for h, rs, w in [("Técnica",3,"90px"),("Plan SAP",3,"70px"),("Actividad",3,"220px"),
                     ("Frec.",3,"55px"),("Último mtto",3,"85px"),("Próximo mtto",3,"85px")]:
        html.append(th(h, rs=rs, w=w))
    html.append(th(f"Cronograma de mantenimiento — Anual {YEAR}", cs=24))
    html.append('</tr><tr>')
    for i, mes in enumerate(MESES):
        bg = C_MES
        html.append(th(mes, bg=bg, cs=2))
    html.append('</tr><tr>')
    for _ in MESES:
        html.append(th("P", bg="#3a8fb0", w="34px"))
        html.append(th("E", bg="#3a8fb0", w="34px"))
    html.append('</tr>')

    for tecnica, group in df.groupby(COL_TECNICA, sort=False):
        n = len(group); first = True
        for _, r in group.iterrows():
            rid = r["rowid"]
            html.append('<tr>')
            if first:
                html.append(th(tecnica, bg="#e8f5e9", fg="#1a6b2a", rs=n, w="90px"))
                first = False
            html.append(td(r[COL_PLAN], bg="#f5f5f5"))
            html.append(td(r[COL_ACTIVIDAD], bg="#fff", w="220px", extra="text-align:left;"))
            html.append(td(f"{int(r[COL_FRECUENCIA])} D", bg="#f5f5f5"))
            inf  = resumen.get(rid, {}); ult = inf.get("ultimo_mtto"); prox = inf.get("proxima")
            html.append(td(ult.strftime("%d/%m/%Y") if ult else "-", bg="#f5f5f5"))
            html.append(td(prox["fecha_programada"].strftime("%d/%m/%Y") if prox else "-", bg="#fff3e0"))

            acts = prog_df[prog_df["id_actividad"] == rid] if not prog_df.empty else prog_df
            for m in range(12):
                bp, tp = "#e7f1f8", ""
                be, te = "#fdf3e3", ""
                if not acts.empty:
                    ma = acts[acts["fecha_programada"].dt.month == (m + 1)]
                    if not ma.empty:
                        ev = ma.iloc[0]; estado = ev["estado"]
                        if estado == "ejecutado":
                            fe = ev["fecha_ejecucion"]
                            col = C_VERDE if (fe is not None and fe.month == m + 1) else C_ROJO
                            bp, tp = col, "X"
                            if fe is not None and fe.month - 1 == m: be, te = col, "X"
                        elif estado == "programado": bp, tp = C_PEND, "X"
                        elif estado == "vencido":    bp, tp = C_ROJO,  "X"
                html.append(td(tp, bg=bp, fg="#333", bold=bool(tp)))
                html.append(td(te, bg=be, fg="#333", bold=bool(te)))
            html.append('</tr>')

    html.append('</table></div>')
    st.markdown("".join(html), unsafe_allow_html=True)

# =========================================================
# VISTA SEMANAL
# =========================================================
else:
    mes_idx  = st.session_state.mes_idx
    mes_name = MESES[mes_idx]

    cb, ct, cd = st.columns([1, 4, 1])
    with cb:
        if st.button("← Vista anual"):
            st.session_state.vista = "anual"; st.rerun()
    with ct:
        encabezado(f"🗓️ {mes_name} {YEAR} — Programación semanal")
    with cd:
        if es_editor:
            if st.button("↩ Deshacer", type="secondary"):
                if deshacer_ultima(): st.success("Registro eliminado."); st.rerun()
                else: st.warning("No hay registros.")

    # Selector de mes
    cols_m = st.columns(12)
    for i, mes in enumerate(MESES):
        with cols_m[i]:
            t = "primary" if i == mes_idx else "secondary"
            if st.button(mes, key=f"sm_{i}", type=t, use_container_width=True):
                st.session_state.mes_idx = i; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    for wi, semana in enumerate(SEMANAS):
        dias_mes = [d for d in semana if d.month == (mes_idx + 1) and d.year == YEAR]
        if not dias_mes: continue

        st.markdown(f"#### Semana {wi + 1}")

        html = ['<div style="overflow-x:auto;font-size:11px;">',
                '<table style="border-collapse:collapse;">']
        html.append('<tr>')
        for h, rs, w in [("Técnica",2,"90px"),("Plan SAP",2,"60px"),("Actividad",2,"200px"),
                         ("Frec.",2,"50px"),("Último mtto",2,"80px"),("Próximo mtto",2,"80px")]:
            html.append(th(h, rs=rs, w=w))
        for d in semana:
            bg = C_MES
            html.append(th(f"{DOW[d.weekday()]}<br>{d.strftime('%d/%m/%Y')}", bg=bg, cs=2))
        html.append('</tr><tr>')
        for _ in semana:
            html.append(th("P", bg="#3a8fb0", w="32px"))
            html.append(th("E", bg="#3a8fb0", w="32px"))
        html.append('</tr>')

        botones_semana = []

        for tecnica, group in df.groupby(COL_TECNICA, sort=False):
            n = len(group); first = True
            for _, r in group.iterrows():
                rid = r["rowid"]
                html.append('<tr>')
                if first:
                    html.append(th(tecnica, bg="#e8f5e9", fg="#1a6b2a", rs=n, w="90px"))
                    first = False
                html.append(td(r[COL_PLAN], bg="#f5f5f5"))
                html.append(td(r[COL_ACTIVIDAD], bg="#fff", w="200px", extra="text-align:left;"))
                html.append(td(f"{int(r[COL_FRECUENCIA])} D", bg="#f5f5f5"))
                inf  = resumen.get(rid, {}); ult = inf.get("ultimo_mtto"); prox = inf.get("proxima")
                html.append(td(ult.strftime("%d/%m/%Y") if ult else "-", bg="#f5f5f5"))
                html.append(td(prox["fecha_programada"].strftime("%d/%m/%Y") if prox else "-", bg="#fff3e0"))

                acts = prog_df[prog_df["id_actividad"] == rid] if not prog_df.empty else prog_df

                for d in semana:
                    bp, fg_p, tp = "#e7f1f8", "#000", ""
                    be, fg_e, te = "#fdf3e3", "#000", ""
                    es_ultima = False; tip_p = ""; tip_e = ""

                    if not acts.empty:
                        m_prog = acts[acts["fecha_programada"].dt.date == d]
                        m_ejec = acts[acts["fecha_ejecucion"].notna() &
                                      (acts["fecha_ejecucion"].dt.date == d)]

                        if not m_prog.empty:
                            ev = m_prog.iloc[0]; es_ultima = bool(ev["es_ultima"]); estado = ev["estado"]
                            if estado == "ejecutado":
                                col = semaforo_color(ev["desvio_pct"]) or C_VERDE
                                bp, fg_p, tp = col, "#000", "X"
                                fe  = ev["fecha_ejecucion"]; dev = ev["desvio_pct"]; com = ev["comentario"] or ""
                                tip_p = (f"Prog: {d.strftime('%d/%m/%Y')} | "
                                         f"Ejec: {fe.strftime('%d/%m/%Y') if fe else '-'}"
                                         + (f" | Desvío: {dev:.1f}%" if dev is not None else "")
                                         + (f" | {com}" if com else ""))
                            elif estado == "programado":
                                bp, fg_p, tp = C_PEND, "#fff", "X"
                                tip_p = f"Programado: {d.strftime('%d/%m/%Y')}"
                            elif estado == "vencido":
                                bp, fg_p, tp = C_ROJO, "#fff", "X"
                                tip_p = f"Vencido: {d.strftime('%d/%m/%Y')}"

                        if not m_ejec.empty:
                            ev2 = m_ejec.iloc[0]; col2 = semaforo_color(ev2["desvio_pct"]) or C_VERDE
                            be, fg_e, te = col2, "#000", "X"
                            com2 = ev2["comentario"] or ""; dev2 = ev2["desvio_pct"]
                            fe2  = ev2["fecha_ejecucion"]
                            tip_e = (f"Ejecutado: {fe2.strftime('%d/%m/%Y') if fe2 else '-'}"
                                     + (f" | Desvío: {dev2:.1f}%" if dev2 is not None else "")
                                     + (f" | 💬 {com2}" if com2 else ""))

                    if es_ultima and not m_prog.empty and ev["estado"] in ("programado", "vencido"):
                        botones_semana.append({
                            "rid": rid, "fp": ev["fecha_programada"],
                            "com": ev["comentario"] or "", "act": r[COL_ACTIVIDAD], "wi": wi
                        })

                    borde_p = "3px solid #185fa5" if es_ultima else "1px solid #ccc"
                    tt_p = f'title="{tip_p}"' if tip_p else ""
                    tt_e = f'title="{tip_e}"' if tip_e else ""
                    html.append(f'<td {tt_p} style="background:{bp};color:{fg_p};border:{borde_p};'
                                f'text-align:center;padding:3px 5px;font-weight:bold;">{tp}</td>')
                    html.append(f'<td {tt_e} style="background:{be};color:{fg_e};border:1px solid #ccc;'
                                f'text-align:center;padding:3px 5px;font-weight:bold;">{te}</td>')
                html.append('</tr>')

        html.append('</table></div>')
        st.markdown("".join(html), unsafe_allow_html=True)

        if botones_semana and es_editor:
            st.markdown("**📝 Registrar ejecución:**")
            cols_b = st.columns(min(3, len(botones_semana)))
            for bi, btn in enumerate(botones_semana):
                nombre = btn["act"][:35] + ("..." if len(btn["act"]) > 35 else "")
                with cols_b[bi % 3]:
                    if st.button(f"📝 {nombre}", key=f"btn_{btn['rid']}_{btn['wi']}",
                                 use_container_width=True):
                        st.session_state.modal_rid = btn["rid"]
                        st.session_state.modal_fp  = btn["fp"]
                        st.session_state.modal_com = btn["com"]
                        st.rerun()
        elif botones_semana and not es_editor:
            st.caption("👁️ Solo el editor puede registrar ejecuciones.")

        st.divider()
