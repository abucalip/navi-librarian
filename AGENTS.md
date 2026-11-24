# Navi Librarian agent instructions

Read [ARCHITECTURE.md](docs/ARCHITECTURE.md) in full before running any repository search or opening source files. Use its ownership map to identify the relevant modules and narrow subsequent searches.

Keep updates and replies concise. Avoid chattiness, repetition, and unnecessary detail. Read only files relevant to the task, keep searches and tool output focused, and avoid work that wastes tokens or usage.

Follow the [development workflow](docs/DEVELOPMENT_WORKFLOW.md). The owner applies this rule across the project:

End the task after a successful push and after creating or updating any requested PR. Do not wait for, watch, or poll CI after pushing. The owner handles post-push CI and merge gates unless they explicitly ask the agent to handle them.
