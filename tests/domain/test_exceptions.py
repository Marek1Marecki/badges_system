"""Testy dla wyjątków domenowych."""

import pytest

from domain.exceptions import DomainException, ValidationError


class TestDomainException:
    """Testy klasy bazowej DomainException."""

    def test_domain_exception_inheritance(self):
        """Test że DomainException dziedziczy po Exception."""
        assert issubclass(DomainException, Exception)

    def test_domain_exception_creation(self):
        """Test tworzenia DomainException."""
        exception = DomainException("Test message")
        assert str(exception) == "Test message"
        assert exception.args == ("Test message",)

    def test_domain_exception_without_message(self):
        """Test tworzenia DomainException bez wiadomości."""
        exception = DomainException()
        assert str(exception) == ""
        assert exception.args == ()

    def test_domain_exception_with_multiple_args(self):
        """Test tworzenia DomainException z wieloma argumentami."""
        exception = DomainException("Message", "arg1", "arg2")
        assert exception.args == ("Message", "arg1", "arg2")


class TestValidationError:
    """Testy klasy ValidationError."""

    def test_validation_error_inheritance(self):
        """Test że ValidationError dziedziczy po DomainException."""
        assert issubclass(ValidationError, DomainException)
        assert issubclass(ValidationError, Exception)

    def test_validation_error_creation(self):
        """Test tworzenia ValidationError."""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, DomainException)

    def test_validation_error_without_message(self):
        """Test tworzenia ValidationError bez wiadomości."""
        error = ValidationError()
        assert str(error) == ""
        assert isinstance(error, DomainException)

    def test_validation_error_with_complex_message(self):
        """Test tworzenia ValidationError ze złożoną wiadomością."""
        message = "Wymagano 3 szczytów, masz 2 | Aktywność CYCLING jest niedozwolona"
        error = ValidationError(message)
        assert str(error) == message

    def test_validation_error_can_be_caught_as_domain_exception(self):
        """Test że ValidationError może być łapany jako DomainException."""
        with pytest.raises(DomainException):
            raise ValidationError("Test error")

    def test_validation_error_can_be_caught_as_exception(self):
        """Test że ValidationError może być łapany jako Exception."""
        with pytest.raises(ValidationError):
            raise ValidationError("Test error")

    def test_validation_error_specific_catch(self):
        """Test specyficznego łapania ValidationError."""
        with pytest.raises(ValidationError):
            raise ValidationError("Specific validation error")

    def test_domain_exception_is_not_validation_error(self):
        """Test że DomainException nie jest ValidationError."""
        with pytest.raises(DomainException) as exc_info:
            raise DomainException("Domain error")
        
        assert not isinstance(exc_info.value, ValidationError)
        assert type(exc_info.value) is DomainException
