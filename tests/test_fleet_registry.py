from nekonet_autoupdate.coordinator.fleet_registry import FleetRegistry
from nekonet_autoupdate.models.fleet import FleetServer

def test_add_change_remove(tmp_path):
    registry = FleetRegistry(str(tmp_path / "fleet.json"))
    server = FleetServer(id="x", name="x.example", ip="10.10.0.99")
    registry.upsert(server)
    assert registry.get("x").name == "x.example"

    changed = server.model_copy(update={"name":"changed.example"})
    registry.upsert(changed)
    assert registry.get("x").name == "changed.example"

    assert registry.remove("x") is True
    assert registry.get("x") is None
