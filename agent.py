"""
Voice-controlled AI agent for PC task automation.
Stack: Python, Gemini API (free tier), SpeechRecognition, pyttsx3, pyautogui.

Run:   python agent.py          (voice mode)
       python agent.py --text   (type commands instead of speaking)
Say "exit" or "quit" to stop.
"""

import datetime
import json
import os
import platform
import re
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path

import pyautogui
import pyttsx3
import speech_recognition as sr
from google import genai
from google.genai import types

# ---------- Config ----------
API_KEY = os.environ.get("GEMINI_API_KEY")
# Check Google AI Studio for the current free model name if this one errors.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
SYSTEM = platform.system()  # "Windows", "Darwin" (Mac), "Linux"
SCREENSHOT_DIR = Path.home() / "agent_screenshots"

# ---------- Voice ----------
engine = pyttsx3.init()


def speak(text: str) -> None:
    print(f"Agent: {text}")
    engine.say(text)
    engine.runAndWait()


def listen() -> str:
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, phrase_time_limit=8)
    try:
        text = recognizer.recognize_google(audio)
        print(f"You: {text}")
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        speak("Speech service is unavailable. Check your internet.")
        return ""


# ---------- Tools (whitelist: the LLM can ONLY call these) ----------
APPS = {
    "Windows": {
        "notepad": ["notepad"],
        "calculator": ["calc"],
        "paint": ["mspaint"],
        "file explorer": ["explorer"],
        "chrome": ["cmd", "/c", "start", "chrome"],
    },
    "Darwin": {
        "notepad": ["open", "-a", "TextEdit"],
        "calculator": ["open", "-a", "Calculator"],
        "chrome": ["open", "-a", "Google Chrome"],
        "finder": ["open", "-a", "Finder"],
    },
    "Linux": {
        "notepad": ["gedit"],
        "calculator": ["gnome-calculator"],
        "chrome": ["google-chrome"],
        "files": ["nautilus"],
    },
}


def open_app(name: str) -> str:
    apps = APPS.get(SYSTEM, {})
    key = name.lower().strip()
    if key not in apps:
        return f"I can only open: {', '.join(apps)}."
    try:
        subprocess.Popen(apps[key])
        return f"Opening {key}."
    except Exception as e:
        return f"Could not open {key}: {e}"


def search_web(query: str) -> str:
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open(url)
    return f"Searching the web for {query}."


def open_website(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."


def open_folder(folder: str) -> str:
    # Only allow common folders inside the user's home directory
    allowed = {"downloads", "documents", "desktop", "pictures"}
    key = folder.lower().strip()
    if key not in allowed:
        return f"I can only open: {', '.join(sorted(allowed))}."
    path = Path.home() / key.capitalize()
    if not path.exists():
        return f"{key} folder not found."
    if SYSTEM == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif SYSTEM == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
    return f"Opening {key} folder."


def take_screenshot() -> str:
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    filename = SCREENSHOT_DIR / f"shot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
    pyautogui.screenshot(str(filename))
    return f"Screenshot saved to {filename}."


def get_time() -> str:
    return datetime.datetime.now().strftime("It is %I:%M %p on %A, %d %B.")


def chat(reply: str) -> str:
    """Plain conversation: the LLM just answers."""
    return reply


TOOLS = {
    "open_app": open_app,
    "search_web": search_web,
    "open_website": open_website,
    "open_folder": open_folder,
    "take_screenshot": take_screenshot,
    "get_time": get_time,
    "chat": chat,
}

SYSTEM_PROMPT = """You are a voice assistant that controls a PC.
Convert the user's request into ONE tool call. Reply with ONLY valid JSON:
{"tool": "<tool_name>", "args": {...}}

Available tools:
- open_app          args: {"name": "notepad|calculator|paint|chrome|file explorer|finder|files"}
- search_web        args: {"query": "<text>"}
- open_website      args: {"url": "<domain or url>"}
- open_folder       args: {"folder": "downloads|documents|desktop|pictures"}
- take_screenshot   args: {}
- get_time          args: {}
- chat              args: {"reply": "<short spoken answer, max 2 sentences>"}

Use "chat" for questions or anything no other tool fits.
Never invent tools. Never output anything except the JSON."""


# ---------- Brain ----------
client = genai.Client(api_key=API_KEY)


def ask_llm(command: str) -> dict:
    response = client.models.generate_content(
        model=MODEL,
        contents=command,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    raw = (response.text or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def execute(plan: dict) -> str:
    tool = plan.get("tool")
    args = plan.get("args", {}) or {}
    if tool not in TOOLS:  # safety: reject anything off the whitelist
        return "Sorry, I can't do that."
    try:
        return TOOLS[tool](**args)
    except TypeError:
        return "I didn't get the details right. Please try again."
    except Exception as e:
        return f"Something went wrong: {e}"


# ---------- Main loop ----------
def main() -> None:
    if not API_KEY:
        sys.exit("Set GEMINI_API_KEY first (see README).")

    text_mode = "--text" in sys.argv
    speak("Hello! I'm ready. Say exit to stop.")

    while True:
        command = input("You: ") if text_mode else listen()
        if not command:
            continue
        if command.lower().strip() in {"exit", "quit", "stop", "bye"}:
            speak("Goodbye!")
            break
        try:
            plan = ask_llm(command)
            speak(execute(plan))
        except Exception as e:
            speak("Sorry, I had trouble with that.")
            print(f"[debug] {e}")


if __name__ == "__main__":
    main()
