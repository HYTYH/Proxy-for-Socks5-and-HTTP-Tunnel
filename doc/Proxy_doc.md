# 本地系统

本地系统部分（Local），本地系统部分使用了python的asyncio库提供的streams（streams是用于处理网络连接的支持 async/await 的高层级原语。 允许发送和接收数据，而不需要使用回调或低级协议和传输）实现了一个支持SOCKS5协议和HTTP tunnel的双协议本地代理服务器，可以与客户端（浏览器或LocalGUI）以及远端模块（Remote）通信，并对本地代理进行管理。

## SOCKS5服务

```python
# 同目标服务器通信机制
# 在此计算吞吐率，利用锁机制互斥访问临界变量length
# 在此更新的吞吐率会定时发送给LocalGUI端并显示
async def dst(reader, writer):
    while True:
        data = await reader.read(6000)

        await dict[0][0].acquire()
        try:
            dict[0][1] = dict[0][1] + len(data)
        finally:
            dict[0][0].release()
        if len(data) == 0:
            raise MyError(logger.error("EOF"))
            return

        writer.write(data)
        await writer.drain()

# SOCKS5服务器
# LocalProxy端，与客户端建立连接后，转发到RemoteProxy端，与RemoteProxy端建立连接
async def SOCKS5_server(reader, writer):
    logger.info("SOCKS5_server start")
    try:
        data = await reader.readexactly(2)
        method = await reader.readexactly(data[1])
        flag = False
        for i in range(0, data[1]):
            if (method[i] == 0):
                flag = True
                break
        if (not flag):
            return

        logger.info("Socks5 successfully shake hand")
        # METHOD 00
        writer.write(b'\05\00')
        await writer.drain()

        # CMD进行转发
        rm_reader, rm_writer = await asyncio.open_connection(remoteAdd, sockport)
        logger.info(f'SOCKS5_server open_connection({remoteAdd}, {sockport})')

        # 将命令行接收的用户名和密码发送至Remote端进行验证
        info = username + " " + password
        rm_writer.write(info.encode())
        await rm_writer.drain()
        logger.info(f'SOCKS5_server send info to RemoteProxy which address is:{remoteAdd}, info: {info}')

        ans = await rm_reader.read(6000)
        if(ans.decode() != 'Grant'):
            logger.error(f'User {username} Access Denied, wrong username or password, please try again')
            exit(0)
        else:
            logger.info(f'Access granted, user {username} successfully login')

        task1 = asyncio.create_task(dst(reader, rm_writer))
        task2 = asyncio.create_task(dst(rm_reader, writer))
        await task1
        await task2

    except asyncio.IncompleteReadError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionResetError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionAbortedError as exc:
        raise MyError(logger.error(f'{exc}'))
```

【文字描述】

#### 注意：报文解析过程在远端的与本地模块通信模块实现

- 此协程函数SOCKS5_server用于在本地进行SOCKS5协议代理服务。
- 协程函数与本地端口连接，接受本地端口发来的报文并进行握手，握手成功则向Remote端发起连接，连接建立后向Remote端转发SOCKS5报文中的CMD消息以及从本地命令行读入的用户名及密码到Remote端进行验证。
- 发送用户的用户名和密码之后，在Remote端进行验证，Remote端会返回消息，如果返回了‘Grant’，则验证成功，进行后续内容，弱验证失败则结束本地服务，并显示错误信息，用户需要再次尝试登陆。
- 用户名，密码验证成功则开始转发消息。在本地端口和Remote端的转发功能通过task1和task2两个异步作业调用dst函数实现。
- dst函数是一个单纯的接受消息，转发消息机制，在其中实现了计算吞吐率（利用asyncio的Lock机制），在之后的与远端模块通信模块进行相关讲解。



## HTTPS隧道服务

```python
# 同目标服务器通信机制
# 在此计算吞吐率，利用锁机制互斥访问临界变量length
# 在此更新的吞吐率会定时发送给LocalGUI端并显示
async def dst(reader, writer):
    while True:
        data = await reader.read(6000)

        await dict[0][0].acquire()
        try:
            dict[0][1] = dict[0][1] + len(data)
        finally:
            dict[0][0].release()
        if len(data) == 0:
            raise MyError(logger.error("EOF"))
            return

        writer.write(data)
        await writer.drain()

# HTTP TUNNEL
# LocalProxy端，与客户端建立连接后，转发到RemoteProxy端，与Remote端建立连接
async def HTTP_TUNNEL(reader, writer):
    logger.info("HTTP_TUNNEL start")
    try:
        rm_reader, rm_writer = await asyncio.open_connection(remoteAdd, httpport)
        logger.info(f'HTTP_TUNNEL open_connection({remoteAdd}, {httpport})')

        # 将命令行接收的用户名和密码发送至Remote端进行验证
        info = username + " " + password
        rm_writer.write(info.encode())
        await rm_writer.drain()
        logger.info(f'HTTP_TUNNEL send info to RemoteProxy which address is:{remoteAdd}, info: {info}')

        ans = await rm_reader.read(6000)
        if (ans.decode() != 'Grant'):
            logger.error(f'User {username} Access Denied, wrong username or password, please try again')
            exit(0)
        else:
            logger.info(f'Access Granted, user {username} successfully login')

        task1 = asyncio.create_task(dst(reader, rm_writer))
        task2 = asyncio.create_task(dst(rm_reader, writer))
        await task1
        await task2
    except asyncio.IncompleteReadError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionResetError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionAbortedError as exc:
        raise MyError(logger.error(f'{exc}'))
```

【文字描述】

