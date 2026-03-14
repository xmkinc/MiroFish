"""
LLM客户端封装
统一使用OpenAI格式调用
"""
import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI
from ..config import Config


class LLMClient:
    """LLM客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """发送聊天请求"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 移除思考模型的 <think> 标签（qwen3、deepseek-r1 等）
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """发送聊天请求并返回JSON"""
        # 判断是否为思考模型（不支持 json_object response_format）
        is_thinking_model = any(
            keyword in self.model.lower()
            for keyword in ['qwen3', 'deepseek-r1', 'o1-', 'o3-', 'thinking', 'r1']
        )

        if is_thinking_model:
            # 思考模型：不使用 response_format，在 prompt 中要求 JSON 输出
            enhanced_messages = list(messages)
            if enhanced_messages and enhanced_messages[-1].get('role') == 'user':
                enhanced_messages[-1] = {
                    'role': 'user',
                    'content': enhanced_messages[-1]['content'] + '\n\n请严格以JSON格式输出，不要包含任何其他文字。'
                }
            response = self.chat(
                messages=enhanced_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=None
            )
        else:
            # 标准模型：使用 json_object response_format
            response = self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )

        return self._extract_json(response)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从文本中提取 JSON，支持多种格式"""
        if not text:
            raise ValueError("LLM返回了空响应")

        cleaned = text.strip()

        # 1. 移除 markdown 代码块标记
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()

        # 2. 直接尝试解析
        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # 3. 提取第一个完整的 JSON 对象
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = cleaned[start:end + 1]
            try:
                result = json.loads(json_str)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass

        # 4. 尝试提取 JSON 数组
        start = cleaned.find('[')
        end = cleaned.rfind(']')
        if start != -1 and end != -1 and end > start:
            json_str = cleaned[start:end + 1]
            try:
                result = json.loads(json_str)
                if isinstance(result, list):
                    return {"items": result}
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从LLM响应中提取有效JSON: {cleaned[:200]}")
