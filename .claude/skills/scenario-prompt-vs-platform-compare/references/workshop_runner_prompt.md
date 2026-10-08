# Workshop runner subagent prompt

Spawn one fresh subagent per workshop run (`general-purpose`, model `opus`, `run_in_background: true`).
Several runs may be launched in parallel. Replace `{WORKSPACE}`, `{PROMPTS}`, `{AS_OF}`, `{FOLDER}` and the
`{EVENT_ORDER}` lines before sending. Do not add anything about the platform result: the runner must stay blind.

---

You are a participant in an LNG scenario workshop. Execute a fixed sequence of prompts exactly as written,
acting as the LLM that answers each prompt, and save each step's output as a Markdown file. Work in Korean as the
prompts require.

## Folders (absolute paths)
- Workspace (read inputs, write all outputs here): {WORKSPACE}
- Prompt texts (verbatim from the workshop guide): {PROMPTS}

## Isolation rules (strict)
- Read ONLY files inside the two folders above. Do not open any other file or folder (no other run folders, no
  platform results, no source code, no databases).
- No web search or web fetch. Use only the Event markdown files and the catalog in 00_input.md.
- Do not look for or reuse any previous workshop results. Produce everything fresh.

## Procedure (one continuous run, in this order)
Step 0. Prepare 00_input.md
- The workspace already contains 00_input.md as a template. Its Driver Tree Catalog section is final: keep it
  exactly as is.
- Follow the instruction in {PROMPTS}/00a_input_prompt.txt. The workspace folder name is {FOLDER}, so the
  분석 기준일 is {AS_OF}.
- Read the "Event) ...md" files in the workspace and fill the Event blocks in this order:
{EVENT_ORDER}
  Fill Event ID with E1/E2/..., 제목, 요약, 발생 시각, and 핵심 사실 후보, preserving the original dates and numbers
  exactly. Do not invent facts, dates, or numbers. If the source does not state an occurrence time explicitly,
  use the most direct observation date stated in the source and say so.
- Overwrite 00_input.md with the completed input.

Steps 1-4. For each of step1_event_impact.txt, step2_interactions.txt, step3_dimensions.txt, step4_scenarios.txt:
- Take the prompt text verbatim and replace each {{...}} placeholder with the FULL content of the referenced
  file(s) (00_input.md, 01_event_impact.md, 02_event_interactions.md, 03_dimensions.md). Never summarize the
  pasted inputs.
- Answer that prompt carefully, following every rule and the output format, and save to the file name the
  prompt specifies.
- Treat each step's prompt as the only instructions for that step; earlier answers are available only through
  the pasted file contents.

Step 4a (conditional). Run step4a_additional.txt only if 03_dimensions.md has at least one entry in notUsed.
Save to the file name the prompt specifies. It must not modify 04_scenarios.md.

Step 5. Run step5_review.txt with the required inputs pasted in full; save to 05_agent_design_review.md. Leave
participant-scored fields blank as the prompt says.

Step 6 (conditional). Run step6_remediation.txt only if 05_agent_design_review.md contains at least one Critical
or Major finding that meets the eligibility conditions stated in that prompt.

## Final report (your reply)
Return a short report in Korean: the list of files created, whether Step 4a and Step 6 were executed and why, any
prompt rule you could not satisfy, and a summary of the final scenarios (title, choice combination, pressure,
probability, baseline). Do not paste full file contents.
