"""malla/views.py"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Carrera, Asignatura, AnalisisMalla
from .engine import procesar, generar_html, leer_malla


# ── Decorador: la organización del usuario debe estar activa ───────
def org_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.organization:
            messages.error(request, "Tu cuenta no está asociada a ninguna institución.")
            return redirect("accounts:login")
        if not request.user.organization.activa:
            return render(request, "malla/inactiva.html", status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Vistas principales ─────────────────────────────────────────────
@login_required
@org_required
def dashboard(request):
    """Listado de carreras y últimos análisis de la organización."""
    org      = request.user.organization
    carreras = Carrera.objects.filter(organization=org, activa=True)\
                              .prefetch_related("analisis")
    # Último análisis por carrera
    ultimos = {}
    for c in carreras:
        ul = c.analisis.filter(estado=AnalisisMalla.Estado.LISTO).first()
        ultimos[c.pk] = ul

    return render(request, "malla/dashboard.html", {
        "carreras": carreras,
        "ultimos":  ultimos,
        "org":      org,
    })


@login_required
@org_required
def carrera_detail(request, pk):
    """Detalle de una carrera: lista de análisis."""
    org     = request.user.organization
    carrera = get_object_or_404(Carrera, pk=pk, organization=org)
    analisis = carrera.analisis.all()
    return render(request, "malla/carrera_detail.html", {
        "carrera": carrera,
        "analisis": analisis,
    })


@login_required
@org_required
def subir_excel(request, carrera_pk):
    """Formulario de subida de Excel + procesamiento."""
    org     = request.user.organization
    carrera = get_object_or_404(Carrera, pk=carrera_pk, organization=org)

    if not request.user.puede_subir:
        messages.error(request, "No tienes permisos para subir archivos.")
        return redirect("malla:carrera_detail", pk=carrera_pk)

    if request.method == "POST":
        archivo_malla = request.FILES.get("archivo_malla")
        archivo_actas = request.FILES.get("archivo_actas")
        periodo       = request.POST.get("periodo", "").strip()

        # Validaciones básicas
        errores = []
        if not archivo_malla:
            errores.append("Falta el archivo de malla.")
        if not archivo_actas:
            errores.append("Falta el archivo de actas.")
        if not periodo:
            errores.append("Falta el período (ej: 202510).")
        if errores:
            for e in errores:
                messages.error(request, e)
            return render(request, "malla/subir.html",
                          {"carrera": carrera, "errores": errores})

        # Crear registro de análisis
        analisis = AnalisisMalla.objects.create(
            carrera       = carrera,
            creado_por    = request.user,
            periodo       = periodo,
            estado        = AnalisisMalla.Estado.PROCESANDO,
            archivo_malla = archivo_malla,
            archivo_actas = archivo_actas,
        )

        # Procesar
        try:
            resultado = procesar(
                analisis.archivo_malla.path,
                analisis.archivo_actas.path,
            )
            html = generar_html(resultado, carrera, periodo)

            analisis.html_resultado = html
            analisis.n_asignaturas  = resultado["n_asignaturas"]
            analisis.n_con_datos    = resultado["n_con_datos"]
            analisis.n_criticas     = resultado["n_criticas"]
            analisis.pct_promedio   = resultado["pct_promedio"]
            analisis.estado         = AnalisisMalla.Estado.LISTO
            analisis.save()

            # Actualizar asignaturas en BD (opcional, para reportes futuros)
            _actualizar_asignaturas(carrera, resultado["df"])

            messages.success(request,
                f"✓ Análisis generado: {resultado['n_asignaturas']} asignaturas, "
                f"{resultado['n_con_datos']} con datos reales.")
            return redirect("malla:ver_analisis", pk=analisis.pk)

        except Exception as exc:
            analisis.estado        = AnalisisMalla.Estado.ERROR
            analisis.mensaje_error = str(exc)
            analisis.save()
            messages.error(request, f"Error al procesar: {exc}")
            return render(request, "malla/subir.html", {"carrera": carrera})

    return render(request, "malla/subir.html", {"carrera": carrera})


@login_required
@org_required
def ver_analisis(request, pk):
    """Muestra el dashboard HTML embebido en un iframe o inline."""
    org      = request.user.organization
    analisis = get_object_or_404(
        AnalisisMalla,
        pk=pk,
        carrera__organization=org,
        estado=AnalisisMalla.Estado.LISTO,
    )
    return render(request, "malla/ver_analisis.html", {"analisis": analisis})


@login_required
@org_required
def descargar_html(request, pk):
    """Descarga el HTML del análisis."""
    org      = request.user.organization
    analisis = get_object_or_404(
        AnalisisMalla, pk=pk,
        carrera__organization=org,
        estado=AnalisisMalla.Estado.LISTO,
    )
    filename = (f"dashboard_{analisis.carrera.codigo}_"
                f"{analisis.periodo}.html")
    response = HttpResponse(analisis.html_resultado,
                            content_type="text/html; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@org_required
def api_stats(request, pk):
    """Endpoint JSON con estadísticas del análisis (para integración)."""
    org      = request.user.organization
    analisis = get_object_or_404(
        AnalisisMalla, pk=pk, carrera__organization=org
    )
    return JsonResponse({
        "id":             analisis.pk,
        "carrera":        analisis.carrera.nombre,
        "periodo":        analisis.periodo,
        "estado":         analisis.estado,
        "n_asignaturas":  analisis.n_asignaturas,
        "n_con_datos":    analisis.n_con_datos,
        "n_criticas":     analisis.n_criticas,
        "pct_promedio":   analisis.pct_promedio,
        "creado_en":      analisis.creado_en.isoformat(),
    })


# ── Helper ─────────────────────────────────────────────────────────
def _actualizar_asignaturas(carrera, df):
    """Sincroniza las asignaturas de la BD con los datos del Excel."""
    Asignatura.objects.filter(carrera=carrera).delete()
    Asignatura.objects.bulk_create([
        Asignatura(
            carrera        = carrera,
            codigo         = r.codigo,
            nombre         = r.nombre,
            semestre       = r.semestre,
            fila           = r.fila,
            area           = r.area,
            creditos       = r.creditos,
            prerrequisitos = r.prerrequisitos,
        )
        for r in df.itertuples()
    ])
