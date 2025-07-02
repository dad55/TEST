import time
from .comFT232H import comFT232H
readyTimeOUT = 1
MAX_SERIAL_TIMEOUT = 0.5
class ProtocolMicroFT232H():
    def __init__(self):

        self.myFT = comFT232H()

        self.ready = False
        self.cptSuccess = 0
        self.cptFail = 0
        self.errorFrame = False
        self.errorTimeout = False
        self.errorMCU = False
        self.statusError = 1

        self.lastCMDReceived = []

    def clearReadBuffer(self):
        nb_byte = self.myFT.in_waiting()
        if nb_byte > 0:
            self.myFT.read(nb_byte)


    # def getComToken(func):
    #     '''
    #     Decorator to Check there is no COM with uC
    #     '''
    #     # @wraps(func)
    #     def wrap(*args, **kwargs):
    #         if not args[0].ready:  # args[0] is equivalent to self in decorator
    #             timeStart = time.time()
    #             while time.time() - timeStart < readyTimeOUT:
    #                 if args[0].ready:
    #                     break
    #                 time.sleep(0.001)
    #
    #         args[0].ready = False
    #         result = func(*args, **kwargs)
    #         args[0].ready = True
    #         return result
    #
    #     return wrap

    def readCommand(self, size):
        '''
        Read a frame from the microcontroller
        place result in self.lastCMDReceived
        error flags are self.errorTimeout & self.errorFrame
        '''
        trame = []
        if size > 0:
            SOF_detected = False
            time0 = time.time()

            while not SOF_detected and (time.time() - time0 < MAX_SERIAL_TIMEOUT):  # detect '{'
                if self.myFT.in_waiting() > 0 and not SOF_detected:
                    SOF_detected = (self.myFT.read(1) == b'{')
                else:
                    time.sleep(1E-6)  # 0.0001

            while SOF_detected and (self.myFT.in_waiting() < size - 1) and (time.time() - time0 < MAX_SERIAL_TIMEOUT):  # wait full trame received
                time.sleep(1E-6)  # 0.0001

            if (self.myFT.in_waiting() >= (size - 1)) and SOF_detected and ((time.time() - time0) < MAX_SERIAL_TIMEOUT):
                trame = self.myFT.read(size - 1)
                if trame[-1] == ord('}'):  # framing OK
                    self.lastCMDReceived = trame[:-1]
                    if self.lastCMDReceived[2] == 1:  # mcu status OK
                        self.errorFrame = False
                        self.errorTimeout = False
                        self.errorMCU = False
                        self.cptSuccess += 1
                    else:
                        self.statusError = self.lastCMDReceived[2]
                        self.errorTimeout = False
                        self.errorFrame = False
                        self.errorMCU = True
                        self.cptFail += 1
                else:
                    self.lastCMDReceived = []
                    self.errorTimeout = False
                    self.errorFrame = True
                    self.errorMCU = False
                    self.cptFail += 1
            else:
                self.lastCMDReceived = []
                self.errorTimeout = True
                self.errorFrame = False
                self.errorMCU = False
                self.cptFail += 1
        else:
            self.lastCMDReceived = []
            self.errorFrame = False
            self.errorTimeout = False
            self.errorMCU = False


    def sendCommand(self, data, size):
        '''
        Send a command to microcontroller and read back the response
        result is placed in self.lastCMDReceived
        '''
        self.myFT.send(data)
        self.readCommand(size)

        if size > 1:  # Command with acknowledge (not filling buffer)
            return (not self.errorTimeout) and (not self.errorFrame) and (not self.errorMCU)
        else:
            return True
