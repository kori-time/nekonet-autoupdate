from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_prefix='NEKONET_',env_file='/etc/nekonet-autoupdate.env',extra='ignore')
    role:str='A'; coordinator_name:str='falfa.kori.cat'; coordinator_ip:str='10.10.0.8'; peer_name:str='laika.kori.cat'; peer_ip:str='10.10.0.7'; server_a_ip:str='10.10.0.8'; server_b_ip:str='10.10.0.7'
    api_bind:str='10.10.0.8'; api_port:int=8088; api_token:str=''; internal_token:str=''; discord_webhook:str=''
    ssh_user:str='nekonet'; ssh_port:int=2222; ssh_key:str='/var/lib/nekonet-autoupdate/.ssh/id_ed25519'
    update_spacing_seconds:int=300; reboot_spacing_seconds:int=600; server_return_timeout_seconds:int=600; secondary_delay_seconds:int=900; heartbeat_seconds:int=15; heartbeat_stale_seconds:int=60
    storage_order:str='mysql,postgresql,sqlite,json'; mysql_dsn:str=''; postgresql_dsn:str=''; sqlite_path:str='/var/lib/nekonet-autoupdate/state.db'; json_path:str='/var/lib/nekonet-autoupdate/status.json'; fleet_path:str='/etc/nekonet-autoupdate/fleet.json'; storage_retry_seconds:int=30
    max_avg_rtt_ms:float=250; max_packet_loss_percent:float=20; max_clock_skew_seconds:int=5
    cert_source_ip:str='10.10.0.2'; cert_name:str=''; cert_domains:str=''; cert_email:str=''; cert_webroot:str='/var/www/html'; tls_dir:str='/etc/nekonet-autoupdate/tls'; tls_enabled:bool=False
