"""Widoki HTML dla obszaru Turysty (Faza C - Frontend)."""

from collections import defaultdict
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

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
from apps.tourists.models import AscentLog, UserBadgeProgress
from bootstrap import get_container


@login_required
def dashboard_view(request):
    """Główny ekran aplikacji turysty (Pulpit z mapą i odznakami)."""
    active_progresses = (
        UserBadgeProgress.objects.filter(user=request.user).select_related("badge", "version").order_by("-updated_at")
    )

    return render(request, "tourists/dashboard.html", {"active_progresses": active_progresses})


@login_required
def badge_catalog_view(request):
    """Katalog wszystkich dostępnych odznak z opcją subskrypcji."""
    # Pobieramy wszystkie odznaki z bazy
    badges = BadgeModel.objects.select_related("organizer").all().order_by("name")

    # Sprawdzamy, które odznaki turysta już subskrybuje, by wyszarzyć przycisk
    subscribed_ids = UserBadgeProgress.objects.filter(user=request.user).values_list("badge_id", flat=True)

    return render(
        request,
        "tourists/catalog.html",
        {
            "badges": badges,
            "subscribed_ids": subscribed_ids,
        },
    )


@login_required
def profile_settings_view(request):
    """Prosty formularz zarządzania profilem (w tym datą urodzenia)."""
    from apps.tourists.models import TouristProfile

    # Leniwa inicjalizacja: ratuje stare konta (np. superusera), które powstały
    # przed dodaniem mechanizmu automatycznego tworzenia profili z OAuth.
    profile, created = TouristProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "nickname": request.user.email.split("@")[0] if request.user.email else f"admin_{request.user.id}",
            "active_plan": "FREE",
            "max_photos_per_ascent": 1,
            "max_active_badges": 3,
        },
    )

    if request.method == "POST":
        nickname = request.POST.get("nickname")
        birth_date = request.POST.get("birth_date")

        if nickname:
            profile.nickname = nickname
        if birth_date:
            profile.birth_date = birth_date

        profile.save(update_fields=["nickname", "birth_date"])
        messages.success(request, "Twój profil został zaktualizowany!")
        return redirect("profile")

    return render(request, "tourists/profile.html", {"profile": profile})


@login_required
def object_detail_view(request, object_id: int):
    """Szczegóły konkretnego obiektu, klastry i historia wejść."""
    obj = get_object_or_404(TouristObject, id=object_id)

    # 1. Pobieramy geografię CQRS
    regions = ObjectRegionCache.objects.filter(tourist_object=obj).order_by("region_level")

    # 2. Pobieramy unikalne odznaki, w których występuje (Zarówno nazwa, jak i kod do linku)
    unique_badges = {bv.badge.code: bv.badge.name for bv in obj.badgeversionmodel_set.select_related("badge").all()}

    # Tworzymy listę słowników i sortujemy alfabetycznie po nazwie
    badges_list = [{"code": code, "name": name} for code, name in unique_badges.items()]
    badges_list.sort(key=lambda x: x["name"])

    # 3. Pobieramy punktację 100/n z Redis
    cache_key = f"map_state:{request.user.id}"
    cached_data = cache.get(cache_key) or {}
    scores = cached_data.get("scores", {})
    colors = cached_data.get("colors", {})

    score = scores.get(obj.id, scores.get(str(obj.id), 0))
    color = colors.get(obj.id, colors.get(str(obj.id), "GRAY"))

    # 4. Sprawdzamy historię logów wejść turysty
    ascents = AscentLog.objects.filter(user=request.user, peak=obj).order_by("-ascent_date")

    # 5. Klastry (Rodzic / Dzieci)
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
    from django.core.cache import cache
    from django.utils import timezone

    badge = get_object_or_404(BadgeModel.objects.select_related("organizer"), code=badge_code)

    # Szukamy aktywnego cyklu dla tego użytkownika
    progress = UserBadgeProgress.objects.filter(user=request.user, badge=badge).order_by("-cycle_number").first()

    evaluation = None
    target_version = None

    if progress and progress.version_id:
        target_version = progress.version
        try:
            use_case = get_container()["verify_badge"]
            dto = VerifyBadgeRequestDTO(
                user_id=request.user.id, badge_code=badge_code, cycle_number=progress.cycle_number
            )
            evaluation = use_case.execute(dto)
        except Exception:
            evaluation = None
    else:
        # Prawa Nabyte: Jeśli brak logów, bierzemy najnowszą wersję
        target_version = (
            BadgeVersionModel.objects.filter(badge=badge, valid_from__lte=timezone.now().date())
            .order_by("-valid_from")
            .first()
        )

    # ==========================================================
    # ZŁOŻENIE DANYCH WIZUALNYCH I PRAW AUTORSKICH (D-03)
    # ==========================================================
    has_consent = badge.organizer.has_publication_consent
    tiers_info = []

    if target_version:
        # POBIERAMY STOPNIE BEZPOŚREDNIO Z MODELU (Odporne na nazwy related_name)
        all_db_tiers = BadgeTierModel.objects.filter(version=target_version).order_by("order")
        db_tiers = {t.name: t for t in all_db_tiers}

        # Jeśli mamy wyliczoną ewaluację z Domeny, łączymy to z bazą
        if evaluation and "tiers" in evaluation:
            for eval_tier in evaluation["tiers"]:
                db_tier = db_tiers.get(eval_tier["name"])
                # Invariant D-03: Blokada wizerunku bez zgody!
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
            # Jeśli turysta jeszcze nie zaczął, pokazujemy mu po prostu puste stopnie z obrazkami
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

    # Pobieranie listy obiektów i kolorów z Redis
    objects_list = []
    if target_version:
        cache_key = f"map_state:{request.user.id}"
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
            "target_version": target_version,  # <--- Dodano przekazanie wersji (dla TinyMCE i linków)
            "tiers_info": tiers_info,  # <--- Dodano połączone dane o Stopniach i obrazkach
            "has_consent": has_consent,  # <--- Flaga RODO / Praw Autorskich do UI
        },
    )


