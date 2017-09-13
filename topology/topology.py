#!/usr/bin/python
"""File used to create a NFV infrastructure."""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.util import dumpNodeConnections2
from mininet.log import setLogLevel
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch, Docker
from functools import partial
import sys
import json
import os
from collections import namedtuple
import subprocess

DOWNLOAD_IMAGE = False


class CustomTopo(Topo):
    """Custom topology based on a parsed file."""

    def build(self, topoFile, placements=None):
        """Used to build a topology with containers."""
        with open(topoFile) as data_file:
            data = json.load(data_file)

        defaultBw = data['links'][0]['capacity']['t-s']
        defaultDelay = '1'
        print placements
        for node in data['nodes']:
            switch = self.addSwitch('s%s' % (int(node['id']) + 1))
            if str(int(node['id']) + 1) in placements:
                # for testing purpose images won't be downloaded each time --
                # saving time
                image = subprocess.Popen("docker images --format"
                                         "\"{{.Repository}}\" | "
                                         "grep gmiotto/click", shell=True,
                                         stdout=subprocess.PIPE)
                if not image:
                    process = subprocess.Popen("docker pull gmiotto/click",
                                               shell=True,
                                               stdout=subprocess.PIPE)
                    process.wait()
                if 'pops' in node:
                    for i in range(node['pops']):
                        host = self.addHost(
                               'p%s%s' % (int(node['id']) + 1, i + 1),
                               mac='00:04:00:10:%s:%s' % (
                                str(int(node['id']) + 1).zfill(2),
                                str(i + 1).zfill(2)),
                               cls=Docker, dimage='gmiotto/click',
                               mem_limit="1g")
                        self.addLink(host,
                                     switch,
                                     bw=defaultBw,
                                     delay='%sms'
                                     % defaultDelay)
                        self.addLink(host,
                                     switch,
                                     bw=defaultBw,
                                     delay='%sms'
                                     % defaultDelay)

            host = self.addHost('h%s' % (int(node['id']) + 1),
                                ip='10.0.0.%s' % (int(node['id']) + 1),
                                mac='00:04:00:00:00:%s' % (
                                    str(int(node['id']) + 1).zfill(2)))

            # adding one host to each switch hi - si
            self.addLink(host,
                         switch, bw=defaultBw, delay='%sms' % defaultDelay)

        # links between switches
        for link in data['links']:
            self.addLink('s%s' % (int(link['source']) + 1), 's%s' % (
                         int(link['target']) + 1),
                         bw=link['capacity']['t-s'],
                         delay='%sms' % link['delay'])


# baixar imagens da internet e executa-las

def topoCreator(topoFile, networkFunctions, commandsPlacement):
    """Create and test a simple network."""
    # loading network functions
    with open(networkFunctions) as data_file:
        nf_data = json.load(data_file)

    # loading nfv placement
    with open(commandsPlacement) as data_file:
        placement_data = json.load(data_file)

    # starting the NFs
    # {host: h2, func: firewall}
    Placement = namedtuple(
        'Placement', ['type', 'instance', 'server1', 'server2'])
    placements = {}
    for i in xrange(0, len(placement_data['sfc'])):
        for node in placement_data['sfc'][i]['nodes']:
            if node['type'] == 'network-function':
                host = 'h%s' % (node['location'] + 1)
                for nf in nf_data:
                    if nf['id'] == node['nfid']:
                        print "%s executing the instance %s of a %s" % (
                                host, node['instance'], nf['type'])
                        if nf['type'] == "Load Balancer":
                            placements[host[1:]] = Placement(
                                                type=nf['type'],
                                                instance=node['instance'],
                                                server1=(node['server1'] + 1),
                                                server2=(node['server2'] + 1))
                        else:
                            placements[host[1:]] = Placement(
                                                type=nf['type'],
                                                instance=node['instance'],
                                                server1=None, server2=None)

    topo = CustomTopo(topoFile, placements)
    c0 = RemoteController('c0', ip='127.0.0.1', port=6633)
    switch = partial(OVSSwitch, protocols="OpenFlow13")
    net = Mininet(topo=topo, controller=RemoteController,
                  switch=switch, link=TCLink, autoStaticArp=True)

    net.addNAT().configDefault()

    net.controllers = [c0]

    # Dumping topology to file
    topofile = open('topology.txt', mode="w")
    output = dumpNodeConnections2(net.values())
    topofile.write(output)
    topofile.close()

    net.start()

    for host in net.hosts:
        if "h" in host.name:
            host.cmd('ethtool -K %s-eth0 tso off' % host.name)

    CLI(net)
    net.stop()

    if DOWNLOAD_IMAGE:
        os.system("sudo docker rmi gmiotto/click")
    os.system("rm topology.txt")

if __name__ == '__main__':
    if os.getuid() != 0:
        print "%s must run as root" % sys.argv[0]
        sys.exit(-1)

    if len(sys.argv) < 4:
        print "Usage: $> %s infra_topo.json network_functions.json"\
              "output_optimizer.json" %\
              sys.argv[0]
        sys.exit(1)
    # Tell mininet to print useful information
    setLogLevel('info')
    topoCreator(sys.argv[1], sys.argv[2], sys.argv[3])
