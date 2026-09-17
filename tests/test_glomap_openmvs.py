import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.config import PipelineConfig, SfMConfig, VideoConfig, find_glomap_binary
from app.video.extractor import VideoExtractor, VideoMetadata
from app.reconstruction.openmvs import DenseReconstructor, find_openmvs_binary
from app.reconstruction.colmap import SfMPipeline
from app.geospatial.gps import GPSExtractor, TelemetryPoint
from app.geospatial.georeference import Georeferencer


class TestReconstructionBackends(unittest.TestCase):
    def test_01_glomap_executable_detection_is_optional(self):
        path = find_glomap_binary()
        if path:
            self.assertTrue(os.access(path, os.X_OK))
        else:
            self.assertIsNone(path)

    def test_02_openmvs_executable_detection_is_explicit(self):
        names = ["InterfaceCOLMAP", "DensifyPointCloud", "ReconstructMesh", "TextureMesh"]
        detected = {name: find_openmvs_binary(name) for name in names}
        for name, path in detected.items():
            if path:
                self.assertTrue(os.access(path, os.X_OK))

    def test_03_sparse_model_dir_detection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ws = Path(tmp_dir)
            sfm = SfMPipeline(ws)
            self.assertEqual(sfm.detect_sparse_model_dir(), ws / "sparse")
            sub_0 = ws / "sparse" / "0"
            sub_0.mkdir(parents=True, exist_ok=True)
            (sub_0 / "cameras.bin").write_bytes(b"dummy")
            self.assertEqual(sfm.detect_sparse_model_dir(), sub_0)

    def test_04_openmvs_output_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            recon = DenseReconstructor(tmp_dir)
            if not recon.is_openmvs_available():
                with self.assertRaises(RuntimeError):
                    recon.reconstruct([], [], {})
            else:
                with self.assertRaises((RuntimeError, subprocess.CalledProcessError)):
                    recon.run_openmvs()

    def test_05_explicit_telemetry_handling(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            srt_file = Path(tmp_dir) / "flight.srt"
            srt_file.write_text("1\n00:00:01,000 --> 00:00:02,000\n[latitude: 37.7749] [longitude: -122.4194] [rel_alt: 50.5 abs_alt: 50.5]\n")
            points = GPSExtractor().parse_srt(srt_file)
            self.assertEqual(len(points), 1)
            self.assertAlmostEqual(points[0].lat, 37.7749)
            self.assertAlmostEqual(points[0].lon, -122.4194)
            self.assertAlmostEqual(points[0].alt, 50.5)

    def test_06_gps_to_frame_interpolation(self):
        extractor = GPSExtractor()
        raw = [TelemetryPoint(0.0, 37.7749, -122.4194, 50.0), TelemetryPoint(10.0, 37.7750, -122.4195, 55.0)]
        interp = extractor.interpolate_telemetry(raw, [0.0, 10.0])
        self.assertEqual(len(interp), 2)
        self.assertAlmostEqual(interp[0].lat, 37.7749)
        self.assertAlmostEqual(interp[1].lat, 37.7750)

    def test_07_local_coordinates_without_gps(self):
        georef = Georeferencer()
        self.assertFalse(georef.is_georeferenced)
        self.assertEqual(georef.crs_name, "Local (Non-georeferenced)")

    def test_08_no_synthetic_gps_fallback(self):
        extractor = GPSExtractor()
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = extractor.extract_flight_telemetry(Path(tmp_dir) / "novideo.mp4", [Path(tmp_dir) / "frame_0.png"], duration_sec=5.0)
            self.assertIsNone(result)

    def test_09_no_synthetic_dense_fallback(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            recon = DenseReconstructor(tmp_dir)
            if not recon.is_openmvs_available():
                with self.assertRaises(RuntimeError):
                    recon.reconstruct([], [], {})

    def test_10_rejects_portrait_non_aerial_input(self):
        extractor = VideoExtractor(VideoConfig(capture_profile="aerial_drone"))
        metadata = VideoMetadata(60.0, 1080, 1920, 660, 11.0, "mp4")
        with self.assertRaisesRegex(ValueError, "portrait street/handheld"):
            extractor.validate_capture_profile(metadata)


if __name__ == "__main__":
    unittest.main()
