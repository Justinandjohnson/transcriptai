import express from "express";
import multer from "multer";
import fs from "fs";
import axios from "axios";
import FormData from "form-data";
import ffmpeg from "fluent-ffmpeg";
import ffmpegPath from "ffmpeg-static";
import path from "path";
import cors from "cors";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

ffmpeg.setFfmpegPath(ffmpegPath);

const app = express();
const upload = multer({ dest: "uploads/" });

app.use(cors());
app.use(express.static(path.join(process.cwd(), "public")));

// Endpoint for frontend to upload and get transcription
app.post("/transcribe", upload.single("audio"), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: "No file uploaded" });
    }
    const convertedPath = `${req.file.path}.mp3`;
    await new Promise((resolve, reject) => {
      ffmpeg(req.file.path)
        .toFormat("mp3")
        .audioCodec("libmp3lame")
        .audioQuality(5) // Faster conversion
        .on("error", reject)
        .on("end", resolve)
        .save(convertedPath);
    });

    const formData = new FormData();
    formData.append("audio", fs.createReadStream(convertedPath));

    const response = await axios.post(
      "http://localhost:3001/transcribe-cli",
      formData,
      {
        headers: formData.getHeaders(),
      }
    );

    fs.unlinkSync(req.file.path);
    fs.unlinkSync(convertedPath);

    res.json(response.data);
  } catch (err) {
    console.error("API error:", err?.response?.data || err?.message || err);
    res.status(500).json({ error: "Transcription failed" });
  }
});

// Endpoint to generate GPT-based notes, summary, action items
app.post("/generate-sections", express.json(), async (req, res) => {
  try {
    const { text } = req.body;
    if (!text) {
      return res.status(400).json({ error: "Missing transcription text" });
    }
    const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
    if (!OPENAI_API_KEY) {
      throw new Error("Missing OPENAI_API_KEY in environment");
    }

    const { default: OpenAI } = await import("openai");
    const client = new OpenAI({ apiKey: OPENAI_API_KEY });

    const prompt = `
      You are an assistant that extracts insights from a meeting transcription.

      Transcription:
      ${text}

      Provide JSON with keys:
      - summary: A concise paragraph summary of the meeting.
      - notes: Bullet points with key points discussed.
      - action: Numbered list of actionable next steps derived from the conversation.
    `;

    const completion = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [
        { role: "system", content: "Only respond with valid JSON." },
        { role: "user", content: prompt },
      ],
      temperature: 0,
      response_format: { type: "json_object" }
    });

    let data;
    try {
      data = JSON.parse(completion.choices[0].message.content);
    } catch (e) {
      console.error("Failed to parse GPT JSON:", completion.choices[0].message.content);
      return res.status(500).json({ error: "Invalid JSON from GPT" });
    }

    res.json(data);
  } catch (err) {
    console.error("Error in /generate-sections:", err);
    res.status(500).json({ error: err.message || "Server error" });
  }
});

// CLI endpoint runs same logic directly for standalone use
app.post("/transcribe-cli", upload.single("audio"), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: "No file uploaded" });

    // Convert file to mp3
    const convertedPath = `${req.file.path}.mp3`;
    await new Promise((resolve, reject) => {
      ffmpeg(req.file.path)
        .toFormat("mp3")
        .audioCodec("libmp3lame")
        .audioQuality(5) // Faster conversion
        .on("error", reject)
        .on("end", resolve)
        .save(convertedPath);
    });

    // Ensure file exists
    if (!fs.existsSync(convertedPath)) {
      throw new Error(`Converted file not found: ${convertedPath}`);
    }

    // Call OpenAI transcription
    const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
    if (!OPENAI_API_KEY) {
      throw new Error("Missing OPENAI_API_KEY in environment");
    }

    const { default: OpenAI } = await import("openai");
    const client = new OpenAI({ apiKey: OPENAI_API_KEY });

    const transcription = await client.audio.transcriptions
      .create({
        file: fs.createReadStream(convertedPath),
        model: "whisper-1", // Use standard whisper model for faster response
        language: "en",
        temperature: 0,
      })
      .catch((err) => {
        console.error(
          "OpenAI API error details:",
          err.response?.data || err.message || err
        );
        if (err.response?.status === 500) {
          console.error(
            "OpenAI 500 error: unsupported/invalid audio format or server issue."
          );
        }
        throw err;
      });

    if (!transcription || !transcription.text) {
      throw new Error("No transcription text returned from API");
    }

    // Clean up files
    fs.unlinkSync(req.file.path);
    fs.unlinkSync(convertedPath);

    // New AI-generated breakdown
    const breakdownPrompt = `
      Given the following transcription, generate structured sections:
      1. Summary - brief summary in plain text.
      2. Notes - bullet points of key information.
      3. Plans - high-level plan to address issues raised.
      4. TODO - actionable to-do list items.
      5. Plan Breakdown - step-by-step breakdown to execute the plan.

      Transcription:
      ${transcription.text}
    `;

    const breakdownResponse = await client.chat.completions.create({
      model: "gpt-4o-mini", // Use gpt-4o-mini for faster response
      messages: [{ role: "system", content: "You are an assistant that extracts actionable insights from transcripts." },
                 { role: "user", content: breakdownPrompt }],
      temperature: 0,
      max_tokens: 500, // Limit tokens for faster response
    });

    const breakdownText = breakdownResponse.choices[0]?.message?.content || "";

    res.json({ 
      text: transcription.text,
      breakdown: breakdownText
    });
  } catch (err) {
    console.error("CLI transcription error:", err);
    res.status(500).json({ error: err?.message || "CLI transcription error" });
  }
});

import portfinder from "portfinder";

const BASE_PORT = process.env.PORT || 3000;
let server;

async function startServer() {
  try {
    const port = await portfinder.getPortPromise({
      port: BASE_PORT,
      stopPort: BASE_PORT + 50,
    });
    server = app.listen(port, () => {
      console.log(`Server running on port ${port}`);
      console.log(`Open http://localhost:${port} in your browser`);
    });
  } catch (err) {
    console.error("Failed to bind to a port:", err);
    process.exit(1);
  }
}

// Graceful shutdown on exit
function shutdown() {
  if (server) {
    console.log("Shutting down server...");
    server.close(() => {
      console.log("Server closed.");
      process.exit(0);
    });
  } else {
    process.exit(0);
  }
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
process.on("exit", shutdown);

startServer();