- 与SOCKS5_server协程函数相似，HTTP_TUNNEL协程函数实现了在本地进行HTTP TUNNEL代理服务。
- HTTP TUNNEL发起与Remote端的连接
- 将用户在本地输入的用户名及密码打包发送给Remote端进行验证。
- 由于HTTP的协议格式十分简单，所以直接将报文转发到Remote端进行验证。不再特殊在Local端进行解析
- Remote端会返回消息，如果返回了‘Grant’，则验证成功，进行后续内容，弱验证失败则结束本地服务，并显示错误信息，用户需要再次尝试登陆。用户名，密码验证成功则开始转发消息。
- 在本地端口和Remote端的转发功能通过task1和task2两个异步作业调用dst函数实现。
- dst函数是一个单纯的接受消息，转发消息机制，在其中实现了计算吞吐率（利用锁机制），在之后的与远端模块通信模块进行相关讲解。



## 与远端模块通信

```python
# 同目标服务器通信机制
# 在此计算吞吐率，利用锁机制互斥访问临界变量length
# 在此更新的吞吐率会定时发送给LocalGUI端并显示
async def dst(reader, writer):
    while True:
        data = await reader.read(6000)

        await dict[0][0].acquire()
        try:
            dict[0][1] = dict[0][1] + len(data)
        finally:
            dict[0][0].release()
        if len(data) == 0:
            raise MyError(logger.error("EOF"))
            return

        writer.write(data)
        await writer.drain()
```

【文字描述】

- dst协程函数用于转发消息，并且实时计算吞吐率（用于在LocalGUI端进行显示）
- dst协程函数被上面的HTTP隧道服务，SOCKS5服务模块调用（用asyncio.create_task生成），可供本地模块与远程模块以及客户端通信使用。
- 简单介绍一下localGUI的用途，具体实现可参见下面的图形管理界面：LocalGUI为一个供用户使用的图形化界面，所以在用户发起登录成功以后，一个Local进程就是服务这个用户的，dict是由锁和转发量（带宽）组成的字典，保证在计算带宽的过程中数据不受影响。
- dst协程函数中的字典：下面是在主函数中字典的声明：

```python
if (dict.get(0) == None):
        lock = asyncio.Lock()
        dict[0] = [lock, length]
```

- 每次向LocalGUI转发length之后会将length清零（每秒转发，通过异步作业实现），实现实时更新吞吐率。
- 下面介绍转发机制：dst的reader和writer是单向的，由两个异步作业控制（参见上面两个模块的task1和task2），之所以称为单向的，是因为dst协程函数从本地端口利用reader读入消息，使用writer向Remote端转发，或者是利用reader读入Remote端消息，并利用writer向本地端口进行转发。



## 图形管理界面

```python
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
```

【文字描述】

- LocalGUI实现了一个图形化界面供用户使用。可以对Local端进行管理，实现进程的开始，运行，关闭，与Local端进行通信，显示认证信息以及实时吞吐率，用户登录成功则创建一个进程服务用户。
- 用户可以通过输入自己的用户名和密码，连接服务器，进行下载操作并实时查看吞吐率。
- 创建LocalGUI类，在类的构造函数中利用initUI函数初始化图形化界面。（19-61行）
- 界面设置了三个按钮（QPushButton）：start，close，test（63-65行）

#### 在pdf版本可以查看LocalGUI的图形化界面截图

- 界面通过QLineEdit控件接收本地服务器地址，本地端口，远程服务器地址，以及用户名和密码等参数。
- start按钮与槽函数StartLocalProcess关联，用于为用户创建一个进程（启动Local端），服务用户。
- close按钮与槽函数CloseLocalProcess关联，用于关闭进程。
- test按钮与槽函数StartTestProcess关联，此函数创建一个新的进程，运行curl命令下载文件进行测试，可供用户在localGUI界面上查看实时吞吐率。
- LocalGUI图形界面也可实时查看进程状态。
- 吞吐率是由Local端实时计算并显示到GUI上的：创建WebsocketClient类，用Qtwebsocket与本地进行通信，可以与local端进行认证（简单握手），并接受在local端计算得到的吞吐率以及报错信息（如用户名密码错误），实时显示在UI界面上。



# 远端系统

【文字描述】

远端系统提供了一个对用户进行管理的服务器，对从本地发来的请求进行验证，返回对应信息，与本地请求的网址 / 下载内容等进行向外部服务器的转发，并将外部服务器返回的信息转发会本地，对用户进行流控，用户信息验证，并可以通过sanic实现的REST接口对用户信息（用户数据库）进行相应的管理（增删改查）。



## 与本地模块通信

