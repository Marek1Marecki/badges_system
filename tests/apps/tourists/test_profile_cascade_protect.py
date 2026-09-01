from datetime import date

import pytest
from django.db.models.deletion import ProtectedError

from apps.badges.models import TouristObject
from apps.tourists.models import AscentLog, TouristProfile
from tests.factories.tourist import TouristProfileFactory


@pytest.mark.django_db(transaction=True)
@pytest.mark.integration
class TestProfileCascadeProtect:
    def test_deleting_profile_protects_ascent_logs(self):
        profile = TouristProfileFactory()
        peak = TouristObject.objects.create(name="Test Peak", type="Szczyt", is_active=True, status="READY")
        AscentLog.objects.create(profile=profile, peak=peak, ascent_date=date(2024, 1, 1))

        with pytest.raises(ProtectedError):
            profile.delete()

        assert TouristProfile.objects.filter(id=profile.id).exists()
        assert AscentLog.objects.filter(profile=profile).exists()
