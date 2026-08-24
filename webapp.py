import webview
import subprocess


def closed():
    subprocess.run(
        ["docker", "compose", "down"],
        cwd="/home/knightmares/Documents/project/OllamaAgent",
    )


window = webview.create_window(
    "OllamaAgent",
    "http://localhost:8501",
    width=1280,
    height=720,
    min_size=(800, 600),
    minimized=True,
    maximized=True,
    confirm_close=True,
)

if window:
    window.events.closed += closed

webview.start(gui="qt")