```python
# 同目标服务器通信机制
async def dst(reader, writer, bandwidth, u):
    while True:
        data = await reader.read(dict[u][1])
        if len(data) == 0:
            raise MyError(logger.error("EOF"))
            return
        await dict[u][0].acquire()
        try:
            writer.write(data)
            await writer.drain()
            if (int(dict[u][1]) > len(data)):
                dict[u][1] = int(dict[u][1]) - len(data)
            logger.info(f'USER {u} TOKEN remain: {dict[u][1]}')
            if (dict[u][1] < bandwidth * 128):
                logger.info(f'TOKEN remain less than 1/8, produce TOKEN')
                dict[u][1] = bandwidth * 1024
                await asyncio.sleep(0.9)# 调参所得
                logger.info(f'TOKEN produced for USER {u}, now remain TOKEN: {dict[u][1]}')
                logger.info(f'Now have enough TOKEN, time to continue')

        finally:
            dict[u][0].release()
            
# HTTP TUNNEL
async def HTTP_TUNNEL(reader, writer):
    try:
        mark = 0
        info = await reader.read(6000)
        u = info.decode().split()[0]
        p = info.decode().split()[1]
        logger.info(f'Login request from LocalProxy where user name:{u}')
        logger.info(f'Checking the SQLite3 database...')
        async with aiosqlite.connect('test.db') as db:
            async with db.execute("select name, password, bandwidth from user") as query:
                async for row in query:
                    if (str(row[0]) == u and str(row[1]) == p):
                        mark = 1
                        user_bandwidth = row[2]
                        if(dict.get(u) == None):
                            lock = asyncio.Lock()
                            dict[u] = [lock, user_bandwidth*1024]
                        logger.info(f'{dict[u][1]}')


        if (mark == 1):
            writer.write('Grant'.encode())
            await writer.drain()
            logger.info(f'Grant user {u} from LocalProxy, {u} with bandwidth:{user_bandwidth}')

            data = await reader.read(6000)
            data = data.decode()

            # 使用正则表达式
            pattern = 'CONNECT (.+):([0-9]+) (HTTP/\d\.\d)(.*)'

            match_result = re.match(pattern, data)
            if (match_result is None):
                logger.error(' wrong!')
                return
            url = match_result.group(1)
            port = match_result.group(2)
            http_version = match_result.group(3)
            logger.info('Request to ' + url + ':' + port + ' ' + http_version)
            dst_reader, dst_writer = await asyncio.open_connection(url, int(port))
            res = (http_version + ' 200 Connection Established' + '\r\n\r\n').encode()
            writer.write(res)
            await writer.drain()

            task1 = asyncio.create_task(dst(reader, dst_writer, user_bandwidth, u))
            task2 = asyncio.create_task(dst(dst_reader, writer, user_bandwidth, u))
            await task1
            await task2
            return
        else:
            writer.write('Reject'.encode())
            await writer.drain()
            logger.info(f'Access Denied, Username {u} or Password {p} wrong')


    except asyncio.IncompleteReadError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionResetError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionAbortedError as exc:
        raise MyError(logger.error(f'{exc}'))
    except OSError as exc:
        raise MyError(logger.error(f'{exc}'))
    return

# SOCKS5服务器
async def SOCKS5_server(reader, writer):
    try:
        mark = 0
        info = await reader.read(6000)
        u = info.decode().split()[0]
        p = info.decode().split()[1]
        logger.info(f'Login request from LocalProxy where user name:{u}')
        logger.info(f'Checking the SQLite3 database...')
        async with aiosqlite.connect('test.db') as db:
            async with db.execute("select name, password, bandwidth from user") as query:
                async for row in query:
                    if (str(row[0]) == u and str(row[1]) == p):
                        mark = 1
                        user_bandwidth = row[2]
                        if (dict.get(u) == None):
                            lock = asyncio.Lock()
                            dict[u] = [lock, user_bandwidth * 1024]
                        logger.info(f'{dict[u][1]}')


        if (mark == 1):
            writer.write('Grant'.encode())
            await writer.drain()
            logger.info(f'Grant user {u} from LocalProxy, {u} with bandwidth:{user_bandwidth}')
            recieved = await reader.readexactly(4)

            # 握手
            if recieved[1] != 1:
                writer.write(b'\05\02\00\01\00\00\00\00\00\00')  # 返回出错信息
                return

            # ipv4
            if recieved[3] == 1:
                addr = await reader.readexactly(4)
                addr = socket.inet_ntoa(addr)
                port = await reader.readexactly(2)
                port = struct.unpack('>H', port)
                port = port[0]

            # 域名
            elif recieved[3] == 3:
                domain_len = await reader.readexactly(1)
                domain_len = domain_len[0]
                addr = await reader.readexactly(domain_len)
                port = await reader.readexactly(2)
                port = struct.unpack('>H', port)
                port = port[0]

            # ipv6
            elif recieved[3] == 4:
                addr = await reader.readexactly(16)
                addr = socket.inet_ntop(socket.AF_INET6, addr)
                port = await reader.readexactly(2)
                port = struct.unpack('>H', port)
                port = port[0]

            # 均不是
            else:
                writer.write(b'\05\02\00\01\00\00\00\00\00\00')  # 返回出错信息
                await writer.drain()
                return
            # reader_host, writer_host = await asyncio.open_connection(addr, port)
            # 这里返回连接成功的消息，后面是127.0.0.1和端口1080
            writer.write(b'\05\00\00\01\127\00\00\01\x04\x38')
            await writer.drain()
            # 第三步转发
            dst_reader, dst_writer = await asyncio.open_connection(addr, port)
            task1 = asyncio.create_task(dst(reader, dst_writer, user_bandwidth, u))
            task2 = asyncio.create_task(dst(dst_reader, writer, user_bandwidth, u))
            await task1
            await task2
            return
        else:
            writer.write('Denied'.encode())
            await writer.drain()
            logger.info(f'Access Denied, Username {u} or Password {p} wrong')
    except asyncio.IncompleteReadError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionResetError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionAbortedError as exc:
        raise MyError(logger.error(f'{exc}'))
    except OSError as exc:
        raise MyError(logger.error(f'{exc}'))
    return
```

【文字描述】

- 与本地模块通信模块实现了用户登陆验证（数据库的创建与查询）解析来自本地模块的协议报文，返回相应消息，实现流量控制的功能。
- 接受来自本地发起的连接以后，首先对用户信息进行验证，对数据库进行查询，如果用户的用户名和密码均正确，则返回相应的信息确认连接（Grant）。
- 对首次进行连接的用户分配用户锁，一个用户一个锁，用于实现对用户所有连接的控制：

```python
# dict[u][0]是分配到的用户锁
# dict[u][1]是用户的带宽信息（从数据库读入的）
if (dict.get(u) == None):
    lock = asyncio.Lock()
    dict[u] = [lock, user_bandwidth * 1024]
    logger.info(f'{dict[u][1]}')
```

