
	Ubuntu VM		    CentOS6
	Ansible 2.4.2.0	            Cisco IOU
	ISC DHCP server
	TFTP server
	--------		    --------
	|	|		    |       |
	|	|		    |       |
	|	|		    |       | 
	|	|	            |       |
	--------		    --------
	    |				|
	    |				|
---------------------------------------------------- VMware workstation VMnet adapter


The idea:
I've build a virtual lab to demonstrate how to stage configurations on network elements using
ansible and some other tools. In a real world scenario, you need to unpack a new network element,
log in via console to configure basic connectivity, then connect it to a ftp server to upload ios,
and then make a config and push it to the device. Wouldn't it be nice if you connect new elements
to a switch which on turn is connected to an ansible host that will do all the work for you? 

When you buy a new switch, in Cisco case it will be delivered with a MAC address, which is printed 
on the box and on the switch. This MAC address will be used to identify the switch and thus to put some device specific config
on it. I will use a very simple excel sheet with some common and device specific variables to generate some config and put it 
on the virtual elements. As this is a coding challenge it is not relevant what config is put on the device. 
The excel file is 'loaded' into ansible as the data model for this project. I used a python plugin which is written 
for this purpose and it is published here:

https://github.com/mamullen13316/ansible_xls_to_facts

The Lab:
Every virtual network element in IOU is connected to a virtual management switch.
Traffic from 'uplink' of virtual management switch is bridged into VMnet adapter. 
An Ansible host is connected to this VMnet adapter for connectivity with all virtual elements.
All virtual network elements are IOU router instances, except for the switch, which is an IOU switch instance.
Each virtual router has a dedicated 'management' interface with connects to the virtual management switch.

I assume that with more coding effort this solution can be build into a "real" solution. Also then you could add 
a step to upgrade the network elements as this is not possible in this virtual environment. 


I decided to split up my ansible playbooks. At the end of most playbooks I used a 'workaround' to reset the ansible inventory file. The split helped 
me also to focus on a particular part of the solution. I will give a short description of each playbook to give an idea what components are used and
how the overall solution works.


#### Playbook1: reset inventory file. ####
The inventory file is reset. The reason to perform this operation is because in further steps the inventory will be dynamically created.
The hosts.start file is included.


#### Playbook2: build first inventory. ####
The autoinstall feature is used to assign IP addresses to the virtual routers when they are connected to the network via its management
port. An ISC DHCP server is used to assign IP addresses. Within the DHCP configuration the routers are instructed to download a configuration
file via TFTP. This config file enables ansible to telnet to all devices and to generate SSH keys. See next playbook for more details.
The DHCP assigned IP addresses are 'scraped' from the ARP table of the Ansible machine and are 'coupled' to hostnames E1, E2, E3, etc. 
Finally the generated hostfile is copied into the default ansible hosts location.
The config of the DHCP server and the TFTP pushed config file is included, dhcpd.conf and network-confg


#### Playbook3: Generate SSH keys on devices. ####
Using the new ansible 2.4 telnet module, the SSH keys are generated on the router elements. Also the SSH keys from the routers are
scanned by the ansible hosts so that it can access the elements in further steps.


#### Playbook4: Generate final ansible inventory configuration. ####
In the excel file the MAC address of each element is stored. First ansible scans the MAC addresses of all connected elements.
If the MAC address is found in the excel file, then the 'production' hostname is known and the final inventory hosts file can be generated
and loaded into the ansible host.


#### Playbook5: Push final configurations to network elements. ####
Finally the configurations are generated and pushed into the network elements.

















