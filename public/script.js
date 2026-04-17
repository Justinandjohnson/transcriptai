const dropZone = document.getElementById("drop-zone");
const progressBar = document.getElementById("progress-bar");
const progressContainer = document.getElementById("progress-container");
const result = document.getElementById("result");
const gptSections = document.getElementById("gpt-sections");

// Animation stages
const stages = {
  upload: document.getElementById("stage-upload"),
  convert: document.getElementById("stage-convert"),
  transcribe: document.getElementById("stage-transcribe"),
  gpt: document.getElementById("stage-gpt"),
};

// Create waveform bars
function createWaveform() {
  const waveform = document.getElementById("waveform");
  waveform.innerHTML = "";
  for (let i = 0; i < 20; i++) {
    const bar = document.createElement("div");
    bar.className = "waveform-bar";
    bar.style.animationDelay = `${i * 0.05}s`;
    waveform.appendChild(bar);
  }
}

// Update stage progress
function updateStage(stageName, progress, status = "active") {
  const stage = stages[stageName];
  if (!stage) return;

  // Update stage status
  stage.classList.remove("active", "completed");
  if (status === "active") {
    stage.classList.add("active");
  } else if (status === "completed") {
    stage.classList.add("completed");
    stage.querySelector(".stage-icon").textContent = "✅";
  }

  // Update progress bar
  const fill = stage.querySelector(".stage-fill");
  if (fill) {
    fill.style.width = `${progress}%`;
  }
}

// Update overall progress
function updateProgress(percent, text) {
  const progressText = document.getElementById("progress-text");
  const progressPercent = document.getElementById("progress-percent");

  if (progressText) progressText.textContent = text;
  if (progressPercent) progressPercent.textContent = `${Math.round(percent)}%`;
}

// Fast text display - no typing animation for speed
function typeText(element, text, speed = 0) {
  element.textContent = text;
  element.classList.remove("typing");
  return Promise.resolve();
}

// Drag and drop handlers
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const files = Array.from(e.dataTransfer.files);
  if (files.length > 0) {
    uploadMultipleFiles(files);
  }
});

dropZone.addEventListener("click", () => {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".mp4,.m4a,.wav,.mp3";
  input.multiple = true; // Enable multiple file selection
  input.onchange = () => {
    if (input.files.length > 0) {
      uploadMultipleFiles(Array.from(input.files));
    }
  };
  input.click();
});

// Process multiple files
async function uploadMultipleFiles(files) {
  // Show file count
  const fileCount = files.length;
  const fileNames = files.map(f => f.name).join(', ');
  
  result.textContent = `Processing ${fileCount} file${fileCount > 1 ? 's' : ''}: ${fileNames}`;
  result.style.opacity = "1";
  
  // Process files sequentially to avoid overwhelming the server
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    updateProgress((i / files.length) * 100, `Processing file ${i + 1} of ${fileCount}: ${file.name}`);
    await uploadFile(file, i + 1, fileCount);
  }
  
  // Show completion message
  updateProgress(100, `All ${fileCount} files processed successfully!`);
  
  // Add summary if multiple files
  if (fileCount > 1) {
    const summaryDiv = document.createElement("div");
    summaryDiv.className = "batch-summary";
    summaryDiv.style.cssText = `
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 20px;
      border-radius: 12px;
      margin: 20px 0;
      font-size: 1.1em;
      text-align: center;
      animation: fadeInUp 0.5s ease-out;
    `;
    summaryDiv.innerHTML = `
      <h3 style="margin: 0 0 10px 0;">✅ Batch Processing Complete</h3>
      <p style="margin: 0;">Successfully processed ${fileCount} audio files</p>
      <p style="margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.9;">Check the history panel for all transcriptions</p>
    `;
    result.parentElement.insertBefore(summaryDiv, result.nextSibling);
    
    // Remove summary after 10 seconds
    setTimeout(() => {
      summaryDiv.style.opacity = "0";
      setTimeout(() => summaryDiv.remove(), 500);
    }, 10000);
  }
}

