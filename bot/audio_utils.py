import io
import discord
from pydub import AudioSegment


async def play_audio_data(ctx, audio_data):
    audio_data = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
    audio_data = audio_data.set_channels(2).set_frame_rate(48000)

    silence = AudioSegment.silent(duration=1500)
    audio_data = audio_data + silence

    audio_file = io.BytesIO()
    audio_data.export(audio_file, format="wav")
    audio_file.seek(0)

    source = discord.FFmpegPCMAudio(
        audio_file, pipe=True,  options="-loglevel error")
    ctx.voice_client.play(source, after=lambda e: print(
        f'Player error: {e}') if e else None)
