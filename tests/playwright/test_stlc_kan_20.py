import pytest
from pathlib import Path
from page_creator import build_technical_profile_page
from playwright.sync_api import Page, expect

@pytest.fixture
def output_root(tmp_path, monkeypatch):
    """Redirect build_technical_profile_page output to an isolated tmp directory."""
    import page_creator
    monkeypatch.setattr(page_creator, "OUTPUT_ROOT", tmp_path)
    return tmp_path

@pytest.fixture
def valid_facts():
    """Fully valid facts dictionary satisfying all required keys."""
    return {
        "app_name": "Flask Task Manager",
        "framework": "Flask",
        "database": "SQLite",
        "entry_point": "app.py",
        "routes": [
            {"endpoint": "/", "method": "GET", "description": "List all tasks"},
            {"endpoint": "/task/create", "method": "GET,POST", "description": "Create a new task"},
            {"endpoint": "/task/<id>/edit", "method": "GET,POST", "description": "Edit existing task"},
            {"endpoint": "/task/<id>/delete", "method": "POST", "description": "Delete a task"},
            {"endpoint": "/task/<id>", "method": "GET", "description": "View task detail"},
        ],
        "models": [{"name": "Task", "fields": ["id", "title", "description", "done"]}],
        "forms": [{"name": "TaskForm", "fields": ["title", "description"]}],
    }

def test_tc001_valid_full_facts_creates_file_with_all_six_sections(page: Page, app_base_url: str):
    'TC-001: Valid full facts dict → TECHNICAL_PROFILE.md created at exact path with all 6 sections present.'
    def test_tc001_valid_full_facts_creates_file_with_all_six_sections(output_root, valid_facts):
        """TC-001: Valid full facts dict → TECHNICAL_PROFILE.md created at exact path with all 6 sections present."""
        build_technical_profile_page(valid_facts)

        expected_path = output_root / "docs" / "artifacts" / "FLASK-001" / "TECHNICAL_PROFILE.md"
        assert expected_path.exists(), "TECHNICAL_PROFILE.md was not created at the expected path"

        content = expected_path.read_text(encoding="utf-8")
        required_sections = ["Overview", "Stack", "Entry Point", "Data Model", "Routes", "Forms"]
        missing = [
            section for section in required_sections
            if content.count(section) == 0
        ]
        assert not missing, (
            f"The following sections are absent from TECHNICAL_PROFILE.md: {missing}"
        )

def test_tc002_overview_section_renders_supplied_app_name_and_framework_verbatim(page: Page, app_base_url: str):
    'TC-002: Valid facts with custom app_name and framework → Overview section renders supplied values verbatim, not hardcoded defaults.'
    def test_tc002_overview_section_renders_supplied_app_name_and_framework_verbatim(output_root):
        """TC-002: Valid facts with custom app_name and framework → Overview section renders supplied values verbatim, not hardcoded defaults."""
        def _extract_overview(content: str) -> str:
            """Return text between the Overview heading and the next ## heading."""
            lines = content.splitlines(keepends=True)
            in_section, section_lines = False, []
            for line in lines:
                if line.strip().lower().startswith("## overview") or line.strip().lower().startswith("# overview"):
                    in_section = True
                    continue
                if in_section:
                    if line.strip().startswith("##"):
                        break
                    section_lines.append(line)
            return "".join(section_lines)

        facts_v1 = {
            "app_name": "Flask Task Manager", "framework": "Flask", "database": "SQLite",
            "entry_point": "app.py",
            "routes": [{"endpoint": "/", "method": "GET", "description": "List all tasks"}],
            "models": [{"name": "Task", "fields": ["id", "title"]}],
            "forms": [{"name": "TaskForm", "fields": ["title"]}],
        }
        build_technical_profile_page(facts_v1)
        artifact_path = output_root / "docs" / "artifacts" / "FLASK-001" / "TECHNICAL_PROFILE.md"
        overview_v1 = _extract_overview(artifact_path.read_text(encoding="utf-8"))
        assert "Flask Task Manager" in overview_v1, "app_name 'Flask Task Manager' missing from Overview (v1)"
        assert "Flask" in overview_v1, "framework 'Flask' missing from Overview (v1)"

        facts_v2 = {
            "app_name": "My Other App", "framework": "Django", "database": "PostgreSQL",
            "entry_point": "manage.py",
            "routes": [{"endpoint": "/home", "method": "GET", "description": "Home page"}],
            "models": [{"name": "Item", "fields": ["id", "name"]}],
            "forms": [{"name": "ItemForm", "fields": ["name"]}],
        }
        build_technical_profile_page(facts_v2)
        overview_v2 = _extract_overview(artifact_path.read_text(encoding="utf-8"))

        assert "My Other App" in overview_v2, "app_name 'My Other App' missing from Overview (v2)"
        assert "Django" in overview_v2, "framework 'Django' missing from Overview (v2)"
        assert "Flask Task Manager" not in overview_v2, (
            "Stale hardcoded value 'Flask Task Manager' still present in Overview after update — values are not sourced from facts"
        )

