---
applyTo: '**'
---
# Steering Rules

## 1. General Principles

* Optimize for **clarity, simplicity, and learning**, not cleverness.
* Prefer **explicit, readable solutions** over abstractions.
* Assume the code will be **read by a junior-to-mid engineer learning AWS and system design**.
* If something is unclear or ambiguous, **stop and ask before proceeding**.

---

## 2. Architecture & Design

* Follow the architecture described in `design.md` **strictly**.
* Do **not invent new services, stacks, or flows** unless explicitly requested.
* Keep responsibilities clearly separated between components.
* Avoid tight coupling between stacks and services.
* Prefer managed AWS services over self-managed infrastructure.

---

## 3. Infrastructure as Code

* Use **AWS CDK with Python only**.
* Do **not** use Terraform, CloudFormation YAML, or SAM unless explicitly instructed.
* Do **not assume infrastructure is already deployed**.
* Avoid cross-stack references unless clearly justified.
* Prefer simple CDK constructs over advanced patterns.

---

## 4. Coding Standards (Python)

* Use clear, descriptive variable and function names.
* Keep functions small and single-purpose.
* Add comments for non-obvious logic or AWS-specific behavior.
* Public functions and classes should have docstrings.
* Avoid unnecessary third-party libraries.
* Always use context7 when I need code generation, setup or
configuration steps, or library/API documentation. This means
you should automatically use the Context7 MCP tools to resolve
library id and get library docs without me having to
explicitly ask.

---

## 5. AWS-Specific Guidance

* Provision resources in the 'ap-southeast-1' region whenever possible. 
* Enable observability (logs, metrics, tracing) when it adds learning value.
* Optimize for cost, but do not over-optimize unless asked.
* Clearly explain AWS concepts when they appear in code or design.

---

## 6. Safety & Scope Control

* Do not modify files outside the explicitly mentioned scope.
* Do not refactor existing code unless requested.
* Ask before changing public APIs or stack interfaces.
* Avoid destructive actions (deletions, migrations) unless explicitly instructed.


---

## 7. Output Expectations

* Explain *why* decisions are made, not just *what* is done.
* Use step-by-step reasoning for architecture and infrastructure changes.
* Prefer examples over theory.
* When generating code, ensure it is runnable and internally consistent.

---

## 8. When to Pause

The agent **must stop and ask for clarification** if:

* Requirements conflict with `design.md`
* A major architectural trade-off is required
* A decision would significantly increase complexity
* Multiple valid approaches exist with different implications

---

*End of steering rules.*
