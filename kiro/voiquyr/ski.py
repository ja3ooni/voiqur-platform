#!/usr/bin/env python3

from pathlib import Path
import shutil

home = Path.home()

user_skill_dirs = [
    home / ".claude/skills",
    home / ".claude/.agents/skills",
    home / ".claude/.cursor/skills"
]

plugin_dirs = [
    home / ".claude/plugins/marketplaces"
]

cleanup_dirs = [
    home / ".claude/plugins/cache",
    home / ".claude/homunculus",
    home / "Library/Application Support/Claude/local-agent-mode-sessions"
]


def collect_skill_names(paths):
    skills = set()
    for root in paths:
        if root.exists():
            for f in root.rglob("*.md"):
                skills.add(f.stem)
    return skills


print("Collecting plugin skills...")
plugin_skills = collect_skill_names(plugin_dirs)

print("Collecting user skills...")
user_skills = collect_skill_names(user_skill_dirs)

duplicates = plugin_skills & user_skills

print(f"Duplicate skills found: {len(duplicates)}")

for skill in duplicates:
    for d in user_skill_dirs:
        file = d / f"{skill}.md"
        if file.exists():
            print(f"Removing duplicate user skill {file}")
            file.unlink()


print("\nRemoving cached plugin copies...")

for d in cleanup_dirs:
    if d.exists():
        print(f"Cleaning {d}")
        shutil.rmtree(d)

print("\nCleanup complete")