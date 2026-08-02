import asyncio
import cv2
from fastapi import Request
from security_ai_system.cameras.camera_manager import CameraManager

async def generate_mjpeg_stream(camera_id: str, manager: CameraManager, request: Request):
    """
    Asynchronous generator that yields MJPEG frames for a given camera.
    Reads from the manager's latest_results.
    """
    worker = manager.get_worker(camera_id)
    
    # We poll at roughly 30 FPS to reduce CPU burn on the web server thread
    polling_interval = 1.0 / 30.0

    while True:
        if await request.is_disconnected():
            break

        result = worker.latest_result()
        if result is not None and result.frame is not None:
            # Encode frame to JPEG
            # Use lower quality (e.g. 70) to save bandwidth for web streams
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            success, buffer = cv2.imencode('.jpg', result.frame, encode_param)
            
            if success:
                frame_bytes = buffer.tobytes()
                # Yield multipart boundary and the jpeg data
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        await asyncio.sleep(polling_interval)
