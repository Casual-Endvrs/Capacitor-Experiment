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
        self.port = '/dev/ttyACM0'
        self.baud = 115200
        self.serial = Arduino(self.port, self.baud, timeout=1, eol='/')
        
        if self.port not in self.serial.get_avail_ports() :
            self.port = self.serial.get_avail_ports()[0]
            self.serial.port = self.port
        
        self.Vcc = 5.
        self.R = 0
        self.C = 0
        self.exp_dur_factor = 0
        self.samples_per_tc = 0
        self.pulse_duration = 0
        self.pulse_duty_cycle = 0
        
        self.dis_charge_choice = 1
    
    def connect(self) :
        print( "Please wait while a connection is established.")
        
        connection_result = self.serial.connect()
        
        if connection_result != 'Success' :
            print( self.serial.get_avail_ports() )
            print( 'Failed to connect to the Arduino' )
        else :
            attempts = 5
            while not self.serial.test_connection() :
                attempts -= 1
                if attempts <= 0 :
                    print( 'Failed to confirm a good connection.' )
                    return False
                time_sleep( 0.15 )
            self.update_all_parameters()
        print( 'Connected Successfully.' )
    
    def update_all_parameters(self) :
        self.Vcc = self.serial.get_parameter('k', 'f')
        self.R = self.serial.get_parameter('g', 'f')
        self.C = self.serial.get_parameter('i', 'f')
        self.exp_dur_factor = self.serial.get_parameter('m', 'f')
        self.samples_per_tc = self.serial.get_parameter('o', 'f')
        
        self.pulse_duration = self.serial.get_parameter('s', 'i')
        self.pulse_duty_cycle = self.serial.get_parameter('u', 'i')

class MainWindow(QMainWindow) :
    def __init__(self) :
        super().__init__()
        
        title = 'Capacitor Experiments'
        self.setWindowTitle(title)
        
        self.uController = arduino()
        self.uController.connect()
        
        main_layout = QVBoxLayout()
        
        intro_tab = intro_page(self)
        dis_charge_exp_tab = dis_charge_exp_controls(self)
        freq_exp_tab = freq_exp_controls(self)
        
        main_tabs = QTabWidget()
        # main_tabs.addTab(intro_tab, "Introduction")
        main_tabs.addTab(dis_charge_exp_tab, "(Dis)Charge Experiment")
        main_tabs.addTab(freq_exp_tab, "Pulse Experiment")
        
        
        main_layout.addWidget(main_tabs)
        self.setCentralWidget(main_tabs)
        
        self.show()

