"""
seed.py — Crea datos iniciales para arrancar el proyecto
Ejecutar: python seed.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from accounts.models import Organization, User
from malla.models import Carrera

# ── Organización ──────────────────────────────────────────────────
org, created = Organization.objects.get_or_create(
    slug="unab",
    defaults={"nombre": "Universidad Andrés Bello", "activa": True}
)
print(f"{'Creada' if created else 'Ya existe'} organización: {org}")

# ── Usuarios ──────────────────────────────────────────────────────
admin_pass   = os.environ.get("PASS_ADMIN",   "admin2026")
docente_pass = os.environ.get("PASS_DOCENTE", "docencia2026")

admin, c = User.objects.get_or_create(username="admin", defaults={
    "email": "admin@unab.cl", "first_name": "Admin",
    "organization": org, "rol": User.Rol.ORG_ADMIN, "is_staff": True,
})
if c:
    admin.set_password(admin_pass)
    admin.save()
print(f"{'Creado' if c else 'Ya existe'} usuario: admin / {admin_pass if c else '(contraseña existente)'}")

docente, c = User.objects.get_or_create(username="jefe_carrera", defaults={
    "email": "docencia@unab.cl", "first_name": "Jorge", "last_name": "Sabattin",
    "organization": org, "rol": User.Rol.DOCENTE,
})
if c:
    docente.set_password(docente_pass)
    docente.save()
print(f"{'Creado' if c else 'Ya existe'} usuario: jefe_carrera / {docente_pass if c else '(contraseña existente)'}")

# ── Carrera ICI ───────────────────────────────────────────────────
carrera, c = Carrera.objects.get_or_create(
    organization=org, codigo="UNAB12210",
    defaults={
        "nombre":         "Ingeniería Civil en Informática",
        "campus":         "Campus Antonio Varas",
        "n_semestres":    10,
        "umbral_verde":   85,
        "umbral_amarillo":70,
        "umbral_naranjo": 55,
        "activa":         True,
    }
)
print(f"{'Creada' if c else 'Ya existe'} carrera: {carrera}")

print("\n✓ Seed completado. Accede en http://localhost:8000")
print(f"  Usuario admin   : admin / {admin_pass}")
print(f"  Usuario docente : jefe_carrera / {docente_pass}")
