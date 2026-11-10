def test_TC_001_start_without_database_creates_project_root_database():
    'TC-001: Start with no database and create data.db in the project root.'
def test_TC_001_start_without_database_creates_project_root_database(isolated_project, app_process_factory):
    """TC-001: Start with no database and create data.db in the project root."""
    first = app_process_factory()
    time.sleep(1)
    first_started = first.poll() is None
    if first_started:
        first.terminate()
        first.wait(timeout=10)
    second = app_process_factory()
    time.sleep(1)
    second_started = second.poll() is None
    database = isolated_project / "data.db"
    assert first_started and second_started and database.is_file() and database.resolve().parent == isolated_project.resolve()

def test_TC_002_restart_without_secret_key_generates_distinct_long_keys():
    'TC-002: Restart without SECRET_KEY and generate a different 32-character-or-longer key each time.'
def test_TC_002_restart_without_secret_key_generates_distinct_long_keys(run_python):
    """TC-002: Restart without SECRET_KEY and generate a different 32-character-or-longer key each time."""
    command = "from app import app; print(app.config['SECRET_KEY'])"
    results = [run_python(command) for _ in range(3)]
    keys = [result.stdout.strip() for result in results]
    assert all(result.returncode == 0 for result in results) and all(len(key) >= 32 for key in keys) and len(set(keys)) == 3

def test_TC_003_configured_secret_key_is_retained_across_restarts():
    'TC-003: Start with a configured SECRET_KEY and retain its exact value across restarts.'
def test_TC_003_configured_secret_key_is_retained_across_restarts(run_python):
    """TC-003: Start with a configured SECRET_KEY and retain its exact value across restarts."""
    expected = "KAN14-qa-key-2026-11-10-keep-exactly"
    command = "from app import app; print(app.config['SECRET_KEY'])"
    results = [run_python(command, secret_key=expected) for _ in range(2)]
    assert all(result.returncode == 0 and result.stdout.strip() == expected for result in results)

def test_TC_004_corrupted_database_logs_error_and_exits_with_status_one():
    'TC-004: Boot with a corrupted database and log the cause before exiting with status 1.'
def test_TC_004_corrupted_database_logs_error_and_exits_with_status_one(isolated_project):
    """TC-004: Boot with a corrupted database and log the cause before exiting with status 1."""
    (isolated_project / "data.db").write_text("this is not a SQLite database", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "app.py"],
        cwd=isolated_project,
        env={key: value for key, value in os.environ.items() if key != "SECRET_KEY"},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 1 and "Database connection failed:" in output and "file is not a database" in output

def test_TC_005_all_specified_routes_return_http_200():
    'TC-005: Request all five specified routes and receive their expected HTTP statuses.'
def test_TC_005_all_specified_routes_return_http_200(isolated_project, http_request):
    """TC-005: Request all five specified routes and receive their expected HTTP statuses."""
    import socket

    with socket.socket() as port_socket:
        port_socket.bind(("127.0.0.1", 0))
        port = port_socket.getsockname()[1]

    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            f"from app import app; app.run(host='127.0.0.1', port={port}, use_reloader=False)",
        ],
        cwd=isolated_project,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 10
        ready = False
        while time.monotonic() < deadline and process.poll() is None:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    ready = True
                    break
            except OSError:
                time.sleep(0.1)
        assert ready and process.poll() is None, "Flask app did not become ready before timeout"

        create_status = http_request(
            f"{base_url}/tasks/new",
            {"title": "KAN14 route check", "description": "Route availability test", "completed": "false"},
        )
        database = isolated_project / "data.db"
        with sqlite3.connect(database) as connection:
            row = connection.execute("SELECT id FROM tasks ORDER BY id DESC LIMIT 1").fetchone()
        assert create_status in (200, 302) and row is not None, "Could not create an isolated task for route checks"
        task_id = row[0]
        statuses = [
            http_request(f"{base_url}/"),
            http_request(f"{base_url}/tasks"),
            http_request(f"{base_url}/tasks/new"),
            http_request(f"{base_url}/tasks/{task_id}/edit"),
            http_request(f"{base_url}/tasks/{task_id}/delete"),
        ]
        assert statuses == [200, 200, 200, 200, 302]
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
