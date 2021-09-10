from typing import Optional

from node_launcher.gui.qt import QObject, Signal
from node_launcher.constants import OPERATING_SYSTEM
from .bitcoind.bitcoind_node import BitcoindNode
from .lib.hard_drives import Partition
from .lib.node_status import NodeStatus
from .lnd.lnd_node import LndNode
from .tor.tor_node import TorNode
from node_launcher.app_logging import log


class NodeSet(QObject):
    tor_node: TorNode
    bitcoind_node: Optional[BitcoindNode]
    lnd_node: LndNode

    set_icon_number = Signal(int)

    def __init__(self, full_node_partition: Partition):
        super().__init__()
        self.full_node_partition = full_node_partition

        self.tor_node = TorNode(operating_system=OPERATING_SYSTEM)
        self.bitcoind_node = BitcoindNode(operating_system=OPERATING_SYSTEM, partition=self.full_node_partition)
        self.lnd_node = LndNode(operating_system=OPERATING_SYSTEM, bitcoind_partition=self.full_node_partition)

        self.tor_node.status.connect(
            self.handle_tor_node_status_change
        )
        self.bitcoind_node.status.connect(
            self.handle_bitcoind_node_status_change
        )
        self.lnd_node.status.connect(
            self.handle_lnd_node_status_change
        )

    def start(self):
        log.debug('Starting node set')
        self.tor_node.start_process()
        self.set_icon_number.emit(1)
        self.bitcoind_node.start_process()

    def handle_tor_node_status_change(self, tor_status):
        if tor_status == NodeStatus.RESTART:
            self.start()
        elif tor_status == NodeStatus.LIBRARY_ERROR:
            self.tor_node.software.start_update_worker()
        elif tor_status == NodeStatus.SYNCED:
            self.set_icon_number.emit(2)
            self.bitcoind_node.tor_synced = True

    def handle_bitcoind_node_status_change(self, bitcoind_status):
        if bitcoind_status == NodeStatus.SYNCING:
            self.bitcoind_node.configuration['reindex'] = False
            self.lnd_node.start_process()

    def handle_lnd_node_status_change(self, lnd_status):
        if lnd_status == NodeStatus.BITCOIND_SYNCED:
            self.set_icon_number.emit(3)
            self.bitcoind_node.process.update_status(NodeStatus.SYNCED)
        elif lnd_status == NodeStatus.SYNCED:
            self.set_icon_number.emit(4)
