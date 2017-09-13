// load Balancer
define($S1 10, $M1 10, $S2 20, $M2 20, $LB 2, $MLB 02)

AddressInfo(
  SERVER1 10.0.0.$S1 00:00:00:00:00:$M1,
  SERVER2 10.0.0.$S2 00:00:00:00:00:$M2,
  LB_IP   10.0.0.$LB 00:00:00:00:00:$MLB
)
 // 'pattern SADDR SPORT DADDR DPORT FOUTPUT ROUTPUT'
r :: RoundRobinIPMapper(- - SERVER1 - 0 1, - - SERVER2 - 0 1);
to_eth1 :: Queue(10000) -> ToDevice(eth1);

icprw :: ICMPPingRewriter(pattern - SERVER1 0-65535 0 0, pattern - SERVER2 0-65535 1 1);
rw :: IPRewriter(r);
icerw :: ICMPRewriter(rw icprw);

FromDevice(eth0, SNIFFER false, PROMISC true, BURST 8)
  -> Classifier(12/0800)
  -> CheckIPHeader(OFFSET 14)
  -> cl :: IPClassifier(dst host LB_IP and ip proto udp or tcp,
                        dst host != LB_IP and ip proto udp or tcp,
                        icmp type echo or echo-reply,
                  	proto icmp );

  cl[0] -> [0]rw;
  cl[1] -> [0]rw;
  cl[2] -> rb :: RandomSwitch;
  cl[3] -> [0]icerw;


  rb[0] -> [0]icprw;
  rb[1] -> [1]icprw;


  // going to servers
  rw[0] -> to_eth1;
  // return from servers
  rw[1] -> to_eth1;

  icprw[0] -> to_eth1;
  icprw[1] -> to_eth1;
  icerw[0] -> to_eth1;  
