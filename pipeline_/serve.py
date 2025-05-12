from flask import Flask, request, jsonify
import os
import subprocess
import datetime

app = Flask(__name__)

UPLOAD_DIR = "/home/piai/uploads"
PIPELINE_SCRIPT = "/home/piai/instant-ngp/scripts/pipeline/run_pipeline.sh"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    print(f"✅ 저장 완료: {save_path}")

    # 워크스페이스 이름 생성 (타임스탬프 포함)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_name = f"{os.path.splitext(filename)[0]}_{timestamp}"

    # 파이프라인 실행
    subprocess.Popen([
        "bash", PIPELINE_SCRIPT, save_path, workspace_name
    ])

    return jsonify({
        "message": "업로드 성공 및 파이프라인 실행 시작!",
        "saved_path": save_path,
        "workspace": workspace_name
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
