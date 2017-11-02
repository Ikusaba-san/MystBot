from asyncqlio.db import DatabaseInterface
import asyncio

db = DatabaseInterface('postgresql+asyncpg://postgres:myst@127.0.0.1:5432/mysterial')


class DBTest:

    def __init__(self):
        self.db = db

    async def db_test(self):
        await self.db.connect()

        async with self.db.get_session() as session:

            await session.execute("""CREATE TABLE prefixes(
            guild_id BIGINT PRIMARY KEY,
            entries TEXT[25]);
            
            CREATE TABLE blocks(
            user_id BIGINT PRIMARY KEY,
            user_name TEXT NOT NULL,
            time TIMESTAMP);
            
            CREATE TABLE statistics(
            name VARCHAR(50) UNIQUE NOT NULL,
            count INT,
            other VARCHAR(100)
            )""")


test = DBTest()
asyncio.get_event_loop().run_until_complete(test.db_test())
