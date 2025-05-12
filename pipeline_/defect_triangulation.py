import pandas as pd
import numpy as np
from scipy.spatial.transform import Rotation as R
import os
import argparse

def load_cameras(path):
    cam_intrinsics = {}
    with open(path, 'r') as f:
        for line in f:
            if line.startswith("#") or line.strip() == "":
                continue
            parts = line.strip().split()
            cam_id = int(parts[0])
            fx = float(parts[4])
            cx = float(parts[5])
            cy = float(parts[6])
            cam_intrinsics[cam_id] = (fx, cx, cy)
    return cam_intrinsics

def load_images(path):
    poses = {}
    with open(path, 'r') as f:
        lines = f.readlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#") or line.strip() == "":
                i += 1
                continue
            parts = line.strip().split()
            qw, qx, qy, qz = map(float, parts[1:5])
            tx, ty, tz = map(float, parts[5:8])
            cam_id = int(parts[8])
            name = parts[9]
            rot = R.from_quat([qx, qy, qz, qw]).as_matrix()
            t = np.array([tx, ty, tz])
            poses[name] = {'R': rot, 't': t, 'cam_id': cam_id}
            i += 2
    return poses

def pixel_to_ray(x, y, fx, cx, cy):
    x_cam = (x - cx) / fx
    y_cam = (y - cy) / fx
    return np.array([x_cam, y_cam, 1.0])

def triangulate_rays(origins, directions):
    A, b = [], []
    for o, d in zip(origins, directions):
        d = d / np.linalg.norm(d)
        I = np.eye(3)
        A.append(I - np.outer(d, d))
        b.append((I - np.outer(d, d)) @ o)
    A = np.concatenate(A, axis=0)
    b = np.concatenate(b, axis=0)
    return np.linalg.lstsq(A, b, rcond=None)[0]

def save_ply(points, output_path):
    radius = 0.2  # 박스 반 길이
    vertex_offsets = [
        [-radius, -radius, -radius],
        [-radius, -radius,  radius],
        [-radius,  radius, -radius],
        [-radius,  radius,  radius],
        [ radius, -radius, -radius],
        [ radius, -radius,  radius],
        [ radius,  radius, -radius],
        [ radius,  radius,  radius],
    ]

    face_indices = [
        [0, 1, 3], [0, 3, 2],  # front
        [4, 6, 7], [4, 7, 5],  # back
        [0, 4, 5], [0, 5, 1],  # bottom
        [2, 3, 7], [2, 7, 6],  # top
        [0, 2, 6], [0, 6, 4],  # left
        [1, 5, 7], [1, 7, 3],  # right
    ]

    vertices = []
    faces = []

    for x, y, z, _ in points:
        base_idx = len(vertices)
        for dx, dy, dz in vertex_offsets:
            vertices.append([x + dx, y + dy, z + dz])
        for face in face_indices:
            faces.append([base_idx + i for i in face])

    with open(output_path, 'w') as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(vertices)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write(f"element face {len(faces)}\n")
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")

        for x, y, z in vertices:
            f.write(f"{x} {y} {z} 255 0 0\n")  # 항상 빨간색

        for face in faces:
            f.write(f"3 {' '.join(map(str, face))}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=str, required=True)
    args = parser.parse_args()

    w = args.workspace
    center_path = os.path.join(w, "tracking_with_cls.csv")
    images_path = os.path.join(w, "sparse/0/images.txt")
    cameras_path = os.path.join(w, "sparse/0/cameras.txt")
    output_path = os.path.join(w, "defect_points.ply")

    df = pd.read_csv(center_path, encoding='utf-8-sig')

    if not all(col in df.columns for col in ['frame', 'track_id', 'class', 'center_x', 'center_y']):
        print("❌ CSV 열 이름이 일치하지 않습니다. 현재 열 목록:", df.columns.tolist())
        return

    poses = load_images(images_path)
    intrinsics = load_cameras(cameras_path)

    grouped = df.groupby('track_id')
    points = []

    for obj_id, group in grouped:
        origins, directions = [], []
        cls_name = group['class'].values[0]

        for _, row in group.iterrows():
            fname_raw = str(row['frame']).strip()
            if fname_raw.replace('.0', '').isdigit():
                fname_core = f"frame_{int(float(fname_raw)):04d}"
            else:
                fname_core = fname_raw.split('.')[0]

            candidates = [f"{fname_core}.jpg", f"{fname_core}.jpeg", f"{fname_core}.png"]
            fname = None
            for c in candidates:
                if c in poses:
                    fname = c
                    break
            if fname is None:
                print(f"⚠️ 프레임 {fname_core}(.jpg/.jpeg/.png) 이 images.txt에 없습니다.")
                continue

            pose = poses[fname]
            R_w2c = pose['R']
            t_w2c = pose['t']
            fx, cx, cy = intrinsics[pose['cam_id']]
            ray_cam = pixel_to_ray(row['center_x'], row['center_y'], fx, cx, cy)
            ray_world = R_w2c.T @ ray_cam
            cam_origin = -R_w2c.T @ t_w2c
            origins.append(cam_origin)
            directions.append(ray_world)

        if len(origins) >= 2:
            pt3d = triangulate_rays(origins, directions)
            points.append([*pt3d, cls_name])

    save_ply(points, output_path)
    print(f"✅ Done. Saved {len(points)} points to {output_path}")

if __name__ == "__main__":
    main()
