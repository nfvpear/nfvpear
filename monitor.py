"""This module is responsible for providing a Stats Monitor for the VNFs."""

from __future__ import division
import humanize
import subprocess
from docker import Client
import threading
import time
import tempfile


CLI = Client(base_url='unix://var/run/docker.sock')


class Monitor(threading.Thread):
    """
    Class to monitor some statistics about the VNFs.

    An instance has at least the following attributes.
    ============== ============================================================
    Attribute      Description
    ============== ============================================================
    container_name String with the container name
    period         Integer with the monitoring interval
    m_stats        Monitor objetive, a string among the following options:
                    "mem" in percentage
                    "cpu" in percentage
                    "net_in" in packets
                    "net_out" in packets
    threshold      Threshold of the previous argument, will trigger an action
                   when the threshold is achieved. (Integer)
    ============== ============================================================

    """

    def __init__(self, container_name, period, m_stats, threshold):
        threading.Thread.__init__(self)
        self.container_name = container_name
        self.period = period
        self.m_stats = m_stats
        self.threshold = threshold
        self._temp_file = tempfile.NamedTemporaryFile(
                                                mode="w+t",
                                                suffix=self.container_name[3:])
        self._stop = threading.Event()

    def run(self):
        if int(self.period) > 1:
            while not self.stopped():
                stats = CLI.stats(self.container_name, stream=False)
                value = self.__stats_selector(self.m_stats, stats)
                if value >= self.threshold:
                    self._temp_file.write(
                                    '%s threshold hit at %s\n' %
                                    (str.upper(self.m_stats), time.asctime()))
                    self._temp_file.flush()
                time.sleep(self.period)
        else:
            for stats in CLI.stats(self.m_stats):
                value = self.__stats_selector(self.m_stats, stats)
                if value >= self.threshold:
                    self._temp_file.write(
                                    '%s threshold hit at %s\n' %
                                    (str.upper(self.m_stats), time.asctime()))
                    self._temp_file.flush()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.is_set()

    def __stats_selector(self, m_stats, stats):
        if m_stats == "mem":
            return self.__get_mem_percent(stats)
        elif m_stats == "cpu":
            return self.__get_cpu_percent(stats)
        elif m_stats == "net_in":
            ret_pkt = self.__get_network_usage()
            return ret_pkt[self.container_name[3:]+"-eth0"]['rx']
        elif m_stats == "net_out":
            ret_pkt = self.__get_network_usage()
            return ret_pkt[self.container_name[3:]+"-eth1"]['tx']

    def __get_cpu_percent(self, stats_json):
        cpu_percent = 0.0

        previousCPU = stats_json['precpu_stats']['cpu_usage']['total_usage']
        previousSystem = stats_json['precpu_stats']['system_cpu_usage']

        cpu_delta = stats_json['cpu_stats']['cpu_usage']['total_usage'] -\
            previousCPU
        systemDelta = stats_json['cpu_stats']['system_cpu_usage'] -\
            previousSystem

        if systemDelta > 0.0 and cpu_delta > 0.0:
            cpu_percent = (cpu_delta/systemDelta) *\
                len(stats_json[u'cpu_stats']
                    ['cpu_usage']
                    ['percpu_usage']) * 100

        return cpu_percent

    def __get_mem_percent(self, stats_json):
        if stats_json['memory_stats']['limit'] != 0:
            mem_percent = (stats_json['memory_stats']['usage'] /
                           stats_json['memory_stats']['limit']) * 100
        else:
            mem_percent = 0.0
        return round(mem_percent, 4)

    def __get_mem_usage(self, stats_json):
        return humanize.naturalsize(stats_json['memory_stats']['usage'])

    def __get_network_usage(self):
        pid = CLI.inspect_container(self.container_name)['State']['Pid']
        ret = subprocess.check_output('cat /proc/%s/net/dev' % pid, shell=True)
        mn_ifaces = ret.splitlines()[3:-1]
        mn_ifaces = [i.strip().split() for i in mn_ifaces]
        # stats = {h1-eth0:{rx:0, tx:0}, ...}
        stats_pkt = {}
        stats_bytes = {}
        for _mn in mn_ifaces:
            dev_name = _mn[0][:-1]
            received = _mn[1:5]
            transmitted = _mn[9:13]
            stats_pkt.setdefault(dev_name, {})
            stats_bytes.setdefault(dev_name, {})
            stats_pkt[dev_name]["rx"] = received[1]
            stats_pkt[dev_name]["tx"] = transmitted[1]
            stats_bytes[dev_name]["rx"] = received[0]
            stats_bytes[dev_name]["tx"] = transmitted[0]

        return stats_pkt
