from pathlib import Path

def test_public_api_has_no_write_routes():
    text = Path("src/nekonet_autoupdate/api/app.py").read_text()
    assert '@app.post("/api/v1' not in text
    assert '@app.put("/api/v1' not in text
    assert '@app.delete("/api/v1' not in text
