"""Model routing across providers -- AWS Bedrock, Azure AI Foundry, and a Gemini/mock fallback.

The JD lists Snowflake Cortex, AWS Bedrock, or Azure AI Foundry. Different agents want different
models: the supervisor needs a strong reasoner; specialists can run a cheaper/faster model. This
router encodes that policy and picks a backend from whatever credentials are present, falling back
to a deterministic offline model so the whole workflow runs with no keys.

Each provider is a thin seam: the Bedrock/Foundry constructors show exactly where the real SDK
call goes. All expose one method -- complete(prompt, system) -> str.
"""
from __future__ import annotations
import os


class OfflineModel:
    """Deterministic, no-key stand-in so the graph runs anywhere. Agents don't rely on its
    'intelligence' -- their control flow is deterministic; this only fills natural-language text."""
    name = "offline"

    def complete(self, prompt: str, *, system: str = "") -> str:
        return ""   # agents fall back to their own deterministic phrasing


class BedrockModel:
    name = "bedrock"

    def __init__(self, model_id: str):
        # real: boto3.client("bedrock-runtime") using the service IAM role (no static keys);
        #       self._client.converse(modelId=model_id, ...)
        self.model_id = model_id

    def complete(self, prompt: str, *, system: str = "") -> str:  # pragma: no cover (seam)
        raise NotImplementedError("wire boto3 bedrock-runtime.converse here")


class FoundryModel:
    name = "azure-foundry"

    def __init__(self, endpoint: str, deployment: str):
        # real: azure-ai-inference ChatCompletionsClient(endpoint, AzureKeyCredential/AAD token)
        self.endpoint, self.deployment = endpoint, deployment

    def complete(self, prompt: str, *, system: str = "") -> str:  # pragma: no cover (seam)
        raise NotImplementedError("wire azure-ai-inference ChatCompletionsClient here")


# role -> preferred model tier (supervisor reasons harder than specialists)
_ROLE_TIER = {
    "supervisor": "strong",
    "knowledge": "fast",
    "analytics": "fast",
    "compliance": "strong",
}


def get_model(role: str):
    """Select a provider for an agent role from available credentials; offline if none."""
    tier = _ROLE_TIER.get(role, "fast")
    if os.environ.get("AWS_REGION") or os.environ.get("AWS_ACCESS_KEY_ID"):
        return BedrockModel("anthropic.claude-3-5-sonnet-20240620-v1:0"
                            if tier == "strong" else "anthropic.claude-3-haiku-20240307-v1:0")
    if os.environ.get("AZURE_AI_ENDPOINT"):
        return FoundryModel(os.environ["AZURE_AI_ENDPOINT"],
                            "gpt-4o" if tier == "strong" else "gpt-4o-mini")
    return OfflineModel()
