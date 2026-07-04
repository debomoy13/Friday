// Friday HUD Orchestrator Client
let socket = null;
let currentRequestId = null;
let assistantName = "Friday";
let userName = "Sir";
let safetyLevel = "medium";
let isListening = false;
let isSpeaking = false;
let autoRestartSpeech = true;
let recognition = null;
let activeListeningMode = false; // True when Friday is active and waiting for a command

// HTML Elements
const connStatus = document.getElementById("connection-status");
const chatMessages = document.getElementById("chat-messages");
const actionProgress = document.getElementById("action-progress");
const actionProgressText = document.getElementById("action-progress-text");
const commandInput = document.getElementById("command-input");
const sendBtn = document.getElementById("send-btn");
const voiceTriggerBtn = document.getElementById("voice-trigger-btn");
const systemLogs = document.getElementById("system-logs");
const spokenText = document.getElementById("spoken-text");
const fridayOrb = document.getElementById("friday-orb");
const speechModeLabel = document.getElementById("speech-mode-label");

// Diagnostics
const cpuBar = document.getElementById("cpu-bar");
const cpuVal = document.getElementById("cpu-val");
const memBar = document.getElementById("mem-bar");
const memVal = document.getElementById("mem-val");
const batBar = document.getElementById("bat-bar");
const batVal = document.getElementById("bat-val");

// Webcam
const webcamVideo = document.getElementById("webcam-video");
const webcamCanvas = document.getElementById("webcam-capture-canvas");
const toggleCameraBtn = document.getElementById("toggle-camera");
const cameraLabel = document.getElementById("camera-label");
const screenshotBtn = document.getElementById("trigger-screenshot");

// Modals
const settingsToggle = document.getElementById("settings-toggle");
const settingsModal = document.getElementById("settings-modal");
const settingsClose = document.getElementById("settings-close");
const saveSettingsBtn = document.getElementById("save-settings-btn");
const settingsApiKey = document.getElementById("settings-api-key");
const settingsUserName = document.getElementById("settings-user-name");
const settingsAssistantName = document.getElementById("settings-assistant-name");
const settingsSafetyLevel = document.getElementById("settings-safety-level");

const safetyModal = document.getElementById("safety-modal");
const safetyToolName = document.getElementById("safety-tool-name");
const safetyToolArgs = document.getElementById("safety-tool-args");
const safetyApproveBtn = document.getElementById("safety-approve-btn");
const safetyDenyBtn = document.getElementById("safety-deny-btn");

// Scheduler
const reminderTitle = document.getElementById("reminder-title");
const reminderDelay = document.getElementById("reminder-delay");
const addReminderBtn = document.getElementById("add-reminder-btn");

// Canvas waveform
const canvas = document.getElementById("waveform-canvas");
const ctx = canvas.getContext("2d");
let animationFrameId = null;

// Initialize Page
document.addEventListener("DOMContentLoaded", () => {
    connectWebSocket();
    initSpeechRecognition();
    initSpeechSynthesis();
    initCanvas();
    setupEventListeners();
    animateWaveform();
});

