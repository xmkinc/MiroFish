"""
MiroFish Backend - 生产环境启动入口
在 Railway 等平台上使用，Flask 同时提供 API 和前端静态文件
"""
import os
import sys

# 添加 backend 目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import send_from_directory, jsonify, request
from app import create_app
from app.config import Config


def main():
    """主函数"""
    # 验证配置
    errors = Config.validate()
    if errors:
        print("配置错误:")
        for err in errors:
            print(f"  - {err}")
        print("\n请检查环境变量配置")
        sys.exit(1)

    # 创建应用
    app = create_app()

    # 调试端点：测试 LLM 连接
    @app.route("/api/debug/llm-test", methods=["GET"])
    def debug_llm_test():
        import traceback
        try:
            from app.utils.llm_client import LLMClient
            client = LLMClient()
            result = client.chat(
                messages=[{"role": "user", "content": "Say hello in one word"}],
                max_tokens=10
            )
            return jsonify({
                "success": True,
                "response": result,
                "model": client.model,
                "base_url": client.base_url,
                "api_key_prefix": client.api_key[:10] + "..." if client.api_key else None
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }), 500

    # 前端静态文件目录（构建产物）
    frontend_dist = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "frontend", "dist"
    )

    if os.path.exists(frontend_dist):
        print(f"[MiroFish] 前端静态文件目录: {frontend_dist}")

        # 静态文件路由（精确匹配 assets 目录）
        @app.route("/assets/<path:filename>")
        def serve_assets(filename):
            return send_from_directory(os.path.join(frontend_dist, "assets"), filename)

        # 根路径
        @app.route("/")
        def serve_index():
            return send_from_directory(frontend_dist, "index.html")

        # favicon 和其他根级静态文件
        @app.route("/favicon.ico")
        def serve_favicon():
            return send_from_directory(frontend_dist, "favicon.ico")

        # SPA fallback：所有非 API 的 404 返回 index.html
        @app.errorhandler(404)
        def spa_fallback(e):
            # API 路由的 404 返回 JSON 错误
            if request.path.startswith("/api/"):
                return jsonify({"error": "Not found", "path": request.path}), 404
            # 前端路由返回 index.html
            index_path = os.path.join(frontend_dist, "index.html")
            if os.path.exists(index_path):
                return send_from_directory(frontend_dist, "index.html")
            return jsonify({"error": "Not found"}), 404

    else:
        print(f"[MiroFish] 警告：未找到前端构建产物 ({frontend_dist})，仅提供 API 服务")

    # 获取运行配置（Railway 会注入 PORT 环境变量）
    port = int(os.environ.get("PORT", os.environ.get("FLASK_PORT", 5001)))
    host = os.environ.get("FLASK_HOST", "0.0.0.0")

    print(f"[MiroFish] 启动服务: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
