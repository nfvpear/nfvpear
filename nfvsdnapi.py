"""This module provides an API for NFV deployment over a SDN infrastructure."""

import subprocess
from suds.client import Client
import networkx as nx
import copy

suds_client = Client('http://localhost:8000/?wsdl', cache=None)


class SFC(object):
    """
    A class to keep an instance of a Service Function Chaining (SFC).

    An instance has at least the following attributes.
    =========== ===============================================================
    Attribute   Description
    =========== ===============================================================
    sfc_id      An integer that represents the SFC.
    edges_list  A list of 3-tuples edges (u,v,d) where d is a dictionary
                containing {src_ip:x, dst_ip:y, pop: Bool} related to the
                source u node. This list represents the paths
                (source -> destiny, destiny -> source) of the sfc.
    nfs_pops    A dictionay of nfs and pops, in this order. Maps nfs to pops
    =========== ===============================================================
    """

    def __init__(self, sfc_id, edges_list, nfs_pops):
        self.sfc_id = sfc_id
        # self.graph = nx.DiGraph()
        self.graph = edges_list
        self.nfs_pops = nfs_pops
        self.__nf_datas = []  # class NfData
        self.__flow_enable = False
        self.__internet = False
        self.first_dict = {}
        self.pop_dict = {}

    def deploy_sfc(self):
        """
        Deploy the sfc
        """
        for nf, pop in self.nfs_pops.iteritems():
            if not self.deploy_nf(nf, pop):
                raise AttributeError("Dict nfs:pops malformed")

        if not self.deploy_flow():
            raise Exception("Error when deploying the chain")

        for nf_data in self.__nf_datas:
            ret = self.enable_nf(nf_data)
            if not ret:
                raise Exception("NF: %s couldn't be enabled",
                                nf_data.nfunction.type)

        self.enable_flow()

    def deploy_nf(self, network_function, pop):
        # if not self.__internet:
        #    self.__enable_internet()
        # deploy(pop, nf_type="default"):
        if pop.is_deployed():
            nf_data = NfData(nfunction=network_function, pop=pop, enabled=True)
            self.__nf_datas.append(nf_data)
        elif suds_client.service.deploy(pop.location, network_function.type):
            pop.add_deploy(network_function.type)
            nf_data = NfData(nfunction=network_function, pop=pop)
            self.__nf_datas.append(nf_data)
        else:
            return False
        return True

    def enable_nf(self, nf_data):
        # enable(pop, server1=None, server2=None, nf_type="default" )
        if nf_data.enabled:
            return True
        elif suds_client.service.enable(
                            nf_data.pop.location, nf_data.nfunction.server1,
                            nf_data.nfunction.server2, nf_data.nfunction.type):
            nf_data.enable()
            return True
        else:
            return False

    def deploy_flow(self):
        for edges in self.graph:
            if not self.deploy_pair(edges[0], edges[1], edges[2]):
                return False
        return True

    def enable_flow(self):
        self.__flow_enable = True

    def deploy_pair(self, src, dst, info):
        # Uses a dictionary, with information about
        # pops in the switch.
        # Eg: {s2:[(h21,'Firewall'),(h22,'TrafficShaper), ....]}

        src_ip = info["src_ip"]
        dst_ip = info["dst_ip"]
        if info["pop"]:
            # src has a POP
            if(src[:1] == 's') and (dst[:1] == 'p'):
                # It is a connection to a PoP so it saves in a dict the
                # information so it can be used to install later the rules
                # in the switch

                if src in self.pop_dict:
                    list_pop = self.pop_dict[src]
                    list_pop.append((dst, self.__get_function(dst)))

                else:
                    list_pop = []
                    nfunction = self.__get_function(dst)
                    list_pop.append((dst, nfunction))
                self.pop_dict = {src: list_pop}
                return True

            if(src[:1] == 's') and ((dst[:1] == 's') or (dst[:1] == 'h')):
                # Source is connected to the pop we saved in the dict
                # so it needs to pass the list of pops connected to
                # this switch to install the rules

                if src in self.pop_dict:
                    # Pop is this string [('h2','Firewall')]
                    # It need to pass in a way that works with curl
                    popString = ""
                    for pop in self.pop_dict[src]:
                        # Removes white space so it can use cURL
                        nfString = pop[1].replace(" ", "")
                        popString = popString + pop[0] + '_'+nfString+'!'
                    popString = popString[:-1]
                    if('fromLB' not in info):
                        del self.pop_dict[src]
                    # See if is the returning from servers when using LB
                    if('fromLB' in info and (src_ip[1:] == src[1:])):
                        popString = pop[0] + '_'+"returnLB"

                    url = "curl -i http://localhost:8080/sfcforwarding/"\
                          "deploy_pair_pop"\
                          "-sfc_id=%s-src=%s-dst=%s-dst_ip=%s-pop_type=%s" % \
                          (self.sfc_id, src, dst, dst_ip, popString)
                else:
                    return False
            else:
                return False
        else:
            # Test if it is the first connection in the SFC
            first = True if src_ip == src else False
            if(first is True):
                # Puts in a dictionary the information that it will be
                # used in the next link to install the rules in the switch
                self.first_dict = {dst: src}
                return True
            if(src in self.first_dict):
                # In this link it will see that it is connected to the
                # first Host, so it gets the name of the host and passes
                # in the url to the sfc_forwarding, so rules can be installed
                first_host = self.first_dict[src]
                # Deletes the key, so other connections involving that switch
                # wont give any problem
                del self.first_dict[src]
            else:
                first_host = 'no'
            last_lb = self.__is_lb(dst[1:])  # must pass the locations
            url = "curl -i http://localhost:8080/sfcforwarding/deploy_pair" \
                  "-sfc_id=%s-src=%s-dst=%s-dst_ip=%s-first=%s-last_lb=%s" % \
                  (self.sfc_id, src, dst, dst_ip, first_host, last_lb)
        print(url)
        if subprocess.Popen(url, shell=True,
                            stdout=subprocess.PIPE).wait() == 0:
            return True
        else:
            return False

    def get_nf_data(self):
        return copy.deepcopy(self.__nf_datas)

    def __get_function(self, pop):
        for nfdata in self.__nf_datas:
            if nfdata.pop.location == pop:
                return nfdata.nfunction.type
        return None

    def __is_lb(self, _pop):
        pop = int(_pop)
        if Pop.deployed.has_key(pop):
            function = Pop.deployed[pop]
            if function == "Load Balancer":
                return True
            else:
                return False
        else:
            return False

