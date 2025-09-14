import discord
import traceback
import datetime
import re
from discord import app_commands, Member
from discord.ext import commands, tasks
from mcstatus import JavaServer

class MinecraftServerStatus(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.channel_cache = {}   # {channel_id: channel_object}
        self.category_cache = {}  # {category_id: category_object}
        
        # Register commands here
        self.bot.tree.add_command(self.mcserver, guild=self.guild_object)
    
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            guild = self.bot.get_guild(self.guild_object.id)
            # Make sure guild is ready before starting the cache load
            if guild:
                await self.load_channel_cache()
            else:
                print("⚠️ Guild not found yet when on_ready fired")
            
            # Make sure guild is ready before starting the server_ping task loop 
            if not self.server_ping.is_running():
                self.server_ping.start()
                print("[DEBUG] server_ping loop started!")
        except:
            traceback.print_exc()
    
    def cog_unload(self):
        self.server_ping.cancel()
    
    # Method to get the server ID from the DB
    async def get_server_id(self, ip_address: str):
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                                SELECT id FROM mc_server
                                WHERE ip_address = $1
                            """, ip_address)
            server_id = row["id"]
        return server_id
    
    # Method to add the server to DB
    async def insert_server(self, interaction: discord.Interaction, ip_address: str):
        async with self.bot.db_pool.acquire() as conn:
            result = await conn.execute("""
                INSERT INTO mc_server (ip_address)
                VALUES ($1)
                ON CONFLICT (ip_address) DO NOTHING;
            """, ip_address)
            
            if result == "INSERT 0 1":
                await interaction.response.send_message("Server successfully added!", ephemeral=True)
            else:
                await interaction.response.send_message("Server IP already exists.", ephemeral=True)
    
    # Check the status of the server via API and return values
    async def server_check(self, ip_address: str):
        server = JavaServer.lookup(ip_address)
        try:
            status = await server.async_status()
            desc = status.description
            motd = desc.simplify() if hasattr(desc, "simplify") else str(desc)
            
            # Strip Minecraft formatting codes (e.g., §a, §r, etc.)
            motd_clean = re.sub(r"§.", "", motd)
            
            return {
                "online": True,
                "motd": motd_clean,
                "players": f"{status.players.online}/{status.players.max}"
            }
        except Exception as e:
            print(f"[DEBUG] Server check failed: {e}")
            return {
                "online": False,
                "motd": None,
                "players": "0/0"
            }
    
    async def status_channel_insert(self, ip_address: str, category_id: int, status_channel_id: int, player_count_channel_id: int):
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO mc_server (ip_address, category_id, status_channel_id, player_count_channel_id, setup_status)
                VALUES ($1, $2, $3, $4, TRUE)
                ON CONFLICT (ip_address) 
                DO UPDATE SET category_id = $2,
                            status_channel_id = $3,
                            player_count_channel_id = $4,
                            setup_status = TRUE;
            """, ip_address, category_id, status_channel_id, player_count_channel_id)
                
    async def setup_status_channels(self, ip_address: str):
        server_id = await self.get_server_id(ip_address)
        results = await self.server_check(ip_address)
        guild = self.bot.get_guild(self.guild_object.id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True)
        }

        online = results["online"]
        motd = results["motd"]
        players = results["players"]

        status_emoji = "🟢" if online else "🔴"
        channel_name = f"{status_emoji} {motd}"
        player_count_name = f"👥 {players} Players"
        category_name = f"Minecraft Server {server_id}"

        category = await guild.create_category(category_name)
        status_channel = await guild.create_voice_channel(channel_name, category=category, overwrites=overwrites)
        player_count_channel = await guild.create_voice_channel(player_count_name, category=category, overwrites=overwrites)

        # Cache
        self.category_cache[category.id] = category
        self.channel_cache[status_channel.id] = status_channel
        self.channel_cache[player_count_channel.id] = player_count_channel

        try:
            await self.status_channel_insert(ip_address, category.id, status_channel.id, player_count_channel.id)
            print("[DEBUG] MC Server status channel insert successful")
        except Exception:
            traceback.print_exc()
    
    async def get_all_servers(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                                SELECT ip_address, category_id, status_channel_id, player_count_channel_id
                                FROM mc_server
                                WHERE setup_status = TRUE
                            """)
        return rows
    
    async def load_channel_cache(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                                SELECT category_id, status_channel_id, player_count_channel_id
                                FROM mc_server
                                WHERE setup_status = TRUE
                            """)
            
        guild = self.bot.get_guild(self.guild_object.id)
        
        for row in rows:
            # Try to pull objects from cache first
            category = guild.get_channel(row["category_id"])
            status_channel = guild.get_channel(row["status_channel_id"])
            player_count_channel = guild.get_channel(row["player_count_channel_id"])

            # Store them if they exist
            if category:
                self.category_cache[row["category_id"]] = category
            if status_channel:
                self.channel_cache[row["status_channel_id"]] = status_channel
            if player_count_channel:
                self.channel_cache[row["player_count_channel_id"]] = player_count_channel
    
    # Remove a server and its channels
    async def remove_server(self, ip_address: str):
        # Find all the details of the server from DB via IP
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                                SELECT category_id, status_channel_id, player_count_channel_id
                                FROM mc_server
                                WHERE ip_address = $1
                            """, ip_address)
            
            if not row:
                return False # In case the server isn't found
        
            # Init the IDs from cache or from DB pull as fallback
            category = self.category_cache.pop(row["category_id"], None) or self.bot.get_channel(row["category_id"])
            status_channel = self.channel_cache.pop(row["status_channel_id"], None) or self.bot.get_channel(row["status_channel_id"])
            player_count_channel = self.channel_cache.pop(row["player_count_channel_id"], None) or self.bot.get_channel(row["player_count_channel_id"])
            
            # Remove the channels from the server
            for ch in (status_channel, player_count_channel, category):
                try:
                    await ch.delete()
                except discord.NotFound:
                    pass
                
            # Remove the channels from the cache
            self.category_cache.pop(row["category_id"], None)
            self.channel_cache.pop(row["status_channel_id"], None)
            self.channel_cache.pop(row["player_count_channel_id"], None)

            
            # Remove the server from the DB
            async with self.bot.db_pool.acquire() as conn:
                await conn.execute("DELETE FROM mc_server WHERE ip_address = $1", ip_address)
                
            # Reset the ID sequence if the mc_server table is empty in the DB
            row_count = await conn.fetchval("SELECT COUNT(*) FROM mc_server;")
            if row_count == 0:
                # Reset sequence
                await conn.execute("ALTER SEQUENCE mc_server_id_seq RESTART WITH 1;")
                print("MC Server DB table empty — ID sequence reset to 1")
            
            return True    
        
    # Server ping happens every 2 mins
    @tasks.loop(minutes=2)
    async def server_ping(self):
        try:
            servers_data = await self.get_all_servers()
            server_count = 0
            for server_row in servers_data:
                
                server_count += 1
                
                ip_address = server_row["ip_address"]
                status_channel_id = server_row["status_channel_id"]
                player_count_channel_id = server_row["player_count_channel_id"]
                
                # 1. Run the server check and init details from response
                results = await self.server_check(ip_address)
                online = results["online"]
                motd = results["motd"]
                players = results["players"]
                
                # 2. Stage the channel names and category name
                status_emoji = "🟢" if online else "🔴"
                status_name = f"{status_emoji} {motd}"
                player_count_name = f"👥 {players} Players"
                
                # 3. Try to get loaded channel IDs (fallback icluded)
                status_channel = self.channel_cache.get(status_channel_id)
                if not status_channel:
                    status_channel = self.bot.get_channel(status_channel_id)
                    if status_channel:
                        self.channel_cache[status_channel_id] = status_channel
                
                player_count_channel = self.channel_cache.get(player_count_channel_id)
                if not player_count_channel:
                    player_count_channel = self.bot.get_channel(player_count_channel_id)
                    if player_count_channel:
                        self.channel_cache[player_count_channel_id] = player_count_channel
                
                # 4. Update the channel names
                if status_channel:
                    await status_channel.edit(name=status_name)
                if player_count_channel:
                    await player_count_channel.edit(name=player_count_name)
                    
                # Logging
                print(f"[DEBUG] server_ping loop completed: {server_count} server(s) updated")
        except:
            traceback.print_exc()
            
    # Need a slash command to first add the ip address to DB table. Will return server ID, allows for multiple servers
    @app_commands.command(name="mcserver", description="Utilize the MC Server functionality")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Server", value="add"),
        app_commands.Choice(name="Remove Server", value="remove"),
        app_commands.Choice(name="List Servers", value="list")
    ])
    async def mcserver(self, interaction: discord.Interaction, action: app_commands.Choice[str], ip_address: str = None):
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return
        
        # Logic to add a server
        if action.value == "add":
            try:
                await self.insert_server(interaction, ip_address) # Insert the server IP to DB
                await self.setup_status_channels(ip_address) # Setup the status channels
            except Exception as e:
                traceback.print_exc()
                print(f"Error adding server {ip_address}: {e}")
        
        # Logic to remove a server
        if action.value == "remove":
            try:
                await self.remove_server(ip_address)
                await interaction.response.send_message("Server successfully removed!", ephemeral=True)
            except Exception as e:
                traceback.print_exc()
                print(f"Error removing server {ip_address}: {e}")
                
        # Logic to list all current server IPs
        if action.value == "list":
            server_list = await self.get_all_servers()
            
            description = ""
            
            for server in server_list:
                ip_address = server["ip_address"]
                description += f"{ip_address}\n"
                
            embed = discord.Embed(
                    title="MC Server List",
                    description=description or "No servers found.",
                    color=discord.Color.green()
            )
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
                
        
async def setup(bot, guild_object, allowed_roles):
    cog = MinecraftServerStatus(bot, guild_object, allowed_roles)          
    await bot.add_cog(cog)      