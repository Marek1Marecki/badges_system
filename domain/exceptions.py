"""Hierarchia wyjątków domenowych."""


class DomainException(Exception):
    """Bazowy wyjątek domenowy."""


class ValidationError(DomainException):
    """Naruszenie reguły biznesowej odznaki."""
