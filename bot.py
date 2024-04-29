from datetime import datetime
import calendar
import configparser
import discord
from discord import ApplicationContext, utils, OptionChoice
from discord.ext import commands
from pymongo import MongoClient
from pymongo.database import Database
import pandas as pd

config = configparser.ConfigParser()
config.read('config.properties')

MONGO_DB_URL = config['MONGO']['DB_URL']

DISCORD_COMMAND_PREFIX = config['DISCORD']['COMMAND_PREFIX']
DISCORD_OWNER_ID = int(config['DISCORD']['OWNER_ID'])
DISCORD_BOT_SECRET = config['DISCORD']['BOT_SECRET']

MBD_GUILD_ID = int(config['MBD']['GUILD_ID'])

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

mongo = MongoClient(MONGO_DB_URL)

def which_database(guild: discord.Guild) -> Database:
    if guild.id == MBD_GUILD_ID:
        return mongo.mbd
    if guild.id == DCD_GUILD_ID:
        return mongo.dcd
    return None

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.typing = False
intents.presences = False
intents.message_content = True
bot = commands.Bot(command_prefix=DISCORD_COMMAND_PREFIX,
                   intents=intents,
                   owner_id=DISCORD_OWNER_ID)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.slash_command(name='reloadregulars',
                   description="Reloads the list of Regulars based on the current role's members.")
@discord.commands.default_permissions(manage_channels=True)
async def reload_regulars(ctx: ApplicationContext):
    await ctx.defer()
    print(ctx.guild.id)
    db = which_database(ctx.guild)
    if db is None:
        await ctx.respond('Unable to process request! Server is not registered!')
        return
    current_regs = utils.get(ctx.guild.roles, name='Regular').members
    actual_regs = current_regs
    # This is so stupid but it works so whatever
    for _ in range(0, 2):
        for reg in current_regs:
            if reg in utils.get(ctx.guild.roles, name='Server Mods').members:
                actual_regs.remove(reg)
    regs_filter = []
    for member in actual_regs:
        if db.regulars.find_one({'discord_id': str(member.id)}) is None:
            db.regulars.insert_one({'discord_id': str(member.id),
                                    'joined_guild_at': member.joined_at})
            print(f'New Regular Alert! Added {member} ({member.id})!')
        regs_filter.append({'discord_id': {'$eq': str(member.id)}})

    for doc in db.regulars.find({'$nor': regs_filter}):
        deleted_reg = db.regulars.find_one_and_delete({'_id': doc['_id']})
        deleted_id = str(deleted_reg['discord_id'])
        print(f'Removed {deleted_id} from the regulars collection')

    await ctx.respond('Regulars reloaded!')

@bot.slash_command(name='checkuser', description="Checks for a user's message count.")
@discord.commands.option('length', type=str,
                         choices=[OptionChoice(name='All Time', value='all'),
                                  OptionChoice(name='This Month', value='this-month'),
                                  OptionChoice(name='Last Month', value='last-month')],
                         parameter_name='time_length')
@discord.commands.option('user', type=discord.User, parameter_name='user', required=True)
@discord.commands.default_permissions(manage_channels=True)
async def check_user(ctx: ApplicationContext, time_length: str, user: discord.User):
    await ctx.defer()
    db = which_database(ctx.guild)
    if db is None:
        await ctx.respond('Unable to process request! Server is not registered!')
        return
    print(ctx.guild.get_member(user.id))
    if ctx.guild.get_member(user.id) is None:
        print(f'Could not find user with ID {user.id}')
        await ctx.respond(f'Could not find user with ID {user.id}')
        return

    if time_length == 'all':
        count_docs = db.messages.count_documents({'user_id': str(user.id)})
        print(f'Number of messages (all-time) by {user} ({user.id}): {count_docs}')
        await ctx.respond(f'Number of messages (all-time) by {user} ({user.id}): {count_docs}')
        return
    elif time_length == 'this-month':
        current_year = datetime.now().year
        current_month = datetime.now().month
        last_day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
        count_docs = db.messages.count_documents(
            {'user_id': str(user),
                'created_at': {
                    '$gte': datetime(current_year, current_month, 1),
                    '$lt': datetime(current_year, current_month, last_day)}})
        print(f'Number of messages (current month) by {user} ({user.id}): {count_docs}')
        await ctx.respond(f'Number of messages (current month) by {user} ({user.id}): '
                          f'{count_docs}')
        return
    elif time_length == 'last-month':
        current_year = datetime.now().year
        current_month = datetime.now().month
        last_month = 0
        last_months_year = 0
        if current_month == 1:
            last_month = 12
            last_months_year = current_year - 1
        else:
            last_month = current_month - 1
            last_months_year = current_year
        last_day = calendar.monthrange(last_months_year, last_month)[1]
        count_docs = db.messages.count_documents({
            'user_id': str(user),
            'created_at': {
                '$gte': datetime(last_months_year, last_month, 1),
                '$lt': datetime(last_months_year, last_month, last_day)}})
        print(f'Number of messages (last month) by {user} ({user.id}): {count_docs}')
        await ctx.respond(f'Number of messages (last month) by {user} ({user.id}): '
                          f'{count_docs}')
        return

