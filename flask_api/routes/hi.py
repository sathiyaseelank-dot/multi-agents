from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User

bp = Blueprint("hi", __name__, url_prefix="/api/hi")


def validate_hi_request(data):
    errors = []

    if not data:
        errors.append("No data provided")
        return errors

    name = data.get("name")
    if not name:
        errors.append("Name is required")
    elif not isinstance(name, str):
        errors.append("Name must be a string")
    elif len(name.strip()) < 1:
        errors.append("Name cannot be empty")
    elif len(name) > 100:
        errors.append("Name must be 100 characters or less")

    return errors


def get_greeting(name, greeting_type="default", language="en"):
    greetings = {
        "en": {
            "default": "Hi",
            "formal": "Hello",
            "casual": "Hey",
            "emoji": "👋 Hey",
        },
        "es": {
            "default": "Hola",
            "formal": "Buenos días",
            "casual": "Ey",
            "emoji": "👋 ¡Hola!",
        },
        "fr": {
            "default": "Bonjour",
            "formal": "Bonsoir",
            "casual": "Salut",
            "emoji": "👋 Salut!",
        },
        "de": {
            "default": "Hallo",
            "formal": "Guten Tag",
            "casual": "Hey",
            "emoji": "👋 Hallo!",
        },
        "ja": {
            "default": "こんにちは",
            "formal": "おはようございます",
            "casual": "やあ",
            "emoji": "👋 こんにちは!",
        },
    }

    base_greeting = greetings.get(language, greetings["en"]).get(
        greeting_type, greetings["en"]["default"]
    )

    if language == "ja":
        return f"{base_greeting}、{name}さん！"
    else:
        return f"{base_greeting}, {name}!"


@bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "hi"}), 200


@bp.route("", methods=["POST"])
@jwt_required()
def send_hi():
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    validation_errors = validate_hi_request(data)
    if validation_errors:
        return jsonify(
            {"error": validation_errors[0], "details": validation_errors}
        ), 400

    name = data.get("name", "").strip()
    greeting_type = data.get("greeting_type", "default")
    language = data.get("language", "en")

    greeting = get_greeting(name, greeting_type, language)

    return jsonify(
        {
            "message": greeting,
            "name": name,
            "greeting_type": greeting_type,
            "language": language,
            "user_id": current_user_id,
        }
    ), 201


@bp.route("", methods=["GET"])
@jwt_required()
def get_hi():
    current_user_id = int(get_jwt_identity())
    user = User.get_by_id(current_user_id)

    name = request.args.get("name", user.username if user else "User")
    greeting_type = request.args.get("greeting_type", "default")
    language = request.args.get("language", "en")

    greeting = get_greeting(name, greeting_type, language)

    return jsonify(
        {
            "message": greeting,
            "name": name,
            "greeting_type": greeting_type,
            "language": language,
            "user_id": current_user_id,
            "username": user.username if user else None,
        }
    ), 200