class NfData:
    """
    A class to keep track of a deployed Network Function in a Pop.

    An instance has at least the following attributes.
    ========== ================================================================
    Attribute  Description
    ========== ================================================================
    nfunction  An instance of the NFunction class
    pop        An instance of the Pop class
    enabled    A boolean to keep status of the Network function
    ========== ================================================================

    """

    def __init__(self, nfunction, pop, enabled=False):
        self.nfunction = nfunction
        self.pop = pop
        self.enabled = enabled

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def __str__(self):
        return "An instance of NfData with state: nfunction=%s\n\
                pop=%s\nenabled=%s" % \
                (self.nfunction, self.pop, self.enabled)


class NFunction:
    """
    A class to keep track of an instance of a Network Function.

    An instance has at least the following attributes:
    ============ ==============================================================
    Attribute    Description
    ============ ==============================================================
    nf_id        Id of the network function
    type         A string with the network function type (ex. "Load Balancer")
    server1      (Default: False) - The server 1 of a nf type load balancer
    server2      (Default: False) - The server 2 of a nf type load balancer
    requirements (Default: None) - Not implemented yet
    ============ ==============================================================

    """

    def __init__(self, nf_id, _type, server1=None, server2=None,
                 requirements=None):
        self.nf_id = nf_id
        self.type = _type
        self.server1 = server1
        self.server2 = server2
        self.requirements = requirements

    def __str__(self):
        return "An instance of NFunction with state: nf_id=%s\ntype=%s\n"\
                "server1=%s\nserver2=%s" % \
                (self.nf_id, self.type, self.server1, self.server2)


class NfRequirements:
    """
    NOT IMPLEMENTED YET.

    A class to keep track of an instance of a Network Function Requirements

    An instance has at least the following attributes.
    ========== ================================================================
    Attribute  Description
    ========== ================================================================
    cpu        Minimum cpu necessary
    bandwidth  Minimum bandwidth necessary
    memory     Minimum memory necessary
    in_out     Minimum I/O necessary
    ========== ================================================================

    """

    def __init__(self, cpu, bandwidth, memory, in_out=None):
        self.cpu = cpu
        self.bandwidth = bandwidth
        self.memory = memory
        self.in_out = in_out


class Pop:
    """
    A class to keep track of an instance of a Point-of-presence.

    An instance has at least the following attributes.
    ========== ================================================================
    Attribute  Description
    ========== ================================================================
    pop_id     Id of the pop
    location   Switch id where the pop is attached
    resources  (Default: None) - Not implemented yet
    ========== ================================================================

    """

    deployed = {}

    def __init__(self, location, resources=None):
        self.pop_id = location
        self.location = location
        self.resources = resources

    def add_deploy(self, function):
        Pop.deployed[self.location] = function

    def is_deployed(self):
        if Pop.deployed.has_key(self.location):
            return True
        else:
            return False

    def __str__(self):
        return "An instance of Pop with state: pop_id=%s\nlocation=%s" % \
                (self.pop_id, self.location)


class PopResources:
    """
    NOT IMPLEMENTED.

    A class to keep track of an instance of a Point-of-presence resources

    An instance has at least the following attributes.
    ========== ================================================================
    Attribute  Description
    ========== ================================================================
    cpu        Maximum cpu available
    bandwidth  Maximum bandwidth available
    memory     Maximum memory available
    ========== ================================================================

    """

    def __init__(self, cpu, bandwidth, memory):
        self.cpu = cpu
        self.bandwidth = bandwidth
        self.memory = memory
