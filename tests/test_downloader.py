import unittest

from downloader import (\n    detect_platform, format_bytes, format_duration, is_http_url,\n    is_supported_url, is_tiktok_challenge_error,\n)


class TikTokChallengeDetectionTests(unittest.TestCase):
    def test_known_tiktok_challenge_errors_are_recognised(self):
        self.assertTrue(is_tiktok_challenge_error("Unexpected response from webpage request"))
        self.assertTrue(is_tiktok_challenge_error("Unable to extract challenge data"))
        self.assertTrue(is_tiktok_challenge_error("Unable to extract universal data for rehydration"))

    def test_unrelated_errors_are_not_marked_as_tiktok_challenges(self):
        self.assertFalse(is_tiktok_challenge_error("HTTP Error 404: Not Found"))
        self.assertFalse(is_tiktok_challenge_error("This video is private"))


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

    def test_reject_unknown_host_from_main_platform_filter(self):
        self.assertEqual(detect_platform("https://example.com/video"), "Unsupported")
        self.assertFalse(is_supported_url("https://example.com/video"))

    def test_other_dl_accepts_generic_http_websites(self):
        self.assertTrue(is_http_url("https://example.com/video"))
        self.assertTrue(is_http_url("https://cdn.example.com/media/clip.mp4"))
        self.assertFalse(is_supported_url("https://example.com/video"))
        self.assertFalse(is_http_url("file:///C:/video.mp4"))
        self.assertFalse(is_http_url("javascript:alert(1)"))
        self.assertFalse(is_http_url("not a url"))

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
