**User Guide**

*How to Set Up Main.py?*

Main.py needs to be set following some rules. In general, the user needs to define
the links used in each SFC and a dictionary containing the Pops saying which network
function they represent and where they are located.

*Configuring Links*

The links needs to be set accordingly to these example:
* [link1,link2,link3 ...]
* Each link needs to be set in this way:
  * (name of host or switch source (string), name of host, pop or switch destiny (string), link_info)
  * Each link_info needs to be set this way:
    * {'src_ip': host source, 'dst_ip': host destiny, 'pop': True or False}
    * 'pop' is True when the 'switch source' is connected to a pop otherwise it is False
* Switches are named  's1', 's2' ,'s(n)'
* Hosts are named 'h1', 'h2', ....
* Host 'h1' should be the host connected to 's1'
* Pops are named as id of the switch it is connected plus and index beginning with 1, starting with a 'p'
  * Eg. For a Pop connected to switch 's2', the name should be 'p2' + index, so it is 'p21'
* In each link after a link that connects to a pop you shouldn't put the link of the packet coming back from the pop. So for example, if a packet goes trough h1, s1, s2, a pop,s3 and h3, you should only make the link (s2 - pop) and (s2 - s3) -  NOT (pop - s2).

*Configuring Pops and Network Functions*

* You need to set the pops you will use in the links.
* You need to create a dictionary containing the Pops relating to which Network Function they will be executing.
* First, you need to create a Pop. Just use Pop(name of the pop (string)). So, if you used in the links a pop called 'p21', you need to create it as Pop('p21') and set to a variable.
* After creating all the pops, you need to create the Network Functions so you can relate the Pops with them. To create a Network function just use NFunction(0, "Firewall"), for a firewall for example.
* Finally, create the dictionary relating each Pop with its respective Network Function.

*Creating the SFC and Deploying*

* After all variables are created you need to create and deploy the corresponding SFC. To create a SFC just use SFC(0, links, nfs_pop), where 'links' are the links previously created and and 'nfs_pop' is the dictionary.
* To deploy just use sfc.deploy_sfc(), where 'sfc' is the SFC previously created.
* Full examples can be seen in main.py and others 'main' python files created in 'examples' folder.

*Configuring Main.py to use Load Balancer*

* When using a Load Balancer a few changes need to be made in the 'links'. You will need to add in the 'link_info' another key ('fromLB': True), in first links that the Load Balancer splits the path where it will balance the Load (so, in each beginning of path). You also need to set this key in a link in the return of the packets. You should put in the link after the link which is connected to the Load Balancer in the return.
* A full example can be seen in the  main-load-balancer.py file.


*Describing the Topology in file topo.txt*

* This file contains the description of the topology you are using. The connections between your hosts, switches and pops, in which port they are connected and also the IP of each POP.
* This file is described following some rules. An example, with description of the rule in brackets, can be seen right below:
  *  _link: s[switch number]-eth[port numeber]:h[host number]-eth[port number]  s1-eth3:s2-eth3_
  *  _link: s2-eth1:p21-eth0 s2-eth2:p21-eth1 s2-eth3:s1-eth3 s2-eth4:s3-eth4_
  *  _link: s3-eth1:h3-eth0  s3-eth4:s2-eth4_
  *  _pop: p[pop number]-[pop IP]_
  *  _pop: p21-192.168.122.92_
