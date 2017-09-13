#!/usr/bin/python

from nfvsdnapi import *
import os
from collections import namedtuple
import json
import sys

def load_files(networkFunctions, commandsPlacement):
    #loading network functions
    with open(networkFunctions) as data_file:
        nf_data = json.load(data_file)

    #loading nfv placement
    with open(commandsPlacement) as data_file:
        placement_data = json.load(data_file)

    Placement = namedtuple( 'Placement', ['nfid', 'type', 'instance', 'server1', 'server2'])
    placements = {}
    for i in xrange(0,len(placement_data['sfc'])):
        for node in placement_data['sfc'][i]['nodes']:
            placements.setdefault(i, {})
            if node['type'] == 'network-function':
                host = 'h%s' % (node['location']+1)
                for nf in nf_data:
                    if nf['id'] == node['nfid']:
                        if nf['type'] == "Load Balancer":
                            if(host[1:] not in placements[i]):
                                placements[i][host[1:]] = []
                            placements[i][host[1:]].append(Placement(
                             nfid=nf['id'], type=nf['type'],
                             instance=node['instance'],
                             server1=(node['server1']+1),
                             server2=(node['server2']+1)))
                        else:
                            if(host[1:] not in placements[i]):
                                placements[i][host[1:]] = []
                            placements[i][host[1:]].append(
                             Placement(nfid=nf['id'],
                                       type=nf['type'],
                                       instance=node['instance'],
                                       server1=None,
                                       server2=None))
    return placements


def graph_parser(output_optimizer):
    elist = {}
    # loading nfv placement
    with open(output_optimizer) as data_file:
        placement_data = json.load(data_file)
    for nf in placement_data['sfc']:
        elist.setdefault(nf['id'], [])
        # necessary to check wheter a path has a split
        # Adds host to list in the begining
        for link in nf['links']:
            for pos in link['position']:
                firsthost = "h%s" % (pos['source']+1)
                dst = "s%s" % (pos['source']+1)
                break
        elist[nf['id']].append((firsthost, dst)) if (firsthost, dst) not in elist else Noneprint(elist)
        for link in nf['links']:
            for pos in link['position']:
                src = "s%s" % (pos['source']+1)
                dst = "s%s" % (pos['target']+1)
                endhost = "h%s" % (pos['target']+1)
                elist[nf['id']].append((src, dst)) if (src, dst) not in elist else None
        elist[nf['id']].append((dst, endhost)) if (dst, endhost) not in elist else Noneprint(elist)
        elist[nf['id']].append((endhost, dst)) if (endhost, dst) not in elist else Noneprint(elist)
        for link in nf['links']:
            for pos in reversed(link['position']):
                src = "s%s" % (pos['source']+1)
                dst = "s%s" % (pos['target']+1)
                elist[nf['id']].append((dst, src)) if (dst, src) not in elist else Noneprint(elist)
        elist[nf['id']].append((src, firsthost )) if (src, firsthost) not in elist else Noneprint(elist)
    return elist

