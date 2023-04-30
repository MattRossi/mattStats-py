from datetime import datetime
import calendar
import discord
from discord.ext import commands
from pymongo import MongoClient
from pprint import pprint
import pandas as pd
import configparser

config = configparser.ConfigParser()
config.read('config.properties')

MONGO_DB_URL = config['MONGO']['DB_URL']

DISCORD_COMMAND_PREFIX = config['DISCORD']['COMMAND_PREFIX']
DISCORD_OWNER_ID = int(config['DISCORD']['OWNER_ID'])
DISCORD_BOT_SECRET = config['DISCORD']['BOT_SECRET']

MBD_GUILD_ID = int(config['MBD']['GUILD_ID'])
MBD_REGULAR_ROLE_ID = int(config['MBD']['REGULAR_ROLE_ID'])
MBD_MOD_ROLE_ID = int(config['MBD']['MOD_ROLE_ID'])

MBD_GRADUATE_ROLE_ID = int(config['MBD']['GRADUATE_ROLE_ID'])
MBD_SENIOR_ROLE_ID = int(config['MBD']['SENIOR_ROLE_ID'])
MBD_JUNIOR_ROLE_ID = int(config['MBD']['JUNIOR_ROLE_ID'])
MBD_SOPHOMORE_ROLE_ID = int(config['MBD']['SOPHOMORE_ROLE_ID'])
MBD_FRESHMAN_ROLE_ID = int(config['MBD']['FRESHMAN_ROLE_ID'])
MBD_EIGHTH_GRADER_ROLE_ID = int(config['MBD']['EIGHTH_GRADER_ROLE_ID'])
MBD_SEVENTH_GRADER_ROLE_ID = int(config['MBD']['SEVENTH_GRADER_ROLE_ID'])

MBD_GRADUATE_CHANNEL_ID = int(config['MBD']['GRADUATE_CHANNEL_ID'])
MBD_SENIOR_CHANNEL_ID = int(config['MBD']['SENIOR_CHANNEL_ID'])
MBD_JUNIOR_CHANNEL_ID = int(config['MBD']['JUNIOR_CHANNEL_ID'])
MBD_SOPHOMORE_CHANNEL_ID = int(config['MBD']['SOPHOMORE_CHANNEL_ID'])
MBD_FRESHMAN_CHANNEL_ID = int(config['MBD']['FRESHMAN_CHANNEL_ID'])
MBD_JR_HIGH_CHANNEL_ID = int(config['MBD']['JR_HIGH_CHANNEL_ID'])

DCD_GUILD_ID = int(config['DCD']['GUILD_ID'])
DCD_JON_ROLE_ID = int(config['DCD']['JON_ROLE_ID'])
DCD_JON_USER_ID = int(config['DCD']['JON_USER_ID'])

mongo = MongoClient(MONGO_DB_URL)
db = mongo.mbd
print(db.users.find_one())

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.typing = False
intents.presences = False
intents.message_content = True
bot = commands.Bot(command_prefix=DISCORD_COMMAND_PREFIX, intents=intents, owner_id=DISCORD_OWNER_ID)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    guild = member.guild
    if guild.id == DCD_GUILD_ID:
        if member.id == DCD_JON_USER_ID:
            role = member.guild.get_role(DCD_JON_ROLE_ID)
            await member.add_roles(role)

@bot.slash_command(name='reloadregulars', description="Reloads the list of Regulars based on the current role's members.")
async def reloadRegulars(ctx):
    isOwner = await bot.is_owner(ctx.author)
    if isOwner:
        currentRegs = ctx.guild.get_role(MBD_REGULAR_ROLE_ID).members
        actualRegs = currentRegs
        # This is so stupid but it works so whatever
        for x in range(0, 2):
            for reg in currentRegs:
                if reg in ctx.guild.get_role(MBD_MOD_ROLE_ID).members:
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

        await ctx.respond('Regulars reloaded!')

@bot.slash_command(name='checkuser', description="Checks for a user's message count.")
async def checkuser(ctx, timelength: discord.Option(str, choices=['all', 'this-month', 'last-month']), userid: discord.Option(str)):
    isOwner = await bot.is_owner(ctx.author)
    if isOwner:
        print(bot.get_guild(MBD_GUILD_ID).get_member(int(userid)))
        if bot.get_guild(MBD_GUILD_ID).get_member(int(userid)) == None:
            print(f'Could not find user with ID {userid}')
            await ctx.respond(f'Could not find user with ID {userid}')
            return

        if timelength == 'all':
            countDocs = db.messages.count_documents({'user_id': str(userid)})
            print(f'Number of messages (all-time) by {userid}: {countDocs}')
            await ctx.respond(f'Number of messages (all-time) by {userid}: {countDocs}')
            return
        elif timelength == 'this-month':
            currentYear = datetime.now().year
            currentMonth = datetime.now().month
            lastDay = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
            countDocs = db.messages.count_documents({'user_id': str(userid), 'created_at': {'$gte': datetime(currentYear, currentMonth, 1), '$lt': datetime(currentYear, currentMonth, lastDay)}})
            print(f'Number of messages (current month) by {userid}: {countDocs}')
            await ctx.respond(f'Number of messages (current month) by {userid}: {countDocs}')
            return
        elif timelength == 'last-month':
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
            countDocs = db.messages.count_documents({'user_id': str(userid), 'created_at': {'$gte': datetime(lastMonthsYear, lastMonth, 1), '$lt': datetime(lastMonthsYear, lastMonth, lastDay)}})
            print(f'Number of messages (last month) by {userid}: {countDocs}')
            await ctx.respond(f'Number of messages (last month) by {userid}: {countDocs}')
            return

