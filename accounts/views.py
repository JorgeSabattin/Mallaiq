"""accounts/views.py"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User, Organization


def login_view(request):
    if request.user.is_authenticated:
        return redirect("malla:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            if user.organization and not user.organization.activa:
                messages.error(request, "Tu institución no tiene acceso activo.")
            else:
                login(request, user)
                return redirect(request.GET.get("next", "malla:dashboard"))
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {"user": request.user})