// --- WEBSOCKET CONNECTION ---
function connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname}:${window.location.port || '8000'}/ws`;
    logToConsole("System", "Establishing socket uplink...", "info");

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        connStatus.classList.add("online");
        connStatus.querySelector(".status-text").innerText = "ONLINE";
        logToConsole("System", "WebSocket uplink operational.", "success");
    };

    socket.onclose = () => {
        connStatus.classList.remove("online");
        connStatus.querySelector(".status-text").innerText = "OFFLINE";
        logToConsole("System", "WebSocket connection lost. Retrying in 3s...", "error");
        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = (err) => {
        console.error("WS Error:", err);
        logToConsole("System", "WebSocket connection fault.", "error");
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };
}

function handleServerMessage(data) {
    switch (data.type) {
        case "init":
            userName = data.preferences.user_name || "Sir";
            assistantName = data.preferences.assistant_name || "Friday";
            safetyLevel = data.safety_level || "medium";

            settingsUserName.value = userName;
            settingsAssistantName.value = assistantName;
            settingsSafetyLevel.value = safetyLevel;

            if (data.preferences.api_key) {
                settingsApiKey.value = data.preferences.api_key;
            }

            logToConsole("Memory", `Preferences loaded. Welcome back, ${userName}.`, "info");

            // Render conversation history
            if (data.history && data.history.length > 0) {
                chatMessages.innerHTML = "";
                data.history.forEach(msg => {
                    appendMessage(msg.role, msg.content);
                });
            }
            break;

        case "status":
            showProgressOverlay(data.content);
            break;

        case "tool_executing":
            logToConsole("Router", `Executing [${data.name}] args: ${JSON.stringify(data.args)}`, "executing");
            showProgressOverlay(`Running: ${data.name}...`);
            break;

        case "tool_result":
            logToConsole("Router", `Executed tool [${data.name}]. Output success.`, "success");
            break;

        case "requires_approval":
            hideProgressOverlay();
            showSafetyApproval(data.request_id, data.tool_name, data.arguments);
            break;

        case "final_response":
            hideProgressOverlay();
            appendMessage("assistant", data.content);
            speakText(data.content);
            break;

        case "settings_updated":
            userName = data.preferences.user_name;
            assistantName = data.preferences.assistant_name;
            safetyLevel = data.preferences.safety_level;
            logToConsole("System", "Settings successfully applied.", "success");
            settingsModal.style.display = "none";
            break;

        case "reminder_added":
            logToConsole("Scheduler", `Scheduled reminder id [${data.event_id}]: '${data.title}' delay ${data.delay_seconds}s`, "info");
            break;

        case "reminder_trigger":
            logToConsole("Scheduler", `Fired alert: ${data.message}`, "executing");
            appendMessage("assistant", `[Reminder Alarm]: ${data.message}`);
            speakText(data.message);
            alert(`[Alarm Alert] ${data.message}`);
            break;

        case "proactive_battery_low":
        case "proactive_high_load":
        case "proactive_break_suggestion":
            logToConsole("Monitor", `Proactive: ${data.message}`, "executing");
            appendMessage("assistant", `[Proactive Alert]: ${data.message}`);
            speakText(data.message);
            break;

        case "stats_update":
            // Periodically sent from scheduler if active
            updateDiagnostics(data.cpu, data.memory, data.battery);
            break;

        default:
            console.log("Unhandled WS msg:", data);
    }
}

// --- CONVERSATION VIEW ---
function appendMessage(role, content) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", role);

    const bubble = document.createElement("div");
    bubble.classList.add("msg-bubble");
    bubble.innerText = content;

    msgDiv.appendChild(bubble);
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showProgressOverlay(text) {
    actionProgress.style.display = "flex";
    actionProgressText.innerText = text;
}

function hideProgressOverlay() {
    actionProgress.style.display = "none";
}

// --- CONSOLE LOGS ---
function logToConsole(module, message, type = "info") {
    const line = document.createElement("div");
    line.classList.add("log-line", type);

    const timestamp = new Date().toLocaleTimeString();
    line.innerText = `[${timestamp}] [${module}] ${message}`;

    systemLogs.appendChild(line);
    systemLogs.scrollTop = systemLogs.scrollHeight;
}

// --- LIVE PERFORMANCE DIAGNOSTICS ---
function updateDiagnostics(cpu, mem, battery) {
    cpuBar.style.width = `${cpu}%`;
    cpuVal.innerText = `${cpu}%`;

    memBar.style.width = `${mem}%`;
    memVal.innerText = `${mem}%`;

    if (battery !== null) {
        batBar.style.width = `${battery}%`;
        batVal.innerText = `${battery}%`;
    } else {
        batBar.style.width = `0%`;
        batVal.innerText = `N/A`;
    }
}

// Periodically poll diagnostics locally via safe tool call
async function startDiagnosticsPolling() {
    setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            // We can send a silent request to get stats or rely on FastAPI stats
            // To keep traffic low, we can request it every 10 seconds
            // Let's send a system stats call
            socket.send(JSON.stringify({
                type: "user_message",
                content: "Friday, return system stats for diagnostics dashboard (silent)"
            }));
        }
    }, 10000);
}

// --- SPEECH RECOGNITION (STT) ---
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        logToConsole("Speech", "Web Speech API not supported in browser. Voice control disabled.", "error");
        speechModeLabel.innerText = "NO MIC SUPPORT";
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
        isListening = true;
        voiceTriggerBtn.classList.add("active");
        speechModeLabel.innerText = "LISTENING (WAKE WORD)";
        logToConsole("Speech", "Continuous ear listening active. Wake word: Friday", "info");
    };

    recognition.onerror = (event) => {
        console.error("Speech Recognition Error:", event.error);
        if (event.error === 'not-allowed') {
            logToConsole("Speech", "Microphone access blocked.", "error");
            autoRestartSpeech = false;
            voiceTriggerBtn.classList.remove("active");
            speechModeLabel.innerText = "MIC BLOCKED";
        }
    };

    recognition.onend = () => {
        isListening = false;
        voiceTriggerBtn.classList.remove("active");
        if (autoRestartSpeech) {
            recognition.start(); // Always keep listening
        } else {
            speechModeLabel.innerText = "SPEECH STANDBY";
        }
    };

    recognition.onresult = (event) => {
        const lastResultIndex = event.resultIndex;
        const transcript = event.results[lastResultIndex][0].transcript.trim().toLowerCase();

        console.log("Heard phrase:", transcript);

        // 1. Wake word matching
        const wakeWord = assistantName.toLowerCase();
        if (transcript.includes(wakeWord)) {
            // Find index of wake word to parse command immediately following it
            const index = transcript.indexOf(wakeWord);
            const command = transcript.substring(index + wakeWord.length).trim();

            triggerFridayActivation(command);
        } else if (activeListeningMode) {
            // If already activated and waiting for follow-up phrase
            triggerFridayActivation(transcript);
        }
    };

    // Start listening automatically
    recognition.start();
}

function triggerFridayActivation(command) {
    activeListeningMode = false;
    spokenText.style.display = "block";

    if (command && command.length > 2) {
        // Speak chime or immediate ACK
        spokenText.innerText = `"${command}"`;
        speakText(`Processing, Sir.`);
        sendVerbalCommand(command);
    } else {
        // Just heard "Friday", wake up and request further command
        spokenText.innerText = `Active Listening...`;
        speakText(`Yes, ${userName}?`);
        activeListeningMode = true;
        // Keep active for 6 seconds to wait for speech
        setTimeout(() => { activeListeningMode = false; }, 6000);
    }
}

function sendVerbalCommand(text) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        logToConsole("System", "Cannot execute: disconnected from server.", "error");
        return;
    }

    appendMessage("user", text);

    // Check if webcam is running and extract base64 capture
    let base64Image = null;
    if (webcamVideo.srcObject) {
        try {
            webcamCanvas.width = webcamVideo.videoWidth || 320;
            webcamCanvas.height = webcamVideo.videoHeight || 240;
            const ctxWebcam = webcamCanvas.getContext("2d");
            ctxWebcam.drawImage(webcamVideo, 0, 0, webcamCanvas.width, webcamCanvas.height);
            base64Image = webcamCanvas.toDataURL("image/jpeg", 0.7);
        } catch (err) {
            console.error("Failed to capture webcam frame:", err);
        }
    }

    socket.send(JSON.stringify({
        type: "user_message",
        content: text,
        image: base64Image
    }));
}

// --- SPEECH SYNTHESIS (TTS) ---
let synth = null;
let currentUtterance = null;

function initSpeechSynthesis() {
    synth = window.speechSynthesis;
    if (!synth) {
        logToConsole("Speech", "Speech synthesis (TTS) unsupported in this browser.", "error");
    }
}

function speakText(text) {
    if (!synth) return;

    // Stop continuous STT listening while Friday is speaking to avoid self-listening loop
    if (recognition && isListening) {
        autoRestartSpeech = false;
        recognition.stop();
    }

    // Cancel active speech
    synth.cancel();

    // Remove markdown symbols (bold, italic, list markers) for cleaner pronunciation
    const cleanText = text.replace(/[*_`#\-]/g, "").replace(/\n/g, ". ");

    currentUtterance = new SpeechSynthesisUtterance(cleanText);
    isSpeaking = true;

    // Try to find a nice British/standard female voice to match Friday's cinematic persona
    const voices = synth.getVoices();
    const preferredVoice = voices.find(voice =>
        voice.lang.includes("en-GB") ||
        voice.name.includes("Google US English") ||
        voice.name.includes("Zira")
    );
    if (preferredVoice) {
        currentUtterance.voice = preferredVoice;
    }

    currentUtterance.rate = 1.05; // Slightly faster pacing

    currentUtterance.onend = () => {
        isSpeaking = false;
        spokenText.style.display = "none";
        // Resume STT
        if (recognition && !isListening) {
            autoRestartSpeech = true;
            recognition.start();
        }
    };

    currentUtterance.onerror = () => {
        isSpeaking = false;
        if (recognition && !isListening) {
            autoRestartSpeech = true;
            recognition.start();
        }
    };

    synth.speak(currentUtterance);
}

