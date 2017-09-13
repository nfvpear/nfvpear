// You can run it at user level (as root) as
// 'userlevel/click < conf/Print-pings.click'
// or in the kernel with
// 'click-install conf/Print-pings.click'

FromDevice(eth0, SNIFFER false, PROMISC true, BURST 8)	// read packets from device
   -> pkt :: Classifier(12/0800, -)
   -> ck :: CheckIPHeader(OFFSET 14)
   -> IPFilter( allow icmp,
		 allow tcp && dst port 8000 || src port 8000,	
		allow tcp && dst port 5001 || src port 5001,	
		allow udp && dst port 5001 || src port 5001,
		allow tcp && dst port 5201 || src port 5201,
    		allow udp && dst port 11111 || src port 11111,
    		allow tcp && dst port 8080 || src port 8080,
		drop all)
   -> queue :: ThreadSafeQueue(10000)
   pkt[1] -> queue
   ck[1] -> queue
   -> ToDevice(eth1, BURST 8);

