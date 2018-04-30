class ValidationError(ValueError):
    pass


class PermissionError(ValidationError):
    pass


class DNSPodError(ValueError):
    pass


class CeleryError(ValueError):
    pass


class UnImplemented(ValidationError):
    pass
