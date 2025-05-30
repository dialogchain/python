#!/home/tom/github/dialogchain/python/venv/bin/python

import json
import sys
import time
import numpy as np
import cv2
import signal
import os
import gc
import threading
import pathlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import JSON utilities
from scripts.json_utils import safe_json_dumps

# Load environment variables from .env file
env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Log loaded environment variables
print("Loaded environment variables from .env file:", file=sys.stderr, flush=True)
env_vars = [
    'CAMERA_IP', 'CAMERA_USER', 'CAMERA_PASS', 'ALERT_EMAIL',
    'SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS',
    'SMTP_USERNAME', 'SMTP_PASSWORD', 'FROM_EMAIL', 'REPLY_TO_EMAIL',
    'IMAP_SERVER', 'IMAP_PORT', 'IMAP_USERNAME', 'IMAP_PASSWORD', 'IMAP_FOLDER'
]

for var in env_vars:
    value = os.environ.get(var)
    if value:
        # Mask passwords and sensitive information
        if 'PASS' in var or 'PASSWORD' in var:
            masked_value = '********'
            print(f"  {var}={masked_value}", file=sys.stderr, flush=True)
        else:
            print(f"  {var}={value}", file=sys.stderr, flush=True)

# Only import YOLO if we're using it
USE_YOLO = False  # Set to False to use simple motion detection instead

if USE_YOLO:
    try:
        from ultralytics import YOLO
        print("YOLO imported successfully", file=sys.stderr, flush=True)
    except ImportError:
        print("YOLO not available, falling back to simple detection", file=sys.stderr, flush=True)
        USE_YOLO = False

# Set up a timeout handler to prevent the script from hanging
def timeout_handler(signum, frame):
    print("Processing timed out", file=sys.stderr, flush=True)
    sys.exit(0)  # Exit cleanly

# Get processor timeout from environment variables
TIMEOUT_SECONDS = int(os.environ.get('PROCESSOR_TIMEOUT', 25))
print(f"Setting timeout to {TIMEOUT_SECONDS} seconds", file=sys.stderr, flush=True)

# Get camera details from environment variables
CAMERA_IP = os.environ.get('CAMERA_IP', '192.168.188.176')
CAMERA_USER = os.environ.get('CAMERA_USER', 'admin')
CAMERA_PASS = os.environ.get('CAMERA_PASS', '')
print(f"Camera details: {CAMERA_USER}@{CAMERA_IP}", file=sys.stderr, flush=True)

# Global variables
model = None
previous_frame = None
background_subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=50)

# Initialize YOLO model if we're using it
if USE_YOLO:
    try:
        print("Loading YOLO model...", file=sys.stderr, flush=True)
        model = YOLO('yolov8n.pt')
        
        # Warm up the model with a tiny dummy input
        print("Warming up model...", file=sys.stderr, flush=True)
        dummy_input = np.zeros((160, 160, 3), dtype=np.uint8)
        _ = model(dummy_input, verbose=False, imgsz=160, max_det=1)
        
        # Force garbage collection after model load
        gc.collect()
        print("Model loaded successfully", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"Error loading model: {str(e)}", file=sys.stderr, flush=True)
        USE_YOLO = False

# Function to detect motion in a frame (much faster than YOLO)
def detect_motion(frame, min_area=500):
    global previous_frame, background_subtractor
    
    # Apply background subtraction
    fg_mask = background_subtractor.apply(frame)
    
    # Threshold the mask
    thresh = cv2.threshold(fg_mask, 25, 255, cv2.THRESH_BINARY)[1]
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by area
    detections = []
    for contour in contours:
        if cv2.contourArea(contour) > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            detections.append({
                'class': 'motion',
                'confidence': 0.9,
                'position': {
                    'x1': float(x),
                    'y1': float(y),
                    'x2': float(x + w),
                    'y2': float(y + h)
                }
            })
    
    return detections

