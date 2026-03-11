import React, { useState } from "react";
import axios from "axios";

import {
  Container,
  Typography,
  Card,
  CardContent,
  Button,
  Grid,
  TextField,
  Box,
  CircularProgress,
  Backdrop
} from "@mui/material";

import {
  ArrowUpward,
  ArrowDownward,
  CloudUpload,
  Movie
} from "@mui/icons-material";

export default function VideoEditor() {

  const [audio, setAudio] = useState(null)
  const [images, setImages] = useState([])
  const [durations, setDurations] = useState([])
  const [jobId, setJobId] = useState(null)
  const [preview, setPreview] = useState(null)
  const [finalVideo, setFinalVideo] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleImages = (e) => {

    const files = Array.from(e.target.files)

    setImages(files)

    setDurations(files.map(() => 2))

  }

  const moveImage = (i, dir) => {

    const j = dir === "up" ? i - 1 : i + 1;

    if (j < 0 || j >= images.length) return;

    const imgs = [...images];
    const durs = [...durations];

    [imgs[i], imgs[j]] = [imgs[j], imgs[i]];
    [durs[i], durs[j]] = [durs[j], durs[i]];

    setImages(imgs);
    setDurations(durs);
  };

  const updateDuration = (index, value) => {

    const arr = [...durations]

    arr[index] = parseFloat(value) || 0

    setDurations(arr)

  }

  const uploadFiles = async () => {

    if (!audio || images.length === 0) {
      alert("Please select audio and images")
      return
    }

    setLoading(true)

    try {

      const form = new FormData()

      form.append("audio", audio)

      images.forEach(img => {
        form.append("images", img)
      })

      const res = await axios.post(
        "http://localhost:8000/upload",
        form
      )

      setJobId(res.data.job_id)

      alert("Files uploaded successfully")

    } catch (err) {

      alert("Upload failed")

    }

    setLoading(false)

  }

  const generatePreview = async () => {

    setLoading(true)

    try {

      const form = new FormData()

      form.append("folder", jobId)

      form.append("durations", durations.join(","))

      const res = await axios.post(
        "http://localhost:8000/preview",
        form
      )

      setPreview(`http://localhost:8000${res.data.video}?t=${Date.now()}`)

    } catch (err) {

      alert("Preview failed")

    }

    setLoading(false)

  }

  const renderVideo = async (type) => {

    setLoading(true)

    try {

      const form = new FormData()

      form.append("job_id", jobId)

      form.append("resolution", type)

      const res = await axios.post(
        "http://localhost:8000/render",
        form
      )

      setFinalVideo(`http://localhost:8000${res.data.video}?t=${Date.now()}`)

    } catch (err) {

      alert("Render failed")

    }

    setLoading(false)

  }

  return (

    <Container maxWidth="lg" sx={{ py: 4 }}>

      <Backdrop open={loading} sx={{ zIndex: 2000, color: "#fff" }}>
        <Box textAlign="center">
          <CircularProgress color="inherit" />
          <Typography mt={2}>Processing Video...</Typography>
        </Box>
      </Backdrop>

      <Typography variant="h4" align="center" gutterBottom>
        🎬 Story To Video Creator
      </Typography>

      {/* Upload Section */}

      <Card sx={{ mb: 3 }}>
        <CardContent>

          <Typography variant="h6">1️⃣ Upload Media</Typography>

          <Grid container spacing={2} mt={1}>

            <Grid item xs={12} md={6}>
              <Button
                variant="contained"
                component="label"
                fullWidth
                startIcon={<CloudUpload />}
              >
                Upload Audio
                <input
                  type="file"
                  hidden
                  accept="audio/*"
                  onChange={(e) => setAudio(e.target.files[0])}
                />
              </Button>
            </Grid>

            <Grid item xs={12} md={6}>
              <Button
                variant="contained"
                component="label"
                fullWidth
                startIcon={<CloudUpload />}
              >
                Upload Images
                <input
                  type="file"
                  hidden
                  multiple
                  accept="image/*"
                  onChange={handleImages}
                />
              </Button>
            </Grid>

          </Grid>

        </CardContent>
      </Card>


      {/* Timeline */}

      {images.length > 0 && (

        <Card sx={{ mb: 3 }}>

          <CardContent>

            <Typography variant="h6">2️⃣ Timeline Editor</Typography>

            {images.map((img, i) => (

              <Grid
                container
                spacing={2}
                alignItems="center"
                key={i}
                sx={{ mb: 2 }}
              >

                <Grid item xs={3} md={2}>

                  <img
                    src={URL.createObjectURL(img)}
                    alt=""
                    style={{
                      width: "100%",
                      borderRadius: "6px"
                    }}
                  />

                </Grid>

                <Grid item xs={4} md={3}>

                  {i === images.length - 1 ? (

                    <Typography color="primary">
                      Ends With Audio
                    </Typography>

                  ) : (

                    <TextField
                      label="Duration (sec)"
                      type="number"
                      value={durations[i]}
                      onChange={(e) => updateDuration(i, e.target.value)}
                      size="small"
                    />

                  )}

                </Grid>

                <Grid item xs={5} md={3}>

                  <Button
                    size="small"
                    onClick={() => moveImage(i, "up")}
                    startIcon={<ArrowUpward />}
                    disabled={i === 0}
                  >

                    Up

                  </Button>

                  <Button
                    size="small"
                    onClick={() => moveImage(i, "down")}
                    startIcon={<ArrowDownward />}
                    disabled={i === images.length - 1}
                  >

                    Down

                  </Button>

                </Grid>

              </Grid>

            ))}

            <Button
              variant="contained"
              color="success"
              onClick={uploadFiles}
            >

              Save Order & Upload

            </Button>

          </CardContent>

        </Card>

      )}

      {/* Preview */}

      {jobId && (

        <Card sx={{ mb: 3 }}>

          <CardContent>

            <Typography variant="h6">3️⃣ Preview</Typography>

            <Button
              variant="contained"
              startIcon={<Movie />}
              onClick={generatePreview}
            >

              Generate Preview

            </Button>

            {preview && (

              <Box mt={3}>

                <video
                  width="100%"
                  controls
                  controlsList="nodownload"
                  onContextMenu={(e) => e.preventDefault()}
                >

                  <source src={preview} type="video/mp4" />

                </video>

                <Box mt={2}>

                  <Button
                    variant="contained"
                    sx={{ mr: 2 }}
                    onClick={() => renderVideo("youtube")}
                  >

                    Render YouTube

                  </Button>

                  <Button
                    variant="contained"
                    color="secondary"
                    onClick={() => renderVideo("insta")}
                  >

                    Render Instagram

                  </Button>

                </Box>

              </Box>

            )}

          </CardContent>

        </Card>

      )}

      {/* Final Video */}

      {finalVideo && (

        <Card>

          <CardContent>

            <Typography variant="h6">Final Video</Typography>

            <Box mt={2}>

              <video width="100%" controls>

                <source src={finalVideo} type="video/mp4" />

              </video>

            </Box>

          </CardContent>

        </Card>

      )}

    </Container>

  )

}