- 后面进行相关报文的解析：SOCKS5以及HTTP
- SOCKS5报文的解析：首先需要接收method消息，根据消息的不同类型返回选择的验证方式，然后接收cmd消息并解析其中内容，向外部服务器请求连接，连接成功创建异步作业task1和task2进行转发。
- HTTP报文的解析：可以从HTTP报文中解析得到url以及端口信息，从而进行连接，连接成功创建异步作业task1和task2进行转发。具体转发机制可以参考local端的讲解。



## 多用户管理

```python
# 数据库定义及数据导入
# 加入用户的带宽，管理员用户带宽很大
async def sql():
    findTable = False
    async with aiosqlite.connect('test.db') as db:
        async with db.execute("select name from sqlite_master where type='table' order by name;") as query:
            async for row in query:
                if (row[0] == 'user'):
                    findTable = True
        if findTable is False:
            await db.execute("create table user(name text primary key, password text not null, bandwidth int not null)")
            await db.commit()
            await db.execute("insert into user(name, password, bandwidth) values('Admin', '123456', 99999999)")
            await db.execute("insert into user(name, password, bandwidth) values('tyh', '123', 4096)")
            await db.execute("insert into user(name, password, bandwidth) values('u1', '11', 64)")
            await db.execute("insert into user(name, password, bandwidth) values('u2', '22', 512)")
            await db.execute("insert into user(name, password, bandwidth) values('u3', '33', 1024)")
            await db.commit()
```

```python
# 对请求登陆的用户进行验证：输入的用户名：u，输入的密码：p
logger.info(f'Login request from LocalProxy where user name:{u}')
        logger.info(f'Checking the SQLite3 database...')
        async with aiosqlite.connect('test.db') as db:
            async with db.execute("select name, password, bandwidth from user") as query:
                async for row in query:
                    if (str(row[0]) == u and str(row[1]) == p):
                        mark = 1
                        user_bandwidth = row[2]
                        if (dict.get(u) == None):
                            lock = asyncio.Lock()
                            dict[u] = [lock, user_bandwidth * 1024]
                        logger.info(f'{dict[u][1]}')
```

【文字描述】

#### 多用户管理模块给出了多用户的数据库表初始化的过程：原因如下

- 因为设计了用户数据库管理接口（REST），可以通过接口更加方便的对数据库中的用户进行增删改查的管理，但每个数据库都是需要进行一定的初始化的：如上面插入的Admin管理员用户，可供管理者进行服务器一些功能的测试与管理。
- 仅在没有找到数据库表的情况下创建一个新的表并初始化。

#### 验证过程介绍：

- 验证的主要流程其实很简单，就是利用用户的名称和密码在数据库中进行查询语句select，如果未查询到则返回错误信息，查询到则验证成功，执行后续步骤（连接）。
- 上面还给出了为不同用户加锁的过程，这样可以保证对用户带宽的限制是以用户本身为单位的，而不是以连接为单位，防止用户通过多个连接来突破带宽限制。且仅在用户的第一个连接请求时为用户加锁。



## 用户流控

```python
# 同目标服务器通信机制
async def dst(reader, writer, bandwidth, u):
    while True:
        data = await reader.read(dict[u][1])
        if len(data) == 0:
            raise MyError(logger.error("EOF"))
            return
        await dict[u][0].acquire()
        try:
            writer.write(data)
            await writer.drain()
            if (int(dict[u][1]) > len(data)):
                dict[u][1] = int(dict[u][1]) - len(data)
            logger.info(f'USER {u} TOKEN remain: {dict[u][1]}')
            if (dict[u][1] < bandwidth * 128):
                logger.info(f'TOKEN remain less than 1/8, produce TOKEN')
                dict[u][1] = bandwidth * 1024
                await asyncio.sleep(0.9)# 调参所得
                logger.info(f'TOKEN produced for USER {u}, now remain TOKEN: {dict[u][1]}')
                logger.info(f'Now have enough TOKEN, time to continue')

        finally:
            dict[u][0].release()
```

【文字描述】

- 之前在与本地模块通信模块说到，对首次进行连接的用户分配用户锁，一个用户一个锁，用于实现对用户所有连接的控制：

```python
# dict[u][0]是分配到的用户锁
# dict[u][1]是用户的带宽信息（从数据库读入的）
if (dict.get(u) == None):
    lock = asyncio.Lock()
    dict[u] = [lock, user_bandwidth * 1024]
    logger.info(f'{dict[u][1]}')
```

- 流控功能主要体现在dst协程函数中，前面讲解了用户锁机制，用于更改用户的令牌数量的时候不被其它协程影响。在dst函数中如果不加以限制，则会一直进行转发。我的流控机制是基于令牌桶算法的一种流控方法：用户的带宽，在每次转发消息以后减去转发消息的大小，在每次用户对应的令牌减少到一定数量时，为用户加满令牌（等于用户带宽），同时让转发协程sleep(0.9)，这样就实现了流控机制。
- 根据测试结果，流控效果良好且有效。



## 用户数据库管理接口