def process_batch(frames):
    # Configuration - optimized for speed
    TARGET_WIDTH = 320  # Reduced width but not too small for motion detection
    CONFIDENCE_THRESHOLD = 0.6  # Higher confidence threshold
    MAX_PROCESSING_TIME = 5  # Maximum seconds to spend on a single frame
    
    # Initialize timing
    start_time = datetime.now()
    
    # Process frames in batch
    batch_detections = []
    for frame in frames:
        try:
            # Start timing the processing
            process_start = time.time()
            
            # Convert to numpy array and reshape
            frame = np.frombuffer(frame, dtype=np.uint8)
            
            # Resize frame to reduce processing time - use INTER_NEAREST for speed
            scale = TARGET_WIDTH / max(frame.shape[1], frame.shape[0])
            new_size = (int(frame.shape[1] * scale), int(frame.shape[0] * scale))
            if new_size[0] > 0 and new_size[1] > 0:
                frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_NEAREST)
            
            # Create a timer to ensure we don't exceed MAX_PROCESSING_TIME
            processing_timer = threading.Timer(MAX_PROCESSING_TIME, lambda: print("Processing taking too long, skipping", file=sys.stderr, flush=True))
            processing_timer.start()
            
            # Detect objects
            detections = detect_motion(frame)
            
            # Cancel the timer
            processing_timer.cancel()
            
            # Calculate processing time
            process_time = time.time() - process_start
            
            # Log detection results
            print(f"Found {len(detections)} objects in {process_time:.3f} seconds", file=sys.stderr, flush=True)
            
            # Output results as JSON with proper numpy array handling
            result = {
                'detections': detections,
                'frame_size': {'width': int(frame.shape[1]), 'height': int(frame.shape[0])},
                'timestamp': datetime.now().isoformat(),
                'process_time': float(process_time)
            }
            # Convert numpy arrays to Python native types
            batch_detections.append(json.loads(safe_json_dumps(result)))
        except Exception as e:
            print(f"Error processing frame: {str(e)}", file=sys.stderr, flush=True)
            # Try to clean up memory on error
            gc.collect()
            
            # Make sure we don't hit the system timeout
            if time.time() - start_time > MAX_PROCESSING_TIME:
                print("Processing took too long, exiting cleanly", file=sys.stderr, flush=True)
                sys.exit(0)
                
    return batch_detections

