import os
import re
import csv
import json
import subprocess
import ruamel.yaml
from nornir import InitNornir
from isc_dhcp_leases import IscDhcpLeases
from nornir_netmiko.tasks import netmiko_send_config
from nornir_netmiko.tasks import netmiko_send_command
from nornir_jinja2.plugins.tasks import template_file
from nornir_utils.plugins.functions import print_result
from ruamel.yaml.scalarstring import SingleQuotedScalarString as sq

yaml = ruamel.yaml.YAML()

# Get IP addresses of booted network elements ##################################
leases = IscDhcpLeases('/var/lib/dhcp/dhcpd.leases')
current_leases = leases.get_current()
lease_ips = []
for lease in current_leases.values():
    m = re.search(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', str(lease))
    if m:
        lease_ips.append(m.group(1))

# Generate initial inventory file ##############################################
os.chdir('/home/nornir-ztp/inventory')
hosts = {}
for index, lease_ip in enumerate(lease_ips):
    router_name = 'R' + str(index+1)
    hosts[router_name] = {'hostname': lease_ip}
    # Add single quoted (sq) value in YAML dumper
    device_type = {'device_type': sq('cisco_ios_telnet')}
    conn_opts = {'connection_options': {'netmiko': {'extras': device_type}}}
    hosts[router_name].update(conn_opts)
        
with open('hosts.yaml', 'w') as f:
    data = yaml.dump(hosts, f)

# Reload inventory
nr = InitNornir(config_file="/home/nornir-ztp/config.yaml")

# Configure SSH keys on network elements #######################################
def gen_ssh_keys(task):
    # Generate config commands
    cfg = [task.run(
        template_file, path="templates", template="ssh-config.j2"
    ).result]
    # Configure on hosts
    task.run(netmiko_send_config, config_commands=cfg)
    
result = nr.run(gen_ssh_keys)
print_result(result)

# Update SSH keys on server ####################################################
subprocess.call("cp /dev/null /home/eve/.ssh/known_hosts", shell=True)
for lease_ip in lease_ips:
    fmt = 'ssh-keyscan {} >> /home/eve/.ssh/known_hosts'.format(lease_ip )
    subprocess.call(fmt, shell=True)

# Find MAC of E0/0 interfaces of elements ######################################
COMMAND = 'show interface eth0/0 | i Hardware is AmdP2'

response = nr.run(task=netmiko_send_command, command_string=COMMAND)
mac_result = {} 
for hostname in response:
    fmt = 'is (\w{4}\.\w{4}\.\w{4})'
    mac_result[hostname] = re.search(fmt, response[hostname][0].result).group(1)

# Read CSV file, compare MAC addresses and create new inventory ################
os.chdir('/home/nornir-ztp')
new_hosts = {} # New Nornir inventory
with open('Map1.csv') as csv_file:
    csv_reader = csv.DictReader(csv_file)
    for row in csv_reader:
        for old_hostname in mac_result:
            if mac_result[old_hostname] == row['MAC_Add']:
                hostname = row['Hostname'] # New hostname from CSV file
                ip_add = nr.inventory.hosts[old_hostname].hostname
                new_hosts[hostname] = {}
                new_hosts[hostname]['hostname'] = ip_add
                data = new_hosts[hostname]['data'] = {}
                data['prod_ip'] = row['Prod_IP']
                data.update({'prod_mask': row['Prod_subnet']})
                data.update({'prod_gw': row['Prod_GW']})
                data.update({'prod_intf': row['Prod_intf']})
                data.update({'username': row['Username']})
                data.update({'password': row['Password']})
                # No DNS available, so real hostname is stored here.
                data.update({'hostname': hostname})

os.chdir('/home/nornir-ztp/inventory')
with open('hosts.yaml', 'w') as f:
    data = yaml.dump(new_hosts, f)

# Reload inventory
nr = InitNornir(config_file="/home/nornir-ztp/config.yaml")

# Push final configs to network elements #######################################
def push_final_configs(task):
    # Generate config commands
    cfg = task.run(
        template_file, path="templates", template="final-config.j2"
    ).result.splitlines()
    # Configure on hosts
    task.run(netmiko_send_config, config_commands=cfg)
    
result = nr.run(push_final_configs)
print_result(result)









    

























    
    
