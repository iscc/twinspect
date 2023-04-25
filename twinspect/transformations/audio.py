from pathlib import Path
from pydub import AudioSegment
import subprocess


def trim(file_path: Path, seconds: float, position: str) -> Path:
    # Load audio file
    audio = AudioSegment.from_file(file_path)

    # Calculate the trim duration in milliseconds
    trim_duration = int(seconds * 1000)

    # Trim the audio based on the given position
    if position == 'start':
        trimmed_audio = audio[trim_duration:]
    elif position == 'end':
        trimmed_audio = audio[:-trim_duration]
    elif position == 'both':
        trimmed_audio = audio[trim_duration:-trim_duration]
    else:
        raise ValueError("Invalid position argument. Must be 'start', 'end', or 'both'.")

    # Generate a new file name with the trimming information
    new_file_path = file_path.with_stem(f"z{file_path.stem}_trimmed-{seconds}s-{position}")

    # Export the trimmed audio file
    trimmed_audio.export(new_file_path, format=file_path.suffix[1:])

    return new_file_path


def fade(file_path: Path, seconds: int, position: str) -> Path:
    # Load audio file
    audio = AudioSegment.from_file(file_path)

    # Calculate the fade duration in milliseconds
    fade_duration = seconds * 1000

    # Apply fade in/out effect based on the given position
    if position == 'in':
        faded_audio = audio.fade_in(fade_duration)
    elif position == 'out':
        faded_audio = audio.fade_out(fade_duration)
    elif position == 'both':
        faded_audio = audio.fade_in(fade_duration).fade_out(fade_duration)
    else:
        raise ValueError("Invalid position argument. Must be 'in', 'out', or 'both'.")

    # Generate a new file name with the fade information
    new_file_path = file_path.with_stem(f"z{file_path.stem}_faded-{seconds}s-{position}")

    # Export the faded audio file
    faded_audio.export(new_file_path, format=file_path.suffix[1:])

    return new_file_path


def transcode(file_path: Path, codec: str, kbps: int) -> Path:
    """Transcode audio to different formats.

    Note:
        Requires ffmpeg on your path-
        AAC Plus V2 transcoding requires ffmpeg with non-free libfdk_aac.
        See: https://github.com/AnimMouse/ffmpeg-autobuild
    """
    # Define output file format and extension based on codec
    output_format, file_extension, codec_profile = {
        'mp3': ('libmp3lame', '.mp3', None),
        'wav': ('pcm_s16le', '.wav', None),
        'ogg': ('libvorbis', '.ogg', None),
        'flac': ('flac', '.flac', None),
        'aac': ('aac', '.m4a', 'aac_he_v2'),
    }.get(codec.lower(), (None, None, None))

    if output_format is None:
        raise ValueError(
            "Invalid codec. Supported codecs are 'mp3', 'wav', 'ogg', 'flac', and 'aac'.")

    # Generate a new file name with the codec and kbps information
    new_file_name = f"z{file_path.stem}_transcoded-{codec}-{kbps}kbps{file_extension}"
    new_file_path = file_path.with_name(new_file_name)

    # Prepare the FFmpeg command
    cmd = [
        'ffmpeg',
        '-i', str(file_path),
        '-vn',
        '-c:a', output_format,
        '-b:a', f'{kbps}k'
    ]

    if codec_profile:
        cmd.extend(['-profile:a', codec_profile])

    cmd.append(str(new_file_path))

    # Execute the FFmpeg command using subprocess and suppress console output
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return new_file_path


def master(file_path: Path, intensity: str) -> Path:
    if intensity.lower() not in ['low', 'medium', 'strong']:
        raise ValueError("Intensity should be 'low', 'medium', or 'strong'.")

    # Define compression settings based on intensity
    settings = {
        'low': {'attack': 20, 'release': 250, 'ratio': 2, 'threshold': -15},
        'medium': {'attack': 10, 'release': 200, 'ratio': 3, 'threshold': -20},
        'strong': {'attack': 5, 'release': 100, 'ratio': 4, 'threshold': -25},
    }[intensity.lower()]

    # Generate a new file name with the intensity information
    new_file_name = f"z{file_path.stem}_mastered-{intensity.lower()}{file_path.suffix}"
    new_file_path = file_path.with_name(new_file_name)

    # Prepare the FFmpeg command
    cmd = [
        'ffmpeg',
        '-i', str(file_path),
        '-af', f'acompressor=attack={settings["attack"]}:release={settings["release"]}:ratio={settings["ratio"]}:threshold={settings["threshold"]}dB',
        str(new_file_path)
    ]

    # Execute the FFmpeg command using subprocess and suppress console output
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return new_file_path
