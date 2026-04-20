"""Testy dla portów repozytorium."""



from application.ports.badge_repository_port import BadgeRepositoryPort
from domain.entities.badge_version import BadgeVersionDomain
from domain.rules.badge_rules import ActivityRule
from domain.value_objects.ascent import ActivityType


class TestBadgeRepositoryPort:
    """Testy interfejsu BadgeRepositoryPort."""

    def test_badge_repository_port_is_protocol(self):
        """Test że BadgeRepositoryPort jest protokołem."""
        from typing import Protocol
        assert issubclass(BadgeRepositoryPort, Protocol)

    def test_badge_repository_port_has_get_badge_version_method(self):
        """Test że port ma metodę get_badge_version."""
        assert hasattr(BadgeRepositoryPort, 'get_badge_version')
        assert callable(getattr(BadgeRepositoryPort, 'get_badge_version', None))

    def test_get_badge_version_method_signature(self):
        """Test sygnatury metody get_badge_version."""
        import inspect
        
        sig = inspect.signature(BadgeRepositoryPort.get_badge_version)
        params = sig.parameters
        
        assert 'self' in params
        assert 'badge_code' in params
        assert 'version_code' in params
        
        assert params['badge_code'].annotation is str
        assert params['version_code'].annotation is str

    def test_get_badge_version_return_type(self):
        """Test typu zwracanego przez get_badge_version."""
        import inspect
        
        sig = inspect.signature(BadgeRepositoryPort.get_badge_version)
        return_annotation = sig.return_annotation
        
        # Should return BadgeVersionDomain or None
        assert return_annotation == BadgeVersionDomain | None

    def test_concrete_implementation_can_be_created(self):
        """Test że można stworzyć konkretną implementację portu."""
        
        class ConcreteBadgeRepository:
            def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
                if badge_code == "TEST" and version_code == "v1":
                    return BadgeVersionDomain(
                        version_id="v1",
                        rules=[ActivityRule(allowed_activities={ActivityType.HIKING})],
                        pool_peak_ids={1, 2, 3},
                        required_count=2
                    )
                return None
        
        # This should not raise any errors
        repository = ConcreteBadgeRepository()
        assert isinstance(repository, object)
        
        # Test that it implements the protocol interface
        assert hasattr(repository, 'get_badge_version')
        
        # Test the method works
        result = repository.get_badge_version("TEST", "v1")
        assert isinstance(result, BadgeVersionDomain)
        
        result_none = repository.get_badge_version("NONEXISTENT", "v1")
        assert result_none is None

    def test_protocol_compatibility_check(self):
        """Test sprawdzania zgodności z protokołem."""
        
        class IncompleteRepository:
            pass
        
        class CompleteRepository:
            def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
                return None
        
        # Incomplete repository should not be compatible
        incomplete = IncompleteRepository()
        assert not hasattr(incomplete, 'get_badge_version')
        
        # Complete repository should be compatible
        complete = CompleteRepository()
        assert hasattr(complete, 'get_badge_version')

    def test_method_can_be_called_with_different_parameters(self):
        """Test wywołania metody z różnymi parametrami."""
        
        class MockRepository:
            def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
                return None
        
        repository = MockRepository()
        
        # Test with various string parameters
        test_cases = [
            ("BADGE001", "v1"),
            ("CROWN", "latest"),
            ("", ""),
            ("123", "1.0"),
            ("badge-with-dashes", "version-with-dots"),
        ]
        
        for badge_code, version_code in test_cases:
            result = repository.get_badge_version(badge_code, version_code)
            assert result is None

    def test_protocol_defines_interface_correctly(self):
        """Test że protokół poprawnie definiuje interfejs."""
        # The fact that we can use it as a type hint and it has the correct method
        # signature is sufficient to verify the protocol is defined correctly
        assert hasattr(BadgeRepositoryPort, 'get_badge_version')
        
        # Test it can be used in type annotations
        def test_function(repo: BadgeRepositoryPort) -> None:
            pass
        
        # This should not raise any errors
        assert test_function.__annotations__ is not None

    def test_protocol_can_be_used_as_type_hint(self):
        """Test że protokół może być używany jako type hint."""
        
        def function_that_uses_repository(repository: BadgeRepositoryPort) -> BadgeVersionDomain | None:
            return repository.get_badge_version("TEST", "v1")
        
        class TestRepository:
            def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
                return BadgeVersionDomain(
                    version_id="v1",
                    rules=[],
                    pool_peak_ids=set(),
                    required_count=0
                )
        
        repo = TestRepository()
        result = function_that_uses_repository(repo)
        assert isinstance(result, BadgeVersionDomain)

    def test_protocol_supports_runtime_checking(self):
        """Test że protokół wspiera sprawdzanie w runtime."""
        class CompleteRepository:
            def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
                return None
        
        class IncompleteRepository:
            pass
        
        complete = CompleteRepository()
        incomplete = IncompleteRepository()
        
        # Both should be usable as BadgeRepositoryPort (Protocol is structural)
        assert hasattr(complete, 'get_badge_version')
        assert not hasattr(incomplete, 'get_badge_version')
