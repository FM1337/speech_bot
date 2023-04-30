import os
from elevenlabs import generate, voices, set_api_key as elevenlabs_set_api_key
from typing import Optional

import requests


def set_api_key(api_key):
    elevenlabs_set_api_key(api_key)


def generate_audio(text, voice_id: Optional[str] = None, stability: Optional[float] = None, similarity_boost: Optional[float] = None):
    vs = voices()
    v = None

    if voice_id is None:
        v = vs[0]
    else:
        for voice in vs:
            if voice.voice_id == voice_id:
                v = voice
        if v is None:
            return None

    if stability is not None:
        v.settings.stability = stability
    if similarity_boost is not None:
        v.settings.similarity_boost = similarity_boost

    return generate(text, voice=v)


def get_voices():
    eVoices = voices()
    available_voices = []
    # loop through the voices and create an array
    for voice in eVoices:
        available_voices.append({
            "id": voice.voice_id,
            "name": voice.name,
        })
    return available_voices


def get_remaining_quota():
    # Why aren't I using User.from_api()? Because it doesn't work and I wasn't
    # going to spend 10+ hours figuring it out for something
    # that is essentially being written as a "ha ha funni" meme project

    # Endpoint is /v1/user/subscription
    resp = requests.get("https://api.elevenlabs.io/v1/user/subscription", headers={
        "xi-api-key": os.getenv('API_KEY')
    }
    )

    if resp.status_code != 200:
        # This means something went wrong.
        raise Exception(
            'GET /v1/user/subscription {}'.format(resp.status_code))
    data = resp.json()

    return data['character_limit'] - data['character_count']