```python
import asyncio
import logging
import aiosqlite
from sanic import Sanic
from sanic.response import json
from sanic import response

app = Sanic("App Name")
app.config.host = 'localhost'
app.config.db = 'test.db'
app.config.u = 'user'

# 批量查询
@app.get('/userdb')
async def listAllUsers(request):
    allUsers = list()
    async with aiosqlite.connect(app.config.db) as db:
        async with db.execute("select name, password, bandwidth from user") as query:
            async for row in query:
                usersContent = {'name':row[0],
                           'password':row[1],
                           'bandwidth':row[2]}
                allUsers.append(usersContent)
    logger.info(f'List all users info')
    return response.json(allUsers)

# 单用户查询
@app.get('/userdb/<uname:string>')
async def listUser(request, uname):
    async with aiosqlite.connect(app.config.db) as db:
        async with db.execute("select name, password, bandwidth from user where name=?", (uname,)) as query:
            async for row in query:
                usersContent = {'name':row[0],
                           'password':row[1],
                           'bandwidth':row[2]}
    logger.info(f'List user {uname}\'s info')
    return response.json(usersContent)

# 单用户删除
@app.delete('/userdb/<uname:string>')
async def deleteUser(request, uname):
    async with aiosqlite.connect(app.config.db) as db:
        await db.execute("delete from user where name=?", (uname,))
        await db.commit()
    logger.info(f'Delete user {uname}\'s info')
    return response.text(f'User {uname}\'s info deleted')

# 插入单用户
@app.post('/userdb')
async def addUser(request):
    uname = request.json.get('name')
    password = request.json.get('password')
    bandwidth = request.json.get('bandwidth')
    if ((str(uname) is None) or (str(password) is None) or (str(bandwidth) is None)):
        logger.error(f'Invalid input, please make sure your input is complete')
    else:
        async with aiosqlite.connect(app.config.db) as db:
            await db.execute("insert into user(name, password, bandwidth) values(?, ?, ?)", (uname, password, bandwidth,))
            await db.commit()
        logger.info(f'insert user {uname}\'s info')
        return response.text(f'User {uname}\'s info inserted')

# 修改单用户
@app.put('/userdb/<uname>')
async def modifyUser(request, uname):
    password = request.json.get('password')
    bandwidth = request.json.get('bandwidth')
    if ((str(uname) is None) or (str(password) is None) or (str(bandwidth) is None)):
        logger.error(f'Invalid input, please make sure your input is complete')
    else:
        async with aiosqlite.connect(app.config.db) as db:
            await db.execute("update user set password=?, bandwidth=? where name=?", (password, bandwidth, uname,))
            await db.commit()
        logger.info(f'Modify user {uname}\'s info')
        return response.text(f'User {uname}\'s info modified')

if __name__ == "__main__":
    # create logger
    logger = logging.getLogger('DBController')
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    app.run(host="0.0.0.0", port=8000)

```

【文字描述】

- 上面代码实现了通过REST接口对数据库进行增删改查操作
- 使用sanic库，通过不同的路由选项，连接本地的数据库，实现了批量查询，单用户查询，单用户删除，单用户插入，单用户修改的操作。
- 对数据库的修改通过sqlite库以及相关的SQL语句实现。

- 批量查询：通过路由@app.get('/userdb')，以及SQL语句列出所有的用户信息(JSON格式)
- 单用户查询：通过路由@app.get('/userdb/<uname:string>')，以及SQL语句列出用户名为uname的用户的信息(JSON格式)
- 单用户删除：通过路由@app.delete('/userdb/<uname:string>')，以及SQL语句删除用户名为uname的用户的信息
- 单用户插入：通过路由@app.post('/userdb')，以及SQL语句插入以JSON格式保存的用户到数据库表中。
- 单用户修改：通过路由@app.put('/userdb/<uname>')，以及SQL语句，读入要修改的信息（以JSON格式存储）。修改用户名为uname的用户的信息。

# 程序完整源码

【此处根据个人具体情况粘贴程序源码，可以是单个文件或多个文件，但是只限于自己编写的源程序】

local.py 

