"""Stable errors for callers; none imply that replay is safe."""

class LabelSDKError(Exception):
    pass

class ConfigurationError(LabelSDKError, ValueError):
    pass

class GeometryError(ConfigurationError):
    pass

class AlignmentRequired(LabelSDKError):
    pass

class PrinterBusy(LabelSDKError):
    pass

class PrinterNotFound(LabelSDKError):
    pass

class DuplicateJob(LabelSDKError):
    def __init__(self, job_id, receipt):
        self.job_id, self.receipt = job_id, receipt
        super().__init__(f"Job {job_id!r} already exists; inspect its receipt instead of replaying it")

class PrinterFault(LabelSDKError):
    pass

class DrainTimeout(LabelSDKError):
    pass

class DeliveryUncertain(LabelSDKError):
    def __init__(self, job_id, cause):
        self.job_id, self.cause = job_id, cause
        super().__init__(f"Delivery of {job_id!r} is uncertain; do not retry automatically: {type(cause).__name__}")
