# Important Clarification: Referee Status Logic

## "Potential Referees" Section

This section contains **contacted referees who have NOT accepted**, which includes:

1. **Declined**: `(Status: Declined)` - Explicitly declined the invitation
2. **No Response**: `(Status: No Response)` - Contacted but haven't responded
3. **Awaiting Response**: No status shown - Recently contacted, still waiting
4. **Other statuses**: Parse whatever status text is shown

## "Referees" Section

This section contains **ONLY referees who ACCEPTED** the invitation:

1. **Report Submitted**: Shows `(Rcvd: YYYY-MM-DD)` - Already submitted their report
2. **Report Pending**: Shows `(Due: YYYY-MM-DD)` - Accepted but report not yet submitted

## Example Breakdown

```
Potential Referees:
  Samuel Daudin #1 (Last Contact Date: 2025-02-04) (Status: Declined)      ← Declined
  John Doe #2 (Last Contact Date: 2025-02-10) (Status: No Response)        ← No response yet
  Jane Smith #3 (Last Contact Date: 2025-02-15)                            ← Awaiting response

Referees:
  Giorgio Ferrari #1 (Rcvd: 2025-06-02)                                    ← Accepted & submitted
  Juan Li #2 (Due: 2025-04-17)                                            ← Accepted, pending
```

## Updated Status Categories

1. **Contacted but no decision**: In "Potential Referees" with no status or "No Response"
2. **Declined**: In "Potential Referees" with "Status: Declined"
3. **Accepted, pending report**: In "Referees" with "Due:" date
4. **Accepted, report submitted**: In "Referees" with "Rcvd:" date

This means the total referee count includes:
- All contacted referees (whether they responded or not)
- All declined referees
- All accepted referees (whether report submitted or not)

## Key Insight

"Potential Referees" ≠ "Declined Referees"
"Potential Referees" = "Contacted but not (yet) accepted"

This is critical for accurate referee tracking and timeline analysis!
