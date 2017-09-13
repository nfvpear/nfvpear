"""SDN controller for the infrastructure."""

from ryu.base import app_manager
from ryu.controller import ofp_event, dpset
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3, ether
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4, arp, lldp
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
import re
import networkx as nx
import ast
from webob import Response

ARP = arp.arp.__name__
IPV4 = ipv4.ipv4.__name__
UINT32_MAX = 0xffffffff

sfc_forwarding_instance_name = 'sfc_forwarding_api_app'
url = '/sfcforwarding/{method}'


class SFCForwardingAPI(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset': dpset.DPSet,
        'wsgi': WSGIApplication
    }

    def __init__(self, *args, **kwargs):
        super(SFCForwardingAPI, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(SFCForwardingController,
                      {sfc_forwarding_instance_name: self})

        self.mac_to_port = {}
        self.dpset = kwargs['dpset']
        self.dp_dict = {}   # dictionary of datapaths
        self.elist = []  # edges list to the graph
        self.edges_ports = {}   # dictionary that maps switches conn with ports
        self.parse_graph()      # to populates the previous variables
        self.graph = nx.MultiGraph()    # create the graph
        self.graph.add_edges_from(self.elist)   # add edges to the graph

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        dpid = datapath.id

        self.dp_dict[dpid] = datapath
        # install table-miss flow entry
        # dropping unknown flows
        match = parser.OFPMatch()
        actions = []
        self.add_flow(datapath, 0, match, actions)

        # flow mod to block ipv6 traffic (annoying and not related to the work)
        match = parser.OFPMatch(eth_type=0x86dd)
        actions = []
        self.add_flow(datapath, ofproto.OFP_DEFAULT_PRIORITY, match, actions)

        self.logger.debug("<switch_features_handler> dpid %s done!", dpid)

    def add_flow(self, datapath, priority, match, actions=None, buffer_id=None,
                 instruction=[]):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = []
        if not instruction:
            inst.append(parser.OFPInstructionActions(
                                            ofproto.OFPIT_APPLY_ACTIONS,
                                            actions))
        else:
            if actions:
                inst.append(parser.OFPInstructionActions(
                                            ofproto.OFPIT_APPLY_ACTIONS,
                                            actions))
            inst = inst + instruction

        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    # Simple switch packet in function
    # Not used by this controller
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        if pkt.get_protocol(lldp.lldp):
            return
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        ip = pkt.get_protocol(ipv4.ipv4)
        p_arp = pkt.get_protocol(arp.arp)

        header_list = dict((p.protocol_name, p)
                           for p in pkt.protocols if type(p) != str)

        ipv4_src = ip.src if ip is not None else p_arp.src_ip
        ipv4_dst = ip.dst if ip is not None else p_arp.dst_ip

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.mac_to_port[dpid][src] = in_port

        if ARP in header_list:
            self.logger.info("ARP packet in s%s, src: %s, dst: %s,\
                             in_port: %s", dpid, src, dst,
                             in_port)
        else:
            self.logger.info("packet in s%s, src: %s, dst: %s,\
                             in_port: %s", dpid, ipv4_src,
                             ipv4_dst, in_port)

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)

    def send_arp(self, datapath, arp_opcode, src_mac, dst_mac,
                 src_ip, dst_ip, arp_target_mac, in_port, output):
        """
        Function that create and sends arp message.

        Args: datapath: datapath of the switch,
              arp_opcode: ARP_TYPE
              src_mac, dst_mac: ethernet addresses
              src_ip, dst_ip: ipv4 addresses
              arp_target_mac: ethernet addr to be the answer in arp reply
              in_port: port were entered the packet,
              output: out_port to send the packet
        """
        ether_proto = ether.ETH_TYPE_ARP
        hwtype = 1
        arp_proto = ether.ETH_TYPE_IP
        hlen = 6
        plen = 4

        pkt = packet.Packet()
        e = ethernet.ethernet(dst_mac, src_mac, ether_proto)
        a = arp.arp(hwtype, arp_proto, hlen, plen, arp_opcode,
                    src_mac, src_ip, arp_target_mac, dst_ip)
        pkt.add_protocol(e)
        pkt.add_protocol(a)
        pkt.serialize()

        actions = [datapath.ofproto_parser.OFPActionOutput(output)]

        datapath.send_packet_out(in_port=in_port, actions=actions,
                                 data=pkt.data)

    def deploy_pair_pop(self, sfc_id, _src, _dst, _dst_ip, pops=[]):
        # pops it is a list of tuples, with information about
        # pops in the switch. Eg: For one switch the info can be is
        # [('h21','Firewall'),('h22','TrafficShaper')]
        # so it is possible to support multiple pops in one switch
        src = _src[1:]
        dst = _dst[1:]
        dst_ip = _dst_ip[1:]
        dpid = int(src)
        datapath = self.dp_dict[dpid]
        parser = datapath.ofproto_parser
        eth_dst = "00:04:00:00:00:%s" % str(dst_ip).zfill(2)
        ip_dst = "10.0.0.%s" % dst_ip
        # Iterates through each pop so it install all rules regarding pops on
        # that switch with multiple pops
        # Test for in case it is not multiple pops
        if (len(pops) > 1):
            for pop in pops:
                if pop[1] == "Firewall" or pop[1] == "TrafficShaper":
                    #  send to the firewall through one port and returns on
                    # another
                    # Also it needs to test if it is the last pop of the
                    # multiple pops because then the output should be
                    # the next switch, not the next pop
                    lastindex = (len(pops) - 1)
                    if(pops[lastindex] == pop):
                        lastPop = True
                    else:
                        lastPop = False
                    if(pops[0] == pop):
                        firstPop = True
                    else:
                        firstPop = False
                    nextPop = (pops.index(pop)+1)
                    if (firstPop is True):
                        # The output will be the the port which is connected to
                        # the next pop
                        out_port = self.edges_ports[
                                   's%s' % dpid][(pops[nextPop][0])]['in_port']
                        nf_1port = self.edges_ports[
                                   's%s' % dpid][pop[0]]['in_port']
                        nf_2port = self.edges_ports[
                                   's%s' % dpid][pop[0]]['out_port']
                        # enters the nf
                        match = parser.OFPMatch(
                         eth_type=0x0800, ipv4_dst=ip_dst, ip_dscp=sfc_id)
                        action = [parser.OFPActionOutput(int(nf_1port))]
                        self.add_flow(
                         datapath=datapath, priority=1024, match=match,
                         actions=action)
                        # leaves the nf
                        match1 = parser.OFPMatch(
                         in_port=nf_2port, eth_type=0x0800,
                         ipv4_dst=ip_dst, ip_dscp=sfc_id)
                        action1 = [parser.OFPActionOutput(int(out_port))]
                        # To the next pop
                        self.add_flow(
                          datapath=datapath, priority=1096, match=match1,
                          actions=action1)
                    elif(lastPop is True):
                        # out_port is the port connecting to the next switch
                        if(_src[:1] == 's') and (_dst[:1] == 'h'):
                            out_port = self.edges_ports[
                                       's%s' % dpid]['h%s' % dst]['out_port']
                        else:
                            out_port = self.edges_ports[
                                       's%s' % dpid]['s%s' % dst]['out_port']
                        nf_2port = self.edges_ports[
                                   's%s' % dpid][pop[0]]['out_port']
                        # Rule to enter the NF was already created
                        # by the previous pop, so it only needs the rule
                        # to leave NF to next switch
                        match1 = parser.OFPMatch(
                         in_port=nf_2port, eth_type=0x0800,
                         ipv4_dst=ip_dst, ip_dscp=sfc_id)
                        action1 = [parser.OFPActionOutput(int(out_port))]
                        # To the next switch
                        self.add_flow(
                         datapath=datapath, priority=1096, match=match1,
                         actions=action1)
                    else:
                        # The output will be the the port which is connected to
                        # the next pop
                        out_port = self.edges_ports[
                                   's%s' % dpid][(pops[nextPop][0])]['in_port']
                        nf_2port = self.edges_ports[
                                   's%s' % dpid][pop[0]]['out_port']

                        # Rule to enter the NF was already created by the prev
                        # pop, so it only needs the rule to leave NF to nxt pop
                        match1 = parser.OFPMatch(
                         in_port=nf_2port, eth_type=0x0800,
                         ipv4_dst=ip_dst, ip_dscp=sfc_id)
                        action1 = [parser.OFPActionOutput(int(out_port))]
                        # To the next pop
                        self.add_flow(
                         datapath=datapath, priority=1096, match=match1,
                         actions=action1)
        # it is just one pop
        else:
            pop = pops[0]
            if pop[1] == "Firewall" or pop[1] == "TrafficShaper":
                #  send to the firewall through one port and returns on
                # another
                    # The output will be the the next switch or host
                    # Test if it is the last switch
                    if(_src[:1] == 's') and (_dst[:1] == 'h'):
                        out_port = self.edges_ports[
                                   's%s' % dpid]['h%s' % dst]['out_port']
                    else:
                        out_port = self.edges_ports['s%s' % dpid][
                                   's%s' % dst]['out_port']

                    nf_1port = self.edges_ports[
                               's%s' % dpid][pop[0]]['in_port']
                    nf_2port = self.edges_ports[
                               's%s' % dpid][pop[0]]['out_port']
                    # enters the nf
                    match = parser.OFPMatch(
                     eth_type=0x0800, ipv4_dst=ip_dst, ip_dscp=sfc_id)
                    action = [parser.OFPActionOutput(int(nf_1port))]
                    self.add_flow(
                     datapath=datapath, priority=1024, match=match,
                     actions=action)
                    # leaves the nf
                    match1 = parser.OFPMatch(
                     in_port=nf_2port, eth_type=0x0800,
                     ipv4_dst=ip_dst, ip_dscp=sfc_id)
                    action1 = [parser.OFPActionOutput(int(out_port))]
                    # To the next pop
                    self.add_flow(
                      datapath=datapath, priority=1096, match=match1,
                      actions=action1)

            elif pop[1] == "LoadBalancer":
                out_port = self.edges_ports[
                           's%s' % dpid]['s%s' % dst]['out_port']
                nf_1port = self.edges_ports['s%s' % dpid][pop[0]]['in_port']
                nf_2port = self.edges_ports['s%s' % dpid][pop[0]]['out_port']

                # enters the nf
                match = parser.OFPMatch(
                        eth_type=0x0800, ipv4_dst="10.0.0.%s" % src,
                        ip_dscp=sfc_id)

                action = [parser.OFPActionOutput(int(nf_1port))]
                self.add_flow(datapath=datapath, priority=1024, match=match,
                              actions=action)
                # leaves the nf
                match = parser.OFPMatch(in_port=nf_2port, eth_type=0x0800,
                                        ipv4_dst=ip_dst, ip_dscp=sfc_id)
                action = [parser.OFPActionSetField(eth_dst=eth_dst)]
                action.append(parser.OFPActionOutput(int(out_port)))
                self.add_flow(datapath=datapath, priority=1096, match=match,
                              actions=action)
            elif (pop[1] == "returnLB"):
                # enters the nf

                out_port = self.edges_ports[
                           's%s' % dpid]['s%s' % dst]['out_port']
                nf_1port = self.edges_ports['s%s' % dpid][pop[0]]['in_port']
                nf_2port = self.edges_ports['s%s' % dpid][pop[0]]['out_port']

                # enters the nf
                match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=ip_dst,
                                        ip_dscp=sfc_id)

                action = [parser.OFPActionOutput(int(nf_1port))]
                self.add_flow(datapath=datapath, priority=1024, match=match,
                              actions=action)
                # leaves the nf
                match = parser.OFPMatch(in_port=nf_2port, eth_type=0x0800,
                                        ipv4_dst=ip_dst, ip_dscp=sfc_id)
                action = [parser.OFPActionSetField(eth_dst=eth_dst)]
                action.append(parser.OFPActionOutput(int(out_port)))
        self.add_flow(
             datapath=datapath, priority=1096, match=match, actions=action)

    def deploy_pair(self, sfc_id, _src, _dst, _dst_ip, first,
                    last_lb=False):
        """Method used to deploy a flow on switch src with destination dst."""
        src = _src[1:]
        dst = _dst[1:]
        dst_ip = _dst_ip[1:]
        dpid = int(src)
        datapath = self.dp_dict[dpid]
        parser = datapath.ofproto_parser
        ip_dst = "10.0.0.%s" % dst_ip
        actions = []
        if(_src[:1] == 's') and (_dst[:1] == 's'):
            if last_lb:
                match1 = parser.OFPMatch(eth_type=0x0800, ipv4_dst=ip_dst,
                                         ip_dscp=sfc_id)
                action = [parser.OFPActionOutput(int(
                          self.edges_ports[
                               "s%s" % dpid]["s%s" % dst]['out_port']))]
                dp_host = self.dp_dict[int(dst)]
                self.add_flow(datapath=dp_host, priority=1024, match=match1,
                              actions=action)
            # Test to see if it is the fisr switch connected to src
            elif first == 'no':
                # So it is a simple conection between two switches not
                # connected with any host or pop
                match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=ip_dst,
                                        ip_dscp=sfc_id)
                actions.append(parser.OFPActionOutput(int(
                               self.edges_ports[
                                    "s%s" % dpid]["s%s" % dst]['out_port'])))
                self.add_flow(datapath=datapath, priority=1024, match=match,
                              actions=actions)
            else:
                # The variable 'first' will have the name of the src host
                # connected to the switch so it can know in which port it
                # connects so it can create the rules
                # First switch (match without sfc-tag)
                out_port = self.edges_ports[
                           "s%s" % dpid]["s%s" % dst]['out_port']
                match = parser.OFPMatch(eth_type=0x0800,
                                        ipv4_dst=ip_dst)
                actions.append(parser.OFPActionSetField(ip_dscp=sfc_id))
                actions.append(parser.OFPActionOutput(int(out_port)))
                self.add_flow(datapath=datapath, priority=1024, match=match,
                              actions=actions)

        elif(_src[:1] == 's') and (_dst[:1] == 'h'):
            match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=ip_dst,
                                    ip_dscp=sfc_id)
            actions.append(parser.OFPActionOutput(int(
                           self.edges_ports[
                                "s%s" % dpid]["h%s" % dst]['out_port'])))
            self.add_flow(datapath=datapath, priority=1024, match=match,
                          actions=actions)

    def parse_graph(self):
        """Descr: Function that parser the topology.txt into a graph."""
        _file = open('topology/topo.txt', 'r')
        regPattern = re.compile(r'link: ([\w]+)-eth([0-9]+):([\w]+)-eth[0-9]+')
        linkPattern = re.compile(r'([\w]+)-eth([0-9]+):([\w]+)-eth[0-9]+')
        for line in _file:
            if "link:" in line:
                refnode = (regPattern.match(line)).group(1)
                self.edges_ports.setdefault(refnode, {})
        _file.close
        _file = open('topology/topo.txt', 'r')
        for line in _file:
            if "link:" in line:
                for conn in linkPattern.findall(line):
                    link_src = conn[0]
                    link_dst = conn[2]
                    inp = conn[1]
                    outp = conn[1]
                    # Tests if it already created the link (only Pops will
                    # have more then one link with the same dst and src)
                    if link_dst not in self.edges_ports[link_src]:
                        self.edges_ports[
                         link_src].update(
                         {link_dst: {'in_port': int(inp),
                          'out_port': int(outp)}})
                    # If it is a pop, it needs to change the out_port for the
                    # port of the connection of the other interface
                    else:
                        inp = self.edges_ports[link_src][link_dst]['in_port']
                        outp = conn[1]
                        self. edges_ports[
                         link_src].update(
                         {link_dst: {'in_port': int(inp),
                          'out_port': int(outp)}})


