import open3d as o3d

# 메시 로드
mesh = o3d.io.read_triangle_mesh("/home/piai/nerf/IMG_8629/combined_mesh_reconstructed.glb")

# 노멀 재계산 (정방향)
mesh.compute_vertex_normals()

# 색상 없으면 회색 지정
if not mesh.has_vertex_colors():
    mesh.paint_uniform_color([0.6, 0.6, 0.6])  # 회색 계열

# 다시 저장
o3d.io.write_triangle_mesh("/home/piai/nerf/IMG_8629/combined_mesh_fixed.glb", mesh)
print("✅ fixed.glb 저장 완료 (조명 및 색상 문제 보완)")
