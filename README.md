# MallaIQ — Dashboard Estrés de Malla Curricular
**SaaS multi-universidad · Django · Campus Antonio Varas UNAB**

---

## Estructura del proyecto

```
malla_saas/
│
├── config/
│   ├── settings.py       ← Configuración Django
│   └── urls.py           ← URLs raíz
│
├── accounts/             ← App: usuarios y organizaciones
│   ├── models.py         ← Organization, User (multi-tenant)
│   ├── views.py          ← Login / logout / perfil
│   └── urls.py
│
├── malla/                ← App: análisis de malla
│   ├── models.py         ← Carrera, Asignatura, AnalisisMalla
│   ├── views.py          ← Dashboard, subida, visualización
│   ├── engine.py         ← Motor de procesamiento Excel → HTML
│   └── urls.py
│
├── templates/
│   ├── base.html         ← Layout con sidebar
│   ├── accounts/
│   │   └── login.html
│   └── malla/
│       ├── dashboard.html
│       ├── carrera_detail.html
│       ├── subir.html
│       └── ver_analisis.html
│
├── manage.py
├── seed.py               ← Datos iniciales
├── requirements.txt
└── .env.example          ← Variables de entorno (copiar a .env)
```

---

## Instalación y puesta en marcha

### 1. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores reales
```

### 3. Crear tablas en la BD

```bash
python manage.py makemigrations accounts malla
python manage.py migrate
```

### 4. Crear datos iniciales (organización + usuarios + carrera ICI)

```bash
python seed.py
```

### 5. Arrancar el servidor

```bash
python manage.py runserver
# → http://localhost:8000
```

---

## Credenciales iniciales

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| `admin` | `admin2026` | Admin de institución |
| `jefe_carrera` | `docencia2026` | Jefe de Carrera (puede subir Excel) |

---

## Flujo de uso

```
1. Login  →  Dashboard  →  Seleccionar carrera
2. "Nuevo análisis"  →  Subir malla.xlsx + actas.xlsx  →  Indicar período
3. Django procesa con engine.py  →  Genera HTML dashboard
4. Ver análisis inline (iframe)  →  Descargar HTML standalone
```

---

## Archivos Excel esperados

### malla.xlsx (primera hoja)
| Posición | Contenido |
|----------|-----------|
| Fila 0   | Encabezados |
| Col 0    | Semestre (ej: "1° Semestre") |
| Col 1    | Código asignatura |
| Col 2    | Nombre asignatura |
| Col 9    | Créditos UNAB |
| Col 10   | Prerrequisitos |

### actas.xlsx (primera hoja)
| Posición | Contenido |
|----------|-----------|
| Fila 0   | Título general |
| Fila 1   | Subtítulo |
| Fila 2   | Encabezados reales |
| Col X    | `%reprobación 202510` |
| Col Y    | `%reprobación 202410` |

---

## Agregar nuevas universidades (multi-tenant)

```bash
# Via admin Django (http://localhost:8000/admin/)
# 1. Crear Organization  →  nombre + slug
# 2. Crear User          →  asignar a la organización + rol
# 3. Crear Carrera       →  asociar a la organización
```

---

## Despliegue en producción

```bash
# 1. Cambiar en .env:
DEBUG=False
ALLOWED_HOSTS=tu-dominio.cl
SECRET_KEY=clave-larga-aleatoria

# 2. Colectar estáticos
python manage.py collectstatic --no-input

# 3. Arrancar con Gunicorn
gunicorn config.wsgi:application -w 2 -b 0.0.0.0:8000

# 4. Nginx como proxy inverso (ver documentación)
```

---

## Endpoints disponibles

| URL | Descripción |
|-----|-------------|
| `/` | Dashboard principal |
| `/accounts/login/` | Login |
| `/carrera/<pk>/` | Detalle carrera + historial análisis |
| `/carrera/<pk>/subir/` | Subir Excel + generar análisis |
| `/analisis/<pk>/` | Ver dashboard interactivo |
| `/analisis/<pk>/descargar/` | Descargar HTML standalone |
| `/analisis/<pk>/api/` | Stats JSON (integración externa) |
| `/admin/` | Admin Django |
