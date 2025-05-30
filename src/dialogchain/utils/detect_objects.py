#!/usr/bin/env python3
"""
Zewnętrzny skrypt do detekcji obiektów - delegowany przez Camel Router
Można zastąpić dowolnym innym narzędziem/językiem
"""

import sys
import json
import argparse
import os
import base64
import numpy as np
import cv2
from pathlib import Path
from dialogchain.utils.logger import setup_logger
logger = setup_logger(__name__)


# Optional: ultralytics for YOLO
try:
    from ultralytics import YOLO

    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logger.info("Warning: ultralytics not installed, using dummy detection")


def load_config():
    """Load configuration from environment variables set by Camel Router"""
    return {
        "confidence_threshold": float(os.getenv("CONFIG_CONFIDENCE_THRESHOLD", "0.6")),
        "model": os.getenv("CONFIG_MODEL", "yolov8n.pt"),
        "target_objects": os.getenv("CONFIG_TARGET_OBJECTS", "person,car").split(","),
    }


def dummy_detection(frame_data):
    """Dummy detection for when YOLO is not available"""
    return [
        {
            "object_type": "person",
            "confidence": 0.85,
            "bbox": [100, 100, 200, 200],
            "position": "center-center",
        }
    ]


def yolo_detection(frame_data, config):
    """Real YOLO detection"""
    if not HAS_YOLO:
        return dummy_detection(frame_data)

    model = YOLO(config["model"])

    # Decode frame if it's base64 encoded
    if isinstance(frame_data, str):
        try:
            frame_bytes = base64.b64decode(frame_data)
            frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
        except:
            return []
    else:
        frame = frame_data

    results = model(frame)
    detections = []

    class_mapping = {0: "person", 2: "car", 15: "cat", 16: "dog"}

    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                confidence = float(box.conf[0])
                if confidence > config["confidence_threshold"]:
                    class_id = int(box.cls[0])

                    if class_id in class_mapping:
                        object_type = class_mapping[class_id]
                        if object_type in config["target_objects"]:
                            bbox = box.xyxy[0].tolist()

                            # Calculate position
                            x1, y1, x2, y2 = bbox
                            center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                            position = get_position(center_x, center_y)

                            detections.append(
                                {
                                    "object_type": object_type,
                                    "confidence": confidence,
                                    "bbox": bbox,
                                    "position": position,
                                }
                            )

    return detections


def get_position(x, y):
    """Convert coordinates to position description"""
    # Assuming 640x480 frame
    if x < 213:
        horizontal = "left"
    elif x > 427:
        horizontal = "right"
    else:
        horizontal = "center"

    if y < 160:
        vertical = "top"
    elif y > 320:
        vertical = "bottom"
    else:
        vertical = "middle"

    return f"{vertical}-{horizontal}"


def main():
    parser = argparse.ArgumentParser(description="Object Detection Script")
    parser.add_argument("--input", required=True, help="Input JSON file")
    parser.add_argument("--output", help="Output JSON file (optional)")

    args = parser.parse_args()

    # Load configuration from environment
    config = load_config()

    try:
        # Read input data
        with open(args.input, "r") as f:
            input_data = json.load(f)

        # Extract frame data
        frame_data = input_data.get("frame") or input_data.get("data")

        # Perform detection
        detections = yolo_detection(frame_data, config)

        # Prepare output
        output = {
            "timestamp": input_data.get("timestamp"),
            "source": input_data.get("source"),
            "detections": detections,
            "detection_count": len(detections),
        }

        # Output results
        if args.output:
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2)
        else:
    logger.info(json.dumps(output, indent=2))

    except Exception as e:
        error_output = {"error": str(e), "success": False}
    logger.info(json.dumps(error_output, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
