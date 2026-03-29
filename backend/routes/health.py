from flask import Blueprint, request, jsonify

bp = Blueprint("health", __name__)


@bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "auth-backend"}), 200
