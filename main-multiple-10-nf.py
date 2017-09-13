#!/usr/bin/python
from nfvsdnapi import SFC, Pop, NFunction


def load_sfcs():
    links = [
             ('h1', 's1', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s1', 's2', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': False}),
             ('s2', 'p21', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p22', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p23', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p24', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p25', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p26', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p27', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p28', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p29', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
             ('s2', 'p210', {'src_ip': 'h1', 'dst_ip': 'h3', 'pop': True}),
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
    pop23 = Pop('p23')
    pop24 = Pop('p24')
    pop25 = Pop('p25')
    pop26 = Pop('p26')
    pop27 = Pop('p27')
    pop28 = Pop('p28')
    pop29 = Pop('p29')
    pop210 = Pop('p210')

    fw1 = NFunction(0, "Firewall")
    ts2 = NFunction(2, "Traffic Shaper")
    fw3 = NFunction(0, "Firewall")
    ts4 = NFunction(2, "Traffic Shaper")
    fw5 = NFunction(0, "Firewall")
    ts6 = NFunction(2, "Traffic Shaper")
    fw7 = NFunction(0, "Firewall")
    ts8 = NFunction(2, "Traffic Shaper")
    fw9 = NFunction(0, "Firewall")
    ts10 = NFunction(2, "Traffic Shaper")
    nfs_pop = {fw1: pop21, ts2: pop22,
               fw3: pop23, ts4: pop24,
               fw5: pop25, ts6: pop26,
               fw7: pop27, ts8: pop28,
               fw9: pop29, ts10: pop210
               }

    sfc = SFC(0, links, nfs_pop)

    sfc.deploy_sfc()


if __name__ == '__main__':
    load_sfcs()
