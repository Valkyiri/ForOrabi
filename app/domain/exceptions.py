class DomainError(Exception):
    pass

class ConfigurationError(DomainError):
    pass

class EmptyCorpusError(DomainError):
    pass

class ExternalServiceError(DomainError):
    pass

class IngestionError(DomainError):
    pass
