import os
import requests
import subprocess
import tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

# FFmpeg Binary URL (Prebuilt static binary)
FFMPEG_URL = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz"
FFMPEG_DIR = "/workspace/ffmpeg"
FFMPEG_PATH = f"{FFMPEG_DIR}/ffmpeg"

# Function to download and extract FFmpeg
def install_ffmpeg():
    if not os.path.exists(FFMPEG_PATH):
        os.makedirs(FFMPEG_DIR, exist_ok=True)

        # Download FFmpeg binary
        ffmpeg_tar = f"{FFMPEG_DIR}/ffmpeg.tar.xz"
        response = requests.get(FFMPEG_URL, stream=True)
        if response.status_code == 200:
            with open(ffmpeg_tar, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        else:
            raise HTTPException(status_code=500, detail="Failed to download FFmpeg binary")

        # Extract FFmpeg
        subprocess.run(["tar", "xvf", ffmpeg_tar, "-C", FFMPEG_DIR], check=True)
        extracted_folder = next(Path(FFMPEG_DIR).glob("ffmpeg-*"))
        os.rename(extracted_folder, f"{FFMPEG_DIR}/ffmpeg")

        # Make executable
        os.chmod(FFMPEG_PATH, 0o755)


@app.get("/")
async def root():
    return {"message": "FastAPI running on Koyeb"}

@app.get("/convert")
async def convert_audio(url: str):
    install_ffmpeg()  # Ensure FFmpeg is installed

    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as input_file:
        input_path = input_file.name

    output_path = input_path.replace(".m4a", ".mp3")
    output_file = Path(output_path)

    # Download the input file
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to download the file")

    with open(input_path, "wb") as file:
        file.write(response.content)

    # Run FFmpeg conversion
    command = [FFMPEG_PATH, "-i", input_path, "-q:a", "2", output_path]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        os.remove(input_path)
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr}")

    os.remove(input_path)

    if not output_file.exists():
        raise HTTPException(status_code=500, detail="Conversion failed, output file not found")

    return FileResponse(output_file, filename="converted.mp3", media_type="audio/mpeg")
