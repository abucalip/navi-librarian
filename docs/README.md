# Docs

Start at [`PROJECT_STATUS.md`](PROJECT_STATUS.md) (rolling snapshot + next action), [`ACTIVE_WORK.md`](ACTIVE_WORK.md) (open server/web queue), and [`ARCHITECTURE.md`](ARCHITECTURE.md) (file + focused-test router).

| Where | What |
| --- | --- |
| top level | Standing docs: `PROJECT_STATUS`, `ACTIVE_WORK`, `ARCHITECTURE`, `DEVELOPMENT_WORKFLOW`, `DECISIONS`, `REQUIREMENTS`, `TEST_PLAN`, `LOCAL_UI_TESTING`, `UI_DESIGN_RULES`, `DEPLOYMENT`, `SESSION_CONTEXT_SEARCH` |
| [`contracts/`](contracts/) | Shared server API contracts (server v2, search, radio, playlist inbox, recommendations) |
| [`plans/`](plans/) | Active server/web plans with unbuilt steps or open decisions |
| [`design/`](design/) | Mockups, tokens, and design tooling |
| [`architecture/`](architecture/) | Generated inventories |
| [`archive/`](archive/README.md) | Finished plans, migrated native-client plans (`archive/native-clients/`), and historical logs (excluded from default grep via `.rgignore`) |

When a plan's build is finished, move it to `archive/completed/` and fix its links in the same change.
