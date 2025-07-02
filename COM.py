"""____________________________________________________

FILENAME: COM.py
AUTHOR: David SCLAFER / Guerric PANIS
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import serial.tools.list_ports
import serial
import can
import can.interfaces.canalystii as canalyst
import time
import CONST as const
import DEVICES as dev

### from comFT232H import SerialCOM

class SerialCOM():
    def __init__(self):
        self.uart_com = None
        self.ready = False
        self.available = []
        self.selectedAddr = ''

    def scan(self):
        # Produce a list of all serial ports. The list contains a tuple with the port number, description and hardware addre
        available = []
        ports = list(serial.tools.list_ports.comports())

        self.available = [] # Clear array
        self.close()        # Close port if open

        # return the ports if 'OpenSDA' is in the description
        for available_ports in ports:
            available_ports = list(tuple([available_ports]))
            for port_no, description, address in available_ports:
                self.available.append(port_no)

        print(self.available)

    def open(self):
        try:
            self.uart_com = serial.Serial(port=self.selectedAddr, baudrate=const.UART_BAUDRATE, timeout=1)
            self.uart_com.set_buffer_size(const.UART_BUFFER_SIZE)
            self.ready = True
        except IOError:
            print("port already open !")
            self.ready = False

    def close(self):
        if self.uart_com is not None:
            if self.uart_com.is_open:
                self.uart_com.close()
                self.ready = False

    def send(self, data):
        if self.uart_com.is_open and self.ready:
            self.ready = False
            try:
                self.uart_com.write(data)
            except serial.serialutil.SerialException:
                print("Serial send error")
            self.ready = True
        else:
            print('impossible to send data')

    def clearSendBuffer(self):
        if self.uart_com is not None:
            if self.uart_com.is_open:
                self.uart_com.reset_output_buffer()

    def clearReadBuffer(self):
        if self.uart_com is not None:
            if self.uart_com.is_open:
                self.uart_com.reset_input_buffer()


class CANCOM():
    def __init__(self):
        self.can_com = None
        self.ready = False
        self.channel = 0
        self.available = []

    def open(self):
        self.can_com = canalyst.CANalystIIBus(channel=self.channel, device=0, baud=1000000)
        self.ready = True
        return True

    def close(self):
        if self.can_com is not None:
            self.can_com.shutdown()
            self.ready = False

    def send(self, data):
        if self.ready:
            self.ready = False
            msg = can.Message(arbitration_id=0x18800000, data=data)
            self.can_com.send(msg)
            self.ready = True
        else:
            print('Impossible to send data')

    def clearSendBuffer(self):
        if self.can_com is not None:
            self.can_com.flush_tx_buffer()

    def clearReadBuffer(self):
        if self.can_com is not None:
            recv = self.can_com._recv_internal(timeout=0.0001)[0]
            while recv is not None:  # Read all frames received
                recv = self.can_com._recv_internal(timeout=0.0001)[0]


class ProtocolMicro():
    def __init__(self):
        self.lenByID = {}
        self.updatelenByID()
        self.rev = 0

        self.interface = const.UART_INTERFACE
        self.uart = SerialCOM()
        self.can = CANCOM()
        self.cptSuccess = 0
        self.cptFail = 0

        self.buffer = b''

        self.SOF_detected = False
        self.correct_ID_detected = False
        self.statusRCV = 0  # 0 : Waiting receive header / 1 : waiting receive data until }
        self.sizePayload = 0
        self.currentRC = ''
        self.errorFrame = False
        self.errorTimeout = False
        self.lastCMDReceived = []
        self.endLoopFlag = False

        self.scriptLine = 0 # For display script line if error
        self.currentScript = ""
        self.fileScript = None

    def updatelenByID(self):
        # Create a synthetic table of PRODUCT_PARAMS ( RC | App resp(x2) + Len | Stat_disp | Data disp )
        limited_params = []
        limited_params.append((0, 0, 0, 0)) # Add id 0 command
        limited_params.append((dev.SCRIPT_FLAG_RC, 0, 0, 0))  # Add En loop ID command
        for device in dev.DEVICES_LIST:
            for i in device.SCRIPT_FRAMES:
                limited_params.append((i[0] + device.RC_OFFSET, 2*(i[1]) + i[2], i[3], i[4]))

        limited_params = list(set(limited_params))
        for i in limited_params:
            self.lenByID[i[0]] = (i[1], i[2], i[3])
        #print(self.lenByID)


    def clearCpt(self):
        self.cptFail = 0
        self.cptSuccess = 0

    def fillBuffer(self):
        if self.interface == const.UART_INTERFACE:
            try:
                #self.buffer += self.uart.myComFTD.read(self.uart.in_waiting())
                self.buffer += self.uart.uart_com.read(self.uart.uart_com.in_waiting)
            except serial.serialutil.SerialException:
                #except:
                print("Serial read error")
            #print(self.buffer)

        elif self.interface == const.CAN_INTERFACE:
            recv = self.can.can_com._recv_internal(timeout=0.0001)[0]
            while recv is not None:  # Read all frames received
                self.buffer += recv.data[0:recv.dlc]
                recv = self.can.can_com._recv_internal(timeout=0.0001)[0]

    def readBuffer(self, size):
        if len(self.buffer) >= size:
            ret = self.buffer[:size]
            self.buffer = self.buffer[size:]
            return ret
        return None

    def sizeBuff(self):
        if self.interface == const.UART_INTERFACE:
            return len(self.buffer) + self.uart.uart_com.in_waiting
        elif self.interface == const.CAN_INTERFACE:
            return len(self.buffer)

    def clear_buffers(self):
        self.buffer = b''
        #self.uart.uart_com.read(self.uart.uart_com.in_waiting)
        self.uart.clearReadBuffer()
        self.uart.clearSendBuffer()
        self.can.clearReadBuffer()
        self.can.clearSendBuffer()

    def readCommand(self, size):
        trame = []
        if size > 0:
            SOF_detected = False
            time0 = time.time()

            while not SOF_detected and (time.time() - time0 < const.MAX_COM_TIMEOUT): #detect '{'
                if len(self.buffer) > 0 and not SOF_detected:
                    SOF_detected = (self.readBuffer(1) == b'{')
                else:
                    self.fillBuffer()
                    time.sleep(0.0001)

            while SOF_detected and (len(self.buffer) < size-1) and (time.time() - time0 < const.MAX_COM_TIMEOUT): #wait full trame received
                self.fillBuffer()
                time.sleep(0.0001)
            if (len(self.buffer) >= (size-1)) and SOF_detected and ((time.time() - time0) < const.MAX_COM_TIMEOUT):
                trame = self.readBuffer(size-1)
                if trame[-1] == ord('}'):   # Framing OK
                    self.lastCMDReceived = trame[:-1]
                    self.errorFrame = False
                    self.errorTimeout = False
                    self.cptSuccess += 1
                else:
                    self.lastCMDReceived = []
                    self.errorTimeout = False
                    self.errorFrame = True
                    self.cptFail += 1
            else:
                self.lastCMDReceived = []
                self.errorTimeout = True
                self.errorFrame = False
                self.cptFail += 1
        else:
            self.lastCMDReceived = []
            self.errorFrame = False
            self.errorTimeout = False

    def readCommandByID(self):
        trame = ''
        trame_received = False

        while not trame_received:   # While rc==0
            trame_received = True
            self.errorTimeout = True
            if self.statusRCV == 0:
                self.SOF_detected = False
                self.correct_ID_detected = False
                if len(self.buffer) >= 3:
                    self.SOF_detected = self.readBuffer(1) == b'{'
                    if self.SOF_detected:
                        self.currentRC = self.readBuffer(2)
                        if int.from_bytes(self.currentRC, "big") in self.lenByID:
                            self.sizePayload = self.lenByID[int.from_bytes(self.currentRC, "big")][0]+5  # Data length + 5 control byte {, rc x 2, stat, }
                            self.correct_ID_detected = True
                        self.statusRCV = 1
                else:
                    self.fillBuffer()

            if self.statusRCV == 1:
                if len(self.buffer) >= (self.sizePayload - 3):
                    self.statusRCV = 0
                    if self.SOF_detected and self.correct_ID_detected:
                        trame = self.readBuffer(self.sizePayload - 3)
                        #print(trame)
                        #print("RC: " + str(self.currentRC))
                        if trame[-1] == ord('}'):  # framing OK
                            if (self.lenByID[int.from_bytes(self.currentRC, "big")][1] != 0) or (self.lenByID[int.from_bytes(self.currentRC, "big")][2] != 0): # if Stat_disp or Data disp of trame != 0
                                self.lastCMDReceived = self.currentRC + trame[:-1]

                                #print(self.lastCMDReceived)
                                self.errorFrame = False
                                self.errorTimeout = False
                                self.cptSuccess += 1
                            elif int.from_bytes(self.currentRC, "big") == dev.SCRIPT_FLAG_RC:   # End loop flag
                                self.endLoopFlag = True
                                self.errorFrame = False
                                self.errorTimeout = False
                                self.cptSuccess += 1
                            else:
                                trame_received = False
                        else:
                            self.lastCMDReceived = []
                            self.errorTimeout = False
                            self.errorFrame = True
                            self.cptFail += 1
                            print("Len err")
                    else:
                        #print(self.lastCMDReceived)
                        self.lastCMDReceived = []
                        self.errorTimeout = False
                        self.errorFrame = True
                        self.cptFail += 1
                        print("ID err")
                else:
                    self.fillBuffer()
                    self.errorTimeout = True

        if (len(self.lastCMDReceived)) > 1:
            return (not self.errorTimeout) and (not self.errorFrame) #and (self.lastCMDReceived[1] == 1)
        else:
            return False

    def sendCommand(self, data, size):
        if self.interface == const.UART_INTERFACE:
            self.uart.send(data)

        elif self.interface == const.CAN_INTERFACE:
            to_send = data
            while to_send is not None:
                if len(to_send) <= 8:   # 8 bytes per send max
                    self.can.send(to_send)
                    to_send = None
                else:
                    self.can.send(to_send[0:8])
                    to_send = to_send[8:]

        self.readCommand(size)
        #print(f'{data} ({size}) : {self.lastCMDReceived}')
        if size > 1:  # Command with acknowledge (not filling buffer)
            return (not self.errorTimeout) and (not self.errorFrame) and (self.lastCMDReceived[2] == 1)
        else:
            return True

    def readRev(self):
        #self.sendCommand(JSON.packRev(0).encode(), 9)
        if self.sendCommand(JSON.packRev(0).encode(), 9):
            self.rev = (self.lastCMDReceived[3] << 24) + (self.lastCMDReceived[4] << 16) + (self.lastCMDReceived[5] << 8) + self.lastCMDReceived[6]
            if self.rev > const.MAX_MICRO_REV:
                self.rev = 0
        else:
            self.rev = 0

    def scriptOpen(self, path):
        #print(const.SCRIPT_PATH + self.scriptFName)
        self.fileScript = open(path , "r")

    def scriptClose(self):
        self.fileScript.close()

    def scriptExtract_CMD_Size(self, scriptLine):
        scriptLine = scriptLine.replace("\n", "")
        return scriptLine[:scriptLine.rindex("}") + 1], int(scriptLine[scriptLine.rindex("}") + 1:])

    def scriptExecute(self, path):
        try:
            self.scriptOpen(path)
            result = True
            self.scriptLine = 0
            for line in self.fileScript:
                if result:
                    scriptLine = line.replace("\n", "")
                    line_extracted = self.scriptExtract_CMD_Size(scriptLine)
                    result = self.sendCommand(bytes(line_extracted[0], "utf8"), line_extracted[1])
                    #print(f'{line_extracted[0]} : {self.lastCMDReceived} {self.uart.uart_com.in_waiting}')
                    if line_extracted[1] == 0: # No ack, wait a little bit for execution
                        time.sleep(0.005)
                    self.scriptLine = self.scriptLine + 1
                    #print('status : ' + str(self.errorFrame) + ' ' + str(self.errorTimeout) + '   |   ' + str(self.lastCMDReceived))

            self.scriptClose()
            if result:
                self.scriptLine = 0

            return result
        except IOError:
            print('Can\'t open Script')
            return False

    def startChain(self, appPath, scripts, HWscriptUsed, matrixSetup, devTypeUsed, wait):
        self.clear_buffers()

        #print(devTypeUsed)
        #print(scripts)

        # Execute commands at reception
        if not self.sendCommand(JSON.packCom(1, 0).encode(), 5):
            print('Execute command at reception error')
            return False

        # Enable commands acknowledge
        if not self.sendCommand(JSON.packCom(6, 0x3).encode(), 5):
            print('Enable command ack error')
            return False

        # Clear micro buffer
        """
        if not self.sendCommand(JSON.packCom(3).encode(), 4):
            print('Fill loop error')
            return False
        """

        # Disable INTB pin as buffer trig (if MC33664 in sleep mode)
        if not self.sendCommand(JSON.packComTrg(2, 16, 0, 2).encode(), 5):
            print('Disable INT error2')
            return False

        # Disable RXD pin as buffer trig (if MC33665 in sleep mode)
        if not self.sendCommand(JSON.packComTrg(4, 20, 0, 2).encode(), 5):  # SPI_SIN -> PTD20 # Check if needed to add PTC29 (CAN3_RX)?
            print('Enable INT error2')
            return False

        # Disable STB_N pin as buffer trig  (if MC33665 in sleep mode)
        if not self.sendCommand(JSON.packComTrg(4, 21, 0, 2).encode(), 5):  # STB_N -> PTD21
            print('Enable INT error3')
            return False

        # Define setup (APP init + Nodes Bind)
        print(f'{matrixSetup=}')
        for chain in range(const.MAX_CHAIN_NB):
            cadd = matrixSetup[0][chain + 1]
            send = matrixSetup[1][chain + 1]
            echo = matrixSetup[2][chain + 1]

            echo = 9 if echo in (7,8,9) else echo
            devPos = 1

            if send not in (7,8,9):   # Send phy must be not NULL
                # App init for each chain
                if not self.sendCommand(JSON.packAppInit(chain, cadd, send, echo).encode(), 5):
                    print('App init error')
                    return False

                # Bind node 0 with same type as first device in chain
                # Find node 0 type (first node found)
                deviceID = 0
                devT = 0
                while (deviceID < const.MAX_DEVICE_NB) and (devT == 0):
                    devT = matrixSetup[3 + deviceID][chain + 1]
                    deviceID = deviceID + 1

                if not self.sendCommand(JSON.packAppBind(chain, "0", "0", "0", devT).encode(), 5):
                    print('Bind error')
                    return False

                # App bind for each device
                for device in range(const.MAX_DEVICE_NB):
                    devType = matrixSetup[3 + device][chain + 1]
                    if devType > 0:
                        dadd = matrixSetup[3 + device][0]
                        if not self.sendCommand(JSON.packAppBind(chain, devPos, dadd, dadd, devType).encode(), 5):
                            print('Bind error: IC ' + str(devPos))
                            return False
                        devPos = devPos + 1

            else:   # Bind chain to deInit chain if previously initialized
                if not self.sendCommand(JSON.packAppInit(chain, cadd, 9, 9).encode(), 5):
                    print('App init error')
                    return False

        # Fill loops, first one is phy
        if not self.sendCommand(JSON.packCom(1,1).encode(), 5):
            print('Fill loop error')
            return False

        for i in range(const.MAX_DEVICE_TYPE):
            if i in devTypeUsed:
                self.currentScript = dev.DEVICES_LIST[i].DEV_NAME + "/" + scripts[i] + const.LOOPS_PATH
                Fpath = appPath + const.SCRIPT_PATH + self.currentScript
                print('Filling: ' + str(self.currentScript))
                if not self.scriptExecute(Fpath):
                    print('Fill loop error: ' + str(self.currentScript))
                    return False

        # Final wait in loop
        if not self.sendCommand(JSON.packWaitMs(wait).encode(), 0):
            print('Initializing error')
            return False

        # End loop flag
        if not self.sendCommand(JSON.packFlag(65535).encode(), 0):
            print('Initializing error')
            return False

        if not self.sendCommand(JSON.packCom(1,0).encode(), 5):
            print('Initializing error')
            return False

        # Hardware init
        self.currentScript = const.HW_PATH + HWscriptUsed + ".txt"
        Fpath = appPath + const.SCRIPT_PATH + self.currentScript
        print('Initializing HW: ' + str(self.currentScript))
        if not self.scriptExecute(Fpath):
            print('Initializing hardware: ' + str(self.currentScript))
            return False

        # Launch init, starting by phy device that will configure phy and start all defined chains
        for i in range(const.MAX_DEVICE_TYPE):
            if i in devTypeUsed:
                self.currentScript = dev.DEVICES_LIST[i].DEV_NAME + "/" + scripts[i] + const.INITS_PATH
                Fpath = appPath + const.SCRIPT_PATH + self.currentScript
                print('Initializing: ' + str(self.currentScript))
                if not self.scriptExecute(Fpath):
                    print('Initializing error: ' + str(self.currentScript))
                    return False

        # Launching loops (Interruptible)
        if not self.sendCommand(JSON.packCom(3,'xFFFFFFFF', 0).encode(), 5):
            print('Launching error 2')
            return False


        print('Chain started')
        return True

    def stopChain(self):
        self.sendCommand("{com:{cmd:5,val:0},rc:0}".encode(), 5)
        time.sleep(1)
        self.clear_buffers()
        self.lastCMDReceived = []
        self.clearCpt()

    def clearFaults(self, devTypesUsed):
        for deviceID in devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]

            if device == dev.BMA7126T:
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x1840', 6, 0, 0).encode(), 0):  # Clear VC_OV_STAT0&1 and VC_UV0&1_STAT0&1 by read
                    print('Sleep error1')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x1C40', 4, 0, 0).encode(), 0):  # Clear VB_OV_STAT0&1 and VB_UV_STAT0&1 by read
                    print('Sleep error2')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x1846', 2, 0, 0).encode(), 0):  # Clear VC_VB_CMP_STAT0&1 by read
                    print('Sleep error3')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x1C46', 2, 0, 0).encode(), 0):  # Clear VB_VC_CMP_STAT0&1 by read
                    print('Sleep error4')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x184B', 2, 0, 0).encode(), 0):  # Clear PRMM_AIN_OV_STAT and PRMM_AIN_UV_STAT by read
                    print('Sleep error5')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x1C4B', 2, 0, 0).encode(), 0):  # Clear SECM_AIN_OV_STAT and SECM_AIN_UV_STAT by read
                    print('Sleep error6')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x184D', 1, 0, 'x2000').encode(), 0):  # Clear PRMM_MEAS_STAT by write
                    print('Sleep error7')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x184D', 1, 0, 0).encode(), 0):  # Clear PRMM_MEAS_STAT by read
                    print('Sleep error8')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x1C4F', 1, 0, 'x2000').encode(), 0):  # Clear SECM_MEAS_STAT by write
                    print('Sleep error9')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x1C4F', 1, 0, 0).encode(), 0):  # Clear SECM_MEAS_STAT by read
                    print('Sleep error10')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x420', 1, 0, 'x07C7').encode(), 0):  # Clear FEH_SUPPLY_FLT_STAT by write
                    print('Sleep error11')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x422', 3, 'x0007', 'xFF3F0003').encode(), 0):  # Clear FEH_SUPPLY_FLT_STAT, FEH_ANA_FLT_STAT, FEH_COM_FLT_STAT and FEH_MEAS_FLT_STAT by write
                    print('Sleep error12')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x41F', 1, 0, 0).encode(), 0):  # Clear FEH_GRP_FLT_STAT by read
                    print('Sleep error13')
                    return False
                if not self.sendCommand(JSON.packAppCmd(8, 0, deviceID, 'x40A', 2, 0, 0).encode(), 0):  # Clear FEH_WAKEUP_REASON0&1 by read
                    print('Sleep error14')
                    return False
            elif not device.PHY:
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x24', 1, 0, 0).encode(), 0):  # Clear FAULT1
                    print('Fault1 clear error')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x25', 1, 0, 0).encode(), 0):  # Clear FAULT2
                    print('Fault2 clear error')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x26', 1, 0, 0).encode(), 0):  # Clear FAULT3
                    print('Fault3 clear error')
                    return False
        return True

    def sleepChain(self, devTypesUsed):
        chains_sleep = []
        self.stopChain()

        # Sleep devices (Global write)
        for deviceID in devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]
            if deviceID == 2:  # BMA7126T
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x1840', 6, 0, 0).encode(), 7):  # Clear VC_OV_STAT0&1 and VC_UV0&1_STAT0&1 by read
                    print('Sleep error1')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x1C40', 4, 0, 0).encode(), 7):  # Clear VB_OV_STAT0&1 and VB_UV_STAT0&1 by read
                    print('Sleep error2')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x1846', 2, 0, 0).encode(), 7):  # Clear VC_VB_CMP_STAT0&1 by read
                    print('Sleep error3')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x1C46', 2, 0, 0).encode(), 7):  # Clear VB_VC_CMP_STAT0&1 by read
                    print('Sleep error4')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x184B', 2, 0, 0).encode(), 7):  # Clear PRMM_AIN_OV_STAT and PRMM_AIN_UV_STAT by read
                    print('Sleep error5')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x1C4B', 2, 0, 0).encode(), 7):  # Clear SECM_AIN_OV_STAT and SECM_AIN_UV_STAT by read
                    print('Sleep error6')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x184D', 1, 0, 'x2000').encode(), 7):  # Clear PRMM_MEAS_STAT by write
                    print('Sleep error7')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x184D', 1, 0, 0).encode(), 7):  # Clear PRMM_MEAS_STAT by read
                    print('Sleep error8')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x1C4F', 1, 0, 'x2000').encode(), 7):  # Clear SECM_MEAS_STAT by write
                    print('Sleep error9')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x1C4F', 1, 0, 0).encode(), 7):  # Clear SECM_MEAS_STAT by read
                    print('Sleep error10')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x420', 1, 0, 'x07C7').encode(), 7):  # Clear FEH_SUPPLY_FLT_STAT by write
                    print('Sleep error11')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x422', 3, 'x0007', 'xFF3F0003').encode(), 7):  # Clear FEH_SUPPLY_FLT_STAT, FEH_ANA_FLT_STAT, FEH_COM_FLT_STAT and FEH_MEAS_FLT_STAT by write
                    print('Sleep error12')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x41F', 1, 0, 0).encode(), 7):  # Clear FEH_GRP_FLT_STAT by read
                    print('Sleep error13')
                    return False
                if not self.sendCommand(JSON.packAppCmd(14, 0, deviceID, 'x40A', 2, 0, 0).encode(), 7):  # Clear FEH_WAKEUP_REASON0&1 by read
                    print('Sleep error14')
                    return False

            elif not device.PHY:    # Others devices except PHYs
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x24', 1, 0, 0).encode(), 7):  # Clear FAULT1
                    print('Fault1 clear error')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x25', 1, 0, 0).encode(), 7):  # Clear FAULT2
                    print('Fault2 clear error')
                    return False
                if not self.sendCommand(JSON.packAppCmd(9, 0, deviceID, 'x26', 1, 0, 0).encode(), 7):  # Clear FAULT3
                    print('Fault3 clear error')
                    return False

        if not self.sendCommand(JSON.packAppCmd(15, 0, 0, 0, 0, 0, '0').encode(), 7):  # Sleep all chains + phy
            print('Sleep error Gen1')
            return False

        return True

    def wakeupChain(self, devTypesUsed):

        for deviceID in devTypesUsed:
            device = dev.DEVICES_LIST[deviceID]
            if device.PHY:
                if deviceID == 0:   # MC33664 PHY_1 in MC33665 Cz board
                    if not self.sendCommand(JSON.packComTrg(2, 16, 0, 2).encode(), 5):  # Disable INTB pin as buffer trig (PTB16)
                        print('Disable INT error2')
                        return False
                    if not self.sendCommand(JSON.packIOSet(4, 27, 1).encode(), 5):  # EN -> PTD27
                        print('Enable PHY error1')
                        return False

                elif deviceID == 1: # MC33665
                    # Disable RXD pin as buffer trig
                    if not self.sendCommand(JSON.packComTrg(3, 9, 0, 2).encode(), 5):  # CAN_RX/SPI_SIN -> PTC9
                        print('Enable INT error2')
                        return False

                    # Disable STB_N pin as buffer trig
                    if not self.sendCommand(JSON.packComTrg(4, 21, 0, 2).encode(), 5):  # STB_N -> PTD21
                        print('Enable INT error3')
                        return False

        # Wakeup devices
        """if not self.sendCommand(JSON.packAppCmd(4, 0, 0, 0, 0, 0, 0).encode(), 6):
            print('Wakeup error')
            return False"""

        # Execute buffer in loop interruptible
        if not self.sendCommand(JSON.packCom(3,'xFFFFFFFF').encode(), 5):
            print('Start buffer error')
            return False

        return True

    def initTrigPins(self, device):
        for i in range(device.DISP_PARAMS_NB + 1):
            if device.trigPorts[i] != 0:
                cmd = JSON.packIOInit(device.trigPorts[i], device.trigPins[i], 0, 0, 0, 0)
                if self.sendCommand(cmd.encode(), 5) is not True:
                    return False
                cmd = JSON.packIOSet(device.trigPorts[i], device.trigPins[i], 0)
                if self.sendCommand(cmd.encode(), 5) is not True:
                    return False
        return True

    def setGPIO(self, port, pin, state):
        cmd = JSON.packIOSet(port, pin, state)
        self.sendCommand(cmd.encode(), 0)

class JSON():
    def packCom(cmd, val, RC = 0):
        return "{com:{cmd:" + str(cmd) + ",val:" + str(val) + "},rc:" + str(RC) + "}"

    def packFlag(RC = 65535):
        return "{flag:0,rc:" + str(RC) + "}"

    def packWaitMs(value, RC = 0):
        return "{wt_ms:" + str(value) + ",rc:" + str(RC) + "}"

    def packIOInit(port, pin, out, in_, imcr, opt, RC = 0):
            return "{io_init:{port:" + str(port) + ",pin:" + str(pin) + ",out:" + str(out) + ",in:" + str(in_) + ",imcr:" + str(imcr) + ",opt:" + str(opt) + "},rc:" + str(RC) + "}"

    def packIOSet(port, pin, val, RC = 0):
        return "{io_set:{port:" + str(port) + ",pin:" + str(pin) + ",val:" + str(val) + "},rc:" + str(RC) + "}"

    def MISCPackWait(wt_type, value, RC = 0):
        return "{wt_" + str(wt_type) + ":" + str(value) + ",rc:" + str(RC) + "}"

    def packPhyInit(id, type, speed, speed_2, canid, prot, RC = 0):
        return "{phy_init:{id:" + str(id) + ",type:" + str(type) + ",speed:" + str(speed) + ",speed_2:" + str(speed_2) + ",id:" + str(canid) + ",prot:" + str(prot) + "},rc:" + str(RC) + "}"

    def packAppInit(chain, cadd, send, echo, RC = 0):
        return "{app_init:{chain:" + str(chain) + ",cadd:" + str(cadd) + ",send:" + str(send) + ",echo:" + str(echo) + "},rc:" + str(RC) + "}"

    def packAppBind(chain, node, cid_s, cid_e, ic_type, RC = 0):
        return "{app_bind:{chain:" + str(chain) + ",node:" + str(node) + ",cid_s:" + str(cid_s) + ",cid_e:" + str(cid_e) + ",type:" + str(ic_type) + "},rc:" + str(RC) + "}"

    def packAppStart(chain, RC = 0):
        return "{app_start:" + str(chain) + ",rc:" + str(RC) + "}"

    def packAppCmd(cmd_type, chain, node, addr, n_reg, val2, val1, RC = 0):
        return "{app_cmd:{type:" + str(cmd_type) + ",chain:" + str(chain) + ",node:" + str(node) + ",addr:" + str(addr) + ",n_reg:" + str(n_reg) + ",val2:" + str(val2) + ",val1:" + str(val1) + "},rc:" + str(RC) + "}"

    def packRev(RC = 0):
        return "{rev:1,rc:" + str(RC) + "}"

    def packComTrg(port, pin, tr_type, trig, RC = 0):
        return "{com_trg:{port:" + str(port) + ",pin:" + str(pin) + ",type:" + str(tr_type) + ",trig:" + str(trig) + "},rc:" + str(RC) + "}"