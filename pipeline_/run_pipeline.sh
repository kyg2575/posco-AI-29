#!/bin/bash
set -ex

# 입력 인자 받기
if [ $# -lt 3 ]; then
  echo " 사용법: $0 [이미지 폴더 경로] [워크스페이스_SUFFIX] [CSV 파일 경로]"
  exit 1
fi

IMAGE_DIR="$1"
WORKSPACE_SUFFIX="$2"
CSV_PATH="$3"
WORKSPACE="/home/team/nerf/${WORKSPACE_SUFFIX}"

echo " 워크스페이스: $WORKSPACE"
echo " 이미지 경로: $IMAGE_DIR"
echo " CSV 파일 경로: $CSV_PATH"

if [ ! -f "$CSV_PATH" ]; then
  echo " CSV 파일이 존재하지 않습니다: $CSV_PATH"
  exit 1
fi

# [1] DB 생성 및 Feature 추출 (GPU → CPU 변경)
colmap feature_extractor \
    --database_path "$WORKSPACE/database.db" \
    --image_path "$IMAGE_DIR" \
    --ImageReader.single_camera 1 \
    --ImageReader.camera_model PINHOLE \
    --SiftExtraction.use_gpu 0

# [2] Feature 매칭 (GPU → CPU 변경)
colmap exhaustive_matcher \
    --database_path "$WORKSPACE/database.db" \
    --SiftMatching.use_gpu 0

# [3] Mapping (sparse 생성)
mkdir -p "$WORKSPACE/sparse/0"
colmap mapper \
    --database_path "$WORKSPACE/database.db" \
    --image_path "$IMAGE_DIR" \
    --output_path "$WORKSPACE/sparse/0" \
    --Mapper.num_threads 8

# [4] COLMAP image_undistorter
colmap image_undistorter \
 --image_path "$IMAGE_DIR" \
 --input_path "$WORKSPACE/sparse/0" \
 --output_path "$WORKSPACE/dense" \
 --output_type COLMAP \
 --max_image_size 2000

# [5] COLMAP 모델 변환 (TXT 포맷으로)
colmap model_converter \
 --input_path "$WORKSPACE/sparse/0" \
 --output_path "$WORKSPACE/sparse/0" \
 --output_type TXT

# [6] transforms.json 생성
python scripts/colmap2nerf.py \
  --text "$WORKSPACE/sparse/0" \
  --images "$IMAGE_DIR" \
  --out "$WORKSPACE/transforms.json" \
  --aabb_scale 16

# [7] transforms.json 절대경로로 수정
pip install trimesh --quiet
python3 << EOF
import json, os
json_path = "$WORKSPACE/transforms.json"
with open(json_path, 'r') as f:
    data = json.load(f)

base_path = os.path.abspath(os.path.join("$WORKSPACE", "images"))
for frame in data["frames"]:
    filename = os.path.basename(frame["file_path"])
    frame["file_path"] = os.path.join(base_path, filename)

with open(json_path, 'w') as f:
    json.dump(data, f, indent=2)

print(" transforms.json 경로 절대경로로 수정 완료")
EOF

# [8] 중심좌표 CSV 기반 ray-tracing → ply
python /home/team/instant-ngp/scripts/pipeline/run_pipeline.py \
  --center_path "$CSV_PATH" \
  --colmap_pose_path "$WORKSPACE/sparse/0/images.txt" \
  --output_ply "$WORKSPACE/defect_points.ply"

# [9] 3D Bounding Box 메쉬 생성
python /home/team/instant-ngp/scripts/pipeline/box3d_generator.py \
  --csv_path "$CSV_PATH" \
  --output_path "$WORKSPACE/model.ply"

# [10] instant-ngp 학습 및 메쉬 저장
python scripts/run.py \
  --scene "$WORKSPACE" \
  --save_mesh "$WORKSPACE/model.ply" \
  --marching_cubes_res 256 \
  --train

# [11] 메쉬 스케일링 및 디시메이션
python3 << EOF
import open3d as o3d
import numpy as np

mesh = o3d.io.read_triangle_mesh("$WORKSPACE/model.ply")
mesh.compute_vertex_normals()
bbox = mesh.get_axis_aligned_bounding_box()
center = bbox.get_center()
scale_factor = 1 / np.linalg.norm(bbox.max_bound - bbox.min_bound)
mesh.translate(-center)
mesh.scale(scale_factor, center=(0, 0, 0))
mesh = mesh.filter_smooth_laplacian(number_of_iterations=5)
mesh.compute_vertex_normals()
mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=100000)
mesh.compute_vertex_normals()
o3d.io.write_triangle_mesh("$WORKSPACE/scene_mesh_refined.ply", mesh)
print(" 메쉬 스케일링, 스무딩, 디시메이션 완료 및 저장")
EOF

# [12] 최신 메쉬 병합
LATEST_MESH=$(ls -t "$WORKSPACE/mesh_stage0"/*.ply 2>/dev/null | head -n1)
if [ ! -f "$LATEST_MESH" ]; then
  echo " nerf2mesh 결과 메쉬가 없습니다: $LATEST_MESH"
  exit 1
fi
echo " 최신 메쉬 선택됨: $LATEST_MESH"

python3 << EOF
import open3d as o3d
scene_path = "$LATEST_MESH"
box_path = "$WORKSPACE/model.ply"
output_path = "$WORKSPACE/combined_mesh.ply"
scene = o3d.io.read_triangle_mesh(scene_path)
boxes = o3d.io.read_triangle_mesh(box_path)
combined = scene + boxes
o3d.io.write_triangle_mesh(output_path, combined)
print(" combined_mesh.ply 저장 완료 (자동 선택된 mesh + box)")
EOF

# [13] GLB 변환
python3 << EOF
import open3d as o3d
import numpy as np
mesh = o3d.io.read_triangle_mesh("$WORKSPACE/combined_mesh.ply")
mesh.compute_vertex_normals()
R = mesh.get_rotation_matrix_from_xyz((np.pi / 2, 0, 0))
mesh.rotate(R, center=(0, 0, 0))
o3d.io.write_triangle_mesh("$WORKSPACE/combined_mesh.glb", mesh, write_vertex_colors=True)
print(" combined_mesh.glb 저장 완료 (앱 전송용, 색상 + 좌표계 반영)")
EOF
