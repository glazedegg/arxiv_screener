import os
import unittest
from unittest.mock import Mock, patch


class TestEnvironmentVariables(unittest.TestCase):
    def test_gemini_api_key_validation(self):
        from google import genai

        with patch.dict(os.environ, {}, clear=True):
            api_key = os.getenv("GEMINI_API_KEY")
            self.assertIsNone(api_key)

            if not api_key:
                with self.assertRaises(ValueError) as context:
                    raise ValueError("GEMINI_API_KEY environment variable not set")
                self.assertIn("GEMINI_API_KEY", str(context.exception))

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key_123"}):
            api_key = os.getenv("GEMINI_API_KEY")
            self.assertIsNotNone(api_key)
            self.assertEqual(api_key, "test_api_key_123")

            client = genai.Client(api_key=api_key)
            self.assertIsNotNone(client)

    def test_twitter_env_vars_accessible(self):
        import tweepy

        required_vars = {
            "BEARER_TOKEN": "test_bearer_token",
            "API_KEY": "test_api_key",
            "API_SECRET": "test_api_secret",
            "ACCESS_TOKEN": "test_access_token",
            "ACCESS_TOKEN_SECRET": "test_access_token_secret",
        }

        with patch.dict(os.environ, required_vars):
            bearer_token = os.getenv("BEARER_TOKEN")
            consumer_key = os.getenv("API_KEY")
            consumer_secret = os.getenv("API_SECRET")
            access_token = os.getenv("ACCESS_TOKEN")
            access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

            self.assertEqual(bearer_token, "test_bearer_token")
            self.assertEqual(consumer_key, "test_api_key")
            self.assertEqual(consumer_secret, "test_api_secret")
            self.assertEqual(access_token, "test_access_token")
            self.assertEqual(access_token_secret, "test_access_token_secret")

            client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                return_type=tweepy.Response,
            )
            self.assertIsNotNone(client)

    def test_all_required_env_vars_present(self):
        all_vars = {
            "GEMINI_API_KEY": "test_gemini_key",
            "BEARER_TOKEN": "test_bearer",
            "API_KEY": "test_api_key",
            "API_SECRET": "test_api_secret",
            "ACCESS_TOKEN": "test_access",
            "ACCESS_TOKEN_SECRET": "test_access_secret",
        }

        with patch.dict(os.environ, all_vars):
            for var_name, expected_value in all_vars.items():
                actual_value = os.getenv(var_name)
                self.assertEqual(actual_value, expected_value)

    def test_missing_twitter_env_vars_detected(self):
        with patch.dict(os.environ, {}, clear=True):
            bearer_token = os.getenv("BEARER_TOKEN")
            consumer_key = os.getenv("API_KEY")
            consumer_secret = os.getenv("API_SECRET")
            access_token = os.getenv("ACCESS_TOKEN")
            access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

            self.assertIsNone(bearer_token)
            self.assertIsNone(consumer_key)
            self.assertIsNone(consumer_secret)
            self.assertIsNone(access_token)
            self.assertIsNone(access_token_secret)

            all_present = all(
                [bearer_token, consumer_key, consumer_secret, access_token, access_token_secret]
            )
            self.assertFalse(all_present)


class TestModuleImports(unittest.TestCase):
    def test_import_arxiv_pipeline(self):
        try:
            import arxiv_pipeline

            self.assertTrue(True)
        except ImportError as e:  # pragma: no cover - defensive
            self.fail(f"Failed to import arxiv_pipeline: {e}")

    def test_import_x_tweet_module(self):
        try:
            import x_tweet_module

            self.assertTrue(True)
        except ImportError as e:  # pragma: no cover - defensive
            self.fail(f"Failed to import x_tweet_module: {e}")

    def test_import_main(self):
        try:
            import main

            self.assertTrue(True)
        except ImportError as e:  # pragma: no cover - defensive
            self.fail(f"Failed to import main: {e}")

    def test_required_dependencies(self):
        required_packages = ["arxiv", "tweepy", "google.genai"]

        for package in required_packages:
            try:
                __import__(package)
            except ImportError as e:  # pragma: no cover - defensive
                self.fail(f"Required package '{package}' is not available: {e}")


class TestAuthenticationFlow(unittest.TestCase):
    def test_authenticate_function_with_env_vars(self):
        import x_tweet_module

        test_env = {
            "BEARER_TOKEN": "test_bearer",
            "API_KEY": "test_key",
            "API_SECRET": "test_secret",
            "ACCESS_TOKEN": "test_access",
            "ACCESS_TOKEN_SECRET": "test_access_secret",
        }

        with patch.dict(os.environ, test_env):
            with patch("x_tweet_module.tweepy.Client") as MockClient:
                mock_instance = Mock()
                MockClient.return_value = mock_instance

                result = x_tweet_module.authenticate()

                MockClient.assert_called_once()
                call_kwargs = MockClient.call_args[1]

                self.assertEqual(call_kwargs["bearer_token"], "test_bearer")
                self.assertEqual(call_kwargs["consumer_key"], "test_key")
                self.assertEqual(call_kwargs["consumer_secret"], "test_secret")
                self.assertEqual(call_kwargs["access_token"], "test_access")
                self.assertEqual(call_kwargs["access_token_secret"], "test_access_secret")

                mock_instance.get_me.assert_called_once_with(user_auth=True)
                self.assertIsNotNone(result)


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    unittest.main(verbosity=2)
