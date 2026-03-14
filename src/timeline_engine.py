class TimelineEngine:
    def __init__(self):
        self.events = []

    def clear(self):
        self.events = []

    def add_event(self, minute, kind, text):
        self.events.append({
            "minute": int(minute),
            "kind": str(kind),
            "text": str(text)
        })

    def as_lines(self, limit=None):
        lines = [f"{e['minute']:02d}' [{e['kind'].upper()}] {e['text']}" for e in self.events]
        if limit is not None:
            return lines[-limit:]
        return lines