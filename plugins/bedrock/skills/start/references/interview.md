# The new-project interview

Depth comes from the branches that apply, never from a score. A branch that does not apply is
skipped whole, never asked "for completeness".

## Branches
| Ask when the product… | Branch | Lands in |
|---|---|---|
| always | purpose: the core job, for whom | entry, a decision |
| always, once | scope: in the first version, explicitly out | decisions |
| always, early | type: web app, API, CLI, library, worker | entry, project commands |
| stores domain entities | entities, relations, states | an architecture note, the glossary |
| has accounts | identity, roles, permissions | decisions, critical zones |
| moves money | who pays whom and when, refunds | decisions, critical zones |
| calls outside services | which ones, their contracts | decisions, open questions |
| has scale, SLA or compliance needs | the numbers, the rules | architecture, a domain pack |
| has screens | which ones | scope; the design work goes to design-creator |
| always, last | anything still undecided | open questions |

## Cadence
- Open questions one at a time. A wall of questions is the most common interview failure.
- Discrete choices of one branch may share one question with buttons. Never mix branches.
- "Just do what's best": proceed on defaults, but still get what cannot be invented: the
  scope, the core entities, who holds the money if money moves.
- An answer nobody can give becomes an open question with the options and a leaning. The
  interview moves on.

## Where answers go
- A settled answer: a decision note, with why and the rejected options.
- An entity: the glossary and, when stored, the architecture note.
- An unknown: `open-questions.md`, never a decision.
Save each answer the moment it is given. The owner confirms coverage once, at the end.