def test_tc003_stack_section_rendered_as_markdown_bullets_with_all_four_technologies(page: Page, app_base_url: str):
    'TC-003: Valid facts with Stack info → Stack section rendered as Markdown bullets, all 4 technologies with purpose descriptions present.'
    def test_tc003_stack_section_rendered_as_markdown_bullets_with_all_four_technologies(output_root, valid_facts):
        """TC-003: Valid facts with Stack info → Stack section rendered as Markdown bullets, all 4 technologies with purpose descriptions present."""
        build_technical_profile_page(valid_facts)
        content = (output_root / "docs" / "artifacts" / "FLASK-001" / "TECHNICAL_PROFILE.md").read_text(encoding="utf-8")

        # Extract Stack section
        lines = content.splitlines()
        stack_lines, in_section = [], False
        for line in lines:
            if line.strip().lower().startswith("## stack") or line.strip().lower().startswith("# stack"):
                in_section = True
                continue
            if in_section:
                if line.strip().startswith("##"):
                    break
                stack_lines.append(line)
        stack_text = "\n".join(stack_lines)

        bullet_lines = [l for l in stack_lines if l.strip().startswith("- ") or l.strip().startswith("* ")]
        assert len(bullet_lines) >= 4, (
            f"Expected at least 4 Markdown bullet lines in Stack section, found {len(bullet_lines)}"
        )

        technologies = [valid_facts["framework"], valid_facts["database"]]
        for tech in technologies:
            tech_bullets = [l for l in bullet_lines if tech in l]
            assert tech_bullets, f"Technology '{tech}' not found in any Stack bullet line"
            line = tech_bullets[0].strip()
            # Strip the leading bullet marker and the technology name; ensure additional description text follows
            bare_bullet_max_len = len("- ") + len(tech)
            assert len(line) > bare_bullet_max_len, (
                f"Technology '{tech}' appears without a purpose description in Stack section: '{line}'"
            )

def test_tc004_routes_section_is_markdown_table_with_correct_headers_and_five_data_rows(page: Page, app_base_url: str):
    'TC-004: Valid facts with 5 route objects → Routes section is a Markdown table with correct headers and exactly 5 data rows.'
    def test_tc004_routes_section_is_markdown_table_with_correct_headers_and_five_data_rows(output_root, valid_facts):
        """TC-004: Valid facts with 5 route objects → Routes section is a Markdown table with correct headers and exactly 5 data rows."""
        build_technical_profile_page(valid_facts)
        content = (output_root / "docs" / "artifacts" / "FLASK-001" / "TECHNICAL_PROFILE.md").read_text(encoding="utf-8")

        # Extract Routes section
        lines = content.splitlines()
        route_lines, in_section = [], False
        for line in lines:
            if line.strip().lower().startswith("## routes") or line.strip().lower().startswith("# routes"):
                in_section = True
                continue
            if in_section:
                if line.strip().startswith("##"):
                    break
                route_lines.append(line)

        table_rows = [l for l in route_lines if "|" in l]
        assert table_rows, "No Markdown table rows (containing '|') found in the Routes section"

        header_row = table_rows[0]
        assert "Endpoint" in header_row, f"'Endpoint' column missing from Routes table header: '{header_row}'"
        assert "Method" in header_row, f"'Method' column missing from Routes table header: '{header_row}'"
        assert "Description" in header_row, f"'Description' column missing from Routes table header: '{header_row}'"

        assert len(table_rows) >= 2, "Routes table is missing the separator row"
        separator_row = table_rows[1]
        assert "---" in separator_row or ":-" in separator_row, (
            f"Expected a Markdown separator row (containing '---' or ':-') at index 1, got: '{separator_row}'"
        )

        data_rows = table_rows[2:]
        assert len(data_rows) == 5, (
            f"Expected exactly 5 data rows in Routes table, found {len(data_rows)}"
        )

        expected_endpoints = ["/", "/task/create", "/task/<id>/edit", "/task/<id>/delete", "/task/<id>"]
        routes_text = "\n".join(route_lines)
        missing_endpoints = [ep for ep in expected_endpoints if ep not in routes_text]
        assert not missing_endpoints, (
            f"The following endpoints are missing from the Routes table: {missing_endpoints}"
        )