// Ensure voices are loaded (Chrome loads asynchronously)
if (window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => { };
}

// --- WEBCAM VIDEO STREAM ---
async function toggleCamera() {
    if (webcamVideo.srcObject) {
        // Stop stream
        const stream = webcamVideo.srcObject;
        const tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
        webcamVideo.srcObject = null;
        toggleCameraBtn.innerText = "ACTIVATE WEBCAM";
        cameraLabel.innerText = "WEBCAM: LOCKED";
        logToConsole("Vision", "Camera viewport offline.", "info");
    } else {
        // Start stream
        try {
            logToConsole("Vision", "Requesting camera resource...", "info");
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: "user" }
            });
            webcamVideo.srcObject = stream;
            toggleCameraBtn.innerText = "LOCK WEBCAM";
            cameraLabel.innerText = "WEBCAM: STREAMING";
            logToConsole("Vision", "Camera feed mounted successfully.", "success");
        } catch (err) {
            logToConsole("Vision", `Failed camera mount: ${err.message}`, "error");
        }
    }
}

// --- SAFETY APPROVAL INTERFACE ---
function showSafetyApproval(requestId, toolName, args) {
    currentRequestId = requestId;
    safetyToolName.innerText = toolName;
    safetyToolArgs.innerText = JSON.stringify(args, null, 2);

    if (toolName === "execute_terminal_command") {
        safetyToolArgs.classList.add("code-block");
    } else {
        safetyToolArgs.classList.remove("code-block");
    }

    safetyModal.style.display = "flex";
}

