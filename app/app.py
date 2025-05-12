from flask import Flask, request, send_from_directory
import os
import cv2

app = Flask(__name__)

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(BASE_DIR, "received_videos")
FRAME_DIR = os.path.join(BASE_DIR, "frames")
GLB_DIR = os.path.join(BASE_DIR, "glb_files")

# 폴더가 없다면 생성
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)
os.makedirs(GLB_DIR, exist_ok=True)

@app.route("/")
def health():
    return "✅ Flask 서버 작동 중"

@app.route("/upload_video", methods=["POST"])
def upload_video():
    file = request.files.get("video")
    if not file:
        return "❌ video 파일 없음", 400

    filename = f"received_{len(os.listdir(VIDEO_DIR))}.mp4"
    save_path = os.path.join(VIDEO_DIR, filename)
    file.save(save_path)
    print(f"💾 영상 저장됨: {save_path}")

    # 프레임 추출
    output_dir = os.path.join(FRAME_DIR, filename.split('.')[0])
    extract_frames(save_path, output_dir)

    return "✅ 영상 업로드 및 프레임 추출 완료"

@app.route("/glb/<filename>")
def serve_glb(filename):
    return send_from_directory(GLB_DIR, filename)

def extract_frames(video_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("❌ 동영상 열기 실패")
        return

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_filename = os.path.join(output_dir, f"frame_{frame_count:04d}.jpg")
        cv2.imwrite(frame_filename, frame)
        print(f"🖼 프레임 저장: {frame_filename}")
        frame_count += 1

    cap.release()
    print("✅ 프레임 추출 완료.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
