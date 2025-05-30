#!/home/tom/github/dialogchain/python/venv/bin/python

import json
import sys
import time
import numpy as np
from ultralytics import YOLO
import cv2
from datetime import datetime, timedelta

def main():
    # Configuration
    TARGET_FPS = 1.0  # Process 1 frame per second
    TARGET_WIDTH = 640  # Target width for resizing
    CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence threshold
    
    # Initialize timing
    last_processed = datetime.now()
    frame_interval = timedelta(seconds=1.0/TARGET_FPS)
    
    # Load the smallest YOLO model
    model = YOLO('yolov8n.pt')
    
    # Warm up the model
    dummy_input = np.zeros((TARGET_WIDTH, TARGET_WIDTH, 3), dtype=np.uint8)
    _ = model(dummy_input, verbose=False)
    
    frame_count = 0
    
    # Process frames from stdin
    while True:
        current_time = datetime.now()
        
        # Read frame size (first 8 bytes: width and height as 32-bit integers)
        header = sys.stdin.buffer.read(8)
        if len(header) != 8:
            break
            
        width = int.from_bytes(header[:4], byteorder='little')
        height = int.from_bytes(header[4:8], byteorder='little')
        
        # Read frame data (3 channels: BGR)
        frame_size = width * height * 3
        frame_data = sys.stdin.buffer.read(frame_size)
        if len(frame_data) != frame_size:
            break
        
        frame_count += 1
        
        # Skip frames to achieve target FPS
        if current_time - last_processed < frame_interval:
            continue
            
        last_processed = current_time
        
        try:
            # Convert to numpy array and reshape
            frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((height, width, 3))
            
            # Resize frame to reduce processing time
            scale = TARGET_WIDTH / max(width, height)
            new_size = (int(width * scale), int(height * scale))
            if new_size[0] > 0 and new_size[1] > 0:
                frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_LINEAR)
            
            # Run YOLO detection with optimized parameters
            results = model(
                frame,
                conf=CONFIDENCE_THRESHOLD,
                imgsz=TARGET_WIDTH,
                max_det=10,  # Limit max detections
                verbose=False,
                half=False,  # Disable half precision for better compatibility
                device='cpu'  # Force CPU usage
            )
            
            # Extract detections
            detections = []
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = box.conf.item()
                    cls = int(box.cls.item())
                    name = result.names[cls]
                    
                    # Scale coordinates back to original size
                    if scale != 1.0:
                        x1, x2 = x1/scale, x2/scale
                        y1, y2 = y1/scale, y2/scale
                    
                    detections.append({
                        'class': name,
                        'confidence': float(conf),
                        'position': {
                            'x1': x1,
                            'y1': y1,
                            'x2': x2,
                            'y2': y2
                        }
                    })
            
            # Output results as JSON
            print(json.dumps({
                'detections': detections,
                'frame_size': {'width': width, 'height': height},
                'timestamp': current_time.isoformat(),
                'frame_count': frame_count
            }), flush=True)
            
            # Clear memory
            del frame
            
        except Exception as e:
            print(f"Error processing frame: {str(e)}", file=sys.stderr, flush=True)
            continue

if __name__ == '__main__':
    main()
