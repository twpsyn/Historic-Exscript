# Historic Exscript Scripts

This is a small collection of scripts that I wrote back in the early months of 2015. They're using python2 and the [Exscript](https://github.com/knipknap/exscript) module to connect out to network devices and make configuration changes. The chances are slim that this will be useful to anyone, but these have a little nostalgia value for me as the first pieces of network automation I did using python, so for posterity!

At the time these were written, I was working on a provider network which had been built out a little organically and sometimes lacking in strict configuration management. As a result while almost all devices had a management VRF configured on them, some didn't, and the naming wasn't consistent on the ones that did. Hence one of the tasks in some of these scripts is to work out what VRF and/or source IP the device should be using for whatever it is that the script is configuring.

This ability of a python script to inspect the existing configuration and then base its change on that is why these scripts existed. That wasn't something that was possible with the other configuration tools available there. Those other tools were Ciscoworks or Kiwi Cattools if memory serves.

The scripts are here almost exactly as I dug them out. The only changes I've made have been to sanitise them for credentials and real IP addresses.

## set_syslog.py

We had installed new syslog servers, Splunk if memory serves, and we needed everything to send logs to them. Script is also removing any other syslog servers so that we aren't spaffing logs at random IP addresses that shouldn't be getting them.

The method chosen for identifying the management vrf here was to check on the AAA servers. Makes sense, the TACACS servers were in the same subnet so however the device was getting to those, and we know it is because we've logged in, that's how it should get to the syslog servers.

## set_ntp.py

We actually got our own NTP servers, fancy that! So now we had to change the NTP config on all of our devices - set the new ones, and remove any old ones.  We also tightened up the ACLs that applied to NTP on the devices to prevent them being used for NTP reflection DDoS attacks.

Because one model of device didn't support the full NTP configuration the script did a check to identify those and apply a simpler configuration on them.

This one uses the AAA server configuration to check the VRF as well. I think these two scripts were written at about the same time, so plenty of copy and paste.

## snmpv3_deploy.py

Get SNMPv3 configured on everything with different credentials depending on where in the network the device was based on its hostname.

## passwd_change.py

Similar to the SNMPv3 script, but only two levels of device. Changing the fallback credentials.