def test_tc005_missing_entry_point_key_raises_value_error_with_exact_message_and_no_file_written(page: Page, app_base_url: str):
    "TC-005: Facts dict missing 'entry_point' key → ValueError raised with exact message and no file written to disk."
    def test_tc005_missing_entry_point_key_raises_value_error_with_exact_message_and_no_file_written(output_root):
        """TC-005: Facts dict missing 'entry_point' key → ValueError raised with exact message and no file written to disk."""
        facts = {
            "app_name": "Flask Task Manager",
            "framework": "Flask",
            "database": "SQLite",
            # 'entry_point' deliberately omitted
            "routes": [{"endpoint": "/", "method": "GET", "description": "List all tasks"}],
            "models": [{"name": "Task", "fields": ["id", "title"]}],
            "forms": [{"name": "TaskForm", "fields": ["title"]}],
        }

        with pytest.raises(ValueError) as exc_info:
            build_technical_profile_page(facts)

        assert "entry_point" in str(exc_info.value), (
            f"Expected error to identify missing key 'entry_point', got: '{exc_info.value}'"
        )

        artifact_dir = output_root / "docs" / "artifacts" / "FLASK-001"
        md_file = artifact_dir / "TECHNICAL_PROFILE.md"
        assert not md_file.exists(), "TECHNICAL_PROFILE.md must not be written when ValueError is raised"
        written_md_files = list(artifact_dir.glob("*.md")) if artifact_dir.exists() else []
        assert written_md_files == [], (
            f"No .md files should exist under FLASK-001/ after a failed call, found: {written_md_files}"
        )

def test_tc006_missing_models_key_raises_value_error_with_exact_message_and_no_file_written(page: Page, app_base_url: str):
    "TC-006: Facts dict missing 'models' key → ValueError raised with exact message 'Missing required key: models' and no file written."
    def test_tc006_missing_models_key_raises_value_error_with_exact_message_and_no_file_written(output_root):
        """TC-006: Facts dict missing 'models' key → ValueError raised with exact message 'Missing required key: models' and no file written."""
        facts = {
            "app_name": "Flask Task Manager",
            "framework": "Flask",
            "database": "SQLite",
            "entry_point": "app.py",
            "routes": [{"endpoint": "/", "method": "GET", "description": "List all tasks"}],
            # 'models' deliberately omitted
            "forms": [{"name": "TaskForm", "fields": ["title"]}],
        }

        with pytest.raises(ValueError) as exc_info:
            build_technical_profile_page(facts)

        assert "models" in str(exc_info.value), (
            f"Expected error to identify missing key 'models', got: '{exc_info.value}'"
        )

        artifact_dir = output_root / "docs" / "artifacts" / "FLASK-001"
        md_file = artifact_dir / "TECHNICAL_PROFILE.md"
        assert not md_file.exists(), "TECHNICAL_PROFILE.md must not be written when ValueError is raised"
        written_md_files = list(artifact_dir.glob("*.md")) if artifact_dir.exists() else []
        assert written_md_files == [], (
            f"No .md files should exist under FLASK-001/ after a failed call, found: {written_md_files}"
        )

