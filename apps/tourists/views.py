"""Widoki HTML dla obszaru Turysty (Faza C - Frontend)."""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.tourists.models import (
    DomainStatus,
    TouristProfile,
    UserBadgeProgress,
)

logger = logging.getLogger(__name__)


def _get_queries(request):
    """Pobiera ExploreQueriesService z kontenera DI (AUDYT-016)."""
    return request.app_container.explore_queries_service


def _get_active_profile_id(request) -> int:
    """Helper: Pobiera ID aktywnego profilu (Konto Rodzinne) z sesji.

    Strona profilu jest zapewniona przez ``EnsureTouristProfileMiddleware``,
    który uruchamia się raz na żądanie. Ta funkcja jest czystym getterem —
    nie wykonuje żadnych operacji zapisu (Zero Side Effects).

    Args:
      request:

    Returns:
      ID profilu turysty jako int.
    """
    active_id = request.session.get("active_profile_id")
    return int(active_id)


@login_required
def dashboard_view(request):
    """Główny ekran aplikacji turysty (Pulpit z mapą i odznakami).

    Args:
      request:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    active_progresses = (
        UserBadgeProgress.objects.filter(profile_id=profile_id)
        .select_related("badge", "version")
        .order_by("-updated_at")
    )

    return render(request, "tourists/dashboard.html", {"active_progresses": active_progresses})


@login_required
def badge_catalog_view(request):
    """Katalog wszystkich dostępnych odznak z opcją subskrypcji i podglądem szczytów.

    Args:
      request:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    entries = _get_queries(request).get_catalog_badges(profile_id)

    badges = [e.badge for e in entries]
    active_ids = [e.id for e in entries if e.domain_status != "COMPLETED"]
    completed_ids = [e.id for e in entries if e.domain_status == "COMPLETED"]

    return render(
        request,
        "tourists/catalog.html",
        {
            "badges": badges,
            "active_ids": active_ids,
            "completed_ids": completed_ids,
        },
    )


@login_required
def switch_profile_view(request, profile_id: int):
    """Zmienia aktywny profil w sesji (Przełącznik Rodzinny).

    Args:
      request:
      profile_id: int:
      profile_id: int:

    Returns:
    """
    profile = get_object_or_404(TouristProfile, id=profile_id, user=request.user)

    request.session["active_profile_id"] = profile.id
    messages.success(request, f"Przełączono na profil: {profile.nickname}")
    # === ZABEZPIECZENIE (CWE-601: Open Redirect) ===
    next_url = request.META.get("HTTP_REFERER", "/")

    is_safe = url_has_allowed_host_and_scheme(
        url=next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )

    if not is_safe:
        next_url = "home"

    return redirect(next_url)


@login_required
def profile_settings_view(request):
    """Formularz zarządzania profilami (Konta Rodzinne).

    Args:
      request:

    Returns:
    """
    profiles = list(TouristProfile.objects.filter(user=request.user))
    main_profile = next((p for p in profiles if p.is_main_profile), None)

    active_id = request.session.get("active_profile_id")
    active_profile = next((p for p in profiles if p.id == active_id), None) or main_profile

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update":
            nickname = request.POST.get("nickname")
            birth_date = request.POST.get("birth_date")

            if nickname:
                active_profile.nickname = nickname

            # SECURITY (AUDYT-048): birth_date jest niezmienny po ustawieniu.
            # Chroni to przed Age Fraud — manipulacją wiekiem w celu zdobycia odznak.
            if birth_date == "":
                if active_profile.birth_date is not None:
                    raise PermissionDenied("Data urodzenia nie może być usunięta po ustawieniu.")
                active_profile.birth_date = None
            elif birth_date:
                if active_profile.birth_date is not None:
                    logger.warning(
                        "Attempt to modify birth_date for profile %s by user %s",
                        active_profile.id,
                        request.user.id,
                        extra={"request_id": getattr(request, "request_id", "unknown")},
                    )
                    raise PermissionDenied("Data urodzenia nie może być zmieniona po ustawieniu.")
                active_profile.birth_date = birth_date

            active_profile.save(update_fields=["nickname", "birth_date"])
            messages.success(request, f"Zaktualizowano profil: {active_profile.nickname}")

        elif action == "add_profile":
            new_nickname = request.POST.get("new_nickname")
            if len(profiles) >= 5:
                messages.error(request, "Osiągnięto maksymalny limit profili na tym koncie (5).")
            elif new_nickname:
                new_p = TouristProfile.objects.create(
                    user=request.user,
                    nickname=new_nickname,
                    is_main_profile=False,
                    active_plan=main_profile.active_plan if main_profile else "FREE",
                    max_photos_per_ascent=main_profile.max_photos_per_ascent if main_profile else 1,
                    max_active_badges=main_profile.max_active_badges if main_profile else 3,
                )
                request.session["active_profile_id"] = new_p.id
                messages.success(request, f"Utworzono i przełączono na nowy profil: {new_nickname}")

        return redirect("profile")

    return render(
        request,
        "tourists/profile.html",
        {
            "profile": active_profile,
            "profiles_count": len(profiles),
            "max_profiles": 5,
        },
    )


