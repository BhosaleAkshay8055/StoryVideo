import React, { useState } from "react";
import axios from "axios";

export default function VideoEditor() {

const [audio,setAudio] = useState(null)
const [images,setImages] = useState([])
const [jobId,setJobId] = useState(null)
const [durations,setDurations] = useState([])
const [preview,setPreview] = useState(null)
const [finalVideo,setFinalVideo] = useState(null)


// Handle image selection
const handleImages = (files) => {

const arr = [...files]

setImages(arr)

// default duration 2 seconds
setDurations(arr.map(()=>2))

}


// Upload files
const uploadFiles = async () => {

if(!audio){
alert("Please upload audio file")
return
}

if(images.length === 0){
alert("Please upload images")
return
}

try{

const form = new FormData()

form.append("audio",audio)

images.forEach(img=>{
form.append("images",img)
})

const res = await axios.post(
"http://localhost:8000/upload",
form
)

setJobId(res.data.job_id)

alert("Files uploaded successfully")

}catch(err){

console.error(err)
alert("Upload failed")

}

}


// Update timeline duration
const updateDuration=(index,value)=>{

let arr=[...durations]

arr[index]=value

setDurations(arr)

}


// Generate preview video
const generatePreview = async ()=>{

if(!jobId){
alert("Upload files first")
return
}

try{

const form=new FormData()

form.append("folder",jobId)
form.append("durations",durations.join(","))

const res = await axios.post(
"http://localhost:8000/preview",
form
)

setPreview("http://localhost:8000"+res.data.preview_url)

}catch(err){

console.error(err)
alert("Preview generation failed")

}

}

// Render final video
const renderVideo = async(type)=>{

if(!jobId){
alert("Upload files first")
return
}

try{

const form=new FormData()

form.append("job_id",jobId)
form.append("resolution",type)

const res = await axios.post(
"http://localhost:8000/render",
form
)

setFinalVideo("http://localhost:8000"+res.data.video)

}catch(err){

console.error(err)
alert("Render failed")

}

}


return (

<div style={{padding:"40px",maxWidth:"800px"}}>

<h2>Audio Image Video Creator</h2>


<h3>Upload Audio</h3>

<input
type="file"
accept=".mp3"
onChange={(e)=>setAudio(e.target.files[0])}
/>


<h3>Upload Images</h3>

<input
type="file"
multiple
accept="image/*"
onChange={(e)=>handleImages(e.target.files)}
/>

<br/><br/>

<button onClick={uploadFiles}>
Upload Files
</button>

<hr/>


<h3>Timeline</h3>

{images.map((img,i)=>(

<div key={i} style={{marginBottom:"10px",display:"flex",gap:"10px",alignItems:"center"}}>

<img
src={URL.createObjectURL(img)}
width="100"
alt=""
/>

<input
type="number"
value={durations[i]}
min="1"
onChange={(e)=>updateDuration(i,e.target.value)}
/>

<span>seconds</span>

</div>

))}


{images.length>0 && (

<button onClick={generatePreview}>
Generate Preview
</button>

)}


{preview && (

<div>

<h3>Preview</h3>

<video width="500" controls>

<source src={preview} type="video/mp4"/>

</video>

</div>

)}


<hr/>


<h3>Render Final Video</h3>

<button onClick={()=>renderVideo("youtube")}>
Render YouTube
</button>

<button onClick={()=>renderVideo("insta")}>
Render Instagram
</button>


{finalVideo && (

<div>

<h3>Final Video</h3>

<video width="500" controls>

<source src={finalVideo} type="video/mp4"/>

</video>

</div>

)}

</div>

)

}