@bot.slash_command(name='checkregulars',
                   description="Checks for all of the current Regular member message counts.")
@discord.commands.option('length', type=str,
                         choices=[OptionChoice(name='All Time', value='all'),
                                  OptionChoice(name='This Month', value='this-month'),
                                  OptionChoice(name='Last Month', value='last-month')],
                         parameter_name='time_length',
                         description='Length of time to check against.')
@discord.commands.option('exclude', type=discord.abc.GuildChannel,
                         parameter_name='exclude_channel')
@discord.commands.default_permissions(manage_channels=True)
async def check_regs(ctx: ApplicationContext, time_length: str,
                     exclude_channel: discord.abc.GuildChannel = None):
    await ctx.defer()
    db = which_database(ctx.guild)
    if db is None:
        await ctx.respond('Unable to process request! Server is not registered!')
        return
    overall_message = []
    df = pd.DataFrame({
        'Username': [],
        'DiscordID': [],
        'MessageCount': []
    })
    for document in db.regulars.find({}):
        user_id = document['discord_id']
        discord_user = ctx.guild.get_member(int(user_id))

        if time_length == 'all':
            query = {'user_id': str(user_id)}
            if exclude_channel:
                query.update({'channel_id': {'$not': { '$eq': str(exclude_channel.id)}}})
            count_docs = db.messages.count_documents(query)
            name_time = 'Not Found'
            if discord_user is None:
                name_time = 'Not Found'
            else:
                name_time = discord_user.name
            overall_message.append(
                f'Number of messages (all-time) by {name_time} ({user_id}): {count_docs} \n')
        elif time_length == 'this-month':
            current_year = datetime.now().year
            current_month = datetime.now().month
            last_day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
            query = {'user_id': str(user_id),
                        'created_at': {
                            '$gte': datetime(current_year, current_month, 1),
                            '$lt': datetime(current_year, current_month, last_day)}}
            if exclude_channel:
                query.update({'channel_id': {'$not': { '$eq': str(exclude_channel.id)}}})
            count_docs = db.messages.count_documents(query)
            overall_message.append(
                f'Number of messages '
                f'(current month) by {discord_user} ({user_id}): '
                f'{count_docs} \n')
            name_time = 'Not Found'
            if discord_user is None:
                name_time = 'Not Found'
            else:
                name_time = discord_user.name
            df = pd.concat([df, pd.DataFrame(
                {'Username': [str(name_time)],
                    'DiscordID': [str(user_id)],
                    'MessageCount': [int(count_docs)]})])
        elif time_length == 'last-month':
            current_year = datetime.now().year
            current_month = datetime.now().month
            last_month = 0
            last_months_year = 0
            if current_month == 1:
                last_month = 12
                last_months_year = current_year - 1
            else:
                last_month = current_month - 1
                last_months_year = current_year
            last_day = calendar.monthrange(last_months_year, last_month)[1]
            query = {'user_id': str(user_id),
                        'created_at': {
                            '$gte': datetime(last_months_year, last_month, 1),
                            '$lt': datetime(last_months_year, last_month, last_day)}}
            if exclude_channel:
                query.update({'channel_id': {'$not': { '$eq': str(exclude_channel.id)}}})
            count_docs = db.messages.count_documents(query)
            overall_message.append(f'Number of messages (last month) by {discord_user} '
                                   f'({user_id}): {count_docs} \n')
            name_time = 'Not Found'
            if discord_user is None:
                name_time = 'Not Found'
            else:
                name_time = discord_user.name
            df = pd.concat([df, pd.DataFrame(
                {'Username': [str(name_time)],
                    'DiscordID': [str(user_id)],
                    'MessageCount': [int(count_docs)]})])
    final_message = '```'
    for line in overall_message:
        final_message += line
        if len(final_message) >= 1750:
            await ctx.respond(final_message + '```')
            final_message = '```'
    if final_message != '```':
        await ctx.respond(final_message + '```')
    if time_length in ['this-month', 'last-month']:
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
        worksheet.conditional_format('C2:C' + str(len(df.index)+1), {
            'type': 'cell',
            'criteria': 'less than',
            'value': '=(((DAY(TODAY())/DAY(EOMONTH(TODAY(),0))))*150)',
            'format': format1})
        worksheet.conditional_format('C2:C' + str(len(df.index)+1), {
            'type': 'cell',
            'criteria': 'less than',
            'value': 150,
            'format': format2})
        writer.close()