@login_required
def region_detail_view(request, region_level: str, region_id: int):
    """Szczegóły regionu geograficznego z rankingiem obiektów i mapą."""

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
    cache_key = f"map_state:{request.user.id}"
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

    # 1. Hierarchia pionowa (Góra / Dół) - oparta o relacje ORM
    if lvl == "MESOREGION":
        parent_region = getattr(region, "macroregion", None)
        parent_level = "MACROREGION"
    elif lvl == "MACROREGION":
        parent_region = getattr(region, "subprovince", None)
        parent_level = "SUBPROVINCE"
        children_regions = region.mesoregionmodel_set.all() if hasattr(region, "mesoregionmodel_set") else []
        children_level = "MESOREGION"
    elif lvl == "SUBPROVINCE":
        parent_region = getattr(region, "province", None)
        parent_level = "PROVINCE"
        children_regions = region.macroregionmodel_set.all() if hasattr(region, "macroregionmodel_set") else []
        children_level = "MACROREGION"
    elif lvl == "PROVINCE":
        children_regions = region.subprovincemodel_set.all() if hasattr(region, "subprovincemodel_set") else []
        children_level = "SUBPROVINCE"
    elif lvl == "TOURIST_REGION":
        # Region turystyczny to byt wirtualny (M2M), pokazujemy jego składowe
        children_regions = region.mesoregions.all() if hasattr(region, "mesoregions") else []
        children_level = "MESOREGION"

    # 2. Relacje poziome (Sąsiedzi) - Magia PostGIS (ST_Touches)
    neighbors: list[Any] = []
    if hasattr(region, "shape") and region.shape:
        # Znajduje poligony tego samego typu, które fizycznie stykają się granicami
        qs = ModelClass.objects.filter(shape__touches=region.shape).exclude(id=region.id).order_by("name")
        neighbors = list(qs)

    return render(
        request,
        "tourists/region_detail.html",
        {
            "region": region,
            "region_level": region_level,
            "region_id": region_id,
            "extent": extent,  # (min_lon, min_lat, max_lon, max_lat)
            "top_objects": ranking_data[:20],  # Pokażemy TOP 20 w tabelce
            "total_objects": len(ranking_data),
            # Przekazujemy nawigację do szablonu:
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
    user_id = request.user.id

    cache_key = f"map_state:{user_id}"
    cached_data = cache.get(cache_key) or {}

    scores = cached_data.get("scores", {})
    colors = cached_data.get("colors", {})

    # Helpery wymuszające odpowiedni typ z Redisa (zabezpieczenie przed stringami)
    def get_score(pid):
        s = scores.get(pid, scores.get(str(pid), 0))
        try:
            return int(s)
        except ValueError, TypeError:
            return 0

    def get_color(pid):
        return colors.get(pid, colors.get(str(pid), "GRAY"))

    valid_peak_ids = [int(pid) for pid in scores.keys() if get_score(pid) > 0 and get_color(pid) != "GRAY"]

    from collections import defaultdict

    from django.db.models import Q

    # 1. POBIERAMY CAŁE RODZINY! Jeśli punktuje rodzic LUB dziecko - bierzemy wszystkich.
    peaks = (
        TouristObject.objects.filter(
            Q(id__in=valid_peak_ids)
            | Q(child_objects__id__in=valid_peak_ids)  # Bierzemy rodziców dla punktujących dzieci
            | Q(parent_object_id__in=valid_peak_ids)  # Bierzemy dzieci dla punktujących rodziców
        )
        .select_related("parent_object")
        .prefetch_related("badgeversionmodel_set__badge")
        .distinct()
    )

    # 2. Grupowanie w "Rodziny"
    clusters = defaultdict(list)
    for peak in peaks:
        anchor_id = peak.parent_object_id if peak.parent_object_id else peak.id
        clusters[anchor_id].append(peak)

    ranking_data = []

    # 3. Budujemy paczki dla szablonu
    for anchor_id, family_members in clusters.items():
        cluster_score = sum(get_score(p.id) for p in family_members)

        if cluster_score == 0:
            continue

        parent_node = next((p for p in family_members if p.id == anchor_id), None)
        # Sortujemy dzieci alfabetycznie
        children_nodes = sorted([p for p in family_members if p.id != anchor_id], key=lambda x: x.name)

        cluster_items = []

        # Formatujemy rodzica
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

        # Formatujemy dzieci
        for child in children_nodes:
            c_score = get_score(child.id)
            # Pokazujemy dziecko, tylko jeśli ma > 0 pkt
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

        # Flagujemy jako rodzinę tylko gdy pobrano więcej niż 1 obiekt z bazy
        is_family = len(cluster_items) > 1 or (parent_node and children_nodes)

        ranking_data.append(
            {
                "cluster_id": anchor_id,
                "cluster_name": cluster_name,
                "cluster_score": cluster_score,
                "is_family": is_family,
                "items": cluster_items,
            }
        )

    # Sortujemy Klastry od najbardziej opłacalnego
    ranking_data.sort(key=lambda x: x["cluster_score"], reverse=True)

    return render(request, "tourists/ranking.html", {"ranking": ranking_data})


@login_required
def region_ranking_view(request):
    """Widok tabelaryczny pokazujący skumulowany ranking dla całych regionów."""
    user_id = request.user.id

    # Definicja dostępnych poziomów do menu (bez Państw, bo to bezcelowe)
    LEVELS = {
        "MESOREGION": "Mezoregiony",
        "TOURIST_REGION": "Regiony Turystyczne (PTTK)",
        "MACROREGION": "Makroregiony",
        "SUBPROVINCE": "Podprowincje",
        "PROVINCE": "Prowincje",
        "VOIVODESHIP": "Województwa",
    }

    # Pobieramy poziom z URL. Domyślnie MESOREGION (idealny na wycieczkę)
    active_level = request.GET.get("level", "MESOREGION").upper()
    if active_level not in LEVELS:
        active_level = "MESOREGION"

    # 1. Pobieramy statystyki z Redis
    cache_key = f"map_state:{user_id}"
    cached_data = cache.get(cache_key) or {}

    scores = cached_data.get("scores", {})
    colors = cached_data.get("colors", {})

    # Wyłapujemy tylko szczyty punktujące
    valid_peak_ids = []
    for pid_str, score in scores.items():
        if score > 0 and colors.get(pid_str) != "GRAY":
            valid_peak_ids.append(int(pid_str))

    regions_agg = defaultdict(lambda: {"score": 0, "peak_count": 0})

    if valid_peak_ids:
        # 2. Pobieramy CQRS (Tylko dla jednego, konkretnego poziomu!)
        from apps.badges.models import ObjectRegionCache

        region_caches = ObjectRegionCache.objects.filter(
            tourist_object_id__in=valid_peak_ids, region_level=active_level
        )

        for rc in region_caches:
            peak_score = scores.get(rc.tourist_object_id, scores.get(str(rc.tourist_object_id), 0))
            if peak_score > 0:
                key = (rc.region_level, rc.region_id, rc.region_name)
                regions_agg[key]["score"] += peak_score
                regions_agg[key]["peak_count"] += 1

    # 3. Formatujemy dane dla szablonu
    ranking_data = []
    for (level, rid, name), data in regions_agg.items():
        ranking_data.append(
            {"level": level, "id": rid, "name": name, "total_score": data["score"], "peak_count": data["peak_count"]}
        )

    # 4. Sortujemy od najbardziej zyskownego regionu
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
    organizer = get_object_or_404(OrganizerModel, id=organizer_id)

    # Pobieramy odznaki przypisane do tego organizatora
    badges = organizer.badges.all().order_by("name")

    # Aby przyciski "+ Zacznij zdobywać" działały, sprawdzamy subskrypcje turysty
    subscribed_ids = UserBadgeProgress.objects.filter(user=request.user).values_list("badge_id", flat=True)

    return render(
        request,
        "tourists/organizer_detail.html",
        {
            "organizer": organizer,
            "badges": badges,
            "subscribed_ids": subscribed_ids,
        },
    )
