# Load the required category skill from the project's approved skill paths.
"""Load the required category skill from the project's approved skill paths."""
from pathlib import Path
import re

_SKILLS = {"CI001": "c2c-access", "CI002": "c2c-launch", "CI003": "c2c-completion"}


# Read an approved skill file and extract its content and guidance.
def _read_skill(name: str) -> dict:
    path = Path(__file__).resolve().parents[1] / "skills" / name / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    content = text.split("---", 2)[-1].strip()
    _, marker, rules = content.partition("SOP as follows:")
    rules = rules.split("\n## Apply the rules to API evidence", 1)[0].strip() if marker else content
    return {"name": name, "content": content, "rules": rules}


# Return shared rules and the scenario index without the detailed scenario sections.
def load_category_skill(issue_id: str) -> dict:
    skill = _read_skill(_SKILLS[issue_id])
    overview, marker, _ = skill['content'].partition('\n## Scenarios\n')
    if not marker:
        raise ValueError('Category skill has no scenario sections')
    skill.update(content=overview, rules=overview.split('## Shared rules\n', 1)[1])
    return skill


# Return only a scenario section from the selected category's approved file.
def load_scenario_skill(issue_id: str, scenario_id: str) -> dict:
    """Return only a scenario section from the selected category's approved file."""
    skill = _read_skill(_SKILLS[issue_id])
    sections = list(re.finditer(r'^### ([A-Z]{2}\d{3}) \| .+$', skill['content'], re.M))
    for index, section in enumerate(sections):
        if section[1] == scenario_id:
            end = sections[index + 1].start() if index + 1 < len(sections) else len(skill['content'])
            return {'skill': skill['name'], 'scenario_id': scenario_id,
                    'rules': skill['content'][section.start():end].strip()}
    raise ValueError('Scenario is not in the selected category skill')


# Load the wording guidance used for incident messages and user-information requests.
def load_communication_skill() -> dict:
    return _read_skill("c2c-communication")
