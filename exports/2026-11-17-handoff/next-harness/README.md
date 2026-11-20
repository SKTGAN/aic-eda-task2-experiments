# Proposed next Harness

This fresh development variant starts from the published program and uses the official model and evaluator interfaces.

- The first model call receives the 87-word English expert note and makes a short, falsifiable plan. Later plans use receipts from this run. Separate code generation receives the plan and a shorter prompt. The high/low split stays within the existing gateway cap.
- Candidate two can refine the first candidate when complete paired evidence shows improvement across a majority of represented cases, with no flagged identical-assignment timing discrepancy. Otherwise it tests the other component from the official initial program and carries observed evidence. Later repairs and exploration retain the earlier policy. Three consecutive rejected generated programs stop search if a scored candidate is available.
- Candidate parsing, edit-scope checks, request ID deduplication, selection on complete evaluator receipts and official budgeting stay in place. Public validation stays outside search.
- program.py is the published starting program. Do not initialize a new formal run with the best server candidate. The corresponding program for each server run is archived separately.
- Use the independent development runner in the review pack to screen 3 candidates on seed 1002 of the 3 training cases. Recheck the strongest on all nine before making a competition claim.
