#!/bin/bash
set -e

# 사용법 확인
if [ $# -lt 1 ]; then
  echo "❌ 사용법: $0 [워크스페이스_SUFFIX]"
  exit 1
fi

WORKSPACE_SUFFIX="$1"
WORKSPACE="/home/piai/nerf/${WORKSPACE_SUFFIX}"

echo "📁 병합 및 GLB 변환 시작!"
echo "🔧 워크스페이스: $WORKSPACE"

python3 << EOF
import open3d as o3d
import os

scene_path = os.path.join("$WORKSPACE", "scene_mesh.ply")
box_path = os.path.join("$WORKSPACE", "model.ply")
combined_path = os.path.join("$WORKSPACE", "combined_mesh.ply")
glb_path = os.path.join("$WORKSPACE", "combined_mesh.glb")

scene = o3d.io.read_triangle_mesh(scene_path)
box = o3d.io.read_triangle_mesh(box_path)

combined = scene + box
o3d.io.write_triangle_mesh(combined_path, combined)
print("✅ combined_mesh.ply 저장 완료")

o3d.io.write_triangle_mesh(glb_path, combined)
print("✅ combined_mesh.glb 저장 완료 (앱 전송용)")
EOF
