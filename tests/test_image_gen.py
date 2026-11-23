import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class WorkersAiImageHelpersTest(unittest.TestCase):
    def test_run_url_uses_account_and_flux2_klein_4b(self):
        url = main.workers_ai_image_url("acc-123")
        self.assertEqual(
            url,
            "https://api.cloudflare.com/client/v4/accounts/acc-123/ai/run/@cf/black-forest-labs/flux-2-klein-4b",
        )

    def test_decode_envelope_image_field(self):
        payload = {"success": True, "result": {"image": "ZmFrZS1pbWFnZQ=="}}
        decoded = main.decode_workers_ai_image(
            json.dumps(payload).encode(), "application/json"
        )
        self.assertEqual(decoded, b"fake-image")

    def test_decode_raw_image_bytes(self):
        jpeg = b"\xff\xd8\xff" + b"raw"
        decoded = main.decode_workers_ai_image(jpeg, "image/jpeg")
        self.assertEqual(decoded, jpeg)

    def test_decode_failed_envelope_raises(self):
        payload = {"success": False, "errors": [{"message": "quota"}]}
        with self.assertRaises(RuntimeError):
            main.decode_workers_ai_image(
                json.dumps(payload).encode(), "application/json"
            )


class GenerateWeatherImageTest(unittest.TestCase):
    def test_returns_false_without_cloudflare_token(self):
        env = {
            "CLOUDFLARE_ACCOUNT_ID": "acc",
            "CF_AI_GATEWAY_ID": "default",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("CLOUDFLARE_API_TOKEN", None)
            with mock.patch("urllib.request.urlopen") as urlopen:
                with mock.patch("time.sleep"):
                    with tempfile.TemporaryDirectory() as tmp:
                        result = main.generate_weather_image(
                            {"text": "晴", "temp": "25"},
                            {},
                            Path(tmp) / "cover.png",
                        )
        urlopen.assert_not_called()
        self.assertFalse(result)

    def test_posts_through_ai_gateway_and_writes_file(self):
        raw = b"\x89PNG\r\n\x1a\n" + b"ok"
        response = mock.MagicMock()
        response.headers.get.return_value = "image/png"
        response.read.return_value = raw
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        env = {
            "CLOUDFLARE_ACCOUNT_ID": "acc-123",
            "CLOUDFLARE_API_TOKEN": "tok",
            "CF_AI_GATEWAY_ID": "weather",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
                with tempfile.TemporaryDirectory() as tmp:
                    out = Path(tmp) / "cover.png"
                    ok = main.generate_weather_image(
                        {"text": "晴", "temp": "25"}, {}, out
                    )
                    self.assertTrue(ok)
                    self.assertEqual(out.read_bytes(), raw)
        req = urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, main.workers_ai_image_url("acc-123"))
        self.assertEqual(req.get_header("Cf-aig-gateway-id"), "weather")


if __name__ == "__main__":
    unittest.main()
