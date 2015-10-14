#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
Created on Wed Nov  25 13:17:15 2013

@author: Alan Yorinks
@edited: Mirko Budszuhn 
Copyright (c) 2013-14 Alan Yorinks All right reserved.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
import os
import sys
import logging
import subprocess
from PyMata.pymata import PyMata
import scratch_http_server
from scratch_command_handlers import ScratchCommandHandlers
import time
from discover_com_ports import serial_ports


#noinspection PyBroadException
class s2a_fm:

    """
    This is the "main" function of the program.
    It will instantiate PyMata for communication with an Arduino micro-controller
    and the command handlers class.
    It will the start the HTTP server to communicate with Scratch 2.0
    @return : This is the main loop and should never return
    """
    def __init__(self):
        subprocess.Popen("scratch2")
        # total number of pins on arduino board
        self.total_pins_discovered = 0
        # number of pins that are analog
        self.number_of_analog_pins_discovered = 0
        # COM-Port
        self.com_port = "COM1"
        #firmata
        #self.firmata ="-

        # make sure we have a log directory and if not, create it.
        if not os.path.exists('log'):
            os.makedirs('log')

        # turn on logging
        logging.basicConfig(filename='./log/s2a_fm_debugging.log', filemode='w', level=logging.DEBUG)
        logging.info('s2a_fm version 1.5    Copyright(C) 2013-14 Alan Yorinks    All Rights Reserved ')
        print 's2a_fm version 1.5   Copyright(C) 2013-14 Alan Yorinks    All Rights Reserved '

        # get the com_port from the command line or default if none given
        # if user specified the com port on the command line, use that when invoking PyMata,
        # else use '/dev/ttyACM0'
    

    def search_port(self):
        #returns all serial COM-Ports
        possible_ports = serial_ports() 
        print 
        for com_port in possible_ports:
            logging.info('com port = %s' % com_port)
            try:
                # instantiate PyMata
                self.firmata = PyMata(com_port)  # pragma: no cover
                self.com_port = com_port
                return 1
            except Exception:
                print('Could not instantiate PyMata - is your Arduino plugged in?')
                logging.exception('Could not instantiate PyMata on Port %s' % com_port)
        return 0
        #TODO: Ask if User Wants to flash Arduino on this Port
            
        
    def discover_arduino(self):
        # determine the total number of pins and the number of analog pins for the Arduino
        # get the arduino analog pin map
        # it will contain an entry for all the pins with non-analog set to self.firmata.IGNORE
        self.firmata.analog_mapping_query()

        self.capability_map = self.firmata.get_analog_mapping_request_results()

        self.firmata.capability_query()
        print("Please wait for Total Arduino Pin Discovery to complete. This can take up to 30 additional seconds.")

        # count the pins
        for pin in self.capability_map:
                self.total_pins_discovered += 1
                # non analog pins will be marked as IGNORE
                if pin != self.firmata.IGNORE:
                    self.number_of_analog_pins_discovered += 1

        # log the number of pins found
        logging.info('%d Total Pins and %d Analog Pins Found' % (self.total_pins_discovered, self.number_of_analog_pins_discovered))

        # instantiate the command handler
        self.scratch_command_handler = ScratchCommandHandlers(self.firmata, self.com_port, self.total_pins_discovered,
                                                         self.number_of_analog_pins_discovered)

        # wait for a maximum of 30 seconds to retrieve the Arduino capability query
        start_time = time.time()

        pin_capability = self.firmata.get_capability_query_results()
        while not pin_capability:
            if time.time() - start_time > 30:
                print ''
                print "Could not determine pin capability - exiting."
                self.firmata.close()
                # keep sending out a capability query until there is a response
            pin_capability = self.firmata.get_capability_query_results()
            time.sleep(.1)

        # we've got the capability, now build a dictionary with pin as the key and a list of all the capabilities
        # for the pin as the key's value
        pin_list = []
        total_pins_discovered = 0
        for entry in pin_capability:
            # bump up pin counter each time IGNORE is found
            if entry == self.firmata.IGNORE:
                self.scratch_command_handler.pin_map[total_pins_discovered] = pin_list
                total_pins_discovered += 1
                pin_list = []
            else:
                pin_list.append(entry)

        print "Arduino Total Pin Discovery completed in %d seconds" % (int(time.time() - start_time))

    def start_server(self):
        try:
            # start the server passing it the handle to PyMata and the command handler.
            scratch_http_server.start_server(self.firmata, self.scratch_command_handler)

        except Exception:
            logging.debug('Exception in s2a_fm.py %s' % str(Exception))
            self.firmata.close()
            return

        except KeyboardInterrupt:
            # give control back to the shell that started us
            logging.info('s2a_fm.py: keyboard interrupt exception')
            self.firmata.close()
            return


if __name__ == "__main__":
    s2a = s2a_fm()
    if s2a.search_port() :
        s2a.discover_arduino()
        s2a.start_server()    
