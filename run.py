import os
import sys
import time
import subprocess
import webbrowser

def install_dependencies():
    print("Checking system dependencies...")
    try:
        import fastapi
        import uvicorn
        import websockets
        import dotenv
        import google.generativeai
        import pyautogui
        import psutil
        import PIL
        import bs4
        import httpx
        print("All dependencies are already installed.")
    except ImportError:
        print("Missing dependencies. Installing from requirements.txt...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("Dependencies successfully installed.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {str(e)}")
            sys.exit(1)

def setup_env():
    if not os.path.exists(".env"):
        print("Creating .env file from template...")
        if os.path.exists(".env.example"):
            try:
                with open(".env.example", "r") as src, open(".env", "w") as dest:
                    dest.write(src.read())
                print(".env created successfully. Please configure your API keys.")
            except Exception as e:
                print(f"Error copying .env: {str(e)}")
        else:
            with open(".env", "w") as f:
                f.write("PORT=8000\nUSER_NAME=Sir\nASSISTANT_NAME=Friday\nSAFETY_LEVEL=medium\nGEMINI_API_KEY=\n")
            print("Default .env file initialized.")

def main():
    # 1. Prepare environment
    install_dependencies()
    setup_env()
    
    # Load dotenv variables
    from dotenv import load_dotenv
    load_dotenv()
    
    port = int(os.getenv("PORT", 8000))
    url = f"http://127.0.0.1:{port}/ui/index.html"
    
    print("\n" + "="*50)
    print("      FRIDAY DESKTOP ASSISTANT SYSTEM INITIALIZED")
    print(f"      Launching HUD at: {url}")
    print("="*50 + "\n")
    
    # 2. Automatically open web dashboard in default browser after 1.5 seconds delay
    def open_browser():
        time.sleep(1.5)
        print(f"Opening dashboard in browser: {url}")
        webbrowser.open(url)
        
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # 3. Start Uvicorn Server
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=True)

if __name__ == "__main__":
    main()
