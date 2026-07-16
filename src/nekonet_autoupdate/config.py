from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NEKONET_", env_file="/etc/nekonet-autoupdate.env", extra="ignore")
    role: str = "A"
    coordinator_name: str = "falfa.kori.cat"
    coordinator_ip: str = "10.10.0.8"
    peer_name: str = "laika.kori.cat"
    peer_ip: str = "10.10.0.7"
    server_a_ip: str = "10.10.0.8"
    server_b_ip: str = "10.10.0.7"
    api_bind: str = "10.10.0.8"
    api_port: int = 8088
    api_token: str = ""
    discord_webhook: str = ""
    ssh_user: str = "root"
    ssh_port: int = 2222
    ssh_key: str = "/root/.ssh/nekonet-autoupdate"
    update_spacing_seconds: int = 300
    reboot_spacing_seconds: int = 600
    server_return_timeout_seconds: int = 600
    storage_order: str = "mysql,postgresql,sqlite,json"
    mysql_dsn: str = ""
    postgresql_dsn: str = ""
    sqlite_path: str = "/var/lib/nekonet-autoupdate/state.db"
    json_path: str = "/var/lib/nekonet-autoupdate/status.json"
    fleet_path: str = "/etc/nekonet-autoupdate/fleet.json"
    storage_retry_seconds: int = 30
    max_avg_rtt_ms: float = 250
    max_packet_loss_percent: float = 20
    max_clock_skew_seconds: int = 5
