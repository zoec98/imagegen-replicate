from imagegen import web


def test_web_main_starts_local_server(monkeypatch):
    calls = []

    class FakeApp:
        def run(self, **options):
            calls.append(options)

    monkeypatch.setattr(web, "create_app", lambda: FakeApp())

    assert web.main([]) == 0
    assert calls == [{"debug": False, "host": "127.0.0.1", "port": 5002}]


def test_web_main_rejects_dev_and_secure_network(monkeypatch, capsys):
    calls = []

    class FakeApp:
        def run(self, **options):
            calls.append(options)

    monkeypatch.setattr(web, "create_app", lambda: FakeApp())

    assert web.main(["--dev", "--secure-network"]) == 2
    assert calls == []
    assert "cannot combine --dev with --secure-network" in capsys.readouterr().err


def test_web_main_rejects_unknown_arguments(monkeypatch, capsys):
    def fail_create_app():
        raise AssertionError("app should not start")

    monkeypatch.setattr(web, "create_app", fail_create_app)

    assert web.main(["--unknown"]) == 2
    assert "unrecognized arguments: --unknown" in capsys.readouterr().err
