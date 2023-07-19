"""
Collection of synthetic audio transformations.

TODO: Use relative transformations (trim 1pct ... )
"""
from pathlib import Path
from pydub import AudioSegment
import subprocess


def trim(file_path: Path, seconds: float, position: str) -> Path:
    # Load audio file
    audio = AudioSegment.from_file(file_path)

    # Calculate the trim duration in milliseconds
    trim_duration = int(seconds * 1000)

    # Trim the audio based on the given position
    if position == "start":
        trimmed_audio = audio[trim_duration:]
    elif position == "end":
        trimmed_audio = audio[:-trim_duration]
    elif position == "both":
        trimmed_audio = audio[trim_duration:-trim_duration]
    else:
        raise ValueError("Invalid position argument. Must be 'start', 'end', or 'both'.")

    # Generate a new file name with the trimming information
    new_file_path = file_path.with_stem(f"z{file_path.stem}_trim-{seconds}s-{position}")

    # Export the trimmed audio file
    trimmed_audio.export(new_file_path, format=file_path.suffix[1:])

    return new_file_path


def fade(file_path: Path, seconds: int, position: str) -> Path:
    file_path = Path(file_path)

    audio = AudioSegment.from_file(file_path)
    fade_duration = seconds * 1000

    # Apply fade in/out effect based on the given position
    if position == "in":
        faded_audio = audio.fade_in(fade_duration)
    elif position == "out":
        faded_audio = audio.fade_out(fade_duration)
    elif position == "both":
        faded_audio = audio.fade_in(fade_duration).fade_out(fade_duration)
    else:
        raise ValueError("Invalid position argument. Must be 'in', 'out', or 'both'.")

    # Generate a new file name with the fade information
    new_file_path = file_path.with_stem(f"z{file_path.stem}_fade-{seconds}s-{position}")

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
    file_path = Path(file_path)
    output_format, file_extension, codec_profile = {
        "mp3": ("libmp3lame", ".mp3", None),
        "wav": ("pcm_s16le", ".wav", None),
        "ogg": ("libvorbis", ".ogg", None),
        "flac": ("flac", ".flac", None),
        "aac": ("aac", ".m4a", "aac_he_v2"),
    }.get(codec.lower(), (None, None, None))

    if output_format is None:
        raise ValueError(
            "Invalid codec. Supported codecs are 'mp3', 'wav', 'ogg', 'flac', and 'aac'."
        )

    new_file_name = f"z{file_path.stem}_transcode-{codec}-{kbps}kbps{file_extension}"
    new_file_path = file_path.with_name(new_file_name)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(file_path),
        "-vn",
        "-c:a",
        output_format,
        "-b:a",
        f"{kbps}k",
        str(new_file_path),
    ]

    # Note: Disabled using aac_he_v2 profile
    #       Using libfdk_aac encoder failes with some files
    #       Using built-in acc encoder cannot be decoded by fpcalc
    # if codec_profile:
    #     cmd.extend(['-profile:a', codec_profile])

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return new_file_path


def compress(file_path: Path, intensity: str) -> Path:
    if intensity.lower() not in ["low", "medium", "strong"]:
        raise ValueError("Intensity should be 'low', 'medium', or 'strong'.")

    settings = {
        "low": {"attack": 20, "release": 250, "ratio": 2, "threshold": -15},
        "medium": {"attack": 10, "release": 200, "ratio": 3, "threshold": -20},
        "strong": {"attack": 5, "release": 100, "ratio": 4, "threshold": -25},
    }[intensity.lower()]

    new_file_name = f"z{file_path.stem}_compress-{intensity.lower()}{file_path.suffix}"
    new_file_path = file_path.with_name(new_file_name)

    cmd = [
        "ffmpeg",
        "-i",
        str(file_path),
        "-af",
        f'acompressor=attack={settings["attack"]}:release={settings["release"]}:ratio={settings["ratio"]}:threshold={settings["threshold"]}dB',
        str(new_file_path),
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return new_file_path


def equalize(file_path: Path) -> Path:
    file_path = Path(file_path)
    new_file_name = f"z{file_path.stem}_equalize{file_path.suffix}"
    new_file_path = file_path.with_name(new_file_name)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(file_path),
        "-af",
        "equalizer=f=1000:t=h:width=150:g=-1, highpass=f=300, lowpass=f=12000",
        str(new_file_path),
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return new_file_path


def echo(file_path: Path) -> Path:
    file_path = Path(file_path)
    new_file_name = f"z{file_path.stem}_echo{file_path.suffix}"
    new_file_path = file_path.with_name(new_file_name)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(file_path),
        "-af",
        "aecho=0.8:0.7:60:0.2",
        str(new_file_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return new_file_path


def loudnorm(file_path: Path) -> Path:
    file_path = Path(file_path)
    new_file_name = f"z{file_path.stem}_loudnorm{file_path.suffix}"
    new_file_path = file_path.with_name(new_file_name)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(file_path),
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        str(new_file_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return new_file_path
