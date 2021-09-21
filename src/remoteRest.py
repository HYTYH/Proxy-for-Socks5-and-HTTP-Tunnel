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
