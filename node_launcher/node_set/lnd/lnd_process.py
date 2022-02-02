import re
from dataclasses import dataclass
from datetime import datetime

import humanize
from node_launcher.gui.qt import QTimer, Signal, QSystemTrayIcon

from node_launcher.node_set.lib.managed_process import ManagedProcess
from node_launcher.node_set.lib.node_status import NodeStatus


@dataclass
class ProgressBarStatus(object):
    percentage: int
    humanized_eta: str


class LndProcess(ManagedProcess):
    set_progress_bar = Signal(ProgressBarStatus)

    def __init__(self, binary: str, args):
        super().__init__(binary, args)

        self.old_height = None
        self.old_timestamp = None
        self.rescan_height = None
        self.old_status = None

    def process_output_line(self, line: str):
        if 'Waiting for wallet encryption password' in line:
            self.update_status(NodeStatus.UNLOCK_READY)
        elif 'Waiting for chain backend to finish sync' in line:
            self.update_status(NodeStatus.SYNCING)
        elif 'Unable to synchronize wallet to chain' in line:
            self.terminate()
            self.restart_process()
        elif 'Error during rescan: rescan block subscription was canceled' in line:
            self.restart_process()
        elif 'Started rescan from block' in line:
            self.rescan_height = int(re.search('height \d{6}', line)[0].split()[-1])
        elif 'Unable to complete chain rescan' in line:
            self.terminate()
            self.restart_process()
        elif 'unable to create chain control' in line:
            self.terminate()
            self.waitForFinished(-1)
            self.start()
        elif 'Starting HTLC Switch' in line:
            self.update_status(NodeStatus.SYNCED)
            self.notification.emit(
                'Nodes are ready',
                'Open Joule',
                QSystemTrayIcon.Information
            )
        elif 'Filtering block' in line:
            line_parts = line.split(' ')
            height_line_part = line_parts[6]
            new_height = int(height_line_part)
            timestamp = ' '.join(line_parts[0:1])
            new_timestamp = datetime.strptime(
                timestamp,
                '%Y-%m-%d %H:%M:%S.%f'
            )
            if self.old_height is not None:
                change = new_height - self.old_height
                if change:
                    timestamp_change = new_timestamp - self.old_timestamp
                    total_left = 800000 - new_height
                    time_left = (total_left / change) * timestamp_change
                    humanized = humanize.naturaltime(-time_left, future=True)
                    description = f'syncing, ready {humanized}'
                    self.update_status(NodeStatus.SYNCING, description)
                    self.set_progress_bar.emit(ProgressBarStatus(percentage=50, humanized_eta=humanized))
            self.old_height = new_height
            self.old_timestamp = new_timestamp

    def delayed_start(self, **kwargs):
        self.stop()
        super().start(**kwargs)

    def start(self):
        QTimer.singleShot(4000, self.delayed_start)
