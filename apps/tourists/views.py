"""Widoki HTML dla obszaru Turysty (Faza C - Frontend)."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.tourists.models import UserBadgeProgress


@login_required
def dashboard_view(request):
    """Główny ekran aplikacji turysty (Pulpit z mapą i odznakami)."""

    # Zgodnie z CQRS, widoki tylko do odczytu (HTML) mogą bezpiecznie
    # pytać bazę danych z pominięciem Use Case'ów (które służą do akcji).
    active_progresses = (
        UserBadgeProgress.objects.filter(user=request.user).select_related("badge", "version").order_by("-updated_at")
    )

    return render(request, "tourists/dashboard.html", {"active_progresses": active_progresses})
