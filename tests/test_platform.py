import unittest

from app.platform import choose_torch_device, detect_compute, detect_host


class PlatformRuntimeTests(unittest.TestCase):
    def test_host_detection_has_stable_shape(self):
        host = detect_host()
        self.assertTrue(host.os)
        self.assertTrue(host.machine)
        self.assertGreaterEqual(host.cpu_count, 1)

    def test_compute_candidates_include_cpu(self):
        candidates = detect_compute()
        backends = {item.backend for item in candidates}
        self.assertIn("cpu", backends)
        self.assertTrue(any(item.available for item in candidates if item.backend == "cpu"))

    def test_auto_device_is_one_of_supported_values(self):
        device = choose_torch_device("auto")
        self.assertIn(device, {"cpu", "cuda", "mps"})

    def test_cpu_mode_is_always_valid(self):
        self.assertEqual(choose_torch_device("cpu"), "cpu")


if __name__ == "__main__":
    unittest.main()
