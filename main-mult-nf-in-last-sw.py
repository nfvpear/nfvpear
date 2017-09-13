#!/usr/bin/python
from nfvsdnapi import SFC, Pop, NFunction


def load_sfcs():
    links = [
             ('h1', 's1', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s1', 's2', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s2', 's3', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s3', 'p31', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s3', 'p32', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s3', 'h3', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('h3', 's3', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False}),
             ('s3', 'p32', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s3', 'p31', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s3', 's2', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s2', 's1', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False}),
             ('s1', 'h1', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False}),
            ]

    pop31 = Pop('p31')
    pop32 = Pop('p32')
    fw = NFunction(0, "Firewall")
    ts = NFunction(2, "Traffic Shaper")

    nfs_pop = {fw: pop31, ts: pop32}

    sfc = SFC(0, links, nfs_pop)

    sfc.deploy_sfc()


if __name__ == '__main__':
    load_sfcs()