// Main upload function with animations - OPTIMIZED
async function uploadFile(file, currentFileNum = 1, totalFiles = 1) {
  // Show progress container with animation
  progressContainer.style.display = "block";
  progressContainer.classList.add("progress-container");

  // Create waveform
  createWaveform();

  // Reset all stages
  Object.values(stages).forEach((stage) => {
    stage.classList.remove("active", "completed");
    stage.querySelector(".stage-fill").style.width = "0%";
    const icon = stage.querySelector(".stage-icon");
    if (stage.id === "stage-upload") icon.textContent = "📤";
    else if (stage.id === "stage-convert") icon.textContent = "🔄";
    else if (stage.id === "stage-transcribe") icon.textContent = "🎯";
    else if (stage.id === "stage-gpt") icon.textContent = "🤖";
  });

  // Show immediate feedback with file counter if multiple files
  if (totalFiles > 1) {
    result.innerHTML = `
      <div style="margin-bottom: 10px; color: #667eea; font-weight: 600;">
        File ${currentFileNum} of ${totalFiles}
      </div>
      <div>Processing ${file.name}...</div>
    `;
  } else {
    result.textContent = `Processing ${file.name}...`;
  }
  result.style.opacity = "1";
  result.classList.remove("typing");

  // Hide GPT sections initially
  document.querySelectorAll(".gpt-section").forEach((section) => {
    section.classList.remove("show");
    section.querySelector(".gpt-output").textContent = "";
  });

  const formData = new FormData();
  formData.append("audio", file);

  const xhr = new XMLHttpRequest();
  // Use optimized combined endpoint for speed
  const backendUrl = `/transcribe-and-analyze`;
  xhr.open("POST", backendUrl, true);

  // Upload progress
  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const percent = (e.loaded / e.total) * 100;
      updateStage("upload", percent, "active");
      const baseProgress = ((currentFileNum - 1) / totalFiles) * 100;
      const fileProgress = (percent * 0.25) / totalFiles;
      updateProgress(baseProgress + fileProgress, `Uploading ${file.name}... (${currentFileNum}/${totalFiles})`);
    }
  };

  // Handle response
  xhr.onload = async () => {
    if (xhr.status === 200) {
      const response = JSON.parse(xhr.responseText);

      // Rapid stage updates
      updateStage("upload", 100, "completed");
      updateStage("convert", 100, "completed");
      updateProgress(40, "Processing...");
      
      updateStage("transcribe", 100, "completed");
      updateProgress(60, "Analyzing...");

      // Display transcription immediately with file info
      if (response.text) {
        if (totalFiles > 1) {
          result.innerHTML = `
            <div style="margin-bottom: 10px; padding: 10px; background: #f7fafc; border-radius: 8px;">
              <span style="color: #667eea; font-weight: 600;">File ${currentFileNum}/${totalFiles}:</span>
              <span style="color: #4a5568; margin-left: 10px;">${file.name}</span>
            </div>
            <div>${response.text}</div>
          `;
        } else {
          result.textContent = response.text;
        }
        result.style.opacity = "1";
      }

      // Process GPT sections if available
      if (response.sections) {
        updateStage("gpt", 50, "active");
        displayGPTSections(response.sections);
        updateStage("gpt", 100, "completed");
        
        // Save to history with GPT data
        addToHistory(file.name, response.text, response.sections);
      } else {
        // Fallback to separate GPT call if needed
        updateStage("gpt", 0, "active");
        await simulateGPTProcessing(response.text);
        updateStage("gpt", 100, "completed");
        
        // Save to history
        addToHistory(file.name, response.text);
      }

      // Update progress based on file position
      const finalProgress = (currentFileNum / totalFiles) * 100;
      updateProgress(finalProgress, totalFiles > 1 ? `Completed ${currentFileNum} of ${totalFiles} files` : "Complete!");

      // Only hide progress container after all files are done
      if (currentFileNum === totalFiles) {
        setTimeout(() => {
          progressContainer.style.display = "none";
        }, 300);
      }

    } else {
      result.textContent = "Error during processing.";
      progressContainer.style.display = "none";
    }
  };

  xhr.onerror = () => {
    result.textContent = "Network error. Please check if the server is running.";
    progressContainer.style.display = "none";
  };

  xhr.send(formData);
}

