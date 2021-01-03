#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 31 15:10:57 2020

@author: Casual Endvrs
Email: casual.endvrs@gmail.com
GitHub: https://github.com/Casual-Endvrs
Reddit: CasualEndvrs
Twitter: @CasualEndvrs
"""


from time import sleep as time_sleep
from sys import exit as sys_exit

from Arduino import Arduino

port_str = '/dev/ttyACM1'
baud = 230400
ending = '/'
arduino = Arduino(port_str, baud, timeout=1, eol=ending)
connection_result = arduino.connect()

if connection_result != 'Success' :
    print( arduino.get_avail_ports() )
    print( 'Failed to connect to the Arduino' )
    sys_exit()

while not arduino.test_connection() :
    time_sleep(1)


#tests = [
#         ["prep_charge", "get_pin_state", '1'], 
#         ["prep_discharge", "get_pin_state", '0'], 
#         ["prep_charge", "get_pin_state", '1'], 
#         ["prep_discharge", "get_pin_state", '0'], 
#         ["set_R;123", "get_R", '123.00'], 
#         ["set_R;456.5", "get_R", '456.50'], 
#         ["set_C;123", "get_C", '123.00'], 
#         ["set_C;456.5", "get_C", '456.50'], 
#         ["set_Vcc;123", "get_Vcc", '123.00'], 
#         ["set_Vcc;456.5", "get_Vcc", '456.50'], 
#         ["set_num_tcs;123", "get_num_tcs", '123'], 
#         ["set_num_tcs;456", "get_num_tcs", '456'], 
#         ["set_steps_per_tc;123", "get_steps_per_tc", '123'], 
#         ["set_steps_per_tc;456", "get_steps_per_tc", '456'], 
#         ["set_pw_dur;123", "get_pw_dur", '123'], 
#         ["set_pw_dur;456", "get_pw_dur", '456'], 
#         ["set_pw_dc;123", "get_pw_dc", '123'], 
#         ["set_pw_dc;456", "get_pw_dc", '456'], 
#        ]

tests = [
         ["d", "e", '1'], 
         ["c", "e", '0'], 
         ["d", "e", '1'], 
         ["c", "e", '0'], 
         ["f;123", "g", '123.00'], 
         ["f;456.5", "g", '456.50'], 
         ["h;123", "i", '123.00'], 
         ["h;456.5", "i", '456.50'], 
         ["j;123", "k", '123.00'], 
         ["j;456.5", "k", '456.50'], 
         ["l;123", "m", '123'], 
         ["l;456", "m", '456'], 
         ["n;123", "o", '123'], 
         ["n;456", "o", '456'], 
         ["r;123", "s", '123'], 
         ["r;456", "s", '456'], 
         ["t;123", "u", '123'], 
         ["t;456", "u", '456'], 
        ]

print( '\nstarting tests\n' )

test_num = 0
itr = 0
num_success = 0
for test in tests :
    [cmd, param_cmd, target] = test
    arduino.set_parameter( cmd )
    # time_sleep(2)
    result = arduino.get_parameter( param_cmd )
    if result != target :
        print()
        print( f'error found on test {itr}' )
        print( f'obtained results was: {result}' )
        print( test )
        print()
    else :
        num_success += 1
        print( f'test {itr} was successful' )
    itr += 1



print()
print( 'Report:' )
print( f'{num_success} successes of {itr} total' )




















