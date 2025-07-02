import ftd2xx as ftd
import time

import CONST as const

#class comFT232H():
class SerialCOM():
    def __init__(self):
        self.available = []
        self.myComFTD = None #Will be the class FTD2xx
        self.ready = False
        self.selectedAddr = ''

    def __del__(self):
        self.close()

    def scan(self=None):
        self.close()
        self.available = [] #Remove previous ports scan
        listCom = ftd.listDevices()
        try :
            nbCom = len(listCom)
            for i in range(nbCom):
                comFTD2XX = ftd.open(i) #Return a FTD2XX object
                comFTD2XX.setBitMode(0x00, 0x2)  # Set MPSSE mode
                comFTD2XX.write(bytes.fromhex(f'81')) # Read only AD0 to AD7 pins
                temp = int.from_bytes(comFTD2XX.read(1),'little')
                ad6 = temp & 0x40
                comFTD2XX.setBitMode(0x00, 0x0) #Reset the FT232H to asynchronus uart mode (rx/tx with mcu)
                if ad6 == 0x40:
                    self.available.append(comFTD2XX.getComPortNumber()) #If ad6=1, port de com, sinon port de debug
                comFTD2XX.close()
        except:
            return "No micro available"
        else:
            return self.available

    def read_AD6(self,comFTD2XX):
        comFTD2XX.setBitMode(0x00, 0x2)  # Set MPSSE mode

    def open(self):
        print(f'{self.selectedAddr=}')
        print(f'{self.available=}')
        port = self.available.index(int(self.selectedAddr))
        try:
            self.myComFTD = ftd.open(port)
            self.myComFTD.setBaudRate(const.UART_BAUDRATE)
            self.myComFTD.setBreakOff()
            self.myComFTD.setTimeouts(10,10)
            self.myComFTD.setLatencyTimer(1)
            self.reset_mcu()
            self.ready = True
        except IOError:
            print("Can't open uart port ")
            self.ready = False


    def reset_mcu(self):
        self.set_gpio_mode()
        # self.set_gpio_input_output('00', '80')
        self.set_gpio_input_output('80', '80')
        self.set_gpio_input_output('00', '80')
        self.set_usb_mode()
        time.sleep(0.5)

    def close(self):
        if self.ready:
            self.myComFTD.close()
            self.ready = False

    def in_waiting(self):
        if self.ready:
            return self.myComFTD.getQueueStatus()
        else:
            return 0

    def send(self, msg):
        if self.ready:
            if isinstance(msg, str):
                msg = msg.encode()
            self.myComFTD.write(msg)


    def read(self, size=None):
        if self.ready:
            return self.myComFTD.read(size)
        else:
            return None

    def set_gpio_mode(self):
        self.myComFTD.setBitMode(0x00, 0x2) #Set MPSSE mode

    def set_gpio_input_output(self, value:str, direction:str):
        '''
        Syntax : <Command><Value><Direction>
            - Command :
                    0x80 : Set the direction and value of the first 8 lines (AD0 to AD7)
                    0x82 : Set the direction and value of the second 8 lines (AC0 to AC7)
                    0x81 : Read the current states of the first 8 lines (AD0 to AD7) /!\ No param <Value><Direction> for this command
                    0x83 : Read the current states of the second 8 lines (AC0 to AC7) /!\ No param <Value><Direction> for this command
            - Value :
                    0 = GND
                    1 = 3V3
            - Direction :
                    0 = Input
                    1 = Output
            - For Value and Direction, order is : 0x01=AD0 , 0x02=AD1 , ... , 0x80=AD7
        '''
        frame = bytes.fromhex(f'80'+value+direction)
        # print(f"{frame=}")
        self.send(frame)

    def read_gpio(self):
        frame = bytes.fromhex(f'81') # Read only AD0 to AD7 pins
        self.send(frame)
        return(self.read(1))

    def set_usb_mode(self):
        self.myComFTD.setBitMode(0x00, 0x0) #Reset the FT232H to asynchronus uart mode (rx/tx with mcu)


    def clearSendBuffer(self):
        PURGE_TX = 2
        self.myComFTD.purge(PURGE_TX)

    def clearReadBuffer(self):
        PURGE_RX = 1
        self.myComFTD.purge(PURGE_RX)
