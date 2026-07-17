from nekonet_autoupdate.models.fleet import FleetServer

def test_canary_and_policy_defaults():
    server = FleetServer(id="x", name="x", ip="10.0.0.1", canary=True)
    assert server.canary is True
    assert server.update_policy.mode == "all"
