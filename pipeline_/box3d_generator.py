import numpy as np
import pandas as pd
import open3d as o3d
import cv2
import argparse

def triangulate_points(proj_matrices, points_2d):
    # OpenCV triangulation
    points_4d_hom = cv2.triangulatePoints(proj_matrices[0], proj_matrices[1],
                                          points_2d[0].T, points_2d[1].T)
    points_3d = points_4d_hom[:3, :] / points_4d_hom[3, :]
    return points_3d.T

def create_wireframe_box(center, size, color):
    s = size / 2
    points = np.array([
        [s, s, s], [-s, s, s], [-s, -s, s], [s, -s, s],
        [s, s, -s], [-s, s, -s], [-s, -s, -s], [s, -s, -s]
    ]) + center

    lines = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7]
    ]

    colors = [color for _ in lines]

    line_set = o3d.geometry.LineSet(
        points=o3d.utility.Vector3dVector(points),
        lines=o3d.utility.Vector2iVector(lines)
    )
    line_set.colors = o3d.utility.Vector3dVector(colors)
    return line_set

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path", required=True)
    parser.add_argument("--output_path", required=True)
    parser.add_argument("--box_size", type=float, default=0.1)
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path)

    # 임시 예시용 projection matrix (실제 값으로 교체 필수)
    proj_matrix_1 = np.eye(3, 4)
    proj_matrix_2 = np.eye(3, 4)
    proj_matrix_2[0, 3] = -1.0  # 두 번째 카메라는 오른쪽으로 1m 이동한 예시

    all_lines = o3d.geometry.LineSet()
    unique_ids = df['track_id'].unique()

    np.random.seed(42)
    colors_map = {tid: np.random.rand(3) for tid in unique_ids}

    for tid in unique_ids:
        df_tid = df[df['track_id'] == tid]

        if len(df_tid) < 2:
            continue  # 삼각측량은 최소 두 프레임 필요

        # 첫 번째와 두 번째 관측만 사용한 예시
        points_2d_cam1 = df_tid[['center_x', 'center_y']].iloc[0].values.reshape(1, 2)
        points_2d_cam2 = df_tid[['center_x', 'center_y']].iloc[1].values.reshape(1, 2)

        # 실제 사용 시 2D 좌표를 정규화된 카메라 좌표로 변환해야 함
        points_2d = [points_2d_cam1, points_2d_cam2]
        proj_matrices = [proj_matrix_1, proj_matrix_2]

        points_3d = triangulate_points(proj_matrices, points_2d)

        # 박스 생성 (첫 번째 추정 위치 사용)
        center_3d = points_3d[0]
        color = colors_map[tid]
        box = create_wireframe_box(center_3d, args.box_size, color)

        all_lines += box

    o3d.io.write_line_set(args.output_path, all_lines)
    print(f"✅ 삼각측량 기반 track_id별 박스 생성 완료: {args.output_path}")
