# Search evaluation source decision

Status: pre-result design decision; no provider comparison has run.

- Primary objective: source-supported task pass rate versus the host's current
  fixed search service. Cost is secondary and reported separately.
- FreshQA may supply time-sensitive tasks, but its answer-level score cannot be
  reused as a search-provider score. Use a retained, licensed dataset snapshot.
- BrowseComp may supply difficult browsing tasks, but only tasks that can be
  judged from the common search output contract enter the primary comparison.
- Provider identity is hidden from the judge. Every service receives the same
  query, result limit, time window and downstream judging procedure.
- The previous LLM live-execution tasks are excluded: they test model routing,
  contain different operations, and cannot establish web-search quality.

Primary sources checked on 2026-09-06:

- https://github.com/openai/simple-evals (`browsecomp_eval.py`, MIT)
- https://github.com/freshllms/freshqa (Apache-2.0; dated dataset releases)

Current candidate: 60 content-committed SimpleQA rows, 20 held out as two rows
from each of ten topics. The public snapshot contains query/answer commitments,
not raw benchmark content. Evaluation reloads the exact source bytes, verifies
every commitment, and binds result task IDs and splits back to that snapshot.

Still required before freeze: Chinese and time-sensitive task coverage, an
external task contribution, exact judge model/version and piloted disagreement
procedure, provider versions/accounts, and authorized comparison budget.

## Candidate-source disposition

| Source | Decision | Reason |
|---|---|---|
| FreshQA 2026-04-21 | use for time-sensitive candidate rows once the exact sheet export is retained | official repository is Apache-2.0 and versions the sheet, but Google Sheets was unreachable from this build environment |
| Chinese SimpleQA | do not ingest yet | the official GitHub repository reports MIT while the Hugging Face dataset card reports CC-BY-NC-SA-4.0; commercial-use rights are therefore unresolved |
| CDQA | do not ingest | useful Chinese dynamic questions, but the official repository declares no license |
| UIS-QA / BrowseComp-ZH | secondary agent benchmark only | they intentionally require navigation or deep browsing beyond the common title/snippet contract |
| WideSearch | secondary end-to-end benchmark only | MIT and bilingual, but measures broad multi-step collection rather than one-call search-provider quality |

The cleanest remaining route is to combine licensed FreshQA rows with a small
external Chinese task contribution. That closes time-sensitive, Chinese, and
external-origin coverage without pretending a deep-research benchmark measures
the same operation as a search API.

## External contribution intake

Raw submissions are processed locally by
`experiments/search_evaluation/commit_external_contribution.py`. The command
requires explicit evaluation/public-commitment permission, submitter authority,
and a no-personal-data declaration. It writes an owner-only `0600` private
record and a public task containing only commitments. Raw questions, answers,
reference URLs, contribution IDs, and batch IDs must never be sent to the
hosted contract-validation API; public provenance contains only their digests.

The existence of this intake is not external contribution evidence. That gate
remains open until an independent user submits a task and the retained private
record passes review.

Private records are plaintext JSON protected by local directory/file modes
`0700/0600`; they are not encrypted at rest. Only reviewed, non-personal-data
submissions under the versioned contribution terms may enter this path. A
future hosted intake requires managed encryption, deletion/withdrawal handling,
and identity/consent audit before accepting real submissions.