// New function to display GPT sections directly
function displayGPTSections(data) {
  const sections = [
    { id: "notes-section", outputId: "gpt-notes", key: "notes" },
    { id: "summary-section", outputId: "gpt-summary", key: "summary" },
    { id: "action-items-section", outputId: "gpt-action-items", key: "action" },
  ];

  sections.forEach((sectionInfo) => {
    const section = document.getElementById(sectionInfo.id);
    const output = document.getElementById(sectionInfo.outputId);
    
    section.classList.add("show");
    
    // Format the output based on the section type
    if (sectionInfo.key === "notes" && Array.isArray(data[sectionInfo.key])) {
      const notes = data[sectionInfo.key];
      if (notes.length > 0) {
        const formattedNotes = notes.map(note => `• ${note}`).join('\n\n');
        output.textContent = formattedNotes;
        output.style.whiteSpace = "pre-wrap";
        output.style.lineHeight = "1.6";
      } else {
        output.textContent = "No notes available";
      }
    } else if (sectionInfo.key === "summary") {
      output.textContent = data[sectionInfo.key] || "No summary available";
      output.style.whiteSpace = "pre-wrap";
      output.style.lineHeight = "1.8";
      output.style.textAlign = "justify";
    } else if (sectionInfo.key === "action" && Array.isArray(data[sectionInfo.key])) {
      const actions = data[sectionInfo.key];
      if (actions.length > 0) {
        const formattedActions = actions.map((action, index) => `${index + 1}. ${action}`).join('\n\n');
        output.textContent = formattedActions;
        output.style.whiteSpace = "pre-wrap";
        output.style.lineHeight = "1.8";
        output.style.fontWeight = "500";
      } else {
        output.textContent = "No action items identified";
      }
    }
  });
}

// GPT processing replaced with real API call
async function simulateGPTProcessing(transcriptionText) {
  const sections = [
    { id: "notes-section", outputId: "gpt-notes", key: "notes" },
    { id: "summary-section", outputId: "gpt-summary", key: "summary" },
    { id: "action-items-section", outputId: "gpt-action-items", key: "action" },
  ];

  try {
    // Use relative URL to work with any port
    const backendUrl = `/generate-sections`;
    const resp = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: transcriptionText }),
    });
    const data = await resp.json();

    // Display all sections with proper formatting
    sections.forEach((sectionInfo, i) => {
      const section = document.getElementById(sectionInfo.id);
      const output = document.getElementById(sectionInfo.outputId);
      
      section.classList.add("show");
      
      // Format the output based on the section type
      if (sectionInfo.key === "notes" && Array.isArray(data[sectionInfo.key])) {
        // Format notes as a bulleted list with proper spacing
        const notes = data[sectionInfo.key];
        if (notes.length > 0) {
          const formattedNotes = notes.map(note => {
            // Add bullet point and proper formatting
            return `• ${note}`;
          }).join('\n\n');
          output.textContent = formattedNotes;
          output.style.whiteSpace = "pre-wrap";
          output.style.lineHeight = "1.6";
        } else {
          output.textContent = "No notes available";
        }
      } else if (sectionInfo.key === "summary") {
        // Display summary with proper paragraph formatting
        output.textContent = data[sectionInfo.key] || "No summary available";
        output.style.whiteSpace = "pre-wrap";
        output.style.lineHeight = "1.8";
        output.style.textAlign = "justify";
      } else if (sectionInfo.key === "action" && Array.isArray(data[sectionInfo.key])) {
        // Format action items as a numbered list with emphasis
        const actions = data[sectionInfo.key];
        if (actions.length > 0) {
          const formattedActions = actions.map((action, index) => {
            // Add numbering and formatting
            return `${index + 1}. ${action}`;
          }).join('\n\n');
          output.textContent = formattedActions;
          output.style.whiteSpace = "pre-wrap";
          output.style.lineHeight = "1.8";
          output.style.fontWeight = "500";
        } else {
          output.textContent = "No action items identified";
        }
      } else {
        // Fallback for any other format
        output.textContent = data[sectionInfo.key] || "No data available";
      }
      
      updateStage("gpt", (i + 1) * 33, "active");
    });
    
    // Store the GPT data with the transcription for history
    const history = JSON.parse(localStorage.getItem("transcriptionHistory")) || [];
    if (history.length > 0) {
      history[0].gptData = data;
      localStorage.setItem("transcriptionHistory", JSON.stringify(history));
    }
    
  } catch (err) {
    console.error("Error fetching GPT sections:", err);
    // Show error message in sections
    sections.forEach((sectionInfo) => {
      const section = document.getElementById(sectionInfo.id);
      const output = document.getElementById(sectionInfo.outputId);
      section.classList.add("show");
      output.textContent = "Error generating content. Please try again.";
      output.style.color = "#ff6b6b";
    });
  }
}

