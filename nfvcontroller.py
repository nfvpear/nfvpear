#!/usr/bin/python
"""This module provides a controller for the NFV infrastructure."""
import re
import sys
import os
import paramiko
from spyne import Application, rpc, ServiceBase, Unicode
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
# from openssh_wrapper import SSHConnection
# Gets all pops informations to be able to connect to them via IP
pop_info = {}
popPattern = re.compile(r'([\w]+)-([0-9]+.[0-9]+.[0-9]+.[0-9]+)')

sshclient = paramiko.SSHClient()
sshclient.load_system_host_keys()
class NfvControllerService(ServiceBase):
    """Class that provides the RPC service for the controller."""
    @rpc(Unicode, Unicode, _returns=bool)
    def deploy(ctx, pop, nf_type="default"):
        NfvControllerService.readingTopo()
        print (pop_info[pop]['ip'])
        process = 'whoami'
        if nf_type == 'Firewall':
           process = "wget 143.54.10.37/firewall.click -O firewall.click &" #"wget 143.54.85.8/~gmiotto/firewall.click &"

        elif nf_type == 'Load Balancer':
           process = "wget 143.54.85.8/~gmiotto/load-balancer.click -O load-balancer.click &"

        elif nf_type == 'Traffic Shaper':
           process = "wget 143.54.85.8/~gmiotto/ts.click -O ts.click &"
        else:
            print "<NFV_SERVICE:deploy:28> invalid nf_type"
            return False
        try:
            sshclient.connect(pop_info[pop]['ip'])
            sshclient.exec_command(process)
            print("SSH Command executed")
            sshclient.close()
            return True
        except paramiko.ssh_exception.SSHException:
            print("SSH ERROR")
            return False

    @rpc(Unicode, Unicode, Unicode, Unicode, _returns=bool)
    def enable(ctx, pop, server1=None, server2=None, nf_type="default"):
        process = "whoami"
        if nf_type == 'Firewall':
            process = "ps -eaf | grep 'firewall' | grep -v grep | awk '{print $2}' | xargs kill -9 ; /root/Click -j4 firewall.click &"
        elif nf_type == 'Load Balancer':
            process = "ps -eaf | grep 'balancer' | grep -v grep | awk '{print $2}' | xargs kill -9 ; /root/Click -j4 load-balancer.click LB=%s MLB=%s S1=%s M1=%s S2=%s M2=%s &" % (pop, str(pop).zfill(2), server1,
                                  str(server1).zfill(2), server2,
                                  str(server2).zfill(2))
        elif nf_type == 'Traffic Shaper':
            process = "ps -eaf | grep 'ts.click' | grep -v grep | awk '{print $2}' | xargs kill -9 ; /root/Click -j4 ts.click &"
        else:
            print "<NFV_SERVICE:enable:45> invalid nf_type"
            return False
        try:
            sshclient.connect(pop_info[pop]['ip'])
            sshclient.exec_command(process)
            print("SSH Command executed")
            sshclient.close()
            return True
        except paramiko.ssh_exception.SSHException:
            print("SSH ERROR")
            return False

    @staticmethod
    def readingTopo():
        _file = open('topology/topo.txt', 'r')
        for line in _file:
            if 'pop:' in line:
                for conn in popPattern.findall(line):
                    pop_name = conn[0]
                    ip = conn[1]
                    pop_info.setdefault(pop_name, {})
                    pop_info[pop_name].update({'ip': ip})
        _file.close

application = Application([NfvControllerService], 'nfvsdn.api.soap',
                          in_protocol=Soap11(validator='lxml'),
                          out_protocol=Soap11())

wsgi_application = WsgiApplication(application)


if __name__ == '__main__':
    if os.getuid() != 0:
        print "%s must run as root" % sys.argv[0]
        sys.exit(-1)
    import logging

    from wsgiref.simple_server import make_server

    logging.basicConfig(level=logging.INFO)
    logging.getLogger('spyne.protocol.xml').setLevel(logging.INFO)

    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server = make_server('127.0.0.1', 8000, wsgi_application)
    server.serve_forever()
