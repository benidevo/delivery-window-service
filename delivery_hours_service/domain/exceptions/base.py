class DomainError(Exception):
    """Base class for all domain-specific exceptions."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
