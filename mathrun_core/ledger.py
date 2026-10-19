"""Bookkeeping for numbered work units.

Every problem's search is cut into numbered units 0, 1, 2, ... The ledger
remembers which are finished. ``frontier`` is the first unit that is NOT
finished, so everything below it is certainly done; that is the only number
we ever claim as "searched". Units handed out but not finished when the
computer turns off are simply handed out again next time.
"""


class Ledger:
    def __init__(self, data=None):
        data = data or {}
        self.frontier = int(data.get("frontier", 0))
        self.next = max(int(data.get("next", 0)), self.frontier)
        self.done = set(int(i) for i in data.get("done", []) if int(i) >= self.frontier)

    def to_dict(self):
        return {"frontier": self.frontier, "next": self.next, "done": sorted(self.done)}

    def issue(self, inflight):
        """Smallest unit number that is neither finished nor being worked on."""
        i = self.frontier
        while i < self.next:
            if i not in self.done and i not in inflight:
                return i
            i += 1
        self.next += 1
        return self.next - 1

    def complete(self, i):
        i = int(i)
        if i < self.frontier or i in self.done:
            return False
        if i >= self.next:
            raise ValueError("unit %d was never issued" % i)
        self.done.add(i)
        while self.frontier in self.done:
            self.done.discard(self.frontier)
            self.frontier += 1
        return True

    def completed_count(self):
        return self.frontier + len(self.done)
