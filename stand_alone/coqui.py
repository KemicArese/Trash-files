from coqui import CoquiTTS
def initialize_tts(model_name: str = "tts_models/en/ljspeech/") -> CoquiTTS:
    """
    Initialize the Coqui TTS model.

    Args:
        model_name (str): The name of the TTS model to load.

    Returns:
        CoquiTTS: An instance of the Coqui TTS model.
    """
    tts = CoquiTTS(model_name)
    return tts
def synthesize_speech(tts: CoquiTTS, text: str, output_path: str) -> None:
    """
    Synthesize speech from text and save it to a file.

    Args:
        tts (CoquiTTS): The Coqui TTS model instance.
        text (str): The text to synthesize.
        output_path (str): The path to save the synthesized speech.
    """
    audio = tts.tts(text)
    with open(output_path, "wb") as f:
        f.write(audio)
def list_available_models() -> list:
    """
    List available Coqui TTS models.

    Returns:
        list: A list of available TTS model names.
    """
    return CoquiTTS.list_models()