@bot.slash_command(name='graduationtime',
                   description="Graduates all of the Seniors and moves all of the other roles \
                   up a year.")
@discord.commands.default_permissions(administrator=True)
async def graduation(ctx: ApplicationContext):
    is_owner = await bot.is_owner(ctx.author)
    if is_owner:
        await ctx.defer()
        # Rename role channels
        # TODO make this more dynamic
        # jr-high -> Stays the same, no automated action needed
        # senior -> Rename to class-of-2022
        # TODO Add automation to move this to the Archive category
        await ctx.guild.get_channel(MBD_SENIOR_CHANNEL_ID).edit(
            name='class-of-2023')
        # junior -> Rename to senior
        await ctx.guild.get_channel(MBD_JUNIOR_CHANNEL_ID).edit(name='senior')
        # sophomore -> rename to junior
        await ctx.guild.get_channel(MBD_SOPHOMORE_CHANNEL_ID).edit(name='junior')
        # freshman -> rename to sophomore
        await ctx.guild.get_channel(MBD_FRESHMAN_CHANNEL_ID).edit(
            name='sophomore')
        # MANUAL ACTION -> Create new channel for rising freshmen
        # TODO make this automated
        await ctx.respond('Renamed channels')

        # Rename roles
        # TODO make this more dynamic
        # Junior - 202X -> Senior - 202X
        await ctx.guild.get_role(MBD_JUNIOR_ROLE_ID).edit(name='Senior - 2024')
        # Sophomore - 202X -> Junior - 202X
        await ctx.guild.get_role(MBD_SOPHOMORE_ROLE_ID).edit(name='Junior - 2025')
        # Freshman - 202X -> Sophomore - 202X
        await ctx.guild.get_role(MBD_FRESHMAN_ROLE_ID) \
            .edit(name='Sophomore - 2026')
        # 8th Grader - 202X -> Freshman - 202X
        await ctx.guild.get_role(MBD_EIGHTH_GRADER_ROLE_ID) \
            .edit(name='Freshmen - 2027')
        # 7th Grader - 202X -> 8th Grader - 202X
        await ctx.guild.get_role(MBD_SEVENTH_GRADER_ROLE_ID) \
            .edit(name='8th Grader - 2028')
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
async def on_message(message: discord.Message):
    author = message.author
    if author == bot.user or author.bot:
        return
    db = which_database(message.guild)

    if db is not None:
        db.messages.insert_one({"user_id": str(author.id),
                                "message_id": str(message.id),
                                "channel_id": str(message.channel.id),
                                "created_at": message.created_at})

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message: discord.Message):
    author = message.author
    if author == bot.user or author.bot:
        return
    db = which_database(message.guild)

    if db is not None:
        if db.messages.find_one({"message_id": str(message.id)}):
            if db.messages.delete_one({"message_id": str(message.id)}).deleted_count == 0:
                print(f"Unable to delete message from database with message ID '{str(message.id)}'")
        else:
            print(f"Unable to find message in database to delete with message ID "
                  f"'{str(message.id)}'")

bot.run(DISCORD_BOT_SECRET)
