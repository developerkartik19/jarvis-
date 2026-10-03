# AI PC Agent

A voice-controlled AI agent that automates everyday PC tasks.

**Stack:** Python, Gemini API (free tier), SpeechRecognition, pyttsx3, pyautogui

## How it works
1. Speech is captured and converted to text (SpeechRecognition)
2. The LLM turns the command into a structured JSON tool call
3. Python executes the matching function from a **whitelist** of safe tools
4. The result is spoken back (pyttsx3)

## Features
- Open apps, folders and websites
- Web search by voice
- Take screenshots
- Conversational answers
- Safety: only whitelisted tools can run; no delete/shell access

## Setup
```bash
pip install -r requirements.txt
set GEMINI_API_KEY=your_key      # Windows (cmd)
export GEMINI_API_KEY=your_key   # Mac/Linux
python agent.py          # voice mode
python agent.py --text   # typing mode
```

Get a free API key at Google AI Studio.

## Example commands
- "Open notepad"
- "Search for Python tutorials"
- "Take a screenshot"
- "What time is it?"

## Future improvements
- Wake word, more tools, confirmation prompts for risky actions
