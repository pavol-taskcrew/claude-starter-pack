# Claude Starter Pack

A collection of agents and skills for Claude Code to help you get started quickly.

## Contents

### Agents

| Agent | Description |
|-------|-------------|
| **launch-project** | Project setup specialist. Creates customized project structures with context folders, workfiles, and Git integration. |

### Skills

| Skill | Description |
|-------|-------------|
| **skill-creator** | Creates new Claude Code skills with proper structure and best practices. |

## Installation

Clone this repo and copy the contents to your `~/.claude/` folder:

```bash
git clone https://github.com/pavol-taskcrew/claude-starter-pack.git
cp -r claude-starter-pack/agents/* ~/.claude/agents/
cp -r claude-starter-pack/skills/* ~/.claude/skills/
rm -rf claude-starter-pack
```

Or ask Claude Code to do it for you:

```
Clone https://github.com/pavol-taskcrew/claude-starter-pack and copy the agents and skills to my ~/.claude folder.
```

## Usage

### launch-project

Say "launch project" or "set up a new project" and the agent will guide you through creating a project structure.

### skill-creator

Use `/skill-creator` or ask Claude to help you create a new skill.

## License

MIT
