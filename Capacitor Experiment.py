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

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from multiprocessing import Queue

import os
import sys

import numpy as np
import lmfit

import matplotlib
import matplotlib.ticker as ticker
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import lmfit

from time import sleep as time_sleep
from time import time as current_time

from Arduino import Arduino

def cap_charge(x, Vcc, tc, offset=0) :
    return Vcc * (1 - np.exp(-(x-offset)/tc) )

def cap_discharge(x, Vcc, tc) :
    return Vcc * np.exp(-x/tc)

class arduino() :
    def __init__(self) :
        self.connected = False
        
        self.port = '/dev/ttyACM0'
        self.baud = 230400
        self.serial = Arduino(self.port, self.baud, timeout=1, eol='/')
        
        """
        if self.port not in self.serial.get_avail_ports() :
            self.port = self.serial.get_avail_ports()[0]
            self.serial.port = self.port
        """
        
        self.Vcc = -1
        self.R = -1
        self.C = -1
        self.exp_dur_factor = -1
        self.pulse_duration = -1
        self.pulse_duty_cycle = -1
        
        self.dis_charge_choice = 1
    
    def connect(self) :
        if not self.connected :
            connection_result = self.serial.connect()
            
            if connection_result == 'Success' :
                self.connected = True
                attempts = 5
                while not self.serial.test_connection() :
                    attempts -= 1
                    if attempts <= 0 :
                        return False
                    time_sleep( 0.15 )
                self.update_all_parameters()
            
            self.serial.send_command('z')
            
        return self.connected
    
    def disconnect(self) :
        if self.connected :
            self.serial.disconnect()
    
    def update_all_parameters(self) :
        attempts = 3
        while True :
            self.Vcc = self.serial.get_parameter('k', 'f')
            self.R = self.serial.get_parameter('g', 'f')
            self.C = self.serial.get_parameter('i', 'f')
            self.exp_dur_factor = self.serial.get_parameter('m', 'f')
            self.pulse_duration = self.serial.get_parameter('s', 'i')
            self.pulse_duty_cycle = self.serial.get_parameter('u', 'i')
            
            if -1 in [self.Vcc, self.R, self.C, self.exp_dur_factor, 
                    self.pulse_duration, self.pulse_duty_cycle] :
                attempts -= 1
                if attempts <= 0 :
                    break
                time_sleep(0.15)
            else :
                break

class MainWindow(QMainWindow) :
    def __init__(self) :
        super().__init__()
        
        title = 'Capacitor Experiments'
        self.setWindowTitle(title)
        
        self.uController = arduino()
        
        main_layout = QVBoxLayout()
        
        self.intro_tab = intro_page(self, self.uController)
        self.dis_charge_exp_tab = dis_charge_exp_controls(self)
        self.freq_exp_tab = freq_exp_controls(self)
        
        self.main_tabs = QTabWidget()
        self.main_tabs.addTab(self.intro_tab, "Introduction")
        self.main_tabs.addTab(self.dis_charge_exp_tab, "(Dis)Charge Experiment")
        self.main_tabs.addTab(self.freq_exp_tab, "Pulse Experiment")
        
        self.main_tabs.setTabEnabled(1, False)
        self.main_tabs.setTabEnabled(2, False)
        
        self.main_tabs.currentChanged.connect(self.tab_changed)
        
        main_layout.addWidget(self.main_tabs)
        self.setCentralWidget(self.main_tabs)
        
        self.show()
    
    def tab_changed(self) :
        tab_idx = self.main_tabs.currentIndex()
        if tab_idx == 1 :
            self.dis_charge_exp_tab.update_param_lbls()
        elif tab_idx == 2 :
            self.freq_exp_tab.update_param_lbls()

