import logging
import time
import threading
from datetime import datetime, timedelta
import pytest
from extractor import RepositoryExtractor, ValidationError
from playwright.sync_api import Page, expect

@pytest.fixture(scope="module")
def valid_tasks():
    return [
        {"id": 1, "title": "Alpha task",   "description": "First task desc",  "due_date": datetime(2025, 6, 1,  9,  0, 0), "status": "Open"},
        {"id": 2, "title": "Beta task",    "description": "Second task desc", "due_date": datetime(2025, 6, 2, 10,  0, 0), "status": "In Progress"},
        {"id": 3, "title": "Gamma task",   "description": "Third task desc",  "due_date": datetime(2025, 6, 3, 11,  0, 0), "status": "Done"},
        {"id": 4, "title": "Delta task",   "description": "Fourth task desc", "due_date": datetime(2025, 6, 4, 12,  0, 0), "status": "Blocked"},
        {"id": 5, "title": "Epsilon task", "description": "Fifth task desc",  "due_date": datetime(2025, 6, 5, 13,  0, 0), "status": "Open"},
    ]

@pytest.fixture(scope="function")
def fake_repository():
    """Return the FakeRepository class so individual tests can seed it independently."""
    from extractor import FakeRepository  # import here so collection never fails if class moves
    return FakeRepository

def test_tc001_extract_five_valid_records_returns_exact_field_mappings(page: Page, app_base_url: str):
    'TC-001: extract() on a 5-record repository returns all tasks with exact field mappings and zero WARNING-or-above log entries.'
    def test_tc001_extract_five_valid_records_returns_exact_field_mappings(fake_repository, valid_tasks, caplog):
        """TC-001: extract() on a 5-record repository returns all tasks with exact field mappings and zero WARNING-or-above log entries."""
        repo = fake_repository(records=valid_tasks)
        extractor = RepositoryExtractor(repository=repo)

        with caplog.at_level(logging.WARNING):
            result = extractor.extract()

        # Single compound assertion block: length, every field on every record, and clean log.
        assert len(result) == 5, f"Expected 5 tasks, got {len(result)}"
        for i, expected in enumerate(valid_tasks):
            assert result[i].id          == expected["id"],          f"id mismatch at index {i}"
            assert result[i].title       == expected["title"],       f"title mismatch at index {i}"
            assert result[i].description == expected["description"], f"description mismatch at index {i}"
            assert result[i].due_date    == expected["due_date"],    f"due_date mismatch at index {i}"
            assert result[i].status      == expected["status"],      f"status mismatch at index {i}"
        assert caplog.records == [], (
            f"Expected zero log warnings, got: {[r.message for r in caplog.records]}"
        )

def test_tc002_extract_empty_repository_returns_empty_list(page: Page, app_base_url: str):
    "TC-002: extract() on an empty repository returns an empty list (type list, length 0) and the extractor's fallback status is 'Not Specified'."
    def test_tc002_extract_empty_repository_returns_empty_list(fake_repository):
        """TC-002: extract() on an empty repository returns an empty list (type list, length 0) and the extractor's fallback status is 'Not Specified'."""
        repo = fake_repository(records=[])
        extractor = RepositoryExtractor(repository=repo)

        result = extractor.extract()

        # Single assertion block: return type, emptiness, and fallback-status contract.
        assert isinstance(result, list),  "extract() must return a list, not None or a generator"
        assert result == [],              "extract() on an empty repository must return an empty list"
        # Verify the fallback status default through the public/private API without records.
        # _default_status() surfaces the AC-2 contract; if the method is renamed, update here.
        assert extractor._default_status() == "Not Specified", (
            "Fallback status must be exactly 'Not Specified'"
        )