```python
import asyncio
import logging
import os
import time
import websockets
import struct
import argparse
import random
import nest_asyncio
nest_asyncio.apply()

global guiLisPort
global remoteAdd
global remotePort
global sla
global slp
global hla
global hlp
global httpport
global sockport
global username
global password
global length
dict = {}
nowTime = 0
length = 0

# 错误处理机制
class MyError(Exception):
    pass

# 同目标服务器通信机制
# 在此计算吞吐率，利用锁机制互斥访问临界变量length
# 在此更新的吞吐率会定时发送给LocalGUI端并显示
async def dst(reader, writer):
    while True:
        data = await reader.read(6000)

        await dict[0][0].acquire()
        try:
            dict[0][1] = dict[0][1] + len(data)
        finally:
            dict[0][0].release()
        if len(data) == 0:
            raise MyError(logger.error("EOF"))
            return

        writer.write(data)
        await writer.drain()

# HTTP TUNNEL
# LocalProxy端，与客户端建立连接后，转发到RemoteProxy端，与Remote端建立连接
async def HTTP_TUNNEL(reader, writer):
    logger.info("HTTP_TUNNEL start")
    try:
        rm_reader, rm_writer = await asyncio.open_connection(remoteAdd, httpport)
        # 9934端口为Remote端设置的http监听端口
        logger.info(f'HTTP_TUNNEL open_connection({remoteAdd}, {httpport})')

        # 将命令行接收的用户名和密码发送至Remote端进行验证
        info = username + " " + password
        rm_writer.write(info.encode())
        await rm_writer.drain()
        logger.info(f'HTTP_TUNNEL send info to RemoteProxy which address is:{remoteAdd}, info: {info}')

        ans = await rm_reader.read(6000)
        if (ans.decode() != 'Grant'):
            logger.error(f'User {username} Access Denied, wrong username or password, please try again')
            exit(0)
        else:
            logger.info(f'Access Granted, user {username} successfully login')

        task1 = asyncio.create_task(dst(reader, rm_writer))
        task2 = asyncio.create_task(dst(rm_reader, writer))
        await task1
        await task2
    except asyncio.IncompleteReadError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionResetError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionAbortedError as exc:
        raise MyError(logger.error(f'{exc}'))

# SOCKS5服务器
# LocalProxy端，与客户端建立连接后，转发到RemoteProxy端，与RemoteProxy端建立连接
async def SOCKS5_server(reader, writer):
    logger.info("SOCKS5_server start")
    try:
        data = await reader.readexactly(2)
        method = await reader.readexactly(data[1])
        flag = False
        for i in range(0, data[1]):
            if (method[i] == 0):
                flag = True
                break
        if (not flag):
            return

        logger.info("Socks5 successfully shake hand")
        # METHOD 00
        writer.write(b'\05\00')
        await writer.drain()

        # CMD进行转发
        rm_reader, rm_writer = await asyncio.open_connection(remoteAdd, sockport)
        logger.info(f'SOCKS5_server open_connection({remoteAdd}, {sockport})')

        # 将命令行接收的用户名和密码发送至Remote端进行验证
        info = username + " " + password
        rm_writer.write(info.encode())
        await rm_writer.drain()
        logger.info(f'SOCKS5_server send info to RemoteProxy which address is:{remoteAdd}, info: {info}')

        ans = await rm_reader.read(6000)
        if(ans.decode() != 'Grant'):
            logger.error(f'User {username} Access Denied, wrong username or password, please try again')
            exit(0)
        else:
            logger.info(f'Access granted, user {username} successfully login')

        task1 = asyncio.create_task(dst(reader, rm_writer))
        task2 = asyncio.create_task(dst(rm_reader, writer))
        await task1
        await task2

    except asyncio.IncompleteReadError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionResetError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionAbortedError as exc:
        raise MyError(logger.error(f'{exc}'))

# 每个用户使用时执行localtask，实现用户间同时使用
async def localtask():
    # 在本地和remote服务器通信时端口设为1111测试使用，实际情况下为远程服务器地址和对应端口
    req_reader, req_writer = await asyncio.open_connection(remoteAdd, remotePort)

    info = remoteAdd + " " + str(httpport) + " " + str(sockport) + " " + str(username)
    req_writer.write(info.encode())
    await req_writer.drain()
    logger.info(f'User {username} request for addr:{remoteAdd}, HTTP port:{httpport}, SOCKS5 port:{sockport}')
    logger.info(f'HTTP TUNNEL listen address:{hla}, listen port:{hlp}')
    logger.info(f'SOCKS5 listen address:{sla}, SOCKS5 listen port:{slp}')

    sock = await asyncio.start_server(SOCKS5_server, sla, slp)
    task_sock = asyncio.create_task(sock.serve_forever())

    http = await asyncio.start_server(HTTP_TUNNEL, hla, hlp)
    task_http = asyncio.create_task(http.serve_forever())

    await task_sock
    await task_http

# 实时发送吞吐率到LocalGUI端
async def toLocalGUI(websocket, path):
    nowTime = 0
    data = await websocket.recv()
    if(data == 'CONNECT FROM LOCALGUI'):# 认证是来自LocalGUI的连接
        while True:
            if (time.time() - nowTime) > 1:
                nowTime = time.time()
                logger.info(f'THROUGHPUT:{dict[0][1]}')
                await websocket.send(str(dict[0][1]))
                await dict[0][0].acquire()
                try:
                    dict[0][1] = 0
                finally:
                    dict[0][0].release()
                await asyncio.sleep(1)
    else:
        await websocket.send("DENIED")

# 使用websocket与LocalGUI端进行连接
async def GUItask():
    start_server = websockets.serve(toLocalGUI, "127.0.0.1", guiLisPort)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

# 异步处理LocalProxy与RemoteProxy端传输以及LocalProxy与LocalGUI端传输
async def main():
    asyncio.create_task(localtask())
    asyncio.create_task(GUItask())

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    if (dict.get(0) == None):
        lock = asyncio.Lock()
        dict[0] = [lock, length]
    # 从命令行参数读入相关信息
    parser = argparse.ArgumentParser()
    parser.add_argument("-sla", "--sockListenAddress", type=str, default='127.0.0.1', help="listen address for SOCKS5 protocol")
    parser.add_argument("-slp", "--sockListenPort", type=str, default=1081, help="listen port for SOCKS5 protocol")
    parser.add_argument("-hla", "--httpListenAddress", type=str, default='127.0.0.1', help="listen address for HTTP Tunnel")
    parser.add_argument("-hlp", "--httpListenPort", type=str, default=11081, help="listen port for HTTP Tunnel")
    parser.add_argument("-rd", "--remoteAddress", type=str, default='127.0.0.1', help="Address of RemoteProxy")
    parser.add_argument("-rp", "--remotePort", type=str, default=1111, help="Port of RemoteProxy")
    parser.add_argument("-u", "--username", default='Admin', type=str, help="username")
    parser.add_argument("-p", "--password", default='123456', type=str, help="password")
    args = parser.parse_args()

    # 将从命令行读入的信息存储到变量中
    sla = args.sockListenAddress
    slp = args.sockListenPort
    hla = args.httpListenAddress
    hlp = args.httpListenPort
    remoteAdd = args.remoteAddress
    remotePort = args.remotePort
    username = args.username
    password = args.password

    # 利用随机数生成请求remote端分配的http端口和socks5端口
    port = random.sample(range(9000, 10000), 2)
    httpport = port[0]
    sockport = port[1]

    # 与LocalGUI端通信用端口
    guiLisPort = 8765

    # create logger
    logger = logging.getLogger('LocalProxy')
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    # 运行
    asyncio.run(main())

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
```

localGui.py

```python
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
```

remote.py

