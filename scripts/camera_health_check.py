#!/usr/bin/env python3
"""
Camera Health Check Script

This script checks the health of RTSP camera streams by:
1. Attempting to connect to the RTSP stream
2. Verifying frames are being received
3. Checking frame rate
"""
import os
import sys
import json
import time
import cv2
from urllib.parse import urlparse

def check_camera_health(rtsp_url, timeout=10, expected_fps=25):
    """Check the health of an RTSP camera stream."""
    start_time = time.time()
    cap = None
    status = "unhealthy"
    message = ""
    fps = 0
    frame_count = 0
    
    try:
        # Parse the RTSP URL to check if it's valid
        parsed = urlparse(rtsp_url)
        if not all([parsed.scheme, parsed.netloc]):
            return {
                "status": "error",
                "message": f"Invalid RTSP URL: {rtsp_url}",
                "fps": 0,
                "response_time": time.time() - start_time
            }
        
        # Try to open the RTSP stream
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            return {
                "status": "error",
                "message": f"Failed to open RTSP stream: {rtsp_url}",
                "fps": 0,
                "response_time": time.time() - start_time
            }
        
        # Try to read a few frames to verify the stream is working
        frame_count = 0
        start_time = time.time()
        
        while (time.time() - start_time) < timeout and frame_count < (expected_fps * 2):
            ret, frame = cap.read()
            if ret:
                frame_count += 1
            else:
                break
            
        elapsed = time.time() - start_time
        if elapsed > 0:
            fps = frame_count / elapsed
        
        # Determine status based on FPS
        if frame_count == 0:
            status = "error"
            message = "No frames received"
        elif fps < expected_fps * 0.5:  # Less than 50% of expected FPS
            status = "degraded"
            message = f"Low FPS: {fps:.1f} (expected {expected_fps})"
        else:
            status = "healthy"
            message = f"Stream healthy, FPS: {fps:.1f}"
            
    except Exception as e:
        status = "error"
        message = f"Error checking camera: {str(e)}"
        
    finally:
        if cap is not None:
            cap.release()
    
    return {
        "status": status,
        "message": message,
        "fps": fps,
        "frame_count": frame_count,
        "response_time": time.time() - start_time,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def main():
    # Get config from environment or use defaults
    camera_endpoints = os.getenv('CAMERA_HEALTH_ENDPOINTS', '').split(',')
    timeout = int(os.getenv('timeout', 10))
    expected_fps = int(os.getenv('expected_fps', 25))
    
    if not camera_endpoints or not camera_endpoints[0]:
        print(json.dumps({
            "status": "error",
            "message": "No camera endpoints provided. Set CAMERA_HEALTH_ENDPOINTS environment variable.",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }))
        return
    
    # Check each camera
    results = []
    for endpoint in camera_endpoints:
        if not endpoint.strip():
            continue
            
        result = check_camera_health(endpoint.strip(), timeout, expected_fps)
        result["camera"] = endpoint
        results.append(result)
    
    # Print results as JSON
    if len(results) == 1:
        print(json.dumps(results[0]))
    else:
        print(json.dumps({"cameras": results}))

if __name__ == "__main__":
    main()
