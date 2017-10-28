from asyncqlio.db import DatabaseInterface
import asyncio

db = DatabaseInterface('postgresql+asyncpg://postgres:myst@127.0.0.1:5432/mysterial')


class DBTest:

    def __init__(self):
        self.db = db

    async def db_test(self):
        await self.db.connect()

        async with self.db.get_session() as session:

            selc = await session.cursor("""SELECT prefix FROM mysterialbot.prefixes WHERE guild_id IN (328873861481365514);""")
            things = await selc.fetch_many(n=10000)
            print(things[0]['prefix'])
            if things[0]['exists'] is True:
                print('Working')
                print(things)


test = DBTest()
asyncio.get_event_loop().run_until_complete(test.db_test())
