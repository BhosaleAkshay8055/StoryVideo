from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
import uuid
import subprocess
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
    job_folder = os.path.join(UPLOAD_FOLDER, job_id)
    os.makedirs(job_folder, exist_ok=True)

    # Save Audio
    audio_path = os.path.join(job_folder, audio.filename)
    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    # Save Images with numeric prefix to preserve frontend order
    for index, img in enumerate(images):
        # Example: 000_myphoto.jpg, 001_other.png
        filename = f"{index:03d}_{img.filename}"
        path = os.path.join(job_folder, filename)
        with open(path, "wb") as buffer:
            shutil.copyfileobj(img.file, buffer)

    return {"job_id": job_id}

@app.post("/preview")
async def preview_video(
    folder: str = Form(...), 
    durations: str = Form(...) 
):
    folder_path = os.path.join(UPLOAD_FOLDER, folder)
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    try:
        duration_list = [float(d) for d in durations.split(",")]
    except:
        raise HTTPException(status_code=400, detail="Invalid durations format")

    # 1. Load Audio first to know the total limit
    audio_path = next((os.path.join(folder_path, f) for f in os.listdir(folder_path) 
                      if f.lower().endswith((".mp3", ".wav"))), None)
    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    audio_clip = AudioFileClip(audio_path)
    total_audio_time = audio_clip.duration

    # 2. Get images in correct order
    images = sorted([
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ])

    if not images:
        raise HTTPException(status_code=404, detail="Images missing")

    clips = []
    # 3. Calculate time consumed by all images EXCEPT the last one
    time_used_so_far = sum(duration_list[:-1])

    for i, img in enumerate(images):
        if i == len(images) - 1:
            # The last image fills the remaining gap
            d = max(0.1, total_audio_time - time_used_so_far)
        else:
            d = duration_list[i]
            
        clip = ImageClip(img).with_duration(d)
        clips.append(clip)

    # 4. Create video and attach audio
    video = concatenate_videoclips(clips, method="compose")
    video = video.with_audio(audio_clip)

    output_filename = f"{folder}_preview.mp4"
    output_path = os.path.join(VIDEO_FOLDER, output_filename)

    video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

    return {"video": f"/videos/{output_filename}"}

# @app.post("/render")
# async def render_video(job_id: str = Form(...), resolution: str = Form(...)):
#     preview = os.path.join(VIDEO_FOLDER, f"{job_id}_preview.mp4")
#     if not os.path.exists(preview):
#         raise HTTPException(status_code=404, detail="Run preview first")

#     # Set dimensions based on resolution
#     if resolution == "youtube":
#         w, h = 1920, 1080
#     else:
#         w, h = 1080, 1080

#     final_video = os.path.join(VIDEO_FOLDER, f"{job_id}_final.mp4")

#     # Improved FFmpeg Command:
#     # 1. Adds padding to maintain aspect ratio without stretching
#     # 2. Forces pix_fmt yuv420p for Windows compatibility
#     # 3. Ensures dimensions are divisible by 2
#     cmd = [
#         "ffmpeg", "-y", 
#         "-i", preview, 
#         "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p", 
#         "-c:v", "libx264", 
#         "-profile:v", "main", 
#         "-level:v", "4.0",
#         "-c:a", "aac", 
#         "-movflags", "+faststart", # Allows video to start playing before fully downloaded
#         final_video
#     ]

#     try:
#         subprocess.run(cmd, check=True)
#     except subprocess.CalledProcessError as e:
#         raise HTTPException(status_code=500, detail="FFmpeg render failed")

#     return {"video": f"/videos/{job_id}_final.mp4"}

@app.post("/render")
async def render_video(job_id: str = Form(...), resolution: str = Form(...)):
    preview = os.path.join(VIDEO_FOLDER, f"{job_id}_preview.mp4")
    if not os.path.exists(preview):
        raise HTTPException(status_code=404, detail="Run preview first")

    # Target dimensions
    if resolution == "youtube":
        w, h = 1920, 1080
    else:
        w, h = 1080, 1080

    final_video = os.path.join(VIDEO_FOLDER, f"{job_id}_final.mp4")

    # Force even dimensions for BOTH layers to satisfy libx264
    # 'trunc(iw/2)*2' ensures the width is even
    # 'trunc(ih/2)*2' ensures the height is even
    filter_complex = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"scale='trunc(iw/2)*2':'trunc(ih/2)*2',boxblur=20:10[bg]; "
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"scale='trunc(iw/2)*2':'trunc(ih/2)*2'[fg]; "
        f"[bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2,format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y", 
        "-i", preview, 
        "-filter_complex", filter_complex,
        "-c:v", "libx264", 
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", # Changed 'copy' to 'aac' to ensure audio compatibility
        "-shortest",    # Ensures video ends when audio ends
        final_video
    ]

    try:
        print(f"Executing FFmpeg with fixed even dimensions...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg Stdout: {e.stdout}")
        print(f"FFmpeg Stderr: {e.stderr}")
        raise HTTPException(status_code=500, detail="FFmpeg render failed")

    return {"video": f"/videos/{job_id}_final.mp4"}