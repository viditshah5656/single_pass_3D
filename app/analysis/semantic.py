import numpy as np
import open3d as o3d
import cv2
from pathlib import Path
from typing import List, Dict, Any, Tuple
from ultralytics import YOLO

from app.config import DEVICE, logger


class SemanticAnnotator:
    """Project 2D detections onto reconstructed 3D points with portable inference."""
    def __init__(self, yolo_model: str = "yolov8n.pt", device=None):
        self.device = device or DEVICE
        self.device_name = str(self.device)
        try:
            self.yolo = YOLO(yolo_model)
            self.yolo.to(self.device)
        except Exception as exc:
            logger.warning("Could not load YOLO semantic model: %s", exc)
            self.yolo = None

    def annotate_point_cloud(
        self,
        pcd: o3d.geometry.PointCloud,
        camera_poses: List[Dict[str, Any]],
        camera_calibration: Dict[str, Any],
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        points = np.asarray(pcd.points)
        colors = np.asarray(pcd.colors) if pcd.has_colors() else np.zeros_like(points)
        n_points = len(points)
        if n_points == 0:
            return np.empty(0, dtype=np.int32), []

        logger.info("Annotating %d 3D points on %s", n_points, self.device_name)
        classification = np.full(n_points, 2, dtype=np.int32)

        if pcd.has_colors():
            r, g, b = colors[:, 0], colors[:, 1], colors[:, 2]
            exg = 2.0 * g - r - b
            veg_mask = (exg > 0.08) & (g > r * 1.05) & (g > b * 1.05)
            water_mask = (b > r + 0.05) & (b > g * 0.95) & (r < 0.35)
            classification[veg_mask] = 5
            classification[water_mask] = 9

        K = camera_calibration.get("K")
        if K is None:
            focal = float(camera_calibration.get("focal_px", 0.0))
            principal = camera_calibration.get("principal_pt")
            if focal <= 0 or not principal:
                return classification, []
            K = np.array([[focal, 0.0, principal[0]], [0.0, focal, principal[1]], [0.0, 0.0, 1.0]], dtype=np.float64)

        reg_views = [p for p in camera_poses if p.get("is_registered") and p.get("R") is not None]
        detected_objects: List[Dict[str, Any]] = []
        if self.yolo is not None and reg_views:
            sampled_indices = np.linspace(0, len(reg_views) - 1, min(8, len(reg_views))).astype(int)
            building_pts_accumulator = []
            for idx in sampled_indices:
                view = reg_views[idx]
                img_path = Path(view["file_path"])
                if not img_path.exists():
                    continue
                image = cv2.imread(str(img_path))
                if image is None:
                    continue
                h_img, w_img = image.shape[:2]
                results = self.yolo(image, conf=0.30, verbose=False, device=self.device_name)
                R = np.asarray(view["R"], dtype=np.float64)
                t = np.asarray(view["t"], dtype=np.float64)
                pts_cam = (points @ R.T) + t.reshape(1, 3)
                z_cam = pts_cam[:, 2]
                front_idx = np.where(z_cam > 0.5)[0]
                if len(front_idx) == 0:
                    continue
                u_px = (K[0, 0] * (pts_cam[front_idx, 0] / z_cam[front_idx]) + K[0, 2]).astype(int)
                v_px = (K[1, 1] * (pts_cam[front_idx, 1] / z_cam[front_idx]) + K[1, 2]).astype(int)
                in_bounds = (u_px >= 0) & (u_px < w_img) & (v_px >= 0) & (v_px < h_img)
                valid_pt_indices = front_idx[in_bounds]
                u_valid = u_px[in_bounds]
                v_valid = v_px[in_bounds]

                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    cname = self.yolo.names[cls_id]
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    inside = (u_valid >= x1) & (u_valid <= x2) & (v_valid >= y1) & (v_valid <= y2)
                    matched = valid_pt_indices[inside]
                    if len(matched) and cname in {"building", "house", "roof"}:
                        classification[matched] = 6
                        building_pts_accumulator.append({"pts": points[matched], "conf": conf, "cname": cname})
                    elif len(matched) and cname in {"car", "truck", "bus", "vehicle"}:
                        classification[matched] = 2

        z_vals = points[:, 1]
        ground_datum = float(np.percentile(z_vals, 10))
        bld_count = 0
        bld_indices = np.where(classification == 6)[0]
        if len(bld_indices) >= 10:
            try:
                from sklearn.cluster import DBSCAN
                bld_pts = points[bld_indices]
                clustering = DBSCAN(eps=4.0, min_samples=10).fit(bld_pts[:, [0, 2]])
                for cluster_id in set(clustering.labels_) - {-1}:
                    cluster_pts = bld_pts[clustering.labels_ == cluster_id]
                    if len(cluster_pts) < 10:
                        continue
                    bld_count += 1
                    min_c, max_c = cluster_pts.min(axis=0), cluster_pts.max(axis=0)
                    center_x = float((min_c[0] + max_c[0]) * 0.5)
                    center_z = float((min_c[2] + max_c[2]) * 0.5)
                    roof_y = float(np.percentile(cluster_pts[:, 1], 95))
                    local_ground = (np.abs(points[:, 0] - center_x) < 8.0) & (np.abs(points[:, 2] - center_z) < 8.0) & (classification == 2)
                    ground_y = float(np.percentile(points[local_ground, 1], 15)) if np.any(local_ground) else ground_datum
                    height_m = max(1.5, round(roof_y - ground_y, 1))
                    length_m = round(float(max_c[0] - min_c[0]), 1)
                    width_m = round(float(max_c[2] - min_c[2]), 1)
                    area_m2 = round(length_m * width_m, 1)
                    detected_objects.append({
                        "id": f"BLD-{bld_count:02d}",
                        "type": "Reconstructed Building Structure",
                        "label": f"Building #{bld_count}",
                        "category": "building",
                        "icon": "domain",
                        "x": round(center_x, 2),
                        "y": round(ground_y, 2),
                        "z": round(center_z, 2),
                        "height_m": height_m,
                        "length_m": length_m,
                        "width_m": width_m,
                        "area_m2": area_m2,
                        "volume_m3": round(area_m2 * height_m, 1),
                        "points_count": len(cluster_pts),
                        "confidence": 0.85,
                        "evidence": "3D Multi-View Point Cluster",
                        "asprs_class": 6,
                    })
            except Exception as exc:
                logger.debug("Building clustering notice: %s", exc)

        logger.info("Semantic annotation complete: %d building structures", bld_count)
        return classification, detected_objects
