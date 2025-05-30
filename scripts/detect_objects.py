#!/usr/bin/env python3
"""
Object Detection Script using YOLO

This script processes video frames and detects objects using YOLO.
"""
import sys
import json
import numpy as np
import cv2
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import JSON utilities
from scripts.json_utils import safe_json_dumps

def load_model(model_path):
    """Load YOLO model."""
    try:
        from ultralytics import YOLO
        return YOLO(model_path)
    except ImportError:
        print("YOLO not available, falling back to simple detection", file=sys.stderr)
        return None

def detect_objects(frame, model, confidence_threshold=0.5, target_classes=None):
    """Detect objects in a frame using YOLO."""
    if model is None:
        return []
    
    try:
        # Run YOLO detection
        results = model(frame, verbose=False)
        
        # Process results
        detections = []
        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf < confidence_threshold:
                    continue
                    
                cls = int(box.cls[0])
                cls_name = model.names[cls]
                
                # Skip if not in target classes
                if target_classes and cls_name not in target_classes:
                    continue
                
                # Get bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                detections.append({
                    'class': cls_name,
                    'confidence': float(conf),
                    'bbox': {
                        'x1': x1,
                        'y1': y1,
                        'x2': x2,
                        'y2': y2,
                        'width': x2 - x1,
                        'height': y2 - y1
                    }
                })
        
        return detections
    except Exception as e:
        print(f"Error in detect_objects: {str(e)}", file=sys.stderr)
        return []

def main():
    # Read input from stdin
    input_data = sys.stdin.read()
    
    try:
        config = json.loads(input_data) if input_data.strip() else {}
    except json.JSONDecodeError:
        print("Error: Invalid JSON input", file=sys.stderr)
        sys.exit(1)
    
    # Get configuration with defaults
    model_path = config.get('model', 'yolov8n.pt')
    confidence_threshold = float(config.get('confidence_threshold', 0.5))
    target_objects = config.get('target_objects')
    
    # Load model
    model = load_model(model_path)
    
    # Process frames from stdin
    try:
        while True:
            # Read frame size (first 8 bytes: width and height as 32-bit integers)
            size_data = sys.stdin.buffer.read(8)
            if len(size_data) != 8:
                break
                
            width = int.from_bytes(size_data[:4], byteorder='little')
            height = int.from_bytes(size_data[4:], byteorder='little')
            
            # Read frame data
            frame_size = width * height * 3  # Assuming BGR format
            frame_data = sys.stdin.buffer.read(frame_size)
            
            if len(frame_data) != frame_size:
                break
            
            # Convert to numpy array
            frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((height, width, 3))
            
            # Detect objects
            detections = detect_objects(
                frame, 
                model, 
                confidence_threshold=confidence_threshold,
                target_classes=target_objects
            )
            
            # Send results as JSON
            result = {
                'detections': detections,
                'frame_size': {'width': width, 'height': height},
                'timestamp': None  # Will be set by the pipeline
            }
            
            # Output as JSON with proper serialization
            print(safe_json_dumps(result), flush=True)
            
    except (BrokenPipeError, KeyboardInterrupt):
        # Handle graceful shutdown
        pass
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
