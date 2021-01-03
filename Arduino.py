#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 30 11:41:45 2020

@author: Casual Endvrs
Email: casual.endvrs@gmail.com
GitHub: https://github.com/Casual-Endvrs
Reddit: CasualEndvrs
Twitter: @CasualEndvrs
"""

import numpy as np
from time import sleep as time_sleep
import serial
import serial.tools.list_ports
from itertools import zip_longest as itertools_zip_longest

class Arduino() :
    def __init__(self, port=None, baud=9600, timeout=0, eol='') :
        self.port = port
        self.baud = baud
        
        self.timeout = timeout
        self.eol = eol.encode("utf-8")
        
        self.arduino = None
    
    def get_avail_ports(self) :
        """
        Search for all available ports with an Arduino connected.
        
        Returns
        -------
        avail_ports : list
            List of ports.
        
        """
        list_ports = serial.tools.list_ports.comports()
        
        avail_ports = []
        for port, desc, hwid in sorted(list_ports) :
            avail_ports.append( port )
        
        return avail_ports
    
    def connect(self, port=None, baud=None, timeout=None, flush=True) :
        """
        Connects to an Arduino at "port" with "baud" rate.
        
        Parameters
        ----------
        port : string
            Port address for the Arduino.
        baud : int
            Baud rate for communication with Arduino.
        timeout : float
            Seconds to wait before timeout.
        
        Returns
        -------
        str
            Description of connection result.
        
        """
        if port is None :
            port = self.port
        if baud is None :
            baud = self.baud
        if timeout is None :
            timeout = self.timeout
        
        if port is None :
            return 'port not provided'
        if baud is None :
            return 'baud not provided'
        if self.arduino is not None :
            return 'Arduino already connected'
        
        try :
            self.arduino = serial.Serial(port, baud, 
                                timeout=timeout)
            time_sleep(0.25)
            if flush :
                self.flush_buffer()
            return 'Success'
        except :
            if port not in self.get_avail_ports() :
                return 'Nothing connected to point'
            return 'Connection Failure'
    
    def test_connection(self) :
        if self.arduino is not None :
            self.send_command( 'test_connection' )
            response = self.arduino.readline()
            response = response.decode('utf-8').strip()
            if response == 'good_connection' :
                return True
            else :
                return False
    
    def disconnect(self) :
        """
        Disconnects from an Arduino if it is connected.
        
        Returns
        -------
        None.
        
        """
        if self.arduino is not None :
            self.arduino.close()
    
    def flush_buffer(self) :
        if self.arduino is not None :
            self.arduino.flush()
    
    def set_parameter(self, cmd) :
        if self.arduino is not None :
            attempts_left = 3
            while True :
                self.send_command( cmd )
                response = self.arduino.readline()
                if response != b'' :
                    response = int( float( response.decode("utf-8").strip() ) )
                    if response == 1 :
                        return True
                attempts_left -= 1
                if attempts_left <= 0 :
                    return False
                time_sleep(0.1)
                print( 'attempting again - set' )
            return True
        else :
            return False
    
    def get_parameter(self, cmd, dtype=None) :
        if self.arduino is not None :
            attempts_left = 3
            while True :
                self.send_command( cmd )
                response = self.arduino.readline()
                if response != b'' :
                    response = response.decode("utf-8").strip()
                    if dtype is not None :
                        response = self.convert_type(response, dtype)
                    return response
                else :
                    attempts_left -= 1
                    if attempts_left <= 0 :
                        return None
                time_sleep(0.1)
                # print( 'attempting again - get' )
        else :
            return None
    
    def send_command(self, cmd) :
        """
        Sends a simple command to the Arduino.
        
        Parameters
        ----------
        cmd : string
            String command to be send to Arduino.
            
        Returns
        -------
        bool
            True --> Command was sent successfully.
            False --> Command failed.
        """
        if self.arduino is not None :
            cmd = str(cmd).encode("utf-8")
            # if len cmd is less than eol, append eol
            # else: test if last characters of cmd are eol
            if len(cmd) < len(self.eol) :
                cmd += self.eol
            elif cmd[-len(self.eol):] != self.eol :
                cmd += self.eol
            
            self.arduino.write( cmd )
            return True
        else :
            return False
    
    def get_responses(self, num_responses=None, element_separator=',', 
        response_types=None, transpose=True, eol='\r\n', end_message=False, 
        ) :
        """
        element_separator
        response_types
        transpose
        """
        if self.arduino is None :
            return False
        
        elements = 0
        responses = []
        result = b''
        eol = eol.encode('utf-8')
        while True :
            result += self.arduino.readline()
            # this requires a timeout break
            if result in [b'\n', b'end\r\n'] :
                if end_message :
                    responses.append( ['end'] )
                break
            if eol in result :
                result = [result.decode('utf-8')]
                responses.append( result )
                result = b''
                elements += 1
                if num_responses is not None \
                        and elements >= num_responses :
                    #print( 'found max number of responses' )
                    break
        
        if element_separator is not None :
            responses = [ row[0].split(element_separator) 
                            for row in responses ]
        
        if response_types is not None :
            if isinstance(response_types, (list, tuple, np.ndarray)) :
                num_response_types = len(response_types)
                responses = [ [ self.convert_type(row[i], response_types[i])
                                for i in range(num_response_types) ]
                             for row in responses ]
            elif isinstance(response_types, str) :
                responses = [ [ self.convert_type(ele, response_types)
                                for ele in row ]
                             for row in responses ]
        
        if transpose :
            responses = list(map(list, itertools_zip_longest(*responses, fillvalue=None)))
        
        if num_responses == 1 :
            return responses[0]
        return responses
    
    def convert_type(self, data, d_type, eol=None) :
        try :
            if data == 'end' :
                return 'end'
            if d_type in ['s', 'str', 'string'] :
                return str(data).strip(eol)
            if d_type in ['i', 'int', 'integer'] :
                return int(data)
            if d_type in ['f', 'float'] :
                return float(data)
        except :
            print()
            print( f'data : {data}' )
            print( f'd_type : {d_type}' )
            print()



