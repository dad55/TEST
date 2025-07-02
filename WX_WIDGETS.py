"""____________________________________________________

FILENAME: WX_WIDGETS.py
AUTHOR: Stephane AMANS / Guerric PANIS
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import CONST as const
import os
import wx.aui
import wx.lib.agw.aui
from wx import DefaultSize
import wx.html

class ToolBar(wx.lib.agw.aui.AuiToolBar):

    def __init__(self, parent, tool_id, pos = wx.DefaultPosition, size = DefaultSize, style = wx.lib.agw.aui.AUI_TB_PLAIN_BACKGROUND):
        wx.lib.agw.aui.AuiToolBar.__init__(self, parent, tool_id, pos, size, style)
        self.parent = parent
        self.combobox = []
        self.textctrl = None
        self.gauge = None
        self.menu = None
        self.checkBoxes = []

    def AddItem(self, tool_id, icon, label, size, pos = wx.DefaultPosition):
        # Size the image to convert into button icon:
        image = wx.Image(icon, wx.BITMAP_TYPE_ANY)              # Create an image from any format
        image = image.Scale(size.width, size.height, wx.IMAGE_QUALITY_HIGH)      # Resize the image.
        sizedIcon = image.ConvertToBitmap()                     # Convert the icon into bitmap.
        #self.AddTool(tool_id, label, sizedIcon, label)          # Add the item to the toolbar.
        self.AddTool(tool_id, label, sizedIcon, wx.NullBitmap, wx.lib.agw.aui.ITEM_NORMAL)
        #button=wx.BitmapButton(self, bitmap=sizedIcon)
        #self.AddTool(tool_id, label, button, label)  # Add the item to the toolbar.

    def AddCombobox(self, myParent, tool_id, label, tooltip, callbackFunc, width = 100):
        self.comboSize = wx.Size(width, wx.DefaultSize[1])                              # Create the size objetc with specific width.
        self.combobox.append(wx.ComboBox(myParent, tool_id, label, size = self.comboSize))     # Create the combobox with specific size.
        self.combobox[-1].SetFont(self.parent.comboBoxFont)
        self.combobox[-1].SetToolTip(tooltip) # Set a tooltip help.
        if callbackFunc != None:
            self.combobox[-1].Bind(wx.EVT_COMBOBOX, callbackFunc)
        self.AddControl(self.combobox[-1], label)                                           # Add combobox to the toolbar.

    def SetComboboxList(self, list):
        self.combobox[-1].SetItems(list)
        #self.combobox.Append(list)  # Adding the elements to the CB.

    def SetComboboxListID(self, indice, list):
        self.combobox[indice].SetItems(list)

    def SetComboboxItem(self, item):
        self.combobox[-1].Select(item)

    def changeBtnBitmap(self, tool_id, icon):
        image = wx.Image(icon, wx.BITMAP_TYPE_ANY)              # Create an image from any format
        image = image.Scale(16, 16, wx.IMAGE_QUALITY_HIGH)      # Resize the image.
        sizedIcon = image.ConvertToBitmap()                     # Convert the icon into bitmap.
        self.SetToolBitmap(tool_id, sizedIcon)

    def addTextCtrl(self, myParent, tool_id, label, tooltip, size=100):
        self.textSize = wx.Size(size, wx.DefaultSize[1])  # Create the size object with specific width.
        self.textctrl = wx.TextCtrl(myParent, tool_id, label, size=self.textSize)  # Create the text control with specific size.
        self.textctrl.SetFont(self.parent.comboBoxFont)
        self.textctrl.SetToolTip(tooltip)  # Set a tooltip help.
        self.AddControl(self.textctrl, label)  # Add the text control to the toolbar.
        return self.textctrl  # Return the text control reference.

    def AddGauge(self, myParent, tool_id, size=100):
        self.gaugeSize = wx.Size(size, wx.DefaultSize[1])
        self.gauge = wx.Gauge(myParent, tool_id, pos = wx.DefaultPosition, size=self.gaugeSize)
        return self.gauge

    def AddCheckBox(self, myParent, tool_id, label, size):
        self.checkBoxes.append(wx.CheckBox(myParent, tool_id, label, wx.DefaultPosition, size=size))  # Create the combobox with specific size.
        self.checkBoxes[-1].SetFont(wx.Font(3, wx.MODERN, wx.NORMAL, wx.NORMAL, 0, "Segoe UI") )
        self.AddControl(self.checkBoxes[-1], label)
        #return self.checkBoxes[-1]

class MyTextControl(wx.TextCtrl):
    def __init__(self, parent, name, caption,  position, size, mgr=None):
        pos = wx.DefaultPosition
        wx.TextCtrl.__init__(self, parent, -1, "", pos, size, style=wx.TE_READONLY | wx.TE_MULTILINE)
        self._mgr = mgr
        self.paneInfo = wx.lib.agw.aui.AuiPaneInfo()            # Create the pane infos.
        self.mousePos = None                            # Variable used to store the mouse position.

        self.paneInfo.Name(name)                        # Name the pane.
        self.paneInfo.Caption(caption)                  # Caption of the pane.

        self.paneInfo.Right()                           # The panes are on the right side of the app.
        self.paneInfo.Layer(position)                   # Specify the pane position.       
        self.paneInfo.MaximizeButton(True)              # Display the maximize button on the window.
        self.paneInfo.CloseButton(False)

        self._mgr.AddPane(self, self.paneInfo)          # Add the pane.
    
    def clearLog(self, event):
        event.Skip()
        self.Clear()

    def onSize(self, event):
        self.Refresh()                              # Refresh the panel

    def setSize(self, size):                        # Set size of text ctrl
        self.SetMinSize(size)
        self.Layout()

    def appendText(self, text):                     # Append text into text ctrl
        self.WriteText(text)

    def clearText(self):                            # Clear the text control content.
        #print('lines: ' + str(self.GetNumberOfLines()))
        self.SetValue('')

class MyIcon():
    def __init__(self, parent, bitmap, size):
        self.icon = wx.Icon()
        self.icon.CopyFromBitmap(wx.Bitmap(bitmap, wx.BITMAP_TYPE_ANY))
        self.icon.SetWidth(size[0])
        self.icon.SetHeight(size[1])
        #parent.SetIcon(self.icon)

    def addIconWindow(self, win):
        win.SetIcon(self.icon)
        
    def getIcon(self):
        return self.icon


class MyCustomNotebook(wx.lib.agw.aui.AuiNotebook):
    def __init__(self, parent, path):
        self.path = path
        #self.appInfo = appInfo
        
        self._nbStyle = (wx.lib.agw.aui.AUI_NB_DEFAULT_STYLE)                                       # Set up default notebook style
        self._nbStyle &= ~(wx.lib.agw.aui.AUI_NB_CLOSE_ON_ACTIVE_TAB)                               # Remove close button on sheets.
        wx.lib.agw.aui.AuiNotebook.__init__(self, parent, id=const.ID_NOTEBOOK, pos=wx.DefaultPosition, size=wx.Size(430, 200), agwStyle = self._nbStyle)

        # Create and size welcome page sheet's icon
        #self.imgWP = wx.Image(self.path + const.IMG_Company_Logo, wx.BITMAP_TYPE_PNG).Rescale(16, 16)
        #self.imgWP = self.imgWP.ConvertToBitmap()

        #self.SetSelection(0)
        self.sheets = []

    def addSheets(self, name, object):
        self.sheets.append(object)
        self.AddPage(self.sheets[len(self.sheets)-1], name, True)  # Add the grid to a new page.

    def removeSheet(self, index):
        self.RemovePage(index)

    def deleteSheet(self, index):
        self.DeletePage(index)

    def setSelectedSheet(self, index):
        self.SetSelection(index)

    def getSelectedSheet(self):
        return self.GetPageIndex(self.GetCurrentPage())

class MyNoteBook(MyCustomNotebook):
    def __init__(self, parent, path, name, mgr=None, refWin = None):
        MyCustomNotebook.__init__(self, parent, path)

        self.___mgr = mgr
        self.noteParent = parent
        self.paneInfo = wx.lib.agw.aui.AuiPaneInfo()        # Create the pane infos.
        
        # Names:
        self.paneInfo.Name(name)                    # Name the pane.

        # Position:
        self.paneInfo.Left()                        # The panes are on the right side of the app.
        self.paneInfo.CenterPane()                  # Specify the pane position.       
        self.paneInfo.MaximizeButton(True)          # Display the maximize button on the window.
        self.paneInfo.CloseButton(False)            # Dislays the close button on the window.
        
        self.___mgr.AddPane(self, self.paneInfo)      # Add the pane.