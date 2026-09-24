"""Pure completion rules. Unknown/malformed states always block the action."""
from .i18n import _
import math

KEYS = ['state', 'progress', 'is_finished']
ACTIONS = {'sleep': 'Сон', 'hibernate': 'Гибернация', 'shutdown': 'Выключение'}


def summarize(torrents):
    if not isinstance(torrents, dict):
        raise ValueError(_('Deluge не вернул список торрентов.'))
    total, paused, pending = len(torrents), 0, 0
    for row in torrents.values():
        if not isinstance(row, dict):
            pending += 1
            continue
        if row.get('state') == 'Paused':
            paused += 1
            continue
        progress = row.get('progress')
        complete = (isinstance(progress, (int, float)) and not isinstance(progress, bool)
                    and math.isfinite(progress) and progress >= 100
                    and row.get('is_finished') is True
                    and row.get('state') in ('Seeding', 'Queued'))
        if not complete:
            pending += 1
    return dict(total=total, paused=paused, pending=pending,
                ready=bool(total and not pending))


class Monitor:
    """Countdown consumes fresh snapshots, never reuses a pre-countdown snapshot."""
    def __init__(self, clock):
        self.clock = clock
        self.deadline = None

    def observe(self, torrents, final=False):
        summary = summarize(torrents)
        if not summary['ready']:
            self.deadline = None
            return 'wait', summary
        if self.deadline is None:
            self.deadline = self.clock() + 60
            return 'countdown', summary
        if final and self.clock() >= self.deadline:
            return 'execute', summary
        return 'countdown', summary

    def remaining(self):
        return max(0, math.ceil(self.deadline - self.clock())) if self.deadline is not None else None
