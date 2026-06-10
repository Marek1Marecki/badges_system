"""Testy dla User Progress Ports."""

from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)


def test_tourist_profile_repository_port_is_protocol():
    """Test że TouristProfileRepositoryPort jest protokołem."""
    assert hasattr(TouristProfileRepositoryPort, "get_profile")
    assert callable(TouristProfileRepositoryPort.get_profile)


def test_ascent_log_repository_port_is_protocol():
    """Test że AscentLogRepositoryPort jest protokołem."""
    assert hasattr(AscentLogRepositoryPort, "get_object_lifespan")
    assert hasattr(AscentLogRepositoryPort, "ascent_exists")
    assert hasattr(AscentLogRepositoryPort, "get_oldest_ascent_date")
    assert hasattr(AscentLogRepositoryPort, "save_ascent")
    assert hasattr(AscentLogRepositoryPort, "get_unconsumed_ascents")
    assert callable(AscentLogRepositoryPort.get_object_lifespan)
    assert callable(AscentLogRepositoryPort.ascent_exists)
    assert callable(AscentLogRepositoryPort.get_oldest_ascent_date)
    assert callable(AscentLogRepositoryPort.save_ascent)
    assert callable(AscentLogRepositoryPort.get_unconsumed_ascents)


def test_user_progress_repository_port_is_protocol():
    """Test że UserProgressRepositoryPort jest protokołem."""
    assert hasattr(UserProgressRepositoryPort, "get_active_progresses")
    assert hasattr(UserProgressRepositoryPort, "get_progress")
    assert hasattr(UserProgressRepositoryPort, "start_progress")
    assert hasattr(UserProgressRepositoryPort, "update_domain_status")
    assert hasattr(UserProgressRepositoryPort, "update_logistic_status")
    assert callable(UserProgressRepositoryPort.get_active_progresses)
    assert callable(UserProgressRepositoryPort.get_progress)
    assert callable(UserProgressRepositoryPort.start_progress)
    assert callable(UserProgressRepositoryPort.update_domain_status)
    assert callable(UserProgressRepositoryPort.update_logistic_status)


def test_tourist_profile_repository_port_return_types():
    """Test typów zwracanych przez TouristProfileRepositoryPort."""
    # Test that the method has a return type annotation
    assert "return" in TouristProfileRepositoryPort.get_profile.__annotations__


def test_ascent_log_repository_port_return_types():
    """Test typów zwracanych przez AscentLogRepositoryPort."""
    # Test that methods have return type annotations
    assert "return" in AscentLogRepositoryPort.get_object_lifespan.__annotations__
    assert "return" in AscentLogRepositoryPort.ascent_exists.__annotations__
    assert "return" in AscentLogRepositoryPort.get_oldest_ascent_date.__annotations__
    assert "return" in AscentLogRepositoryPort.save_ascent.__annotations__
    assert "return" in AscentLogRepositoryPort.get_unconsumed_ascents.__annotations__


def test_user_progress_repository_port_return_types():
    """Test typów zwracanych przez UserProgressRepositoryPort."""
    # Test that methods have return type annotations
    assert "return" in UserProgressRepositoryPort.get_active_progresses.__annotations__
    assert "return" in UserProgressRepositoryPort.get_progress.__annotations__
    assert "return" in UserProgressRepositoryPort.start_progress.__annotations__
    assert "return" in UserProgressRepositoryPort.update_domain_status.__annotations__
    assert "return" in UserProgressRepositoryPort.update_logistic_status.__annotations__
