from datetime import datetime
import calendar
import nextcord
from nextcord.ext import commands
from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import configparser

config = configparser.ConfigParser()
config.read('config.properties')
MONGO_DB_URL = config['MONGO']['DB_URL']
DISCORD_COMMAND_PREFIX = config['DISCORD']['COMMAND_PREFIX']
DISCORD_OWNER_ID = int(config['DISCORD']['OWNER_ID'])
DISCORD_MBD_ID = int(config['DISCORD']['MBD_ID'])
DISCORD_REGULAR_ROLE_ID = int(config['DISCORD']['REGULAR_ROLE_ID'])
DISCORD_MOD_ROLE_ID = int(config['DISCORD']['MOD_ROLE_ID'])
DISCORD_BOT_SECRET = config['DISCORD']['BOT_SECRET']

mongo = MongoClient(MONGO_DB_URL)
db = mongo.mbd
print(db.users.find_one())

intents = nextcord.Intents.default()
intents.members = True
intents.messages = True
intents.typing = False
intents.presences = False
bot = commands.Bot(command_prefix=DISCORD_COMMAND_PREFIX, intents=intents, owner_id=DISCORD_OWNER_ID)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name='reload-regs')
async def reloadRegulars(ctx):
    isOwner = await bot.is_owner(ctx.author);
    if isOwner:
        currentRegs = ctx.guild.get_role(DISCORD_REGULAR_ROLE_ID).members
        actualRegs = currentRegs
        # This is so stupid but it works so whatever
        for x in range(0, 2):
            for reg in currentRegs:
                if reg in ctx.guild.get_role(DISCORD_MOD_ROLE_ID).members:
                    actualRegs.remove(reg)
        regsFilter = []
        for member in actualRegs:
            if db.regulars.find_one({'discord_id': str(member.id)}) == None:
                db.regulars.insert_one({'discord_id': str(member.id), 'joined_guild_at': member.joined_at})
                print(f'New Regular Alert! Added {member} ({member.id})!')
            regsFilter.append({'discord_id': {'$eq': str(member.id)}})
        
        for doc in db.regulars.find({'$nor': regsFilter}):
            deleted_reg = db.regulars.find_one_and_delete({'_id': doc['_id']})
            deleted_id = str(deleted_reg['discord_id'])
            print(f'Removed {deleted_id} from the regulars collection')

@bot.command(name='check-user')
async def checkuser(ctx, arg1, arg2):
    isOwner = await bot.is_owner(ctx.author);
    if isOwner:
        print(bot.get_guild(DISCORD_MBD_ID).get_member(int(arg2)))
        if bot.get_guild(DISCORD_MBD_ID).get_member(int(arg2)) == None:
            print(f'Could not find user with ID {arg2}')
            await ctx.send(f'Could not find user with ID {arg2}')
            return

        if arg1 == 'all':
            countDocs = db.messages.count_documents({'user_id': str(arg2)})
            print(f'Number of messages (all-time) by {arg2}: {countDocs}')
            await ctx.send(f'Number of messages (all-time) by {arg2}: {countDocs}')
            return
        elif arg1 == 'this-month':
            currentYear = datetime.now().year
            currentMonth = datetime.now().month
            lastDay = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
            countDocs = db.messages.count_documents({'user_id': str(arg2), 'created_at': {'$gte': datetime(currentYear, currentMonth, 1), '$lt': datetime(currentYear, currentMonth, lastDay)}})
            print(f'Number of messages (current month) by {arg2}: {countDocs}')
            await ctx.send(f'Number of messages (current month) by {arg2}: {countDocs}')
            return
        elif arg1 == 'last-month':
            currentYear = datetime.now().year
            currentMonth = datetime.now().month
            lastMonth = 0
            lastMonthsYear = 0
            if currentMonth == 1:
                lastMonth = 12
                lastMonthsYear = currentYear - 1
            else:
                lastMonth = currentMonth - 1
                lastMonthsYear = currentYear
            lastDay = calendar.monthrange(lastMonthsYear, lastMonth)[1]
            countDocs = db.messages.count_documents({'user_id': str(arg2), 'created_at': {'$gte': datetime(lastMonthsYear, lastMonth, 1), '$lt': datetime(lastMonthsYear, lastMonth, lastDay)}})
            print(f'Number of messages (last month) by {arg2}: {countDocs}')
            await ctx.send(f'Number of messages (last month) by {arg2}: {countDocs}')
            return

