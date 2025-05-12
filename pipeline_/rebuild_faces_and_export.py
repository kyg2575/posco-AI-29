import open3d as o3d

# 원본 병합된 point mesh
pcd = o3d.io.read_point_cloud("/home/piai/nerf/IMG_8629/combined_mesh.ply")

# Poisson sampling → 삼각형 생성 (Ball Pivoting Algorithm)
pcd.estimate_normals()
mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=9)

# 저장
o3d.io.write_triangle_mesh("/home/piai/nerf/IMG_8629/combined_mesh_reconstructed.glb", mesh)
print("✅ 삼각형 생성 완료 → GLB 저장 완료!")
