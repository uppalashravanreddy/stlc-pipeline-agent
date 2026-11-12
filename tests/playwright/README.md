# STLC Playwright tests

The pipeline generates Python pytest tests that use the `page` fixture supplied
by `pytest-playwright` and the `app_base_url` fixture in `conftest.py`.

Install dependencies and the browser once:

```powershell
python -m pip install -r tests/playwright/requirements.txt
python -m playwright install chromium
```

Set the application URL and run the generated tests:

```powershell
$env:STLC_BASE_URL = "http://localhost:8000"
python -m pytest -c tests/playwright/pytest.ini tests/playwright
```

Generated tests are committed to this directory by the Phase 7 PR flow.
Review selectors and expected UI behavior against the real application before
merging; the pipeline does not run these browser tests automatically.
