# Class demo feedback

`class-demo-feedback.xlsx` holds what the class told us about the PharmAgentics demo: the five-question platform questionnaire, thumbs up and down on answers, the session ratings and written suggestions. It is a copy of the app's stored feedback at the time it was exported, with sheets Summary, Questionnaire, Answer votes, Session ratings and Comments.

Refresh it with:

```
uv run python deploy/gcp.py feedback --project pharmagentics --account <you>
```

That downloads the bucket's `feedback/` folder, prints the report and rewrites the workbook. Read the free-text cells before you commit the new file.

This repository is public. The workbook carries only the pseudonymous participant IDs the app already stores and role names such as "Commercial Analyst"; it holds no names or emails, and the test login's records are left out. The free-text answers are published exactly as people wrote them.

Questionnaire version 1 used the ten-statement SUS. Responses to it, if any, stay in the workbook with their SUS score; version 2 reports UMUX-Lite and its SUS-equivalent.
