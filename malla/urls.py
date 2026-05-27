"""malla/urls.py"""
from django.urls import path
from . import views

app_name = "malla"

urlpatterns = [
    path("",                              views.dashboard,       name="dashboard"),
    path("carrera/<int:pk>/",             views.carrera_detail,  name="carrera_detail"),
    path("carrera/<int:carrera_pk>/subir/",views.subir_excel,    name="subir_excel"),
    path("analisis/<int:pk>/",            views.ver_analisis,    name="ver_analisis"),
    path("analisis/<int:pk>/descargar/",  views.descargar_html,  name="descargar_html"),
    path("analisis/<int:pk>/api/",        views.api_stats,       name="api_stats"),
]
