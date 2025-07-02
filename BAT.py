import socket
import select

class BAT():

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('127.0.0.1', 7171))
        self.sock.listen(1)                 #One client maximum (Bat Emc only)
        self.connection = None
        self.client_addr = None

        self.inputs = [self.sock]
        self.outputs = []
        self.state = 1                      #Waiting connection state

        self.dataSplit = []

        self.event = ''

        self.projectName = ''
        self.testName = ''
        self.modulation = ''
        self.frequency = 0
        self.target = 0
        self.levelMa = 0

        self.updated = False

        #self.debug_output = open("bat_debug.txt", "a")
        #self.debug_output.truncate(0)   # Clear file

        print('Socket waiting bat')

    def update(self):
        if (self.state == 1) or (len(self.dataSplit) == 0): # No data in buffer
            readable, writable, exceptional = select.select(self.inputs, self.outputs, self.inputs, 0.0001)
            for s in readable:
                if (s is self.sock) and self.state == 1:      #Waiting bat connection and connection on-going
                    self.connection, self.client_addr = self.sock.accept()
                    self.connection.setblocking(0)
                    self.inputs.append(self.connection)
                    print('Client accepted')
                    self.state = 2
                elif self.state == 2:
                    try:
                        data = s.recv(1024)
                        dataStr = data.decode('utf-8', errors='ignore')
                        #print('BAT: ' + dataStr)
                        theSplit = dataStr.split('|')
                        for i in theSplit:
                            if len(i) > 0:
                                self.dataSplit.append(i)
                        if not data: # Client disconnected
                            if s in self.outputs:
                                self.outputs.remove(s)
                            self.inputs.remove(s)
                            self.close()
                    except ConnectionResetError: #Connection reset by peer
                        if s in self.outputs:
                            self.outputs.remove(s)
                        self.inputs.remove(s)
                        self.close()

        #print(self.dataSplit)
        if (self.state == 2) and (len(self.dataSplit) > 0):  # Data in buffer
            cmdSplit = str(self.dataSplit[0]).split('~')
            #print(cmdSplit)
            #self.debug_output.write(str(cmdSplit) + '\n\r') # Debug output
            self.event = cmdSplit[0]
            if (len(cmdSplit) >= 3) and (cmdSplit[0] == 'START'):
                self.projectName = cmdSplit[1]
                self.testName = cmdSplit[2]
                self.updated = True
                #print('Start: ' + self.projectName + ' ' + self.testName)
            elif (len(cmdSplit) >= 4) and (cmdSplit[0] == 'TRIG'):
                if (int(cmdSplit[3])) != 2: #Workaround target = 2 is rejected
                    self.modulation = cmdSplit[1]
                    #self.frequency = int(cmdSplit[2])
                    self.frequency = float(cmdSplit[2])
                    self.target = int(cmdSplit[3])  # Added for test
                    self.updated = True
                else:
                    self.sendAck()  #Workaround target = 2 is rejected
                #print('Trig')

            elif (len(cmdSplit) >= 5) and (cmdSplit[0] == 'MEAS'):
                self.modulation = cmdSplit[1]
                #self.frequency = int(cmdSplit[2])
                self.frequency = float(cmdSplit[2])
                self.target = int(cmdSplit[3])
                self.levelMa = int(cmdSplit[4])
                self.updated = True
                #print('Meas: ' + self.modulation + ' ' + str(self.frequency) + ' ' + str(self.target) + ' ' + str(self.levelMa) + 'mA')

            elif (len(cmdSplit) >= 4) and (cmdSplit[0] == 'CTRL'):
                self.updated = True
                self.modulation = cmdSplit[1]
                # self.frequency = int(cmdSplit[2])
                self.frequency = float(cmdSplit[2])
                self.target = int(cmdSplit[3])
                #print('Ctrl')

            elif (len(cmdSplit) >= 1) and (cmdSplit[0] == 'END'):
                self.updated = True
                #print('End')

            self.dataSplit = self.dataSplit[1:]  # Remove Item from dataSplit

    def sendAck(self):
        self.connection.send(b"NONE")

    def sendMove(self):
        self.connection.send(b"MOVE")

    def close(self):
        print('Client disconnected')
        self.dataSplit = []
        #self.debug_output.close()
        if self.connection is not None:
            self.connection.close()
            self.state = 1
