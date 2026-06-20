"""Widoki HTML dla obszaru Turysty (Faza C - Frontend)."""

from collections import defaultdict
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from application.dto.verify_badge_dto import VerifyBadgeRequestDTO
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
from bootstrap import get_container


def _get_active_profile_id(request) -> int:
    """Helper: Pobiera ID aktywnego profilu (Konto Rodzinne) z sesji."""
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
    """Główny ekran aplikacji turysty (Pulpit z mapą i odznakami)."""
    profile_id = _get_active_profile_id(request)

    active_progresses = (
        UserBadgeProgress.objects.filter(profile_id=profile_id)
        .select_related("badge", "version")
        .order_by("-updated_at")
    )

    return render(request, "tourists/dashboard.html", {"active_progresses": active_progresses})


@login_required
def badge_catalog_view(request):
    """Katalog wszystkich dostępnych odznak z opcją subskrypcji i podglądem szczytów."""
    from django.utils import timezone

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

    # 4. Sprawdzanie subskrypcji
    subscribed_ids = UserBadgeProgress.objects.filter(profile_id=profile_id).values_list("badge_id", flat=True)

    return render(
        request,
        "tourists/catalog.html",
        {
            "badges": badges,
            "subscribed_ids": subscribed_ids,
        },
    )


@login_required
def switch_profile_view(request, profile_id: int):
    """Zmienia aktywny profil w sesji (Przełącznik Rodzinny)."""
    profile = get_object_or_404(TouristProfile, id=profile_id, user=request.user)

    request.session["active_profile_id"] = profile.id
    messages.success(request, f"Przełączono na profil: {profile.nickname}")
    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def profile_settings_view(request):
    """Formularz zarządzania profilami (Konta Rodzinne)."""
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
            if birth_date:
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
    """Szczegóły konkretnego obiektu, klastry i historia wejść."""
    profile_id = _get_active_profile_id(request)
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
        },
    )


