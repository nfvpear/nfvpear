define($BW 65536B/s)

// BandwidthShaper parameters
// 262144 B/s -> 2   Mb/s
// 131072 B/s -> 1   Mb/s
// 16384  B/s -> 128 Kb/s
// 7168   B/s -> 56  Kb/s

FromDevice(eth0, SNIFFER false, PROMISC true, BURST 8)
  -> ThreadSafeQueue(100000)
  -> BandwidthShaper($BW) // 1Mb
  -> ToDevice(eth1);

