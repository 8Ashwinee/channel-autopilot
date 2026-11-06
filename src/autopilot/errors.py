class AutopilotError(Exception):
    """Anything that stops one post; recorded in the ledger and retried on a later day."""


class QuotaReached(AutopilotError):
    """The platform said stop for today (upload cap, publishing quota). Not a failure of the item."""


class ConfigError(AutopilotError):
    pass
