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