@login_required
def object_detail_view(request, object_id: int):
    """Szczegóły konkretnego obiektu, klastry i historia wejść.

    Args:
      request:
      object_id: int:
      object_id: int:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    query = _get_queries(request)
    dto = query.get_object_details(object_id, profile_id)

    return render(
        request,
        "tourists/object_detail.html",
        {
            "obj": dto.obj,
            "regions": dto.regions,
            "badges": dto.badges_list,
            "score": dto.score,
            "color": dto.color,
            "ascents": dto.ascents,
            "parent": dto.parent,
            "children": dto.children,
            "subscribed_badge_codes": dto.subscribed_badge_codes,
        },
    )


@login_required
def badge_detail_view(request, badge_code: str):
    """Szczegóły odznaki: mapa, regulamin, postęp, logistyka i wykaz obiektów.

    Args:
      request:
      badge_code: str:
      badge_code: str:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    # EvaluateBadgeProgressQuery (US-C06) — evaluation on-demand;
    # failure degrades gracefully (no evaluation shown)
    evaluation: dict[str, object] | None = None
    try:
        query_service = request.app_container.evaluate_badge_progress
        evaluation = query_service.execute(profile_id=profile_id, badge_code=badge_code)
    except Exception:
        evaluation = None

    dto = _get_queries(request).get_badge_details(badge_code=badge_code, profile_id=profile_id, evaluation=evaluation)

    return render(
        request,
        "tourists/badge_detail.html",
        {
            "badge": dto.badge,
            "progress": dto.progress,
            "evaluation": dto.evaluation,
            "objects_list": [
                {"id": o.id, "name": o.name, "altitude": o.altitude, "score": o.score, "color": o.color}
                for o in dto.objects_list
            ],
            "target_version": dto.target_version,
            "tiers_info": [
                {"name": t.name, "required_count": t.required_count, "status": t.status, "image_url": t.image_url}
                for t in dto.tiers_info
            ],
            "has_consent": dto.has_consent,
        },
    )


@login_required
def region_detail_view(request, region_level: str, region_id: int):
    """Szczegóły regionu geograficznego z rankingiem obiektów i mapą.

    Args:
      request:
      region_level: str:
      region_id: int:
      region_level: str:
      region_id: int:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    ctx = _get_queries(request).get_region_context(region_level, region_id, profile_id)

    return render(
        request,
        "tourists/region_detail.html",
        {
            "region": ctx.region,
            "region_level": ctx.region_level,
            "region_id": ctx.region_id,
            "extent": ctx.extent,
            "top_objects": ctx.ranking_data,
            "total_objects": ctx.total_objects,
            "parent_region": ctx.parent_region,
            "parent_level": ctx.parent_level,
            "children_regions": ctx.children_regions,
            "children_level": ctx.children_level,
            "neighbors": ctx.neighbors,
        },
    )


@login_required
def poi_ranking_view(request):
    """Widok: Ranking Poszczególnych Celów (Szczytów i Klastrów).

    Args:
      request:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    # 1. Odpytujemy Czysty Serwis Odczytu
    queries_service = request.app_container.explore_queries_service
    dto_response = queries_service.get_poi_ranking(profile_id=profile_id)

    context = {
        "active_progresses": dto_response.active_progresses,
        "subscribed_badge_codes": dto_response.subscribed_badge_codes,
        "ranking_data": dto_response.ranking,
    }
    return render(request, "tourists/ranking.html", context)


@login_required
def region_ranking_view(request):
    """Widok: Skumulowany ranking dla całych regionów z podziałem na poziomy.

    Args:
      request:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    # Bezpieczne pobieranie poziomu z URL, z domyślnym przejściem na MEZOREGION
    level = request.GET.get("level", "MESOREGION").upper()
    if level not in ["VOIVODESHIP", "MACROREGION", "MESOREGION"]:
        level = "MESOREGION"

    # 1. Odpytujemy Czysty Serwis Odczytu
    queries_service = request.app_container.explore_queries_service
    dto_response = queries_service.get_region_ranking(profile_id=profile_id, level=level)

    context = {
        "ranking_data": dto_response.ranking,
        "current_level": level,
    }
    return render(request, "tourists/region_ranking.html", context)


@login_required
def organizer_detail_view(request, organizer_id: int):
    """Szczegóły organizatora i wylistowanie wszystkich jego odznak.

    Args:
      request:
      organizer_id: int:
      organizer_id: int:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    query = _get_queries(request)
    organizer_dto = query.get_organizer_detail(organizer_id)
    organizer = organizer_dto.organizer
    subscribed_ids = query.get_subscribed_badge_ids(profile_id)

    return render(
        request,
        "tourists/organizer_detail.html",
        {
            "organizer": organizer,
            "badges": organizer.badges.all().order_by("name"),
            "subscribed_ids": subscribed_ids,
        },
    )


@login_required
def logistics_view(request):
    """Centralna tablica Kanban dla wysyłek i weryfikacji fizycznych.

    Args:
      request:

    Returns:
    """
    profile_id = _get_active_profile_id(request)

    completed_progresses = (
        UserBadgeProgress.objects.filter(profile_id=profile_id, domain_status=DomainStatus.COMPLETED)
        .select_related("badge")
        .order_by("-updated_at")
    )

    kanban = {
        "WAITING_FOR_SEND": [],
        "WAITING_FOR_VERIFICATION": [],
        "WAITING_FOR_RECEIVING": [],
        "ALBUM": [],
    }

    for prog in completed_progresses:
        status = prog.logistic_status if prog.logistic_status else "WAITING_FOR_SEND"
        if status in kanban:
            kanban[status].append(prog)

    warning_date = timezone.now().date() - timezone.timedelta(days=30)

    return render(
        request,
        "tourists/logistics.html",
        {
            "kanban": kanban,
            "total_completed": completed_progresses.count(),
            "warning_date": warning_date,
        },
    )
