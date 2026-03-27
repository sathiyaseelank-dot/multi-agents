import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from config import TestingConfig
import database
from routes.hi import validate_hi_request, get_greeting


class TestValidateHiRequest(unittest.TestCase):
    def test_none_data(self):
        errors = validate_hi_request(None)
        self.assertIn("No data provided", errors)

    def test_empty_data(self):
        errors = validate_hi_request({})
        self.assertIn("Name is required", errors)

    def test_missing_name(self):
        errors = validate_hi_request({"other": "field"})
        self.assertIn("Name is required", errors)

    def test_name_empty_string(self):
        errors = validate_hi_request({"name": ""})
        self.assertIn("Name is required", errors)

    def test_name_whitespace_only(self):
        errors = validate_hi_request({"name": "   "})
        self.assertIn("Name cannot be empty", errors)

    def test_name_integer_type(self):
        errors = validate_hi_request({"name": 123})
        self.assertIn("Name must be a string", errors)

    def test_name_list_type(self):
        errors = validate_hi_request({"name": ["John"]})
        self.assertIn("Name must be a string", errors)

    def test_name_dict_type(self):
        errors = validate_hi_request({"name": {"first": "John"}})
        self.assertIn("Name must be a string", errors)

    def test_name_boolean_type(self):
        errors = validate_hi_request({"name": True})
        self.assertIn("Name must be a string", errors)

    def test_name_exactly_101_chars(self):
        errors = validate_hi_request({"name": "a" * 101})
        self.assertIn("Name must be 100 characters or less", errors)

    def test_name_exceeds_100_chars(self):
        errors = validate_hi_request({"name": "a" * 200})
        self.assertIn("Name must be 100 characters or less", errors)

    def test_valid_name(self):
        errors = validate_hi_request({"name": "John"})
        self.assertEqual(errors, [])

    def test_valid_name_with_spaces(self):
        errors = validate_hi_request({"name": "  John  "})
        self.assertEqual(errors, [])

    def test_valid_name_single_char(self):
        errors = validate_hi_request({"name": "A"})
        self.assertEqual(errors, [])

    def test_valid_name_exactly_100_chars(self):
        errors = validate_hi_request({"name": "a" * 100})
        self.assertEqual(errors, [])

    def test_unicode_name(self):
        errors = validate_hi_request({"name": "José"})
        self.assertEqual(errors, [])

    def test_cjk_name(self):
        errors = validate_hi_request({"name": "太郎"})
        self.assertEqual(errors, [])

    def test_emoji_name(self):
        errors = validate_hi_request({"name": "👋"})
        self.assertEqual(errors, [])

    def test_name_with_newline(self):
        errors = validate_hi_request({"name": "John\nDoe"})
        self.assertEqual(errors, [])

    def test_name_with_tab(self):
        errors = validate_hi_request({"name": "John\tDoe"})
        self.assertEqual(errors, [])

    def test_special_characters(self):
        errors = validate_hi_request({"name": "O'Brien-Smith"})
        self.assertEqual(errors, [])