class intro_page(QWidget) :
    """
    Introduction page widget.
    Displays information about the experiment.
    """
    def __init__(self, parent) :
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
        
        self.parent = parent
        
        self.layout = QGridLayout(self)
        
        
        self.instruction_tabs = QTabWidget()
        
        self.intro_instructions = "\n".join([
            "Insert the introduction text here."
            ])
        self.intro_text = QPlainTextEdit(readOnly=True, plainText = self.intro_instructions)
        self.intro_text.backgroundVisible = False
        self.intro_text.wordWrapMode = True
        self.intro_text.zoomIn(2)
        self.instruction_tabs.addTab(self.intro_text, "Instruction Text")
        
        self.label = QLabel(self)
        
        self.instruction_tabs.addTab(self.label, "Circuit Diagram")
        
        self.layout.addWidget(self.instruction_tabs, 1, 0, 1, 4)
        
        self.setLayout(self.layout)



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
        self.layout.addLayout(self.plot_layout, 0, 0)
        
        #self.data_plot = MplCanvas(self, width=5, height=4, dpi=100)
        #self.layout.addWidget(self.data_plot, 0, 0, 5, 1)
        
        self.exp_prog_bar = QProgressBar()
        self.layout.addWidget(self.exp_prog_bar, 5, 0, 1, 2)
        
        
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
        
        
        
        # Set samples per time constant
        self.lbl_samples_per_tc = QLabel( f"Samples per time constant: (Current: {self.uController.samples_per_tc:.0f})" )
        self.lbl_samples_per_tc.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.lbl_samples_per_tc, row, 0); row += 1
        
        self.qle_set_samples_per_tc = QLineEdit()
        self.qle_set_samples_per_tc.setMaximumWidth( max_widget_width )
        self.control_layout.addWidget(self.qle_set_samples_per_tc, row, 0); row += 1
        
        self.btn_set_samples_per_tc = QPushButton("Update Samples/tc")
        self.btn_set_samples_per_tc.setMaximumWidth( max_widget_width )
        self.btn_set_samples_per_tc.clicked.connect(self.update_set_samples_per_tc)
        self.control_layout.addWidget(self.btn_set_samples_per_tc, row, 0); row += 1
        
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
        self.btn_run_exp_dis_charge.clicked.connect(self.run_experiment)
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
        
        
        
        self.layout.addLayout(self.control_layout, 0, 1)
        self.setLayout(self.layout)
        
        self.update_param_lbls()
    
    def discharge_cap(self) :
        self.uController.dis_charge_choice = -1
        self.run_experiment()
    
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
    
    def update_set_samples_per_tc(self) :
        new_val = self.qle_set_samples_per_tc.text()
        
        try :
            new_val = int( float(new_val) )
        except :
            title = "Samples per Time Constant - Value Error"
            warning_msg = '\n'.join(["Experiment Duration Factor must be a number"])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        
        if new_val < 1 :
            title = "Samples per Time Constant - Value Error"
            warning_msg = '\n'.join(["Samples per Time Constant must be an integer greater than 0. "])
            warning_window = warningWindow(self)
            warning_window.build_window(title=title, msg=warning_msg)
            return
        else :
            self.disable_controls()
            successful = self.uController.serial.set_parameter( f'n;{new_val}' )
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
    
    def update_param_lbls(self) :
        self.disable_controls()
        self.uController.update_all_parameters()
        
        Vcc = self.uController.Vcc
        if Vcc == 3.3 :
            self.qcb_Vcc_choice.setCurrentIndex(0)
        elif Vcc == 5.0 :
            self.qcb_Vcc_choice.setCurrentIndex(1)
        self.lbl_Vcc.setText(f"Set Vcc [V]: (Current: {self.uController.Vcc})")
        
        self.lbl_resistance.setText( f"Resistance [Ohms]: (Current: {self.uController.R:.0f} Ohms)" )
        self.lbl_capacitance.setText( f"Capacitance [uF]: (Current: {self.uController.C:.0f} uF)" )
        self.lbl_exp_dur_factor.setText( f"Experiment duration factor: (Current: {self.uController.exp_dur_factor:.0f})" )
        self.lbl_samples_per_tc.setText( f"Samples per time constant: (Current: {self.uController.samples_per_tc:.0f})" )
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
        self.btn_set_samples_per_tc.setEnabled(False)
        self.qcb_dis_charge_choice.setEnabled(False)
        self.btn_run_exp_dis_charge.setEnabled(False)
        self.btn_save_data.setEnabled(False)
        #self.parent.main_tabs.setTabEnabled(0, False)
    
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
        self.btn_set_samples_per_tc.setEnabled(True)
        self.qcb_dis_charge_choice.setEnabled(True)
        self.btn_run_exp_dis_charge.setEnabled(True)
        self.btn_save_data.setEnabled(True)
        #self.parent.main_tabs.setTabEnabled(0, True)
    
    def exp_complete(self) :
        self.enable_controls()
        if self.uController.dis_charge_choice in [0, 1] :
            self.xy_data = self.result_q.get()
    
    def run_experiment(self) :
        self.disable_controls()
        
        vals = [
            self.uController.R, self.uController.C, 
            self.uController.exp_dur_factor, self.uController.samples_per_tc, 
            ]
        
        if 0 in vals :
            self.update_param_lbls()
        
        self.running_exp = dis_charge_exp(uController=self.uController, result_q=self.result_q, canvas=self.data_plot)
        self.running_exp.notifyProgress.connect(self.exp_prog_update)
        self.running_exp.start()
        self.running_exp.finished.connect(self.exp_complete)
    
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
        
        self.plot_layout = QGridLayout()
        self.data_plot = MplCanvas(self, width=5, height=4, dpi=100)
        self.data_plot_toolbar = NavigationToolbar(self.data_plot, self)
        self.plot_layout.addWidget(self.data_plot_toolbar, 0, 0, 1, 1)
        self.plot_layout.addWidget(self.data_plot, 1, 0, 4, 1)
        self.layout.addLayout(self.plot_layout, 0, 0)
        
        # self.exp_prog_bar = QProgressBar()
        # self.layout.addWidget(self.exp_prog_bar, 5, 0, 1, 2)
        
        
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
        self.btn_run_pulse_exp.clicked.connect(self.run_experiment)
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
        
        self.update_param_lbls()
    
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
        #self.parent.main_tabs.setTabEnabled(0, False)
    
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
        #self.parent.main_tabs.setTabEnabled(0, True)
    
    def discharge_cap(self) :
        self.uController.dis_charge_choice = -1
        self.run_experiment()
    
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
        self.uController.update_all_parameters()
        
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
        self.uController.serial.send_command( 'z' )
        self.enable_controls()
        self.xy_data = self.result_q.get()
    
    def run_experiment(self) :
        self.disable_controls()
        self.btn_stop_pulse_exp.setEnabled(True)
        
        self.running_exp = pulse_exp(uController=self.uController, result_q=self.result_q, canvas=self.data_plot)
        self.running_exp.start()
        self.running_exp.finished.connect(self.exp_complete)
    
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
        
        if fit and self.uController.dis_charge_choice in [0, 1] :
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
            self.canvas.axes.text(txt_x, txt_y, f"tc: {fit_result.params['tc'].value:.3f} s", fontsize=15); txt_y -= txt_dy
        
        self.canvas.axes.set_xlabel( 'Time [s]' )
        self.canvas.axes.set_ylabel( 'Voltage Across Capacitor [V]' )
        
        self.canvas.fig.tight_layout()
        self.canvas.draw()
    
    def cap_prepping(self) :
        print()
        print( self.uController.Vcc )
        print()
        
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
        samples = self.uController.exp_dur_factor * self.uController.samples_per_tc
        print()
        print( self.uController.exp_dur_factor )
        print( self.uController.samples_per_tc )
        print( samples )
        print()
        
        
        itr = 0
        percent_last_update = 0
        x_offset = 0
        
        if self.uController.dis_charge_choice == -1 :
            self.uController.serial.send_command('v')
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f")
            self.cap_prepping()
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f")
            return
        elif self.uController.dis_charge_choice == 0 :
            self.uController.serial.send_command('w')
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f")
            self.cap_prepping()
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f")
            self.uController.serial.send_command('b')
        elif self.uController.dis_charge_choice == 1 :
            self.uController.serial.send_command('v')
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f")
            self.cap_prepping()
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f")
            self.uController.serial.send_command('a')
        else :
            return False
        
        while True :
            result = self.uController.serial.get_responses(num_responses=1, transpose=False, response_types="f", end_message=True)
            
            if result[0] == 'end' :
                break
            if itr == 0 :
                x_offset = result[0]/(1000*1000)
            itr += 1
            self.x_data.append( result[0]/(1000*1000)-x_offset )
            self.y_data.append( result[1] )
            percent_complete = int(100*itr/samples)
            self.notifyProgress.emit( percent_complete )
            if self.canvas is not None and percent_complete >= percent_last_update :
                percent_last_update += 1
                self.update_plot()
        
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
































































































































