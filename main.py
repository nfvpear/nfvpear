#!/usr/bin/python
from nfvsdnapi import SFC, Pop, NFunction
# To test it, it can be used with 'topology/conf/infra-last-sw.json' and 'topology/conf/output-simple-example-NF-last-switch.json'

def load_sfcs():
    links = [
             ('h1', 's1', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s1', 's2', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s2', 'p21', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 's3', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s3', 'h3', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             # Return
             ('h3', 's3', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False}),
             ('s3', 's2', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False}),
             ('s2', 'p21', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s2', 's1', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': True}),
             ('s1', 'h1', {'src_ip': 'h3', 'dst_ip': 'h1', 'pop': False})
            ]

    pop21 = Pop('p21')

    fw = NFunction(0, "Firewall")

    nfs_pop = {fw: pop21}

    sfc = SFC(0, links, nfs_pop)

    sfc.deploy_sfc()


if __name__ == '__main__':
    load_sfcs()