class intro_page(QWidget) :
    """
    Introduction page widget.
    Displays information about the experiment.
    """
    def __init__(self, parent, uController) :
        """
        Constructs the intro_page class.

        Parameters
        ----------
        parent : MainWindow object
            MainWindow object that this object belongs to.

        Returns
        -------
        None.

        """
        super(QWidget, self).__init__(parent)
        max_widget_width = 150
        
        self.result_q = Queue()
        
        self.parent = parent
        self.uController = uController
        
        self.layout = QGridLayout(self)
        
        label_txt = "Select the port your Arduino is connected to: "
        label = QLabel(label_txt)
        label.setMaximumWidth(325)
        self.layout.addWidget(label, 0, 0)
        
        self.btn_check_devices = QPushButton("Check for Devices")
        self.btn_check_devices.setMaximumWidth(max_widget_width)
        self.btn_check_devices.clicked.connect(self.search_for_devices)
        self.layout.addWidget(self.btn_check_devices, 0, 1)
        
        self.ports_selection = QComboBox(self)
        self.layout.addWidget(self.ports_selection, 0, 2)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_init)
        #self.connect_btn.clicked.connect(self.connect_to_exp)
        self.connect_btn.setMaximumWidth(max_widget_width)
        self.layout.addWidget(self.connect_btn, 0, 3)
        
        self.lbl_connection_status = QLabel("Connection Status: Disconnected")
        self.layout.addWidget(self.lbl_connection_status, 1, 0, 1, 4)
        
        
        
        
        
        
        
        
        self.instruction_tabs = QTabWidget()
        
        self.intro_instructions = "\n".join([
            "Important Note:",
            "Arduino micro-controllers are only designed to provide a peak current of 50 ma. "
            "This experiment uses an RC circuit; a circuit composed of a resistor (R) and a capacitor (C). "
            "To protect the micro-controller, always use a resistor that has a resistance of 250 Ohms or greater. "
            "This software is setup to require a resistance of 250 Ohms or more. This is done as a reminder to "
            "the user. Do not use a resistor values less than this.",
            "",
            "There is a known issue where the program will present obviously erroneous data or may crash. This is "
            "caused by communication errors between the Arduino and pc. If this happens, try resetting the Arduino "
            "(using the Arduino's reset button or unplugging and plugging it back in again) and restarting the software. "
            "Generally, either the software has an issue with the first experiment or it runs flawlessly.",
            "",
            "-----------------------",
            "Resistor/Capacitor (RC) Circuits - Time Constants",
            "-----------------------",
            "The characteristic parameter of an RC circuit is called the \"time constant,\" TC. "
            "The TC determines how the circuit responds to input voltages, either AC or DC. "
            "These experiments perform best when the RC circuit has a time constant between 0.5 and 1 second.",
            "An example calculation for a time constant is as follows:",
            "     If the resistor has a value of 2200 Ohms, and the capacitor has a value of 220 micro-Farad, then",
            "            tc = RC",
            "                = 2200 Ohms x 220E-6 Farad ",
            "                = 0.484 seconds ",
            "",
            "-----------------------",
            "Circuit Diagram:",
            "-----------------------",
            "Circuit pin connections: (Note: A circuit diagram is provided in the \"Circuit Diagram\" tab.)",
            "     Arduino D8 --> Resistor --> (Measure Point) --> Capacitor --> Arduino ground (GND)",
            "     Arduino A0 --> Measure Point",
            "Note: For electrolytic capacitors it is important to connect the negative terminal to ground (GND), the terminal "
            "next to the silver line.",
            "",
            "-----------------------",
            "Experiment Parameters:",
            "-----------------------",
            "There are several parameters that can be set. It is important that the values for resistor "
            "and the capacitor are provided. These are used by the Arduino to determine how long experiments "
            "should be run and by this software for model fits.",
            "Parameters (Common to all experiments):",
            "     Vcc [Volts] --> The voltage output of the Arduino. Note: this does not change "
            "the output voltage of the Arduino, it only sets a value used by the software.",
            "     Resistance [Ohms] --> The resistance of the resistor used in the experiment. "
            "This must have a value of 250 Ohms or greater. Used to determine the circuits time constant.",
            "     Capacitance [micro-Farads] --> The capacitance of the capacitor used in the experiment. "
            "Used to determine the circuits time constant.",
            "",
            "Parameters ( (Dis)Charge Experiment ):",
            "     Experiment duration factor [unitless] --> This number is multiplied by the circuits time "
            "constant to determine how long the charge/discharge experiment should run. It is recommended to "
            "use a number from 3 to 10.",
            "",
            "Parameters (Pulse Experiment):",
            "     Pulse Duration [milli-seconds] --> Full duration of a pulse. This is the amount of time taken "
            "for the signal pulse to switch HIGH, stay HIGH, switch LOW, stay LOW. This HIGH/LOW process is then "
            "repeated. It is recommended to use a value between 10 and 500. Values less than 10 will not be accepted.",
            "     Pulse Duty-Cycle [%] --> This is the percent of the pulse duration which will be spent in the "
            "HIGH state. 100 is always HIGH, 0 is always LOW, and 50 is HIGH half the time and LOW the other half. "
            "Any integer value between 0 and 100 inclusive is accepted.",
            "",
            "-----------------------",
            "(Dis)Charge Experiment:",
            "-----------------------",
            "This experiment measures the time constant of the RC circuit by recording the voltage "
            "across the capacitor as a function of time and then fits these results with the equations "
            "that describes a theoretical capacitor charging or discharging.",
            "There are two different equations, one for each case.",
            "     Charging --> capacitor voltage = Vcc * (1- exp(-t/TC) )",
            "     Discharging --> capacitor voltage = Vcc * exp(-t/TC)",
            "     where: Vcc --> (charging) supply voltage to charge the capacitor",
            "                             (discharging) initial voltage across the capacitor",
            "                             exp(x) --> Euler's number to the power of x, e^x",
            "                             TC --> RC circuit's time constant, equal to Resistance x Capacitance",
            "Proceedure (Charging):",
            "    1) Pin D8 is set LOW, the capacitor is discharged to 0 volts",
            "    2) Pin D8 is set HIGH (3.3 or 5 volts), the capacitor starts charging and live data is sent to the pc",
            "    3) The experiment will automatically stop after (Experiment duration factor) * TC seconds",
            "    4) The analysis is automatically performed and the results (both plot figure and "
            "the data as a csv file) can be saved.",
            "Proceedure (Discharging):",
            "    1) Pin D8 is set HIGH, the capacitor is charged to Vcc (3.3 or 5) volts",
            "    2) Pin D8 is set LOW (0 volts or GND), the capacitor starts discharging and live data is sent to the pc",
            "    3) The experiment will automatically stop after (Experiment duration factor) * TC seconds",
            "    4) The analysis is automatically performed and the results (both plot figure and "
            "the data as a csv file) can be saved.",
            "",
            "-----------------------",
            "Pulse Experiment",
            "-----------------------",
            "This experiment measures the voltage across a capacitor as the supply voltage is quickly turned on and off. "
            "The on/off process is done using a pulse signal which is either HIGH (3.3 or 5 volts) or LOW (0 volts, GND). The pulse "
            "duration and duty cycle can be changed to see how RC circuits respond. As these values are changed the user should "
            "look at the change to the average voltage as well as the voltage variation, min/max voltages, after the system has "
            "reached a consistent behaviour.",
            "Proceedure:",
            "     1) Set pulse duration and duty cycle",
            "     2) Run experiment - This experiment will not stop on its own. To stop the experiment click \"STOP Experiment\". "
            "If it doesn't stop within a second click \"STOP Experiment\" again.",
            "     3) The user can now save the plot figure and data as a csv file is they wish.",
            "     4) Pulse duration and duty cycle can be changed and the experiment repeated to observe changes."
            ])
        self.intro_text = QPlainTextEdit(readOnly=True, plainText = self.intro_instructions)
        self.intro_text.backgroundVisible = False
        self.intro_text.wordWrapMode = True
        self.intro_text.zoomIn(2)
        self.instruction_tabs.addTab(self.intro_text, "Instruction Text")
        
        self.label = QLabel(self)
        self.image_file = os.path.join(os.getcwd(), 'Capacitor Schematic.jpg')
        self.circuit_image = QPixmap(self.image_file)
        
        self.label.setPixmap(self.circuit_image)
        
        self.instruction_tabs.addTab(self.label, "Circuit Diagram")
        
        self.layout.addWidget(self.instruction_tabs, 2, 0, 1, 4)
        
        self.setLayout(self.layout)
        
        self.search_for_devices()
    
    def search_for_devices(self) :
        """
        Runs test to find ports that Arduinos are connected to.

        Returns
        -------
        None.

        """
        self.avail_ports = self.uController.serial.get_avail_ports()
        
        self.ports_selection.clear()
        if len(self.avail_ports) > 0 and not self.uController.connected :
            self.lbl_connection_status.setText("Connection Status: Disconnected")
            for port in self.avail_ports :
                self.ports_selection.addItem( port )
            self.connect_btn.setEnabled(True)
        else :
            self.connect_btn.setEnabled(False)
    
    def connect_init(self) :
        """
        Establishes connect to Arduino.

        Returns
        -------
        None.

        """
        self.lbl_connection_status.setText("Connection Status: Attempting to Connect")
        self.btn_check_devices.setEnabled(False)
        self.ports_selection.setEnabled(False)
        self.connect_btn.setEnabled(False)
        port = self.avail_ports[ self.ports_selection.currentIndex() ]
        self.uController.port = port
        
        self.thread = connect_thread(uController=self.uController, result_q=self.result_q)
        self.thread.finished.connect(self.connect_complete)
        self.thread.start()
    
    def connect_complete(self) :
        success = self.result_q.get()
        
        if success == 'Success' :
            self.lbl_connection_status.setText("Connection Status: Connected")
            self.parent.main_tabs.setTabEnabled(1, True)
            self.parent.main_tabs.setTabEnabled(2, True)
        else :
            self.lbl_connection_status.setText("Connection Status: Connection Attempt Failed")
            self.btn_check_devices.setEnabled(True)
            self.ports_selection.setEnabled(True)





