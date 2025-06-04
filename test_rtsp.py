import cv2
import asyncio
import os
from dotenv import load_dotenv

async def test_rtsp_stream(rtsp_uri):
    """Test RTSP stream connection and display first frame"""
    print(f"\n🔍 Testing RTSP connection to: {rtsp_uri}")
    
    cap = cv2.VideoCapture(rtsp_uri)
    
    if not cap.isOpened():
        print("❌ Failed to open RTSP stream")
        return False
    
    print("✅ Successfully connected to RTSP stream")
    print("📊 Stream properties:")
    print(f"  - Frame width: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}")
    print(f"  - Frame height: {int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print(f"  - FPS: {cap.get(cv2.CAP_PROP_FPS)}")
    
    # Try to read one frame
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read frame from stream")
        cap.release()
        return False
    
    print("✅ Successfully read frame from stream")
    
    # Save the frame as an image
    output_path = "test_frame.jpg"
    cv2.imwrite(output_path, frame)
    print(f"💾 Saved test frame to: {os.path.abspath(output_path)}")
    
    cap.release()
    return True

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Get RTSP URI from environment or use a test one
    rtsp_uri = os.getenv("RTSP_URI", "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mov")
    
    print(f"🚀 Starting RTSP connection test...")
    success = asyncio.run(test_rtsp_stream(rtsp_uri))
    
    if success:
        print("\n✅ RTSP test completed successfully!")
    else:
        print("\n❌ RTSP test failed. Check the error messages above.")
    
    print("\n💡 If you're using your own camera, make sure to set the RTSP_URI in your .env file:")
    print(f"RTSP_URI=rtsp://username:password@camera-ip:port/stream")
    print("\nNote: The test used a public RTSP stream. For your camera, replace with actual credentials and IP.")
