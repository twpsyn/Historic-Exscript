#!/usr/bin/python2

import re
import sys
from Exscript import Queue, Host, Account
from Exscript.util.file import get_hosts_from_csv
from Exscript.util.match import first_match, any_match
from Exscript.protocols.drivers import ios
from Exscript.protocols.Exception import *

inputfile = sys.argv[1]

accounts = [Account('user','password')]
hosts = get_hosts_from_csv(inputfile,default_protocol='ssh')
# get_hosts_from_csv expects a csv with tab delimiters
# the csv MUST have a first column titled address
# it also needs a second column titled hostname

core_pattern = re.compile('(COR)|(LAP)|(NAP)',re.I)
pop_pattern = re.compile('(POP)',re.I)

creds = { 'core':['snmp_core','password_1'],
          'pop':['snmp_pop','password_2'],
          'other':['snmp_user','password_3'] }

### UTILITY FUNCTIONS

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


def add_new_user(job, host, conn):
    
    conn.execute('conf t')
    
    if core_pattern.match(host.get_name()):     # CORE device
        myuser = creds['core'][0]
        mypass = creds['core'][1]
    elif cpop_pattern.match(host.get_name()):   # POP device
        myuser = creds['cpop'][0]
        mypass = creds['cpop'][1]
    else:                                       # something else, probably CPE
        myuser = creds['other'][0]
        mypass = creds['other'][1]

    try:
        conn.execute('snmp-server user ' + myuser + ' ROGROUP v3 auth sha ' 
                     + mypass + ' priv des56 ' + mypass + ' access mgmt_in')
    except InvalidCommandException:
        printerr('Could not add new user on ' + host.get_name() + '. Aborting!')
        raise
        
    conn.execute('end')
    
        
### DONE

  
def launcher(job, host, conn):
    conn.set_timeout(30)
    conn.set_driver('ios')
    try:
        conn.connect()
    except:
        printerr('unable to connect to ' + host.get_name())
        raise
    conn.authenticate()
    conn.guess_os()
    conn.autoinit()
    conn.set_prompt('(\S)+\#')
    add_new_user(job, host, conn)
    save(job, host, conn)

queue = Queue(verbose = 1, max_threads = 10)
queue.add_account(accounts)
queue.run(hosts, launcher)
queue.shutdown()

print "\n\n"