def test_import_main():
    from app.main import app
    assert app is not None
    assert app.title == "PAM Tool API"