```python
import asyncio
import socket
import struct
import aiosqlite
import logging
import re
dict = {}

class MyError(Exception):
    pass

# 同目标服务器通信机制
async def dst(reader, writer, bandwidth, u):
    while True:
        data = await reader.read(dict[u][1])
        if len(data) == 0:
            raise MyError(logger.error("EOF"))
            return
        await dict[u][0].acquire()
        try:
            writer.write(data)
            await writer.drain()
            if (int(dict[u][1]) > len(data)):
                dict[u][1] = int(dict[u][1]) - len(data)
            logger.info(f'USER {u} TOKEN remain: {dict[u][1]}')
            if (dict[u][1] < bandwidth * 128):
                logger.info(f'TOKEN remain less than 1/8, produce TOKEN')
                dict[u][1] = bandwidth * 1024
                await asyncio.sleep(0.9)# 调参所得
                logger.info(f'TOKEN produced for USER {u}, now remain TOKEN: {dict[u][1]}')
                logger.info(f'Now have enough TOKEN, time to continue')

        finally:
            dict[u][0].release()


# 数据库定义及数据导入
# 加入用户的带宽，管理员用户带宽很大
async def sql():
    findTable = False
    async with aiosqlite.connect('test.db') as db:
        async with db.execute("select name from sqlite_master where type='table' order by name;") as query:
            async for row in query:
                if (row[0] == 'user'):
                    findTable = True
        if findTable is False:
            await db.execute("create table user(name text primary key, password text not null, bandwidth int not null)")
            await db.commit()
            await db.execute("insert into user(name, password, bandwidth) values('Admin', '123456', 99999999)")
            await db.execute("insert into user(name, password, bandwidth) values('tyh', '123', 4096)")
            await db.execute("insert into user(name, password, bandwidth) values('u1', '11', 64)")
            await db.execute("insert into user(name, password, bandwidth) values('u2', '22', 512)")
            await db.execute("insert into user(name, password, bandwidth) values('u3', '33', 1024)")
            await db.commit()




# HTTP TUNNEL
async def HTTP_TUNNEL(reader, writer):
    try:
        mark = 0
        info = await reader.read(6000)
        u = info.decode().split()[0]
        p = info.decode().split()[1]
        logger.info(f'Login request from LocalProxy where user name:{u}')
        logger.info(f'Checking the SQLite3 database...')
        async with aiosqlite.connect('test.db') as db:
            async with db.execute("select name, password, bandwidth from user") as query:
                async for row in query:
                    if (str(row[0]) == u and str(row[1]) == p):
                        mark = 1
                        user_bandwidth = row[2]
                        if(dict.get(u) == None):
                            lock = asyncio.Lock()
                            dict[u] = [lock, user_bandwidth*1024]
                        logger.info(f'{dict[u][1]}')


        if (mark == 1):
            writer.write('Grant'.encode())
            await writer.drain()
            logger.info(f'Grant user {u} from LocalProxy, {u} with bandwidth:{user_bandwidth}')

            data = await reader.read(2048)
            data = data.decode()

            # re
            pattern = 'CONNECT (.+):([0-9]+) (HTTP/\d\.\d)(.*)'

            match_result = re.match(pattern, data)
            if (match_result is None):
                logger.error(' wrong!')
                return
            url = match_result.group(1)
            port = match_result.group(2)
            http_version = match_result.group(3)
            logger.info('Request to ' + url + ':' + port + ' ' + http_version)
            dst_reader, dst_writer = await asyncio.open_connection(url, int(port))
            res = (http_version + ' 200 Connection Established' + '\r\n\r\n').encode()
            writer.write(res)
            await writer.drain()

            task1 = asyncio.create_task(dst(reader, dst_writer, user_bandwidth, u))
            task2 = asyncio.create_task(dst(dst_reader, writer, user_bandwidth, u))
            await task1
            await task2
            return
        else:
            writer.write('Reject'.encode())
            await writer.drain()
            logger.info(f'Access Denied, Username {u} or Password {p} wrong')


    except asyncio.IncompleteReadError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionResetError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionAbortedError as exc:
        raise MyError(logger.error(f'{exc}'))
    except OSError as exc:
        raise MyError(logger.error(f'{exc}'))
    return

# SOCKS5服务器
async def SOCKS5_server(reader, writer):
    try:
        mark = 0
        info = await reader.read(6000)
        u = info.decode().split()[0]
        p = info.decode().split()[1]
        logger.info(f'Login request from LocalProxy where user name:{u}')
        logger.info(f'Checking the SQLite3 database...')
        async with aiosqlite.connect('test.db') as db:
            async with db.execute("select name, password, bandwidth from user") as query:
                async for row in query:
                    if (str(row[0]) == u and str(row[1]) == p):
                        mark = 1
                        user_bandwidth = row[2]
                        if (dict.get(u) == None):
                            lock = asyncio.Lock()
                            dict[u] = [lock, user_bandwidth * 1024]
                        logger.info(f'{dict[u][1]}')


        if (mark == 1):
            writer.write('Grant'.encode())
            await writer.drain()
            logger.info(f'Grant user {u} from LocalProxy, {u} with bandwidth:{user_bandwidth}')
            recieved = await reader.readexactly(4)

            # 握手
            if recieved[1] != 1:
                writer.write(b'\05\02\00\01\00\00\00\00\00\00')  # 返回出错信息
                return

            # ipv4
            if recieved[3] == 1:
                addr = await reader.readexactly(4)
                addr = socket.inet_ntoa(addr)
                port = await reader.readexactly(2)
                port = struct.unpack('>H', port)
                port = port[0]

            # 域名
            elif recieved[3] == 3:
                domain_len = await reader.readexactly(1)
                domain_len = domain_len[0]
                addr = await reader.readexactly(domain_len)
                port = await reader.readexactly(2)
                port = struct.unpack('>H', port)
                port = port[0]

            # ipv6
            elif recieved[3] == 4:
                addr = await reader.readexactly(16)
                addr = socket.inet_ntop(socket.AF_INET6, addr)
                port = await reader.readexactly(2)
                port = struct.unpack('>H', port)
                port = port[0]

            # 均不是
            else:
                writer.write(b'\05\02\00\01\00\00\00\00\00\00')  # 返回出错信息
                await writer.drain()
                return
            # reader_host, writer_host = await asyncio.open_connection(addr, port)
            # 这里返回连接成功的消息，后面是127.0.0.1和端口1080
            writer.write(b'\05\00\00\01\127\00\00\01\x04\x38')
            await writer.drain()
            # 第三步转发
            dst_reader, dst_writer = await asyncio.open_connection(addr, port)
            task1 = asyncio.create_task(dst(reader, dst_writer, user_bandwidth, u))
            task2 = asyncio.create_task(dst(dst_reader, writer, user_bandwidth, u))
            await task1
            await task2
            return
        else:
            writer.write('Denied'.encode())
            await writer.drain()
            logger.info(f'Access Denied, Username {u} or Password {p} wrong')
    except asyncio.IncompleteReadError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionResetError as exc:
        raise MyError(logger.error(f'{exc}'))
    except ConnectionAbortedError as exc:
        raise MyError(logger.error(f'{exc}'))
    except OSError as exc:
        raise MyError(logger.error(f'{exc}'))
    return

async def remotetask(address, h, s):
    logger.info(f'addr:{address}, HTTP port:{h}, SOCKS5 port:{s}')

    sock = await asyncio.start_server(SOCKS5_server, address, int(s))
    task_sock = asyncio.create_task(sock.serve_forever())

    http = await asyncio.start_server(HTTP_TUNNEL, address, int(h))
    task_http = asyncio.create_task(http.serve_forever())

    await task_sock
    await task_http


async def doLocalRequest(reader, writer):
    data = await reader.read(6000)
    addr = data.decode().split()[0]
    hport = data.decode().split()[1]
    sport = data.decode().split()[2]
    user = data.decode().split()[3]
    logger.info(f'Request from {user} apply for addr:{addr}, HTTP port:{hport}, SOCKS5 port:{sport}')

    asyncio.create_task(remotetask(addr, hport, sport))


async def main():
    task1 = asyncio.create_task(sql())
    await task1
    logger.info("successfully load data into SQLite3")

    # 为本机设定的统一处理请求端口1111，实际情况下为实际ip和端口
    doReq = await asyncio.start_server(doLocalRequest, '127.0.0.1', 1111)
    async with doReq:
        await doReq.serve_forever()

    while True:
        await asyncio.sleep(1)

if __name__ == '__main__':
    # create logger
    logger = logging.getLogger('RemoteProxy')
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)
    dict.clear()
    asyncio.run(main())
```

