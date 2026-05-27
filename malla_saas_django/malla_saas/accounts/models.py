"""accounts/models.py — Organizaciones (universidades) y usuarios"""
from django.db import models
from django.contrib.auth.models import AbstractUser


class Organization(models.Model):
    """Una universidad o institución cliente del SaaS."""
    nombre    = models.CharField(max_length=200)
    slug      = models.SlugField(unique=True, help_text="Identificador URL, ej: unab")
    logo      = models.ImageField(upload_to="logos/", blank=True, null=True)
    activa    = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Organización"
        verbose_name_plural = "Organizaciones"
        ordering            = ["nombre"]

    def __str__(self):
        return self.nombre


class User(AbstractUser):
    """Usuario extendido con organización y rol."""

    class Rol(models.TextChoices):
        ADMIN     = "admin",     "Administrador SaaS"
        ORG_ADMIN = "org_admin", "Admin de Institución"
        DOCENTE   = "docente",   "Jefe de Carrera / Docente"
        VIEWER    = "viewer",    "Solo Lectura"

    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="users"
    )
    rol = models.CharField(
        max_length=20, choices=Rol.choices, default=Rol.VIEWER
    )

    class Meta:
        verbose_name        = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"

    @property
    def puede_subir(self):
        return self.rol in (self.Rol.ADMIN, self.Rol.ORG_ADMIN, self.Rol.DOCENTE)

    @property
    def es_admin_saas(self):
        return self.rol == self.Rol.ADMIN or self.is_superuser
