"""AI integration exceptions."""


class AIConfigurationError(Exception):
    """Raised when required AI configuration is missing or invalid."""


class AIProviderError(Exception):
    """Raised when the upstream AI provider request fails."""


class AIResponseError(Exception):
    """Raised when the upstream AI provider returns unusable content."""
