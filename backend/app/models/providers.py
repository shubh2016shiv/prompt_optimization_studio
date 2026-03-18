"""
Static data definitions for LLM providers, frameworks, task types, and TCRTE dimensions.

These mirror the frontend constants for consistency.
"""

from typing import TypedDict


class Model(TypedDict):
    """LLM model definition."""
    id: str
    label: str
    reasoning: bool


class Provider(TypedDict):
    """LLM provider definition with models."""
    label: str
    icon: str
    key_placeholder: str
    key_hint: str
    models: list[Model]
    default_endpoint: str


class Framework(TypedDict):
    """Optimization framework definition."""
    id: str
    label: str
    icon: str
    description: str


class TaskType(TypedDict):
    """Task type definition."""
    id: str
    label: str
    icon: str


class TCRTEDimension(TypedDict):
    """TCRTE coverage dimension definition."""
    id: str
    label: str
    icon: str
    description: str


class QuickAction(TypedDict):
    """Chat quick action definition."""
    icon: str
    label: str


# LLM Providers with their available models
PROVIDERS: dict[str, Provider] = {
    "anthropic": {
        "label": "Anthropic",
        "icon": "◆",
        "key_placeholder": "sk-ant-api03-…",
        "key_hint": "Anthropic API key",
        "models": [
            {"id": "claude-opus-4-6", "label": "Claude Opus 4.6", "reasoning": False},
            {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6", "reasoning": False},
            {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5", "reasoning": False},
            {"id": "claude-sonnet-4-5", "label": "Claude Sonnet 4.5 (Ext. Thinking)", "reasoning": True},
        ],
        "default_endpoint": "https://api.anthropic.com/v1/messages",
    },
    "openai": {
        "label": "OpenAI",
        "icon": "⬡",
        "key_placeholder": "sk-proj-…",
        "key_hint": "OpenAI API key",
        "models": [
            {"id": "gpt-4o", "label": "GPT-4o", "reasoning": False},
            {"id": "gpt-4.1", "label": "GPT-4.1", "reasoning": False},
            {"id": "o3", "label": "o3 (Reasoning)", "reasoning": True},
            {"id": "o4-mini", "label": "o4-mini (Reasoning)", "reasoning": True},
        ],
        "default_endpoint": "https://api.openai.com/v1/chat/completions",
    },
    "google": {
        "label": "Google",
        "icon": "✦",
        "key_placeholder": "AIza…",
        "key_hint": "Google AI Studio key",
        "models": [
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "reasoning": False},
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "reasoning": False},
            {"id": "gemini-2.0-flash-thinking", "label": "Gemini 2.0 Flash Thinking", "reasoning": True},
        ],
        "default_endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
    },
}

# Optimization frameworks
FRAMEWORKS: list[Framework] = [
    {"id": "auto", "label": "Auto-Select", "icon": "✦", "description": "AI picks the best framework for your model & task"},
    {"id": "kernel", "label": "KERNEL", "icon": "⬡", "description": "Keep · Explicit · Narrow · Known · Enforce · Logical"},
    {"id": "xml_structured", "label": "XML Structured", "icon": "⟨/⟩", "description": "Anthropic XML semantic bounding — best for Claude"},
    {"id": "progressive", "label": "Progressive Disclosure", "icon": "◈", "description": "Agent Skills layered context injection"},
    {"id": "cot_ensemble", "label": "CoT Ensemble", "icon": "⊕", "description": "Medprompt-style multi-path reasoning"},
    {"id": "textgrad", "label": "TextGrad", "icon": "∇", "description": "Iterative textual backpropagation + constraint hardening"},
    {"id": "reasoning_aware", "label": "Reasoning-Aware", "icon": "◎", "description": "For o-series / extended-thinking — no forced CoT"},
    {"id": "tcrte", "label": "TCRTE", "icon": "⊞", "description": "Task · Context · Role · Tone · Execution — full coverage"},
    {"id": "create", "label": "CREATE", "icon": "⟳", "description": "Context · Role · Instruction · Steps · Execution"},
]

# Task types
TASK_TYPES: list[TaskType] = [
    {"id": "planning", "label": "Planning", "icon": "📋"},
    {"id": "reasoning", "label": "Reasoning", "icon": "🧠"},
    {"id": "coding", "label": "Coding", "icon": "💻"},
    {"id": "routing", "label": "Routing", "icon": "🔀"},
    {"id": "analysis", "label": "Analysis", "icon": "📊"},
    {"id": "extraction", "label": "Extraction", "icon": "🔍"},
    {"id": "creative", "label": "Creative", "icon": "✍️"},
    {"id": "qa", "label": "Q&A / RAG", "icon": "💬"},
]

# TCRTE dimensions
TCRTE_DIMENSIONS: list[TCRTEDimension] = [
    {"id": "task", "label": "Task", "icon": "T", "description": "Core objective & action"},
    {"id": "context", "label": "Context", "icon": "C", "description": "Background & grounding data"},
    {"id": "role", "label": "Role", "icon": "R", "description": "Model persona & expertise"},
    {"id": "tone", "label": "Tone", "icon": "T", "description": "Style & communication register"},
    {"id": "execution", "label": "Execution", "icon": "E", "description": "Format, length & constraints"},
]

# Quick actions for chat
QUICK_ACTIONS: list[QuickAction] = [
    {"icon": "✂", "label": "Make V1 more concise"},
    {"icon": "🛡", "label": "Add anti-hallucination guards to V2"},
    {"icon": "◎", "label": "Convert V3 to reasoning-aware"},
    {"icon": "⊕", "label": "Merge best parts of all 3 variants"},
    {"icon": "📎", "label": "Add few-shot examples to V2"},
    {"icon": "🔒", "label": "Harden output format constraints"},
    {"icon": "⚠", "label": "What are the biggest risks here?"},
    {"icon": "⟨/⟩", "label": "Rewrite V1 with XML structural bounding"},
    {"icon": "⊞", "label": "Apply full TCRTE coverage to V3"},
    {"icon": "CoRe", "label": "Apply Context Repetition for multi-hop"},
]