class TestGetGreeting(unittest.TestCase):
    def test_default_english(self):
        result = get_greeting("John")
        self.assertEqual(result, "Hi, John!")

    def test_formal_english(self):
        result = get_greeting("John", greeting_type="formal")
        self.assertEqual(result, "Hello, John!")

    def test_casual_english(self):
        result = get_greeting("John", greeting_type="casual")
        self.assertEqual(result, "Hey, John!")

    def test_emoji_english(self):
        result = get_greeting("John", greeting_type="emoji")
        self.assertEqual(result, "👋 Hey, John!")

    def test_default_spanish(self):
        result = get_greeting("Juan", language="es")
        self.assertEqual(result, "Hola, Juan!")

    def test_formal_spanish(self):
        result = get_greeting("Juan", greeting_type="formal", language="es")
        self.assertEqual(result, "Buenos días, Juan!")

    def test_casual_spanish(self):
        result = get_greeting("Juan", greeting_type="casual", language="es")
        self.assertEqual(result, "Ey, Juan!")

    def test_emoji_spanish(self):
        result = get_greeting("Juan", greeting_type="emoji", language="es")
        self.assertEqual(result, "👋 ¡Hola!, Juan!")

    def test_default_french(self):
        result = get_greeting("Pierre", language="fr")
        self.assertEqual(result, "Bonjour, Pierre!")

    def test_formal_french(self):
        result = get_greeting("Pierre", greeting_type="formal", language="fr")
        self.assertEqual(result, "Bonsoir, Pierre!")

    def test_casual_french(self):
        result = get_greeting("Pierre", greeting_type="casual", language="fr")
        self.assertEqual(result, "Salut, Pierre!")

    def test_emoji_french(self):
        result = get_greeting("Pierre", greeting_type="emoji", language="fr")
        self.assertEqual(result, "👋 Salut!, Pierre!")

    def test_default_german(self):
        result = get_greeting("Hans", language="de")
        self.assertEqual(result, "Hallo, Hans!")

    def test_formal_german(self):
        result = get_greeting("Hans", greeting_type="formal", language="de")
        self.assertEqual(result, "Guten Tag, Hans!")

    def test_casual_german(self):
        result = get_greeting("Hans", greeting_type="casual", language="de")
        self.assertEqual(result, "Hey, Hans!")

    def test_emoji_german(self):
        result = get_greeting("Hans", greeting_type="emoji", language="de")
        self.assertEqual(result, "👋 Hallo!, Hans!")

    def test_default_japanese(self):
        result = get_greeting("太郎", language="ja")
        self.assertEqual(result, "こんにちは、太郎さん！")

    def test_formal_japanese(self):
        result = get_greeting("太郎", greeting_type="formal", language="ja")
        self.assertEqual(result, "おはようございます、太郎さん！")

    def test_casual_japanese(self):
        result = get_greeting("太郎", greeting_type="casual", language="ja")
        self.assertEqual(result, "やあ、太郎さん！")

    def test_emoji_japanese(self):
        result = get_greeting("太郎", greeting_type="emoji", language="ja")
        self.assertEqual(result, "👋 こんにちは!、太郎さん！")

    def test_unknown_language_falls_back_to_english(self):
        result = get_greeting("John", language="xx")
        self.assertEqual(result, "Hi, John!")

    def test_unknown_greeting_type_falls_back_to_default(self):
        result = get_greeting("John", greeting_type="unknown")
        self.assertEqual(result, "Hi, John!")

    def test_unknown_language_and_type(self):
        result = get_greeting("John", greeting_type="unknown", language="xx")
        self.assertEqual(result, "Hi, John!")

    def test_empty_name(self):
        result = get_greeting("")
        self.assertEqual(result, "Hi, !")

    def test_unicode_name_greeting(self):
        result = get_greeting("José")
        self.assertEqual(result, "Hi, José!")


class HiAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        with self.app.app_context():
            database.init_db()
            self._create_test_users()

    def tearDown(self):
        with self.app.app_context():
            db = database.get_db()
            db.execute("DELETE FROM messages")
            db.execute("DELETE FROM users")
            db.commit()
            db.close()

        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def _create_test_users(self):
        response = self.client.post(
            "/api/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        self.user_id = response.get_json()["id"]

        response = self.client.post(
            "/api/users",
            json={
                "username": "seconduser",
                "email": "second@example.com",
                "password": "password456",
            },
        )
        self.second_user_id = response.get_json()["id"]

    def _login(self, username, password):
        response = self.client.post(
            "/api/users/login", json={"username": username, "password": password}
        )
        return response.get_json()["access_token"]

    def _auth_headers(self, username="testuser", password="password123"):
        token = self._login(username, password)
        return {"Authorization": f"Bearer {token}"}


class TestHiPostEndpoint(HiAPITestCase):
    def test_success(self):
        response = self.client.post(
            "/api/hi", json={"name": "John"}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["message"], "Hi, John!")
        self.assertIn("user_id", data)
        self.assertIsNotNone(data["user_id"])

    def test_unauthorized(self):
        response = self.client.post("/api/hi", json={"name": "John"})
        self.assertEqual(response.status_code, 401)

    def test_invalid_token(self):
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = self.client.post("/api/hi", json={"name": "John"}, headers=headers)
        self.assertIn(response.status_code, (401, 422))

    def test_missing_bearer_prefix(self):
        token = self._login("testuser", "password123")
        headers = {"Authorization": token}
        response = self.client.post("/api/hi", json={"name": "John"}, headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_missing_name(self):
        response = self.client.post("/api/hi", json={}, headers=self._auth_headers())
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertIn("Name is required", data["error"])

    def test_empty_name(self):
        response = self.client.post(
            "/api/hi", json={"name": ""}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_whitespace_only_name(self):
        response = self.client.post(
            "/api/hi", json={"name": "   "}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Name cannot be empty", data["error"])

    def test_name_too_long(self):
        response = self.client.post(
            "/api/hi", json={"name": "a" * 101}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("100 characters or less", data["error"])

    def test_name_exactly_100_chars(self):
        response = self.client.post(
            "/api/hi", json={"name": "a" * 100}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 201)

    def test_invalid_type_integer(self):
        response = self.client.post(
            "/api/hi", json={"name": 123}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("string", data["error"])

    def test_invalid_type_list(self):
        response = self.client.post(
            "/api/hi", json={"name": ["John"]}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("string", data["error"])

    def test_no_json_body(self):
        response = self.client.post(
            "/api/hi",
            data="{}",
            content_type="application/json",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_null_json_body(self):
        response = self.client.post(
            "/api/hi",
            data="null",
            content_type="application/json",
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("error", data)

    def test_whitespace_trimming(self):
        response = self.client.post(
            "/api/hi", json={"name": "  John  "}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("Hi, John!", data["message"])

    def test_unicode_name(self):
        response = self.client.post(
            "/api/hi", json={"name": "José"}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("José", data["message"])

    def test_cjk_name(self):
        response = self.client.post(
            "/api/hi", json={"name": "太郎"}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("太郎", data["message"])

    def test_single_character_name(self):
        response = self.client.post(
            "/api/hi", json={"name": "A"}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["message"], "Hi, A!")

    def test_name_with_special_characters(self):
        response = self.client.post(
            "/api/hi", json={"name": "O'Brien-Smith"}, headers=self._auth_headers()
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("O'Brien-Smith", data["message"])

    def test_extra_fields_ignored(self):
        response = self.client.post(
            "/api/hi",
            json={"name": "John", "extra": "field", "another": 123},
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("Hi, John!", data["message"])

    def test_content_type_form_urlencoded(self):
        response = self.client.post(
            "/api/hi",
            data="name=John",
            content_type="application/x-www-form-urlencoded",
            headers=self._auth_headers(),
        )
        self.assertIn(response.status_code, (400, 415))

    def test_response_structure(self):
        response = self.client.post(
            "/api/hi", json={"name": "John"}, headers=self._auth_headers()
        )
        data = response.get_json()
        self.assertIn("message", data)
        self.assertIn("user_id", data)

    def test_user_id_matches_authenticated_user(self):
        response = self.client.post(
            "/api/hi", json={"name": "John"}, headers=self._auth_headers()
        )
        data = response.get_json()
        self.assertEqual(str(data["user_id"]), str(self.user_id))

    def test_multiple_requests_same_user(self):
        for name in ["Alice", "Bob", "Charlie"]:
            response = self.client.post(
                "/api/hi", json={"name": name}, headers=self._auth_headers()
            )
            self.assertEqual(response.status_code, 201)
            data = response.get_json()
            self.assertIn(f"Hi, {name}!", data["message"])


class TestHiGetEndpoint(HiAPITestCase):
    def test_success(self):
        response = self.client.get("/api/hi", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("message", data)
        self.assertIn("Hi, testuser!", data["message"])
        self.assertIn("user_id", data)
        self.assertIn("username", data)
        self.assertEqual(data["username"], "testuser")

    def test_unauthorized(self):
        response = self.client.get("/api/hi")
        self.assertEqual(response.status_code, 401)

    def test_invalid_token(self):
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = self.client.get("/api/hi", headers=headers)
        self.assertIn(response.status_code, (401, 422))

    def test_missing_bearer_prefix(self):
        token = self._login("testuser", "password123")
        headers = {"Authorization": token}
        response = self.client.get("/api/hi", headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_response_structure(self):
        response = self.client.get("/api/hi", headers=self._auth_headers())
        data = response.get_json()
        self.assertIn("message", data)
        self.assertIn("user_id", data)
        self.assertIn("username", data)
        self.assertIsNotNone(data["user_id"])

    def test_second_user_greeting(self):
        response = self.client.get(
            "/api/hi", headers=self._auth_headers("seconduser", "password456")
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Hi, seconduser!", data["message"])
        self.assertEqual(data["username"], "seconduser")

    def test_user_id_matches(self):
        response = self.client.get("/api/hi", headers=self._auth_headers())
        data = response.get_json()
        self.assertEqual(str(data["user_id"]), str(self.user_id))

    def test_get_after_post(self):
        self.client.post(
            "/api/hi", json={"name": "Alice"}, headers=self._auth_headers()
        )
        response = self.client.get("/api/hi", headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Hi, testuser!", data["message"])


class TestHiHealthCheck(HiAPITestCase):
    def test_health_check(self):
        response = self.client.get("/api/hi/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "hi")

    def test_health_check_no_auth_required(self):
        response = self.client.get("/api/hi/health")
        self.assertEqual(response.status_code, 200)

    def test_health_check_post_not_allowed(self):
        response = self.client.post("/api/hi/health")
        self.assertEqual(response.status_code, 405)


if __name__ == "__main__":
    unittest.main()
