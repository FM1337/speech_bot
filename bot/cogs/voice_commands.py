import asyncio
import hashlib
import json
import os
from typing import Optional
import discord
from discord.ext import commands
from bot.audio_utils import play_audio_data
from bot.elevenlabs_utils import generate_audio, get_voices, get_remaining_quota
from discord import app_commands


class VoiceCommands(commands.Cog):
    # create a buffer of incoming text messages
    # just in case the bot is still speaking and we get another message
    # this way we can queue up the messages
    buffer = []
    voice_id_history = {}
    voice_id_history_checksum = ""
    bot_speaking = False

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="list-voices", description="List all available voices")
    async def list_voices(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Fetching voices...", ephemeral=True)
        voices = get_voices()
        # create an embed
        embed = discord.Embed(title="Available voices", color=0x00ff00)
        # loop through the voices and add them to the embed
        needsFollowup = False
        for voice in voices:
            embed.add_field(name=voice["name"],
                            value=voice["id"], inline=False)
            if len(embed.fields) == 25:
                if needsFollowup:
                    # if we already sent a message we just edit it
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    # wait a bit so we don't get rate limited
                    await asyncio.sleep(1)
                else:
                    # if we haven't sent a message we send one
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    needsFollowup = True
                embed = discord.Embed(title="Available voices", color=0x00ff00)
        # send the embed
        if needsFollowup:
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="remaining-quota", description="Get the remaining quota")
    async def remaining_quota(self, interaction: discord.Interaction) -> None:
        remaining = get_remaining_quota()
        await interaction.response.send_message(f"You have {remaining} characters left", ephemeral=True)

    @app_commands.command(name="speak", description="Join a voice channel and converts text to speech")
    @app_commands.describe(
        message='The message you want to send',
        voice_id='The voice you want to use',
        voice_stability='A 0-1 decimal value that determines how stable the voice is',
        voice_similarity_boost='A 0-1 decimal value that determines how similar the voice is to the original voice'
    )
    async def speak(self, interaction: discord.Interaction, message: str, voice_id: Optional[str] = None, voice_stability: Optional[float] = None,  voice_similarity_boost: Optional[float] = None) -> None:
        if interaction.user.voice is None:
            await interaction.response.send_message("You are not in a voice channel", ephemeral=True)
            return

        if (voice_id is None or voice_id == "") and str(interaction.user.id) in self.voice_id_history:
            voice_id = self.voice_id_history[str(interaction.user.id)]

        remaining = get_remaining_quota()
        if len(message) > remaining:
            await interaction.response.send_message("Oi! you don't got enough credits left to speak this message! You only got {remaining} left", ephemeral=True)
            return

        if voice_stability is not None and (voice_stability < 0 or voice_stability > 1):
            await interaction.response.send_message("Oi! stability has to be between 0 and 1", ephemeral=True)
            return

        if voice_similarity_boost is not None and (voice_similarity_boost < 0 or voice_similarity_boost > 1):
            await interaction.response.send_message("Oi! similarity boost has to be between 0 and 1", ephemeral=True)
            return

        if self.bot_speaking:
            await interaction.response.send_message("I'm already speaking, adding your message to the queue!", ephemeral=True)
            self.buffer.append(
                (interaction, message, voice_id, voice_stability, voice_similarity_boost))
            return
        else:
            self.bot_speaking = True
            await interaction.response.send_message("Getting ready to do a big speak!", ephemeral=True)

        voice_channel = interaction.user.voice.channel
        # check if already connected
        if interaction.guild.voice_client is None or not interaction.guild.voice_client.is_connected() or interaction.guild.voice_client.channel != voice_channel:
            await voice_channel.connect()

        audio = generate_audio(
            message, voice_id, stability=voice_stability, similarity_boost=voice_similarity_boost)
        if audio is None:
            await interaction.followup.send("Either the voice ID is invalid, or something horribly went wrong\nEIther way try again later!", ephemeral=True)
            self.bot_speaking = False
            self.buffer = []
            return
        if voice_id is not None:
            self.voice_id_history[str(interaction.user.id)] = voice_id
            await self.write_history_to_disk()
        await play_audio_data(interaction.guild, audio)

        while interaction.guild.voice_client is not None and interaction.guild.voice_client.is_playing():
            await asyncio.sleep(1)

        while len(self.buffer) > 0 and interaction.guild.voice_client is not None:
            while interaction.guild.voice_client.is_playing():
                await asyncio.sleep(1)
            interaction, message, voice, voice_stability, voice_similarity_boost = self.buffer.pop(
                0)
            audio = generate_audio(
                message, voice, stability=voice_stability, similarity_boost=voice_similarity_boost)
            await play_audio_data(interaction.guild, audio)

        # clear the buffer
        self.buffer = []
        self.bot_speaking = False

    @app_commands.command(name="get-out", description="Leave the voice channel")
    async def get_out(self, interaction: discord.Interaction) -> None:
        if interaction.guild.voice_client is None or not interaction.guild.voice_client.is_connected():
            await interaction.response.send_message("I'm not in a voice channel!", ephemeral=True)
            return
        self.bot_speaking = False
        self.buffer = []
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Bye bye!", ephemeral=True)

    @app_commands.command(name="stop", description="Stop speaking")
    async def stop(self, interaction: discord.Interaction) -> None:
        if interaction.guild.voice_client is None or not interaction.guild.voice_client.is_connected():
            await interaction.response.send_message("I'm not in a voice channel!", ephemeral=True)
            return
        self.bot_speaking = False
        self.buffer = []
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Stopped!", ephemeral=True)

    async def write_history_to_disk(self):
        # calculate current checksum
        checksum = hashlib.md5()
        checksum.update(json.dumps(self.voice_id_history).encode("utf-8"))
        checksum = checksum.hexdigest()
        # if the checksum is the same we don't need to write to disk
        if checksum == self.voice_id_history_checksum:
            return

        self.voice_id_history_checksum = checksum
        with open("voice_id_history.json", "w") as f:
            json.dump(self.voice_id_history, f)

    async def load_history_from_disk(self):
        if not os.path.exists("voice_id_history.json"):
            return

        with open("voice_id_history.json", "r") as f:
            self.voice_id_history = json.load(f)


async def setup(bot):
    cmd = VoiceCommands(bot)
    await cmd.load_history_from_disk()
    await bot.add_cog(cmd)
