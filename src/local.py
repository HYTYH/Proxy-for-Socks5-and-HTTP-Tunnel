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
        writer.write(b'\\05\\00')
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