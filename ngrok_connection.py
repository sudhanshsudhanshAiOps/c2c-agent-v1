# Expose the local webhook server through the configured ngrok tunnel.
import ngrok
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

# Open the ngrok tunnel to the local server and report the public endpoint.
def start_tunnel():
    # Expose your running local server (e.g., port 8080) to the internet
    # Make sure your NGROK_AUTHTOKEN environment variable is set
    listener = ngrok.forward("localhost:8000", authtoken=os.getenv("NGROK_AUTHTOKEN"))

    # Print out the secure URL to share
    print(f"Public URL: {listener.url()}")

if __name__ == "__main__":
    start_tunnel()

    # Keep your script running so the tunnel stays open
    import time
    while True:
        time.sleep(1)
