import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flask_api", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flask_api"))

from flask import Flask
from config import Config, DevelopmentConfig, TestingConfig
from database import get_db, init_app
from models import User


class AppFactoryTestCase(unittest.TestCase):
    def setUp(self):
        from app import create_app

        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def test_app_is_flask_instance(self):
        self.assertIsInstance(self.app, Flask)

    def test_app_testing_mode(self):
        self.assertTrue(self.app.config["TESTING"])

    def test_app_has_blueprints(self):
        blueprint_names = list(self.app.blueprints.keys())
        self.assertIn("users", blueprint_names)

    def test_cors_enabled(self):
        response = self.client.options(
            "/api/users",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertIn("Access-Control-Allow-Origin", dict(response.headers))

    def test_health_endpoint(self):
        response = self.client.get("/api/orchestrator/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")


class ConfigTestCase(unittest.TestCase):
    def test_base_config_has_database(self):
        self.assertTrue(hasattr(Config, "DATABASE"))
        self.assertTrue(Config.DATABASE.endswith("users.db"))

    def test_base_config_defaults(self):
        self.assertFalse(Config.DEBUG)
        self.assertFalse(Config.TESTING)

    def test_development_config_debug(self):
        self.assertTrue(DevelopmentConfig.DEBUG)

    def test_testing_config_testing(self):
        self.assertTrue(TestingConfig.TESTING)
        self.assertTrue(TestingConfig.DATABASE.endswith("test_users.db"))

    def test_testing_config_isolation(self):
        from app import create_app

        app = create_app(TestingConfig)
        self.assertNotEqual(app.config["DATABASE"], Config.DATABASE)


class BlueprintRoutesTestCase(unittest.TestCase):
    def setUp(self):
        from app import create_app

        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def test_get_users_endpoint(self):
        response = self.client.get("/api/users")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

    def test_post_users_endpoint(self):
        response = self.client.post(
            "/api/users",
            json={
                "username": "routetest",
                "email": "route@example.com",
                "password": "pass123",
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_get_user_by_id_endpoint(self):
        create_resp = self.client.post(
            "/api/users",
            json={
                "username": "getroute",
                "email": "getroute@example.com",
                "password": "pass",
            },
        )
        user_id = create_resp.get_json()["id"]
        response = self.client.get(f"/api/users/{user_id}")
        self.assertEqual(response.status_code, 200)

    def test_put_user_endpoint(self):
        create_resp = self.client.post(
            "/api/users",
            json={
                "username": "putroute",
                "email": "putroute@example.com",
                "password": "pass",
            },
        )
        user_id = create_resp.get_json()["id"]
        response = self.client.put(
            f"/api/users/{user_id}", json={"username": "updatedroute"}
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_user_endpoint(self):
        create_resp = self.client.post(
            "/api/users",
            json={
                "username": "delroute",
                "email": "delroute@example.com",
                "password": "pass",
            },
        )
        user_id = create_resp.get_json()["id"]
        response = self.client.delete(f"/api/users/{user_id}")
        self.assertEqual(response.status_code, 200)

    def test_404_on_invalid_route(self):
        response = self.client.get("/api/nonexistent")
        self.assertEqual(response.status_code, 404)


class ServiceIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        from app import create_app

        self.app = create_app(TestingConfig)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.execute("DELETE FROM users")
            db.commit()
            db.close()
        if os.path.exists(self.app.config["DATABASE"]):
            os.remove(self.app.config["DATABASE"])

    def test_full_user_lifecycle(self):
        resp = self.client.post(
            "/api/users",
            json={
                "username": "lifecycle",
                "email": "life@example.com",
                "password": "pass123",
            },
        )
        self.assertEqual(resp.status_code, 201)
        user_id = resp.get_json()["id"]

        resp = self.client.get(f"/api/users/{user_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["username"], "lifecycle")

        resp = self.client.put(
            f"/api/users/{user_id}", json={"username": "lifecycle_updated"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["username"], "lifecycle_updated")

        resp = self.client.get("/api/users")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()), 1)

        resp = self.client.delete(f"/api/users/{user_id}")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(f"/api/users/{user_id}")
        self.assertEqual(resp.status_code, 404)

    def test_multiple_users_persisted(self):
        for i in range(5):
            self.client.post(
                "/api/users",
                json={
                    "username": f"user_{i}",
                    "email": f"user_{i}@example.com",
                    "password": "pass",
                },
            )
        resp = self.client.get("/api/users")
        data = resp.get_json()
        self.assertEqual(len(data), 5)

    def test_error_responses_are_json(self):
        resp = self.client.post("/api/users", json={})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.content_type, "application/json")
        self.assertIn("error", resp.get_json())


if __name__ == "__main__":
    unittest.main()
