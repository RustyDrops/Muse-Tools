# 12 - Turn a PDF into a podcast

From the 128 Muse use cases directory (bookmark [319], via the OpenBuilder
listing): "PDF to podcast" as a plain prompt job. This is not a summary and
not a read-aloud. It turns one document you supply into a two-host
conversation a listener can follow without seeing the page, using only what
the document actually says.

## The prompt

"Turn the attached PDF into a podcast episode.

1. Read the whole document first. List its main points, in its own order,
   with the page each one comes from. Show me that list before scripting.
2. Write a two-host script: one host explains, the other asks the questions
   a smart listener would ask. Conversational, not lecture. Target
   [10 / 20 / 30] minutes, which is roughly [1,500 / 3,000 / 4,500] spoken
   words - say which target you are writing to.
3. Every claim in the script must come from the document. If you add
   context the document does not contain, mark that line [added context]
   in the script so I can cut it. Never invent examples, numbers, quotes,
   or the author's views.
4. Quotes from the document stay exact and get the page number in the
   script notes.
5. End with: the 3 things a listener should remember, and one honest
   limit - what the document does not cover.
6. Stop after the script. I approve the exact script before any audio
   is made. No voices, music, or publishing until I say go."

## The rules that make it trustworthy

- Script first, audio second. Approval is on the exact script text.
- The page list in step 1 is the check: if a point is not on it, it does
  not belong in the episode.
- Long PDFs: ask for a chapter at a time and keep one running point list,
  instead of letting the model skim and improvise the middle.
- A document you do not have the rights to republish stays a private
  episode for you. The prompt does not change the rights.
