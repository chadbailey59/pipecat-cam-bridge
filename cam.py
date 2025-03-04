import os

import cv2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    # Get camera URL from environment variable
    camera_url = os.getenv("CAMERA_RTSP_URL")
    if not camera_url:
        print("Error: CAMERA_URL environment variable not set")
        return

    try:
        # Create VideoCapture directly with authenticated URL
        cap = cv2.VideoCapture(camera_url)

        # Check if camera opened successfully
        if not cap.isOpened():
            print(f"Error: Could not open camera stream at {camera_url}")
            return

        while True:
            ret, frame = cap.read()

            if ret:
                cv2.imshow("MJPEG Stream", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            else:
                print("Failed to read frame")
                break

    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Clean up
        if "cap" in locals():
            cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
