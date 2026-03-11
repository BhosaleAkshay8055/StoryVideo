from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
import uuid
import subprocess
from fastapi import HTTPException
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
VIDEO_FOLDER = "videos"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

app.mount("/videos", StaticFiles(directory="videos"), name="videos")


@app.post("/upload")
async def upload_files(
    audio: UploadFile = File(...),
    images: list[UploadFile] = File(...)
):
    job_id = str(uuid.uuid4())

    job_folder = f"{UPLOAD_FOLDER}/{job_id}"
    os.makedirs(job_folder)

    audio_path = f"{job_folder}/{audio.filename}"

    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    image_paths = []

    for img in images:
        path = f"{job_folder}/{img.filename}"

        with open(path, "wb") as buffer:
            shutil.copyfileobj(img.file, buffer)

        image_paths.append(path)

    return {
        "job_id": job_id,
        "images": image_paths
    }


@app.post("/preview")
async def preview_video(folder: str = Form(...)):

    if not folder or folder == "null":
        raise HTTPException(status_code=400, detail="Folder not provided")

    folder_path = os.path.join(UPLOAD_FOLDER, folder)

    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    # Find audio
    audio_path = None
    for f in os.listdir(folder_path):
        if f.endswith(".mp3") or f.endswith(".wav"):
            audio_path = os.path.join(folder_path, f)
            break

    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Get images
    images = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    if len(images) == 0:
        raise HTTPException(status_code=404, detail="Images not found")

    images.sort()

    clips = []

    for img in images:
        # Use .with_duration instead of .set_duration
        clip = ImageClip(img).with_duration(2)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    audio_clip = AudioFileClip(audio_path)
    # Use .with_audio instead of .set_audio
    video = video.with_audio(audio_clip)

    output_path = f"{VIDEO_FOLDER}/{folder}_preview.mp4"

    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    return {
        "video": f"/videos/{folder}_preview.mp4"
    }


@app.post("/render")
async def render_video(
    job_id: str = Form(...),
    resolution: str = Form(...)
):
    preview = f"{VIDEO_FOLDER}/{job_id}_preview.mp4"
    
    # Check if preview exists first to avoid another error
    if not os.path.exists(preview):
         raise HTTPException(status_code=404, detail="Preview video not found. Generate preview first.")

    scale = "1920:1080" if resolution == "youtube" else "1080:1080"
    final_video = f"{VIDEO_FOLDER}/{job_id}_final.mp4"

    # Try to use the full path if 'ffmpeg' alone doesn't work
    # Example: cmd = [r"C:\PATH_TO_YOUR_FFMPEG\bin\ffmpeg.exe", "-y", ... ]
    cmd = [
        "ffmpeg", 
        "-y",
        "-i", preview,
        "-vf", f"scale={scale}",
        final_video
    ]

    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500, 
            detail="FFmpeg not found. Please install FFmpeg and add it to your system PATH."
        )

    return {"video": f"/videos/{job_id}_final.mp4"}