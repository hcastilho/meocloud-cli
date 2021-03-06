import os
import sys
import signal
import gevent
from subprocess import Popen, check_output


from meocloud.client.linux.settings import (
    CORE_BINARY_FILENAME,
    CORE_DIR,
    CORE_LISTENER_SOCKET_ADDRESS,
    CORE_PID_PATH,
    CORE_WATCHDOG_PERIOD,
    DAEMON_LISTENER_SOCKET_ADDRESS,
    LOGGER_NAME,
    MEOCLOUD_PREFIX,
    )
from meocloud.client.linux.utils import test_already_running, get_own_dir
from meocloud.client.linux.daemon.communication import Events

import logging
log = logging.getLogger(LOGGER_NAME)


class Core(object):
    def __init__(self, core_client):
        log.debug('Core: Initializing...')
        super(Core, self).__init__()
        self.core_client = core_client
        self.process = None
        self.core_binary_path = os.path.join(MEOCLOUD_PREFIX, CORE_DIR, CORE_BINARY_FILENAME)
        self.core_env = os.environ.copy()
        self.core_env['CLD_CORE_SOCKET_PATH'] = DAEMON_LISTENER_SOCKET_ADDRESS
        self.core_env['CLD_UI_SOCKET_PATH'] = CORE_LISTENER_SOCKET_ADDRESS
        try:
            if sys.getfilesystemencoding().lower() != 'utf-8':
                if 'C.UTF-8' in check_output(['locale', '-a']).splitlines():
                    log.info('Forcing locale to C.UTF-8')
                    self.core_env['LC_ALL'] = 'C.UTF-8'
                else:
                    log.info('Forcing locale to en_US.utf8')
                    self.core_env['LC_ALL'] = 'en_US.utf8'
        except Exception:
            log.exception('Something went wrong while trying to fix set the LC_ALL env variable')

    def start(self):
        """
        Starts core without verifying if it is already running
        """
        log.info('Core: Starting core')
        self.process = Popen([self.core_binary_path], env=self.core_env)

    def stop_by_pid(self):
        pid = test_already_running(CORE_PID_PATH, CORE_BINARY_FILENAME)
        if pid:
            os.kill(pid, signal.SIGTERM)
            log.debug('Core: Killed core running with pid {0}'.format(pid))

    def stop(self):
        if self.process is not None:
            self.process.kill()
            self.process = None
        else:
            self.stop_by_pid()

    def watchdog(self):
        # Watchdog wait for event core_start_ready before starting
        Events.core_start_ready.wait()
        log.debug('Core: watchdog will now start')
        while True:
            # TODO Use ping to core_client
            # TODO Try to use self.process to check if running
            if not test_already_running(CORE_PID_PATH, CORE_BINARY_FILENAME):
                self.start()
            gevent.sleep(CORE_WATCHDOG_PERIOD)
