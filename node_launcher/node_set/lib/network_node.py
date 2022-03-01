from typing import Optional

from node_launcher.gui.qt import Signal, QObject, QProcess
from node_launcher.constants import NodeSoftwareName, OperatingSystem, TOR, BITCOIND, LND
from node_launcher.app_logging import log
from node_launcher.node_set.bitcoind.bitcoind_configuration import BitcoindConfiguration
from node_launcher.node_set.bitcoind.bitcoind_process import BitcoindProcess
from node_launcher.node_set.lib.hard_drives import Partition
from node_launcher.node_set.lib.managed_process import ManagedProcess
from node_launcher.node_set.lib.node_status import NodeStatus
from node_launcher.node_set.lib.software import Software
from node_launcher.node_set.lnd.lnd_configuration import LndConfiguration
from node_launcher.node_set.lnd.lnd_process import LndProcess
from node_launcher.node_set.tor.tor_configuration import TorConfiguration


class NetworkNode(QObject):
    node_software_name: NodeSoftwareName

    current_status: Optional[NodeStatus]

    status = Signal(str)

    def __init__(self, operating_system: OperatingSystem,
                 node_software_name: NodeSoftwareName,
                 bitcoind_partition: Optional[Partition]):
        super().__init__()
        self.node_software_name = node_software_name
        self.current_status = None
        self.software = Software(operating_system=operating_system, node_software_name=node_software_name)
        if node_software_name == LND:
            self.configuration = LndConfiguration(bitcoind_partition=bitcoind_partition)
            self.process = LndProcess(self.software.daemon, self.configuration.args)
        elif node_software_name == BITCOIND:
            self.configuration = BitcoindConfiguration(partition=bitcoind_partition)
            self.process = BitcoindProcess(self.software.daemon, self.configuration.args)
        else:
            self.configuration = TorConfiguration()
            self.process = ManagedProcess(self.software.daemon, self.configuration.args)

        self.software = Software(operating_system=operating_system,
                                 node_software_name=node_software_name)

        if node_software_name == TOR:
            self.configuration = TorConfiguration()
            self.process = ManagedProcess(self.software.daemon,
                                          self.configuration.args)
        elif node_software_name == BITCOIND:
            self.configuration = BitcoindConfiguration(partition=bitcoind_partition)
            self.process = BitcoindProcess(self.software.daemon,
                                           self.configuration.args)
        elif node_software_name == LND:
            self.configuration = LndConfiguration(bitcoind_partition=bitcoind_partition)
            self.process = LndProcess(self.software.daemon,
                                      self.configuration.args)
        self.connect_events()
        self.restart = False

    def stop(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.update_status(NodeStatus.STOPPED)

    def handle_log_line(self, log_line: str):
        pass

    def handle_status_change(self, new_status):
        pass

    def connect_events(self):
        self.status.connect(self.handle_status_change)
        self.software.status.connect(self.update_status)
        self.process.status.connect(self.update_status)
        self.process.log_line.connect(self.handle_log_line)

    def update_status(self, new_status: NodeStatus, new_description: str = None):
        log.debug(f'update_status {self.node_software_name} node',
                  network=self.node_software_name,
                  old_status=self.current_status,
                  new_status=new_status)
        if not new_description:
            new_description = str(new_status)
        self.current_status = new_status
        self.status.emit(str(new_status))
        if new_status == NodeStatus.STOPPED and self.restart:
            self.update_status(NodeStatus.RESTART)

    @property
    def prerequisites_synced(self):
        return True

    def start_process(self):
        log.debug('Start process', node_software_name=self.node_software_name,
                  current_status=self.current_status)
        if self.process.state() == QProcess.Running:
            log.debug('Process already running')
            return

        # Todo: run in threads so they don't block the GUI
        self.update_status(NodeStatus.LOADING_CONFIGURATION)
        self.configuration.load()
        self.update_status(NodeStatus.CHECKING_CONFIGURATION)
        self.configuration.check()
        self.update_status(NodeStatus.CONFIGURATION_READY)
        self.update_status(NodeStatus.STARTING_PROCESS)
        self.process.start()
        self.update_status(NodeStatus.PROCESS_STARTED)