@login_required
def badge_detail_view(request, badge_code: str):
    """Szczegóły odznaki: mapa, regulamin, postęp, logistyka i wykaz obiektów."""
    profile_id = _get_active_profile_id(request)
    badge = get_object_or_404(BadgeModel.objects.select_related("organizer"), code=badge_code)

    progress = UserBadgeProgress.objects.filter(profile_id=profile_id, badge=badge).order_by("-cycle_number").first()

    evaluation = None
    target_version = None

    if progress and progress.version_id:
        target_version = progress.version
        try:
            use_case = get_container()["verify_badge"]
            dto = VerifyBadgeRequestDTO(
                profile_id=profile_id, badge_code=badge_code, cycle_number=progress.cycle_number
            )
            evaluation = use_case.execute(dto)
        except Exception:
            evaluation = None
    else:
        target_version = (
            BadgeVersionModel.objects.filter(badge=badge, valid_from__lte=timezone.now().date())
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
    """Szczegóły regionu geograficznego z rankingiem obiektów i mapą."""
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
    """Widok tabelaryczny pokazujący opłacalne szczyty, pogrupowane w Klastry (Rodziny)."""
    profile_id = _get_active_profile_id(request)
    cache_key = f"map_state:{profile_id}"
    cached_data = cache.get(cache_key) or {}

    scores = cached_data.get("scores", {})
    colors = cached_data.get("colors", {})

    def get_score(pid):
        s = scores.get(pid, scores.get(str(pid), 0))
        try:
            return int(s)
        except ValueError, TypeError:
            return 0

    def get_color(pid):
        return colors.get(pid, colors.get(str(pid), "GRAY"))

    valid_peak_ids = [int(pid) for pid in scores.keys() if get_score(pid) > 0 and get_color(pid) != "GRAY"]

    from django.db.models import Q

    peaks = (
        TouristObject.objects.filter(Q(id__in=valid_peak_ids) | Q(child_objects__id__in=valid_peak_ids))
        .select_related("parent_object")
        .prefetch_related("badgeversionmodel_set__badge")
        .distinct()
    )

    clusters = defaultdict(list)

    for peak in peaks:
        anchor_id = peak.parent_object_id if peak.parent_object_id else peak.id
        clusters[anchor_id].append(peak)

    ranking_data = []

    for anchor_id, family_members in clusters.items():
        cluster_score = sum(get_score(p.id) for p in family_members)

        if cluster_score == 0:
            continue

        parent_node = next((p for p in family_members if p.id == anchor_id), None)
        children_nodes = sorted([p for p in family_members if p.id != anchor_id], key=lambda x: x.name)

        cluster_items = []

        if parent_node:
            cluster_items.append(
                {
                    "id": parent_node.id,
                    "name": parent_node.name,
                    "type": parent_node.type,
                    "score": get_score(parent_node.id),
                    "color": get_color(parent_node.id),
                    "badges": [
                        {"code": c, "name": n}
                        for c, n in {
                            bv.badge.code: bv.badge.name for bv in parent_node.badgeversionmodel_set.all()
                        }.items()
                    ],
                    "is_child": False,
                }
            )

        for child in children_nodes:
            c_score = get_score(child.id)
            if c_score > 0:
                cluster_items.append(
                    {
                        "id": child.id,
                        "name": child.name,
                        "type": child.type,
                        "score": c_score,
                        "color": get_color(child.id),
                        "badges": [
                            {"code": c, "name": n}
                            for c, n in {
                                bv.badge.code: bv.badge.name for bv in child.badgeversionmodel_set.all()
                            }.items()
                        ],
                        "is_child": True,
                    }
                )

        if not cluster_items:
            continue

        cluster_name = parent_node.name if parent_node else cluster_items[0]["name"]
        is_family = bool(len(cluster_items) > 1 or (parent_node and children_nodes))

        ranking_data.append(
            {
                "cluster_id": anchor_id,
                "cluster_name": cluster_name,
                "cluster_score": cluster_score,
                "is_family": is_family,
                "items": cluster_items,
            }
        )

    ranking_data.sort(key=lambda x: x["cluster_score"], reverse=True)

    return render(request, "tourists/ranking.html", {"ranking": ranking_data})


@login_required
def region_ranking_view(request):
    """Widok tabelaryczny pokazujący skumulowany ranking dla całych regionów."""
    profile_id = _get_active_profile_id(request)

    LEVELS = {
        "MESOREGION": "Mezoregiony",
        "TOURIST_REGION": "Regiony Turystyczne (PTTK)",
        "MACROREGION": "Makroregiony",
        "SUBPROVINCE": "Podprowincje",
        "PROVINCE": "Prowincje",
        "VOIVODESHIP": "Województwa",
    }

    active_level = request.GET.get("level", "MESOREGION").upper()
    if active_level not in LEVELS:
        active_level = "MESOREGION"

    cache_key = f"map_state:{profile_id}"
    cached_data = cache.get(cache_key) or {}

    scores = cached_data.get("scores", {})
    colors = cached_data.get("colors", {})

    valid_peak_ids = []
    for pid_str, score in scores.items():
        if score > 0 and colors.get(pid_str) != "GRAY":
            valid_peak_ids.append(int(pid_str))

    regions_agg = defaultdict(lambda: {"score": 0, "peak_count": 0})

    if valid_peak_ids:
        region_caches = ObjectRegionCache.objects.filter(
            tourist_object_id__in=valid_peak_ids, region_level=active_level
        )

        for rc in region_caches:
            peak_score = scores.get(rc.tourist_object_id, scores.get(str(rc.tourist_object_id), 0))
            if peak_score > 0:
                key = (rc.region_level, rc.region_id, rc.region_name)
                regions_agg[key]["score"] += peak_score
                regions_agg[key]["peak_count"] += 1

    ranking_data = []
    for (level, rid, name), data in regions_agg.items():
        ranking_data.append(
            {"level": level, "id": rid, "name": name, "total_score": data["score"], "peak_count": data["peak_count"]}
        )

    ranking_data.sort(key=lambda x: x["total_score"], reverse=True)

    return render(
        request,
        "tourists/region_ranking.html",
        {
            "ranking": ranking_data,
            "levels": LEVELS,
            "active_level": active_level,
        },
    )


@login_required
def organizer_detail_view(request, organizer_id: int):
    """Szczegóły organizatora i wylistowanie wszystkich jego odznak."""
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
    """Centralna tablica Kanban dla wysyłek i weryfikacji fizycznych."""
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
