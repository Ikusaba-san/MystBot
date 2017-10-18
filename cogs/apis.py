import discord
from discord.ext import commands

import configparser
import datetime
import random
import humanize as humnum


class Colour:
    """Colour related commands. More coming soon...™"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='colour', aliases=['color', 'col'])
    async def show_colour(self, ctx, colour: str):
        """Display a colour and popular scheme, from a HEX or RGB."""

        if ctx.message.mentions:
            colour = ctx.message.mentions[0].colour
        else:
            colour = colour.strip('#').strip('0x').replace(' ', ',')

        base = 'http://www.thecolorapi.com/id?format=json&hex={}'
        basep = 'http://www.colourlovers.com/api/palettes?hex={}&format=json'

        if ',' in colour:
            rgb = tuple(map(int, colour.split(',')))
            for x in rgb:
                if x < 0 or x > 255:
                    return await ctx.send('You have entered an invalid colour. Try entering a Hex-Code or R,G,B')
            colour = '%02x%02x%02x' % rgb

        url = base.format(colour)
        urlp = basep.format(colour)

        try:
            resp, data = await self.bot.fetch(url, return_type='json')
        except:
            return await ctx.send('There was a problem with the request. Please try again.')
        else:
            if resp.status > 300:
                return await ctx.send('There was a problem with the request. Please try again.')

        try:
            data['code']
        except KeyError:
            pass
        else:
            return await ctx.send('You have entered an invalid colour. Try entering a Hex-Code or R,G,B')

        try:
            resp, datap = await self.bot.fetch(urlp, return_type='json')
        except:
            pass

        try:
            image = datap[0]['imageUrl']
            colours = datap[0]['colors']
        except:
            image = f'https://dummyimage.com/300/{data["hex"]["clean"]}.png'
            colours = None

        emcol = f"0x{data['hex']['clean']}"
        embed = discord.Embed(title=f'Colour - {data["name"]["value"]}', colour=int(emcol, 0))
        embed.set_thumbnail(url=f'https://dummyimage.com/150/{data["hex"]["clean"]}.png')
        embed.set_image(url=image)
        embed.add_field(name='HEX', value=f'{data["hex"]["value"]}')
        embed.add_field(name='RGB', value=f'{data["rgb"]["value"]}')
        embed.add_field(name='HSL', value=f'{data["hsl"]["value"]}')
        embed.add_field(name='HSV', value=f'{data["hsv"]["value"]}')
        embed.add_field(name='CMYK', value=f'{data["cmyk"]["value"]}')
        embed.add_field(name='XYZ', value=f'{data["XYZ"]["value"]}')
        if colours:
            embed.add_field(name='Scheme:', value=' | '.join(colours), inline=False)

        await ctx.send(content=None, embed=embed)


class Dofus:
    """Commands from the World of Twelve."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='th', invoke_without_command=True)
    @commands.guild_only()
    async def dofus_th(self, ctx, *, search: str):
        """Search DofusGO for Treasure Hunt Clues."""

        base = 'https://dofusgo.com/api/pois?clueName={}'.format(search.replace(' ', '%20'))

        async with ctx.typing():
            try:
                resp, data = await self.bot.fetch(base, return_type='json')
            except Exception as e:
                print(e)
                return await ctx.send('Sorry **DofusGo** is currently experiencing difficulties. Try again later.')

        try:
            urldata = data[0]['nameId']
        except (IndexError, KeyError):
            return await ctx.send(f'**Sorry I found no results for:**   __{search.upper()}__')

        result = f'https://dofusgo.com/app/clues/{urldata}'
        await ctx.send(f'**Search results for:**   {search.upper()}\n{result}')

        db = self.bot.dbc['th'][str(ctx.guild.id)]

        await db.update_one({'_id': '_total'}, {'$inc': {'_uses': +1}}, upsert=True)
        await db.update_one({'_id': search.lower()}, {'$inc': {'searches': +1, str(ctx.author.id): +1}}, upsert=True)
        await db.update_one({'_id': ctx.author.id}, {'$inc': {'uses': +1}}, upsert=True)

    @dofus_th.command(name='stats')
    @commands.guild_only()
    async def th_stats(self, ctx, *, member: discord.Member=None):
        """Guild Treasure Hunt Statistics."""

        db = self.bot.dbc['th'][str(ctx.guild.id)]

        if member is not None:

            embed = discord.Embed(title='Treasure Hunt Stats', description=ctx.guild.name, colour=0x98629d)
            embed.set_thumbnail(url='http://i.imgur.com/ZyJLw6U.png')
            embed.set_author(name=member.name, icon_url=member.avatar_url)

            try:
                cursor = await db.find().sort(str(member.id), -1).to_list(length=100000)
                uses = await db.find_one({'_id': member.id})
                rank = await db.find({'uses': {'$gt': 0}}).sort('uses', -1).to_list(length=100000)
                count = 0
                for x in rank:
                    count += 1
                    if x['_id'] == member.id:
                        break

                embed.add_field(name='Most Searched', value=f'{cursor[0]["_id"]} - ({cursor[0][str(member.id)]})')
                embed.add_field(name='Total Searches', value=f'{uses["uses"]}')
                embed.add_field(name='Rank', value=f'{humnum.ordinal(count)} out of {len(rank)}')
            except:
                return await ctx.send(f'**No TH stats for {member.name}**')
            else:
                return await ctx.send(content=None, embed=embed)

        try:
            total = await db.find_one({'_id': '_total'})
            searched = await db.find({'searches': {'$gt': 0}}).sort('searches', -1).to_list(length=10000)
            unique = len(searched)
            rank = await db.find({'uses': {'$gt': 0}}).sort('uses', -1).to_list(length=100000)
            ranked = ctx.guild.get_member(rank[0]['_id'])

            embed = discord.Embed(title='Treasure Hunt Stats', description=f'{ctx.guild.name}', colour=0x98629d)
            embed.set_thumbnail(url='http://i.imgur.com/ZyJLw6U.png')
            embed.add_field(name='Total Searches', value=f'{total["_uses"]}')
            embed.add_field(name='Unique Searches', value=f'{unique}')
            embed.add_field(name='Most Searched', value=f'{searched[0]["_id"]}')
            embed.add_field(name='Top Rank', value=ranked.mention)
        except:
            return await ctx.send(f'**No TH stats for your {ctx.guild.name}**')
        await ctx.send(content=None, embed=embed)

    @commands.command(name='dofus')
    @commands.guild_only()
    async def dofus_wikia_search(self, ctx, *, search: str):
        """Search the Dofus Wiki for the top 3 results."""
        # todo Clean this mess.

        search = search.replace(' ', '+')

        api_url = 'http://dofuswiki.wikia.com/api/v1/Search/List?' \
                  'query={}' \
                  '&rank=default' \
                  '&limit=3' \
                  '&minArticleQuality=20' \
                  '&batch=1' \
                  '&namespaces=0%2C14'.format(search)

        async with ctx.typing():
            try:
                resp, urldata = await self.bot.fetch(api_url, return_type='json')
            except:
                return await ctx.send('Sorry there was an error with your request. Please try again.')

            if 'exception' in urldata:
                return await ctx.send(f'**Sorry I found no results for:**   __{search.upper()}__')

            urls = [x['url'] for x in urldata['items']]
            titles = [x['title'] for x in urldata['items']]

            if len(urls) == 1:
                return await ctx.send(f'**{titles[0]}**:\n{urls[0]}')

            count = 1
            send_list = []
            for x in urls[1:]:
                send_list.extend((['{} - <{}>'.format(titles[count], x)]))
                count += 1
            send_list = '\n'.join(send_list)
            await ctx.send(f'**{titles[0]}**:\n{urls[0]}\n\n**See also:**\n{send_list}')


