import sys
from PyQt5 import QtCore, QtWebSockets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


class LocalGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.process = QProcess()
        self.process.started.connect(self.processStarted)
        self.initUI()

    def processStarted(self):
        wc = WebsocketClient(self)

    def initUI(self):
        self.QLE_ListenAddr = QLineEdit(self)
        self.QLB_ListenAddr = QLabel('Local Host: ', self)
        self.QLE_ListenPort = QLineEdit(self)
        self.QLB_ListenPort = QLabel('Local Port: ', self)
        self.QLE_RemoteAddr = QLineEdit(self)
        self.QLB_RemoteAddr = QLabel('Remote Host: ', self)
        self.QLE_RemotePort = QLineEdit(self)
        self.QLB_RemotePort = QLabel('Remote Port: ', self)
        self.QLE_Username = QLineEdit(self)
        self.QLB_Username = QLabel('Username: ', self)
        self.QLE_Password = QLineEdit(self)
        self.QLB_Password = QLabel('Password: ', self)
        self.QLE_Password.setEchoMode(QLineEdit.Password)
        self.QPB_Start = QPushButton('Start LocalProxy Process', self)
        self.QPB_Close = QPushButton('Close LocalProxy Process', self)
        self.QLB_LocalState = QLabel('LocalProxy Process State: ', self)
        self.QLE_LocalState = QLineEdit(self)
        self.QLB_Test = QLabel('Download to test throughput: ', self)
        self.QPB_Test = QPushButton('Test Process', self)
        self.QLB_ThroughPut = QLabel('RealTime ThroughPut: ', self)
        self.QLE_ThroughPut = QTextEdit(self)

        self.layout = QGridLayout()
        self.layout.addWidget(self.QLB_ListenAddr, 1, 0)
        self.layout.addWidget(self.QLE_ListenAddr, 1, 1)
        self.layout.addWidget(self.QLB_ListenPort, 2, 0)
        self.layout.addWidget(self.QLE_ListenPort, 2, 1)
        self.layout.addWidget(self.QLB_RemoteAddr, 3, 0)
        self.layout.addWidget(self.QLE_RemoteAddr, 3, 1)
        self.layout.addWidget(self.QLB_RemotePort, 4, 0)
        self.layout.addWidget(self.QLE_RemotePort, 4, 1)
        self.layout.addWidget(self.QLB_Username, 5, 0)
        self.layout.addWidget(self.QLE_Username, 5, 1)
        self.layout.addWidget(self.QLB_Password, 6, 0)
        self.layout.addWidget(self.QLE_Password, 6, 1)
        self.layout.addWidget(self.QPB_Start, 7, 0)
        self.layout.addWidget(self.QPB_Close, 7, 1)
        self.layout.addWidget(self.QLB_LocalState, 8, 0)
        self.layout.addWidget(self.QLE_LocalState, 8, 1)
        self.layout.addWidget(self.QLB_Test, 9, 0)
        self.layout.addWidget(self.QPB_Test, 9, 1)
        self.layout.addWidget(self.QLB_ThroughPut, 10, 0)
        self.layout.addWidget(self.QLE_ThroughPut, 10, 1, 1, 1)

        self.QPB_Start.clicked.connect(self.StartLocalProcess)
        self.QPB_Close.clicked.connect(self.CloseLocalProcess)
        self.QPB_Test.clicked.connect(self.StartTestProcess)

        self.setLayout(self.layout)
        self.setGeometry(300, 300, 300, 300)
        self.setWindowTitle('Local GUI')
        self.show()

    def StartLocalProcess(self):
        ui.QLE_ThroughPut.setText("")
        ui.QLE_LocalState.setText("Localproxy进程正在运行")
        ListenAddr = self.QLE_ListenAddr.text()
        ListenPort = self.QLE_ListenPort.text()
        RemoteAddr = self.QLE_RemoteAddr.text()
        RemotePort = self.QLE_RemotePort.text()
        Username = self.QLE_Username.text()
        Password = self.QLE_Password.text()

        args = ['./Localproxy.py', '-sla', ListenAddr, '-slp', ListenPort, '-rd', RemoteAddr, '-rp', RemotePort, '-u', Username, '-p', Password]
        print(args)
        self.process.start("python3", args)

    def CloseLocalProcess(self):
        ui.QLE_LocalState.setText("Localproxy进程已经关闭")
        self.process.kill()

    #TestProcess封装curl命令，可以直接启动进程进行测试
    def StartTestProcess(self):
        self.TestProcess = QProcess()
        args = ['-L', '-k', '-x', 'socks5h://127.0.0.1:1081', '-o', '/dev/null',
                     'http://download.qt.io/archive/qt/5.15/5.15.1/single/qt-everywhere-src-5.15.1.zip']
        self.TestProcess.start("curl", args)

    def __del__(self):
        self.process.kill()
        self.TestProcess.kill()

class WebsocketClient(QtCore.QObject):
    def __init__(self, parent):
        super().__init__(parent)

        self.client = QtWebSockets.QWebSocket("", QtWebSockets.QWebSocketProtocol.Version13, None)
        self.client.error.connect(self.error)
        self.client.connected.connect(self.SendAuthenMsg)
        self.client.textMessageReceived.connect(self.MsgRecv)
        self.client.open(QUrl("ws://127.0.0.1:8765"))

    # 发送认证信息
    def SendAuthenMsg(self):
        self.client.sendTextMessage('CONNECT FROM LOCALGUI')

    def MsgRecv(self, message):
        ui.QLE_ThroughPut.setText(message)

    def error(self, error_code):
        ui.QLE_ThroughPut.setText(f'ERROR {error_code}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = LocalGUI()
    sys.exit(app.exec_())