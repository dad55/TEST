"""____________________________________________________

FILENAME: WX_FRAME.py
AUTHOR: Stephane AMANS / Guerric PANIS
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import os
import wx.adv
import wx.aui
import wx.lib.agw.aui
import CONST as const
import WX_WIDGETS as wid
import WX_TABLE as tab
import COM as com
import COM_GENE as com_gene
import DEVICES as dev
import subprocess


class NewDialog(wx.Dialog):
    def __init__(self, parent, id=-1, title="New setup name"):
        wx.Dialog.__init__(self, parent, id, title, size=(350, 190))
        self.CenterOnScreen()

        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        self.mainSizer.AddSpacer(10)
        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.mainSizer.AddSpacer(10)

        self.field = wx.TextCtrl(self, value="", size=(300, 30), id=const.ID_NEW_SETUP_ENTER)
        self.mainSizer.Add(self.field, 0, wx.ALL | wx.CENTER, 8)

        self.okbutton = wx.Button(self, label="OK", id=const.ID_NEW_SETUP_OK)
        self.buttonSizer.Add(self.okbutton, 0, wx.ALL, 8)

        self.cancelbutton = wx.Button(self, label="CANCEL", id=const.ID_NEW_SETUP_NOK)
        self.buttonSizer.Add(self.cancelbutton, 0, wx.ALL, 8)

        self.mainSizer.Add(self.buttonSizer, 0, wx.CENTER, 0)

        self.Bind(wx.EVT_BUTTON, self.onOK, id=const.ID_NEW_SETUP_OK)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=const.ID_NEW_SETUP_NOK)

        self.SetSizer(self.mainSizer)
        self.result = None

    def onOK(self, event):
        event.Skip()
        self.result = self.field.GetValue()
        self.Destroy()

    def onCancel(self, event):
        event.Skip()
        self.result = None
        self.Destroy()


class MainFrame(wx.Frame):
    def __init__(self, parent, thePath, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE|wx.SUNKEN_BORDER):
        wx.Frame.__init__(self, parent, id, 'NXP ' + const.complete_name, pos, size, style)  # Create the main frame.
        self.appPath = thePath  # Save the application path. Returns current working directory of a process
        self.comboBoxFont = wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Segoe UI")  # Predefine a font.
        self.buttonFont = wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Segoe UI")  # Predefine a font.
        #self.refreshValuesTmr = wx.Timer(self)                                          # Implements a timer for UI refresh.

        # Instanciate the AUI manager:
        self._mgr = wx.lib.agw.aui.AuiManager(self, wx.lib.agw.aui.AUI_MGR_DEFAULT)

        self.Bind(wx.EVT_CLOSE, self.onExit)                                # For un-init aui manager before closing

        # Set the main frame parameters:
        titleIcon = wid.MyIcon(self, self.appPath + const.LOGO_APP, const.CST_SizeTitleIcon)
        titleIcon.addIconWindow(self)
        wx.ToolTip.Enable(True)

        self.gridDisp = None
        self.gridDisp = None
        self.gridSetup = None
        self.gridScript = None
        self.gridGuard = []
        self.bat = None
        self.gauge = None

        self.micro = com.ProtocolMicro()
        self.geneCom = com_gene.COM_VISA()
        self.targetMod = 'AM'

        self.logTrig = 'BAT TRIG'
        self.logTrigValue = 5
        self.logTimer = 0   # 0 = not started
        self.setups = []

        self.CenterOnScreen()   # Center the main frame on the screen.
        self.buildWindow()  # Call the function to build the frame window.
        self.Show(True)

        self.scanUarts()
        self.geneCom.scan()
        self.geneTB.SetComboboxList(self.geneCom.available)

        self.handlerComButVar = False
        self.handlerComVar = False
        self.handlerSetupCampaign = False
        self.handlerSetupCampaignType = False
        self.handlerSetupUpdate = False
        self.handlerSetupNew = False
        self.handlerSetupDel = False
        self.handlerSetupSave = False
        self.onExitVar = False

    def buildWindow(self):
        self.SetMinSize(wx.Size(400, 300))

        # COM port
        self.comTB = wid.ToolBar(self, -1)
        self.comTB.AddLabel(-1, "Rev -----", 50)
        self.comTB.AddCombobox(self.comTB, const.ID_COM_TYPE, "SERIAL", "Select COM type", self.handlerCom, const.SIZE_COMBO_COM)
        #self.comTB.SetComboboxList(('SERIAL', 'CAN'))
        self.comTB.SetComboboxList(('SERIAL', ''))
        self.comTB.SetComboboxItem(0)
        self.comTB.AddCombobox(self.comTB, const.ID_COM_LIST, "COM port", "Select COM port", self.handlerCom, const.SIZE_COMBO_COM)
        self.comTB.AddItem(const.ID_UART_UPDATE, self.appPath + const.IMG_update, "Update", const.CST_SizeTBButtonIcon)
        #self.comTB.AddGauge(self.comTB, const.ID_UART_GAUGE)
        self.Bind(wx.EVT_MENU, self.handlerComBut, id=const.ID_UART_UPDATE)
        self.comTB.Realize()

        # Generator
        self.geneTB = wid.ToolBar(self, -1)
        self.geneTB.AddLabel(-1, "GENE", 25)
        self.geneTB.AddCombobox(self.geneTB, const.ID_GENE_TARGET, "TARGET", "Select Last Modulation at Target", self.handlerGene, const.SIZE_COMBO_DEFAULT)
        self.geneTB.SetComboboxList(('TARGET CW', 'TARGET AM',  'TARGET PM'))
        self.geneTB.SetComboboxItem(1)
        self.geneTB.AddCombobox(self.geneTB, const.ID_GENE_COM_TYPE, "GENE", "Select GENE Com Type", self.handlerGene, const.SIZE_COMBO_DEFAULT)
        self.geneTB.SetComboboxList(('RFOFF', 'NO RFOFF'))
        self.geneTB.SetComboboxItem(0)
        self.geneTB.AddCombobox(self.geneTB, const.ID_GENE_ADDR, "GENE ADDR", "Select Gene Address", self.handlerGene, const.SIZE_COMBO_GPIB_ADDR)
        self.geneTB.AddItem(const.ID_GENE_UPDATE, self.appPath + const.IMG_update, "Update", const.CST_SizeTBButtonIcon)
        self.Bind(wx.EVT_MENU, self.handlerGeneBut, id=const.ID_GENE_UPDATE)
        self.comTB.Realize()

        # Setups
        self.setupTB = wid.ToolBar(self, -1)
        self.setupTB.AddLabel(-1, "Setup", 25)
        self.setupTB.AddCombobox(self.setupTB, const.ID_SETUP_CAMPAIGN, "SETUP", "Select setup", self.handlerSetup, const.SIZE_COMBO_SETUP/2)
        self.setupTB.AddCombobox(self.setupTB, const.ID_SETUP_CAMPAIGN_TYPE, "SETUP", "Select setup", self.handlerSetup, const.SIZE_COMBO_SETUP/2)
        self.setupTB.AddCombobox(self.setupTB, const.ID_SETUP_UPDATE, "SETUP", "Select setup", self.handlerSetup, const.SIZE_COMBO_SETUP)
        self.setupTB.AddItem(const.ID_SETUP_NEW, self.appPath + const.IMG_new, "New setup",const.CST_SizeTBButtonIcon)
        self.setupTB.AddItem(const.ID_SETUP_DEL, self.appPath + const.IMG_del, "Delete setup",const.CST_SizeTBButtonIcon)
        self.setupTB.AddItem(const.ID_SETUP_SAVE, self.appPath + const.IMG_save, "Save setup", const.CST_SizeTBButtonIcon)
        self.Bind(wx.EVT_MENU, self.handlerSetup, id=const.ID_SETUP_NEW)
        self.Bind(wx.EVT_MENU, self.handlerSetup, id=const.ID_SETUP_DEL)
        self.Bind(wx.EVT_MENU, self.handlerSetup, id=const.ID_SETUP_SAVE)
        self.setupTB.Realize()

        # Logs
        self.logTB = wid.ToolBar(self, -1)
        self.logTB.AddLabel(-1, "LOG", 20)
        self.logTB.AddCombobox(self.logTB, const.ID_LOG_TRIG, "TARGET", "Select logs trigger method", self.handlerLog, const.SIZE_COMBO_DEFAULT)
        self.logTB.SetComboboxList(('BAT TRIG', 'TIMER TRIG'))
        self.logTB.SetComboboxItem(0)
        self.logTB.AddCombobox(self.logTB, const.ID_LOG_TIMER_VAL, "Timer value", "Select timer value in sec", self.handlerLog, const.SIZE_COMBO_IC_NB)
        timer_list = []
        timer_list.append(str(1))
        timer_list.append(str(2))
        timer_list.append(str(3))
        timer_list.append(str(4))
        for x in range(5, 205, 5):
            timer_list.append(str(x))
        self.logTB.SetComboboxList(timer_list)
        self.logTB.SetComboboxItem(4)
        self.logTB.combobox[-1].Enable(False)
        self.logTB.AddItem(const.ID_LOG_GO, self.appPath + const.IMG_go, "Launch timer", const.CST_SizeTBButtonIcon)
        self.logTB.Realize()

        # Gauge
        self.gauge = wx.Gauge(self, const.ID_UART_GAUGE, pos=wx.DefaultPosition)
        self.gauge.SetRange(const.UART_BUFFER_SIZE)

        # Start-Stop
        self.ctrlTB = wid.ToolBar(self, -1)
        self.ctrlTB.AddLabel(-1, "CTRL", 25)
        self.ctrlTB.AddItem(const.ID_START, self.appPath + const.IMG_start, "Start", const.CST_SizeTBButtonIcon)
        self.ctrlTB.AddItem(const.ID_WAKEUP, self.appPath + const.IMG_wakeup, "Wakeup", const.CST_SizeTBButtonIcon)
        self.ctrlTB.AddItem(const.ID_SLEEP, self.appPath + const.IMG_sleep, "Sleep", const.CST_SizeTBButtonIcon)
        self.ctrlTB.AddItem(const.ID_STOP, self.appPath + const.IMG_stop, "Stop", const.CST_SizeTBButtonIcon)
        self.ctrlTB.Realize()

        # Docs and About
        self.docTB = wid.ToolBar(self, -1)
        self.docTB.AddItem(const.ID_RES, self.appPath + const.IMG_result, "Analyser", const.CST_SizeTBButtonIcon)
        self.docTB.AddItem(const.ID_REPORT, self.appPath + const.IMG_report, "Report", const.CST_SizeTBButtonIcon)
        self.docTB.AddItem(const.ID_DOC, self.appPath + const.IMG_doc, "Doc", const.CST_SizeTBButtonIcon)
        self.docTB.AddItem(const.ID_ABOUT, self.appPath + const.IMG_about, "About", const.CST_SizeTBButtonIcon)
        self.docTB.Bind(wx.EVT_MENU, self.startResult, id=const.ID_RES)
        self.docTB.Bind(wx.EVT_MENU, self.onReport, id=const.ID_REPORT)
        self.docTB.Bind(wx.EVT_MENU, self.onDoc, id=const.ID_DOC)
        self.docTB.Bind(wx.EVT_MENU, self.onAbout, id=const.ID_ABOUT)
        self.docTB.Realize()
        
        # Add panes to the app
        self.logs = wid.MyTextControl(self, "Logs", "Logs view", 1, wx.Size(400, 80), self._mgr)
        self.ntBook = wid.MyNoteBook(self, self.appPath, "noteBook", self._mgr)
        #self.ntBook = wid.MyCustomNotebook(self, self.appPath)
        
        self.gridDisp = tab.gridDISPLAY(self)
        self.ntBook.addSheets('DISPLAY', self.gridDisp)
        
        self.gridSetup = tab.gridSETUP(self)
        self.ntBook.addSheets('APP SETUP', self.gridSetup)
        
        for i in range(const.MAX_DEVICE_TYPE):
            self.gridGuard.append(tab.gridGUARD(self))
            self.ntBook.addSheets('GUARDS ' + str(dev.DEVICES_LIST[i].DEV_NAME), self.gridGuard[i])

        self.ntBook.setSelectedSheet(1)

        # Add the toolbars to the manager
        self._mgr.AddPane(self.comTB, wx.lib.agw.aui.AuiPaneInfo().Name("Communication").Caption("Communication toolbar").ToolbarPane().Top().Row(1).Position(0))
        self._mgr.AddPane(self.geneTB, wx.lib.agw.aui.AuiPaneInfo().Name("Generator").Caption("Generator toolbar").ToolbarPane().Top().Row(1).Position(1))
        self._mgr.AddPane(self.docTB, wx.lib.agw.aui.AuiPaneInfo().Name("About").Caption("About").ToolbarPane().Top().Row(1).Position(2))
        self._mgr.AddPane(self.setupTB, wx.lib.agw.aui.AuiPaneInfo().Name("Setup").Caption("Setup").ToolbarPane().Top().Row(2).Position(0))
        self._mgr.AddPane(self.logTB, wx.lib.agw.aui.AuiPaneInfo().Name("Log").Caption("Log toolbar").ToolbarPane().Top().Row(2).Position(1))
        self._mgr.AddPane(self.gauge, wx.lib.agw.aui.AuiPaneInfo().Name("Gauge").Caption("Gauge").ToolbarPane().Top().Row(2).Position(2))
        self._mgr.AddPane(self.ctrlTB, wx.lib.agw.aui.AuiPaneInfo().Name("Ctrl").Caption("Ctrl").ToolbarPane().Top().Row(2).Position(3))
        self._mgr.Update()      # Update the aui manager.

        # Add tabs
        self.scanScripts()
        self.gridSetup.drawSetupGrid()
        self.gridDisp.drawDispGrid(self.gridSetup.matrixSetup, self.gridSetup.devTypesUsed)
        self.scanCampaign()

        for i in range(const.MAX_DEVICE_TYPE):
            self.gridGuard[i].drawGuardGrid(dev.DEVICES_LIST[i])

    def onReport(self, event):
        try:
            path = self.appPath + '\..\\'
            path = path.replace('/', '\\')
            #print(path)
            subprocess.Popen(r'explorer "%s"' % path)
        except FileNotFoundError:
            self.printLog("CANNOT OPEN DOCS")
        event.Skip()

    def onDoc(self, event):
        try:
            path = self.appPath + const.DOCS_PATH
            path = path.replace('/', '\\')
            #print(path)
            subprocess.Popen(r'explorer "%s"' % path)
        except FileNotFoundError:
            self.printLog("CANNOT OPEN DOCS")
        event.Skip()

    def onAbout(self, event):
        event.Skip()
        aboutInfo = wx.adv.AboutDialogInfo()
        aboutInfo.SetName('NXP ' + const.program_name)
        aboutInfo.SetVersion('V' + const.version)
        aboutInfo.SetDescription("NXP Python interface for BCC EMC, ISO pulses and general application testing")
        aboutInfo.SetWebSite("https://www.collabnet.nxp.com/svn/aaa_bms_lab_cz_tools/trunk/6_QPHY/1_Dev/1_Software/1_EMC_GUI/1_Release")
        aboutInfo.AddDeveloper("Guerric PANIS")
        aboutInfo.AddDeveloper("David SCLAFER")
        wx.adv.AboutBox(aboutInfo)

    def startResult(self, event):
        try:
            #print(self.appPath + const.ANALYSER_PATH)
            subprocess.Popen([self.appPath + const.ANALYSER_PATH,  'result'])
        except FileNotFoundError:
            self.printLog("ANALYSER LAUNCH FAILED")
            self.printLog("CHECK ANALYSER SETUP")
        event.Skip()

    def save_context(self):
        path = self.appPath + const.CONTEXT_PATH + 'CONTEXT.txt'
        print(path)
        self.setupTB.combobox[0].GetValue()

    def freezePane(self):
        self.comTB.Enable(False)
        self.geneTB.Enable(False)
        self.setupTB.Enable(False)
        self.docTB.Enable(False)

    def unFreezePane(self):
        self.comTB.Enable(True)
        self.geneTB.Enable(True)
        self.setupTB.Enable(True)
        self.docTB.Enable(True)

    def scanUarts(self):
        if self.comTB.combobox[0].GetValue() == 'SERIAL':
            self.micro.uart.scan()
            self.comTB.SetComboboxList([str(el) for el in self.micro.uart.available])
            self.comTB.combobox[-1].SetBackgroundColour(const.DISP_WHITE_COLOR)
            self.comTB.FindToolByIndex(0).SetLabel('Rev -----')
            self.comTB.Realize()

    def scanScripts(self):
        for i in range(const.MAX_DEVICE_TYPE):
            path = self.appPath + const.SCRIPT_PATH + dev.DEVICES_LIST[i].DEV_NAME
            #print("Scanning " + str(path))
            dev.DEVICES_LIST[i].script_List = []
            for dir in os.listdir(path):
                dev.DEVICES_LIST[i].script_List.append(dir)

            # Hardware scripts
            self.gridSetup.HWscripts = []
            path = self.appPath + const.SCRIPT_PATH + const.HW_PATH
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(".txt"):
                        self.gridSetup.HWscripts.append(file.split('.')[0])

    def scanCampaign(self):
        self.setups = []
        path = self.appPath + const.SETUP_PATH
        #print("Scanning " + str(path))
        campaignList = []
        for dir in os.listdir(path):
            campaignList.append(dir)

        self.setupTB.SetComboboxListID(0, campaignList)
        if len(campaignList) > 0:
            self.setupTB.combobox[0].Select(0)

        self.scanCampaignType()

    def scanCampaignType(self):
        self.setups = []
        path = self.appPath + const.SETUP_PATH + self.setupTB.combobox[0].GetValue() + '/'
        print("Scanning " + str(path))
        campaignTypeList = []
        for dir in os.listdir(path):
            campaignTypeList.append(dir)

        self.setupTB.SetComboboxListID(1, campaignTypeList)
        if len(campaignTypeList) > 0:
            self.setupTB.combobox[1].Select(0)

        self.scanSetups()

    def scanSetups(self):
        self.setups = []
        path = self.appPath + const.SETUP_PATH + self.setupTB.combobox[0].GetValue() + '/' + self.setupTB.combobox[1].GetValue()
        #path = os.path.join((os.environ['USERPROFILE']), 'Documents') + '\\' + const.FOLDER_NAME + const.SETUP_PATH
        print("Scanning " + str(path))
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".txt"):
                    self.setups.append(file.split('.')[0])

        self.setupTB.SetComboboxListID(2, self.setups)
        if len(self.setups) > 0:
            self.setupTB.combobox[2].Select(0)
            path = self.appPath + const.SETUP_PATH + self.setupTB.combobox[0].GetValue() + '/' + self.setupTB.combobox[1].GetValue() + '/' + self.setupTB.combobox[2].GetValue() + '.txt'
            print(path)
            self.readSetup(path)

    def handlerComBut(self, event):
        event.Skip()
        id = event.GetId()
        if id == const.ID_UART_UPDATE:
            self.scanUarts() # Bug if not in interrupt handler
            #self.handlerComButVar = True

    def handlerCom(self, event):
        event.Skip()
        id = event.GetId()
        if id == const.ID_COM_LIST:
            self.handlerComVar = True
        elif id == const.ID_COM_TYPE:
            if self.comTB.combobox[0].GetValue() == 'SERIAL':
                print('SERIAL')
                self.comTB.combobox[-1].SetBackgroundColour(const.DISP_WHITE_COLOR)
                self.scanUarts()
                self.micro.interface = const.UART_INTERFACE
            elif self.comTB.combobox[0].GetValue() == 'CAN':
                print('CAN')
                self.comTB.combobox[-1].SetBackgroundColour(const.DISP_WHITE_COLOR)
                self.comTB.SetComboboxList(('CHAN1', 'CHAN2'))
                self.comTB.SetComboboxItem(0)
                self.micro.interface = const.CAN_INTERFACE
                self.micro.can.channel = 0
                self.handlerComVar = True

    def handlerGeneBut(self, event):
        event.Skip()
        id = event.GetId()
        if (id == const.ID_GENE_UPDATE) and (self.geneTB.combobox[1].GetValue() == 'RFOFF'):
            print('GPIB scan')
            self.geneCom.scan()
            self.geneTB.SetComboboxList(self.geneCom.available)
            self.geneTB.combobox[-1].SetBackgroundColour(const.DISP_WHITE_COLOR)

    def handlerGene(self, event):
        event.Skip()
        id = event.GetId()
        if id == const.ID_GENE_TARGET:
            self.targetMod = self.geneTB.combobox[0].GetValue()[-2:]
            print('Gene target:' + self.targetMod + ".")

        elif id == const.ID_GENE_COM_TYPE:
            choice = self.geneTB.combobox[1].GetValue()
            self.geneTB.combobox[-1].SetBackgroundColour(const.DISP_WHITE_COLOR)
            self.geneCom.opened = False
            if choice == 'NO RFOFF':
                self.geneTB.combobox[-1].Enable(False)
            elif choice == 'RFOFF':
                self.geneTB.combobox[-1].Enable(True)
                self.geneCom.scan()
                self.geneTB.SetComboboxList(self.geneCom.available)

        elif id == const.ID_GENE_ADDR:
            self.geneCom.selectedAddr = self.geneTB.combobox[-1].GetValue()
            self.geneCom.open(self.geneCom.selectedAddr)
            if self.geneCom.opened:
                self.geneTB.combobox[-1].SetBackgroundColour(const.DISP_GREEN_COLOR)
                print('Gene addr opened: ' + self.geneCom.selectedAddr)
                self.geneCom.opened = True
            else:
                self.geneTB.combobox[-1].SetBackgroundColour(const.DISP_RED_COLOR)
                print('Cannot open addr: ' + self.geneCom.selectedAddr)
                self.geneCom.opened = False

    def handlerSetup(self, event):
        event.Skip()
        id = event.GetId()

        if id == const.ID_SETUP_CAMPAIGN:
            self.handlerSetupCampaign = True

        elif id == const.ID_SETUP_CAMPAIGN_TYPE:
            self.handlerSetupCampaignType = True

        elif id == const.ID_SETUP_UPDATE:
            self.handlerSetupUpdate = True

        elif id == const.ID_SETUP_NEW:
            dlg = NewDialog(self)
            dlg.ShowModal()
            if dlg.result is not None:
                campaign = self.setupTB.combobox[0].GetValue()
                campaignType = self.setupTB.combobox[1].GetValue()
                path = self.appPath + const.SETUP_PATH + campaign + '/' + campaignType + '/' + dlg.result + '.txt'
                self.writeSetup(path)
                print('Setup ' + dlg.result + ' created')
            dlg.Destroy()
            self.handlerSetupNew = True

        elif id == const.ID_SETUP_DEL:
            self.handlerSetupDel = True

        elif id == const.ID_SETUP_SAVE:
            self.handlerSetupSave = True

    def handlerLog(self, event):
        event.Skip()
        id = event.GetId()
        if id == const.ID_LOG_TRIG:
            self.logTrig = self.logTB.combobox[0].GetValue()
            print('Log: ' + self.logTrig)

            if self.logTrig =='BAT TRIG':
                self.logTB.combobox[-1].Enable(False)
            elif self.logTrig =='TIMER TRIG':
                self.logTB.combobox[-1].Enable(True)

        elif id == const.ID_LOG_TIMER_VAL:
            self.logTrigValue = int(self.logTB.combobox[1].GetValue())
            print('Log value: ' + str(self.logTrigValue))

    def handlerUpdate(self):
        if self.handlerComButVar:
            self.scanUarts()
            self.handlerComButVar = False
            self._mgr.Update()

        if self.handlerComVar:
            if self.comTB.combobox[0].GetValue() == 'SERIAL':
                #if self.micro.uart.myComFTD is not None:
                if self.micro.uart.uart_com is not None:
                    if self.micro.uart.ready: #self.micro.uart.myComFTD.is_open:
                        self.micro.uart.close() #.myComFTD.close()
                        self.comTB.combobox[-1].SetBackgroundColour(const.DISP_WHITE_COLOR)
                        self.comTB.FindToolByIndex(0).SetLabel('Rev -----')
                        self.comTB.Realize()

                self.micro.uart.selectedAddr = self.comTB.combobox[-1].GetValue()
                print('Selected: ' + self.micro.uart.selectedAddr)
                self.micro.uart.open()
                if self.micro.uart.ready and True:#self.micro.uart.uart_com.is_open:
                    # Read revision to be done
                    self.micro.clear_buffers()
                    self.micro.readRev()

                    if self.micro.rev > 0:
                        self.comTB.FindToolByIndex(0).SetLabel('Rev ' + '{:4}'.format(self.micro.rev))
                        self.comTB.combobox[-1].SetBackgroundColour(const.DISP_GREEN_COLOR)
                    else:
                        self.comTB.FindToolByIndex(0).SetLabel('Rev -----')
                        self.comTB.combobox[-1].SetBackgroundColour(const.DISP_ORANGE_COLOR)

                    self.comTB.Realize()
                else:
                    self.comTB.combobox[-1].SetBackgroundColour(const.DISP_ORANGE_COLOR)
                    self.comTB.Realize()

            elif self.comTB.combobox[0].GetValue() == 'CAN':
                if self.comTB.combobox[-1].GetValue() == 'CHAN1':
                    self.micro.can.channel = 0
                    self.micro.can.open()
                elif self.comTB.combobox[-1].GetValue() == 'CHAN2':
                    self.micro.can.channel = 1
                    self.micro.can.open()

                self.micro.clear_buffers()
                self.micro.readRev()

                if self.micro.rev > 0:
                    self.comTB.FindToolByIndex(0).SetLabel('Rev ' + '{:4}'.format(self.micro.rev))
                    self.comTB.combobox[-1].SetBackgroundColour(const.DISP_GREEN_COLOR)
                else:
                    self.comTB.FindToolByIndex(0).SetLabel('Rev -----')
                    self.comTB.combobox[-1].SetBackgroundColour(const.DISP_ORANGE_COLOR)

                self.comTB.Realize()
            self.handlerComVar = False
            self._mgr.Update()

        if self.handlerSetupCampaign:
            self.scanCampaignType()
            self.handlerSetupCampaign = False
            self._mgr.Update()

        if self.handlerSetupCampaignType:
            self.scanSetups()
            self.handlerSetupCampaignType = False
            self._mgr.Update()

        if self.handlerSetupUpdate:
            campaign = self.setupTB.combobox[0].GetValue()
            campaignType = self.setupTB.combobox[1].GetValue()
            file = self.setupTB.combobox[2].GetValue()
            #print('file: ' + str(file))
            if len(file) > 0:
                path = self.appPath + const.SETUP_PATH + campaign + '/' + campaignType + '/' + file + '.txt'
                #path = os.path.join((os.environ['USERPROFILE']), 'Documents') + '\\' + const.FOLDER_NAME + const.SETUP_PATH + file + '.txt'
                print(str(path))
                self.readSetup(path)
                print('Updating to setup ' + str(file))
            self.handlerSetupUpdate = False
            self._mgr.Update()

        elif self.handlerSetupNew:
            self.scanSetups()
            self.handlerSetupNew = False
            self._mgr.Update()

        elif self.handlerSetupDel:
            campaign = self.setupTB.combobox[0].GetValue()
            campaignType = self.setupTB.combobox[1].GetValue()
            file = self.setupTB.combobox[2].GetValue()
            if len(file) > 0:
                dlg = wx.MessageDialog(None, "Do you really want to delete " + str(file) + " ?", 'Delete setup', wx.YES_NO | wx.ICON_QUESTION)
                result = dlg.ShowModal()
                dlg.Destroy()
                if result == wx.ID_YES:
                    path = self.appPath + const.SETUP_PATH + campaign + '/' + campaignType + '/' + file + '.txt'
                    #path = os.path.join((os.environ['USERPROFILE']), 'Documents') + '\\' + const.FOLDER_NAME + const.SETUP_PATH + file + '.txt'
                    try:
                        os.remove(path)
                    except FileNotFoundError:
                        print("File not found: " + str(path))

                    print("Deleting " + str(path))
                    self.scanSetups()
                    file = self.setupTB.combobox[2].GetValue()
                    if len(file) > 0:
                        path = self.appPath + const.SETUP_PATH + campaign + '/' + campaignType + '/' + file + '.txt'
                        #path = os.path.join((os.environ['USERPROFILE']), 'Documents') + '\\' + const.FOLDER_NAME + const.SETUP_PATH + file + '.txt'
                        self.readSetup(path)
                        print('Updating to setup ' + str(file))
            self.handlerSetupDel = False
            self._mgr.Update()

        elif self.handlerSetupSave:
            campaign = self.setupTB.combobox[0].GetValue()
            campaignType = self.setupTB.combobox[1].GetValue()
            file = self.setupTB.combobox[2].GetValue()
            if len(file) > 0:
                path = self.appPath + const.SETUP_PATH + campaign + '/' + campaignType + '/' + file + '.txt'
                #path = os.path.join((os.environ['USERPROFILE']), 'Documents') + '\\' + const.FOLDER_NAME + const.SETUP_PATH + file + '.txt'
                self.writeSetup(path)
                print('Setup saved in ' + str(file))
                self.handlerSetupSave = False
            self._mgr.Update()

        if self.gridSetup.dispChanged:
            self.gridDisp.drawDispGrid(self.gridSetup.matrixSetup, self.gridSetup.devTypesUsed)
            self.gridSetup.dispChanged = False
            self._mgr.Update()

        if self.onExitVar:
            for grid in self.gridGuard:
                grid.killEditors()
            self.gridSetup.killEditors()

            self.geneCom.close()
            if self.bat is not None:
                self.bat.close()
            self._mgr.UnInit()
            self.onExitVar = False

    def writeSetup(self, path):
        file = open(path, 'w+')
        # Scripts
        line = ''

        for col in range(const.MAX_DEVICE_TYPE):
            line += str(self.gridSetup.scriptsUsed[col]) + const.CSV_SEPARATOR
        line += str(self.gridSetup.HWscriptUsed) + const.CSV_SEPARATOR
        line += str(self.gridSetup.wait) + const.CSV_SEPARATOR
        line += '\n'
        file.write(line)

        # Matrix setup
        for row in range(const.DISP_SETUP_GRID_OFFSET - 1 + const.MAX_DEVICE_NB):
            line = ''
            for col in range(const.MAX_CHAIN_NB + 1):
                line += str(self.gridSetup.matrixSetup[row, col]) + const.CSV_SEPARATOR

            line += '\n'
            file.write(line)

        file.close()

    def readSetup(self, path):
        try:
            file = open(path, 'r')
            data = file.readlines()
            length = len(data)

            # Scripts
            if length > 0:
                self.gridSetup.scriptsUsed = data[0].split(const.CSV_SEPARATOR)[:-3]
                self.gridSetup.HWscriptUsed = data[0].split(const.CSV_SEPARATOR)[-3]
                self.gridSetup.wait = int(data[0].split(const.CSV_SEPARATOR)[-2])
                data = data[1:]
                #data = int(data)
                #print(self.scriptsUsed)

            # Matrix setup
            for row in range(const.DISP_SETUP_GRID_OFFSET - 1 + const.MAX_DEVICE_NB):
                if row < (length - 1):
                    line = data[row].split(const.CSV_SEPARATOR)[:-1]
                    for col in range(const.MAX_CHAIN_NB + 1):
                        self.gridSetup.matrixSetup[row][col] = int(line[col])

            self.gridSetup.setSetupMatrix()
            self.gridSetup.setScriptUsed()
            self.gridSetup.getSetupTypesUsed()
            self.gridDisp.drawDispGrid(self.gridSetup.matrixSetup, self.gridSetup.devTypesUsed)

            file.close()
        except FileNotFoundError:
            print('File not found')
            self.scanSetups()
            campaign = self.setupTB.combobox[0].GetValue()
            campaignType = self.setupTB.combobox[1].GetValue()
            file = self.setupTB.combobox[2].GetValue()
            if len(file) > 0:
                path = self.appPath + const.SETUP_PATH + campaign + '/' + campaignType + '/' + file + '.txt'
                #path = os.path.join((os.environ['USERPROFILE']), 'Documents') + '\\' + const.FOLDER_NAME + const.SETUP_PATH + file + '.txt'
                self.readSetup(path)
                print('Updating to setup ' + str(file))

    def printLog(self, text):
        self.logs.AppendText(text + '\n')

    def clearLog(self):
        self.logs.clearText()
        self.Refresh()

    def onExit(self, event):
        self.onExitVar = True
        event.Skip()
