"""____________________________________________________

FILENAME: DEVICES.py
AUTHOR: Guerric PANIS
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import os
import numpy as np
import CONST as const

#BCC_TYPE_LIST        = ['', 'MC33771A', 'MC33772A', 'MC33771B', 'MC33772B', 'MC33771C1', 'MC33771C2', 'MC33775A', 'MC33772C', 'MC33774', 'MC33777B']    # First indice is unknown device
#BCC_TYPE_INDEX       = [0,      2    ,      3    ,      2    ,      3    ,      2     ,       2    ,      4    ,      3     ,     5     ,      6    ]

BCC_TYPE_LIST        = ['','','','','','','','','','MC33777B','BMA7126T']    # First indice is unknown device
BCC_TYPE_INDEX       = [0 ,0 ,0 ,0 ,0 ,0 ,0 ,0 ,0 ,    3     ,    2]

PHY_TYPE_LIST        = ['SPI_BOX', 'SPI_APP', 'MC33664_BOX', 'MC33664_APP', 'BMA6402_CH0','BMA6402_CH1','BMA6402_CH2','BMA6402_CH3','NULL','NULL','NULL']


SCRIPT_FLAG_RC      = 65535

class MAIN_DEVICE:
    def __init__(self, disp_params_nb):

        self.DISP_PARAMS_NB = disp_params_nb
        self.DISP_COL_OFFSET = 0
        self.RC_OFFSET = 0
        self.DISP_PARAMS = []
        self.DEV_NAME = ''
        self.PHY = False
        self.SCRIPT_FRAMES = None
        self.SCRIPT_FRAME_NB = 0

        # Guard matrices
        # Stop injection at failure
        self.stopAtErr = np.zeros(disp_params_nb + 1, np.int8)

        # GPIO trig pins (+ for COM)
        self.trigPorts = np.zeros(disp_params_nb + 1, np.int8)
        self.trigPins = np.zeros(disp_params_nb + 1, np.int8)
        self.trigStatus = np.zeros(disp_params_nb + 1, np.int8)

        # Guardband matrices
        self.deltaMin = np.zeros(disp_params_nb, np.float64)
        self.deltaMax = np.zeros(disp_params_nb, np.float64)
        self.absMin = np.zeros(disp_params_nb, np.float64)
        self.absMax = np.zeros(disp_params_nb, np.float64)

        # Variables
        self.script_List = []

        # Matrices
        # Frames indices
        self.frameByID = np.zeros(const.SCRIPT_MAX_ID, np.int8)  # Number of data by ID including RC offset
        self.frameByIDLocal = np.zeros(const.SCRIPT_MAX_ID, np.int8)  # Number of data by ID
        self.frameReceived = np.zeros((const.MAX_DEVICE_PER_TYPE, const.SCRIPT_MAX_FRAME))    # Script frame index, chain and node

        # Nb nodes and positions in chains
        self.NbNodes = 0
        self.NodesPos = np.zeros((const.MAX_CHAIN_NB + 1, const.MAX_DEVICE_NB + 1), np.uint8)   # (chain + 1, node + 1) couple for each element
        self.NodesName = [''] * const.MAX_DEVICE_PER_TYPE

        # Data matrices (device 0 for non app commands storage)
        self.matrixScript = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.SCRIPT_MAX_FRAME, const.FRAME_MAX_LEN), np.uint8)  # Frame len + RC + STAT + CID
        self.matrixDisp = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX), np.float64)
        self.matrixAvg = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX), np.float64)
        self.matrixRef = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX), np.float64)
        self.matrixDelta = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX), np.float64)
        self.matrixDeltaMin = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX), np.float64)
        self.matrixDeltaMax = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX), np.float64)
        self.matrixFail = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX + 1), np.int32)  # Last param for COM
        self.matrixFailAM = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX + 1), np.int32)  # Last param for COM
        self.matrixFailPM = np.zeros((const.MAX_DEVICE_PER_TYPE + 1, const.DISP_PARAMS_NB_MAX + 1), np.int32)  # Last param for COM

        # TPL matrix status
        self.matrixCnt = np.zeros((const.MAX_DEVICE_PER_TYPE, const.TPL_STATUS_NB), np.int64)

        # Delta
        self.dispDelta = False

        # Fails
        self.nodeFail = -1
        self.paramFail = -1
        self.comFail = False

        # Display buffer
        self.dispBuffer = []

    def updateframeByID(self):
        for i in range(self.SCRIPT_FRAME_NB):
            self.frameByID[self.SCRIPT_FRAMES[i][0] + self.RC_OFFSET] = i
            self.frameByIDLocal[self.SCRIPT_FRAMES[i][0]] = i

    def scanScripts(self, appPath):
        path = appPath + const.SCRIPT_PATH + self.DEV_NAME
        self.script_List = []
        for dir in os.listdir(path):
            self.script_List.append(dir)

    def addFrameToMatrix(self, frame, frameLen):
        # R=0 frame are kick off at low level before this function call, only RC!=0 appears here

        frameNb = self.frameByID[frame[1] + (frame[0]<<8)]
        indice = 3  # Unpack indice
        index = 0

        if (frameLen > 5) and (self.SCRIPT_FRAMES[frameNb][1] > 0):  # If app response
            chain = frame[3]
            node = frame[4]
            indice = indice + 2
            index = self.NodesPos[chain][node]
            #print('Chain: ' + str(chain) + ' Node: ' + str(node))

        #print('Received Frame RC: ' + str(frame[0]) + ' FrameNb: ' + str(frameNb) + ' INDEX: ' + str(index))

        # Update reception status for loop
        if self.frameReceived[index][frameNb] > 0:    # Frame already received
            print('Frame already received')
            print('Received Frame RC: ' + str(frame[1] + (frame[0]<<8)))
            return False

        self.frameReceived[index][frameNb] = 1    # Update reception status

        # Retrieve data if used and operation correct
        if (frame[2] == 1) and (self.SCRIPT_FRAMES[frameNb][4] > 0):
            j = 0
            while indice < frameLen:
                self.matrixScript[index][frameNb][j] = frame[indice]
                j = j + 1
                indice = indice + 1

        return True

    def updateTPLstatus(self, frame, frameLen, micro):
        #comFail = False
        frameNb = self.frameByID[frame[1] + (frame[0]<<8)]
        #print(frame)
        if (frameLen > 4) and (self.SCRIPT_FRAMES[frameNb][3] > 0):  # Command status is displayed
            if (len(frame) > 5) and (self.SCRIPT_FRAMES[frameNb][1] > 0):  # If app response
                chain = frame[3]
                node = frame[4]
                index = self.NodesPos[chain][node]
            else:
                index = 0

            if frame[2] == 1:
                self.matrixCnt[index][4] = self.matrixCnt[index][4] + 1
            elif (frame[2] & const.TPL_ECHO_ERR) > 0:
                self.matrixCnt[index][0] = self.matrixCnt[index][0] + 1
                self.comFail = True
            elif (frame[2] & const.TPL_NO_RESP) > 0:
                self.matrixCnt[index][1] = self.matrixCnt[index][1] + 1
                self.comFail = True
            elif (frame[2] & const.TPL_RESP_ERR) > 0:
                self.matrixCnt[index][2] = self.matrixCnt[index][2] + 1
                self.comFail = True
            else:   # 0 = 0ther error
                self.matrixCnt[index][3] = self.matrixCnt[index][3] + 1
                self.comFail = True

            if (frame[2] != 1) and (self.matrixFail[index][self.DISP_PARAMS_NB] == 0):
                self.setFail(index, self.DISP_PARAMS_NB, micro)
                self.comFail = True

        return self.comFail

    def updateConv(self):
        if self.PHY:
            #number = self.NbNodes
            the_range = range(self.NbNodes)
        else:
            #number = self.NbNodes + 1
            the_range = range(1, self.NbNodes+1)

        for param in range(self.DISP_PARAMS_NB):
            op1 = self.frameByIDLocal[self.DISP_PARAMS[param][1]]
            pos1 = self.DISP_PARAMS[param][2]
            len1 = self.DISP_PARAMS[param][3]
            op2 = self.frameByIDLocal[self.DISP_PARAMS[param][4]]
            pos2 = self.DISP_PARAMS[param][5]
            len2 = self.DISP_PARAMS[param][6]
            op3 = self.frameByIDLocal[self.DISP_PARAMS[param][7]]
            pos3 = self.DISP_PARAMS[param][8]
            len3 = self.DISP_PARAMS[param][9]
            op4 = self.frameByIDLocal[self.DISP_PARAMS[param][10]]
            pos4 = self.DISP_PARAMS[param][11]
            len4 = self.DISP_PARAMS[param][12]
            func = self.DISP_PARAMS[param][13]

            #for index in range(number):
            for index in the_range:
                val1 = 0
                val2 = 0
                val3 = 0
                val4 = 0
                for i in range(len1):
                    val1 = (val1 * 256) + self.matrixScript[index][op1][pos1 + i]
                if op2 >= 0:
                    for i in range(len2):
                        val2 = (val2 * 256) + self.matrixScript[index][op2][pos2 + i]
                if op3 >= 0:
                    for i in range(len3):
                        val3 = (val3 * 256) + self.matrixScript[index][op3][pos3 + i]
                if op4 >= 0:
                    for i in range(len4):
                        val4 = (val4 * 256) + self.matrixScript[index][op4][pos4 + i]

                #print("Func_call param: " + str(param) + " index: " + str(index))
                self.matrixDisp[index][param] = func(val1, val2, val3, val4)

    def updateAvg(self, sample, nbSamples):
        if (sample == 1) or (nbSamples == 1):   # First sample
            self.matrixAvg = self.matrixDisp
        else:
            self.matrixAvg = (((nbSamples - 1.0)*self.matrixAvg) + self.matrixDisp) / nbSamples
            # Correct digital parameters (no averaging)
            if self.PHY:
                number = self.NbNodes
            else:
                number = self.NbNodes + 1

            for index in range(number):
                for i in range(self.DISP_PARAMS_NB):
                    if self.DISP_PARAMS[i][20] == 'X':  # Digital parameters
                        self.matrixAvg[index][i] = self.matrixDisp[index][i]

    def allParamsReceived(self):
        if self.PHY:
            number = self.NbNodes
        else:
            number = self.NbNodes + 1

        for index in range(number):
            if index > 0:   # App commands
                for i in range(self.SCRIPT_FRAME_NB):
                    if (self.SCRIPT_FRAMES[i][1] > 0) and (self.SCRIPT_FRAMES[i][4] > 0) and (self.frameReceived[index][i] == 0):  # Check only for app response with data used
                        print('Missing frame Device: ' + str(self.DEV_NAME) + ' Node index ' + str(index) + ' Indice: ' + str(i))
                        return False
            else:
                for i in range(self.SCRIPT_FRAME_NB):
                    if (self.SCRIPT_FRAMES[i][1] == 0) and (self.SCRIPT_FRAMES[i][4] > 0) and (self.frameReceived[index][i] == 0):  # Check only for not app response with data used
                        print('Missing global frame: ' + str(self.DEV_NAME) + ' Node index ' + str(index) + ' Indice: ' + str(i))
                        return False
        return True

    def matricesUpdate(self, init, micro):
        if self.PHY:
            the_range = range(self.NbNodes)
        else:
            the_range = range(1, self.NbNodes + 1)

        for index in the_range:
            for param in range(self.DISP_PARAMS_NB):
                if self.DISP_PARAMS[param][20] == 'X':    # Digital param
                    # Update delta (bits that moved)
                    self.matrixDelta[index][param] = int(self.matrixAvg[index][param]) ^ int(self.matrixRef[index][param])

                    # Update bit switches (update if more bits moved)
                    if (int(self.matrixDelta[index][param]) | int(self.matrixDeltaMax[index][param])) > int(self.matrixDeltaMax[index][param]):
                        self.matrixDeltaMax[index][param] = int(self.matrixDelta[index][param]) | int(self.matrixDeltaMax[index][param])

                    max = int(self.matrixDelta[index][param]) & int(self.deltaMax[param]) # self.deltaMax is mask for digital param (no min value)
                    if (self.matrixFail[index][param] == 0) and (max > 0):
                        self.setFail(index, param, micro)

                else:   # Analog param
                    if self.DISP_PARAMS[param][15] == 1:  # Delta from reference is enabled
                        # Update delta from ref
                        self.matrixDelta[index][param] = self.matrixAvg[index][param] - self.matrixRef[index][param]
                    else:  # Delta from reference is disabled
                        # Delta equal to value
                        self.matrixDelta[index][param] = self.matrixAvg[index][param]

                        if init:    # Center min and max to value
                            self.matrixDeltaMax[index][param] = self.matrixAvg[index][param]
                            self.matrixDeltaMin[index][param] = self.matrixAvg[index][param]

                    # Update Min delta and Max delta
                    if self.matrixDelta[index][param] > self.matrixDeltaMax[index][param]:
                        self.matrixDeltaMax[index][param] = self.matrixDelta[index][param]
                    elif self.matrixDelta[index][param] < self.matrixDeltaMin[index][param]:
                        self.matrixDeltaMin[index][param] = self.matrixDelta[index][param]

                    # Update failure
                    if (self.matrixFail[index][param] == 0) and ((self.matrixDeltaMax[index][param] > self.deltaMax[param]) or (self.matrixDeltaMin[index][param] < self.deltaMin[param])):
                        self.setFail(index, param, micro)

    def setFail(self, index, param, micro):
        # Power to update in matrix at next meas event
        # print('Setting failure')
        if (self.matrixFail[index][param] == 0) and (self.matrixFailAM[index][param] == 0) and (self.matrixFailPM[index][param] == 0):
            self.matrixFail[index][param] = -1  # self.frame.bat.levelMa #Value will be updated at next CTRL event (last meas)

        # Update first fail at this frequency
        if self.nodeFail < 0:
            self.nodeFail = index
            self.paramFail = param
            # Notify user if injection will be stopped
            if param == self.DISP_PARAMS_NB:
                self.dispBuffer.append('%s DEV %d TPL FAIL ' % (self.DEV_NAME, index))
            else:
                self.dispBuffer.append('%s DEV %s %s FAIL ' % (self.DEV_NAME, index, self.DISP_PARAMS[param][0]))

        # Trig GPIO if defined
        if (self.trigStatus[param] == 0) and (self.trigPorts[param] > 0):
            micro.setGPIO(self.trigPorts[param], self.trigPins[param], 1)
            self.trigStatus[param] = 1
            micro.setGPIO(self.trigPorts[param], self.trigPins[param], 0)


    def updateFailMatricesBCI(self, levelMa, modulation):
        if self.PHY:
            number = self.NbNodes
        else:
            number = self.NbNodes + 1

        levelFail = 0

        for index in range(number):
            for param in range(self.DISP_PARAMS_NB + 1):
                if self.matrixFail[index][param] == -1:
                    levelFail = levelMa
                    if modulation == 'CW':
                        self.matrixFail[index][param] = levelMa
                    elif modulation == 'AM':
                        self.matrixFail[index][param] = 0
                        self.matrixFailAM[index][param] = levelMa
                    elif modulation == 'PM':
                        self.matrixFail[index][param] = 0
                        self.matrixFailPM[index][param] = levelMa

        return levelFail

    def updateFailMatricesISOPulse(self):
        if self.PHY:
            number = self.NbNodes
        else:
            number = self.NbNodes + 1

        levelFail = 0

        for index in range(number):
            for param in range(self.DISP_PARAMS_NB + 1):
                if self.matrixFail[index][param] == -1:
                    self.matrixFail[index][param] = 1
                    levelFail = 1

        return levelFail

class MC33664(MAIN_DEVICE):
    def __init__(self):
        MAIN_DEVICE.__init__(self, disp_params_nb=1)

        self.PHY = True

        self.DEV_NAME = 'MC33664'
        self.RC_OFFSET = 0

        # Script parameters
        self.SCRIPT_FRAME_NB = 1

        # One single ID by line
        self.SCRIPT_FRAMES = [
            # RC,  App resp , Len   , Stat Disp , Data Used
            (1  , 0         , 2     , 0         , 1         ),  # Mbat 12V
        ]

        # OP define the indice in script param, Last param (not noted here) is COM
        self.DISP_PARAMS = [
        #Name            , Op1, Pos1, Len1, Op2, Pos2, Len2, Op3, Pos3, Len3, Op4, Pos4, Len4, Compute_func     , Format  , Delta , Dmin  , Dmax  , Min   , Max
        ('M_BAT'         , 3  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMbat    ,'{:2.2f}', 1     , -1    , 1     , 11.5  , 14.5  , 'V' ),
        ]

        self.updateframeByID()

    # Conversion functions
    def convMbat(self, val1, val2=0, val3=0, val4=0):
        return (val1 & 65535) * 9.4/1.2 * 0.001
        #return (val1 & 65535) * 0.0078333


class BMA6402(MAIN_DEVICE):
    def __init__(self):
        MAIN_DEVICE.__init__(self, disp_params_nb=19)

        self.PHY = True

        self.DEV_NAME = 'BMA6402'
        self.RC_OFFSET = 5

        # Script parameters
        self.SCRIPT_FRAME_NB = 7

        # One single ID by line
        self.SCRIPT_FRAMES = [
            # RC,  App resp , Len   , Stat Disp , Data Used
            (1  , 0         , 2     , 1         , 1         ),  # SYS_CFG_CRC
            (2  , 0         , 10    , 1         , 1         ),  # Version + UID + Prod version
            (3  , 0         , 2     , 1         , 1         ),  # EVH_CFG_CRC
            (4  , 0         , 22    , 1         , 1         ),  # Errors
            (5  , 0         , 2     , 1         , 0         ),  # NOP for loopback 1
            (6  , 0         , 2     , 1         , 0         ),  # NOP for loopback 2
            (7  , 0         , 2     , 0         , 1         ),  # Mbat 12V
        ]

        # OP define the indice in script param, Last param (not noted here) is COM
        self.DISP_PARAMS = [
        #Name            , Op1, Pos1, Len1, Op2, Pos2, Len2, Op3, Pos3, Len3, Op4, Pos4, Len4, Compute_func     , Format  , Delta , Dmin  , Dmax  , Min   , Max
        ('M_BAT'         , 7  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMbat    ,'{:2.2f}', 1     , -1    , 1     , 11.5  , 14.5  , 'V' ),
        ('VERSION'       , 2  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0x0000, 'X' ),
        ('PART_UID_L'    , 2  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0x0000, 'X' ),
        ('PART_UID_M'    , 2  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0x0000, 'X' ),
        ('PART_UID_H'    , 2  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0x0000, 'X' ),
        ('PROD_VERS'     , 2  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0x0000, 'X' ),
        ('SYS_CFG_CRC'   , 1  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0x0000, 'X' ),
        ('EVH_CFG_CRC'   , 3  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0x0000, 'X' ),
        ('WKUP_REAS'     , 4  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('RST_REAS'      , 4  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('QUEUE STAT'    , 4  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0x0000, 0     , 0x0000, 'X' ),
        ('GRP_ERR'       , 4  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('GEN_ERR'       , 4  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('MCUIF_ERR'     , 4  , 10  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('TPL0_ERR'      , 4  , 12  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('TPL1_ERR'      , 4  , 14  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('TPL2_ERR'      , 4  , 16  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('TPL3_ERR'      , 4  , 18  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('ACC_ERR'       , 4  , 20  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convSimple  ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ]

        self.updateframeByID()

    # Conversion functions
    def convMbat(self, val1, val2=0, val3=0, val4=0):
        return (val1 & 65535) * 9.4 / 1.2 * 0.001
        #return (val1 & 65535) * 0.0078333

    def convSimple(self, val1, val2=0, val3=0, val4=0):
        return val1



class BMA7126T(MAIN_DEVICE):
    def __init__(self):
        MAIN_DEVICE.__init__(self, disp_params_nb=112)

        self.PHY = False

        self.DEV_NAME = 'BMA7126T'
        self.RC_OFFSET = 20

        # Script parameters
        self.SCRIPT_FRAME_NB         = 34

        # One single ID by line
        self.SCRIPT_FRAMES = [
            # RC,  App resp , Len   , Stat Disp , Data Used (check in all param received function)
            (1  , 1         , 52    , 1         , 1         ),  # VC
            (2  , 1         , 52    , 1         , 1         ),  # VB
            (3  , 1         , 14    , 1         , 1         ),  # AIN0-4
            (4  , 1         , 12    , 1         , 1         ),  # AIN5-8
            (5  , 1         , 6     , 1         , 1         ),  # PRMM_TEMP and SECVREF and VAUX
            (6  , 1         , 6     , 1         , 1         ),  # SECM_TEMP and PRMVREF and VAUX
            (7  , 1         , 4     , 1         , 1         ),  # GRP_FLT and SUPPLY_FLT
            (8  , 1         , 6     , 1         , 1         ),  # ANA_FLT and COM_FLT and MEAS_FLT
            (9 ,  1         , 6     , 1         , 1         ),  # WAKEUP_REASON0_1_2
            (10 , 1         , 2     , 1         , 1         ),  # RESET_REASON
            (11 , 1         , 16    , 1         , 1         ),  # VC_OV_S0&1 and VC_UV0_S0&1 and None and None and VC_VB_CMP_S0&1
            (12 , 1         , 8     , 1         , 1         ),  # VB_OV_S0&1 and VB_UV_S0&1
            (13 , 1         , 4     , 1         , 1         ),  # VB_VC_CMP_S0&1
            (14 , 1         , 6     , 1         , 1         ),  # PRM_AIN_OV_S and PRM_AIN_UV_S and PRM_MEAS_S
            (15 , 1         , 4     , 1         , 1         ),  # SEC_AIN_OV_S and SEC_AIN_UV_S
            (16 , 1         , 2     , 1         , 1         ),  # SECM_MEAS_STAT
            (17 , 1         , 2     , 1         , 0         ),  # Write SUPPLY_FLT_S for clearing only
            (18 , 1         , 2     , 1         , 0         ),  # Write ANA_FLT_s and COM_FLT_S and MEAS_FLT_S for clearing only
            (19 , 1         , 2     , 1         , 0         ),  # Read GRP_FLT_S for clearing only
            (20 , 1         , 6     , 1         , 0         ),  # Read WAKEUP_REASON0&1 for clearing only
            (21 , 1         , 2     , 1         , 0         ),  # Write PRMM_VC_DIAG
            (22 , 1         , 2     , 1         , 0         ),  # Write SECM_VB_DIAG
            (23 , 1         , 2     , 1         , 0         ),  # Write PRM_AIN_DIAG
            (24 , 1         , 2     , 1         , 0         ),  # Write SEC_AIN_DIAG
            (25 , 1         , 8     , 1         , 1         ),  # Read PRM_VC_VB_CMP_S0&1 for clearing and PRM_VC_OL_S0&1
            (26 , 1         , 8     , 1         , 1         ),  # Read SEC_VB_VC_CMP_S0&1 for clearing and SEC_VB_OL_S0&1
            (27 , 1         , 4     , 1         , 1         ),  # Read PRM_AIN_OV_S and PRM_AIN_UV_S
            (28 , 1         , 4     , 1         , 1         ),  # Read SEC_AIN_OV_S and SEC_AIN_UV_S
            (29 , 1         , 2     , 1         , 0         ),  # Write PRMM_VC_DIAG
            (30 , 1         , 2     , 1         , 0         ),  # Write SECM_VB_DIAG
            (31 , 1         , 2     , 1         , 0         ),  # Write PRM_AIN_DIAG
            (32 , 1         , 2     , 1         , 0         ),  # Write SEC_AIN_DIAG
            (33 , 1         , 4     , 1         , 1         ),  # Read BAL_CH_S0&1
            (34 , 1         , 2     , 1         , 1         ),  # Read SYS_SYNC_STAT

            # (34, 1, 4, 1, 1),  # Read BAL_SWITCH_FLT_S0&1
        ]

        # OP define the indice in script param, Last param (not noted here) is COM
        self.DISP_PARAMS = [
        #Name           , Op1, Pos1, Len1, Op2, Pos2, Len2, Op3, Pos3, Len3, Op4, Pos4, Len4, Compute_func     , Format  , Delta , Dmin  , Dmax  , Min   , Max
        ('GRP_FLT'      , 7  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SUPPLY_FLT'   , 7  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('ANA_FLT'      , 8  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('COM_FLT'      , 8  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('MEAS_FLT'     , 8  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('WKUP_REAS0'   , 9  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('WKUP_REAS1'   , 9  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('WKUP_REAS2'   , 9  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('RESET_REAS'   , 10 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_VC_OV_S0' , 11 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_VC_OV_S1' , 11 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_VC_UV0_S0', 11 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_VC_UV0_S1', 11 , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_VB_OV_S0' , 12 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_VB_OV_S1' , 12 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_VB_UV_S0' , 12 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_VB_UV_S1' , 12 , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_AIN_OV_S' , 14 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_AIN_UV_S' , 14 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_AIN_OV_S' , 15 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_AIN_UV_S' , 15 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_MEAS_S'   , 14 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFF00, 0     , 0xFF00, 'X' ),
        ('SEC_MEAS_S'   , 16 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFF00, 0     , 0xFF00, 'X' ),
        ('BAL_CH_S0'    , 33 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('BAL_CH_S1'    , 33 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SYS_SYNC_S'   , 34 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SYNC_LOCK_FLT', 34 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFaultSync,'{:01X}', 1     , 0     , 0x0000, 0     , 0x0000, 'X' ),
        ('VC25'         , 1  , 50  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.6   , 3.4   , 'V' ),
        ('VC24'         , 1  , 48  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.6   , 3.4   , 'V' ),
        ('VC23'         , 1  , 46  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.6   , 3.4   , 'V' ),
        ('VC22'         , 1  , 44  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.6   , 3.4   , 'V' ),
        ('VC21'         , 1  , 42  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.6   , 3.4   , 'V' ),
        ('VC20'         , 1  , 40  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.6   , 3.4   , 'V' ),
        ('VC19'         , 1  , 38  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.6   , 3.4   , 'V' ),
        ('VC18'         , 1  , 36  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.6   , 3.4   , 'V' ),
        ('VC17'         , 1  , 34  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC16'         , 1  , 32  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC15'         , 1  , 30  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC14'         , 1  , 28  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC13'         , 1  , 26  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC12'         , 1  , 24  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC11'         , 1  , 22  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC10'         , 1  , 20  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC9'          , 1  , 18  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC8'          , 1  , 16  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC7'          , 1  , 14  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC6'          , 1  , 12  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC5'          , 1  , 10  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC4'          , 1  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC3'          , 1  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC2'          , 1  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC1'          , 1  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('VC0'          , 1  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas    ,'{:2.3f}', 1     , -0.006, 0.006 , 2.3   , 3.1   , 'V' ),
        ('AIN12'        , 4  , 10  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN11'        , 4  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN10'        , 4  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN9'         , 4  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN8'         , 4  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN7'         , 4  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN6'         , 3  , 12  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN5'         , 3  , 10  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN4'         , 3  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN3'         , 3  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN2'         , 3  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN1'         , 3  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('AIN0'         , 3  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatio   ,'{:2.3f}', 1     , -0.016, 0.016 , 1.40  , 2.00  , 'V' ),
        ('PRM_VC_OL_S0' , 25 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_VC_OL_S1' , 25 , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_VB_OL_S0' , 26 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_VB_OL_S1' , 26 , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_AIN_OV_OL', 27 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PRM_AIN_UV_OL', 27 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_AIN_OV_OL', 28 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SEC_AIN_UV_OL', 28 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault   ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('TEMP'         , 5  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convTemp    ,'{:2.1f}', 1     , -3    , 3     , 10    , 65    , '°C'),
        ('VC-VB25'      , 1  , 50  , 2   , 2  , 50  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB24'      , 1  , 48  , 2   , 2  , 48  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB23'      , 1  , 46  , 2   , 2  , 46  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB22'      , 1  , 44  , 2   , 2  , 44  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB21'      , 1  , 42  , 2   , 2  , 42  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB20'      , 1  , 40  , 2   , 2  , 40  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB19'      , 1  , 38  , 2   , 2  , 38  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB18'      , 1  , 36  , 2   , 2  , 36  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB17'      , 1  , 34  , 2   , 2  , 34  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB16'      , 1  , 32  , 2   , 2  , 32  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB15'      , 1  , 30  , 2   , 2  , 30  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB14'      , 1  , 28  , 2   , 2  , 28  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB13'      , 1  , 26  , 2   , 2  , 26  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB12'      , 1  , 24  , 2   , 2  , 24  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB11'      , 1  , 22  , 2   , 2  , 22  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB10'      , 1  , 20  , 2   , 2  , 20  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB9'       , 1  , 18  , 2   , 2  , 18  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB8'       , 1  , 16  , 2   , 2  , 16  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB7'       , 1  , 14  , 2   , 2  , 14  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB6'       , 1  , 12  , 2   , 2  , 12  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB5'       , 1  , 10  , 2   , 2  , 10  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB4'       , 1  , 8   , 2   , 2  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB3'       , 1  , 6   , 2   , 2  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB2'       , 1  , 4   , 2   , 2  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB1'       , 1  , 2   , 2   , 2  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('VC-VB0'       , 1  , 0   , 2   , 2  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD   ,'{:2.3f}', 0     , -0.012, 0.012 , -0.012, 0.012 , 'V' ),
        ('AIN5-12'      , 3  , 10  , 2   , 4  , 10  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatioD  ,'{:2.3f}', 0     , -0.036, 0.036 , -0.036, 0.036 , 'V' ),
        ('AIN4-11'      , 3  , 8   , 2   , 4  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatioD  ,'{:2.3f}', 0     , -0.036, 0.036 , -0.036, 0.036 , 'V' ),
        ('AIN3-10'      , 3  , 6   , 2   , 4  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatioD  ,'{:2.3f}', 0     , -0.036, 0.036 , -0.036, 0.036 , 'V' ),
        ('AIN2-9'       , 3  , 4   , 2   , 4  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatioD  ,'{:2.3f}', 0     , -0.036, 0.036 , -0.036, 0.036 , 'V' ),
        ('AIN1-8'       , 3  , 2   , 2   , 4  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatioD  ,'{:2.3f}', 0     , -0.036, 0.036 , -0.036, 0.036 , 'V' ),
        ('AIN0-7'       , 3  , 0   , 2   , 4  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convRatioD  ,'{:2.3f}', 0     , -0.036, 0.036 , -0.036, 0.036 , 'V' ),
        ('TEMP-SEC'     , 5  , 0   , 2   , 6  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convTempD   ,'{:2.1f}', 0     , -6    , 6     , -6    , 6     , '°C'),
        ('PRMVREF'      , 6  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVref    ,'{:2.3f}', 0     ,  0.8  , 1.2   , 0.8   , 1.2   , 'V' ),
        ('SECVREF'      , 5  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVref    ,'{:2.3f}', 0     ,  0.8  , 1.2   , 0.8   , 1.2   , 'V' ),
        ('PRM_VAUX'     , 5  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVaux    ,'{:2.3f}', 0     ,  4.85 , 5.15  , 4.85  , 5.15  , 'V' ),
        ('SEC_VAUX'     , 6  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVaux    ,'{:2.3f}', 0     ,  4.85 , 5.15  , 4.85  , 5.15  , 'V' ),
        ]

        self.updateframeByID()
        self.last_sync_lock_bit = 0

    # Conversion functions
    def convFault(self, val1, val2=0, val3=0, val4=0):
        return val1 & 65535

    # If 2 consecutive lock bit = 0, raise fault (return 1 means fault)
    def convFaultSync(self, val1, val2=0, val3=0, val4=0):
        if self.last_sync_lock_bit == 0 and (val1  & 0x1) == 0:
            self.last_sync_lock_bit = val1 & 0x1
            return 1
        else:
            self.last_sync_lock_bit = val1 & 0x1
            return 0

    def convMeas(self, val1, val2=0, val3=0, val4=0):
        if val1 > 32767:  # 2^14 - 1 = pow(2, 14) - 1
            return (65536 - val1) * (-0.000186)  # 2^15 - val
        else:
            return val1 * 0.000186

    def convRatio(self, val1, val2=0, val3=0, val4=0):  # Ratio assuming Vaux = 3.3V
        if val1 > 32767:  # 2^14 - 1 = pow(2, 14) - 1
            return (65536 - val1) * (-0.000154) # * (3.3/5)
        else:
            return val1 * 0.000154 # * (3.3/5)

    def convRatioD(self, val1, val2, val3=0, val4=0):
        if val1 > 32767:
            valA = -(65536 - val1)
        else:
            valA = val1
        if val2 > 32767:
            valB = -(65536 - val2)
        else:
            valB = val2
        return (valA - valB) * 0.000154

    def convMeasD(self, val1, val2, val3=0, val4=0):
        if val1 > 32767:
            valA = -(65536 - val1)
        else:
            valA = val1
        if val2 > 32767:
            valB = -(65536 - val2)
        else:
            valB = val2
        return (valA - valB) * 0.000186

    def convTemp(self, val1, val2=0, val3=0, val4=0):
        return (val1 * 0.0324) - 273.15

    def convTempD(self, val1, val2, val3=0, val4=0):
        return (val1 - val2) * 0.0324

    def convVref(self, val1, val2=0, val3=0, val4=0):
        return val1 * 0.000038452

    def convVaux(self, val1, val2=0, val3=0, val4=0):
        return val1 * 0.000308

class MC33777(MAIN_DEVICE):
    def __init__(self):
        MAIN_DEVICE.__init__(self, disp_params_nb=66)

        self.PHY = False

        self.DEV_NAME = 'MC33777'
        self.RC_OFFSET = 160

        # Script parameters
        self.SCRIPT_FRAME_NB         = 51

        # One single ID by line
        self.SCRIPT_FRAMES = [
            # RC,  App resp , Len   , Stat Disp , Data Used (check in all param received function)
            (1  , 1         , 4     , 1         , 1         ),  # Read PRMM_VI0P_PER_RESL and H
            (2  , 1         , 4     , 1         , 1         ),  # Read PRMM_I1P_PER_RESL and H
            (3  , 1         , 4     , 1         , 1         ),  # Read SECM_VI0P_PER_RESL and H
            (4  , 1         , 4     , 1         , 1         ),  # Read SECM_I1P_PER_RESL and H
            (5  , 1         , 16    , 1         , 1         ),  # Read PRMM_IOX_PER_RES
            (6  , 1         , 16    , 1         , 1         ),  # Read SECM_IOX_PER_RES
            (7  , 1         , 2     , 1         , 1         ),  # Read PRMM_INT_ICTEMP0_LST_RES
            (8  , 1         , 2     , 1         , 1         ),  # Read SECM_INT_ICTEMP0_LST_RES
            (9  , 1         , 2     , 1         , 1         ),  # Read PRMM_VI0P_STAT
            (10 , 1         , 2     , 1         , 1         ),  # Read PRMM_I1P_STAT
            (11 , 1         , 4     , 1         , 1         ),  # Read PRMM_IO_PER_LIMHSTAT and L
            (12 , 1         , 2     , 1         , 1         ),  # Read SECM_VI0P_STAT
            (13 , 1         , 2     , 1         , 1         ),  # Read SECM_I1P_STAT
            (14 , 1         , 4     , 1         , 1         ),  # Read SECM_IO_PER_LIMHSTAT and L
            (15 , 1         , 6     , 1         , 1         ),  # Read FEH_ACC_ERR, FEH_GRP_FLT_STAT, FEH_SUPPLY_FLT_STAT0-1   # /!\ remove FEH_SUPPLY_FLT_STAT1
            (16 , 1         , 6     , 1         , 1         ),  # Read FEH_COM_FLT_STAT, FEH_MEAS_FLT_STAT, FEH_PSC_FLT_STAT
            (17 , 1         , 6     , 1         , 1         ),  # Read SECFEH_ACC_ERR, SECFEH_GRP_FLT_STAT, SECFEH_SUPPLY_FLT_STAT0-1   # /!\ SECFEH_SUPPLY_FLT_STAT1
            (18 , 1         , 6     , 1         , 1         ),  # Read SECFEH_COM_FLT_STAT, SECFEH_MEAS_FLT_STAT, SECFEH_PSC_FLT_STAT
            (19 , 1         , 2     , 1         , 1         ),  # Read FEH_WAKEUP_REASON0
            (20 , 1         , 2     , 1         , 1         ),  # Read SECFEH_WAKEUP_REASON0
            (21 , 1         , 2     , 1         , 1         ),  # Read FEH_RESET_REASON
            (22 , 1         , 2     , 1         , 1         ),  # Read SECFEH_RESET_REASON
            (23 , 1         , 2     , 1         , 0         ),  # Read PRMM_VI0P_STAT for clearing only
            (24 , 1         , 2     , 1         , 0         ),  # Read PRMM_I1P_STAT for clearing only
            (25 , 1         , 4     , 1         , 0         ),  # Read PRMM_IO_PER_LIMHSTAT and H for clearing only
            (26 , 1         , 2     , 1         , 0         ),  # Read SECM_VI0P_STAT for clearing only
            (27 , 1         , 2     , 1         , 0         ),  # Read SECM_I1P_STAT for clearing only
            (28 , 1         , 4     , 1         , 0         ),  # Read SECM_IO_PER_LIMHSTAT and H for clearing only
            (29 , 1         , 4     , 1         , 0         ),  # Read FEH_ACC_ERR, FEH_GRP_FLT_STAT for clearing only
            (30 , 1         , 2     , 1         , 0         ),  # Write FEH_SUPPLY_FLT_STAT0 for clearing only
            (31 , 1         , 2     , 1         , 0         ),  # Write FEH_COM_FLT_STAT for clearing only
            (32 , 1         , 2     , 1         , 0         ),  # Write FEH_MEAS_FLT_STAT for clearing only
            (33 , 1         , 2     , 1         , 0         ),  # Write FEH_PSC_FLT_STAT for clearing only
            (34 , 1         , 4     , 1         , 0         ),  # Read SECFEH_ACC_ERR, SECFEH_GRP_FLT_STAT for clearing only
            (35 , 1         , 2     , 1         , 0         ),  # Write SECFEH_SUPPLY_FLT_STAT0 for clearing only
            (36 , 1         , 2     , 1         , 0         ),  # Write SECFEH_COM_FLT_STAT for clearing only
            (37 , 1         , 2     , 1         , 0         ),  # Write SECFEH_MEAS_FLT_STAT for clearing only
            (38 , 1         , 2     , 1         , 0         ),  # Write SECFEH_PSC_FLT_STAT for clearing only
            (39 , 1         , 2     , 1         , 0         ),  # Read FEH_WAKEUP_REASON0 for clearing only
            (40 , 1         , 2     , 1         , 0         ),  # Read SECFEH_WAKEUP_REASON0 for clearing only
            (41 , 1         , 2     , 1         , 0         ),  # Read FEH_RESET_REASON for clearing only
            (42 , 1         , 2     , 1         , 0         ),  # Read SECFEH_RESET_REASON for clearing only
            (43 , 1         , 4     , 1         , 1         ),  # Read PRMM_PSC_VBAT_LST_RES and PRMM_PSC_VCER_LST_RES
            (44 , 1         , 4     , 1         , 1         ),  # Read SECM_PSC_VBAT_LST_RES and SECM_PSC_VCER_LST_RES
            (45 , 1         , 2     , 1         , 0         ),  # Write PRMPSC_DIAG_KEY = 0xB7AA
            (46 , 1         , 2     , 1         , 0         ),  # Write SECPSC_DIAG_KEY = 0xB7AA
            (47 , 1         , 2     , 1         , 0         ),  # Write PRMPSC_ARM_KEY = 0xDEAD
            (48 , 1         , 2     , 1         , 0         ),  # Write SECPSC_ARM_KEY = 0xDEAD
            (49, 1, 10, 1, 1),  # Read PRMPSC_CER_ESR, PRMPSC_CER_CAP, PRMPSC_RHS, PRMPSC_RSQUIB, PRMPSC_RLS
            (50, 1, 10, 1, 1),  # Read SECPSC_CER_ESR, SECPSC_CER_CAP, SECPSC_RHS, SECPSC_RSQUIB, SECPSC_RLS
            (51, 1, 2, 1, 1),  # Read SYS_SYNC_STAT
            # (49 , 1         , 6     , 1         , 1         ),  # Read PRMPSC_VCER1_DIAG, VCER2 and IDISCHARGE
            # (50 , 1         , 6     , 1         , 1         ),  # Read SECPSC_VCER1_DIAG, VCER2 and IDISCHARGE
            # (51 , 1         , 2     , 1         , 1         ),  # Read PRMPSC_VCER3_DIAG
            # (52 , 1         , 2     , 1         , 1         ),  # Read SECPSC_VCER3_DIAG
            # (53 , 1         , 10    , 1         , 1         ),  # Read PRMPSC_CER_ESR, PRMPSC_CER_CAP, PRMPSC_RHS, PRMPSC_RSQUIB, PRMPSC_RLS
            # (54 , 1         , 10    , 1         , 1         ),  # Read SECPSC_CER_ESR, SECPSC_CER_CAP, SECPSC_RHS, SECPSC_RSQUIB, SECPSC_RLS
            # (55 , 1         , 2     , 1         , 1         ),  # Read PRMM_INT_VDDA_LST_RES
            # (56 , 1         , 2     , 1         , 1         ),  # Read PRMM_INT_VDDC_LST_RES
            # (57 , 1         , 4     , 1         , 1         ),  # Read PRMM_INT_VREF5V0_LST_RES, PRMM_INT_VREF2V5_LST_RES
            # (58 , 1         , 2     , 1         , 1         ),  # Read SECM_INT_VDDA_LST_RES
            # (59 , 1         , 2     , 1         , 1         ),  # Read SECM_INT_VDDC_LST_RES
            # (60 , 1         , 4     , 1         , 1         ),  # Read SECM_INT_VREF5V0_LST_RES, SECM_INT_VREF2V5_LST_RES
            # (61 , 1         , 2     , 1         , 1         ),  # Read SYS_SYNC_STAT
        ]

        # OP define the indice in script param, Last param (not noted here) is COM
        self.DISP_PARAMS = [
        #Name               , Op1, Pos1, Len1, Op2, Pos2, Len2, Op3, Pos3, Len3, Op4, Pos4, Len4, Compute_func      , Format  , Delta , Dmin  , Dmax  , Min   , Max
        ('P_VI0P_S'         , 9  , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0x0005, 0     , 0x0005, 'X' ),
        ('P_I1P_S'          , 10 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0x0005, 0     , 0x0005, 'X' ),
        ('P_IO_PER_LIMHS'   , 11 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('P_IO_PER_LIMLS'   , 11 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('S_VI0P_S'         , 12 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0x0005, 0     , 0x0005, 'X' ),
        ('S_I1P_S'          , 13 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0x0005, 0     , 0x0005, 'X' ),
        ('S_IO_PER_LIMHS'   , 14 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('S_IO_PER_LIMLS'   , 14 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('ACC_ERR'          , 15 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('GRP_FLT_S'        , 15 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SUPPLY_FLT_S0'    , 15 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('COM_FLT_S'        , 16 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('MEAS_FLT_S'       , 16 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('PSC_FLT_S'        , 16 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('S_ACC_ERR'        , 17 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('S_GRP_FLT_S'      , 17 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('S_SUPPLY_FLT_S0'  , 17 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('S_COM_FLT_S'      , 18 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('S_MEAS_FLT_S'     , 18 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('S_PSC_FLT_S'      , 18 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('WKUP_REAS0'       , 19 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0x0000, 0     , 0x0000, 'X' ),
        ('S_WKUP_REAS0'     , 20 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0x0000, 0     , 0x0000, 'X' ),
        ('RST_REAS'         , 21 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0x0000, 0     , 0x0000, 'X' ),
        ('S_RST_REAS'       , 22 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0x0000, 0     , 0x0000, 'X' ),
        ('SYS_SYNC_S'       , 51 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFault    ,'{:04X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('SYNC_LOCK_FLT'    , 51 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convFaultSync,'{:01X}' , 1     , 0     , 0xFFFF, 0     , 0xFFFF, 'X' ),
        ('P_VI0P_R'         , 1  , 0   , 2   , 1  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasVd   ,'{:2.3f}', 1     , -0.047, 0.047 , 56    , 64    , 'V' ),
        ('S_VI0P_R'         , 3  , 0   , 2   , 3  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasVd   ,'{:2.3f}', 1     , -0.047, 0.047 , 56    , 64    , 'V' ),
        ('P_I1P_R'          , 2  , 0   , 2   , 2  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasId   ,'{:3.1f}', 1     , -0.5  , 0.5   , -12   , 12    , 'mV'),
        ('S_I1P_R'          , 4  , 0   , 2   , 4  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasId   ,'{:3.1f}', 1     , -0.5  , 0.5   , -12   , 12    , 'mV'),
        ('P_IO1_R'          , 5  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas     ,'{:2.3f}', 1     , -0.016, 0.016 , 2.2   , 2.8   , 'V' ),
        ('P_IO2_R'          , 5  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas_2V5 ,'{:2.3f}', 1     , -0.016, 0.016 , 3.7   , 4.3   , 'V' ),
        ('P_IO3_R'          , 5  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas     ,'{:2.3f}', 1     , -0.016, 0.016 , 2.1   , 2.7   , 'V' ),
        ('P_IO4_R'          , 5  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas_2V5 ,'{:2.3f}', 1     , -0.016, 0.016 , 3.7   , 4.3   , 'V' ),
        ('P_IO5_R'          , 5  , 10  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas     ,'{:2.3f}', 1     , -0.016, 0.016 , 2.1   , 2.7   , 'V' ),
        ('P_IO6_R'          , 5  , 12  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas     ,'{:2.3f}', 1     , -0.016, 0.016 , 0.9   , 1.5   , 'V' ),
        ('S_IO1_R'          , 6  , 2   , 2   , 4  , 32  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas     ,'{:2.3f}', 1     , -0.016, 0.016 , 2.2   , 2.8   , 'V' ),
        ('S_IO2_R'          , 6  , 4   , 2   , 4  , 30  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas_2V5 ,'{:2.3f}', 1     , -0.016, 0.016 , 3.7   , 4.3   , 'V' ),
        ('S_IO3_R'          , 6  , 6   , 2   , 4  , 28  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas     ,'{:2.3f}', 1     , -0.016, 0.016 , 2.1   , 2.7   , 'V' ),
        ('S_IO4_R'          , 6  , 8   , 2   , 4  , 26  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas_2V5 ,'{:2.3f}', 1     , -0.016, 0.016 , 3.7   , 4.3   , 'V' ),
        ('S_IO5_R'          , 6  , 10  , 2   , 4  , 24  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas     ,'{:2.3f}', 1     , -0.016, 0.016 , 2.1   , 2.7   , 'V' ),
        ('S_IO6_R'          , 6  , 12  , 2   , 4  , 22  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas     ,'{:2.3f}', 1     , -0.016, 0.016 , 0.9   , 1.5   , 'V' ),
        ('P_ICTEMP_R'       , 7  , 0   , 2   , 4  , 18  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convTemp     ,'{:2.3f}', 1     , -3    , 3     , 10    , 65    , '°C'),
        ('S_ICTEMP_R'       , 8  , 0   , 2   , 4  , 16  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convTemp     ,'{:2.3f}', 1     , -3    , 3     , 10    , 65    , '°C'),
        ('P_PSC_VBAT_LST'   , 43 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVbatVcer ,'{:2.3f}', 1     , -2    , 2     , 21    , 25    , 'V' ),
        ('S_PSC_VBAT_LST'   , 44 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVbatVcer ,'{:2.3f}', 1     , -2    , 2     , 21    , 25    , 'V' ),
        ('P_PSC_VCER_LST'   , 43 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVbatVcer ,'{:2.3f}', 0     , 17.5  , 18.5  , 17.5  , 18.5  , 'V' ),
        ('S_PSC_VCER_LST'   , 44 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVbatVcer ,'{:2.3f}', 0     , 17.5  , 18.5  , 17.5  , 18.5  , 'V' ),
        ('P_PSC_CER_ESR'    , 49 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVesr     ,'{:2.3f}', 0     , -0.2  , 0.2   , 1.8   , 2.2   , 'Ohm' ),
        ('S_PSC_CER_ESR'    , 50 , 0   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVesr     ,'{:2.3f}', 0     , -0.2  , 0.2   , 1.8   , 2.2   , 'Ohm' ),
        ('P_PSC_CER_CAP'    , 49 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVcap     ,'{:2.3f}', 1     , -0.0132,0.0132, 0.3168,0.3432 , 'mF' ),
        ('S_PSC_CER_CAP'    , 50 , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVcap     ,'{:2.3f}', 1     , -0.0132,0.0132, 0.3168,0.3432 , 'mF' ),
        ('P_PSC_RHS'        , 49 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVrhs     ,'{:2.3f}', 0     , 0.008  , 0.070, 0.008 , 0.070 , 'V' ),
        ('S_PSC_RHS'        , 50 , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVrhs     ,'{:2.3f}', 0     , 0.008  , 0.070, 0.008 , 0.070 , 'V' ),
        ('P_PSC_RSQUIB'     , 49 , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVrlsSq0  ,'{:2.3f}', 1     , -0.56 , 0.56  , 1.44  , 2.56  , 'Ohm' ),
        ('S_PSC_RSQUIB'     , 50 , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVrlsSq1  ,'{:2.3f}', 1     , -0.56 , 0.56  , 1.44  , 2.56  , 'Ohm' ),
        ('P_PSC_RLS'        , 49 , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVrlsSq2  ,'{:2.3f}', 0     , 0.010 , 0.060, 0.010  , 0.060 , 'V' ),
        ('S_PSC_RLS'        , 50 , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , -1 , 0   , 0   , self.convVrlsSq2  ,'{:2.3f}', 0     , 0.010 , 0.060, 0.010  , 0.060 , 'V' ),
        ('VI0P_P-S'         , 1  , 0   , 2   , 1  , 2   , 2   ,  3 , 0   , 2   ,  3 , 2   , 2   , self.convMeasVdD  ,'{:1.4f}', 0     ,-0.006 , 0.006 , -0.006, 0.006 , 'V' ),
        ('I1P_P-S'          , 2  , 0   , 2   , 2  , 2   , 2   ,  4 , 0   , 2   ,  4 , 2   , 2   , self.convMeasIdD  ,'{:2.3f}', 0     ,-0.5   , 0.5   , -0.5  , 0.5   , 'mV' ),
        ('IO1_P-S'          , 5  , 2   , 2   , 6  , 2   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD    ,'{:1.4f}', 0     , -0.016, 0.016 , -0.016, 0.016 , 'V' ),
        ('IO2_P-S'          , 5  , 4   , 2   , 6  , 4   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas_2V5D,'{:1.4f}', 0     , -0.016, 0.016 , -0.016, 0.016 , 'V' ),
        ('IO3_P-S'          , 5  , 6   , 2   , 6  , 6   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD    ,'{:1.4f}', 0     , -0.016, 0.016 , -0.016, 0.016 , 'V' ),
        ('IO4_P-S'          , 5  , 8   , 2   , 6  , 8   , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeas_2V5D,'{:1.4f}', 0     , -0.016, 0.016 , -0.016, 0.016 , 'V' ),
        ('IO5_P-S'          , 5  , 10  , 2   , 6  , 10  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD    ,'{:1.4f}', 0     , -0.016, 0.016 , -0.016, 0.016 , 'V' ),
        ('IO6_P-S'          , 5  , 12  , 2   , 6  , 12  , 2   , -1 , 0   , 0   , -1 , 0   , 0   , self.convMeasD    ,'{:1.4f}', 0     , -0.016, 0.016 , -0.016, 0.016 , 'V' ),
        ]

        self.updateframeByID()

        self.convVrlsSq_avg0 = 0
        self.convVrlsSq_avg1 = 0

        self.last_sync_lock_bit = 0

    # Conversion functions
    def convFault(self, val1, val2=0, val3=0, val4=0):
        return val1 & 65535

    # If 2 consecutive lock bit = 0, raise fault (return 1 means fault)
    def convFaultSync(self, val1, val2=0, val3=0, val4=0):
        if self.last_sync_lock_bit == 0 and (val1 & 0x1) == 0:
            self.last_sync_lock_bit = val1 & 0x1
            return 1
        else:
            self.last_sync_lock_bit = val1 & 0x1
            return 0

    def convMeas(self, val1, val2=0, val3=0, val4=0):
        if val1 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            return (65536 - int(val1)) * (-0.000154)  # 2^15 - val
        else:
            return val1 * 0.000154

    def convMeasD(self, val1, val2, val3=0, val4=0):
        ################
        if val1 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            val_A = (65536 - int(val1)) * (-0.000154)  # 2^15 - val
        else:
            val_A = val1 * 0.000154

        if val2 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            val_B = (65536 - int(val2)) * (-0.000154)  # 2^15 - val
        else:
            val_B = val2 * 0.000154
        return val_A - val_B

    def convMeas_2V5(self, val1, val2=0, val3=0, val4=0):
        if val1 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            return (65536 - int(val1)) * (-0.000154) + 2.5  # 2^15 - val
        else:
            return val1 * 0.000154 + 2.5

    def convMeas_2V5D(self, val1, val2, val3=0, val4=0):
        #####################
        if val1 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            val_A = (65536 - int(val1)) * (-0.000154) + 2.5  # 2^15 - val
        else:
            val_A = val1 * 0.000154 + 2.5

        if val2 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            val_B = (65536 - int(val2)) * (-0.000154) + 2.5  # 2^15 - val
        else:
            val_B = val2 * 0.000154 + 2.5

        return val_A - val_B

    def convMeasVd(self, val1, val2, val3=0, val4=0):
        val = int(val2) * 65536 + int(val1)
        if val2 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            return (4294967296 - val) * (-129.1) / (2**21 * 5.1)    # 2^31 - val   5.1 / 124
        else:
            return val * 129.1 / (2**21 * 5.1)   # Bridge ratio is (12k/(82k+12k)) => 12/94 # B0 Bridge ratio is (5.1k/(124k+5.1k)) => 5.1/129.1

    def convMeasVdD(self, val1, val2, val3, val4):
        ######################
        val = int(val2) * 65536 + int(val1)
        if val2 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            val_A = (4294967296 - val) * (-129.1) / (2**21 * 5.1)    # 2^31 - val   5.1 / 124
        else:
            val_A = val * 129.1 / (2**21 * 5.1)   # Bridge ratio is (12k/(82k+12k)) => 12/94 # B0 Bridge ratio is (5.1k/(124k+5.1k)) => 5.1/129.1

        val = int(val4) * 65536 + int(val3)
        if val4 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            val_B = (4294967296 - val) * (-129.1) / (2 ** 21 * 5.1)  # 2^31 - val   5.1 / 124
        else:
            val_B = val * 129.1 / (
                        2 ** 21 * 5.1)  # Bridge ratio is (12k/(82k+12k)) => 12/94 # B0 Bridge ratio is (5.1k/(124k+5.1k)) => 5.1/129.1

        return val_A - val_B

    def convMeasId(self, val1, val2, val3=0, val4=0):
        val = (int(val2) * 65536) + int(val1)   #int() cast is necessary, if not overflow occurs
        if val2 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            return ((4294967296 - val) * (-0.00005)) / 2.048  # Shunt 50uOm programmed in fuse
        else:
            return val * 0.00005 / 2.048    # Shunt 50uOm programmed in fuse

    def convMeasIdD(self, val1, val2, val3, val4):
        val = (int(val2) * 65536) + int(val1)   #int() cast is necessary, if not overflow occurs
        if val2 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            val_A = ((4294967296 - val) * (-0.00005)) / 2.048  # Shunt 50uOm programmed in fuse
        else:
            val_A = val * 0.00005 / 2.048    # Shunt 50uOm programmed in fuse

        val = (int(val4) * 65536) + int(val3)  # int() cast is necessary, if not overflow occurs
        if val4 > 32767:  # 2^15 - 1 = pow(2, 15) - 1
            val_B = ((4294967296 - val) * (-0.00005)) / 2.048  # Shunt 50uOm programmed in fuse
        else:
            val_B = val * 0.00005 / 2.048  # Shunt 50uOm programmed in fuse

        return val_A - val_B

    def convTemp(self, val1, val2=0, val3=0, val4=0):
        return (val1 * 0.0324) - 273.15

    def convVbatVcer(self, val1, val2=0, val3=0, val4=0):
        return val1 * 0.001

    def convVcerx(self, val1, val2=0, val3=0, val4=0):
        return val1 * 0.0000385284

    def convVidis(self, val1, val2=0, val3=0, val4=0):
        return val1 * 0.0000385284 * 140.625

    def convVesr(self, val1, val2=0, val3=0, val4=0):
        #return val1 * 0.0000385284 / (5 * 0.036) #40mA current
        #return val1 * 0.0000385284 / (5 * 0.096) #100mA current
        return val1 * 0.0000385284 / (2 * 0.098)  # 100mA current & gain = 2

    def convVcap(self, val1, val2=0, val3=0, val4=0):
        if val1 != 0:
            #return 5 * 0.036 * 0.64 / (val1 * 0.0000385284) #40mA current
            #return 5 * 0.096 * 0.64 / (val1 * 0.0000385284) #100mA current
            return 2 * 0.098 * 0.64 / (val1 * 0.0000385284)  # 100mA current & gain = 2
        else:
            return 0

    def convVrhs(self, val1, val2=0, val3=0, val4=0):
        # return val1 * 0.0000385284 / 0.017
        # return val1 * 0.0000385284 / 0.025
        return val1 * 0.0000385284

    def convVrlsSq0(self, val1, val2=0, val3=0, val4=0):
        #return val1 * 0.0000385284 / 0.036 # 40mA current
        return val1 * 0.0000385284 / 0.098 # 100mA current

    def convVrlsSq1(self, val1, val2=0, val3=0, val4=0):
        # return val1 * 0.0000385284 / 0.036 # 40mA current
        return val1 * 0.0000385284 / 0.098  # 100mA current

    def convVrlsSq2(self, val1, val2=0, val3=0, val4=0):
        #return val1 * 0.0000385284 / 0.036 # 40mA current
        #return val1 * 0.0000385284 / 0.098 # 100mA current
        return val1 * 0.0000385284

    def convVdda_2V5(self, val1, val2=0, val3=0, val4=0):
        return val1 * 0.000154

    def convVddc_5V0(self, val1, val2=0, val3=0, val4=0):
        return val1 * 0.000308

DEVICES_LIST = [MC33664(), BMA6402(),  BMA7126T(), MC33777()]
