import os
import tempfile
import requests
import subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from mangum import Mangum  # Vercel needs this

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "FastAPI running on Vercel"}

@app.get("/convert")
async def convert_audio(url: str):
    with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as input_file:
        input_path = input_file.name
    
    output_path = input_path.replace(".m4a", ".mp3")
    output_file = Path(output_path)

    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to download the file")

    with open(input_path, "wb") as file:
        file.write(response.content)

    command = ["ffmpeg", "-i", input_path, "-q:a", "2", output_path]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        os.remove(input_path)
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr}")

    os.remove(input_path)

    if not output_file.exists():
        raise HTTPException(status_code=500, detail="Conversion failed, output file not found")

    return FileResponse(output_file, filename="converted.mp3", media_type="audio/mpeg")

# Required for Vercel
handler = Mangum(app)