// Generate sample notes (in real app, this would come from GPT)
function generateNotes(text) {
  const words = text.split(" ").slice(0, 20).join(" ");
  return `Key Points:\n• ${words}...\n• Important discussion topics identified\n• Follow-up required on mentioned items`;
}

// Generate sample summary (in real app, this would come from GPT)
function generateSummary(text) {
  const words = text.split(" ").slice(0, 15).join(" ");
  return `Summary: ${words}... This transcription covers important topics that were discussed in detail.`;
}

// Generate sample action items (in real app, this would come from GPT)
function generateActionItems(text) {
  return `1. Review transcribed content\n2. Follow up on key discussion points\n3. Schedule next meeting\n4. Share notes with team`;
}

// History management with animations
function addToHistory(filename, text, gptData = null) {
  const history =
    JSON.parse(localStorage.getItem("transcriptionHistory")) || [];
  const item = {
    filename,
    text,
    timestamp: new Date().toISOString(),
    id: Date.now(),
    gptData: gptData
  };

  history.unshift(item);

  // Keep only last 50 items
  if (history.length > 50) {
    history.pop();
  }

  localStorage.setItem("transcriptionHistory", JSON.stringify(history));

  // Add to UI with animation
  const li = document.createElement("li");
  const timestamp = new Date(item.timestamp).toLocaleString();
  li.innerHTML = `
    <div style="font-weight: 600; color: #667eea;">${filename}</div>
    <div style="font-size: 0.85em; color: #718096; margin: 4px 0;">${timestamp}</div>
    <div style="font-size: 0.9em; color: #4a5568;">${text.substring(0, 80)}...</div>
  `;
  li.dataset.id = item.id;
  li.style.animation = "fadeInUp 0.5s ease-out";
  li.style.cursor = "pointer";
  li.style.padding = "12px";
  li.style.borderBottom = "1px solid #e2e8f0";
  li.style.transition = "background-color 0.2s";
  
  // Add hover effect
  li.addEventListener("mouseenter", () => {
    li.style.backgroundColor = "#f7fafc";
  });
  li.addEventListener("mouseleave", () => {
    li.style.backgroundColor = "transparent";
  });

  // Add click handler to load item
  li.addEventListener("click", () => loadHistoryItem(item));

  const historyList = document.getElementById("history-list");
  historyList.insertBefore(li, historyList.firstChild);
}

