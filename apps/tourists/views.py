"""Widoki HTML dla obszaru Turysty (Faza C - Frontend)."""

import logging
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from apps.badges.models import (
    BadgeModel,
    BadgeTierModel,
    BadgeVersionModel,
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ObjectRegionCache,
    OrganizerModel,
    ProvinceModel,
    SubprovinceModel,
    TouristObject,
    TouristRegionModel,
    VoivodeshipModel,
)
from apps.tourists.models import (
    AscentLog,
    DomainStatus,
    TouristProfile,
    UserBadgeProgress,
)

logger = logging.getLogger(__name__)


def _get_active_profile_id(request) -> int:
    """Helper: Pobiera ID aktywnego profilu (Konto Rodzinne) z sesji.

    Args:
      request:

    Returns:
    """
    active_id = request.session.get("active_profile_id")
    if active_id:
        return int(active_id)

    # Fallback na wypadek nowej sesji
    profile = request.user.profiles.first()

    if not profile:
        # MAGIA NAPRAWCZA: Leniwa inicjalizacja dla starych kont (np. superusera),
        # które powstały przed dodaniem sygnału automatycznego tworzenia profili.
        from apps.tourists.models import TouristProfile

        nickname = request.user.email.split("@")[0] if request.user.email else f"admin_{request.user.id}"
        profile = TouristProfile.objects.create(
            user=request.user,
            nickname=nickname,
            is_main_profile=True,
            active_plan="FREE",
            max_photos_per_ascent=1,
            max_active_badges=3,
        )

    request.session["active_profile_id"] = profile.id
    return int(profile.id)


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

    # 1. Pobieramy wszystkie odznaki
    badges = list(BadgeModel.objects.select_related("organizer").all().order_by("name"))

    # 2. Pobieramy najnowsze (obowiązujące) wersje regulaminów i ich szczyty w jednym zapytaniu
    current_versions_qs = (
        BadgeVersionModel.objects.filter(valid_from__lte=timezone.now().date())
        .prefetch_related("pool_peaks")
        .order_by("-valid_from")
    )

    # 3. Złoty środek: Zamiast męczyć ORM z `related_name`, mapujemy to w szybkim słowniku Pythona
    version_map = {}
    for version in current_versions_qs:
        # Ponieważ posortowaliśmy malejąco po dacie, pierwsza wersja jaka wpadnie do słownika jest najnowszą
        if version.badge_id not in version_map:
            version_map[version.badge_id] = version

    # Wstrzykujemy wersję bezpośrenio do obiektu odznaki (jako tymczasowy atrybut dla HTML)
    for badge in badges:
        badge.current_version = version_map.get(badge.id)

    # 4. Sprawdzanie subskrypcji z podziałem na statusy
    progresses = UserBadgeProgress.objects.filter(profile_id=profile_id)

    active_ids = [p.badge_id for p in progresses if p.domain_status != "COMPLETED"]
    completed_ids = [p.badge_id for p in progresses if p.domain_status == "COMPLETED"]

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

    # NOWE: Pobieramy kody odznak subskrybowanych przez ten profil
    subscribed_badge_codes = list(
        UserBadgeProgress.objects.filter(profile_id=profile_id).values_list("badge__code", flat=True)
    )

    obj = get_object_or_404(TouristObject, id=object_id)

    regions = ObjectRegionCache.objects.filter(tourist_object=obj).order_by("region_level")

    unique_badges = {bv.badge.code: bv.badge.name for bv in obj.badgeversionmodel_set.select_related("badge").all()}
    badges_list = [{"code": code, "name": name} for code, name in unique_badges.items()]
    badges_list.sort(key=lambda x: x["name"])

    cache_key = f"map_state:{profile_id}"
    cached_data = cache.get(cache_key) or {}
    scores = cached_data.get("scores", {})
    colors = cached_data.get("colors", {})

    score = scores.get(obj.id, scores.get(str(obj.id), 0))
    color = colors.get(obj.id, colors.get(str(obj.id), "GRAY"))

    ascents = AscentLog.objects.filter(profile_id=profile_id, peak=obj).order_by("-ascent_date")

    parent = obj.parent_object
    children = obj.child_objects.all() if hasattr(obj, "child_objects") else []

    return render(
        request,
        "tourists/object_detail.html",
        {
            "obj": obj,
            "regions": regions,
            "badges": badges_list,
            "score": score,
            "color": color,
            "ascents": ascents,
            "parent": parent,
            "children": children,
            "subscribed_badge_codes": subscribed_badge_codes,
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
    badge = get_object_or_404(BadgeModel.objects.select_related("organizer"), code=badge_code)

    progress = (
        UserBadgeProgress.objects.filter(profile_id=profile_id, badge=badge)
        .select_related("version")
        .prefetch_related("version__pool_peaks")
        .order_by("-cycle_number")
        .first()
    )

    evaluation = None
    target_version = None

    if progress and progress.version_id:
        target_version = progress.version
        try:
            query_service = request.app_container.evaluate_badge_progress
            # Zmienna w szablonie nazywa się 'evaluation'
            evaluation = query_service.execute(profile_id=profile_id, badge_code=badge.code)
        except Exception:
            evaluation = None
    else:
        today = timezone.now().date()
        target_version = (
            BadgeVersionModel.objects.filter(
                badge=badge,
                valid_from__lte=today,
            )
            .prefetch_related("pool_peaks")
            .order_by("-valid_from")
            .first()
        )

    has_consent = badge.organizer.has_publication_consent
    tiers_info = []

    if target_version:
        all_db_tiers = BadgeTierModel.objects.filter(version=target_version).order_by("order")
        db_tiers = {t.name: t for t in all_db_tiers}

        if evaluation and "tiers" in evaluation:
            for eval_tier in evaluation["tiers"]:
                db_tier = db_tiers.get(eval_tier["name"])
                img_url = (
                    db_tier.badge_image.url
                    if (db_tier and getattr(db_tier, "badge_image", None) and has_consent)
                    else None
                )

                tiers_info.append(
                    {
                        "name": eval_tier["name"],
                        "required_count": eval_tier["required_count"],
                        "status": eval_tier["status"],
                        "image_url": img_url,
                    }
                )
        else:
            for db_tier in all_db_tiers:
                img_url = db_tier.badge_image.url if (getattr(db_tier, "badge_image", None) and has_consent) else None
                req_count = (
                    db_tier.required_peaks_count
                    if db_tier.required_peaks_count is not None
                    else len(target_version.pool_peaks.all())
                )
                tiers_info.append(
                    {
                        "name": db_tier.name,
                        "required_count": req_count,
                        "status": "NOT_STARTED",
                        "image_url": img_url,
                    }
                )

    objects_list = []
    if target_version:
        cache_key = f"map_state:{profile_id}"
        cached_data = cache.get(cache_key) or {}
        scores = cached_data.get("scores", {})
        colors = cached_data.get("colors", {})

        for peak in target_version.pool_peaks.all().order_by("name"):
            score = scores.get(peak.id, scores.get(str(peak.id), 0))
            color = colors.get(peak.id, colors.get(str(peak.id), "GRAY"))
            objects_list.append(
                {"id": peak.id, "name": peak.name, "altitude": peak.altitude, "score": score, "color": color}
            )

    return render(
        request,
        "tourists/badge_detail.html",
        {
            "badge": badge,
            "progress": progress,
            "evaluation": evaluation,
            "objects_list": objects_list,
            "target_version": target_version,
            "tiers_info": tiers_info,
            "has_consent": has_consent,
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

    # Mapowanie typu regionu na konkretny model Django
    MODELS_MAP = {
        "country": CountryModel,
        "voivodeship": VoivodeshipModel,
        "province": ProvinceModel,
        "subprovince": SubprovinceModel,
        "macroregion": MacroregionModel,
        "mesoregion": MesoregionModel,
        "tourist_region": TouristRegionModel,
    }

    ModelClass = MODELS_MAP.get(region_level.lower())
    if not ModelClass:
        raise Http404("Nieznany typ regionu geograficznego.")

    region = get_object_or_404(ModelClass, id=region_id)

    # Pobranie Extent (Bounding Boxa) geometrii regionu, by mapa wiedziała gdzie się przybliżyć!
    extent = region.shape.extent if hasattr(region, "shape") and region.shape else None

    # 1. Pobieramy ranking 100/n z Redis
    cache_key = f"map_state:{profile_id}"
    cached_data = cache.get(cache_key) or {}
    scores = cached_data.get("scores", {})
    colors = cached_data.get("colors", {})

    # 2. Pobieramy obiekty w tym regionie za pomocą CQRS
    obj_ids = ObjectRegionCache.objects.filter(region_level=region_level, region_id=region_id).values_list(
        "tourist_object_id", flat=True
    )

    peaks = TouristObject.objects.filter(id__in=obj_ids, is_active=True, status="READY")

    # 3. Zestawiamy obiekty z ich rankingiem
    ranking_data = []
    for peak in peaks:
        score = scores.get(peak.id, scores.get(str(peak.id), 0))
        color = colors.get(peak.id, colors.get(str(peak.id), "GRAY"))

        ranking_data.append(
            {
                "id": peak.id,
                "name": peak.name,
                "type": peak.type,
                "score": score,
                "color": color,
            }
        )

    # Sortujemy od najbardziej zyskownych
    ranking_data.sort(key=lambda x: x["score"], reverse=True)

    # =================================================================
    # NAWIGACJA TERYTORIALNA (Drzewo i Sąsiedzi)
    # =================================================================
    parent_region = None
    parent_level = None
    children_regions: list[Any] = []
    children_level = None

    lvl = region_level.upper()

    # Hierarchia pionowa (Góra / Dół) - oparta o relacje ORM
    if lvl == "MESOREGION":
        parent_region = getattr(region, "macroregion", None)
        parent_level = "MACROREGION"
    elif lvl == "MACROREGION":
        parent_region = getattr(region, "subprovince", None)
        parent_level = "SUBPROVINCE"
        children_regions = list(region.mesoregionmodel_set.all()) if hasattr(region, "mesoregionmodel_set") else []
        children_level = "MESOREGION"
    elif lvl == "SUBPROVINCE":
        parent_region = getattr(region, "province", None)
        parent_level = "PROVINCE"
        children_regions = list(region.macroregionmodel_set.all()) if hasattr(region, "macroregionmodel_set") else []
        children_level = "MACROREGION"
    elif lvl == "PROVINCE":
        children_regions = list(region.subprovincemodel_set.all()) if hasattr(region, "subprovincemodel_set") else []
        children_level = "SUBPROVINCE"
    elif lvl == "TOURIST_REGION":
        children_regions = list(region.mesoregions.all()) if hasattr(region, "mesoregions") else []
        children_level = "MESOREGION"

    # 2. Relacje poziome (Sąsiedzi) - Błyskawiczny odczyt pre-kalkulowanej relacji M2M
    neighbors: list[Any] = []
    if hasattr(region, "neighbors"):
        # Brak obciążenia procesora – zwykły odczyt JOIN z bazy
        neighbors = list(region.neighbors.all().order_by("name"))

    return render(
        request,
        "tourists/region_detail.html",
        {
            "region": region,
            "region_level": region_level,
            "region_id": region_id,
            "extent": extent,
            "top_objects": ranking_data[:20],
            "total_objects": len(ranking_data),
            "parent_region": parent_region,
            "parent_level": parent_level,
            "children_regions": children_regions,
            "children_level": children_level,
            "neighbors": neighbors,
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
    organizer = get_object_or_404(OrganizerModel, id=organizer_id)

    badges = organizer.badges.all().order_by("name")
    subscribed_ids = UserBadgeProgress.objects.filter(profile_id=profile_id).values_list("badge_id", flat=True)

    return render(
        request,
        "tourists/organizer_detail.html",
        {
            "organizer": organizer,
            "badges": badges,
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
