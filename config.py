import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Get a required env var as a string, or raise a clear error if missing
def require_env(key: str) -> str:
    val = os.getenv(key)
    if val is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val

# Get a required env var as an int, or raise a clear error if missing/invalid
def require_env_int(key: str) -> int:
    val = require_env(key)
    try:
        return int(val)
    except ValueError:
        raise RuntimeError(f"Environment variable {key} must be an integer, got: {val!r}")

@dataclass
class Config:
    discord_token: str
    database_url: str
    guild_id: int
    mr_ice_role: set[int]
    wordle_app_id: int
    wordle_channel: int
    purchase_log_channel: int
    daily_payout_log_channel: int
    pack_opening_channel: int
    f1_notifications_channel: int
    game_roles: dict[str, int]

def load_config() -> Config:
    load_dotenv()

    return Config(
        discord_token=require_env("DISCORD_TOKEN"),
        database_url=require_env("DATABASE_URL"),
        guild_id=require_env_int("GUILD_ID"),
        mr_ice_role={require_env_int("MR_ICE_ROLE")},
        wordle_app_id=require_env_int("WORDLE_APP_ID"),
        wordle_channel=require_env_int("WORDLE_CHANNEL"),
        purchase_log_channel=require_env_int("PURCHASE_LOG_CHANNEL"),
        daily_payout_log_channel=require_env_int("DAILYPAYOUT_LOG_CHANNEL"),
        pack_opening_channel=require_env_int("PACK_OPENING_CHANNEL"),
        f1_notifications_channel=require_env_int("F1_NOTIFICATIONS_CHANNEL"),
        game_roles={
            "rocket league": require_env_int("RL_ROLE"),
            "rematch": require_env_int("REMATCH_ROLE"),
            "mtg": require_env_int("MTG_ROLE"),
        },
    )
    