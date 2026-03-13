class TimelineEngine:
    def __init__(self):
        self.events = []

    def clear(self):
        self.events = []

    def add_event(self, minute, kind, text):
        self.events.append({
            "minute": minute,
            "kind": kind,
            "text": text
        })

    def as_lines(self):
        return [f"{e['minute']:02d}' [{e['kind'].upper()}] {e['text']}" for e in self.events]