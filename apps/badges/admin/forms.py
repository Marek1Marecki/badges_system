"""Formularze używane w panelu Django Admin dla aplikacji badgeów."""

from django import forms

from apps.badges.models import BadgeVersionModel


class AddToBadgeForm(forms.Form):
    """Prosty formularz do okienka pośredniego w Akcji Admina."""

    badge_version = forms.ModelChoiceField(
        queryset=BadgeVersionModel.objects.none(),  # Domyślnie puste przy ładowaniu pliku
        label="Wybierz Wersję Odznaki",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        """Inicjalizuje formularz z pustym querysetem wersji odznak."""
        super().__init__(*args, **kwargs)
        # Baza odpytywana JEDYNIE w momencie faktycznego otwarcia okienka przez Admina!
        self.fields["badge_version"].queryset = BadgeVersionModel.objects.select_related("badge").all()


class BadgeTierInlineFormSet(forms.BaseInlineFormSet):
    """Walidator dla wierszy stopni odznaki (FormSet)."""

    def clean(self):
        """Waliduje wiersze FormSetu stopni odznaki."""
        super().clean()
        # Jeśli formularze mają już inne błędy, nie sprawdzamy dalej
        if any(self.errors):
            return

        orders = set()
        for form in self.forms:
            # Pomijamy puste wiersze oraz te zaznaczone do usunięcia
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue

            order_val = form.cleaned_data.get("order")
            if order_val is not None:
                if order_val in orders:
                    raise forms.ValidationError(
                        "Błąd: Kolejność zdobywania stopni (pole 'order') musi być unikalna w ramach jednej odznaki!"
                    )
                orders.add(order_val)
