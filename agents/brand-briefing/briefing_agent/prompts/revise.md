Some of your paragraphs break the brief's rules. Rewrite only those, and keep the same JSON shape ("answer", "stories", "charts").

Problems:
{problems}

Rules again:
- Every number is a claim token copied from the allowed list below. Never type a digit and never spell a number out ("two", "half", "percent"). If a sentence cannot be kept true without a number, remove the number.
- A story's paragraph uses only its own story's tokens. Do not invent a token.
- Short sentences, at most 20 words each. One plain paragraph: no bullets, no headings, no bold, no line breaks. The answer has at most three sentences and a story at most four.
- Readable names only ("Southeast", "primary care"), never ids such as territory:SOUTHEAST or PRIMARY_CARE.
- Do not mention splits by plan, specialty or channel, the method, the glossary or "considered and dropped": they are folded away.
- Say "association" for promotion. Use "because", "caused", "drove", "due to" or "explains" only for a story whose confidence is High.
- Never use "surveillance"; "new patients" only for NBRx; never name or number an individual rep.

Allowed tokens per piece:
{allowed}

What each number measures (describe a comparison only as this list does):
{glossary}

Your previous reply:
{reply}

Reply with JSON only.