def sfc_parser(network_fuctions, output_exemplo):
    #loading network functions
    network_functions = {}
    paths = {}
    pops = {}
    nodes = {}
    with open(network_fuctions) as data_file:
        nf_data = json.load(data_file)
    for nf in nf_data:
        network_functions[nf['id']] = nf['type']
    # loading nfv placement
    with open(output_exemplo) as data_file:
        placement_data = json.load(data_file)
    for nf in placement_data['sfc']:
        nodes[nf['id']] = nf['nodes']
        # necessary to check wheter a path has a split
        lb_index = network_functions.values().index("Load Balancer")
        lb_indexes = []
        eps_indexes = []
        dict_node_location = {}
        for node in nodes[nf['id']]:
            # test to check if node is a lb
            if 'nfid' in node and node['nfid'] == lb_index:
                lb_indexes.append(node['id'])
            if node['type'] == 'end-point' and node['id'] != 0:
                eps_indexes.append(int(node['id']))
            dict_node_location[node['id']] = node['location']+1
        _paths = []
        path = []
        pendings = {}
        sfcs = []
        _sfc = []
        p_sfc = {}
        for link in nf['links']:
            for pos in link['position']:
                path.append('s%s' % (pos['source'] + 1))
                path.append('s%s' % (pos['target'] + 1))
            _sfc.append(dict_node_location[link['source']])
            _sfc.append(dict_node_location[link['target']])
            # if the source is in pendings it must be continued
            if link['source'] in pendings.keys():
                path = pendings.pop(link['source']) + path
                _sfc = p_sfc.pop(link['source']) + _sfc
            print _sfc
            print path
            # if the target is not 'special' it may continue
            if link['target'] not in lb_indexes+eps_indexes:
                pendings[link['target']] = sorted(
                                           set(path),
                                           key=lambda x: path.index(x))
                path = []
                p_sfc[link['target']] = sorted(
                                        set(_sfc),
                                        key=lambda x: _sfc.index(x))
                _sfc = []
                continue
            if link['target'] in lb_indexes or link['source'] in lb_indexes:
                _paths.append(sorted(set(path), key=lambda x: path.index(x)))
                path = []
                sfcs.append(sorted(set(_sfc), key=lambda x: _sfc.index(x)))
                _sfc = []
            elif link['target'] in eps_indexes:
                _paths.append(sorted(set(path), key=lambda x: path.index(x)))
                path = []
                sfcs.append(sorted(set(_sfc), key=lambda x: _sfc.index(x)))
                _sfc = []
        paths[nf['id']] = _paths
        pops.setdefault(nf['id'], {})
        for node in nf['nodes']:
            nf_list = []
            if node['type'] == 'network-function':
                if(("s%s" % (node['location']+1))in pops[nf['id']]):
                    nf_list = pops[nf['id']]["s%s" % (node['location']+1)]
                nf_list.append(network_functions[node['nfid']])
                pops[nf['id']]["s%s" % (node['location']+1)] = nf_list
    return paths, pops

def init_load(network_function, output_optimizer):
    placements = load_files(network_function, output_optimizer)
    edges = graph_parser(output_optimizer)
    paths, pops = sfc_parser(network_function, output_optimizer)
    # Iterate through each SFC
    links = []
    new_edges = {}
    for sfcId, values in placements.iteritems():
        new_edges.setdefault(sfcId, [])
        for i, _tuple in enumerate(edges[sfcId]):
            pop = False
            print(edges[sfcId])
            if i < (len(edges[sfcId]) / 2):
                src = edges[sfcId][0][0]
                dst = edges[sfcId][(len(edges[sfcId])/2 - 1)][1]
            else:
                dst = edges[sfcId][0][0]
                src = edges[sfcId][(len(edges[sfcId])/2 - 1)][1]
            if(_tuple[0] in pops[sfcId]):
                pop = True
                k = 0
                for value in pops[sfcId][_tuple[0]]:
                    k = pops[sfcId][_tuple[0]].index(value) + 1
                    ruleTuple = (_tuple[0], 'p'+str(_tuple[0][1:])+str(k),
                                 {'src_ip': src, 'dst_ip': dst, 'pop': pop})
                    links.append(ruleTuple)
            ruleTuple = (_tuple[0], _tuple[1],
                         {'src_ip': src, 'dst_ip': dst, 'pop': pop})
            links.append(ruleTuple)
        nfs_pops = {}
        nfs_pops.setdefault(sfcId, {})
        nfs_pops.setdefault(sfcId, {})
        for location, plac in values.iteritems():
            j = 0
            for pla in plac:
                j = j + 1
                _pop = Pop('p'+str(location)+str(j))
                print _pop
                _nf = NFunction(plac[j-1].nfid,
                                plac[j-1].type,
                                plac[j-1].server1,
                                plac[j-1].server2)

                nfs_pops[sfcId][_nf] = _pop
        new_edges[sfcId].append(links)
    print nfs_pops
    print(links)
    sfcs = []
    for _id, edge in new_edges.iteritems():
        print _id
        print edge
        sfcs.append(SFC(_id, edge[0], nfs_pops[_id]))
    return sfcs

def load_sfcs(network_functions, output_optimizer):
    sfcs = init_load(network_functions, output_optimizer)
    print sfcs
    for sfc in sfcs:
        print sfc
        sfc.deploy_sfc()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage:\n$.> %s functions.json output_optimizer.json" % sys.argv[0]
        sys.exit(-1)
    load_sfcs(sys.argv[1], sys.argv[2])
