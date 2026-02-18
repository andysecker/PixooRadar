"""
Configuration settings for Pixoo Flight Tracker.

Modify these values to customize the flight tracker for your setup.
"""

# =============================================================================
# Pixoo Device & Network
# =============================================================================
# Pixoo device IP on your local network.
PIXOO_IP = "192.168.x.x"   # Replace with your Pixoo's IP address
PIXOO_PORT = 80
# Reconnect delay (seconds) when Pixoo is unreachable/drops off network.
PIXOO_RECONNECT_SECONDS = 60
# Hard startup timeout (seconds) for first Pixoo connection attempt.
# App exits if initial connection cannot be established in this window.
PIXOO_STARTUP_CONNECT_TIMEOUT_SECONDS = 120

# =============================================================================
# Flight Tracking Location
# =============================================================================
# Observer position used to query nearby flights.
LATITUDE = 52.5200    # Replace with your latitude
LONGITUDE = 13.4050   # Replace with your longitude

# Flight search radius around your location (meters).
# Example: 50000 = 50 km, 25000 = 25 km
FLIGHT_SEARCH_RADIUS_METERS = 50000

# =============================================================================
# Polling & Animation
# =============================================================================
# Fixed polling interval for all flight API checks (seconds).
DATA_REFRESH_SECONDS = 60

# Flight animation frame delay (milliseconds).
# Higher value = slower animation.
ANIMATION_FRAME_SPEED = 300

# =============================================================================
# Weather Sources & Views
# =============================================================================
# Weather refresh interval while idle (seconds). 900 = 15 minutes.
WEATHER_REFRESH_SECONDS = 900

# Seconds to show each weather frame before advancing.
WEATHER_VIEW_SECONDS = 10

# ICAO station for METAR-derived weather values (temp/dewpoint/wind).
# Example: "LCPH", "EGLL", "KJFK". Leave blank to disable METAR fields.
WEATHER_METAR_ICAO = ""

# Primary runway heading (degrees) for the runway/wind weather view.
# Reciprocal runway heading is implied automatically.
RUNWAY_HEADING_DEG = 110

# =============================================================================
# Display Units
# =============================================================================
# Flight speed unit: "mph" or "kt" (displayed as Mph/Kt).
FLIGHT_SPEED_UNIT = "mph"

# Weather wind speed unit: "mph" or "kmh" (legacy "kph" accepted).
WEATHER_WIND_SPEED_UNIT = "mph"

# =============================================================================
# Fonts & Assets
# =============================================================================
FONT_NAME = "splitflap"
FONT_PATH = "./fonts/splitflap.bdf"
# Required font used for active runway label in weather runway view.
# Use a small/pixel font to keep runway numbers legible.
RUNWAY_LABEL_FONT_NAME = "splitflap"
RUNWAY_LABEL_FONT_PATH = "./fonts/splitflap.bdf"

# Local cache folder for downloaded airline logos.
LOGO_DIR = "airline_logos"

# =============================================================================
# Display Colors
# =============================================================================
COLOR_TEXT = "#FFFF00"           # Yellow - main text color
COLOR_BOX = "#454545"            # Dark gray - info boxes
# Background color for airline logos (RGBA)
# Match your display background for seamless logo cards
LOGO_BG_COLOR = (186, 186, 186, 255)

# =============================================================================
# Logging
# =============================================================================
# Verbose event logs for state transitions/poll cycles.
LOG_VERBOSE_EVENTS = True

# Standard logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL.
LOG_LEVEL = "INFO"