class SFCForwardingController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(SFCForwardingController, self).__init__(
                    req, link, data, **config)
        self.sfc_forwarding_spp = data[sfc_forwarding_instance_name]

    @route('sfcforwarding', url, methods=['GET'],
           requirements={'method': r"inet-pops=[\d,]+"})
    def enable_inet(self, req, **kwargs):
        options = kwargs['method'].split('=')
        pops = [int(pop) for pop in options[1].split(',')]
        self.sfc_forwarding_spp.enable_inet_pop(pops)
        return Response(status=200)

    # "curl -X GET http://localhost:7070/sfcforwarding/deploy_pair" \
    #      "-sfc_id=%s-src=%s-dst=%s-dst_ip=%s-first=%s-last=%s" % \
    @route('sfcforwarding', url, methods=['GET'], requirements={'method':
           r"deploy_pair-sfc_id=\w+-src=\w+-dst=\w+-dst_ip=\w+"\
           "-first=\w+-last_lb=\w+"})
    def deploy_pair(self, req, **kwargs):
        options = kwargs['method'].split('-')
        sfc_id = int(options[1].split('=')[1])
        src = options[2].split('=')[1]
        dst = options[3].split('=')[1]
        dst_ip = options[4].split('=')[1]
        first = options[5].split('=')[1]
        last_lb = ast.literal_eval(options[6].split('=')[1])
        self.sfc_forwarding_spp.deploy_pair(sfc_id, src, dst,
                                            dst_ip, first, last_lb)
        return Response(status=200)

    # "curl -X GET http://localhost:7070/sfcforwarding/deploy_pair_pop" \
    #      "-sfc_id=%s-src=%s-dst=%s-dst_ip=%s-pop_type=%s" % \
    # def deploy_pair_pop(self, sfc_id, src, dst, dst_ip, last, pop_type):
    @route('sfcforwarding', url, methods=['GET'], requirements={'method':
           r"deploy_pair_pop-sfc_id=\w+-src=\w+-dst=\w+-dst_ip=\w+"\
            "-pop_type=.+"})
    # pop type is [(h21,'Firewall'),(h22,'TrafficShaper) ...]
    # so it needs to match that, and for that we use .+
    # to match anything after the last =
    def deploy_pair_pop(self, req, **kwargs):
        options = kwargs['method'].split('-')
        sfc_id = int(options[1].split('=')[1])
        src = options[2].split('=')[1]
        dst = options[3].split('=')[1]
        dst_ip = options[4].split('=')[1]
        pop_type_str = options[5].split('=')[1]
        pop_type = []
        for pop in pop_type_str.split('!'):
            pop_data = pop.split('_')
            pop_type.append((pop_data[0], pop_data[1]))
        self.sfc_forwarding_spp.deploy_pair_pop(sfc_id, src, dst,
                                                dst_ip, pop_type)
        return Response(status=200)
