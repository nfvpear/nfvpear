#!/usr/bin/python
from nfvsdnapi import SFC, Pop, NFunction


def load_sfcs():
    links = [
             ('h1', 's1', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s1', 's2', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s2', 'p21', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p22', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 's3', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s3', 'h3', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('h3', 's3', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False}),
             ('s3', 's2', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False}),
             ('s2', 'p22', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p21', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 's1', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s1', 'h1', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False}),
            ]

    pop21 = Pop('p21')
    pop22 = Pop('p22')

    fw = NFunction(0, "Firewall")
    ts = NFunction(2, "Traffic Shaper")
    nfs_pop = {fw: pop21, ts: pop22}

    sfc = SFC(0, links, nfs_pop)

    sfc.deploy_sfc()


if __name__ == '__main__':
    load_sfcs()
