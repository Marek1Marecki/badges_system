"""Testy dla wyjątków warstwy aplikacji."""

import pytest

from application.exceptions import ApplicationException, UseCaseError


class TestApplicationException:
    """Testy klasy bazowej ApplicationException."""

    def test_application_exception_inheritance(self):
        """Test że ApplicationException dziedziczy po Exception."""
        assert issubclass(ApplicationException, Exception)

    def test_application_exception_creation(self):
        """Test tworzenia ApplicationException."""
        exception = ApplicationException("Application error message")
        assert str(exception) == "Application error message"
        assert exception.args == ("Application error message",)

    def test_application_exception_without_message(self):
        """Test tworzenia ApplicationException bez wiadomości."""
        exception = ApplicationException()
        assert str(exception) == ""
        assert exception.args == ()

    def test_application_exception_with_multiple_args(self):
        """Test tworzenia ApplicationException z wieloma argumentami."""
        exception = ApplicationException("Error", "arg1", "arg2")
        assert exception.args == ("Error", "arg1", "arg2")

    def test_application_exception_can_be_caught_as_exception(self):
        """Test że ApplicationException może być łapany jako Exception."""
        with pytest.raises(Exception):
            raise ApplicationException("Test error")


class TestUseCaseError:
    """Testy klasy UseCaseError."""

    def test_use_case_error_inheritance(self):
        """Test że UseCaseError dziedziczy po ApplicationException."""
        assert issubclass(UseCaseError, ApplicationException)
        assert issubclass(UseCaseError, Exception)

    def test_use_case_error_creation(self):
        """Test tworzenia UseCaseError."""
        error = UseCaseError("Use case failed")
        assert str(error) == "Use case failed"
        assert isinstance(error, ApplicationException)

    def test_use_case_error_without_message(self):
        """Test tworzenia UseCaseError bez wiadomości."""
        error = UseCaseError()
        assert str(error) == ""
        assert isinstance(error, ApplicationException)

    def test_use_case_error_with_complex_message(self):
        """Test tworzenia UseCaseError ze złożoną wiadomością."""
        message = "Nie znaleziono odznaki: BADGE001 (v1)"
        error = UseCaseError(message)
        assert str(error) == message
        assert isinstance(error, ApplicationException)

    def test_use_case_error_can_be_caught_as_application_exception(self):
        """Test że UseCaseError może być łapany jako ApplicationException."""
        with pytest.raises(ApplicationException) as exc_info:
            raise UseCaseError("Test use case error")
        
        assert isinstance(exc_info.value, UseCaseError)
        assert isinstance(exc_info.value, ApplicationException)

    def test_use_case_error_can_be_caught_as_exception(self):
        """Test że UseCaseError może być łapany jako Exception."""
        with pytest.raises(Exception):
            raise UseCaseError("Test error")

    def test_use_case_error_specific_catch(self):
        """Test specyficznego łapania UseCaseError."""
        with pytest.raises(UseCaseError):
            raise UseCaseError("Specific use case error")

    def test_application_exception_is_not_use_case_error(self):
        """Test że ApplicationException nie jest UseCaseError."""
        with pytest.raises(ApplicationException) as exc_info:
            raise ApplicationException("Application error")
        
        assert not isinstance(exc_info.value, UseCaseError)
        assert type(exc_info.value) is ApplicationException

    def test_exception_hierarchy_chain(self):
        """Test łańcucha dziedziczenia wyjątków."""
        # Test that both can be caught as Exception
        with pytest.raises(Exception):
            raise ApplicationException("App error")
        
        with pytest.raises(Exception):
            raise UseCaseError("Use case error")
        
        # Test that UseCaseError can be caught as ApplicationException
        with pytest.raises(ApplicationException):
            raise UseCaseError("Use case error")
        
        # But ApplicationException cannot be caught as UseCaseError
        with pytest.raises(ApplicationException) as exc_info:
            raise ApplicationException("App error")
        
        assert not isinstance(exc_info.value, UseCaseError)

    def test_exception_with_different_message_types(self):
        """Test wyjątków z różnymi typami wiadomości."""
        messages = [
            "Simple error",
            "Error with numbers: 123",
            "Error with special chars: !@#$%",
            "Error with unicode: ąęłżśćźń",
            "Very long error message " * 10,
        ]
        
        for message in messages:
            app_error = ApplicationException(message)
            use_case_error = UseCaseError(message)
            
            assert str(app_error) == message
            assert str(use_case_error) == message
