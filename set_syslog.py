#!/usr/bin/python2

import re
import sys
from Exscript import Queue, Host, Account
from Exscript.util.file import get_hosts_from_csv
from Exscript.util.match import any_match
from Exscript.protocols.drivers import ios
from Exscript.protocols.Exception import InvalidCommandException

inputfile = sys.argv[1]

accounts = [Account('user','password')]
hosts = get_hosts_from_csv(inputfile,default_protocol='ssh')
# get_hosts_from_csv expects a csv with tab delimiters
# the csv MUST have a first column titled address
# optionally it may have a second column titled hostname

syslog_servers=['10.10.10.10', '10.10.20.10']
        
### UTILITY FUNCTIONS

def get_vrf_from_aaa(job, host, conn):
    conn.execute('sh run | incl aaa|vrf forwarding')
    match_str = re.findall('ip vrf forwarding (\S+)', 
                           str(conn.response)[:150])
    if match_str:
        return match_str[0]
    else:
        return None

def save(job, host, conn):
    """Saves device config"""
    conn.set_prompt('\[(\S)+\]')
    conn.execute('write mem')
    conn.set_prompt('(\S)+\#')
    conn.execute('')
    conn.execute('')

def printerr(msg):
    """
    Prints a message to stderr
    
    Parameters:
    msg - the message to be printed to stderr
    
    Intention is to provide single place to update to different stderr 
    printing in future if necessary.
    """
    print >> sys.stderr, 'ERROR:', msg


### SYSLOG

def remove_old_syslog(job, host, conn):
    conn.execute('show run | incl logging (host )*([0-9]+)')
    os_servers = set(any_match(conn, r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'))
        
    conn.execute('configure terminal')
    for os_server in os_servers:
        try:
            conn.execute('no logging ' + os_server)
        except InvalidCommandException:
            printerr('Could not remove ' + os_server 
                     + ' on ' + host.get_name())
    conn.execute('end')

def set_syslog(vrf, job, host, conn):
    remove_old_syslog(job, host, conn)
    conn.execute('configure terminal')
    conn.execute('logging origin-id hostname')
    conn.execute('logging trap info')
  
    for sl_server in syslog_servers:
        if vrf is None:
            try:
                conn.execute('logging host ' + sl_server)
            except InvalidCommandException:
                printerr('failed to add syslog server ' + sl_server
                         + ' on ' + host.get_name())
        else:
            try:
                conn.execute('logging host ' + sl_server + ' vrf ' + vrf)
            except InvalidCommandException:
                printerr('failed to add syslog server ' + sl_server
                         + ' with vrf on ' + host.get_name())
    conn.execute('end')


### DONE

  
def launcher(job, host, conn):
    conn.set_timeout(30)
    conn.set_driver('ios')
    conn.connect()
    conn.authenticate()
    conn.guess_os()
    conn.autoinit()
    conn.set_prompt('(\S)+\#')
    vrf = get_vrf_from_aaa(job, host, conn)
    set_syslog(vrf, job, host, conn)
    save(job, host, conn)

queue = Queue(verbose = 1, max_threads = 4)
queue.add_account(accounts)
queue.run(hosts, launcher)
queue.shutdown()

print "\n\n"