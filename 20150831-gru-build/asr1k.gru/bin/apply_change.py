#!/usr/bin/env python

from ncclient import manager
from ncclient.operations.rpc import RPCError
import paramiko
import logging
logging.getLogger("paramiko").setLevel(logging.DEBUG)
import os
import re
import sys
import argparse

c_hdr = \
"""
      <config xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0">
        <cli-config-data>
"""
c_trail = \
"""
		</cli-config-data>
      </config>
"""

start_re = re.compile("([ ]+)?\!.*")
empty_line_re = re.compile("^$")
exit_only_line = re.compile("^exit$")
leading_space_re = re.compile("^([ ]+)")
change_interface = re.compile(".*(Gi|gi|giga|gigabitethernet|GigabitEthernet)([ ])?0\/0\/(?P<intname>[0-9\.]+).*")
skip_test_re = re.compile("^!!!! NO-TEST (?P<reason>.*)?!!!!")

def main():

  parser = argparse.ArgumentParser()
  parser.add_argument('--basedir', dest='basedir', action='store', default=None, help='base directory containing sequenced change files')
  parser.add_argument('--csrip', dest='csrip', action='store', default=None, help='CSR IP address')
  parser.add_argument('--csrkey', dest='csrkey', action='store', default=None, help='CSR SSH keyfile')
  parser.add_argument('--csruser', dest='csruser', action='store', default='netconf', help='CSR SSH username (default netconf)')
  parser.add_argument('--csrkeypass', dest='csrkeypass', action='store', default=None, help='CSR SSH key password')

  ctx = parser.parse_args(sys.argv[1:])

  if None in [ctx.basedir, ctx.csrip, ctx.csrkey]:
    print "Must specify basedir, CSR IP and CSR SSH keyfile!"
    sys.exit(127)

  with manager.connect(host=ctx.csrip, port=22,
  		key_filename=ctx.csrkey, username="netconf",
  		hostkey_verify=False, device_params={'name': 'csr' },
  		allow_agent=True, password=ctx.csrkeypass) as m:

      transactions = []
      for i in sorted(os.listdir(ctx.basedir)):
        candidate_transactions = []
        trans_str = c_hdr
        f = open(ctx.basedir + "/" + i, 'r')
        print "reading %s..." % i
        x = f.readlines()

        # Files marked !!!! NO-TEST <reason> !!!! as the first line are skipped
        # the key reason that this may be required is incompatible interface config
        if skip_test_re.match(x[0]):
          print "Skipping %s - %s" % (i, skip_test_re.sub('\g<reason>', x[0]).rstrip("\n"))
          continue

        for l in x:
          if start_re.match(l) or empty_line_re.match(l):
            continue
          elif change_interface.match(l):
            l = change_interface.sub('interface gi\g<intname>', l)
          cmd = "<cmd>%s</cmd>\n" % leading_space_re.sub('', l).rstrip("\n")

          # Do not rollback elements marked as test pre-requisites when they
          # are included in the special named 00-TEST-PRE-REQ file
          if not i == "00-TEST-PRE-REQ":
            candidate_transactions.append(l.rstrip("\n"))
          trans_str += cmd
        trans_str += c_trail
        f.close()

        try:
          #print trans_str
          m.edit_config(target='running', config=trans_str)
          transactions += candidate_transactions
        except RPCError:
          print "Transaction failed on file %s... Rolling back and aborting" % i
          break

      new_trans = c_hdr
      ctest = ""
      transactions.reverse()
      for c in transactions:
        if not leading_space_re.match(c) and not exit_only_line.match(c):
          new_trans = c_hdr
          new_trans += "<cmd>no %s</cmd>\n" % c
          new_trans += c_trail
          ctest += "no %s\n" % c
          try:
            m.edit_config(target='running', config=new_trans)
          except RPCError:
            print "INFO: could not remove '%s'" % c
            pass


if __name__ == '__main__':
  main()



