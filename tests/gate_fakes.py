"""A stand-in for a provider-gate lane: grants every slot at once and records what happened."""


class FreeLane:
    def __init__(self, grant=True, waits=None):
        self.grant, self.acquired, self.penalties = grant, 0, []
        self.waits = waits if waits is not None else []  # every penalty, for tests that listed sleeps

    def acquire(self, max_wait=None):
        self.acquired += 1 if self.grant else 0
        return self.grant

    def penalize(self, seconds, default=60.0):
        self.penalties.append(seconds)
        self.waits.append(seconds)

    def penalize_response(self, response, default=60.0):
        if getattr(response, "status_code", None) in (429, 503):
            self.penalize(default, default)
            return True
        return False
