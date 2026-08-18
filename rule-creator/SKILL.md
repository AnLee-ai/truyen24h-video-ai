---
name: rule-creator
description: "Use this skill whenever the user asks to create a rule, save a principle, add a new law, or define a persistent instruction (e.g., 'tạo rule', 'hãy lưu nguyên tắc này lại', 'thêm luật mới'). This skill guides the agent to create properly formatted Antigravity rule files and save them globally so they are persistently learned."
---

# Rule Creator

## Overview
This skill helps the user create new custom rules for the Antigravity agent. Rules are markdown files that dictate agent behavior, coding standards, or operational principles. 

This skill creates Global Rules, which apply to all projects and workspaces.

## Workflow

1. **Understand the Rule Intent**
   - Identify what behavior or standard the user wants to enforce.
   - If the user's request is vague, ask clarifying questions before creating the rule.

2. **Draft the Rule Content**
   - Rules MUST have a YAML frontmatter.
   - Required frontmatter fields:
     - `name`: A short, descriptive slug (e.g., `vietnamese-comments`).
     - `description`: A brief summary of what the rule does.
     - `trigger`: A string defining when the rule should activate (e.g., `model_decision`, `always_on`, or a specific context like "When writing code comments").
   - The body of the rule should be written in clear, imperative Markdown. Explain *why* the rule exists and *how* to follow it.

3. **Format Example**
   ```markdown
   ---
   name: [rule-name]
   description: [Brief description]
   trigger: [When should it trigger?]
   ---

   # [Rule Title]

   ## Context
   [Why does this rule exist?]

   ## Instructions
   - [Instruction 1]
   - [Instruction 2]
   ```

4. **Save the Rule**
   - Save the formatted rule to the global rules directory: `C:\Users\david\.gemini\config\rules\[rule-name].md`
   - Use the `write_to_file` tool to save it. Do not include `ArtifactMetadata` as this is a configuration file, not an artifact.

5. **Confirmation**
   - Tell the user that the rule has been successfully created and saved globally, and will take effect in future interactions matching the trigger.
