import argparse
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R

def load_camera_poses(path):
    poses = {}
    with open(path, 'r') as f:
        for line in f:
            if line.startswith("#") or len(line.strip().split()) != 10:
                continue
            parts = line.strip().split()
            poses[parts[9]] = {
                'q': list(map(float, parts[1:5])),
                't': list(map(float, parts[5:8]))
            }
    return poses

def quaternion_to_matrix(q):
    return R.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()

def pixel_to_ray(cx, cy, intrinsics, R, t):
    fx, fy, cx0, cy0 = intrinsics
    x = (cx - cx0) / fx
    y = (cy - cy0) / fy
    ray_dir = R.T @ np.array([x, y, 1.0])
    ray_dir /= np.linalg.norm(ray_dir)
    origin = -R.T @ np.array(t)
    return origin, ray_dir

def triangulate(rays):
    A, b = [], []
    for origin, direction in rays:
        d = direction / np.linalg.norm(direction)
        I = np.eye(3)
        A.append(I - np.outer(d, d))
        b.append((I - np.outer(d, d)) @ origin)
    return np.linalg.lstsq(np.sum(A, axis=0), np.sum(b, axis=0), rcond=None)[0]

def save_ply(points, path):
    with open(path, "w") as f:
        f.write(f"ply\nformat ascii 1.0\nelement vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\nend_header\n")
        for pt in points:
            f.write(f"{pt[0]} {pt[1]} {pt[2]}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--center_path", required=True)
    parser.add_argument("--colmap_pose_path", required=True)
    parser.add_argument("--output_ply", required=True)
    args = parser.parse_args()

    intrinsics = (1000, 1000, 960, 540)  # fx, fy, cx, cy
    poses = load_camera_poses(args.colmap_pose_path)

    df = pd.read_csv(args.center_path)

    rays_by_id = {}
    for row in df.itertuples():
        fname = f"frame_{int(row.frame):04d}.png"
        obj_id = int(row.track_id)
        cx = float(row.center_x)
        cy = float(row.center_y)

        if fname not in poses:
            print(f"⚠️ {fname} → COLMAP 포즈 없음, 건너뜀")
            continue

        q, t = poses[fname]['q'], poses[fname]['t']
        R_ = quaternion_to_matrix(q)
        origin, direction = pixel_to_ray(cx, cy, intrinsics, R_, t)
        rays_by_id.setdefault(obj_id, []).append((origin, direction))

    points = [triangulate(rays) for rays in rays_by_id.values() if len(rays) >= 2]
    save_ply(points, args.output_ply)
    print(f"✅ 3D 위치 {len(points)}개 저장 완료: {args.output_ply}")
