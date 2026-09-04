class ControlKernelError(RuntimeError):
    """Base error for deterministic Control Kernel failures."""


class InvalidTransition(ControlKernelError):
    pass


class StaleLease(ControlKernelError):
    pass


class IdempotencyConflict(ControlKernelError):
    pass


class PolicyDenied(ControlKernelError):
    pass


class UnsupportedRuntime(ControlKernelError):
    pass


class DatabaseUnavailable(ControlKernelError):
    pass


class OrchestratorAlreadyOwned(ControlKernelError):
    pass
