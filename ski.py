#!/usr/bin/env python3

import os
from pathlib import Path

USER_SKILLS = Path.home() / ".claude" / "skills"
USER_COMMANDS = Path.home() / ".claude" / "commands"
PLUGIN_DIR = Path.home() / ".claude" / "plugins"

def get_skill_names(directory):
    if not directory.exists():
        return set()
    return {p.stem for p in directory.glob("*.md")}

def get_plugin_skills():
    skills = set()

    if not PLUGIN_DIR.exists():
        return skills

    for plugin in PLUGIN_DIR.iterdir():
        skill_dir = plugin / "skills"
        if skill_dir.exists():
            skills |= get_skill_names(skill_dir)

    return skills


plugin_skills = get_plugin_skills()
user_skills = get_skill_names(USER_SKILLS)
user_commands = get_skill_names(USER_COMMANDS)

duplicates = (user_skills | user_commands) & plugin_skills

print(f"Found {len(duplicates)} duplicate skills:\n")

for skill in sorted(duplicates):
    skill_file = USER_SKILLS / f"{skill}.md"
    cmd_file = USER_COMMANDS / f"{skill}.md"

    if skill_file.exists():
        print(f"Removing user skill: {skill_file}")
        skill_file.unlink()

    if cmd_file.exists():
        print(f"Removing command skill: {cmd_file}")
        cmd_file.unlink()

print("\nCleanup complete.")
