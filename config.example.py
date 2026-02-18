"""
Configuration settings for Pixoo Flight Tracker.

Modify these values to customize the flight tracker for your setup.
"""

# =============================================================================
# Pixoo Device Settings
# =============================================================================
PIXOO_IP = "192.168.x.x"   # Replace with your Pixoo's IP address
PIXOO_PORT = 80
# Reconnect delay (seconds) when Pixoo is unreachable or drops from network.
PIXOO_RECONNECT_SECONDS = 60
# Hard startup timeout (seconds) for first Pixoo connection attempt.
# App exits if initial connection cannot be established in this window.
PIXOO_STARTUP_CONNECT_TIMEOUT_SECONDS = 120

# =============================================================================
# Location for Flight Tracking
# =============================================================================
# Set your location to track flights overhead
LATITUDE = 52.5200    # Replace with your latitude
LONGITUDE = 13.4050   # Replace with your longitude

# Flight search radius around your location (in meters)
# Example: 50000 = 50 km, 25000 = 25 km
FLIGHT_SEARCH_RADIUS_METERS = 50000

# =============================================================================
# Display Settings
# =============================================================================
FONT_NAME = "splitflap"
FONT_PATH = "./fonts/splitflap.bdf"
# Optional micro font for active runway label on weather runway diagram.
# Set equal to FONT_NAME/FONT_PATH to disable separate runway-label font.
RUNWAY_LABEL_FONT_NAME = "splitflap"
RUNWAY_LABEL_FONT_PATH = "./fonts/splitflap.bdf"
LOGO_DIR = "airline_logos"

# =============================================================================
# Timing
# =============================================================================
# How often to fetch new flight data (in seconds)
DATA_REFRESH_SECONDS = 60

# Weather refresh interval while in idle weather mode (seconds).
# 900s = 15 minutes.
WEATHER_REFRESH_SECONDS = 900

# ICAO station used for METAR-derived weather values (temperature, dewpoint, wind).
# Example: "LCPH" (Paphos), "EGLL" (Heathrow), "KJFK" (JFK). Leave blank to disable METAR.
WEATHER_METAR_ICAO = ""

# Seconds to show each weather frame before advancing (used for weather GIF views).
WEATHER_VIEW_SECONDS = 10

# Primary runway heading (degrees) for idle weather runway-wind view.
# The reciprocal direction is implied automatically.
RUNWAY_HEADING_DEG = 110

# Animation frame speed in milliseconds (how fast the airplane moves)
# Higher = slower airplane but longer per info page
# At 400ms × 9 frames per page = ~3.6s per page, ~10.8s full cycle
ANIMATION_FRAME_SPEED = 300

# Flight speed display unit: "mph" or "kt" (displayed as Mph/Kt)
FLIGHT_SPEED_UNIT = "mph"

# Weather wind speed display unit: "mph" or "kmh" (legacy "kph" also accepted).
WEATHER_WIND_SPEED_UNIT = "mph"

# Verbose runtime logging for state transitions, API polling, and retry behavior.
LOG_VERBOSE_EVENTS = True

# Standard Python logging level (e.g. DEBUG, INFO, WARNING, ERROR).
LOG_LEVEL = "INFO"

# =============================================================================
# Colors
# =============================================================================
COLOR_TEXT = "#FFFF00"           # Yellow - main text color
COLOR_BOX = "#454545"            # Dark gray - info boxes

# =============================================================================
# Logo Processing
# =============================================================================
# Background color for airline logos (RGBA)
# Match your display background for seamless logo cards
LOGO_BG_COLOR = (186, 186, 186, 255)