@bot.slash_command(name='checkregulars', description="Checks for all of the current Regular member message counts.")
async def checkRegs(ctx, timelength: discord.Option(str, choices=['all', 'this-month', 'last-month'])):
    isOwner = await bot.is_owner(ctx.author)
    if isOwner:
        overallMessage = []
        df = pd.DataFrame({
            'Username': [],
            'DiscordID': [],
            'MessageCount': []
        })
        for document in db.regulars.find({}):
            userID = document['discord_id']
            discordUser = bot.get_guild(MBD_GUILD_ID).get_member(int(userID))

            if timelength == 'all':
                countDocs = db.messages.count_documents({'user_id': str(userID)})
                nameTime = 'Not Found'
                if (discordUser == None):
                    nameTime = 'Not Found'
                else:
                    nameTime = discordUser.name
                overallMessage.append(f'Number of messages (all-time) by {nameTime} ({userID}): {countDocs} \n')
            elif timelength == 'this-month':
                currentYear = datetime.now().year
                currentMonth = datetime.now().month
                lastDay = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
                countDocs = db.messages.count_documents({'user_id': str(userID), 'created_at': {'$gte': datetime(currentYear, currentMonth, 1), '$lt': datetime(currentYear, currentMonth, lastDay)}})
                overallMessage.append(f'Number of messages (current month) by {discordUser} ({userID}): {countDocs} \n')
                nameTime = 'Not Found'
                if (discordUser == None):
                    nameTime = 'Not Found'
                else:
                    nameTime = discordUser.name
                df = pd.concat([df, pd.DataFrame({'Username': [str(nameTime)], 'DiscordID': [str(userID)], 'MessageCount': [int(countDocs)]})])
            elif timelength == 'last-month':
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
                nameTime = 'Not Found'
                if (discordUser == None):
                    nameTime = 'Not Found'
                else:
                    nameTime = discordUser.name
                df = pd.concat([df, pd.DataFrame({'Username': [str(nameTime)], 'DiscordID': [str(userID)], 'MessageCount': [int(countDocs)]})])
        finalMessage = ''
        for line in overallMessage:
            finalMessage += line
            if len(finalMessage) >= 1750:
                await ctx.respond(finalMessage)
                finalMessage = ''
        if finalMessage:
            await ctx.respond(finalMessage)
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
        writer.close()

@bot.slash_command(name='graduationtime', description="Graduates all of the Seniors and moves all of the other roles up a year.")
async def graduation(ctx):
    isOwner = await bot.is_owner(ctx.author)
    if isOwner:
        # Rename role channels
        # TODO make this more dynamic
        # jr-high -> Stays the same, no automated action needed
        # senior -> Rename to class-of-2022
        # TODO Add automation to move this to the Archive category
        await bot.get_guild(MBD_GUILD_ID).get_channel(MBD_SENIOR_CHANNEL_ID).edit(name='class-of-2022')
        # junior -> Rename to senior
        await bot.get_guild(MBD_GUILD_ID).get_channel(MBD_JUNIOR_CHANNEL_ID).edit(name='senior')
        # sophomore -> rename to junior
        await bot.get_guild(MBD_GUILD_ID).get_channel(MBD_SOPHOMORE_CHANNEL_ID).edit(name='junior')
        # freshman -> rename to sophomore
        await bot.get_guild(MBD_GUILD_ID).get_channel(MBD_FRESHMAN_CHANNEL_ID).edit(name='sophomore')
        # MANUAL ACTION -> Create new channel for rising freshmen
        # TODO make this automated
        await ctx.respond('Renamed channels')

        # Rename roles
        # TODO make this more dynamic
        # Junior - 202X -> Senior - 202X
        await bot.get_guild(MBD_GUILD_ID).get_role(MBD_JUNIOR_ROLE_ID).edit(name='Senior - 2023')
        # Sophomore - 202X -> Junior - 202X
        await bot.get_guild(MBD_GUILD_ID).get_role(MBD_SOPHOMORE_ROLE_ID).edit(name='Junior - 2024')
        # Freshman - 202X -> Sophomore - 202X
        await bot.get_guild(MBD_GUILD_ID).get_role(MBD_FRESHMAN_ROLE_ID).edit(name='Sophomore - 2025')
        # 8th Grader - 202X -> Freshman - 202X
        await bot.get_guild(MBD_GUILD_ID).get_role(MBD_EIGHTH_GRADER_ROLE_ID).edit(name='Freshmen - 2026')
        # 7th Grader - 202X -> 8th Grader - 202X
        await bot.get_guild(MBD_GUILD_ID).get_role(MBD_SEVENTH_GRADER_ROLE_ID).edit(name='8th Grader - 2027')
        await ctx.respond('Renamed roles')

        # Move all Seniors to Graduate role
        # MANUAL ACTION - Delete the senior role afterwards
        seniors = ctx.guild.get_role(int(MBD_SENIOR_ROLE_ID)).members
        graduate_role = ctx.guild.get_role(int(MBD_GRADUATE_ROLE_ID))
        senior_count = 0
        for senior in seniors:
            if graduate_role not in senior.roles:
                await senior.add_roles(graduate_role)
                senior_count += 1
            print(str(senior_count))
        await ctx.respond('Graduated ' + str(senior_count) + ' senior(s)')

@bot.event
async def on_message(message):
    author = message.author
    if author == bot.user:
        return
    elif author.bot:
        return

    if message.guild.id == MBD_GUILD_ID:
        db.messages.insert_one({"user_id": str(author.id), "message_id": str(message.id), "created_at": message.created_at})
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    author = message.author
    if author == bot.user:
        return
    elif author.bot:
        return

    if message.guild.id == MBD_GUILD_ID:
        if db.messages.find({'message_id': message.id}) != None:
            db.messages.delete_many({'message_id': message.id})

bot.run(DISCORD_BOT_SECRET)