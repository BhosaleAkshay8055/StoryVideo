from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
import uuid
import subprocess
import json

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
async def preview_video(folder: str = Form(...), durations: str = Form(...)):

    folder_path = os.path.join(UPLOAD_FOLDER, folder)

    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    try:
        duration_list = [float(d) for d in durations.split(",")]
    except:
        raise HTTPException(status_code=400, detail="Invalid durations")

    # find audio
    audio_path = None
    for f in os.listdir(folder_path):
        if f.lower().endswith((".mp3", ".wav")):
            audio_path = os.path.abspath(os.path.join(folder_path, f))
            break

    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")

    # get audio duration
    probe = subprocess.run(
        [
            "ffprobe",
            "-v","error",
            "-show_entries","format=duration",
            "-of","json",
            audio_path
        ],
        capture_output=True,
        text=True
    )

    audio_duration = float(json.loads(probe.stdout)["format"]["duration"])

    # get images
    images = sorted([
        os.path.abspath(os.path.join(folder_path, f))
        for f in os.listdir(folder_path)
        if f.lower().endswith((".jpg",".jpeg",".png"))
    ])

    if not images:
        raise HTTPException(status_code=404, detail="Images missing")

    used = sum(duration_list[:-1]) if len(duration_list) > 1 else 0
    last_duration = max(0.1, audio_duration - used)

    concat_file = os.path.join(folder_path,"slides.txt")

    with open(concat_file,"w",encoding="utf-8") as f:

        for i,img in enumerate(images):

            if i == len(images)-1:
                duration = last_duration
            else:
                duration = duration_list[i] if i < len(duration_list) else 2

            img_path = img.replace("\\","/")

            f.write(f"file '{img_path}'\n")
            f.write(f"duration {duration}\n")

        last_img = images[-1].replace("\\","/")
        f.write(f"file '{last_img}'\n")

    output_filename = f"{folder}_preview.mp4"
    output_path = os.path.join(VIDEO_FOLDER,output_filename)

    cmd = [
        "ffmpeg",
        "-y",
        "-f","concat",
        "-safe","0",
        "-i",concat_file,
        "-i",audio_path,

        "-vf",
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",

        "-r","24",
        "-pix_fmt","yuv420p",

        "-c:v","libx264",
        "-preset","ultrafast",

        "-c:a","aac",

        "-t",str(audio_duration),

        output_path
    ]

    result = subprocess.run(cmd,capture_output=True,text=True)

    if result.returncode != 0:
        print(result.stderr)
        raise HTTPException(status_code=500,detail="Preview render failed")

    return {
        "video":f"/videos/{output_filename}",
        "download":f"/videos/{output_filename}"
    }

@app.post("/render")
async def render_video(job_id: str = Form(...), resolution: str = Form(...)):

    preview = os.path.join(VIDEO_FOLDER,f"{job_id}_preview.mp4")

    if not os.path.exists(preview):
        raise HTTPException(status_code=404,detail="Run preview first")

    if resolution == "youtube":
        w,h = 1920,1080
    else:
        w,h = 1080,1080

    final_video = os.path.join(VIDEO_FOLDER,f"{job_id}_final.mp4")

    filter_complex = (
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[v]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",preview,

        "-filter_complex",filter_complex,

        "-map","[v]",
        "-map","0:a",

        "-r","24",

        "-c:v","h264_qsv",
        "-b:v","5M",

        "-c:a","copy",

        "-shortest",

        "-movflags","+faststart",

        final_video
    ]

    result = subprocess.run(cmd,capture_output=True,text=True)

    if result.returncode != 0:
        print(result.stderr)
        raise HTTPException(status_code=500,detail="Render failed")

    return {"video":f"/videos/{job_id}_final.mp4"}