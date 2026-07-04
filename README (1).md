# Cronograma de mantenimiento — Streamlit Cloud

Aplicación web de cronograma de mantenimiento preventivo/predictivo.

## Archivos del proyecto

```
app.py            ← aplicación principal (Streamlit)
requirements.txt  ← dependencias Python
seed.py           ← crea la BD de ejemplo (ejecutar localmente una vez)
mi_basedatos.db   ← tu base de datos SQLite (subir al repositorio)
README.md
```

---

## Pasos para desplegar GRATIS en Streamlit Community Cloud

### 1. Instalar Git y preparar el repositorio (en tu PC)

```bash
# Si no tienes Git: https://git-scm.com/downloads
git init cronograma-mtto
cd cronograma-mtto
# Copia aquí los archivos: app.py, requirements.txt, seed.py, README.md
# y tu mi_basedatos.db ya existente
```

### 2. Crear cuenta en GitHub (si no tienes)
Ir a https://github.com → Sign up (gratis)

### 3. Crear un repositorio en GitHub
- New repository → nombre: `cronograma-mtto`
- Visibility: **Private** (recomendado para datos de empresa)
- Clic en "Create repository"

### 4. Subir los archivos a GitHub

```bash
git add .
git commit -m "Primer commit - cronograma de mantenimiento"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/cronograma-mtto.git
git push -u origin main
```

### 5. Desplegar en Streamlit Community Cloud
1. Ir a https://share.streamlit.io
2. Sign in with GitHub
3. Clic en **"New app"**
4. Seleccionar:
   - Repository: `TU_USUARIO/cronograma-mtto`
   - Branch: `main`
   - Main file path: `app.py`
5. Clic en **"Deploy!"**

En ~2 minutos tendrás una URL pública tipo:
`https://cronograma-mtto-XXXX.streamlit.app`

---

## Configuración de la app

Edita la sección `CONFIGURACIÓN` al inicio de `app.py`:

```python
DB = "mi_basedatos.db"       # nombre de tu BD
TABLA = "Tabla1"             # nombre de la tabla
COL_TECNICA = "Técnica de Mantenimiento"
COL_PLAN = "Plan SAP"
COL_ACTIVIDAD = "Actividad"
COL_FRECUENCIA = "FRECUENCIA PROG"  # en días

fechas_base_lista = [
    "16/01/2026", ...  # una fecha por fila, en el mismo orden
]
```

---

## Notas importantes sobre Streamlit Cloud

- **La BD se guarda en el repositorio** (GitHub). Cada vez que el usuario
  registra una ejecución, la BD se modifica en el servidor de Streamlit,
  pero **no se sincroniza automáticamente con GitHub**.
  
- **Solución para producción**: migrar la BD a un servicio externo como
  [Supabase](https://supabase.com) (PostgreSQL gratuito) o
  [Turso](https://turso.tech) (SQLite en la nube, gratis).
  Para pruebas con 1-3 usuarios, la BD local en Streamlit Cloud es suficiente.

- **La app se "duerme"** tras 7 días sin visitas (free tier). Se despierta
  sola en ~30 segundos cuando alguien la visita.

- **Control de acceso**: para restringir acceso por usuario, añade
  `streamlit-authenticator` al requirements.txt (se puede configurar
  en el futuro cuando se consolide la versión de pruebas).

---

## Uso de la app

| Acción | Cómo |
|--------|------|
| Cambiar fecha del sistema | Barra lateral → "Fecha actual" |
| Ver vista semanal | Barra lateral → "🗓️ Semanal" → elegir mes |
| Registrar ejecución | Vista semanal → botón "📝 Actividad..." bajo la semana |
| Deshacer último registro | Vista semanal → botón "↩ Deshacer" |
| Ver comentarios | Aparecen en el formulario de registro de esa X |