class Observations:
    """Various Observation commands including NASA, Weather and more."""
    def __init__(self, bot):
        self.bot = bot
        key = configparser.ConfigParser()
        key.read('/home/myst/mystbot/mystconfig.ini')  # !!!VPS!!!
        self._nasa_key = key.get("NASA", "_key")

    @commands.group(invoke_without_command=True)
    async def nasa(self, ctx):
        """Various Commands to access Photos and Information from NASA."""
        pass

    @nasa.command(name='curiosity')
    async def curiosity_photos(self, ctx, camerainp: str = None, date: str = None):
        """Retrieve photos from Mars Rover: Curiosity.

        If date is None, the latest photos will be returned. A date is not guaranteed to have photos.
        If camera is None, a random camera will be chosen. A camera is not guaranteed to have photos.

        Cameras: [FHAZ     : Front Hazard Avoidance Camera]
                 [RHAZ     : Rear Hazard Avoidance Camera]
                 [MAST     : Mast Camera]
                 [CHEMCAM  : Chemistry and Camera Complex]
                 [MAHLI    : Mars Hand Lens Imager]
                 [MARDI    : Mars Descent Imager]
                 [NAVCAM   : Navigation Camera]
                 """

        base = 'https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?sol={}&camera={}&api_key={}'
        basenc = 'https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?sol={}&api_key={}'

        cameras = ['fhaz', 'rhaz', 'mast', 'chemcam', 'mahli', 'mardt', 'mardi', 'navcam']

        if camerainp is None:
            camera = 'none'
        else:
            camera = camerainp.lower()

        if camerainp and camerainp.lower() != 'none':

            if camera not in cameras:
                return await ctx.send('You have entered an invalid camera. Valid Cameras:\n'
                                      '```ini\n'
                                      '[FHAZ     : Front Hazard Avoidance Camera]\n'
                                      '[RHAZ     : Rear Hazard Avoidance Camera]\n'
                                      '[MAST     : Mast Camera]\n'
                                      '[CHEMCAM  : Chemistry and Camera Complex]\n'
                                      '[MAHLI    : Mars Hand Lens Imager]\n'
                                      '[MARDI    : Mars Descent Imager]\n'
                                      '[NAVCAM   : Navigation Camera]\n'
                                      '```')

        if date is None or date == 'random':

            url = f'https://api.nasa.gov/mars-photos/api/v1/manifests/Curiosity/?max_sol&api_key={self._nasa_key}'
            try:
                res, sol = await self.bot.fetch(url=url, timeout=15, return_type='json')
            except:
                return await ctx.send('There was an error with your request. Please try again later.')

            if date == 'random':
                if camera and camera != 'none':
                    base = base.format(random.randint(0, sol["photo_manifest"]["max_sol"]), camera, self._nasa_key)
                else:
                    base = basenc.format(random.randint(0, sol["photo_manifest"]["max_sol"]), self._nasa_key)
            else:
                if camera and camera != 'none':
                    base = base.format(sol["photo_manifest"]["max_sol"], camera, self._nasa_key)
                else:
                    base = basenc.format(sol["photo_manifest"]["max_sol"], self._nasa_key)
            date = sol["photo_manifest"]["max_sol"]
        else:
            if camera and camera != 'none':
                base = f'https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?' \
                       f'earth_date={date}' \
                       f'&camera={camera}' \
                       f'&api_key={self._nasa_key}'
            else:
                base = f'https://api.nasa.gov/mars-photos/api/v1/rovers/curiosity/photos?' \
                       f'earth_date={date}' \
                       f'&api_key={self._nasa_key}'

        try:
            res, data = await self.bot.fetch(base, timeout=15, return_type='json')
        except:
            return await ctx.send('There was an error with your request. Please try again later.')

        if len(data['photos']) <= 0:
            return await ctx.send(f'There was no photos available on date/sol'
                                  f' `{date}` with camera `{camera.upper() if camera else "NONE"}`.')

        photos = data['photos']
        main_img = random.choice(photos)

        if len(photos) > 4:
            photos = random.sample(photos, 4)

        embed = discord.Embed(title='NASA Rover: Curiosity', description=f'Date/SOL: {date}', colour=0xB22E20)
        embed.set_image(url=main_img['img_src'])
        embed.add_field(name='Camera', value=camera.upper())
        embed.add_field(name='See Also:',
                        value='\n'.join(x['img_src'] for x in photos[:3]) if len(photos) > 3 else 'None',
                        inline=False)
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text='Generated on ')
        await ctx.send(content=None, embed=embed)

    @nasa.command(name='apod', aliases=['iotd'])
    async def nasa_apod(self, ctx):
        """Returns NASA's Astronomy Picture of the day."""
        # todo Add the ability to select a date.

        url = f'https://api.nasa.gov/planetary/apod?api_key={self._nasa_key}'
        try:
            res, data = self.bot.fetch(url=url, timeout=15, return_type='json')
        except:
            return await ctx.send('There was an error processing your request')

        embed = discord.Embed(title='Astronomy Picture of the Day',
                              description=f'**{data["title"]}** | {data["date"]}',
                              colour=0x1d2951)
        embed.add_field(name='Explanation',
                        value=data['explanation'] if len(data['explanation']) < 1024
                        else f"{data['explanation'][:1020]}...", inline=False)
        embed.add_field(name='HD Download', value=f'[Click here!]({data["hdurl"]})')
        embed.set_image(url=data['url'])
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text='Generated on ')

        await ctx.send(content=None, embed=embed)

    @nasa.command(name='epic', aliases=['EPIC'])
    async def nasa_epic(self, ctx):
        """Returns NASA's most recent EPIC image."""
        # todo Add the ability to select a date.

        base = f'https://api.nasa.gov/EPIC/api/natural?api_key={self._nasa_key}'
        img_base = 'https://epic.gsfc.nasa.gov/archive/natural/{}/png/{}.png'

        try:
            res, data = await self.bot.fetch(base, timeout=15, return_type='json')
        except:
            return await ctx.send('There was an error processing your request. Please try again.')

        img = random.choice(data)
        coords = img['centroid_coordinates']

        embed = discord.Embed(title='NASA EPIC', description=f'*{img["caption"]}*', colour=0x1d2951)
        embed.set_image(url=img_base.format(img['date'].split(' ')[0].replace('-', '/'), img['image']))
        embed.add_field(name='Centroid Coordinates',
                        value=f'Lat: {coords["lat"]} | Lon: {coords["lon"]}')
        embed.add_field(name='Download',
                        value=img_base.format(img['date'].split(' ')[0].replace('-', '/'), img['image']))
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text='Generated on ')

        await ctx.send(content=None, embed=embed)


def setup(bot):
    bot.add_cog(Colour(bot))
    bot.add_cog(Observations(bot))
    bot.add_cog(Dofus(bot))
