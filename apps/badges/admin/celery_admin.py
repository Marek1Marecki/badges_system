"""Integracja ze stonowanymi paczkami Celery (`django-celery-beat`) z motywem Unfold.

Wyrejestrowuje oryginalne, surowe widoki Django Celery Beat, a następnie
ponownie je rejestruje z klasami dziedziczącymi po `unfold.admin.ModelAdmin`,
aby zapewnić spójny wygląd panelu administracyjnego.
"""

from django.contrib import admin
from django_celery_beat.admin import ClockedScheduleAdmin as BaseClockedScheduleAdmin
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from unfold.admin import ModelAdmin

admin.site.unregister(PeriodicTask)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(SolarSchedule)


@admin.register(PeriodicTask)
class UnfoldPeriodicTaskAdmin(ModelAdmin, BasePeriodicTaskAdmin):
    """Panel zadań okresowych Celery z integracją Unfold."""

    pass


@admin.register(CrontabSchedule)
class UnfoldCrontabScheduleAdmin(ModelAdmin):
    """Panel harmonogramów crontab Celery z integracją Unfold."""

    pass


@admin.register(IntervalSchedule)
class UnfoldIntervalScheduleAdmin(ModelAdmin):
    """Panel harmonogramów interwałowych Celery z integracją Unfold."""

    pass


@admin.register(ClockedSchedule)
class UnfoldClockedScheduleAdmin(ModelAdmin, BaseClockedScheduleAdmin):
    """Panel harmonogramów zegarowych Celery z integracją Unfold."""

    pass


@admin.register(SolarSchedule)
class UnfoldSolarScheduleAdmin(ModelAdmin):
    """Panel harmonogramów słonecznych Celery z integracją Unfold."""

    pass