def test_tc003_extract_null_description_and_absent_due_date_applies_defaults(page: Page, app_base_url: str):
    "TC-003: extract() populates description with '' for null values and due_date with None when the key is absent, completing without exception."
    def test_tc003_extract_null_description_and_absent_due_date_applies_defaults(fake_repository):
        """TC-003: extract() populates description with '' for null values and due_date with None when the key is absent, completing without exception."""
        partial_tasks = [
            # description explicitly None; due_date present
            {"id": 101, "title": "No-description task", "description": None,
             "due_date": datetime(2025, 7, 1, 8, 0, 0), "status": "Open"},
            # due_date key entirely absent; description present
            {"id": 102, "title": "No-due-date task", "description": "Has a description",
             "status": "Pending"},
        ]
        repo = fake_repository(records=partial_tasks)
        extractor = RepositoryExtractor(repository=repo)

        result = extractor.extract()

        # Single assertion block covering length, default application, and passthrough fields.
        assert len(result) == 2,              "Expected exactly 2 tasks returned"
        # Record 0 — null description default
        assert result[0].description == "",   "Null description must be replaced with empty string"
        assert result[0].id          == 101
        assert result[0].title       == "No-description task"
        assert result[0].status      == "Open"
        assert result[0].due_date    == datetime(2025, 7, 1, 8, 0, 0), "due_date must be preserved for record with null description"
        # Record 1 — absent due_date default
        assert result[1].due_date    is None, "Absent due_date key must resolve to None"
        assert result[1].id          == 102
        assert result[1].title       == "No-due-date task"
        assert result[1].status      == "Pending"
        assert result[1].description == "Has a description", "description must be preserved for record with absent due_date"

def test_tc004_extract_one_thousand_records_completes_within_five_seconds(page: Page, app_base_url: str):
    'TC-004 [performance]: extract() processes 1,000 records in under 5 seconds with no MemoryError, returning all records with correct boundary ids.'
    @pytest.mark.performance
    def test_tc004_extract_one_thousand_records_completes_within_five_seconds(fake_repository):
        """TC-004 [performance]: extract() processes 1,000 records in under 5 seconds with no MemoryError, returning all records with correct boundary ids."""
        large_tasks = [
            {
                "id": i,
                "title": f"Task number {i}",
                "description": f"Description for task {i}",
                "due_date": datetime(2025, 1, 1) + timedelta(seconds=i),
                "status": "Open",
            }
            for i in range(1, 1001)
        ]
        repo = fake_repository(records=large_tasks)
        extractor = RepositoryExtractor(repository=repo)

        start = time.monotonic()
        result = extractor.extract()
        elapsed = time.monotonic() - start

        # Single assertion block: timing threshold, record count, and boundary spot-checks.
        assert elapsed < 5.0, (
            f"Extraction took {elapsed:.3f}s — exceeded the 5-second CI threshold"
        )
        assert len(result) == 1000, f"Expected 1000 records, got {len(result)}"
        assert result[0].id   == 1,    "First record id must be 1"
        assert result[999].id == 1000, "Last record id must be 1000"

def test_tc005_extract_256_char_title_truncates_or_raises_validation_error(page: Page, app_base_url: str):
    'TC-005: extract() with a 256-character title truncates to 255 chars and logs a WARNING.'
    def test_tc005_extract_256_char_title_truncates_or_raises_validation_error(fake_repository, caplog):
        """TC-005: extract() with a 256-character title truncates to 255 chars and logs a WARNING."""
        long_title = "A" * 256
        assert len(long_title) == 256, "Precondition: title must be exactly 256 characters"

        long_title_task = [{
            "id": 201,
            "title": long_title,
            "description": "Normal description",
            "due_date": datetime(2025, 8, 1, 9, 0, 0),
            "status": "Open",
        }]
        repo = fake_repository(records=long_title_task)
        extractor = RepositoryExtractor(repository=repo)

        with caplog.at_level(logging.WARNING):
            result = extractor.extract()

        assert len(result) == 1, "Truncation mode must still return 1 task"
        assert len(result[0].title) == 255, (
            f"Title must be truncated to 255 chars, got {len(result[0].title)}"
        )
        assert result[0].title == "A" * 255, "Truncated title must be first 255 'A' characters"
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("Task title exceeds maximum length" in msg for msg in warning_messages), (
            f"Expected WARNING containing 'Task title exceeds maximum length'; got: {warning_messages}"
        )