@bot.command(name='check-regulars')
async def checkRegs(ctx, arg1):
    isOwner = await bot.is_owner(ctx.author);
    if isOwner:
        overallMessage = []
        df = pd.DataFrame({
            'Username': [],
            'DiscordID': [],
            'MessageCount': []
        })
        for document in db.regulars.find({}):
            userID = document['discord_id']
            discordUser = bot.get_guild(DISCORD_MBD_ID).get_member(int(userID))

            if arg1 == 'all':
                countDocs = db.messages.count_documents({'user_id': str(userID)})
                overallMessage.append(f'Number of messages (all-time) by {discordUser} ({userID}): {countDocs} \n')
            elif arg1 == 'this-month':
                currentYear = datetime.now().year
                currentMonth = datetime.now().month
                lastDay = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
                countDocs = db.messages.count_documents({'user_id': str(userID), 'created_at': {'$gte': datetime(currentYear, currentMonth, 1), '$lt': datetime(currentYear, currentMonth, lastDay)}})
                overallMessage.append(f'Number of messages (current month) by {discordUser} ({userID}): {countDocs} \n')
                df = df.append({'Username': str(discordUser.name), 'DiscordID': str(userID), 'MessageCount': int(countDocs)}, ignore_index=True)
            elif arg1 == 'last-month':
                currentYear = datetime.now().year
                currentMonth = datetime.now().month
                lastMonth = 0
                lastMonthsYear = 0
                if currentMonth == 1:
                    lastMonth = 12
                    lastMonthsYear = currentYear - 1
                else:
                    lastMonth = currentMonth - 1
                    lastMonthsYear = currentYear
                lastDay = calendar.monthrange(lastMonthsYear, lastMonth)[1]
                countDocs = db.messages.count_documents({'user_id': str(userID), 'created_at': {'$gte': datetime(lastMonthsYear, lastMonth, 1), '$lt': datetime(lastMonthsYear, lastMonth, lastDay)}})
                overallMessage.append(f'Number of messages (last month) by {discordUser} ({userID}): {countDocs} \n')
                df = df.append({'Username': str(discordUser.name), 'DiscordID': str(userID), 'MessageCount': int(countDocs)}, ignore_index=True)
        finalMessage = ''
        for line in overallMessage:
            finalMessage += line
            if len(finalMessage) >= 1750:
                await ctx.send(finalMessage)
                finalMessage = ''
        if finalMessage:
            await ctx.send(finalMessage)
        df = df.sort_values('Username', key=lambda x: x.str.lower()).reset_index(drop=True)
        df.DiscordID = df.DiscordID.astype('string')
        print(df)
        writer = pd.ExcelWriter("regulars.xlsx", engine='xlsxwriter')
        df.to_excel(writer, sheet_name="regulars", index=False)
        workbook = writer.book
        worksheet = writer.sheets['regulars']
        format1 = workbook.add_format()
        format1.set_underline()
        format1.set_bold()
        format1.set_bg_color('red')
        format2 = workbook.add_format()
        format2.set_bg_color('red')
        format3 = workbook.add_format()
        format3.set_num_format(0)
        worksheet.conditional_format('C2:C' + str(len(df.index)+1), {'type': 'cell', 'criteria': 'less than', 'value': '=(((DAY(TODAY())/DAY(EOMONTH(TODAY(),0))))*150)', 'format': format1})
        worksheet.conditional_format('C2:C' + str(len(df.index)+1), {'type': 'cell', 'criteria': 'less than', 'value': 150, 'format': format2})
        writer.save()

@bot.event
async def on_message(message):
    author = message.author
    if author == bot.user:
        return
    elif author.bot:
        return

    if message.guild.id == DISCORD_MBD_ID:
        db.messages.insert_one({"user_id": str(author.id), "message_id": str(message.id), "created_at": message.created_at})
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    author = message.author
    if author == bot.user:
        return
    elif author.bot:
        return

    if message.guild.id == DISCORD_MBD_ID:
        if db.messages.find({'message_id': message.id}) != None:
            db.messages.delete_many({'message_id': message.id})

bot.run(DISCORD_BOT_SECRET)