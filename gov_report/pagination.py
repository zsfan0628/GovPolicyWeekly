"""Conservative date-window stopping for chronologically ordered list pages."""

from __future__ import annotations


class DateWindow:
    def __init__(self, enabled: bool = False, minimum_pages: int = 3, old_pages_required: int = 2):
        self.enabled = enabled
        self.minimum_pages = max(3, minimum_pages)
        self.old_pages_required = max(2, old_pages_required)
        self.pages = 0
        self.old_pages = 0
        self.last_date = None
        self.disabled = False

    def observe(self, items, start) -> bool:
        if not self.enabled or self.disabled:
            return False
        ordinary = [item for item in items if not item.pinned]
        # Do not infer chronological order from URL dates, one-row pages or missing dates.
        if len(ordinary) < 2 or any(not item.date_reliable or item.publish_date is None for item in ordinary):
            self.disabled = True
            return False
        dates = [item.publish_date for item in ordinary]
        if any(a < b for a, b in zip(dates, dates[1:])) or (self.last_date and self.last_date < dates[0]):
            self.disabled = True
            return False
        self.last_date = dates[-1]
        self.pages += 1
        self.old_pages = self.old_pages + 1 if all(date < start for date in dates) else 0
        return self.pages >= self.minimum_pages and self.old_pages >= self.old_pages_required
