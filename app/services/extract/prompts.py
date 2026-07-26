"""Prompt domain knowledge for ADR constraint extraction.

This module imports langextract to define few-shot examples as
lx.data.ExampleData objects, which the engine passes directly
to lx.extract().
"""
from __future__ import annotations

import langextract as lx

PROMPT_DESCRIPTION = (
    "Extract architectural constraints from ADR documents.\n"
    "\n"
    "Predicates:\n"
    "- prohibits_dependency: the subject must NOT import or call the object\n"
    "- requires_dependency: the subject MUST import or call the object\n"
    "- prohibits_implementation: the subject must NOT define the logic described by the object\n"
    "- requires_implementation: the subject MUST define the logic described by the object\n"
    "\n"
    "Fields per extraction:\n"
    "- subject: who the constraint applies to, in the ADR's own words (e.g., 'all endpoints', 'services', 'database layer'). "
    "Use natural language directly from the ADR text. Never invent dotted module paths.\n"
    "- object: what the constraint targets, in the ADR's own words (e.g., 'auth module', 'mysql', 'caching logic'). "
    "Use natural language directly from the ADR text. Never invent dotted module paths.\n"
    "- predicate: one of prohibits_dependency, requires_dependency, prohibits_implementation, requires_implementation\n"
    "- justification: concise reason for the constraint, from the ADR\n"
    "\n"
    "Scoping:\n"
    "- Use 'codebase' as subject for codebase-wide constraints (e.g., 'we will use X' tech-choice ADRs)\n"
    "- Do NOT use wildcards in subject or object fields.\n"
    "\n"
    "Extraction rules:\n"
    "1. MULTIPLE PREDICATES: emit more than one constraint when a single sentence constrains "
    "both what a module must do (implementation layer) and how (dependency layer). "
    "Example: 'All B must implement Y using X package' → "
    "subject='all B', object='Y', predicate=requires_implementation + "
    "subject='all B', object='X package', predicate=requires_dependency.\n"
    "\n"
    "2. EXCLUSION PATTERN — 'no module outside X shall do Y': extract TWO constraints:\n"
    "   a. subject='codebase', predicate=prohibits_*, object=Y  — general prohibition\n"
    "   b. subject=X, predicate=requires_*, object=Y  — explicit responsibility of X\n"
    "\n"
    "3. REPLACEMENT / SUPERCEDES PATTERN — 'Replace X with Y' or 'Switch to Y' (superceding X): extract TWO constraints:\n"
    "   a. subject='codebase', predicate=prohibits_dependency, object=X  — prohibition of old technology\n"
    "   b. subject='codebase', predicate=requires_dependency, object=Y  — requirement of new technology\n"
    "\n"
    "4. LAYER DISAMBIGUATION: parse verb and object as a unit.\n"
    "Verbs carry polarity (required vs prohibited). Objects carry layer (dependency vs implementation). Neither is sufficient alone.\n"
    "Polarity from verb:\n"
    "\n"
    "must / shall / owns / is responsible for → required\n"
    "must not / shall not / may not → prohibited\n"
    "\n"
    "Layer from object:\n"
    "Names a module, library, or package → *_dependency\n"
    "Describes a behaviour, pattern, or logic → *_implementation\n"
)

FEW_SHOT_EXAMPLES = [
    lx.data.ExampleData(
        text="Direct MySQL connections are prohibited for services "
             "in the app.services namespace.",
        extractions=[
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="Direct MySQL connections are prohibited for services",
                attributes={
                    "subject": "services",
                    "object": "MySQL",
                    "predicate": "prohibits_dependency",
                    "justification": "Direct MySQL connections are prohibited for services.",
                },
            )
        ],
    ),
    lx.data.ExampleData(
        text="All API endpoints shall implement authentication "
             "through middleware.",
        extractions=[
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="All API endpoints shall implement authentication",
                attributes={
                    "subject": "all API endpoints",
                    "object": "authentication",
                    "predicate": "requires_implementation",
                    "justification": "All API endpoints must implement authentication.",
                },
            ),
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="through middleware",
                attributes={
                    "subject": "all API endpoints",
                    "object": "middleware",
                    "predicate": "requires_dependency",
                    "justification": "All API endpoints must use middleware for authentication.",
                },
            ),
        ],
    ),
    lx.data.ExampleData(
        text="All services must import internal logging module for structured log output.",
        extractions=[
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="must import internal logging module",
                attributes={
                    "subject": "all services",
                    "object": "internal logging module",
                    "predicate": "requires_dependency",
                    "justification": "All services must import the internal logging module.",
                },
            ),
        ],
    ),
    lx.data.ExampleData(
        text="No module outside auth module shall implement "
            "authentication logic. Only middleware module is permitted "
            "to define authentication behavior.",
        extractions=[
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="No module outside auth shall implement authentication logic",
                attributes={
                    "subject": "codebase",
                    "object": "authentication logic",
                    "predicate": "prohibits_implementation",
                    "justification": "No module outside auth shall implement authentication logic.",
                },
            ),
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="Only middleware is permitted to define authentication behavior",
                attributes={
                    "subject": "auth module",
                    "object": "authentication logic",
                    "predicate": "requires_implementation",
                    "justification": "Only the auth module is permitted to define authentication behavior.",
                },
            ),
        ],
    ),
    lx.data.ExampleData(
        text="We will use Flask. Server should be simple - pretty much just "
             "with a GraphQL endpoint and GraphfixQL.",
        extractions=[
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="We will use Flask",
                attributes={
                    "subject": "codebase",
                    "object": "Flask",
                    "predicate": "requires_dependency",
                    "justification": "The server will use Flask as its web framework.",
                },
            ),
        ],
    ),
    lx.data.ExampleData(
        text="No module outside app.database shall import mysql.connector directly.",
        extractions=[
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="No module outside app.database",
                attributes={
                    "subject": "codebase",
                    "object": "mysql.connector",
                    "predicate": "prohibits_dependency",
                    "justification": "No module outside database shall import mysql.connector directly.",
                },
            ),
            lx.data.Extraction(
                extraction_class="adr_constraint",
                extraction_text="database module",
                attributes={
                    "subject": "database module",
                    "object": "mysql.connector",
                    "predicate": "requires_dependency",
                    "justification": "Only the database module may import mysql.connector.",
                },
            ),
        ],
    ),
]