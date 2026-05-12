from __future__ import annotations

from enum import Enum


class IssueSeverity(str, Enum):
    critical = "critical"
    major = "major"
    minor = "minor"
    nit = "nit"


class IssueCategory(str, Enum):
    accuracy = "accuracy"
    logic = "logic"
    consistency = "consistency"
    grammar = "grammar"
    clarity = "clarity"
    formatting = "formatting"
    citation = "citation"
    tone = "tone"
    risk = "risk"


class IssueStatus(str, Enum):
    open = "open"
    accepted = "accepted"
    rejected = "rejected"
    deferred = "deferred"
    resolved = "resolved"


class JobLifecycleStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class UploadKind(str, Enum):
    main = "main"
    supporting = "supporting"


class EntitlementTier(str, Enum):
    free = "free"
    pro = "pro"


class SubscriptionStatus(str, Enum):
    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    canceled = "canceled"
    unpaid = "unpaid"
    incomplete = "incomplete"
    incomplete_expired = "incomplete_expired"


class UsageEventType(str, Enum):
    job_completed = "job_completed"
    job_failed = "job_failed"
    proof_consumed = "proof_consumed"


class DocumentType(str, Enum):
    general = "general"
    legal = "legal"
    academic = "academic"
    business = "business"
    marketing = "marketing"


class AccuracyPosture(str, Enum):
    false = "false"
    unsupported = "unsupported"
    unverified = "unverified"
    internally_inconsistent = "internally_inconsistent"


class DebateStance(str, Enum):
    defend = "defend"
    revise = "revise"
    withdraw = "withdraw"


class ArbiterVerdict(str, Enum):
    accept_a = "accept_a"
    accept_b = "accept_b"
    merge = "merge"
    reject_both = "reject_both"
    needs_human_evidence = "needs_human_evidence"
