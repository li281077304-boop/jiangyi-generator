"""Read-only disk budgets; never deletes user data or caches."""
from pathlib import Path
import os
import shutil
import tempfile

RESERVE_BYTES = 256 * 1024 * 1024


class DiskSpaceError(ValueError):
    def __init__(self, details):
        self.details = details
        text = '；'.join('%s（%s）：可用 %.0f MB，预计至少需要 %.0f MB' %
                        ('、'.join(r['locations']), r['volume'], r['free_bytes']/1048576,
                         r['required_bytes']/1048576) for r in details)
        super().__init__('磁盘空间不足，尚未开始生成。请释放空间或更换任务目录后重试。' + text)


def check_disk_space(runtime_root, result_root, input_bytes=0, *, temporary_root=None):
    size = max(0, int(input_bytes))
    groups = {}
    for label, raw, multiplier in [('临时目录', temporary_root or tempfile.gettempdir(), 2),
                                   ('任务目录', runtime_root, 6), ('成品目录', result_root, 3)]:
        path = Path(raw).expanduser().resolve()
        probe = path
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        volume = path.anchor.upper() if os.name == 'nt' else str(probe.stat().st_dev)
        row = groups.setdefault(volume, {'volume': volume, 'locations': [],
            'free_bytes': shutil.disk_usage(probe).free, 'required_bytes': RESERVE_BYTES})
        row['locations'].append(label)
        row['required_bytes'] += size * multiplier
    failures = [r for r in groups.values() if r['free_bytes'] < r['required_bytes']]
    if failures:
        raise DiskSpaceError(failures)
    return list(groups.values())
