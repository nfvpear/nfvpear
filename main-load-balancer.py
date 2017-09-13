#!/usr/bin/python
from nfvsdnapi import SFC, Pop, NFunction


def load_sfcs():
    links = [
             # Path to load balancer
             ('h1', 's1', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s1', 's2', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s2', 'p21', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 's3', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s3', 'p31', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             # Path 1
             ('s3', 's4', {'src_ip': 'h1', 'dst_ip': 'h5', 'pop': True, 'fromLB': True}),
             ('s4', 's5', {'src_ip': 'h1', 'dst_ip': 'h5', 'pop': False}),
             ('s5', 'h5', {'src_ip': 'h1', 'dst_ip': 'h5', 'pop': False}),
             # Path 2
             ('s3', 's6', {'src_ip': 'h1', 'dst_ip': 'h7', 'pop': True, 'fromLB': True}),
             ('s6', 's7', {'src_ip': 'h1', 'dst_ip': 'h7', 'pop': False}),
             ('s7', 'h7', {'src_ip': 'h1', 'dst_ip': 'h7', 'pop': False}),

             # Return of packets
             ('h7', 's7', {'src_ip': 'h7', 'dst_ip': 'h1', 'pop': False}),
             ('s7', 's6', {'src_ip': 'h7', 'dst_ip': 'h1', 'pop': False}),
             ('s6', 's3', {'src_ip': 'h7', 'dst_ip': 'h1', 'pop': False}),

             ('h5', 's5', {'src_ip': 'h5', 'dst_ip': 'h1', 'pop': False}),
             ('s5', 's4', {'src_ip': 'h5', 'dst_ip': 'h1', 'pop': False}),
             ('s4', 's3', {'src_ip': 'h5', 'dst_ip': 'h1', 'pop': False}),

             ('s3', 'p31', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s3', 's2', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True, 'fromLB': True}),
             ('s2', 'p21', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s2', 's1', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s1', 'h1', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False})



             ]

    pop2 = Pop('p21')
    pop3 = Pop('p31')
    fw = NFunction(0, "Firewall")
    lb = NFunction(1, "Load Balancer", 5, 7)

    nfs_pop = {fw: pop2, lb: pop3}

    sfc = SFC(0, links, nfs_pop)

    sfc.deploy_sfc()


if __name__ == '__main__':
    load_sfcs()
