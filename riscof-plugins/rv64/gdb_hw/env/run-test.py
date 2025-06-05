#
# Usage:
#   riscv32-unknown-elf-gdb -ex "py elf = '<elf-file>'" \
#                           <-ex "py cfg = 'openocd-<foo>.cfg'"> \
#                           <-ex "py sigref = '<sigref-file>'"> \
#                           <-ex "py sigout = '<sigout-file>'"> \
#                           -x "run-test-wfss.py"

import sys
import gdb
import subprocess
from os import environ
import os
import signal
import serial
import threading
from time import sleep
import re


# Get arguments
try:
    elf
except NameError:
    sys.exit("Error: Must pass elf on gdb command line with -ex 'py elf=foo' " +
             "before calling script.")

try:
    cfg
except NameError:
    cfg = "openocd-spike.cfg"

try:
    sigref
except NameError:
    sigref = None

try:
    sigout
except NameError:
    sigout = None

# TODO Need to change GDBREMOTE and GDBPORT to adapt for your openocd gdb server
# openocd gdb server should run locally using Nuclei openocd
# openocd -f riscof-plugins/rv64/gdb_hw/env/openocd-sample.cfg
GDBREMOTE = "localhost"
GDBPORT = 20400

class Runner:

    def __init__(self, elf, cfg):
        self.elf = elf
        self.live = True
        self.sim_p = None
        self.openocd_p = None
        self.fnull = open(os.devnull, 'w')

        signal.signal(signal.SIGINT, self.signal_handler)

        print(cfg)
        if 'spike' in cfg:
            print("Starting simulator...")
            cmd = "exec spike --halted --isa RV64IMACZicsr_Zifencei --rbb-port 9824 " + elf
            print("Command: " + cmd)
            self.sim_p = subprocess.Popen(cmd, shell=True, stdout=self.fnull,
                                          stderr=subprocess.STDOUT)
            if (self.sim_p is None):
                print("Error: simulator didn't start.")
                self.shutdown()

        if 0:
            print("Sleep a while for spike running")
            sleep(0.5)
            # Start openocd server
            print("Starting openocd...")
            cmd = "exec openocd -f " + cfg
            print("Command: " + cmd)
            self.openocd_p = subprocess.Popen(cmd, shell=True, stdout=self.fnull,
                                              stderr=subprocess.STDOUT)
            if (self.openocd_p is None):
                print("Error: openocd didn't start.")
                self.shutdown()


    # Clean shutdown
    def shutdown(self):
        self.live = False
        if self.openocd_p is not None:
            print("Disconnecting from openocd...")
            gdb.execute("disconnect")
            print("Killing openocd...")
            self.openocd_p.kill()
            if self.sim_p is None:
                self.t.join()
            else:
                print("Killing simulator...")
                self.sim_p.kill()
            self.fnull.close()
            sleep(1)
            sys.exit(0)


    # Register signal handler (for ctrl-c)
    def signal_handler(sig, frame):
        print('User terminated with ctrl-c.')
        shutdown()


    # Serial port reader for UART
    def serialReader(self):
        """Thread function for reading from serial."""
        while self.live or self.ser.in_waiting > 0:
            data = self.ser.readline()
            if data:
                print(data)

        self.ser.close()
        return

    def setup(self):
        sleep(0.5)
        # Setup gdb
        print("Setting up gdb...")
        gdb.execute("set architecture riscv:rv64")
        gdb.execute("file " + self.elf)
        gdb.execute("set breakpoint pending on")
        gdb.execute("set confirm off")

        # Connect to openocd and load symbols
        print("Connecting to openocd...")
        gdb.execute("target remote %s:%s" % (GDBREMOTE, GDBPORT))
        print("Reset CPU...")
        gdb.execute("monitor reset halt")
        print("Loading symbols...")
        gdb.execute("load")


    def sanityCheck(self):
        # Sanity check
        gdb.execute("x /20i 0x80000000")

    def runTest(self):
        fresults = open('results', 'a')

        print("Running test: " + elf)

        #
        # sigref - Look at the signature and compare to the reference given.
        #
        if sigref is not None:
            # Set breakpoint on halt
            print("Setting breakpoint on halt (write_tohost)...")
            gdb.execute("b write_tohost")

            # Continue execution
            print("Continuing...")
            gdb.execute("c")

            # Read the signature
            print("Reading signature...")
            gdb.execute("set $sigsize = (void*)&end_signature - (void*)&begin_signature")
            sigsize = gdb.convenience_variable('sigsize')
            print("Signature is %d bytes" % sigsize.cast(gdb.lookup_type('int')))
            out = []
            for i in range(0, sigsize / 8):
                memstr = gdb.execute("x /1gx (void*)&begin_signature + %d" % (i * 8),
                                     to_string=True)
                out.append(re.sub(r'0x[a-f0-9]+:\t0x', r'', memstr).strip())

            # Read the reference signature
            with open(sigref) as f:
                content = f.readlines()
                ref = [x.strip() for x in content]
            f.close()

            # Compare the lists and report result
            fresults.write("---\n")
            fresults.write("  Test: " + elf + "\n")
            if out == ref:
                fresults.write("  Result: pass\n")
            else:
                fresults.write("  Result: fail\n")
                fresults.write("      Reference : Output\n")
                for r, o in zip(ref, out):
                    fresults.write("      " + r + "  : " + o + "\n")
            fresults.write("---\n")
        #
        # sigout - Just output the signature when used within a framework that
        #          does the comparison against another reference model.
        #
        elif sigout is not None:
            fsigout = open(sigout, 'w')

            # Set breakpoint on halt
            print("Setting breakpoint on halt (write_tohost)...")
            gdb.execute("b write_tohost")

            # Continue execution
            print("Continuing...")
            gdb.execute("c")

            # Read the signature
            print("Reading signature...")
            gdb.execute("set $sigsize = (void*)&end_signature - (void*)&begin_signature")
            sigsize = gdb.convenience_variable('sigsize')
            print("Signature is %d bytes" % sigsize.cast(gdb.lookup_type('int')))
            for i in range(0, sigsize / 8):
                memstr = gdb.execute("x /1gx (void*)&begin_signature + %d" % (i * 8),
                                     to_string=True)
                #print(memstr)
                fsigout.write(re.sub(r'0x[a-f0-9]+:\t0x', r'', memstr).strip() + "\n")

            fsigout.close()

        #
        # Deprecated - Was originally used for tests which send a special value
        #              write_host. riscof doesn't seem to produce tests that
        #              support this, likely due to the way they setup the env.
        else:
            # Set breakpoints on possible exit points
            print("Setting breakpoint on write_tohost/pass/fail...")
            gdb.execute("b write_tohost")
            gdb.execute("b pass")
            gdb.execute("b fail")

            # Continue execution
            print("Continuing...")
            gdb.execute("c")

            # Get the PC and GP values
            pc_output = gdb.execute("p $pc", to_string=True)
            gp_output = gdb.execute("p /d $gp", to_string=True)
            m = re.search(r'\$\d+ = (\d+)', gp_output)
            test = m.group(1)

            fresults.write("---\n")
            fresults.write("  Test: " + elf + "\n")
            if 'write_tohost' in pc_output:
                if test == '1':
                    fresults.write("  Result: pass\n")
                else:
                    fresults.write("  Result: fail (tohost)\n")
                    fresults.write("  Test #: " + test + "\n")
            elif 'pass' in pc_output:
                fresults.write("  Result: pass\n")
            elif 'fail' in pc_output:
                fresults.write("  Result: fail\n")
                fresults.write("  Test #: " + test + "\n")
                fresults.write("---\n")

        fresults.close()
        gdb.execute("quit")


r = Runner(elf, cfg)

r.setup()
r.runTest()
r.shutdown()
