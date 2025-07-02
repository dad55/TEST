"""____________________________________________________

FILENAME: COM_GENE.py
AUTHOR: Guerric PANIS
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import pyvisa

class COM_VISA(pyvisa.ResourceManager):

    def __init__(self):
        pyvisa.ResourceManager.__init__(self)
        self.available = []
        self.selectedAddr = ''
        self.instrument = None
        self.opened = False

    def scan(self):
        self.available = self.list_resources(query='TCPIP?*::INSTR')
        self.available = self.available + self.list_resources(query='GPIB?*::INSTR')

    def open(self, com):
        try:
            self.instrument = self.open_resource(com)
            self.opened = True
        except pyvisa.errors.VisaIOError:
            self.opened = False

    def writeStr(self, data):
        if self.instrument != None:
            self.instrument.write(data)
