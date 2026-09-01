from __future__ import annotations

from dataclasses import dataclass

from easy_a.signals.models import SignalType


@dataclass(frozen=True)
class SignalRule:
    signal_type: SignalType
    value: str
    pattern: str
    confidence: float


RULES: tuple[SignalRule, ...] = (
    SignalRule(
        SignalType.attendance,
        "not_required",
        r"\b(?:attendance\s+(?:is\s+)?not\s+(?:mandatory|required)|"
        r"not\s+required.{0,60}\battendance|optional\s+attendance)\b",
        0.99,
    ),
    SignalRule(
        SignalType.attendance,
        "required",
        r"\b(?:attendance\s+(?:is\s+)?(?:required|mandatory)|mandatory\s+attendance|"
        r"attendance\s+will\s+be\s+taken|attendance\s+counts(?:\s+(?:for|toward))?|"
        r"(?<!not\s)required.{0,80}\battendance)\b",
        0.98,
    ),
    SignalRule(
        SignalType.late_work,
        "not_allowed",
        r"\b(?:late\s+(?:work|assignments?|submissions?)\s+(?:is|are)\s+not\s+accepted|"
        r"no\s+late\s+(?:work|assignments?|submissions?))\b",
        0.99,
    ),
    SignalRule(
        SignalType.late_work,
        "allowed",
        r"\b(?:late\s+(?:work|assignments?|submissions?)\s+(?:is|are)\s+accepted|late\s+penalty)\b",
        0.94,
    ),
    SignalRule(
        SignalType.exams,
        "present",
        r"\b(?:midterm(?:\s+exam)?|final\s+exam|exams?\s+(?:is|are|will|must)|"
        r"tests?\s+(?:is|are|will|must))\b",
        0.94,
    ),
    SignalRule(
        SignalType.exam_location,
        "online",
        r"\b(?:online\s+(?:exam|test)|(?:exam|test)s?.{0,60}\b(?:online|Canvas)\b)\b",
        0.96,
    ),
    SignalRule(
        SignalType.exam_location,
        "in_person",
        r"\b(?:(?:exam|test|quiz)(?:s|zes)?.{0,60}\bin[ -]person\b|"
        r"in[ -]person.{0,60}\b(?:exam|test|quiz)(?:s|zes)?)\b",
        0.97,
    ),
    SignalRule(
        SignalType.exam_location,
        "proctored",
        r"\b(?:proctored\s+(?:exam|test)|(?:exam|test)s?.{0,40}\bproctored)\b",
        0.92,
    ),
    SignalRule(
        SignalType.curve,
        "not_present",
        r"\b(?:no\s+(?:grading\s+)?curve|(?:grades?|course)\s+will\s+not\s+be\s+curved)\b",
        0.99,
    ),
    SignalRule(
        SignalType.curve,
        "present",
        r"\b(?:(?:grading\s+)?curve\s+(?:will|may|is)|grades?\s+(?:will|may)\s+be\s+curved)\b",
        0.94,
    ),
    SignalRule(
        SignalType.participation,
        "required",
        r"\b(?:class\s+)?participation\s+(?:is\s+required|counts|will\s+(?:count|be\s+graded)|grade)\b",
        0.95,
    ),
    SignalRule(
        SignalType.lab,
        "required",
        r"\b(?:lab\s+(?:is\s+)?required|weekly\s+(?:SMART\s+)?Lab|"
        r"(?:must|required\s+to)\s+(?:attend|complete|spend).{0,100}\b(?:SMART\s+)?Lab|"
        r"required.{0,100}\battendance\s+in\s+the\s+SMART\s+Lab)\b",
        0.96,
    ),
    SignalRule(
        SignalType.quiz,
        "present",
        r"\b(?:weekly\s+quizzes|quizzes\s+(?:and|are|will)|quiz\s+(?:is|will))\b",
        0.92,
    ),
    SignalRule(
        SignalType.delivery_format,
        "online",
        r"\b(?:(?:Canvas|online)\s+(?:video\s+)?lectures?|"
        r"video\s+lectures?.{0,50}\bCanvas)\b",
        0.94,
    ),
)
