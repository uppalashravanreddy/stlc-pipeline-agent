---
name: fetch-user-story
description: Fetch and format a user story from Jira by ticket ID into a pipeline-ready structure. Invoke when the user provides a ticket ID instead of story text.
---

## Purpose
Transform a raw Jira ticket (ID, summary, description, ACs) into a clean, structured user story that the STLC pipeline can process consistently.

## When to invoke
- User provides a Jira ticket ID (e.g. KAN-28, PROJ-14)
- Story text is missing, incomplete, or only a ticket reference
- Beginning of any pipeline run where input is a ticket number

## Steps

1. **Extract the ticket key** from user input (format: PROJECT-NUMBER)

2. **Fetch from Jira** using `python tools/jira_client.py` or the `--ticket` flag
   - Retrieve: summary, description, acceptance criteria
   - If fetch fails: ask user to paste the story text directly

3. **Validate completeness** — a pipeline-ready story must have:
   - A clear user role ("As a [role]")
   - A stated goal ("I want to [action]")
   - At least 3 acceptance criteria
   - If any are missing: note the gap but proceed with what exists

4. **Format the output** as:
   ```
   Feature: [TICKET-ID]: [Summary]

   User Story:
   As a [role], I want to [goal] so that [benefit].

   Acceptance Criteria:
   - [AC 1]
   - [AC 2]
   - [AC N]
   ```

5. **Hand off** — pass `feature_name` and `user_story` to the pipeline orchestrator

## Output
Structured `feature_name` + `user_story` text ready for Phase 0 classification.

## Notes
- Never fabricate acceptance criteria not in the ticket
- If description is in Jira wiki markup, convert to plain text
- Ticket ID must be preserved in the feature_name for traceability
