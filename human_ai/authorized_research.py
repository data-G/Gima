from __future__ import annotations

from dataclasses import dataclass


GATE_QUESTIONS = [
    "Do you own this system or have written permission?",
    "What is the scope?",
    "What actions are allowed?",
    "What actions are prohibited?",
    "Should the result be a private report only?",
]

AUTHORIZED_REPORT_TEMPLATE = """# Gima Authorized Research Report

Target:
Permission status:
Scope:
Sources used:
Public information found:
Architecture summary:
API/documentation summary:
Technology stack:
Security observations:
Privacy observations:
Risks:
Recommendations:
Actions not performed due to safety/legal limits:
Next safe steps:
"""

ALLOWED_CAPABILITIES = [
    "Analyze public documentation.",
    "Summarize websites and articles.",
    "Compare AI tools and APIs.",
    "Review open-source code.",
    "Inspect the user's own codebase.",
    "Document system architecture from permitted sources.",
    "Generate API integration plans from official docs.",
    "Run security checks on the user's own apps.",
    "Find bugs in user-owned projects.",
    "Create responsible vulnerability reports.",
    "Suggest privacy and security improvements.",
    "Monitor public changelogs, releases, pricing, and benchmarks.",
]

NOT_ALLOWED = [
    "Do not bypass login, payment, rate limits, CAPTCHA, or API restrictions.",
    "Do not steal API keys, tokens, cookies, credentials, or private data.",
    "Do not scrape private or restricted content.",
    "Do not extract proprietary model weights, prompts, datasets, or hidden system instructions.",
    "Do not clone paid services illegally.",
    "Do not attack websites, servers, models, or APIs.",
    "Do not create malware, phishing, spyware, credential harvesting, or exploit automation.",
    "Do not perform unauthorized penetration testing.",
    "Do not deanonymize or track private people.",
    "Do not publish private phone numbers, home addresses, or sensitive personal data.",
]

SAFE_ALTERNATIVES = [
    "For your own software: analyze architecture, dependencies, APIs, logs, performance, security, and bugs.",
    "For open-source projects: study code, summarize design, find issues, suggest improvements, and contribute patches.",
    "For public AI tools: compare features, pricing, terms, APIs, benchmarks, model cards, and documentation.",
    "For websites: analyze public pages, SEO, UX, accessibility, performance, content structure, and technology stack from legal public sources.",
    "For APIs: use official documentation and provided API keys only.",
]

SECURITY_OR_RESEARCH_TERMS = {
    "audit",
    "bug bounty",
    "cve",
    "exploit",
    "osint",
    "penetration",
    "pentest",
    "privacy",
    "recon",
    "reverse engineer",
    "security",
    "threat",
    "vulnerability",
    "vulnerabilities",
}

PROHIBITED_TERMS = {
    "bypass captcha",
    "bypass login",
    "bypass paywall",
    "bypass payment",
    "credential harvesting",
    "ddos",
    "deanonymize",
    "dump cookies",
    "exploit automation",
    "hidden system prompt",
    "malware",
    "phishing",
    "private api key",
    "rate limit bypass",
    "scrape private",
    "spyware",
    "steal api key",
    "steal cookie",
    "steal token",
}

PUBLIC_RESEARCH_TERMS = {
    "article",
    "benchmark",
    "changelog",
    "compare",
    "documentation",
    "docs",
    "model card",
    "official docs",
    "pricing",
    "public page",
    "release notes",
    "summarize",
    "terms",
}

PERMISSION_TERMS = {
    "authorized",
    "permission",
    "owned by me",
    "own app",
    "own code",
    "my app",
    "my code",
    "my website",
    "written permission",
}


@dataclass(frozen=True)
class AuthorizedResearchDecision:
    category: str
    reason: str
    requires_gate: bool
    allowed_mode: str


def classify_authorized_research_request(message: str) -> AuthorizedResearchDecision:
    normalized = " ".join(message.casefold().split())
    if any(term in normalized for term in PROHIBITED_TERMS):
        return AuthorizedResearchDecision(
            category="prohibited",
            reason="The request appears to involve bypassing controls, stealing data, unauthorized exploitation, or other unsafe activity.",
            requires_gate=False,
            allowed_mode="refuse_and_offer_safe_alternatives",
        )
    has_security_or_research = any(term in normalized for term in SECURITY_OR_RESEARCH_TERMS)
    if has_security_or_research:
        has_permission = any(term in normalized for term in PERMISSION_TERMS)
        return AuthorizedResearchDecision(
            category="authorized_audit" if has_permission else "needs_authorization",
            reason=(
                "The request is security, audit, OSINT, privacy, or reverse-engineering style work. "
                "Gima must confirm authorization and scope before taking any active security steps."
            ),
            requires_gate=not has_permission,
            allowed_mode="authorized_private_report" if has_permission else "public_high_level_only",
        )
    if any(term in normalized for term in PUBLIC_RESEARCH_TERMS):
        return AuthorizedResearchDecision(
            category="public_research",
            reason="The request appears limited to public documentation, articles, pricing, releases, or benchmarks.",
            requires_gate=False,
            allowed_mode="public_sources_only",
        )
    return AuthorizedResearchDecision(
        category="not_research_audit",
        reason="The request does not look like an authorized research or security-audit task.",
        requires_gate=False,
        allowed_mode="normal",
    )


def authorized_research_gate_response(message: str) -> str | None:
    decision = classify_authorized_research_request(message)
    if decision.category == "not_research_audit":
        return None
    if decision.category == "public_research":
        return None
    if decision.category == "prohibited":
        alternatives = "\n".join(f"- {item}" for item in SAFE_ALTERNATIVES)
        return (
            "I cannot help with unauthorized or harmful security activity.\n\n"
            f"Reason: {decision.reason}\n\n"
            "Safe alternatives I can help with:\n"
            f"{alternatives}\n\n"
            "For authorized work, confirm ownership/permission and scope, and I can prepare a private responsible report."
        )
    questions = "\n".join(f"{idx}. {question}" for idx, question in enumerate(GATE_QUESTIONS, start=1))
    return (
        "This looks like an authorized research, security audit, OSINT, privacy, or reverse-engineering-style task. "
        "Before Gima does anything beyond high-level public research, please answer:\n\n"
        f"{questions}\n\n"
        "Until permission is confirmed, Gima will only provide high-level public research and safe analysis.\n\n"
        f"{AUTHORIZED_REPORT_TEMPLATE}"
    )
