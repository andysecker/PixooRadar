import sys
import types


if "config" not in sys.modules:
    config = types.ModuleType("config")
    config.API_RATE_LIMIT_COOLDOWN_SECONDS = 300
    config.FLIGHT_SEARCH_RADIUS_METERS = 50000
    config.LOGO_BG_COLOR = (186, 186, 186, 255)
    config.PIXOO_IP = "127.0.0.1"
    config.PIXOO_PORT = 80
    config.PIXOO_RECONNECT_SECONDS = 5
    config.FONT_NAME = "splitflap"
    config.FONT_PATH = "./fonts/splitflap.bdf"
    config.RUNWAY_LABEL_FONT_NAME = "splitflap"
    config.RUNWAY_LABEL_FONT_PATH = "./fonts/splitflap.bdf"
    config.ANIMATION_FRAME_SPEED = 300
    config.COLOR_BOX = "#454545"
    config.COLOR_TEXT = "#FFFF00"
    config.DATA_REFRESH_SECONDS = 60
    config.FLIGHT_SPEED_UNIT = "mph"
    config.LATITUDE = 0.0
    config.LONGITUDE = 0.0
    config.LOG_LEVEL = "INFO"
    config.LOG_VERBOSE_EVENTS = True
    config.LOGO_DIR = "airline_logos"
    config.IDLE_MODE = "weather"
    config.NO_FLIGHT_RETRY_SECONDS = 15
    config.NO_FLIGHT_MAX_RETRY_SECONDS = 120
    config.RUNWAY_HEADING_DEG = 110
    config.WEATHER_REFRESH_SECONDS = 900
    config.WEATHER_METAR_ICAO = ""
    config.WEATHER_VIEW_SECONDS = 10
    config.WEATHER_WIND_SPEED_UNIT = "mph"
    sys.modules["config"] = config
