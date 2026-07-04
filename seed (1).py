"""
Ejecutar UNA SOLA VEZ para crear mi_basedatos.db con datos de ejemplo.
En Streamlit Cloud, la BD se incluye en el repositorio o se crea en el
primer arranque usando este script.

    python seed.py
"""
import sqlite3

DB = "mi_basedatos.db"
TABLA = "Tabla1"

actividades = [
    ("PREDICTIVA", "20868", "Análisis vibracional (Analizador EMERSON CSI 2140)", 30),
    ("PREDICTIVA", "20868", "Análisis vibracional (Analizador EMERSON CSI 2140) - Eq2", 30),
    ("PREDICTIVA", "-",     "Monitoreo de parámetros (Cámara termográfica FLIR C5)", 30),
    ("PREDICTIVA", "-",     "Monitoreo de parámetros (Cámara termográfica FLIR C5) - Eq2", 30),
    ("PREDICTIVA", "-",     "Muestreo de aceites", 30),
    ("PLANES PREVENTIVOS", "25678", "5A Transmisión: cambiar volante", 1800),
    ("PLANES PREVENTIVOS", "25679", "1A Transmisión: cambiar brazo de seguridad", 360),
    ("PLANES PREVENTIVOS", "25680", "8M Transmisión: cambiar faja de transmisión", 240),
    ("PLANES PREVENTIVOS", "25681", "5A Transmisión: cambiar rodamiento eje excéntrico", 1800),
    ("PLANES PREVENTIVOS", "25682", "2A Transmisión: cambiar semibiela", 720),
    ("PLANES PREVENTIVOS", "25684", "5A Transmisión: cambiar puentes", 1800),
    ("PLANES PREVENTIVOS", "25685", "3M Transmisión: cambiar diafragma", 90),
    ("PLANES PREVENTIVOS", "25686", "4A Transmisión: cambiar resortes", 1440),
    ("PLANES PREVENTIVOS", "25687", "3M Ajuste: cambio perno templ. quijada móvil", 90),
    ("PLANES PREVENTIVOS", "25689", "4A Ajuste: cambio resorte templador q. fija", 1440),
    ("PLANES PREVENTIVOS", "25690", "15M Trituración: cambio muelas fijas y móvil", 450),
    ("PLANES PREVENTIVOS", "25691", "3A Trituración: cambio planchas laterales", 1080),
    ("PLANES PREVENTIVOS", "25692", "3A Cambiar bocina del eje pivotante", 1080),
    ("PLANES PREVENTIVOS", "25693", "1.5M CHA-0019-YA cambio de aceite", 45),
    ("PLANES PREVENTIVOS", "25694", "2A Lubricación: cambiar bomba lubricación", 720),
    ("PLANES PREVENTIVOS", "33148", "Cambio de canal espaciador", 70),
]

conn = sqlite3.connect(DB)
cur  = conn.cursor()

cur.execute(f"""
CREATE TABLE IF NOT EXISTS {TABLA} (
    "Técnica de Mantenimiento" TEXT,
    "Plan SAP"                 TEXT,
    "Actividad"                TEXT,
    "FRECUENCIA PROG"          INTEGER
)""")

cur.execute(f"SELECT COUNT(*) FROM {TABLA}")
if cur.fetchone()[0] == 0:
    cur.executemany(
        f'INSERT INTO {TABLA} VALUES (?,?,?,?)',
        [(tec, plan, act, frec) for tec, plan, act, frec in actividades]
    )
    print(f"✅ {len(actividades)} actividades creadas en {DB}")
else:
    print("La BD ya tiene datos. No se modificó.")

cur.execute("""
CREATE TABLE IF NOT EXISTS ejecuciones (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    id_actividad     INTEGER,
    fecha_programada TEXT,
    fecha_ejecucion  TEXT,
    comentario       TEXT
)""")

conn.commit()
conn.close()