class dis_charge_exp_controls(QWidget) :
    """
    Experimental controls widget.
    The experiment is run here and the results are displayed with a plot.
    """
    def __init__(self, parent) :
        """
        Constructs exp_controls class.

        Parameters
        ----------
        parent : MainWindow object
            MainWindow object that this object belongs to.

        Returns
        -------
        None.

        """
        super(QWidget, self).__init__(parent)
        
        self.parent = parent
        
        self.uController = self.parent.uController
        
        self.folder = os.getcwd()
        self.fil = None
        self.xy_data = []
        self.result_q = Queue()
        
        max_widget_width = 300
        
        self.layout = QGridLayout(self) # plot and progress bar
        
        self.plot_layout = QGridLayout()
        self.data_plot = MplCanvas(self, width=5, height=4, dpi=100)
        self.data_plot_toolbar = NavigationToolbar(self.data_plot, self)
        self.plot_layout.addWidget(self.data_plot_toolbar, 0, 0, 1, 1)
        self.plot_layout.addWidget(self.data_plot, 1, 0, 4, 1)
        self.layout.addLayout(self.plot_layout, 0, 0, 2, 1)
        
        self.exp_prog_bar = QProgressBar()
        self.layout.addWidget(self.exp_prog_bar, 2, 0, 1, 2)
        
        
        self.control_layout = QGridLayout() # controls to run experiment
        row = 0
        
        
        # Discharge the Capacitory
        label = QLabel( "To remove the Capacitory, first:" )
        label.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(label, row, 0); row += 1
        
        self.btn_discharge_cap = QPushButton("Discharge Capacitor")
        self.btn_discharge_cap.setMaximumWidth(max_widget_width)
        self.btn_discharge_cap.clicked.connect(self.discharge_cap)
        self.control_layout.addWidget(self.btn_discharge_cap, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set Vcc
        self.lbl_Vcc = QLabel(f"Set Vcc [V]: (Current: {self.uController.Vcc})")
        self.lbl_Vcc.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_Vcc, row, 0); row += 1
        
        self.qcb_Vcc_choice = QComboBox(self)
        self.qcb_Vcc_choice.addItem("3.3 V")
        self.qcb_Vcc_choice.addItem("5 V")
        self.qcb_Vcc_choice.currentIndexChanged.connect(self.update_Vcc_choice)
        self.control_layout.addWidget(self.qcb_Vcc_choice, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set resistance value
        self.lbl_resistance = QLabel( f"Resistance [Ohms]: (Current: {self.uController.R:.0f} Ohms)" )
        self.lbl_resistance.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_resistance, row, 0); row += 1
        
        self.qle_resistance = QLineEdit()
        self.qle_resistance.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.qle_resistance, row, 0); row += 1
        
        self.btn_set_resistance = QPushButton("Update Resistance")
        self.btn_set_resistance.setMaximumWidth( max_widget_width )
        self.btn_set_resistance.clicked.connect(self.update_resistance)
        self.control_layout.addWidget(self.btn_set_resistance, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set capacitance value
        self.lbl_capacitance = QLabel( f'Capacitance [uF]: (Current: {self.uController.C:.0f} uF)' )
        self.lbl_capacitance.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_capacitance, row, 0); row += 1
        
        self.qle_capacitance = QLineEdit()
        self.qle_capacitance.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.qle_capacitance, row, 0); row += 1
        
        self.btn_set_capacitance = QPushButton("Update Capacitance")
        self.btn_set_capacitance.setMaximumWidth( max_widget_width )
        self.btn_set_capacitance.clicked.connect(self.update_capacitance)
        self.control_layout.addWidget(self.btn_set_capacitance, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set experiment duration
        self.lbl_exp_dur_factor = QLabel( f"Experiment duration factor: (Current: {self.uController.exp_dur_factor:.0f})" )
        self.lbl_exp_dur_factor.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_exp_dur_factor, row, 0); row += 1
        
        label = QLabel( "Experiment duration = factor * tc")
        label.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(label, row, 0); row += 1
        
        self.qle_set_exp_dur_factor = QLineEdit()
        self.qle_set_exp_dur_factor.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.qle_set_exp_dur_factor, row, 0); row += 1
        
        self.btn_set_exp_dur_factor = QPushButton("Update Experiment Duration Factor")
        self.btn_set_exp_dur_factor.setMaximumWidth( max_widget_width )
        self.btn_set_exp_dur_factor.clicked.connect(self.update_exp_dur_factor)
        self.control_layout.addWidget(self.btn_set_exp_dur_factor, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Run experiment
        label = QLabel("(Dis)Charge Experiment:")
        label.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(label, row, 0); row += 1
        
        self.qcb_dis_charge_choice = QComboBox(self)
        self.qcb_dis_charge_choice.addItem("Charge")
        self.qcb_dis_charge_choice.addItem("Discharge")
        self.qcb_dis_charge_choice.currentIndexChanged.connect(self.update_dis_charge_choice)
        self.control_layout.addWidget(self.qcb_dis_charge_choice, row, 0); row += 1
        
        self.btn_run_exp_dis_charge = QPushButton("Run Experiment")
        self.btn_run_exp_dis_charge.setMaximumWidth( max_widget_width )
        self.btn_run_exp_dis_charge.clicked.connect(lambda: self.run_dis_charge_exp(True))
        self.control_layout.addWidget(self.btn_run_exp_dis_charge, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Save Results
        label = QLabel("Save Current Results")
        label.setMaximumWidth(max_widget_width)
        self.control_layout.addWidget(label, row, 0); row += 1
        
        self.btn_save_data = QPushButton("Save Data")
        self.btn_save_data.setMaximumWidth( max_widget_width )
        self.btn_save_data.clicked.connect(self.save_data)
        self.control_layout.addWidget(self.btn_save_data, row, 0); row += 1
        
        
        
        self.layout.addLayout(self.control_layout, 0, 1, 1, 1)
        self.setLayout(self.layout)
    
    def discharge_cap(self) :
        self.uController.dis_charge_choice = -1
        self.run_dis_charge_exp(False)
    
    def update_Vcc_choice(self) :
        status = self.qcb_Vcc_choice.currentText()
        if status == "3.3 V" :
            new_Vcc = 3.3
        elif status == "5 V" :
            new_Vcc = 5.0
        self.disable_controls()
        successful = self.uController.serial.set_parameter( f'j;{new_Vcc}' )
        self.enable_controls()
        if successful :
            self.update_param_lbls()
        else :
            title = "Set Parameter Error"
            warning_msg = '\n'.join([
                "An error was encountered while attempting to update ",
                "a parameter. Ensure the Arduino is connected and try again."
                ])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
    
    def update_resistance(self) :
        new_R = self.qle_resistance.text()
        
        try :
            new_R = float(new_R)
        except :
            title = "Resistor - Value Error"
            warning_msg = '\n'.join(["Resistance must be a number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        
        if new_R < 0 :
            title = "Resistor - Value Error"
            warning_msg = '\n'.join(["Resistance must be a positive number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        elif new_R < 250 :
            title = "Resistor Value Error - FATAL ERROR"
            warning_msg = '\n'.join([
                "Resistor values less than 250 Ohms are not accepted. ",
                "This is to protect the Arduino as it can only supply a ",
                "limited current of 50 mA. Use a higher value resistor to ",
                "limit current and protect your Arduino."
                ])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        else :
            successful = self.uController.serial.set_parameter( f'f;{new_R:.3f}' )
            if successful :
                self.update_param_lbls()
            else :
                title = "Set Parameter Error"
                warning_msg = '\n'.join([
                    "An error was encountered while attempting to update ",
                    "a parameter. Ensure the Arduino is connected and try again."
                    ])
                warning_window = warningWindow(self)
                warning_window.build_window(title=title, msg=warning_msg)
    
    def update_capacitance(self) :
        new_val = self.qle_capacitance.text()
        
        try :
            new_val = float(new_val)
        except :
            title = "Capacitor - Value Error"
            warning_msg = '\n'.join(["Capacitance must be a number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        
        if new_val < 0 :
            title = "Capacitor - Value Error"
            warning_msg = '\n'.join(["Capacitance must be a positive number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        else :
            new_val *= 1e-6
            successful = self.uController.serial.set_parameter( f'h;{new_val:.3e}' )
            if successful :
                self.update_param_lbls()
            else :
                title = "Set Parameter Error"
                warning_msg = '\n'.join([
                    "An error was encountered while attempting to update ",
                    "a parameter. Ensure the Arduino is connected and try again."
                    ])
                warning_window = warningWindow(self)
                warning_window.build_window(title=title, msg=warning_msg)
    
    def update_exp_dur_factor(self) :
        new_val = self.qle_set_exp_dur_factor.text()
        
        try :
            new_val = int( float(new_val) )
        except :
            title = "Experiment Duration Factor - Value Error"
            warning_msg = '\n'.join(["Experiment Duration Factor must be a number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        
        if new_val < 1 :
            title = "Experiment Duration Factor - Value Error"
            warning_msg = '\n'.join(["Experiment Duration Factor must be an integer greater than 0."])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        else :
            successful = self.uController.serial.set_parameter( f'l;{new_val}' )
            if successful :
                self.update_param_lbls()
            else :
                title = "Set Parameter Error"
                warning_msg = '\n'.join([
                    "An error was encountered while attempting to update ",
                    "a parameter. Ensure the Arduino is connected and try again."
                    ])
                warning_window = warningWindow(self)
                warning_window.build_window(title=title, msg=warning_msg)
    
    def update_param_lbls(self) :
        self.disable_controls()
        # self.uController.update_all_parameters()
        
        self.thread = update_uController_params(uController=self.uController)
        self.thread.finished.connect(self.update_param_lbls_complete)
        self.thread.start()
    
    def update_param_lbls_complete(self) :
        Vcc = self.uController.Vcc
        if Vcc == 3.3 :
            self.qcb_Vcc_choice.setCurrentIndex(0)
        elif Vcc == 5.0 :
            self.qcb_Vcc_choice.setCurrentIndex(1)
        self.lbl_Vcc.setText(f"Set Vcc [V]: (Current: {self.uController.Vcc})")
        
        self.lbl_resistance.setText( f"Resistance [Ohms]: (Current: {self.uController.R:.0f} Ohms)" )
        self.lbl_capacitance.setText( f"Capacitance [uF]: (Current: {self.uController.C:.0f} uF)" )
        self.lbl_exp_dur_factor.setText( f"Experiment duration factor: (Current: {self.uController.exp_dur_factor:.0f})" )
        self.enable_controls()
    
    def update_dis_charge_choice(self) :
        status = self.qcb_dis_charge_choice.currentText()
        if status == "Charge" :
            self.uController.dis_charge_choice = 1
        elif status == "Discharge" :
            self.uController.dis_charge_choice = 0
    
    def exp_prog_update(self, i) :
        self.exp_prog_bar.setValue( i )
    
    def disable_controls(self) :
        """
        Disables the experiment controls.

        Returns
        -------
        None.

        """
        self.qcb_Vcc_choice.setEnabled(False)
        self.btn_discharge_cap.setEnabled(False)
        self.btn_set_resistance.setEnabled(False)
        self.btn_set_capacitance.setEnabled(False)
        self.btn_set_exp_dur_factor.setEnabled(False)
        self.qcb_dis_charge_choice.setEnabled(False)
        self.btn_run_exp_dis_charge.setEnabled(False)
        self.btn_save_data.setEnabled(False)
        self.parent.main_tabs.setTabEnabled(0, False)
        self.parent.main_tabs.setTabEnabled(2, False)
    
    def enable_controls(self) :
        """
        Enables the experiment controls.

        Returns
        -------
        None.

        """
        self.qcb_Vcc_choice.setEnabled(True)
        self.btn_discharge_cap.setEnabled(True)
        self.btn_set_resistance.setEnabled(True)
        self.btn_set_capacitance.setEnabled(True)
        self.btn_set_exp_dur_factor.setEnabled(True)
        self.qcb_dis_charge_choice.setEnabled(True)
        self.btn_run_exp_dis_charge.setEnabled(True)
        self.btn_save_data.setEnabled(True)
        self.parent.main_tabs.setTabEnabled(0, True)
        self.parent.main_tabs.setTabEnabled(2, True)
    
    def exp_complete(self) :
        self.enable_controls()
        if self.uController.dis_charge_choice in [0, 1] :
            self.xy_data = self.result_q.get()
    
    def run_dis_charge_exp(self, update_exp_type=True) :
        if update_exp_type :
            self.update_dis_charge_choice()
        
        self.disable_controls()
        
        vals = [
            self.uController.R, self.uController.C, 
            self.uController.exp_dur_factor, 
            ]
        
        if 0 in vals :
            self.update_param_lbls()
        
        self.running_exp = dis_charge_exp(uController=self.uController, result_q=self.result_q, canvas=self.data_plot)
        self.running_exp.notifyProgress.connect(self.exp_prog_update)
        self.running_exp.finished.connect(self.exp_complete)
        self.running_exp.start()
    
    def save_data(self) :
        fil = QFileDialog.getSaveFileName(self, "Select Save File", self.folder, "CSV files (*.csv)")[0]
        
        if fil == '' :
            return
        
        (self.folder, self.fil) = os.path.split( fil )
        
        fil = self.fil.split('.')
        
        if len(fil) == 1 :
            self.fil = fil[0] + '.csv'
        elif fil[-1] != 'csv' :
            fil[-1] = 'csv'
            self.fil = '.'.join(fil)
        
        header = '\n'.join([
            f"Resistor: {self.uController.R} Ohms",
            f"Capacitor: {self.uController.C} uF"
            ])
        
        with open(os.path.join(self.folder, self.fil), 'w') as fil :
            np.savetxt(fil, self.xy_data, fmt='%.7e', delimiter=',', newline='\n', header=header, footer='', comments='# ', encoding=None)

class freq_exp_controls(QWidget) :
    def __init__(self, parent) :
        super(QWidget, self).__init__(parent)
        
        self.parent = parent
        
        self.uController = self.parent.uController
        
        self.folder = os.getcwd()
        self.fil = None
        self.xy_data = []
        self.result_q = Queue()
        
        max_widget_width = 300
        
        self.layout = QGridLayout(self) # plot and progress bar
        
        self.exp_prog_bar = QProgressBar()
        self.layout.addWidget(self.exp_prog_bar, 5, 0, 1, 3)
        
        self.plot_layout = QGridLayout()
        self.data_plot = MplCanvas(self, width=5, height=4, dpi=100)
        self.data_plot_toolbar = NavigationToolbar(self.data_plot, self)
        self.plot_layout.addWidget(self.data_plot_toolbar, 0, 0, 1, 1)
        self.plot_layout.addWidget(self.data_plot, 1, 0, 4, 1)
        self.layout.addLayout(self.plot_layout, 0, 0, 2, 1)
        
        #self.exp_prog_bar = QProgressBar()
        #self.layout.addWidget(self.exp_prog_bar, 2, 0, 1, 2)
        
        
        self.control_layout = QGridLayout() # controls to run experiment
        row = 0
        
        
        # Discharge the Capacitory
        label = QLabel( "To remove the Capacitory, first:" )
        label.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(label, row, 0); row += 1
        
        self.btn_discharge_cap = QPushButton("Discharge Capacitor")
        self.btn_discharge_cap.setMaximumWidth(max_widget_width)
        self.btn_discharge_cap.clicked.connect(self.discharge_cap)
        self.control_layout.addWidget(self.btn_discharge_cap, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set Vcc
        self.lbl_Vcc = QLabel(f"Set Vcc [V]: (Current: {self.uController.Vcc})")
        self.lbl_Vcc.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_Vcc, row, 0); row += 1
        
        self.qcb_Vcc_choice = QComboBox(self)
        self.qcb_Vcc_choice.addItem("3.3 V")
        self.qcb_Vcc_choice.addItem("5 V")
        self.qcb_Vcc_choice.currentIndexChanged.connect(self.update_Vcc_choice)
        self.control_layout.addWidget(self.qcb_Vcc_choice, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set resistance value
        self.lbl_resistance = QLabel( f"Resistance [Ohms]: (Current: {self.uController.R:.0f} Ohms)" )
        self.lbl_resistance.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_resistance, row, 0); row += 1
        
        self.qle_resistance = QLineEdit()
        self.qle_resistance.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.qle_resistance, row, 0); row += 1
        
        self.btn_set_resistance = QPushButton("Update Resistance")
        self.btn_set_resistance.setMaximumWidth( max_widget_width )
        self.btn_set_resistance.clicked.connect(self.update_resistance)
        self.control_layout.addWidget(self.btn_set_resistance, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set capacitance value
        self.lbl_capacitance = QLabel( f'Capacitance [uF]: (Current: {self.uController.C:.0f} uF)' )
        self.lbl_capacitance.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_capacitance, row, 0); row += 1
        
        self.qle_capacitance = QLineEdit()
        self.qle_capacitance.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.qle_capacitance, row, 0); row += 1
        
        self.btn_set_capacitance = QPushButton("Update Capacitance")
        self.btn_set_capacitance.setMaximumWidth( max_widget_width )
        self.btn_set_capacitance.clicked.connect(self.update_capacitance)
        self.control_layout.addWidget(self.btn_set_capacitance, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set pulse duration
        self.lbl_pulse_dur = QLabel( f"Pulse Duration [ms]: (Current: {self.uController.pulse_duration:.0f} ms)" )
        self.lbl_pulse_dur.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_pulse_dur, row, 0); row += 1
        
        self.qle_pulse_dur = QLineEdit()
        self.qle_pulse_dur.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.qle_pulse_dur, row, 0); row += 1
        
        self.btn_set_pulse_dur = QPushButton("Update Pulse Duration")
        self.btn_set_pulse_dur.setMaximumWidth( max_widget_width )
        self.btn_set_pulse_dur.clicked.connect(self.update_pulse_dur)
        self.control_layout.addWidget(self.btn_set_pulse_dur, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Set duty cycle
        self.lbl_pulse_dc = QLabel( f"Pulse Duty Cycle [%]: (Current: {self.uController.pulse_duty_cycle:.0f}%)" )
        self.lbl_pulse_dc.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_pulse_dc, row, 0); row += 1
        
        self.qle_pulse_dc = QLineEdit()
        self.qle_pulse_dc.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.qle_pulse_dc, row, 0); row += 1
        
        self.btn_set_pulse_dc = QPushButton("Update Pulse Duty Cycle")
        self.btn_set_pulse_dc.setMaximumWidth( max_widget_width )
        self.btn_set_pulse_dc.clicked.connect(self.update_pulse_dc)
        self.control_layout.addWidget(self.btn_set_pulse_dc, row, 0); row += 1
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Run experiment
        label = QLabel("Pulse Experiment:")
        label.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(label, row, 0); row += 1
        
        self.btn_run_pulse_exp = QPushButton("Run Experiment")
        self.btn_run_pulse_exp.setMaximumWidth( max_widget_width )
        self.btn_run_pulse_exp.clicked.connect(self.run_pulse_exp)
        self.control_layout.addWidget(self.btn_run_pulse_exp, row, 0); row += 1
        
        self.btn_stop_pulse_exp = QPushButton("STOP Experiment")
        self.btn_stop_pulse_exp.setMaximumWidth( max_widget_width )
        self.btn_stop_pulse_exp.clicked.connect(self.stop_experiment)
        self.control_layout.addWidget(self.btn_stop_pulse_exp, row, 0); row += 1
        self.btn_stop_pulse_exp.setEnabled(False)
        
        self.control_layout.addWidget(QHLine(), row, 0); row += 1
        
        
        # Save Results
        label = QLabel("Save Current Results")
        label.setMaximumWidth(max_widget_width)
        self.control_layout.addWidget(label, row, 0); row += 1
        
        self.btn_save_data = QPushButton("Save Data")
        self.btn_save_data.setMaximumWidth( max_widget_width )
        self.btn_save_data.clicked.connect(self.save_data)
        self.control_layout.addWidget(self.btn_save_data, row, 0); row += 1
        
        
        
        self.layout.addLayout(self.control_layout, 0, 1, 1, 2)
        self.setLayout(self.layout)
    
    def exp_prog_update(self, i) :
        self.exp_prog_bar.setValue( i )
    
    def disable_controls(self) :
        self.btn_discharge_cap.setEnabled(False)
        self.qcb_Vcc_choice.setEnabled(False)
        self.btn_set_resistance.setEnabled(False)
        self.btn_set_capacitance.setEnabled(False)
        self.btn_set_pulse_dur.setEnabled(False)
        self.btn_set_pulse_dc.setEnabled(False)
        self.btn_run_pulse_exp.setEnabled(False)
        self.btn_stop_pulse_exp.setEnabled(False)
        self.btn_save_data.setEnabled(False)
        self.parent.main_tabs.setTabEnabled(0, False)
        self.parent.main_tabs.setTabEnabled(1, False)
    
    def enable_controls(self) :
        self.btn_discharge_cap.setEnabled(True)
        self.qcb_Vcc_choice.setEnabled(True)
        self.btn_set_resistance.setEnabled(True)
        self.btn_set_capacitance.setEnabled(True)
        self.btn_set_pulse_dur.setEnabled(True)
        self.btn_set_pulse_dc.setEnabled(True)
        self.btn_run_pulse_exp.setEnabled(True)
        self.btn_stop_pulse_exp.setEnabled(False)
        self.btn_save_data.setEnabled(True)
        self.parent.main_tabs.setTabEnabled(0, True)
        self.parent.main_tabs.setTabEnabled(1, True)
    
    def discharge_cap(self) :
        self.uController.dis_charge_choice = -1
        self.run_dis_charge_exp()
    
    def update_Vcc_choice(self) :
        status = self.qcb_Vcc_choice.currentText()
        if status == "3.3 V" :
            new_Vcc = 3.3
        elif status == "5 V" :
            new_Vcc = 5.0
        self.disable_controls()
        successful = self.uController.serial.set_parameter( f'j;{new_Vcc}' )
        self.enable_controls()
        if successful :
            self.update_param_lbls()
        else :
            title = "Set Parameter Error"
            warning_msg = '\n'.join([
                "An error was encountered while attempting to update ",
                "a parameter. Ensure the Arduino is connected and try again."
                ])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
    
    def update_resistance(self) :
        new_R = self.qle_resistance.text()
        
        try :
            new_R = float(new_R)
        except :
            title = "Resistor - Value Error"
            warning_msg = '\n'.join(["Resistance must be a number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        
        if new_R < 0 :
            title = "Resistor - Value Error"
            warning_msg = '\n'.join(["Resistance must be a positive number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        elif new_R < 250 :
            title = "Resistor Value Error - FATAL ERROR"
            warning_msg = '\n'.join([
                "Resistor values less than 250 Ohms are not accepted. ",
                "This is to protect the Arduino as it can only supply a ",
                "limited current of 50 mA. Use a higher value resistor to ",
                "limit current and protect your Arduino."
                ])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        else :
            successful = self.uController.serial.set_parameter( f'f;{new_R:.3f}' )
            if successful :
                self.update_param_lbls()
            else :
                title = "Set Parameter Error"
                warning_msg = '\n'.join([
                    "An error was encountered while attempting to update ",
                    "a parameter. Ensure the Arduino is connected and try again."
                    ])
                warning_window = warningWindow(self)
                warning_window.build_window(title=title, msg=warning_msg)
    
    def update_capacitance(self) :
        new_val = self.qle_capacitance.text()
        
        try :
            new_val = float(new_val)
        except :
            title = "Capacitor - Value Error"
            warning_msg = '\n'.join(["Capacitance must be a number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        
        if new_val < 0 :
            title = "Capacitor - Value Error"
            warning_msg = '\n'.join(["Capacitance must be a positive number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        else :
            new_val *= 1e-6
            successful = self.uController.serial.set_parameter( f'h;{new_val:.3e}' )
            if successful :
                self.update_param_lbls()
            else :
                title = "Set Parameter Error"
                warning_msg = '\n'.join([
                    "An error was encountered while attempting to update ",
                    "a parameter. Ensure the Arduino is connected and try again."
                    ])
                warning_window = warningWindow(self)
                warning_window.build_window(title=title, msg=warning_msg)
    
    def update_pulse_dur(self) :
        new_val = self.qle_pulse_dur.text()
        
        try :
            new_val = int( float(new_val) )
        except :
            title = "Pulse Duration - Value Error"
            warning_msg = '\n'.join(["Pulse Duration must be a number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        
        if new_val < 10 :
            title = "Pulse Duration - Value Error"
            warning_msg = '\n'.join(["Pulse Duration must be an integer equal to 10 or greater."])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        else :
            successful = self.uController.serial.set_parameter( f'r;{new_val:.0f}' )
            if successful :
                self.update_param_lbls()
            else :
                title = "Set Parameter Error"
                warning_msg = '\n'.join([
                    "An error was encountered while attempting to update ",
                    "a parameter. Ensure the Arduino is connected and try again."
                    ])
                warning_window = warningWindow(self)
                warning_window.build_window(title=title, msg=warning_msg)
    
    def update_pulse_dc(self) :
        new_val = self.qle_pulse_dc.text()
        
        try :
            new_val = int( float(new_val) )
        except :
            title = "Pulse Duty Cycle - Value Error"
            warning_msg = '\n'.join(["Pulse Duty Cycle must be a number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        
        if new_val < 0 or new_val > 100 :
            title = "Pulse Duty Cycle - Value Error"
            warning_msg = '\n'.join(["Pulse Duty Cycle must be an integer between 0 and 100 inclusive."])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        else :
            successful = self.uController.serial.set_parameter( f't;{new_val:.0f}' )
            if successful :
                self.update_param_lbls()
            else :
                title = "Set Parameter Error"
                warning_msg = '\n'.join([
                    "An error was encountered while attempting to update ",
                    "a parameter. Ensure the Arduino is connected and try again."
                    ])
                warning_window = warningWindow(self)
                warning_window.build_window(title=title, msg=warning_msg)
    
    def update_param_lbls(self) :
        self.disable_controls()
        # self.uController.update_all_parameters()
        
        self.thread = update_uController_params(uController=self.uController)
        self.thread.finished.connect(self.update_param_lbls_complete)
        self.thread.start()
    
    def update_param_lbls_complete(self) :
        Vcc = self.uController.Vcc
        if Vcc == 3.3 :
            self.qcb_Vcc_choice.setCurrentIndex(0)
        elif Vcc == 5.0 :
            self.qcb_Vcc_choice.setCurrentIndex(1)
        self.lbl_Vcc.setText(f"Set Vcc [V]: (Current: {self.uController.Vcc})")
        
        self.lbl_resistance.setText( f"Resistance [Ohms]: (Current: {self.uController.R:.0f} Ohms)" )
        self.lbl_capacitance.setText( f"Capacitance [uF]: (Current: {self.uController.C:.0f} uF)" )
        self.lbl_pulse_dur.setText( f"Pulse Duration [ms]: (Current: {self.uController.pulse_duration:.0f} ms)" )
        self.lbl_pulse_dc.setText( f"Pulse Duty Cycle [%]: (Current: {self.uController.pulse_duty_cycle:.0f}%)" )
        self.enable_controls()
    
    def exp_complete(self) :
        self.enable_controls()
        if self.uController.dis_charge_choice in [0, 1] :
            self.xy_data = self.result_q.get()
    
    def run_pulse_exp(self) :
        self.disable_controls()
        self.btn_stop_pulse_exp.setEnabled(True)
        
        self.running_exp = pulse_exp(uController=self.uController, result_q=self.result_q, canvas=self.data_plot)
        self.running_exp.finished.connect(self.exp_complete)
        self.running_exp.start()
    
    def stop_experiment(self) :
        self.uController.serial.send_command('stop')
    
    def save_data(self) :
        fil = QFileDialog.getSaveFileName(self, "Select Save File", self.folder, "CSV files (*.csv)")[0]
        
        if fil == '' :
            return
        
        (self.folder, self.fil) = os.path.split( fil )
        
        fil = self.fil.split('.')
        
        if len(fil) == 1 :
            self.fil = fil[0] + '.csv'
        elif fil[-1] != 'csv' :
            fil[-1] = 'csv'
            self.fil = '.'.join(fil)
        
        header = '\n'.join([
            f"Resistor: {self.uController.R} Ohms",
            f"Capacitor: {self.uController.C} uF",
            f"Pulse Duration: {self.uController.pulse_duration} ms",
            f"Pulse Duty Cycle: {self.uController.pulse_duty_cycle} %",
            ])
        
        with open(os.path.join(self.folder, self.fil), 'w') as fil :
            np.savetxt(fil, self.xy_data, fmt='%.7e', delimiter=',', newline='\n', header=header, footer='', comments='# ', encoding=None)
    
    def run_dis_charge_exp(self) :
        self.disable_controls()
        
        vals = [
            self.uController.R, self.uController.C, 
            self.uController.exp_dur_factor, 
            ]
        
        if 0 in vals :
            self.update_param_lbls()
        
        self.running_exp = dis_charge_exp(uController=self.uController, result_q=self.result_q, canvas=self.data_plot)
        self.running_exp.notifyProgress.connect(self.exp_prog_update)
        self.running_exp.finished.connect(self.exp_complete)
        self.running_exp.start()











class update_uController_params(QThread) :
    def __init__(self, uController) :
        QThread.__init__(self)
        self.uController = uController
    
    def run(self) :
        self.uController.update_all_parameters()


class connect_thread(QThread) :
    def __init__(self, uController, result_q) :
        QThread.__init__(self)
        self.uController = uController
        self.result_q = result_q
    
    def run(self) :
        success = self.uController.serial.connect()
        if success == 'Success' :
            self.uController.update_all_parameters()
        self.result_q.put( success )

class dis_charge_exp(QThread) :
    notifyProgress = pyqtSignal(int)
    def __init__(self, uController, result_q=None, canvas=None) :
        QThread.__init__(self)
        self.uController = uController
        self.canvas = canvas
        
        self.result_q = result_q
        self.x_data = []
        self.y_data = []
    
    def update_plot(self, fit=False) :
        self.canvas.axes.cla()
        self.canvas.axes.plot(self.x_data, self.y_data, '.')
        
        if fit and self.uController.dis_charge_choice in [0, 1] \
            and len(self.x_data)>5 :
            Vcc = self.uController.Vcc
            tc = self.uController.R * self.uController.C *1e-6
            params = lmfit.Parameters()
            params.add('Vcc', value=Vcc, min=0.8*Vcc, vary=True)
            params.add('tc', value=tc, min=0.8*tc, max=1.2*tc, vary=True)
            if self.uController.dis_charge_choice == 0 :
                model = lmfit.Model( cap_discharge )
            else :
                params.add('offset', value=0, vary=True)
                model = lmfit.Model( cap_charge )
            
            fit_result = model.fit(self.y_data, params, x=self.x_data, nan_policy='omit')
            self.canvas.axes.plot(self.x_data, fit_result.best_fit)
            
            txt_x = 0.6 * self.x_data[-1] 
            txt_y = 0.5 * self.uController.Vcc
            txt_dy = 0.05 * self.uController.Vcc
            self.canvas.axes.text(txt_x, txt_y, "Fit Results:", fontsize=15); txt_y -= txt_dy
            # self.canvas.axes.text(txt_x, txt_y, f"Vcc: {fit_result.params['Vcc'].value:.3f} V", fontsize=15); txt_y -= txt_dy
            self.canvas.axes.text(txt_x, txt_y, f"TC: {fit_result.params['tc'].value:.3f} s", fontsize=15); txt_y -= txt_dy
        
        self.canvas.axes.set_xlabel( 'Time [s]' )
        self.canvas.axes.set_ylabel( 'Voltage Across Capacitor [V]' )
        
        self.canvas.fig.tight_layout()
        self.canvas.draw()
    
    def cap_prepping(self) :
        if self.uController.dis_charge_choice == 0 :
            text = "Charging Capacitor"
        elif self.uController.dis_charge_choice in [-1, 1] :
            text = "Discharging Capacitor"
        else :
            text = "invalid experiment choice"
        self.canvas.axes.cla()
        self.canvas.axes.text(0.3, 0.45, text)
        self.canvas.draw()
        
        while True :
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f", end_message=True)
            
            if result[0] in [None, 'end'] :
                break
            percent_complete = 100 * result[0] / self.uController.Vcc
            self.notifyProgress.emit( percent_complete )
        
        if self.uController.dis_charge_choice == -1 :
            self.canvas.axes.cla()
            self.canvas.axes.text(0.3, 0.45, 'Capacitor discharged.')
            self.canvas.draw()
    
    def run(self) :
        itr = 0
        percent_last_update = 0
        x_offset = 0
        
        next_frame_t = current_time()
        exp_t = self.uController.R * 1e-6*self.uController.C * self.uController.exp_dur_factor
        t_start = current_time()
        
        if self.uController.dis_charge_choice == -1 :
            self.uController.serial.send_command('v')
            self.cap_prepping()
            return
        elif self.uController.dis_charge_choice == 0 :
            self.uController.serial.send_command('w')
            self.cap_prepping()
            time_sleep(1)
            self.uController.serial.send_command('b')
        elif self.uController.dis_charge_choice == 1 :
            self.uController.serial.send_command('v')
            self.cap_prepping()
            time_sleep(1)
            self.uController.serial.send_command('a')
        else :
            return False
        
        self.x_data = []
        self.y_data = []
        
        while True :
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f", end_message=True)
            
            print( result )
            
            if result[0] == 'end' :
                break
            if itr == 0 :
                x_offset = result[0]/(1000*1000)
            itr += 1
            self.x_data.append( result[0]/(1000*1000)-x_offset )
            self.y_data.append( result[1] )
            
            percent_complete = 100*((current_time()-t_start)/exp_t)
            self.notifyProgress.emit( percent_complete )
            
            if self.canvas is not None and current_time() >= next_frame_t :
                next_frame_t += 0.1
                self.update_plot()
        
        self.notifyProgress.emit( 100 )
        self.update_plot(True)
        
        
        if self.result_q is not None :
            self.result_q.put( np.transpose([self.x_data, self.y_data]) )

class pulse_exp(QThread) :
    def __init__(self, uController, result_q=None, canvas=None) :
        QThread.__init__(self)
        self.uController = uController
        self.canvas = canvas
        
        self.result_q = result_q
        self.x_data = []
        self.y_data = []
    
    def update_plot(self) :
        self.canvas.axes.cla()
        self.canvas.axes.plot(self.x_data, self.y_data)
        self.canvas.fig.tight_layout()
        self.canvas.draw()
    
    def run(self) :
        self.uController.serial.send_command('q')
        
        next_frame_t = current_time()
        itr = 0
        while True :
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f", end_message=True)
            
            if result[0] == 'end' :
                break
            if itr == 0 :
                x_offset = result[0]/(1000*1000)
            itr += 1
            self.x_data.append( result[0]/(1000*1000)-x_offset )
            self.y_data.append( result[1] )
            if self.canvas is not None and current_time() >= next_frame_t :
                next_frame_t += 0.1
                self.update_plot()
        
        if self.result_q is not None :
            self.result_q.put( np.transpose([self.x_data, self.y_data]) )














class QHLine(QFrame):
    """
    """
    def __init__(self):
        """
        Plots a horizontal line across the GUI.

        Returns
        -------
        None.

        """
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)

class QVLine(QFrame):
    """
    """
    def __init__(self):
        """
        Plots a vertical line across the GUI.dssdfsdfsdfsdf

        Returns
        -------
        None.

        """
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)

class MplCanvas(FigureCanvas) :
    """
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """

        Parameters
        ----------
        parent : object, optional
            This is for the parent object. The default is None.
        width : int, optional
            Sets the width of the canvas. The default is 5.
        height : int, optional
            Sets the height of the canvas. The default is 4.
        dpi : int, optional
            Sets the dpi of the canvas. The default is 100.

        Returns
        -------
        None.

        """
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)

class warningWindow(QDialog):
    """
    Default pop up window to display warnings.
    There are no buttons or selectable options, this window is to display
        simple information to the user and then have the user close it.
    """
    def __init__(self, *args, **kwargs):
        """
        

        Parameters
        ----------
        *args : TYPE
            DESCRIPTION.
        **kwargs : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        super(warningWindow, self).__init__(*args, **kwargs)
        self.title = ''
        self.msg = ''
    
    def set_title(self, title) :
        """
        Set the window's title.

        Parameters
        ----------
        title : str
            Window title.

        Returns
        -------
        None.

        """
        self.title = title
    
    def set_msg(self, msg) :
        """
        Set the window's main message.

        Parameters
        ----------
        msg : str
            Window message.

        Returns
        -------
        None.

        """
        self.msg = msg
    
    def set_text_msgs(self, title, msg) :
        """
        Set window text, title and main message.

        Parameters
        ----------
        title : str
            Window title.
        msg : str
            Window message.

        Returns
        -------
        None.

        """
        self.title = title
        self.msg = msg
    
    def build_window(self, title=None, msg=None) :
        """
        This will create the window and display it.

        Parameters
        ----------
        title : str
            Window title.
        msg : str
            Window message.

        Returns
        -------
        None.

        """
        if title is not None :
            self.title = title
        if msg is not None :
            self.msg = msg
        
        self.setWindowTitle(self.title)
        
        QBtn = QDialogButtonBox.Ok # | QDialogButtonBox.Cancel
        
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        
        label = QLabel(self.msg)
        self.layout.addWidget(label)
        
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        
        self.exec_()






if __name__ == '__main__' :
    app = QApplication(sys.argv)
    window = MainWindow()
    app.exec_()
    window.uController.serial.disconnect()
    sys.exit()












