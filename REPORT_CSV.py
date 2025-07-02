"""____________________________________________________

FILENAME: REPORT_CSV.py
AUTHOR: David SCLAFER
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import os
import numpy as np
import CONST as const
import DEVICES as dev

class REPORT_CSV():

    def __init__(self, folderPath, projectName, testName, setupName, refAVG, resAVG, microRev, gridSetup):

        self.folderPath = folderPath
        self.projectName = projectName
        self.testName = testName
        self.setupName = setupName
        self.refAVG = refAVG
        self.resAVG = resAVG
        self.microRev = microRev
        self.gridSetup = gridSetup
        self.matrix = []
        self.maskMatrixnNotDisplay = []
        self.maxDispParamNb = 0
        self.nbCol = 0

        self.fName = testName
        self.dirPath = folderPath+'\\'+projectName+'\\'+testName
        ind_file = ''
        cpt = 0
        #Check if file exists and rename it correctly
        try:
            if not os.path.exists(self.dirPath):
                os.makedirs(self.dirPath)
            while self.reportExists(self.dirPath, testName + ind_file + '.csv'):
                cpt += 1
                ind_file = '-' + str(cpt)

            self.fName = testName + ind_file + '.csv'
            self.file = open(self.dirPath + '\\' + self.fName,'w')
        except IOError:
            return

        #self.computeDisplayableMatrix()
        self.createMatrixTitle()

    def __del__(self):
        try:
            self.file.close()
        except:
            print('file already closed')

    def computeDisplayableMatrix(self):
        self.maskMatrixnNotDisplay = np.zeros((self.deviceType.DISP_PARAMS_NB + 9, (self.nbDevice + 3) * 5 + 2 + 2), np.bool)
        paramDisplayableByCID = np.zeros((self.deviceType.DISP_PARAMS_NB, self.nbDevice + 1), np.bool)
        for i, row in enumerate(paramDisplayableByCID):
            for j, cell in enumerate(row):
                opt1 = self.deviceType.DISP_PARAMS[i][1]
                k = 0
                while (k < len(self.deviceType.SCRIPT_FRAMES)) and (self.deviceType.SCRIPT_FRAMES[k][0] != int(opt1)):
                    k += 1
                if k >= self.deviceType.DISP_PARAMS_NB:
                    print('Error loading CSV')
                else:
                    paramDisplayableByCID[i][j] = bool(self.deviceType.SCRIPT_FRAMES[k][1])

        for i in range(5):
            for j in range(self.deviceType.DISP_PARAMS_NB):
                for k in range(self.nbDevice + 1):
                    if k == 0:  # No CID column
                        self.maskMatrixnNotDisplay[j + 8][3 + k + i * (self.nbDevice + 3)] = paramDisplayableByCID[j][k]
                    else:
                        self.maskMatrixnNotDisplay[j + 8][3 + k + i * (self.nbDevice + 3)] = not \
                        paramDisplayableByCID[j][k]

    def cellNotDisplayable(self):
        for i, row in enumerate(self.maskMatrixnNotDisplay):
            for j, cell in enumerate(row):
                if cell:
                    self.matrix[i][j] = '-'

    def reportExists(self, path, reportName):
        # r=root, d=directories, f = files
        for r, d, files in os.walk(path):
            for f in files:
                if reportName == f:
                    return True
        return False

    def saveFile(self):
        self.file.flush()
        os.fsync(self.file)

    def closeFile(self):
        self.file.close()

    def initMatrix(self):
        self.maxDispParamNb = 0
        self.nbCol = 0
        for deviceID in self.gridSetup.devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]
            self.nbCol = self.nbCol + 2 + 6 * (device.NbNodes + 2)   # 2 for Min max delta spec, then 6 matrix with blanc delimiter + reg base display
            if device.DISP_PARAMS_NB > self.maxDispParamNb:
                self.maxDispParamNb = device.DISP_PARAMS_NB

        self.matrix = np.full((self.maxDispParamNb + 8, self.nbCol + 1), '', object)

    def createMatrixTitle(self):
        # Write Header
        row = ['Project', self.projectName, '', 'Test', self.testName, '', 'Setup', self.setupName, '', '', '', 'Rev u', str(self.microRev), 'Ref AVG', str(self.refAVG), 'Res AVG', str(self.resAVG)]
        line = ''
        for val in row:
            line += str(val) + const.CSV_SEPARATOR
        line = line[:-1] + '\n\n'
        self.file.write(line)

        # Write Setup
        nbRow = self.gridSetup.GetNumberRows()
        nbCol = self.gridSetup.GetNumberCols()
        for row in range(nbRow):
            line = ''
            for col in range(nbCol):
                line += str(self.gridSetup.GetCellValue((row, col))) + const.CSV_SEPARATOR
            line = line[:-1] + '\n'
            self.file.write(line)

        self.initMatrix()

    def addDatas1Freq2File(self, Header, SerialStatus, devTypesUsed, Logs, LogType = 0):
        #self.initMatrix()
        self.addHeaderInfos(0, 0, Header, LogType)
        self.addSerialStatus(2, 0, SerialStatus)
        colPos = 0

        for deviceID in devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]
            self.matrix[6][colPos] = device.DEV_NAME
            self.addMaxDelta(7, colPos, device)
            self.addInfoCOM(2, colPos + 2, device)
            self.addCOM(6, colPos + 2 + 3 * (device.NbNodes + 2), device)
            self.addDatas(7, colPos + 2, 'REF', device.matrixRef, device)
            self.addDatas(7, colPos + 2 + (device.NbNodes + 2), 'MIN', device.matrixDeltaMin, device)
            self.addDatas(7, colPos + 2 + 2 * (device.NbNodes + 2), 'MAX', device.matrixDeltaMax, device)
            self.addDatas(7, colPos + 2 + 3 * (device.NbNodes + 2), 'FAIL CW', device.matrixFail, device)
            self.addDatas(7, colPos + 2 + 4 * (device.NbNodes + 2), 'FAIL AM', device.matrixFailAM, device)
            self.addDatas(7, colPos + 2 + 5 * (device.NbNodes + 2), 'FAIL PM', device.matrixFailPM, device)
            colPos = colPos + 2 + 6 * (device.NbNodes + 2)

        self.addLogs(1, colPos, Logs)
        self.cellNotDisplayable()
        self.appendMatrix2File()

    def addHeaderInfos(self, lpos, cpos, Header, LogType):
        if LogType == 0:
            HeaderName = ['Freq ID', 'Freq [kHz]', 'N res', 'Target', '1st fail', '1st type', '1st node', '1st param']
        else:
            HeaderName = ['Time ID', 'Time [s]', 'N res', 'Target', '1st fail', '1st type', '1st node', '1st param']

        for i in range(len(HeaderName)):
            self.matrix[lpos][cpos + i] = HeaderName[i]

        header2 = Header
        devFail = header2[-1]
        if devFail is not None:
            header2 = header2[:-1]
            header2.append(devFail.DEV_NAME)
            if devFail.PHY:
                header2.append("")
            else:
                header2.append(str(devFail.NodesName[devFail.nodeFail]))

            if devFail.paramFail == devFail.DISP_PARAMS_NB:
                header2.append('TPL')
            else:
                header2.append(devFail.DISP_PARAMS[devFail.paramFail][0] + ' [' + devFail.DISP_PARAMS[devFail.paramFail][20] + ']')
        else:
            header2.append("")
            header2.append("")

        for i in range(len(header2)):
            self.matrix[lpos + 1][cpos + i] = header2[i]

    def addSerialStatus(self, lpos, cpos, SerialStatus):
        self.matrix[lpos][cpos] = 'Serial status'
        self.matrix[lpos+1][cpos] = 'ERR/TO'
        self.matrix[lpos + 1][cpos + 1] = 'OK'
        i = 0
        for row in SerialStatus:
            j = 0
            for val in row:
                self.matrix[lpos+2+i][cpos+j] = val
                j += 1
            i += 1

    def addInfoCOM(self, lpos, cpos, device):
        if device.PHY:
            for val in range(const.TPL_STATUS_NB):
                self.matrix[lpos + val][cpos] = const.TPL_STATUS[val]
                self.matrix[lpos + val][cpos + 1] = device.matrixCnt[0][val]
        else:
            for val in range(const.TPL_STATUS_NB):
                self.matrix[lpos + val][cpos] = const.TPL_STATUS[val]
                for index in range(1, device.NbNodes + 1):
                    self.matrix[lpos + val][cpos + index] = device.matrixCnt[index][val]

    def addCOM(self, lpos, cpos, device):
        self.matrix[lpos][cpos] = 'COM'
        self.matrix[lpos][cpos + device.NbNodes + 2] = 'COM'
        self.matrix[lpos][cpos + 2 * (device.NbNodes + 2)] = 'COM'

        if device.PHY:
            self.matrix[lpos][cpos + 1] = device.matrixFail[0, device.DISP_PARAMS_NB]
            self.matrix[lpos][cpos + 1 + device.NbNodes + 2] = device.matrixFailAM[0, device.DISP_PARAMS_NB]
            self.matrix[lpos][cpos + 1 + 2 * (device.NbNodes + 2)] = device.matrixFailPM[0, device.DISP_PARAMS_NB]
        else:
            for index in range(1, device.NbNodes + 1):
                self.matrix[lpos][cpos + index] = device.matrixFail[index, device.DISP_PARAMS_NB]
                self.matrix[lpos][cpos + index + device.NbNodes + 2] = device.matrixFailAM[index, device.DISP_PARAMS_NB]
                self.matrix[lpos][cpos + index + 2 * (device.NbNodes + 2)] = device.matrixFailPM[index, device.DISP_PARAMS_NB]

    def addMaxDelta(self, lpos, cpos, device):
        self.matrix[lpos][cpos] = 'Max DELTA'
        for param in range(device.DISP_PARAMS_NB):
            self.matrix[lpos + 1 + param][cpos] = device.deltaMin[param]
            self.matrix[lpos + 1 + param][cpos + 1] = device.deltaMax[param]

    def addDatas(self, lpos, cpos, name, matrix, device):
        self.matrix[lpos][cpos] = name
        if device.PHY:
            self.matrix[lpos][cpos + 1] = device.NodesName[0]
            for param in range(device.DISP_PARAMS_NB):
                self.matrix[lpos + 1 + param][cpos] = device.DISP_PARAMS[param][0] + ' [' + device.DISP_PARAMS[param][20] + ']'
                self.matrix[lpos + 1 + param][cpos + 1] = matrix[0][param]
        else:
            for index in range(1, device.NbNodes + 1):
                self.matrix[lpos][cpos + index] = device.NodesName[index]
            for param in range(device.DISP_PARAMS_NB):
                self.matrix[lpos + 1 + param][cpos] = device.DISP_PARAMS[param][0] + ' [' + device.DISP_PARAMS[param][20] + ']'
                for index in range(1, device.NbNodes + 1):
                    self.matrix[lpos + 1 + param][cpos + index] = matrix[index][param]

    def addLogs(self, lpos, cpos, Logs):
        self.matrix[lpos][cpos] = 'LOGS'
        self.matrix[lpos + 1][cpos] = str(Logs.encode())[2:-1].replace(',', '.')

    def appendMatrix2File(self):
        list = [''] * (self.nbCol + 1)
        self.file.write(const.CSV_SEPARATOR.join(list) + '\n')  # Empty line
        line = ''
        for row in self.matrix:
            line = ''
            for val in row:
                line += str(val) + const.CSV_SEPARATOR
            line = line[:-1] + '\n'
            self.file.write(line)