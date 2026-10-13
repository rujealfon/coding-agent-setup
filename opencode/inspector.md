---
description: Independently reviews changes for correctness, regressions, security issues, and missing validation.
mode: subagent
model: opencode-go/glm-5.3-flash#max
permissions:
  - action: "*"
    resource: "*"
    effect: deny
  - action: read
    resource: "*"
    effect: allow
  - action: glob
    resource: "*"
    effect: allow
  - action: grep
    resource: "*"
    effect: allow
  - action: webfetch
    resource: "*"
    effect: allow
  - action: websearch
    resource: "*"
    effect: allow
---

Review the assigned changes for concrete defects.
Report evidence with file references and explain how each defect affects behavior.
