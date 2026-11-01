import unittest

from downloader import detect_platform, format_bytes, format_duration, is_supported_url


class PlatformDetectionTests(unittest.TestCase):
    def test_youtube_domains(self):
        self.assertEqual(detect_platform("https://www.youtube.com/watch?v=abc"), "YouTube")
        self.assertEqual(detect_platform("https://youtu.be/abc"), "YouTube")

    def test_tiktok_domains(self):
        self.assertEqual(detect_platform("https://www.tiktok.com/@user/video/123"), "TikTok")
        self.assertEqual(detect_platform("https://vm.tiktok.com/abc/"), "TikTok")

    def test_facebook_domains(self):
        self.assertEqual(detect_platform("https://www.facebook.com/watch/?v=123"), "Facebook")
        self.assertEqual(detect_platform("https://fb.watch/abc"), "Facebook")

    def test_reject_unknown_host(self):
        self.assertEqual(detect_platform("https://example.com/video"), "Unsupported")
        self.assertFalse(is_supported_url("https://example.com/video"))

    def test_reject_malformed_url(self):
        self.assertFalse(is_supported_url("not a url"))
        self.assertFalse(is_supported_url("ftp://youtube.com/watch?v=abc"))

    def test_supported_urls(self):
        self.assertTrue(is_supported_url("https://www.youtube.com/watch?v=abc"))
        self.assertTrue(is_supported_url("https://www.tiktok.com/@user/video/123"))
        self.assertTrue(is_supported_url("https://www.facebook.com/reel/123"))

    def test_byte_formatting(self):
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.0 MB")
        self.assertEqual(format_bytes(None), "Unknown")

    def test_duration_formatting(self):
        self.assertEqual(format_duration(75), "01:15")
        self.assertEqual(format_duration(3661), "01:01:01")
        self.assertEqual(format_duration(None), "--:--")


if __name__ == "__main__":
    unittest.main()