// Load history item with animation
function loadHistoryItem(item) {
  // Animate result display
  result.style.opacity = "0";
  setTimeout(() => {
    result.textContent = item.text;
    result.style.opacity = "1";
    result.style.transition = "opacity 0.5s ease";
  }, 200);

  // Show GPT sections if they exist
  if (item.gptData) {
    const sections = [
      { id: "notes-section", outputId: "gpt-notes", key: "notes" },
      { id: "summary-section", outputId: "gpt-summary", key: "summary" },
      { id: "action-items-section", outputId: "gpt-action-items", key: "action" },
    ];
    
    sections.forEach((sectionInfo, index) => {
      setTimeout(() => {
        const section = document.getElementById(sectionInfo.id);
        const output = document.getElementById(sectionInfo.outputId);
        
        section.classList.add("show");
        
        // Format the output based on the section type
        if (sectionInfo.key === "notes" && Array.isArray(item.gptData[sectionInfo.key])) {
          const notes = item.gptData[sectionInfo.key];
          if (notes.length > 0) {
            const formattedNotes = notes.map(note => `• ${note}`).join('\n\n');
            output.textContent = formattedNotes;
            output.style.whiteSpace = "pre-wrap";
            output.style.lineHeight = "1.6";
          }
        } else if (sectionInfo.key === "summary") {
          output.textContent = item.gptData[sectionInfo.key] || "No summary available";
          output.style.whiteSpace = "pre-wrap";
          output.style.lineHeight = "1.8";
          output.style.textAlign = "justify";
        } else if (sectionInfo.key === "action" && Array.isArray(item.gptData[sectionInfo.key])) {
          const actions = item.gptData[sectionInfo.key];
          if (actions.length > 0) {
            const formattedActions = actions.map((action, idx) => `${idx + 1}. ${action}`).join('\n\n');
            output.textContent = formattedActions;
            output.style.whiteSpace = "pre-wrap";
            output.style.lineHeight = "1.8";
            output.style.fontWeight = "500";
          }
        }
      }, index * 200);
    });
  } else {
    // If no GPT data, regenerate it
    simulateGPTProcessing(item.text);
  }
}

// Load history on page load with staggered animation
window.addEventListener("DOMContentLoaded", () => {
  const history =
    JSON.parse(localStorage.getItem("transcriptionHistory")) || [];
  const historyList = document.getElementById("history-list");
  historyList.innerHTML = "";

  history.forEach((item, index) => {
    const li = document.createElement("li");
    li.textContent = `${item.filename}: ${item.text.substring(0, 50)}...`;
    li.dataset.id = item.id || Date.now() + index;

    // Stagger animation
    li.style.animationDelay = `${index * 0.05}s`;

    // Add click handler
    li.addEventListener("click", () => loadHistoryItem(item));

    historyList.appendChild(li);
  });

  // Add floating particles dynamically
  createFloatingParticles();
});

// Create floating particles for background
function createFloatingParticles() {
  const particlesBg = document.querySelector(".particles-bg");
  if (!particlesBg) return;

  for (let i = 0; i < 5; i++) {
    const particle = document.createElement("div");
    particle.style.position = "absolute";
    particle.style.width = `${Math.random() * 100 + 50}px`;
    particle.style.height = particle.style.width;
    particle.style.background = `radial-gradient(circle, rgba(102, 126, 234, ${
      Math.random() * 0.1 + 0.05
    }) 0%, transparent 70%)`;
    particle.style.borderRadius = "50%";
    particle.style.left = `${Math.random() * 100}%`;
    particle.style.top = `${Math.random() * 100}%`;
    particle.style.animation = `float ${
      20 + Math.random() * 10
    }s infinite ease-in-out`;
    particle.style.animationDelay = `${Math.random() * 10}s`;
    particlesBg.appendChild(particle);
  }
}

// Add keyboard shortcuts
document.addEventListener("keydown", (e) => {
  // Ctrl/Cmd + O to open file
  if ((e.ctrlKey || e.metaKey) && e.key === "o") {
    e.preventDefault();
    dropZone.click();
  }

  // Ctrl/Cmd + H to toggle history
  if ((e.ctrlKey || e.metaKey) && e.key === "h") {
    e.preventDefault();
    const historyPanel = document.getElementById("history-panel");
    historyPanel.style.display =
      historyPanel.style.display === "none" ? "block" : "none";
  }
});

// Add visual feedback for microphone icon
setInterval(() => {
  const titleIcon = document.querySelector(".title-icon");
  if (titleIcon && progressContainer.style.display === "block") {
    titleIcon.style.transform = "scale(1.1)";
    setTimeout(() => {
      titleIcon.style.transform = "scale(1)";
    }, 500);
  }
}, 2000);
