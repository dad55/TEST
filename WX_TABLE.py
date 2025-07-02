"""____________________________________________________

FILENAME: WX_TABLE.py
AUTHOR: Guerric PANIS
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import CONST as const
import DEVICES as dev
import wx.grid
import wx.lib.newevent
import numpy as np

statisticsClicked, EVT_STATICSCLICKED = wx.lib.newevent.NewEvent()

class gridDISPLAY(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.BORDER_DEFAULT) #wx.BORDER_SUNKEN)
        self.parent = parent                                                                    # Grid parent.
        self.grid = False                                                                       # Just a flag to use with create / draw grid methods
        self.fontText = wx.Font(8, wx.MODERN, wx.FONTSTYLE_NORMAL, wx.NORMAL, 0, "Arial")       # Font used for values.
        self.fontHeaders = wx.Font(8, wx.MODERN, wx.FONTSTYLE_ITALIC, wx.NORMAL, 0, "Arial")    # Font used for Headers.
        self.createGrid(const.DISP_PARAMS_NB_MAX + const.DISP_PARAM_OFFSET, const.DISP_MAX_COLUMN)

        #self.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.onCellClicked)
        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.onCellClicked)
        #self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.onCellClicked)
        self.devUsed = None

    def onCellClicked(self, event):
        event.Skip()
        row = event.GetRow()
        col = event.GetCol()
        self.ClearSelection()

        for deviceID in reversed(self.devUsed):
            device = dev.DEVICES_LIST[deviceID]
            if (row > const.DISP_PARAM_OFFSET) and (col > device.DISP_COL_OFFSET):  # Clear param colors
                self.clearColorsDevice(device)
                return
            elif (row == (const.DISP_PARAM_OFFSET - 1)) and (col == device.DISP_COL_OFFSET):  # Change display type
                if self.GetCellValue(row, col) == 'DELTA':
                    device.dispDelta = False
                    self.SetCellValue(row, col, 'ABS')
                else:
                    device.dispDelta = True
                    self.SetCellValue(row, col, 'DELTA')
                return
            elif (row == 0) and (col == device.DISP_COL_OFFSET):  # Hide/expand device type
                if self.GetCellValue(row, col) == device.DEV_NAME + ' <<':
                    self.SetCellValue(row, col, device.DEV_NAME + ' >>')
                    for col in range(device.DISP_COL_OFFSET + 1, device.DISP_COL_OFFSET + 1 + device.NbNodes):
                        self.HideCol(col)
                else:
                    self.SetCellValue(row, col, device.DEV_NAME + ' <<')
                    for col in range(device.DISP_COL_OFFSET + 1, device.DISP_COL_OFFSET + 1 + device.NbNodes):
                        self.ShowCol(col)
                return

    def createGrid(self, nb_row, nb_col):
        self.grid = True
        self.CreateGrid(nb_row, nb_col)  # Create grid.
        self.SetGridLineColour(const.DISP_DEFAULT_COLOR)
        self.HideRowLabels()  # Hide automatic row labels.
        self.HideColLabels()  # Hide automatic column labels.

        self.DisableCellEditControl()
        for i in range(nb_col):
            self.DisableColResize(i)
            self.SetColSize(i, const.DISP_DEFAULT_COL_WIDTH)
        for i in range(nb_row):
            self.DisableRowResize(i)
        self.DisableDragRowSize()
        self.DisableDragGridSize()
        self.DisableKeyboardScrolling()
        self.EnableDragCell(False)
        self.EnableDragColMove(False)
        #self.SetSelectionMode(wx.grid.Grid.GridSelectNone)
        #self.SetSelectionBackground(const.DISP_WHITE_COLOR)
        self.SetSelectionForeground(const.DISP_BLACK_COLOR)
        self.SetCellHighlightPenWidth(0)
        self.EnableEditing(False)  # The cells are not editable.

    def setCellValueFormat(self, row, col, the_format, value):
        if the_format[-2] == 'X':
            self.SetCellValue(row, col, the_format.format(int(value)))
        else:
            self.SetCellValue(row, col, the_format.format(value))

    def getColNumberNeeded(self, matrixSetup, devTypeUsed):
        nb = 0
        for deviceID in devTypeUsed:
            nb = nb + 1
            device = dev.DEVICES_LIST[deviceID]
            if device.PHY:
                nb = nb + 1 # 2 cols for one PHY
            else:
                for chain in range(const.MAX_CHAIN_NB):
                    phy_send = matrixSetup[1][chain + 1]
                    if phy_send != 9:
                        nd = 1
                        for node in range(const.MAX_DEVICE_NB):
                            revType = matrixSetup[3 + node][chain + 1]
                            type = dev.BCC_TYPE_INDEX[revType]
                            if type == deviceID:
                                nb = nb + 1
        return nb

    def drawDispGrid(self, matrixSetup, devTypeUsed):
        self.BeginBatch()
        #self.ClearGrid()
        self.devUsed = devTypeUsed
        colPos = 0
        maxDispParamNb = 0
        nbCols = self.GetNumberCols()
        nbColsNeeded = self.getColNumberNeeded(matrixSetup, devTypeUsed)
        if nbCols < nbColsNeeded:
            self.AppendCols(nbColsNeeded - nbCols)
        elif nbCols > nbColsNeeded:
            self.DeleteCols(nbColsNeeded, nbCols - nbColsNeeded)

        self.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
        #print(devTypeUsed)

        for deviceID in self.devUsed:
            device = dev.DEVICES_LIST[deviceID]
            device.NbNodes = 0
            self.drawRegBase(colPos, device)
            colPos = colPos + 1
            if device.DISP_PARAMS_NB > maxDispParamNb:
                maxDispParamNb = device.DISP_PARAMS_NB

            if device.PHY:
                self.SetCellBackgroundColour(const.DISP_PARAM_OFFSET - 1, colPos, const.DISP_DEFAULT_COLOR)
                colPos = colPos + 1
                device.NbNodes = 1
                device.NodesPos[0][0] = 0
            else:
                for chain in range(const.MAX_CHAIN_NB):
                    phy_send = matrixSetup[1][chain + 1]
                    if phy_send != 9:
                        nd = 1
                        for node in range(const.MAX_DEVICE_NB):
                            revType = matrixSetup[3 + node][chain + 1]
                            type = dev.BCC_TYPE_INDEX[revType]
                            if type == deviceID:
                                self.SetColSize(colPos, const.DISP_DEFAULT_COL_WIDTH)
                                self.SetCellSize(0, colPos, 1, 1)

                                for row in range(1, const.DISP_PARAM_OFFSET - 1):
                                    self.SetCellValue(row, colPos, '')
                                    self.SetCellBackgroundColour(row, colPos, const.DISP_WHITE_COLOR)
                                NodeName = 'CH ' + str(chain) + ' ND ' + str(nd)
                                self.SetCellValue(const.DISP_PARAM_OFFSET - 1, colPos, NodeName)
                                self.SetCellBackgroundColour(const.DISP_PARAM_OFFSET - 1, colPos, const.DISP_DEFAULT_COLOR)

                                for row in range(const.DISP_PARAM_OFFSET, const.DISP_PARAM_OFFSET + const.DISP_PARAMS_NB_MAX):
                                    self.SetCellSize(row, colPos, 1, 1)
                                    self.SetCellValue(row, colPos, '')
                                    self.SetCellBackgroundColour(row, colPos, const.DISP_WHITE_COLOR)

                                device.NbNodes = device.NbNodes + 1
                                device.NodesPos[chain][nd] = colPos - device.DISP_COL_OFFSET
                                device.NodesName[colPos - device.DISP_COL_OFFSET] = NodeName
                                nd = nd + 1
                                colPos = colPos + 1
                            elif revType != 0:
                                nd = nd + 1

        for deviceID in self.devUsed:
            device = dev.DEVICES_LIST[deviceID]
            self.SetCellSize(0, device.DISP_COL_OFFSET, 1, device.NbNodes + 1)
            if device.DISP_PARAMS_NB < maxDispParamNb:
                for row in range(const.DISP_PARAM_OFFSET + device.DISP_PARAMS_NB, const.DISP_PARAM_OFFSET + maxDispParamNb):
                    self.SetCellBackgroundColour(row, device.DISP_COL_OFFSET, const.DISP_WHITE_COLOR)
                    self.SetCellValue(row, device.DISP_COL_OFFSET, '')
                self.SetCellSize(const.DISP_PARAM_OFFSET + device.DISP_PARAMS_NB, device.DISP_COL_OFFSET, const.DISP_PARAMS_NB_MAX - device.DISP_PARAMS_NB, device.NbNodes + 1)

        # Hide unused rows
        for row in range(const.DISP_PARAM_OFFSET, const.DISP_PARAM_OFFSET + maxDispParamNb):
            self.ShowRow(row)

        for row in range(const.DISP_PARAM_OFFSET + maxDispParamNb, const.DISP_PARAM_OFFSET + const.DISP_PARAMS_NB_MAX):
            self.HideRow(row)

        self.EndBatch()
        self.ForceRefresh()

    def drawRegBase(self, colPos, device):
        device.DISP_COL_OFFSET = colPos
        self.SetColSize(colPos, const.DISP_PARAM_COL_WIDTH)
        self.SetCellSize(0, colPos, 1, 1)
        self.SetCellValue(0, colPos, device.DEV_NAME + ' <<')
        self.SetCellBackgroundColour(0, colPos, const.DISP_DEFAULT_COLOR)
        # Counters
        for row in range(1, const.DISP_PARAM_OFFSET - 1):
            self.SetCellValue(row, colPos, const.TPL_STATUS[row - 1])
            self.SetCellBackgroundColour(row, colPos, const.DISP_BLUE_COLOR)

        # Params names
        for row in range(const.DISP_PARAM_OFFSET, const.DISP_PARAM_OFFSET + const.DISP_PARAMS_NB_MAX):
            self.SetCellSize(row, colPos, 1, 1)
            self.SetCellBackgroundColour(row, colPos, const.DISP_DEFAULT_COLOR)

        for row in range(const.DISP_PARAM_OFFSET, const.DISP_PARAM_OFFSET + device.DISP_PARAMS_NB):
            self.SetCellValue(row, colPos, device.DISP_PARAMS[row - const.DISP_PARAM_OFFSET][0] + ' [' + device.DISP_PARAMS[row - const.DISP_PARAM_OFFSET][20] + ']')

        self.SetCellValue(const.DISP_PARAM_OFFSET - 1, colPos, 'ABS')
        self.SetCellBackgroundColour(const.DISP_PARAM_OFFSET - 1, colPos, const.DISP_ORANGE_COLOR)

    def updateGridValues(self, devTypesUsed):
        self.BeginBatch()
        #print('Types Used ' + str(devTypesUsed))
        for deviceID in devTypesUsed:
            devType = dev.DEVICES_LIST[deviceID]
            if devType.dispDelta:
                dataset = devType.matrixDelta
                min = devType.deltaMin
                max = devType.deltaMax
            else:
                dataset = devType.matrixDisp
                min = devType.absMin
                max = devType.absMax

            if devType.PHY:
                theRange = range(0, devType.NbNodes)
                col = devType.DISP_COL_OFFSET + 1
            else:
                theRange = range(1, devType.NbNodes + 1)
                col = devType.DISP_COL_OFFSET

            for index in theRange:
                # Update counters
                for row in range(1, const.TPL_STATUS_NB + 1):
                    self.SetCellValue(row, col + index, str(devType.matrixCnt[index][row - 1]))

                    # Color update
                    if (row < const.TPL_STATUS_NB) and (devType.matrixCnt[index][row - 1] > 0):
                        self.SetCellBackgroundColour(row, col + index, const.DISP_RED_COLOR)
                    else:
                        self.SetCellBackgroundColour(row, col + index, const.DISP_WHITE_COLOR)

                # Update datas
                for row in range(const.DISP_PARAM_OFFSET, const.DISP_PARAM_OFFSET + devType.DISP_PARAMS_NB):
                    param = row - const.DISP_PARAM_OFFSET
                    self.setCellValueFormat(row, col + index, devType.DISP_PARAMS[param][14], dataset[index][param])
                    # Color update
                    if devType.DISP_PARAMS[param][20] == 'X':
                        if (int(dataset[index][param]) & int(max[param])) > 0:  # Digital parameter
                            self.SetCellBackgroundColour(row, col + index, const.DISP_RED_COLOR)
                    elif (dataset[index][param] < min[param]) or (dataset[index][param] > max[param]):  # Analog parameter
                        self.SetCellBackgroundColour(row, col + index, const.DISP_RED_COLOR)

        self.EndBatch()

    def updateGridCounters(self, devTypesUsed):
        self.BeginBatch()

        for deviceID in devTypesUsed:
            devType = dev.DEVICES_LIST[deviceID]

            if devType.PHY:
                theRange = range(0, devType.NbNodes)
                col = devType.DISP_COL_OFFSET + 1
            else:
                theRange = range(1, devType.NbNodes + 1)
                col = devType.DISP_COL_OFFSET

            for index in theRange:
                # Update counters
                for row in range(1, const.TPL_STATUS_NB + 1):
                    self.SetCellValue(row, col + index, str(devType.matrixCnt[index][row - 1]))
                    # Color update
                    if (row < const.TPL_STATUS_NB) and (devType.matrixCnt[index][row - 1] > 0):
                        self.SetCellBackgroundColour(row, col + index, const.DISP_RED_COLOR)
                    else:
                        self.SetCellBackgroundColour(row, col + index, const.DISP_WHITE_COLOR)

        self.EndBatch()

    def clearGridValues(self):
        self.BeginBatch()

        for deviceID in self.devUsed:
            device = dev.DEVICES_LIST[deviceID]
            for col in range(device.DISP_COL_OFFSET + 1, device.DISP_COL_OFFSET + device.NbNodes + 1):

                # Counters
                for row in range(1, const.TPL_STATUS_NB + 1):
                    self.SetCellValue(row, col, '')
                    self.SetCellBackgroundColour(row, col, const.DISP_WHITE_COLOR)

                # Params values
                for row in range(const.DISP_PARAM_OFFSET, const.DISP_PARAM_OFFSET + device.DISP_PARAMS_NB):
                    self.SetCellValue(row, col, '')
                    self.SetCellBackgroundColour(row, col, const.DISP_WHITE_COLOR)

        self.EndBatch()

    def clearColorsDevice(self, device):
        self.BeginBatch()

        for col in range(device.DISP_COL_OFFSET + 1, device.DISP_COL_OFFSET + device.NbNodes + 1):
            # Params values
            for row in range(const.DISP_PARAM_OFFSET, const.DISP_PARAM_OFFSET + device.DISP_PARAMS_NB):
                self.SetCellBackgroundColour(row, col, const.DISP_WHITE_COLOR)

        self.EndBatch()

    def clearColors(self):
        self.BeginBatch()
        for deviceID in self.devUsed:
            device = dev.DEVICES_LIST[deviceID]
            for col in range(device.DISP_COL_OFFSET + 1, device.DISP_COL_OFFSET + device.NbNodes + 1):
                # Params values
                for row in range(const.DISP_PARAM_OFFSET, const.DISP_PARAM_OFFSET + device.DISP_PARAMS_NB):
                    self.SetCellBackgroundColour(row, col, const.DISP_WHITE_COLOR)
        self.EndBatch()


class gridSETUP(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.BORDER_DEFAULT) # wx.BORDER_SUNKEN)
        self.parent = parent                                                                    # Grid parent.
        self.grid = False                                                                       # Just a flag to use with create / draw grid methods
        self.fontText = wx.Font(8, wx.MODERN, wx.FONTSTYLE_NORMAL, wx.NORMAL, 0, "Arial")       # Font used for values.
        self.fontHeaders = wx.Font(8, wx.MODERN, wx.FONTSTYLE_ITALIC, wx.NORMAL, 0, "Arial")    # Font used for Headers.
        self.createGrid(const.DISP_SETUP_GRID_OFFSET + const.MAX_DEVICE_NB, 5 + const.MAX_CHAIN_NB)

        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.onCellClicked)
        self.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.onSetupChanged)

        self.matrixSetup = np.zeros((const.DISP_SETUP_GRID_OFFSET + const.MAX_DEVICE_NB - 1, 1 + const.MAX_CHAIN_NB), np.int8)
        self.devTypesUsed = []
        self.scriptsUsed = []  # Indices are device type
        self.HWscripts = []
        self.HWscriptUsed = None
        self.wait = 0

        self.dispChanged = False

    def onCellClicked(self, event):
        event.Skip()
        event.GetEventObject().SetGridCursor(event.GetRow(), event.GetCol())

    def onSetupChanged(self, event):
        event.Skip()
        #print("Setup changed")
        col = event.GetCol()
        row = event.GetRow()
        if (col == 1) or (row == 1):    # Only number allowed for DEVADD and CADD
            try:
                int(self.GetCellValue(row, col))
            except ValueError:
                self.SetCellValue(row, col, '0')

        if col < (const.MAX_CHAIN_NB + 2):
            self.getSetupMatrix()
            self.getSetupTypesUsed()
            self.dispChanged = True
        else:
            self.getScriptUsed()

    def createGrid(self, nb_row, nb_col):
        self.grid = True
        self.CreateGrid(nb_row, nb_col)  # Create grid.
        self.SetGridLineColour(const.DISP_DEFAULT_COLOR)
        self.HideRowLabels()  # Hide automatic row labels.
        self.HideColLabels()  # Hide automatic column labels.

        self.DisableCellEditControl()
        for i in range(nb_col):
            self.DisableColResize(i)
            self.SetColSize(i, const.DISP_DEFAULT_COL_WIDTH)
        for i in range(nb_row):
            self.DisableRowResize(i)
        self.DisableDragRowSize()
        self.DisableDragGridSize()
        self.DisableKeyboardScrolling()
        self.EnableDragCell(False)
        self.EnableDragColMove(False)
        self.SetSelectionForeground(const.DISP_BLACK_COLOR)
        self.SetCellHighlightPenWidth(0)

    def drawSetupGrid(self):
        self.BeginBatch()
        self.ClearGrid()
        self.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

        # Chain ID dropdown menu
        choiceCADD = wx.grid.GridCellChoiceEditor(["%d" % i for i in range(1, const.MAX_CHAIN_NB + 1)])
        attrchoiceCADD = wx.grid.GridCellAttr()
        attrchoiceCADD.SetEditor(choiceCADD)

        choicePHY = wx.grid.GridCellChoiceEditor(dev.PHY_TYPE_LIST)
        attrchoicePHY = wx.grid.GridCellAttr()
        attrchoicePHY.SetEditor(choicePHY)

        choiceIC = wx.grid.GridCellChoiceEditor(dev.BCC_TYPE_LIST)
        attrchoiceIC = wx.grid.GridCellAttr()
        attrchoiceIC.SetEditor(choiceIC)

        # Set chain number
        for row in range(4):
            self.SetCellSize(row, 0, 1, 2)
            self.SetCellBackgroundColour(row, 0, const.DISP_DEFAULT_COLOR)

        self.SetCellValue(1, 0, "CADD")
        self.SetCellValue(2, 0, "PHY SEND")
        self.SetCellValue(3, 0, "PHY ECHO")

        for row in range(4, const.MAX_DEVICE_NB + 4):
            self.SetCellBackgroundColour(row, 0, const.DISP_DEFAULT_COLOR)
            self.SetCellValue(row, 0, "DEVADD")
            self.SetCellValue(row, 1, str(row-3))

        # Merge top row cells and set chain number
        for col in range(2, const.MAX_CHAIN_NB + 2):
            self.SetCellBackgroundColour(0, col, const.DISP_DEFAULT_COLOR)
            self.SetColSize(col, const.DISP_DEFAULT_COL_WIDTH * 2)
            self.SetCellValue(0, col, "Chain " + str(col - 2))
            #self.SetCellEditor(1, col, choiceCADD)
            self.SetAttr(1, col, attrchoiceCADD)
            attrchoiceCADD.IncRef()
            self.SetCellValue(1, col, str(col-1))
            #self.SetCellEditor(2, col, choicePHY)
            self.SetAttr(2, col, attrchoicePHY)
            attrchoicePHY.IncRef()
            self.SetCellValue(2, col, dev.PHY_TYPE_LIST[-1])
            #self.SetCellEditor(3, col, choicePHY)
            self.SetAttr(3, col, attrchoicePHY)
            attrchoicePHY.IncRef()
            self.SetCellValue(3, col, dev.PHY_TYPE_LIST[-1])
            for row in range(4, const.MAX_DEVICE_NB + 4):
                #self.SetCellEditor(row, col, choiceIC)
                self.SetAttr(row, col, attrchoiceIC)
                attrchoiceIC.IncRef()
                self.SetCellValue(row, col, dev.BCC_TYPE_LIST[0])

        attrchoiceCADD.DecRef()
        attrchoicePHY.DecRef()
        attrchoiceIC.DecRef()

        # Scripts
        self.SetColSize(const.MAX_CHAIN_NB + 2, const.DISP_DEFAULT_COL_WIDTH / 2)
        self.SetColSize(const.MAX_CHAIN_NB + 3, const.DISP_DEFAULT_COL_WIDTH)
        self.SetColSize(const.MAX_CHAIN_NB + 4, const.DISP_SCRIPT_COL_WIDTH)
        self.SetCellSize(0, const.MAX_CHAIN_NB + 2, 4 + const.MAX_DEVICE_NB, 1)
        self.SetCellSize(0, const.MAX_CHAIN_NB + 3, 1, 2)
        self.SetCellValue(0, const.MAX_CHAIN_NB + 3, "Scripts")
        self.SetCellBackgroundColour(0, const.MAX_CHAIN_NB + 3, const.DISP_DEFAULT_COLOR)


        for row in range(1, 1 + const.MAX_DEVICE_TYPE):
            self.SetCellValue(row, const.MAX_CHAIN_NB + 3, dev.DEVICES_LIST[row - 1].DEV_NAME)
            self.SetCellBackgroundColour(row, const.MAX_CHAIN_NB + 3, const.DISP_DEFAULT_COLOR)
            choiceICScript = wx.grid.GridCellChoiceEditor(dev.DEVICES_LIST[row - 1].script_List)
            attrchoiceICScript = wx.grid.GridCellAttr()
            attrchoiceICScript.SetEditor(choiceICScript)
            #self.SetCellEditor(row, const.MAX_CHAIN_NB + 4, choiceICScript)
            self.SetAttr(row, const.MAX_CHAIN_NB + 4, attrchoiceICScript)
            attrchoiceICScript.IncRef()
            attrchoiceICScript.DecRef()
            if len(dev.DEVICES_LIST[row - 1].script_List) > 0:
                self.SetCellValue(row, const.MAX_CHAIN_NB + 4, dev.DEVICES_LIST[row - 1].script_List[0])

        # Hardware
        self.SetCellValue(1 + const.MAX_DEVICE_TYPE, const.MAX_CHAIN_NB + 3, 'HARD')
        self.SetCellBackgroundColour(1 + const.MAX_DEVICE_TYPE, const.MAX_CHAIN_NB + 3, const.DISP_DEFAULT_COLOR)
        choiceHWScript = wx.grid.GridCellChoiceEditor(self.HWscripts)
        attrchoiceHWScript = wx.grid.GridCellAttr()
        attrchoiceHWScript.SetEditor(choiceHWScript)

        #self.SetCellEditor(1 + const.MAX_DEVICE_TYPE, const.MAX_CHAIN_NB + 4, choiceHWScript)
        self.SetAttr(1 + const.MAX_DEVICE_TYPE, const.MAX_CHAIN_NB + 4, attrchoiceHWScript)
        attrchoiceHWScript.IncRef()
        attrchoiceHWScript.DecRef()

        # Wait
        self.SetCellValue(2 + const.MAX_DEVICE_TYPE, const.MAX_CHAIN_NB + 3, 'WAIT_MS')
        self.SetCellBackgroundColour(2 + const.MAX_DEVICE_TYPE, const.MAX_CHAIN_NB + 3, const.DISP_DEFAULT_COLOR)
        self.SetCellValue(2 + const.MAX_DEVICE_TYPE, const.MAX_CHAIN_NB + 4, '0')

        self.SetCellSize(3 + const.MAX_DEVICE_TYPE, const.MAX_CHAIN_NB + 3, 1 + const.MAX_DEVICE_NB - const.MAX_DEVICE_TYPE, 2)
        #time.sleep(0.5)

        self.getSetupMatrix()
        self.getSetupTypesUsed()
        self.getScriptUsed()

        self.unlockGrid()
        self.EndBatch()
        #self.ForceRefresh()

    def getSetupMatrix(self):
        self.BeginBatch()

        # CADD
        for col in range(2, 2 + const.MAX_CHAIN_NB):
            self.matrixSetup[0][col-1] = int(self.GetCellValue(1, col))

        # PHYs
        for row in range(2, 4):
            for col in range(2, 2 + const.MAX_CHAIN_NB):
                self.matrixSetup[row - 1][col - 1] = self.getIndice(dev.PHY_TYPE_LIST, self.GetCellValue(row, col))

        # BCCs
        for row in range(const.DISP_SETUP_GRID_OFFSET, const.DISP_SETUP_GRID_OFFSET + const.MAX_DEVICE_NB):
            self.matrixSetup[row - 1][0] = int(self.GetCellValue(row, 1))   # DEVADD
            for col in range(2, 2 + const.MAX_CHAIN_NB):
                self.matrixSetup[row - 1][col - 1] = self.getIndice(dev.BCC_TYPE_LIST, self.GetCellValue(row, col))

        self.EndBatch()
        #self.ForceRefresh()
        #print(self.matrixSetup)

    def setSetupMatrix(self):
        self.BeginBatch()

        # CADD
        for col in range(2, 2 + const.MAX_CHAIN_NB):
            self.SetCellValue(1, col, str(self.matrixSetup[0][col-1]))

        # PHYs
        print(self.matrixSetup)
        for row in range(2, 4):
            for col in range(2, 2 + const.MAX_CHAIN_NB):
                self.SetCellValue(row, col, dev.PHY_TYPE_LIST[self.matrixSetup[row - 1][col - 1]])

        # BCCs
        for row in range(const.DISP_SETUP_GRID_OFFSET, const.DISP_SETUP_GRID_OFFSET + const.MAX_DEVICE_NB):
            self.SetCellValue(row, 1, str(self.matrixSetup[row - 1][0]))   # DEVADD
            for col in range(2, 2 + const.MAX_CHAIN_NB):
                self.SetCellValue(row, col, dev.BCC_TYPE_LIST[self.matrixSetup[row - 1][col - 1]])

        self.EndBatch()

    def getScriptUsed(self):
        self.BeginBatch()
        self.scriptsUsed = []

        for row in range(1, const.MAX_DEVICE_TYPE + 1):
            self.scriptsUsed.append(self.GetCellValue(row, const.MAX_CHAIN_NB + 4))

        self.HWscriptUsed = self.GetCellValue(const.MAX_DEVICE_TYPE + 1, const.MAX_CHAIN_NB + 4)
        self.wait = int(self.GetCellValue(const.MAX_DEVICE_TYPE + 2, const.MAX_CHAIN_NB + 4))

        self.EndBatch()
        #print(self.scriptsUsed)

    def setScriptUsed(self):
        self.BeginBatch()

        for row in range(1, const.MAX_DEVICE_TYPE + 1):
            self.SetCellValue(row, const.MAX_CHAIN_NB + 4, self.scriptsUsed[row - 1])

        self.SetCellValue(const.MAX_DEVICE_TYPE + 1, const.MAX_CHAIN_NB + 4, self.HWscriptUsed)
        self.SetCellValue(const.MAX_DEVICE_TYPE + 2, const.MAX_CHAIN_NB + 4, str(self.wait))

        self.EndBatch()

    def getSetupTypesUsed(self):
        self.devTypesUsed = []

        for chain in range(const.MAX_CHAIN_NB):
            send = self.matrixSetup[1][chain + 1]

            if send not in (7,8,9):  # Send phy must be not NULL
                if send in (2,3):  # 664 is used
                    self.devTypesUsed.append(0)

                """if (send >= 5) and (send <= 8) and not ((0 in self.devTypesUsed) or (1 in self.devTypesUsed)):  # 665 is used
                    self.devTypesUsed.append(1)"""
                if send in (4,5,6,7) and not ((0 in self.devTypesUsed) or (1 in self.devTypesUsed)):  # 665 is used
                    self.devTypesUsed.append(1)

                echo = self.matrixSetup[2][chain + 1]
                if echo in (2,3):  # 664 is used
                    self.devTypesUsed.append(0)

                if echo in (4,5,6,7):  # 665 is used
                    self.devTypesUsed.append(1)

                for device in range(const.MAX_DEVICE_NB):
                    devType = self.matrixSetup[3 + device][chain + 1]
                    devID = dev.BCC_TYPE_INDEX[devType]
                    if (devType > 0) and not(devID in self.devTypesUsed):
                        self.devTypesUsed.append(devID)

        print(self.devTypesUsed)

    def getIndice(self, tab, value):
        for i in range(len(tab)):
            if tab[i] == value:
                return i
        return None

    def lockGrid(self):
        self.EnableEditing(False)
        self.ForceRefresh()

    def unlockGrid(self):
        self.EnableEditing(True)

        for col in range(2 + const.MAX_CHAIN_NB + 2):
            self.SetReadOnly(0, col)

        for row in range(const.DISP_SETUP_GRID_OFFSET + const.MAX_DEVICE_NB):
            self.SetReadOnly(row, 0)

        for row in range(1, const.MAX_DEVICE_TYPE + 4):
            self.SetReadOnly(row, const.MAX_CHAIN_NB + 3)

        #self.ForceRefresh()

    def killEditors(self):
        self.ClearGrid()
        """for row in range(1, const.DISP_SETUP_GRID_OFFSET + const.MAX_DEVICE_NB):
            for col in range(2, 2 + const.MAX_CHAIN_NB):
                cellEditor = self.GetCellEditor(row, col)
                cellEditor.Destroy()
        for row in range(1, const.MAX_DEVICE_TYPE + 1):
            cellEditor = self.GetCellEditor(row, const.MAX_CHAIN_NB + 4)
            cellEditor.Destroy()"""


class gridGUARD(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.BORDER_DEFAULT) # wx.BORDER_SUNKEN)
        self.parent = parent                                                                    # Grid parent.
        self.grid = False                                                                       # Just a flag to use with create / draw grid methods
        self.fontText = wx.Font(8, wx.MODERN, wx.FONTSTYLE_NORMAL, wx.NORMAL, 0, "Arial")       # Font used for values.
        self.fontHeaders = wx.Font(8, wx.MODERN, wx.FONTSTYLE_ITALIC, wx.NORMAL, 0, "Arial")    # Font used for Headers.
        self.createGrid(const.DISP_PARAMS_NB_MAX + 3, 9)
        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.onCellClicked)

    def onCellClicked(self, event):
        event.GetEventObject().SetGridCursor(event.GetRow(), event.GetCol())
        event.Skip()

    def createGrid(self, nb_row, nb_col):
        self.grid = True
        self.CreateGrid(nb_row, nb_col)  # Create grid.
        self.SetGridLineColour(const.DISP_DEFAULT_COLOR)
        self.HideRowLabels()  # Hide automatic row labels.
        self.HideColLabels()  # Hide automatic column labels.

        self.DisableCellEditControl()
        for i in range(nb_col):
            self.DisableColResize(i)
            self.SetColSize(i, const.DISP_DEFAULT_COL_WIDTH)
        for i in range(nb_row):
            self.DisableRowResize(i)
        self.DisableDragRowSize()
        self.DisableDragGridSize()
        self.DisableKeyboardScrolling()
        self.EnableDragCell(False)
        self.EnableDragColMove(False)
        self.SetSelectionForeground(const.DISP_BLACK_COLOR)
        self.SetCellHighlightPenWidth(0)

        self.SetColSize(0, const.DISP_PARAM_COL_WIDTH)

    def setCellValueFormat(self, row, col, the_format, value):
        if the_format == '{:04X}':
            self.SetCellValue(row, col, the_format.format(int(value)))
        else:
            self.SetCellValue(row, col, the_format.format(value))

    def drawGuardGrid(self, device):
        self.BeginBatch()
        self.ClearGrid()
        self.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

        # Header
        for col in range(9):
            self.SetCellValue(0, col, const.GUARD_HEADER_1[col])
            self.SetCellBackgroundColour(0, col, const.DISP_DEFAULT_COLOR)
            if (col == 4) or (col == 6):
                self.SetCellSize(0, col, 1, 2)
                self.SetCellValue(1, col, const.GUARD_HEADER_2[col-4])
                self.SetCellBackgroundColour(1, col, const.DISP_DEFAULT_COLOR)
            elif (col != 5) and (col != 7):
                self.SetCellSize(0, col, 2, 1)
            else:
                self.SetCellValue(1, col, const.GUARD_HEADER_2[col - 4])
                self.SetCellBackgroundColour(1, col, const.DISP_DEFAULT_COLOR)

        # Params and default values
        choiceStop = wx.grid.GridCellChoiceEditor(const.GUARD_STOP)
        attrchoiceStop = wx.grid.GridCellAttr()
        attrchoiceStop.SetEditor(choiceStop)

        choiceTrigPort = wx.grid.GridCellChoiceEditor(const.GUARD_TRIG_PORT)
        attrchoiceTrigPort = wx.grid.GridCellAttr()
        attrchoiceTrigPort.SetEditor(choiceTrigPort)

        choiceTrigPin = wx.grid.GridCellChoiceEditor(["%d" %i for i in range(0, 31)])
        attrchoiceTrigPin = wx.grid.GridCellAttr()
        attrchoiceTrigPin.SetEditor(choiceTrigPin)

        self.SetCellValue(2, 0, 'TPL')
        self.SetCellBackgroundColour(2, 0, const.DISP_DEFAULT_COLOR)
        #self.SetCellEditor(2, 1, choiceStop)
        self.SetAttr(2, 1, attrchoiceStop)
        attrchoiceStop.IncRef()
        self.SetCellValue(2, 1, const.GUARD_STOP[0])
        #self.SetCellEditor(2, 2, choiceTrigPort)
        self.SetAttr(2, 2, attrchoiceTrigPort)
        attrchoiceTrigPort.IncRef()
        self.SetCellValue(2, 2, const.GUARD_TRIG_PORT[0])
        #self.SetCellEditor(2, 3, choiceTrigPin)
        self.SetAttr(2, 3, attrchoiceTrigPin)
        attrchoiceTrigPin.IncRef()
        self.SetCellValue(2, 3, '0')
        for col in range(4, 9):
            self.SetCellValue(2, col, '-')
        for row in range(3, device.DISP_PARAMS_NB + 3):
            self.SetCellValue(row, 0, device.DISP_PARAMS[row-3][0] + ' [' + device.DISP_PARAMS[row-3][20] + ']')
            self.SetCellBackgroundColour(row, 0, const.DISP_DEFAULT_COLOR)
            #self.SetCellEditor(row, 1, choiceStop)
            self.SetAttr(row, 1, attrchoiceStop)
            attrchoiceStop.IncRef()
            self.SetCellValue(row, 1, const.GUARD_STOP[1])
            #self.SetCellEditor(row, 2, choiceTrigPort)
            self.SetAttr(row, 2, attrchoiceTrigPort)
            attrchoiceTrigPort.IncRef()
            self.SetCellValue(row, 2, const.GUARD_TRIG_PORT[0])
            #self.SetCellEditor(row, 3, choiceTrigPin)
            self.SetAttr(row, 3, attrchoiceTrigPin)
            attrchoiceTrigPin.IncRef()
            self.SetCellValue(row, 3, '0')
            if device.DISP_PARAMS[row-3][20] == 'X': #Digital parameter
                self.SetCellValue(row, 4, 'MASK [X]:')
                self.SetCellBackgroundColour(row, 4, const.DISP_DEFAULT_COLOR)
                self.setCellValueFormat(row, 5, device.DISP_PARAMS[row - 3][14], device.DISP_PARAMS[row - 3][17])
                self.SetCellValue(row, 6, 'MASK [X]:')
                self.SetCellBackgroundColour(row, 6, const.DISP_DEFAULT_COLOR)
                self.setCellValueFormat(row, 7, device.DISP_PARAMS[row - 3][14], device.DISP_PARAMS[row - 3][19])
                self.SetCellValue(row, 8, '-')
            else:
                self.setCellValueFormat(row, 4, device.DISP_PARAMS[row - 3][14], device.DISP_PARAMS[row - 3][16])
                self.SetCellBackgroundColour(row, 4, const.DISP_WHITE_COLOR)
                self.setCellValueFormat(row, 5, device.DISP_PARAMS[row - 3][14], device.DISP_PARAMS[row - 3][17])
                self.setCellValueFormat(row, 6, device.DISP_PARAMS[row - 3][14], device.DISP_PARAMS[row - 3][18])
                self.SetCellBackgroundColour(row, 6, const.DISP_WHITE_COLOR)
                self.setCellValueFormat(row, 7, device.DISP_PARAMS[row - 3][14], device.DISP_PARAMS[row - 3][19])
                if (device.DISP_PARAMS[row - 3][15]) > 0:
                    self.SetCellValue(row, 8, 'Yes')
                else:
                    self.SetCellValue(row, 8, 'No')

        attrchoiceStop.DecRef()
        attrchoiceTrigPort.DecRef()
        attrchoiceTrigPin.DecRef()

        self.updateSizeV(device.DISP_PARAMS_NB)
        self.EndBatch()
        #self.ForceRefresh()
        self.unlockGrid(device)

    def updateSizeV(self, paramNb):
        self.BeginBatch()
        for row in range(2, 3 + paramNb):
            self.ShowRow(row)

        for row in range(3 + paramNb, 2 + const.DISP_PARAMS_NB_MAX + 1):
            self.HideRow(row)
        self.EndBatch()

    def getGuardMatrix(self, device):
        self.BeginBatch()

        matrix = np.zeros((device.DISP_PARAMS_NB + 1, 7), np.float64)

        for row in range(2, device.DISP_PARAMS_NB + 3):
            # TPL fail at last indice
            if row == 2:
                line = device.DISP_PARAMS_NB + 3
            else:
                line = row

            # Stop fail
            val = self.GetCellValue(row, 1)
            if val == 'Yes':
                matrix[line-3][0] = 1

            # Trig port
            val = self.GetCellValue(row, 2)
            if val == 'PTA':
                matrix[line - 3][1] = 1
            if val == 'PTB':
                matrix[line - 3][1] = 2
            if val == 'PTC':
                matrix[line - 3][1] = 3
            if val == 'PTD':
                matrix[line - 3][1] = 4
            if val == 'PTE':
                matrix[line - 3][1] = 5

            # Trig pin
            matrix[line - 3][2] = float(self.GetCellValue(row, 3))

            # Guards (no combobox in this section, need to check if value is float)
            try:
                if row > 2:
                    if device.DISP_PARAMS[row - 3][20] == 'X':
                        for col in range(3, 8):
                            if (col == 6) or (col == 4):
                                matrix[row - 3][col - 1] = 0
                            else:
                                matrix[row - 3][col - 1] = int(self.GetCellValue(row, col), 16) # Convert to hex (base 16)
                    else:
                        for col in range(3, 8):
                            matrix[row - 3][col - 1] = float(self.GetCellValue(row, col))

                        if (matrix[row - 3][4 - 1] > matrix[row - 3][5 - 1]) or (matrix[row - 3][6 - 1] > matrix[row - 3][7 - 1]): # Min value above max value
                            print("Param load error")
                            self.SetCellBackgroundColour(row, 0, const.DISP_RED_COLOR)
                            self.EndBatch()
                            return None

                    self.SetCellBackgroundColour(row, 0, const.DISP_DEFAULT_COLOR)

            except ValueError:
                print("Param load error")
                self.SetCellBackgroundColour(row, 0, const.DISP_RED_COLOR)
                self.EndBatch()
                return None

        self.EndBatch()
        return matrix
        # print(matrix)

    def lockGrid(self):
        self.EnableEditing(False)
        self.ForceRefresh()

    def unlockGrid(self, device):
        self.EnableEditing(True)
        for row in range(0, device.DISP_PARAMS_NB + 3, 1):
            self.SetReadOnly(row, 0)

        for col in range(9):
            self.SetReadOnly(0, col)
            self.SetReadOnly(1, col)

        for col in range(4, 9, 1):
            self.SetReadOnly(2, col)

        for row in range(3, device.DISP_PARAMS_NB + 3, 1):
            self.SetReadOnly(row, 8)
            if device.DISP_PARAMS[row-3][20] == 'X':    # Digital parameter
                self.SetReadOnly(row, 4)
                self.SetReadOnly(row, 6)
            else:
                self.SetReadOnly(row, 4, False)
                self.SetReadOnly(row, 6, False)

        self.ForceRefresh()

    def killEditors(self):
        self.ClearGrid()
        """for row in range(2, self.GetNumberRows()):
            for col in range(1, 4):
                cellEditor = self.GetCellEditor(row, col)
                cellEditor.Destroy()"""