function handleSafetyResponse(approved) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    if (approved) {
        socket.send(JSON.stringify({
            type: "approve_action",
            request_id: currentRequestId
        }));
        logToConsole("Safety", "User approved action execution token.", "success");
    } else {
        socket.send(JSON.stringify({
            type: "deny_action",
            request_id: currentRequestId
        }));
        logToConsole("Safety", "User denied action execution token.", "error");
    }

    safetyModal.style.display = "none";
    currentRequestId = null;
}

// --- CANVAS PROCEDURAL SOUNDWAVE ANIMATOR ---
function initCanvas() {
    // Make resolution crisp for retina displays
    const dpr = window.devicePixelRatio || 1;
    canvas.width = 360 * dpr;
    canvas.height = 120 * dpr;
    ctx.scale(dpr, dpr);
}

function animateWaveform() {
    ctx.clearRect(0, 0, 360, 120);

    const time = Date.now() * 0.004;
    ctx.lineWidth = 1.5;

    // Choose wave properties based on Friday's state
    let amplitude = 8;
    let frequency = 0.03;
    let waveCount = 3;

    if (isSpeaking) {
        amplitude = 25;
        frequency = 0.06;
        waveCount = 5;
    } else if (activeListeningMode) {
        amplitude = 15;
        frequency = 0.1;
        waveCount = 4;
    } else if (isListening) {
        // standby quiet listening
        amplitude = 4;
        frequency = 0.02;
        waveCount = 2;
    }

    for (let i = 0; i < waveCount; i++) {
        ctx.beginPath();
        const grad = ctx.createLinearGradient(0, 0, 360, 0);

        // Stagger colors for futuristic holographic overlaps
        if (i % 3 === 0) {
            grad.addColorStop(0, 'rgba(0, 240, 255, 0)');
            grad.addColorStop(0.5, 'rgba(0, 240, 255, 0.45)');
            grad.addColorStop(1, 'rgba(0, 240, 255, 0)');
        } else if (i % 3 === 1) {
            grad.addColorStop(0, 'rgba(0, 114, 255, 0)');
            grad.addColorStop(0.5, 'rgba(0, 114, 255, 0.3)');
            grad.addColorStop(1, 'rgba(0, 114, 255, 0)');
        } else {
            grad.addColorStop(0, 'rgba(171, 37, 255, 0)');
            grad.addColorStop(0.5, 'rgba(171, 37, 255, 0.25)');
            grad.addColorStop(1, 'rgba(171, 37, 255, 0)');
        }

        ctx.strokeStyle = grad;

        const phase = time + (i * 0.9);
        const ampStagger = amplitude * (1 - (i * 0.15));

        for (let x = 0; x < 360; x++) {
            // Math.sin compound equations for organic ripples
            const y = 60 + Math.sin(x * frequency + phase) * Math.cos(x * 0.005 + phase * 0.5) * ampStagger;
            if (x === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.stroke();
    }

    animationFrameId = requestAnimationFrame(animateWaveform);
}

// --- BUTTONS & FORMS EVENTS ---
function setupEventListeners() {
    // Send message via clicking button or pressing Enter
    sendBtn.addEventListener("click", handleSendMessage);
    commandInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") handleSendMessage();
    });

    // Voice button trigger (manual activation/override)
    voiceTriggerBtn.addEventListener("click", () => {
        if (isListening) {
            autoRestartSpeech = false;
            recognition.stop();
        } else {
            autoRestartSpeech = true;
            recognition.start();
        }
    });

    // Camera toggle
    toggleCameraBtn.addEventListener("click", toggleCamera);

    // Screenshot trigger via socket text command
    screenshotBtn.addEventListener("click", () => {
        logToConsole("Router", "Commanding screenshot capture...", "executing");
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: "user_message",
                content: "Friday, take a screenshot"
            }));
        }
    });

    // Settings modal open/close
    settingsToggle.addEventListener("click", () => {
        settingsModal.style.display = "flex";
    });
    settingsClose.addEventListener("click", () => {
        settingsModal.style.display = "none";
    });
    window.addEventListener("click", (e) => {
        if (e.target === settingsModal) settingsModal.style.display = "none";
    });

    // Apply configuration settings
    saveSettingsBtn.addEventListener("click", () => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: "update_settings",
                api_key: settingsApiKey.value.trim(),
                user_name: settingsUserName.value.trim(),
                assistant_name: settingsAssistantName.value.trim(),
                safety_level: settingsSafetyLevel.value
            }));
        }
    });

    // Safety dialog approvals
    safetyApproveBtn.addEventListener("click", () => handleSafetyResponse(true));
    safetyDenyBtn.addEventListener("click", () => handleSafetyResponse(false));

    // Scheduler reminders
    addReminderBtn.addEventListener("click", () => {
        const title = reminderTitle.value.trim();
        const delay = parseInt(reminderDelay.value);
        if (!title) {
            alert("Please enter a reminder text.");
            return;
        }
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: "add_reminder",
                title: title,
                delay_seconds: delay
            }));
            reminderTitle.value = "";
        }
    });
}

function handleSendMessage() {
    const text = commandInput.value.trim();
    if (!text) return;

    appendMessage("user", text);

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: "user_message",
            content: text
        }));
    }

    commandInput.value = "";
}
