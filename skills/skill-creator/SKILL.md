---
name: skill-creator
description: Creates new Claude Code agent skills with proper structure and best practices. Use when creating a new skill, building agent capabilities, or setting up skill files and folders.
---

# Skill Creator

Create well-structured Claude Code agent skills following official best practices.

## Instructions

When creating a new skill:

1. **Gather Requirements**
   - Ask for the skill name (lowercase, hyphens only)
   - Ask for a clear description of what the skill does
   - Ask when the skill should be triggered
   - Determine if tool restrictions are needed

2. **Create Skill Structure**
   - Create the skill folder in the appropriate location:
     - Personal: `~/.claude/skills/skill-name/`
     - Project: `.claude/skills/skill-name/`
   - Create the required `SKILL.md` file
   - Add supporting files if needed (scripts, templates, references)

3. **Write the SKILL.md File**
   Use this template:

   ```yaml
   ---
   name: skill-name
   description: [What it does]. Use when [trigger conditions].
   allowed-tools: [Optional: comma-separated list of allowed tools]
   ---

   # Skill Name

   ## Instructions
   [Clear, step-by-step guidance for Claude]

   ## Examples
   [Concrete usage examples]
   ```

4. **Validate the Skill**
   - Ensure name uses only lowercase letters, numbers, hyphens (max 64 chars)
   - Verify description explains WHAT and WHEN (max 1024 chars)
   - Check YAML frontmatter syntax (proper `---` delimiters, spaces not tabs)
   - Confirm file is saved as `SKILL.md` in the skill folder

## Best Practices

### Keep Skills Focused
- One skill = one capability
- Good: "pdf-form-filler", "git-commit-messages", "api-documentation"
- Avoid: "document-tools", "utilities" (too broad)

### Write Specific Descriptions
Include:
- What the skill does
- When Claude should use it
- Key trigger terms users might mention

### Use Tool Restrictions When Appropriate
For read-only or security-sensitive skills:
```yaml
allowed-tools: Read, Grep, Glob
```

### Add Supporting Files for Complex Skills
```
skill-name/
├── SKILL.md           # Required
├── reference.md       # Optional detailed docs
├── examples.md        # Optional examples
├── scripts/           # Optional helper scripts
└── templates/         # Optional templates
```

## Example: Creating a Simple Skill

**User request**: "Create a skill for writing API documentation"

**Result**:
```yaml
---
name: api-documenter
description: Generates comprehensive API documentation from code. Use when documenting APIs, creating endpoint references, or writing OpenAPI specs.
---

# API Documenter

## Instructions

1. Read the API source files
2. Extract endpoint definitions, parameters, and response types
3. Generate documentation with:
   - Endpoint path and method
   - Request parameters and body schema
   - Response format and status codes
   - Usage examples

## Output Format

Use OpenAPI 3.0 compatible YAML or Markdown tables depending on user preference.
```

## Version History
- v1.0.0: Initial release
