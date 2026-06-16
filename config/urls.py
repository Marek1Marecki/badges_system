"""URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from apps.tourists.views import (
    badge_catalog_view,
    badge_detail_view,
    dashboard_view,
    object_detail_view,
    organizer_detail_view,
    poi_ranking_view,
    profile_settings_view,
    region_detail_view,
    region_ranking_view,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tinymce/", include("tinymce.urls")),
    path("api/", include("apps.api.urls")),
    path("", dashboard_view, name="home"),
    path("catalog/", badge_catalog_view, name="catalog"),
    path("profile/", profile_settings_view, name="profile"),
    path("accounts/", include("allauth.urls")),
    path("ranking/", poi_ranking_view, name="ranking"),
    path("object/<int:object_id>/", object_detail_view, name="object_detail"),
    path("badge/<str:badge_code>/", badge_detail_view, name="badge_detail"),
    path("region/<str:region_level>/<int:region_id>/", region_detail_view, name="region_detail"),
    path("ranking/regions/", region_ranking_view, name="region_ranking"),
    path("organizer/<int:organizer_id>/", organizer_detail_view, name="organizer_detail"),
]