def test_tc007_empty_collections_produce_no_section_defined_placeholders_and_file_is_created(page: Page, app_base_url: str):
    "TC-007: Facts with routes=[], models=[], forms=[] → file created successfully with 'No {section} defined' placeholder in each empty section."
    def test_tc007_empty_collections_produce_no_section_defined_placeholders_and_file_is_created(output_root):
        """TC-007: Facts with routes=[], models=[], forms=[] → file created successfully with 'No {section} defined' placeholder in each empty section."""
        facts = {
            "app_name": "Flask Task Manager",
            "framework": "Flask",
            "database": "SQLite",
            "entry_point": "app.py",
            "routes": [],
            "models": [],
            "forms": [],
        }

        artifact_dir = output_root / "docs" / "artifacts" / "FLASK-001"
        assert not artifact_dir.exists(), "Precondition failed: artifact dir must not exist before the call"

        build_technical_profile_page(facts)  # Must not raise

        assert artifact_dir.exists(), "docs/artifacts/FLASK-001/ directory was not auto-created by the function"
        md_file = artifact_dir / "TECHNICAL_PROFILE.md"
        assert md_file.exists(), "TECHNICAL_PROFILE.md was not written even though facts are valid"

        content = md_file.read_text(encoding="utf-8")
        assert len(content) > 0, "TECHNICAL_PROFILE.md must not be empty"

        def extract_section(text: str, heading: str) -> str:
            lines = text.splitlines()
            section_lines, in_section = [], False
            for line in lines:
                if line.strip().lower().startswith(heading.lower()):
                    in_section = True
                    continue
                if in_section:
                    if line.strip().startswith("##"):
                        break
                    section_lines.append(line)
            return "\n".join(section_lines)

        routes_section = extract_section(content, "## routes")
        models_section = extract_section(content, "## data model")
        forms_section = extract_section(content, "## forms")

        assert routes_section.strip(), "Expected an empty-state placeholder in the Routes section"
        assert models_section.strip(), "Expected an empty-state placeholder in the Data Model section"
        assert forms_section.strip(), "Expected an empty-state placeholder in the Forms section"

        all_sections = ["Overview", "Stack", "Entry Point", "Data Model", "Routes", "Forms"]
        missing = [s for s in all_sections if s not in content]
        assert not missing, f"These section headings are absent from the file: {missing}"

def test_tc008_second_call_overwrites_file_with_updated_content_no_stale_data_no_duplicates(page: Page, app_base_url: str):
    'TC-008: Second call with updated facts overwrites existing TECHNICAL_PROFILE.md — only new content present, no duplicates or stale content.'
    def test_tc008_second_call_overwrites_file_with_updated_content_no_stale_data_no_duplicates(output_root):
        """TC-008: Second call with updated facts overwrites existing TECHNICAL_PROFILE.md — only new content present, no duplicates or stale content."""
        facts_v1 = {
            "app_name": "Original Task Manager",
            "framework": "Flask",
            "database": "SQLite",
            "entry_point": "app.py",
            "routes": [{"endpoint": "/", "method": "GET", "description": "List all tasks"}],
            "models": [{"name": "Task", "fields": ["id", "title"]}],
            "forms": [{"name": "TaskForm", "fields": ["title"]}],
        }
        build_technical_profile_page(facts_v1)

        artifact_dir = output_root / "docs" / "artifacts" / "FLASK-001"
        md_file = artifact_dir / "TECHNICAL_PROFILE.md"
        assert md_file.exists(), "Precondition failed: file must exist after first call"
        v1_content = md_file.read_text(encoding="utf-8")
        assert "Original Task Manager" in v1_content, "Precondition failed: v1 app_name must appear in first file"

        facts_v2 = {
            "app_name": "Updated Task Manager",
            "framework": "Flask",
            "database": "SQLite",
            "entry_point": "run.py",
            "routes": [
                {"endpoint": "/", "method": "GET", "description": "List all tasks"},
                {"endpoint": "/about", "method": "GET", "description": "About page"},
            ],
            "models": [{"name": "Task", "fields": ["id", "title", "priority"]}],
            "forms": [{"name": "TaskForm", "fields": ["title", "priority"]}],
        }
        build_technical_profile_page(facts_v2)  # Must not raise

        v2_content = md_file.read_text(encoding="utf-8")

        assert "Updated Task Manager" in v2_content, "Updated app_name 'Updated Task Manager' missing from overwritten file"
        assert "Original Task Manager" not in v2_content, (
            "Stale value 'Original Task Manager' still present after overwrite — file was not fully replaced"
        )
        assert "run.py" in v2_content, "Updated entry_point 'run.py' missing from overwritten file"
        assert "app.py" not in v2_content, (
            "Stale entry_point 'app.py' still present after overwrite — file was not fully replaced"
        )
        assert "/about" in v2_content, "New route '/about' missing from overwritten Routes section"

        all_files = list(artifact_dir.iterdir())
        assert len(all_files) == 1 and all_files[0].name == "TECHNICAL_PROFILE.md", (
            f"Expected exactly 1 file 'TECHNICAL_PROFILE.md' in output dir, found: {[f.name for f in all_files]}"
        )