remoteRest.py

```python
import asyncio
import logging
import aiosqlite
from sanic import Sanic
from sanic.response import json
from sanic import response

app = Sanic("App Name")
app.config.host = 'localhost'
app.config.db = 'test.db'
app.config.u = 'user'

# 批量查询
@app.get('/userdb')
async def listAllUsers(request):
    allUsers = list()
    async with aiosqlite.connect(app.config.db) as db:
        async with db.execute("select name, password, bandwidth from user") as query:
            async for row in query:
                usersContent = {'name':row[0],
                           'password':row[1],
                           'bandwidth':row[2]}
                allUsers.append(usersContent)
    logger.info(f'List all users info')
    return response.json(allUsers)

# 单用户查询
@app.get('/userdb/<uname:string>')
async def listUser(request, uname):
    async with aiosqlite.connect(app.config.db) as db:
        async with db.execute("select name, password, bandwidth from user where name=?", (uname,)) as query:
            async for row in query:
                usersContent = {'name':row[0],
                           'password':row[1],
                           'bandwidth':row[2]}
    logger.info(f'List user {uname}\'s info')
    return response.json(usersContent)

# 单用户删除
@app.delete('/userdb/<uname:string>')
async def deleteUser(request, uname):
    async with aiosqlite.connect(app.config.db) as db:
        await db.execute("delete from user where name=?", (uname,))
        await db.commit()
    logger.info(f'Delete user {uname}\'s info')
    return response.text(f'User {uname}\'s info deleted')

# 插入单用户
@app.post('/userdb')
async def addUser(request):
    uname = request.json.get('name')
    password = request.json.get('password')
    bandwidth = request.json.get('bandwidth')
    if ((str(uname) is None) or (str(password) is None) or (str(bandwidth) is None)):
        logger.error(f'Invalid input, please make sure your input is complete')
    else:
        async with aiosqlite.connect(app.config.db) as db:
            await db.execute("insert into user(name, password, bandwidth) values(?, ?, ?)", (uname, password, bandwidth,))
            await db.commit()
        logger.info(f'insert user {uname}\'s info')
        return response.text(f'User {uname}\'s info inserted')

# 修改单用户
@app.put('/userdb/<uname>')
async def modifyUser(request, uname):
    password = request.json.get('password')
    bandwidth = request.json.get('bandwidth')
    if ((str(uname) is None) or (str(password) is None) or (str(bandwidth) is None)):
        logger.error(f'Invalid input, please make sure your input is complete')
    else:
        async with aiosqlite.connect(app.config.db) as db:
            await db.execute("update user set password=?, bandwidth=? where name=?", (password, bandwidth, uname,))
            await db.commit()
        logger.info(f'Modify user {uname}\'s info')
        return response.text(f'User {uname}\'s info modified')

if __name__ == "__main__":
    # create logger
    logger = logging.getLogger('DBController')
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)

    app.run(host="0.0.0.0", port=8000)

```

