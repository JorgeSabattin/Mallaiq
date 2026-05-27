"""malla/models.py — Carreras, asignaturas y análisis de estrés"""
from django.db import models
from accounts.models import Organization, User


class Carrera(models.Model):
    """Una carrera universitaria con su malla curricular."""
    organization  = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                      related_name="carreras")
    nombre        = models.CharField(max_length=200)
    codigo        = models.CharField(max_length=20)
    campus        = models.CharField(max_length=100, blank=True)
    n_semestres   = models.PositiveSmallIntegerField(default=10)
    activa        = models.BooleanField(default=True)
    creada_en     = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    # Umbrales de color (% aprobación)
    umbral_verde    = models.PositiveSmallIntegerField(default=85)
    umbral_amarillo = models.PositiveSmallIntegerField(default=70)
    umbral_naranjo  = models.PositiveSmallIntegerField(default=55)

    class Meta:
        verbose_name        = "Carrera"
        verbose_name_plural = "Carreras"
        unique_together     = [("organization", "codigo")]
        ordering            = ["organization", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo}) — {self.organization}"


class Asignatura(models.Model):
    """Una asignatura dentro de la malla de una carrera."""
    carrera        = models.ForeignKey(Carrera, on_delete=models.CASCADE,
                                       related_name="asignaturas")
    codigo         = models.CharField(max_length=20)
    nombre         = models.CharField(max_length=200)
    semestre       = models.PositiveSmallIntegerField()
    fila           = models.PositiveSmallIntegerField(default=0,
                        help_text="Posición vertical dentro del semestre (0-based)")
    area           = models.CharField(max_length=100, blank=True)
    creditos       = models.PositiveSmallIntegerField(default=0)
    prerrequisitos = models.CharField(max_length=300, blank=True, default="—")

    class Meta:
        verbose_name        = "Asignatura"
        verbose_name_plural = "Asignaturas"
        unique_together     = [("carrera", "codigo")]
        ordering            = ["semestre", "fila"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre} (S{self.semestre})"


class AnalisisMalla(models.Model):
    """
    Un análisis de estrés generado a partir de la subida de Excel.
    Guarda el HTML resultante y metadata del proceso.
    """
    class Estado(models.TextChoices):
        PROCESANDO = "procesando", "Procesando"
        LISTO      = "listo",      "Listo"
        ERROR      = "error",      "Error"

    carrera       = models.ForeignKey(Carrera, on_delete=models.CASCADE,
                                      related_name="analisis")
    creado_por    = models.ForeignKey(User, on_delete=models.SET_NULL,
                                      null=True, related_name="analisis")
    periodo       = models.CharField(max_length=20, help_text="Ej: 202510")
    estado        = models.CharField(max_length=15, choices=Estado.choices,
                                     default=Estado.PROCESANDO)
    # Archivos fuente subidos
    archivo_malla = models.FileField(upload_to="uploads/malla/")
    archivo_actas = models.FileField(upload_to="uploads/actas/")
    # HTML generado
    html_resultado = models.TextField(blank=True)
    # Metadata del análisis
    n_asignaturas  = models.PositiveSmallIntegerField(default=0)
    n_con_datos    = models.PositiveSmallIntegerField(default=0)
    n_criticas     = models.PositiveSmallIntegerField(default=0)
    pct_promedio   = models.FloatField(default=0)
    mensaje_error  = models.TextField(blank=True)
    creado_en      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Análisis de Malla"
        verbose_name_plural = "Análisis de Malla"
        ordering            = ["-creado_en"]

    def __str__(self):
        return f"{self.carrera} · {self.periodo} ({self.get_estado_display()})"

    @property
    def listo(self):
        return self.estado == self.Estado.LISTO
