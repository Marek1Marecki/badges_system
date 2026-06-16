"""Tests for main entry point."""

from main import main


class TestMain:
    """Test suite for main entry point."""

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        assert callable(main)

    def test_main_prints_message(self, capsys):
        """Test that main function prints expected message."""
        main()
        captured = capsys.readouterr()
        assert "Hello from badges-system!" in captured.out
