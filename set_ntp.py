#!/usr/bin/python2

import re
import sys
from Exscript import Queue, Host, Account
from Exscript.util.file import get_hosts_from_csv
from Exscript.util.match import first_match
from Exscript.protocols.drivers import ios
from Exscript.protocols.Exception import InvalidCommandException

inputfile = sys.argv[1]

accounts = [Account('user','password')]
hosts = get_hosts_from_csv(inputfile,default_protocol='ssh')
# get_hosts_from_csv expects a csv with tab delimiters
# the csv MUST have a first column titled address
# optionally it may have a second column titled hostname

ntp_servers=['10.10.10.123', '10.10.20.123']
ntp_auth = True    # Should NTP authentication be configured?
ntp_key = 'xxxxxxxxxxxxxxxxxxx'
        
### UTILITY FUNCTIONS

def get_vrf_from_aaa(job, host, conn):
    conn.execute('sh run | incl aaa|vrf forwarding')
    match_str = re.findall('ip vrf forwarding (\S+)', 
                           str(conn.response)[:150])
    if match_str:
        return match_str[0]
    else:
        return None

def get_pid_from_inventory(job, host, conn):
    conn.execute('show inventory | incl PID')
    pid_match_str = first_match(conn, r'PID: (\S+)')
    if pid_match_str:
        return pid_match_str
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


### NTP

def remove_old_ntp(job, host, conn):
    conn.execute('sh run | incl (s)*ntp server')
    on_servers = str(conn.response).split("\n")
    on_servers.pop(0)  # remove the first element (the command issued)
    on_servers.pop()   # also remove the last element (empty string)
    if len(on_servers) == 0:
        return  
    conn.execute('configure terminal')
    for on_server in on_servers:
        conn.execute('no ' + on_server)
    conn.execute('end')

def set_new_ntp(vrf, job, host, conn):
    # set ntp servers ntp_servers=['serverone_ip','server2_ip']
    model_pid = str(get_pid_from_inventory(job, host, conn))
    remove_old_ntp(job, host, conn)
    if  model_pid == 'CISCO857-K9':
        # 850 series routers don't support full NTP, only SNTP
        conn.execute('configure terminal')
        for ntp_server in ntp_servers:
            try:
                conn.execute('sntp server ' + ntp_server + ' version 3')
            except InvalidCommandException:
                printerr('unable to add sntp server ' + ntp_server 
                         + ' on ' + host.get_name())
        conn.execute('end')
    else:
        conn.execute('configure terminal')
        conn.execute('no access-list 50')
        conn.execute('access-list 50 remark NTP client list')
        conn.execute('access-list 50 deny any')
        conn.execute('ntp access-group serve 50')
        conn.execute('no access-list 51')
        conn.execute('access-list 51 remark NTP Servers')
        for ntp_server in ntp_servers:
            conn.execute('access-list 51 permit ' + ntp_server)
        conn.execute('access-list 51 deny any')
        conn.execute('ntp access-group peer 51')
        # access-list 52 is an odd one. Keep in mind that hosts that match the
        # acl will be denied anything other than basic ntp queries (although 
        # the same hosts will be denied those by acl 50, so they get nothing!)
        try:
            conn.execute('no access-list 52')
        except InvalidCommandException:
            printerr('access-list 52 didn\'t exist on ' + host.get_name())
        conn.execute('access-list 52 remark Disable NTP monlist')
        conn.execute('access-list 52 permit any')
        conn.execute('ntp access-group serve-only 52')
        if ntp_auth:
            try:
                conn.execute('ntp authenticate')
            except InvalidCommandException:
                printerr('ntp authenticaton attempted but unsupported on '
                         +host.get_name()+'. Aborting NTP configuration.')
                conn.execute('end')
                return
            conn.execute('ntp authentication-key 50 md5 ' + ntp_key)
            conn.execute('ntp trusted-key 50')
            for ntp_server in ntp_servers:
                if vrf is None:
                    try:
                        conn.execute('ntp server '+ ntp_server 
                                     +' version 3 key 50')
                    except InvalidCommandException:
                        printerr('unable to add authenticated ntp server '
                                 + ntp_server +' on '+ host.get_name())
                else:
                    try:
                        conn.execute('ntp server vrf ' + vrf + ' ' + ntp_server
                                     + ' version 3 key 50')
                    except InvalidCommandException:
                        printerr('unable to add authenticated ntp server '
                                 + ntp_server + ' with vrf on '
                                 + host.get_name())
        else:
            for ntp_server in ntp_servers:
                if vrf is None:
                    try:
                        conn.execute('ntp server ' + ntp_server + ' version 3')
                    except InvalidCommandException:
                        printerr('unable to add ntp server ' + ntp_server 
                                 + ' on ' + host.get_name())
                else:
                    try:
                        conn.execute('ntp server vrf ' + vrf +' '
                                     + ntp_server + ' version 3')
                    except InvalidCommandException:
                        printerr('unable to add ntp server ' + ntp_server 
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
    set_new_ntp(vrf, job, host, conn)
    save(job, host, conn)

queue = Queue(verbose = 1, max_threads = 4)
queue.add_account(accounts)
queue.run(hosts, launcher)
queue.shutdown()

print "\n\n"