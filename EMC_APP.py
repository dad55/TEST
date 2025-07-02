"""____________________________________________________

FILENAME: EMC_APP.py
AUTHOR: Guerric PANIS
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import os
import wx
import wx.aui
import wx.lib.agw.aui
import CONST as const
import DEVICES as dev
import WX_FRAME
import REPORT_CSV as report
import BAT as bat
import threading
import numpy as np
import sys
import time

class MainApp():
    def __init__(self):
        self.appPath = self.find_app_path()
        self.frame = WX_FRAME.MainFrame(None, self.appPath, -1, wx.DefaultPosition, (1300, 800))

        self.frame.Bind(wx.EVT_MENU, self.handleStart, id=const.ID_START)
        self.frame.Bind(wx.EVT_MENU, self.handleSleep, id=const.ID_SLEEP)
        self.frame.Bind(wx.EVT_MENU, self.handleWakeup, id=const.ID_WAKEUP)
        self.frame.Bind(wx.EVT_MENU, self.handleStop, id=const.ID_STOP)
        self.frame.Bind(wx.EVT_MENU, self.handlerStartLog, id=const.ID_LOG_GO)

        self.deviceByRC = np.zeros(const.SCRIPT_MAX_ID, np.int8)
        self.updateDeviceByRC()

        # Double received in serial reception
        self.doubleReceived = False

        # TPL matrix status
        self.sampleCnt = 0
        self.delayRef = 0

        # State machine
        self.state = const.STATE_INITIAL
        self.frequencyID = 0
        self.stopFailure = False    # Stop injection at the current frequency (critical failure)

        # First param fail log
        self.levelFail = 0
        self.comFail = False
        self.devFail = None
        self.levelTarget = 0

        # Report
        self.rep = None

        # Handlers
        self.handleStartVar = False
        self.handleSleepVar = False
        self.handleWakeupVar = False
        self.handleStopVar = False

        # Sleep mode
        self.sleepMode = False
        self.sleepFail = False

        # Timer log mode
        self.time_init = None
        self.time_log = None
        self.StartLogVar = False
        self.n_count = 0

        # Threads
        self.event = threading.Event()
        #self.threads = [threading.Thread(target=self.mainThread), threading.Thread(target=self.dispThread())]
        self.threads = [threading.Thread(target=self.mainThread)]
        self.threadsActive = False
        self.startThreads()

    def find_app_path(self):
        if getattr(sys, 'frozen', False):
            # The application is frozen
            datadir = os.path.dirname(sys.executable)
        else:
            # The application is not frozen
            # Change this bit to match where you store your data files:
            datadir = os.path.dirname(__file__)
        return datadir

    def updateDeviceByRC(self):
        for rc in range(const.SCRIPT_MAX_ID):
            for i in range(const.MAX_DEVICE_TYPE):
                if (rc >= dev.DEVICES_LIST[i].RC_OFFSET) and (i == (const.MAX_DEVICE_TYPE-1)):
                    self.deviceByRC[rc] = i
                elif (rc >= dev.DEVICES_LIST[i].RC_OFFSET) and (rc < dev.DEVICES_LIST[i+1].RC_OFFSET):
                    self.deviceByRC[rc] = i
        #print(str(self.deviceByRC))

    def loadGuards(self):
        for deviceID in self.frame.gridSetup.devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]
            matrixGuard = self.frame.gridGuard[deviceID].getGuardMatrix(device)

            if matrixGuard is not None:
                device.stopAtErr = (matrixGuard[:, 0]).astype(np.int8)
                device.trigPorts = (matrixGuard[:, 1]).astype(np.int8)
                device.trigPins = (matrixGuard[:, 2]).astype(np.int8)
                device.deltaMin = matrixGuard[0:dev.DEVICES_LIST[deviceID].DISP_PARAMS_NB, 3]
                device.deltaMax = matrixGuard[0:dev.DEVICES_LIST[deviceID].DISP_PARAMS_NB, 4]
                device.absMin = matrixGuard[0:dev.DEVICES_LIST[deviceID].DISP_PARAMS_NB, 5]
                device.absMax = matrixGuard[0:dev.DEVICES_LIST[deviceID].DISP_PARAMS_NB, 6]
            else:
                return False
        return True

    def clearForNewLoop(self):
        for deviceID in self.frame.gridSetup.devTypesUsed:
            dev.DEVICES_LIST[deviceID].frameReceived.fill(0)
        self.doubleReceived = False

    def clearForNewFreq(self):
        self.clearForNewLoop()  # Wait for a new complete frame of data (clear for new freq can occur during reception)
        for deviceID in self.frame.gridSetup.devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]
            device.trigStatus.fill(0)
            device.matrixCnt.fill(0)
            device.matrixDisp.fill(0.0)
            device.matrixAvg.fill(0.0)
            device.matrixRef.fill(0.0)
            device.matrixDelta.fill(0.0)
            device.matrixDeltaMin.fill(0.0)
            device.matrixDeltaMax.fill(0.0)
            device.matrixFail.fill(0)
            device.matrixFailAM.fill(0)
            device.matrixFailPM.fill(0)

            device.nodeFail = -1
            device.paramFail = -1

        self.levelFail = 0
        self.levelTarget = 0
        self.stopFailure = False
        self.devFail = None

        if self.frame.bat is not None:
            self.frame.bat.levelMa = 0  # Reset in case of fail at first frequency

    def clearForNewTest(self):
        self.clearForNewFreq()
        for deviceID in self.frame.gridSetup.devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]
            device.matrixCnt.fill(0)

        self.sampleCnt = 0
        self.state = const.STATE_INITIAL
        self.frequencyID = 0
        self.rep = None

    def clearAllComFail(self):
        self.comFail = False
        for deviceID in self.frame.gridSetup.devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]
            device.comFail = False

    def stopIfComFail(self):
        if self.comFail:
            for deviceID in self.frame.gridSetup.devTypesUsed:
                device = dev.DEVICES_LIST[deviceID]
                if device.comFail and (device.stopAtErr[device.DISP_PARAMS_NB] > 0):
                    return True

        return False

    def handleStart(self, event):
        event.Skip()
        self.handleStartVar = True

    def handleSleep(self, event):
        event.Skip()
        if (not self.sleepMode) and self.threadsActive:
            self.handleSleepVar = True

    def handleWakeup(self, event):
        event.Skip()
        if self.sleepMode and self.threadsActive:
            self.handleWakeupVar = True

    def handleStop(self, event):
        event.Skip()
        self.handleStopVar = True

    def handlerStartLog(self, event):
        event.Skip()
        if self.frame.logTrig == 'TIMER TRIG':
            self.StartLogVar = True

    def start(self):
        if self.threadsActive is False:
            # Micro connection check
            if (self.frame.micro.uart.ready or (self.frame.micro.interface == const.CAN_INTERFACE)) and (self.frame.micro.rev > 0):
                self.frame.clearLog()
                self.frame.micro.clear_buffers()
                self.frame.micro.readRev()  #Double check in case USB has been disconnected in between
                if self.frame.micro.rev == 0:
                    self.frame.scanUarts()
                    self.frame.printLog('NO COM PORT OPENED')
                    return
            else:
                self.frame.scanUarts()
                self.frame.printLog('NO COM PORT OPENED')
                return

            # RFOFF check
            if (self.frame.geneTB.combobox[1].GetValue() == 'RFOFF') and (not self.frame.geneCom.opened):
                self.frame.printLog('RFOFF SELECTED BUT NO GENE AVAILABLE')
                return

            # Trig pin init (all devices, event if not used)
            for device in dev.DEVICES_LIST:
                if not self.frame.micro.initTrigPins(device):
                    self.frame.printLog('TRIG PINS INIT ERROR')
                    return

            # Loading guards
            if not self.loadGuards():
                self.frame.printLog('GUARDS LOAD ERROR')
                return

            # Start chain
            if self.frame.micro.startChain(self.appPath, self.frame.gridSetup.scriptsUsed, self.frame.gridSetup.HWscriptUsed, self.frame.gridSetup.matrixSetup, self.frame.gridSetup.devTypesUsed, self.frame.gridSetup.wait):
                self.frame.printLog('APP STARTED')
                self.frame.bat = bat.BAT()  # Create server
                self.threadsActive = True
                self.frame.freezePane()
                self.frame.printLog('WAITING BAT-EMC OR TIMER')
            else:
                #if self.frame.micro.scriptLine > 0:
                self.frame.printLog(str(self.frame.micro.currentScript) + ' LINE ' + str(self.frame.micro.scriptLine))
                self.frame.printLog('START CHAIN ERROR, CHECK SETUP')
                return

            #Lock grids
            self.frame.gridSetup.lockGrid()
            for i in range(const.MAX_DEVICE_TYPE):
                self.frame.gridGuard[i].lockGrid()

    def cleanFaults(self):
        if not self.frame.micro.clearFaults(self.frame.gridSetup.devTypesUsed):
            self.frame.printLog('Clean faults error')
            return False
        return True

    def sleep(self):
        if not self.frame.micro.sleepChain(self.frame.gridSetup.devTypesUsed):
            self.frame.printLog('CANNOT GO TO SLEEP')
            return False
        self.clearForNewLoop()
        self.frame.gridDisp.clearGridValues()
        self.frame.printLog('GOING TO SLEEP')
        self.sleepMode = True
        return True

    def wakeup(self):
        if not self.frame.micro.wakeupChain(self.frame.gridSetup.devTypesUsed):
            self.frame.printLog('WAKEUP ERROR')
            return False
        self.frame.printLog('WAKING UP')
        self.sleepMode = False
        return True

    def stop(self):
        # Stop thread
        self.threadsActive = False

        # Stop server
        if self.frame.bat is not None:
            self.frame.bat.close()
            self.frame.bat = None

        # Stop chain after micro connection check
        if self.frame.micro.uart.ready:
            self.frame.printLog('STOPPING ...')
            self.frame.micro.stopChain()
            self.frame.gauge.SetValue(0)
            self.frame.printLog('APP STOPPED')
        else:
            self.frame.printLog('NO MICRO PORT SELECTED')

        # Re-init variables
        self.clearForNewTest()
        self.comFail = False
        self.sleepMode = False
        self.sleepFail = False
        self.StartLogVar = False
        self.time_log = None

        # Release grids
        self.frame.gridSetup.unlockGrid()
        for i in range(const.MAX_DEVICE_TYPE):
            self.frame.gridGuard[i].unlockGrid(dev.DEVICES_LIST[i])

        self.frame.unFreezePane()

        # Clear grid
        self.frame.gridDisp.clearGridValues()

    def handlerUpdate(self):
        if self.handleStartVar:
            self.start()
            self.handleStartVar = False

        if self.handleSleepVar:
            if self.sleep():
                self.clearForNewFreq()
            else:
                self.stop()
            self.handleSleepVar = False

        if self.handleWakeupVar:
            self.wakeup()
            self.handleWakeupVar = False

        if self.handleStopVar:
            self.stop()
            self.handleStopVar = False

    def startThreads(self):
        for i in range(len(self.threads)):
            self.threads[i].daemon = True   # For stopping thread at interface close
            self.threads[i].start()

        #for i in range(len(self.threads)):
            #self.threads[i].join()

    def serialUpdate(self):
        # Read command by ID first

        if self.frame.micro.readCommandByID():    # RC is > 0, frame status is ok, data can be stored in matrix
            if not self.frame.micro.endLoopFlag:
                frameLen = len(self.frame.micro.lastCMDReceived)
                devType = dev.DEVICES_LIST[self.deviceByRC[(self.frame.micro.lastCMDReceived[0]<<8) + self.frame.micro.lastCMDReceived[1]]]
                if not (devType.addFrameToMatrix(self.frame.micro.lastCMDReceived, frameLen)):
                    self.doubleReceived = True
                    #self.clearForNewLoop()
                if self.comFail:
                    devType.updateTPLstatus(self.frame.micro.lastCMDReceived, frameLen, self.frame.micro)
                else:
                    self.comFail = devType.updateTPLstatus(self.frame.micro.lastCMDReceived, frameLen, self.frame.micro)
                self.checkDeviceFail(devType)
                self.updateDisplayDevice(devType)
            #else:
                #print('End loop')

        elif self.frame.micro.errorFrame:   # Serial error
            print('Serial error')

        elif self.frame.micro.errorTimeout: # Timeout need to be catch but not used
            a = 1
            #print('Timeout error')

        elif (len(self.frame.micro.lastCMDReceived) > 1) and (self.frame.micro.lastCMDReceived[1] != 1):    # Frame received correctly but status is Nok, update counters
            frameLen = len(self.frame.micro.lastCMDReceived)
            devType = dev.DEVICES_LIST[self.deviceByRC[self.frame.micro.lastCMDReceived[0]]]
            if self.comFail:
                devType.updateTPLstatus(self.frame.micro.lastCMDReceived, frameLen, self.frame.micro)
            else:
                self.comFail = devType.updateTPLstatus(self.frame.micro.lastCMDReceived, frameLen, self.frame.micro)
            self.checkDeviceFail(devType)
            self.updateDisplayDevice(devType)

    def allDevParamsReceived(self):
        for deviceID in self.frame.gridSetup.devTypesUsed:
            devType = dev.DEVICES_LIST[deviceID]
            if not devType.allParamsReceived():
                return False
        return True

    def updateDevConv(self):
        for deviceID in self.frame.gridSetup.devTypesUsed:
            dev.DEVICES_LIST[deviceID].updateConv()

    def checkDeviceFail(self, device):
        if (self.devFail is None) and (device.nodeFail != -1):
            self.devFail = device

    def updateFailMatrices(self):
        if self.frame.logTrig == 'BAT TRIG':
            for deviceID in self.frame.gridSetup.devTypesUsed:
                device = dev.DEVICES_LIST[deviceID]
                levelFail = device.updateFailMatricesBCI(self.frame.bat.levelMa, self.frame.bat.modulation)
                if (levelFail > 0) and (self.levelFail == 0):
                    self.levelFail = levelFail

        else:   # Iso pulse case
            for deviceID in self.frame.gridSetup.devTypesUsed:
                device = dev.DEVICES_LIST[deviceID]
                levelFail = device.updateFailMatricesISOPulse()
                if (levelFail > 0) and (self.levelFail == 0):
                    self.levelFail = levelFail

    def updateDisplayDevice(self, device):
        for line in device.dispBuffer:
            self.frame.printLog(line)
        device.dispBuffer = []

    def batUpdate(self):
        if self.frame.bat is not None:
            self.frame.bat.update()
            if self.frame.bat.updated:
                if self.frame.bat.event == 'START':
                    self.clearForNewTest()
                    try:
                        #self.frame.printLog('Creating report')
                        #self.frame.printLog(self.frame.bat.projectName)
                        #self.frame.printLog(self.frame.bat.testName)
                        #self.frame.printLog(self.frame.micro.scriptFName)
                        setupName=self.frame.setupTB.combobox[0].GetValue() + '/' + self.frame.setupTB.combobox[1].GetValue() + '/' + self.frame.setupTB.combobox[2].GetValue()
                        self.rep = report.REPORT_CSV('c:\%s\%s' % (const.program_name, 'REPORTS'),
                                                     self.frame.bat.projectName,
                                                     self.frame.bat.testName,
                                                     setupName,
                                                     const.REF_SAMPLE_NB,
                                                     const.RES_SAMPLE_NB,
                                                     self.frame.micro.rev,
                                                     self.frame.gridSetup)
                        #self.frame.printLog('Report created')
                        self.rep.saveFile()
                        #self.frame.printLog('Report Saved')
                        self.frame.printLog(self.frame.bat.testName + ' STARTED')
                        self.frame.bat.updated = False  # Release low level update
                    except AttributeError:
                        self.frame.printLog('REPORT CREATION ERROR')
                        self.frame.printLog('CHECK REPORT NAME LENGTH')
                        self.handleStopVar = True

                elif self.frame.bat.event == 'TRIG':
                    #self.frame.printLog('TRIG ' + self.frame.bat.modulation + ' ' + str(self.frame.bat.frequency) + ' ' + str(self.frame.bat.target))
                    if self.state == const.STATE_INITIAL: # First point of next frequency
                        self.frame.gridDisp.clearColors()
                        self.frame.printLog('FREQ ' + str(self.frame.bat.frequency / 1000.0) + ' MHz')

                        # Perform RF off (GPIB or TCP) except for sleep mode
                        if self.frame.geneCom.opened and (not self.sleepMode) and (not self.sleepFail):
                            self.frame.geneCom.writeStr("OUTP:STAT OFF") # TODO stop test if communication fail with instrument
                            self.delayRef = time.time()
                        else:
                            self.delayRef = -1

                        # Restart chain if needed (com err at last frequency)
                        if self.comFail and not self.sleepFail and not self.sleepMode:
                            self.frame.printLog('RESTARTING CHAIN...')
                            self.frame.micro.stopChain()
                            self.frame.micro.clear_buffers()
                            if self.frame.micro.startChain(self.appPath, self.frame.gridSetup.scriptsUsed, self.frame.gridSetup.HWscriptUsed, self.frame.gridSetup.matrixSetup, self.frame.gridSetup.devTypesUsed, self.frame.gridSetup.wait):
                                self.frame.printLog('MEASURING REF')
                                self.delayRef = time.time() # Restart timer for ref (restarting chain take some times, setup stability can be lost)
                                self.state = const.STATE_REF_DELAY  # Start wait delay before performing ref
                            else:
                                #if self.frame.micro.scriptLine > 0:
                                self.frame.printLog(str(self.frame.micro.currentScript) + ' LINE ' + str(self.frame.micro.scriptLine))
                                self.frame.printLog('RESTART CHAIN ERROR')
                                self.handleStopVar = True

                            self.clearForNewFreq()
                            self.clearAllComFail()

                        elif self.sleepMode:    # Sleep mode ok
                            self.sampleCnt = 0
                            self.frequencyID = self.frequencyID + 1
                            self.frame.bat.sendAck()
                            self.state = const.STATE_ACQ

                        elif self.sleepFail:    # Sleep mode error
                            # Restarting chain
                            self.frame.printLog('RESTARTING CHAIN...')
                            self.frame.micro.stopChain()
                            self.frame.micro.clear_buffers()
                            if self.frame.micro.startChain(self.appPath, self.frame.gridSetup.scriptsUsed, self.frame.gridSetup.HWscriptUsed, self.frame.gridSetup.matrixSetup, self.frame.gridSetup.devTypesUsed, self.frame.gridSetup.wait):
                                self.handleSleepVar = True  # Return to sleep
                                self.frame.printLog('GOING BACK TO SLEEP')
                                self.frame.bat.sendAck()
                                self.state = const.STATE_ACQ
                                self.clearForNewFreq()
                                self.clearAllComFail()
                            else:
                                #if self.frame.micro.scriptLine > 0:
                                self.frame.printLog(str(self.frame.micro.currentScript) + ' LINE ' + str(self.frame.micro.scriptLine))
                                self.frame.printLog('RESTART CHAIN ERROR')
                                self.handleStopVar = True

                            self.sleepFail = False

                        else:
                            self.frame.printLog('MEASURING REF')
                            self.state = const.STATE_REF_DELAY  # Start wait delay before performing ref

                    else:
                        self.frame.bat.sendAck()

                    if self.frame.bat is not None:
                        self.frame.bat.updated = False  # Release low level update

                elif self.frame.bat.event == 'MEAS':
                    self.frame.printLog('INJECTION ' + self.frame.bat.modulation + ' ' + str(self.frame.bat.levelMa) + ' mA')
                    if self.state != const.STATE_FAIL:
                        self.levelTarget = self.frame.bat.levelMa
                    #self.frame.printLog('MEAS ' + self.frame.bat.modulation + ' ' + str(self.frame.bat.frequency) + ' ' + str(self.frame.bat.target) + ' ' + str(self.frame.bat.levelMa) + ' mA')
                    self.frame.bat.updated = False  # Release low level update

                elif self.frame.bat.event == 'CTRL':
                    #self.frame.printLog('CTRL ' + self.frame.bat.modulation + ' ' + str(self.frame.bat.frequency) + ' ' + str(self.frame.bat.target))
                    self.updateFailMatrices()  # Replace fails noted '-1' in fail matrices by real injected level after MEAS event
                    stopFail = self.stopIfComFail()

                    if (stopFail or self.sleepFail or (self.state == const.STATE_FAIL)) and (self.frame.bat.modulation != self.frame.targetMod):    # Fail but not at target mod, need to wait target mod next time
                        self.state = const.STATE_FAIL   # Stay in fail state, do not update AVG values and wait for next CTRL at target mod
                        self.frame.bat.sendMove()   # Go to target mod
                    elif stopFail or self.sleepFail or (self.state == const.STATE_FAIL) or ((self.state == const.STATE_ACQ) and (self.frame.bat.modulation == self.frame.targetMod) and (self.frame.bat.target == 1)):

                        self.rep.addDatas1Freq2File([self.frequencyID, self.frame.bat.frequency, self.sampleCnt, self.levelTarget, self.levelFail, self.devFail],
                                                  [[self.frame.micro.cptFail, self.frame.micro.cptSuccess]],
                                                    self.frame.gridSetup.devTypesUsed,
                                                    self.frame.logs.GetValue())

                        self.rep.saveFile()
                        self.clearForNewFreq()
                        self.frame.clearLog()

                        if stopFail or self.sleepFail or (self.state == const.STATE_FAIL):  # Com fail or fail from data
                            self.frame.bat.sendMove()
                        else:
                            self.frame.bat.sendAck()

                        self.state = const.STATE_INITIAL

                    else:
                        self.frame.bat.sendAck()

                    self.frame.bat.updated = False  # Release low level update

                elif self.frame.bat.event == 'END':
                    self.handleStopVar = True

    def timerUpdate(self):
        if self.StartLogVar and (self.time_log is None):
            self.clearForNewTest()
            try:
                tm = time.localtime(time.time())
                #self.rep = report.REPORT_CSV(os.path.join((os.environ['USERPROFILE']), 'Documents', const.FOLDER_NAME + '\PULSE_REPORTS'),
                setupName = self.frame.setupTB.combobox[0].GetValue() + '/' + self.frame.setupTB.combobox[1].GetValue() + '/' + self.frame.setupTB.combobox[2].GetValue()
                self.rep = report.REPORT_CSV('c:\%s\%s' % (const.program_name, 'PULSE_REPORTS'),
                                             'ISO_PULSE',
                                             str('ISO_PULSE_' + str(tm.tm_year) + '_' + str(tm.tm_mon) + '_' + str(tm.tm_mday)),
                                             setupName,
                                             const.REF_SAMPLE_NB,
                                             const.RES_SAMPLE_NB,
                                             self.frame.micro.rev,
                                             self.frame.gridSetup)

                self.rep.saveFile()
                self.frame.printLog('ISO PULSE STARTED')
                self.frame.gridDisp.clearColors()
                self.state = const.STATE_REF    # Going to state ref
                self.time_init = time.time()
                self.time_log = self.time_init
                tm = time.localtime(self.time_log-self.time_init)
                self.frame.printLog('TIME ' + str(tm.tm_hour-1) + ':' + str(tm.tm_min) + ':' + str(tm.tm_sec))

            except AttributeError:
                self.frame.printLog('REPORT CREATION ERROR')
                self.frame.printLog('CHECK REPORT NAME LENGTH')
                self.handleStopVar = True

        elif ((self.state == const.STATE_ACQ) or (self.state == const.STATE_FAIL)) and ((time.time()-self.time_log) > self.frame.logTrigValue): # Timer log expire
            self.frequencyID = self.frequencyID + 1
            self.updateFailMatrices()  # Replace fails noted '-1' in fail matrices by real injected level after MEAS event

            self.rep.addDatas1Freq2File([self.frequencyID, int(self.time_log-self.time_init), self.sampleCnt, 0, self.levelFail, self.devFail],
                                        [[self.frame.micro.cptFail, self.frame.micro.cptSuccess]],
                                        self.frame.gridSetup.devTypesUsed,
                                        self.frame.logs.GetValue())

            self.rep.saveFile()

            # Restart chain if needed (com err at last time interval)
            if self.comFail:
                tentative = 0
                test = False
                while (not test) and (tentative <= 4):
                    tentative = tentative + 1 # TO BE COMMENTED ONLY FOR THE INFINITE RETRY
                    self.frame.printLog('RESTARTING CHAIN...')
                    self.frame.printLog('TENTATIVE ' + str(tentative))
                    self.frame.micro.stopChain()
                    self.frame.micro.clear_buffers()
                    test = self.frame.micro.startChain(self.appPath, self.frame.gridSetup.scriptsUsed, self.frame.gridSetup.HWscriptUsed, self.frame.gridSetup.matrixSetup, self.frame.gridSetup.devTypesUsed, self.frame.gridSetup.wait)
                    if not test:
                        #if self.frame.micro.scriptLine > 0:
                        self.frame.printLog(str(self.frame.micro.currentScript) + ' LINE ' + str(self.frame.micro.scriptLine))
                        self.frame.printLog('RESTART CHAIN ERROR')

                    #if tentative > 4:
                    #    self.handleStopVar = True

                self.clearAllComFail()

            self.clearForNewLoop()  # Wait for a new complete frame of data (clear for new freq can occur during reception)

            # Clear for new time interval
            for deviceID in self.frame.gridSetup.devTypesUsed:
                device = dev.DEVICES_LIST[deviceID]
                device.trigStatus.fill(0)
                device.matrixCnt.fill(0)
                device.matrixDisp.fill(0.0)
                #device.matrixAvg.fill(0.0) Avg not cleared
                #device.matrixRef.fill(0.0) Ref not cleared
                device.matrixDelta.fill(0.0)
                device.matrixDeltaMin.fill(0.0)
                device.matrixDeltaMax.fill(0.0)
                device.matrixFail.fill(0)
                device.matrixFailAM.fill(0)
                device.matrixFailPM.fill(0)

                device.nodeFail = -1
                device.paramFail = -1

            self.levelFail = 0
            self.stopFailure = False
            self.devFail = None

            self.frame.clearLog()
            self.frame.printLog('NEW LOG')
            self.time_log = time.time()
            tm = time.localtime(self.time_log-self.time_init)
            self.frame.printLog('TIME ' + str(tm.tm_hour-1) + ':' + str(tm.tm_min) + ':' + str(tm.tm_sec))
            self.state = const.STATE_NEW_ACQ

    def dispThread(self):
        while True:
            self.frame._mgr.Update()
            time.sleep(1)

    def mainThread(self):
        while True:
            #self.frame.Refresh()
            #self.event.wait(0.001)
            #os.system("pause")
            #os.system
            #asyncio.sleep(0.001)
            #self.frame._mgr.Update()
            if self.n_count > 500:  # Sleep for display update
                self.n_count = 0
                time.sleep(0.001)
            else:
                self.n_count = self.n_count+1

            self.frame.handlerUpdate()
            self.handlerUpdate()
            if self.threadsActive and (self.frame.onExitVar is False):
                self.serialUpdate()
                if self.frame.micro.endLoopFlag and (not self.doubleReceived):
                    if self.sleepMode:
                        self.frame.printLog('WAKEUP DETECTED')
                        self.sleepMode = False
                        self.sleepFail = True
                    self.frame.gauge.SetValue(self.frame.micro.sizeBuff())
                    if self.frame.logTrig =='BAT TRIG':
                        self.batUpdate()
                    else:
                        self.timerUpdate()
                    if self.allDevParamsReceived():
                        self.updateDevConv()
                        self.frame.gridDisp.updateGridValues(self.frame.gridSetup.devTypesUsed)  # Update display
                        self.sampleCnt = self.sampleCnt + 1

                        # Waiting for new frequency point or Bat-EMC start
                        if self.state == const.STATE_INITIAL:
                            self.sampleCnt = 0

                        # Waiting n samples after RF-OFF before starting ref
                        elif (self.state == const.STATE_REF_DELAY) and (((time.time() - self.delayRef) > const.DELAY_BEFORE_REF) or (self.delayRef == -1)):
                            #print('Going to state ref')
                            self.frequencyID = self.frequencyID + 1
                            self.sampleCnt = 0
                            self.state = const.STATE_REF

                        # Acquiring ref during n-samples (averaged)
                        elif self.state == const.STATE_REF:
                            for deviceID in self.frame.gridSetup.devTypesUsed:
                                device = dev.DEVICES_LIST[deviceID]
                                device.updateAvg(self.sampleCnt, const.REF_SAMPLE_NB)
                                #print('Update Avg Sample ' + str(self.sampleCnt) + ' device ' + str(device))
                            if self.sampleCnt > const.REF_SAMPLE_NB:
                                if self.frame.geneCom.opened:
                                    self.frame.geneCom.writeStr("OUTP:STAT ON")  # TODO stop test if communication fail with instrument
                                if self.frame.logTrig == 'BAT TRIG':
                                    self.frame.bat.sendAck()  # Release bat trig function

                                for deviceID in self.frame.gridSetup.devTypesUsed:
                                    device = dev.DEVICES_LIST[deviceID]
                                    device.matrixRef = device.matrixAvg
                                    device.matricesUpdate(init=True, micro=self.frame.micro)
                                    self.checkDeviceFail(device)
                                    self.updateDisplayDevice(device)

                                self.state = const.STATE_ACQ

                        elif self.state == const.STATE_NEW_ACQ: # For timer acquisition only (not bat emc)
                            for deviceID in self.frame.gridSetup.devTypesUsed:
                                device = dev.DEVICES_LIST[deviceID]
                                device.updateAvg(self.sampleCnt, const.RES_SAMPLE_NB)
                                device.matricesUpdate(init=True, micro=self.frame.micro)
                                self.checkDeviceFail(device)
                                self.updateDisplayDevice(device)
                            if self.stopFailure:
                                print('Going to fail state')
                                self.state = const.STATE_FAIL  # Go into fail state
                            else:
                                self.state = const.STATE_ACQ

                        # Acquisition during injection
                        elif self.state == const.STATE_ACQ:
                            for deviceID in self.frame.gridSetup.devTypesUsed:
                                device = dev.DEVICES_LIST[deviceID]
                                device.updateAvg(self.sampleCnt, const.RES_SAMPLE_NB)
                                device.matricesUpdate(init=False, micro=self.frame.micro)
                                self.checkDeviceFail(device)
                                self.updateDisplayDevice(device)
                            if self.stopFailure:
                                print('Going to fail state')
                                self.state = const.STATE_FAIL   # Go into fail state

                        # Failure case, quit at next CTRL event
                        elif self.state == const.STATE_FAIL:
                            self.sampleCnt = 0

                    else:
                        self.frame.gridDisp.updateGridCounters(self.frame.gridSetup.devTypesUsed)

                    self.clearForNewLoop()
                    self.frame.micro.endLoopFlag = False
                    #time.sleep(0.001)

                elif self.frame.micro.endLoopFlag:  # Double param received, clear matrices at the end of the loop
                    print('PROUT')
                    self.clearForNewLoop()
                    self.frame.micro.endLoopFlag = False

                elif self.sleepMode:    # Sleep mode management
                    self.batUpdate()

def Main():
    app = wx.App(False)
    the_app = MainApp()
    app.MainLoop()
    print('Main : finished')

if __name__ == '__main__':
    Main()