def main():
    # Configuration - optimized for speed
    TARGET_FPS = 0.2  # Process only 1 frame every 5 seconds
    SKIP_FRAMES = 15  # Skip more frames
    
    # Set up timeout handler
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(TIMEOUT_SECONDS - 5)  # Set alarm to 5 seconds less than timeout to ensure clean exit
    
    # Initialize timing
    last_processed = datetime.now()
    frame_interval = timedelta(seconds=1.0/TARGET_FPS)
    
    print(f"Starting processor with: TARGET_FPS={TARGET_FPS}, SKIP_FRAMES={SKIP_FRAMES}", file=sys.stderr, flush=True)
    
    frame_count = 0
    skip_count = 0
    process_count = 0
    start_time = datetime.now()
    frame_mod_count = 0
    
    # Process frames from stdin
    while True:
        # Reset the alarm for each iteration, but leave enough time to exit cleanly
        signal.alarm(TIMEOUT_SECONDS - 5)
        
        current_time = datetime.now()
        
        try:
            # Read frame size with timeout
            header = sys.stdin.buffer.read(8)
            if len(header) != 8:
                print("End of input stream", file=sys.stderr, flush=True)
                break
                
            width = int.from_bytes(header[:4], byteorder='little')
            height = int.from_bytes(header[4:8], byteorder='little')
            
            # Read frame data (3 channels: BGR)
            frame_size = width * height * 3
            frame_data = sys.stdin.buffer.read(frame_size)
            if len(frame_data) != frame_size:
                print("Incomplete frame data", file=sys.stderr, flush=True)
                break
            
            frame_count += 1
            frame_mod_count += 1
            
            # Aggressive frame skipping
            if frame_mod_count % SKIP_FRAMES != 0:
                skip_count += 1
                continue
            
            # Also skip based on time interval
            if current_time - last_processed < frame_interval:
                skip_count += 1
                continue
            
            # Log processing attempt
            print(f"Processing frame {frame_count}", file=sys.stderr, flush=True)
            
            # Print processing stats
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > 0 and process_count % 2 == 0:
                print(f"Stats: {frame_count} frames, {process_count} processed, {skip_count} skipped, {process_count/elapsed:.2f} fps", 
                      file=sys.stderr, flush=True)
            
            process_count += 1
            last_processed = current_time
        except Exception as e:
            print(f"Error reading frame: {str(e)}", file=sys.stderr, flush=True)
            continue
        
        try:
            # Start timing the processing
            process_start = time.time()
            
            # Convert to numpy array and reshape
            frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((height, width, 3))
            
            # Resize frame to reduce processing time - use INTER_NEAREST for speed
            scale = TARGET_WIDTH / max(width, height)
            new_size = (int(width * scale), int(height * scale))
            if new_size[0] > 0 and new_size[1] > 0:
                frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_NEAREST)
            
            # Create a timer to ensure we don't exceed MAX_PROCESSING_TIME
            processing_timer = threading.Timer(MAX_PROCESSING_TIME, lambda: print("Processing taking too long, skipping", file=sys.stderr, flush=True))
            processing_timer.start()
            
            # Detect objects
            detections = []
            
            # Use simple motion detection instead of YOLO (much faster)
            if not USE_YOLO:
                # Convert to grayscale for motion detection
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)
                
                # Run motion detection
                print("Running motion detection", file=sys.stderr, flush=True)
                detections = detect_motion(gray_frame)
            else:
                # Run YOLO detection with extreme optimization
                print(f"Running YOLO inference on {new_size[0]}x{new_size[1]} image", file=sys.stderr, flush=True)
                results = model(
                    frame,
                    conf=CONFIDENCE_THRESHOLD,
                    imgsz=TARGET_WIDTH,
                    max_det=3,  # Severely limit max detections for speed
                    verbose=False,
                    half=True,  # Enable half precision for speed
                    device='cpu',  # Force CPU usage
                    agnostic_nms=True,  # Use agnostic NMS for speed
                )
                
                # Extract detections from YOLO results
                classes_of_interest = ['person', 'car', 'truck']
                for result in results:
                    for box in result.boxes:
                        cls = int(box.cls.item())
                        name = result.names[cls]
                        
                        # Skip classes we're not interested in
                        if name.lower() not in classes_of_interest:
                            continue
                            
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = box.conf.item()
                        
                        # Scale coordinates back to original size
                        if scale != 1.0:
                            x1, x2 = float(x1/scale), float(x2/scale)
                            y1, y2 = float(y1/scale), float(y2/scale)
                        else:
                            x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
                        
                        detections.append({
                            'class': str(name),
                            'confidence': float(conf),
                            'position': {
                                'x1': x1,
                                'y1': y1,
                                'x2': x2,
                                'y2': y2
                            }
                        })
            
            # Cancel the timer
            processing_timer.cancel()
            
            # Calculate processing time
            process_time = time.time() - process_start
            
            # Log detection results
            print(f"Found {len(detections)} objects in {process_time:.3f} seconds", file=sys.stderr, flush=True)
            
            # Output results as JSON
            print(json.dumps({
                'detections': detections,
                'frame_size': {'width': width, 'height': height},
                'timestamp': current_time.isoformat(),
                'frame_count': frame_count,
                'process_time': process_time
            }), flush=True)
            
            # Clear memory aggressively
            del frame
            if 'results' in locals():
                del results
            gc.collect()  # Force garbage collection
            
            # Reset the alarm after successful processing
            signal.alarm(TIMEOUT_SECONDS - 5)
            
        except Exception as e:
            print(f"Error processing frame: {str(e)}", file=sys.stderr, flush=True)
            # Try to clean up memory on error
            gc.collect()
            
            # Make sure we don't hit the system timeout
            if time.time() - process_start > MAX_PROCESSING_TIME:
                print("Processing took too long, exiting cleanly", file=sys.stderr, flush=True)
                sys.exit(0)
                
            continue

if __name__ == '__main__':
    main()
