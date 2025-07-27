#!/usr/bin/env python3
# examples/weather_calculations_server.py
"""
Weather Calculations MCP Server - Pure functions example implementation.

This demonstrates pure weather calculation functions using the chuk_mcp_function_server infrastructure.
All functions are stateless, deterministic, and have no side effects - they only perform calculations.
"""

import json
import logging
import math
from typing import Dict, Any, List, Optional

# Import from the local source directory
import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

try:
    from chuk_mcp_function_server import (
        BaseMCPServer, 
        ServerConfig,
        main
    )
except ImportError as e:
    print(f"❌ Failed to import chuk_mcp_function_server: {e}")
    print("💡 Available exports should include: BaseMCPServer, ServerConfig, main")
    sys.exit(1)

logger = logging.getLogger(__name__)

class WeatherCalculationsMCPServer(BaseMCPServer):
    """Weather calculations MCP server - pure functions only."""
    
    def __init__(self, config: ServerConfig):
        # Update server metadata
        config.server_name = "weather-calculations-mcp-server"
        config.server_description = "Pure weather calculation functions MCP server"
        
        super().__init__(config)
        
        logger.info("🌤️ Weather Calculations MCP Server initialized")
    
    def _register_tools(self):
        """Register pure weather calculation functions."""
        
        # Define weather calculation tools with their schemas
        weather_tools = [
            {
                "name": "celsius_to_fahrenheit",
                "handler": self._celsius_to_fahrenheit,
                "description": "Convert temperature from Celsius to Fahrenheit",
                "schema": {
                    "type": "object",
                    "properties": {
                        "celsius": {
                            "type": "number",
                            "description": "Temperature in Celsius"
                        }
                    },
                    "required": ["celsius"]
                }
            },
            {
                "name": "fahrenheit_to_celsius",
                "handler": self._fahrenheit_to_celsius,
                "description": "Convert temperature from Fahrenheit to Celsius",
                "schema": {
                    "type": "object",
                    "properties": {
                        "fahrenheit": {
                            "type": "number",
                            "description": "Temperature in Fahrenheit"
                        }
                    },
                    "required": ["fahrenheit"]
                }
            },
            {
                "name": "calculate_heat_index",
                "handler": self._calculate_heat_index,
                "description": "Calculate heat index from temperature and humidity",
                "schema": {
                    "type": "object",
                    "properties": {
                        "temperature_f": {
                            "type": "number",
                            "description": "Temperature in Fahrenheit"
                        },
                        "humidity": {
                            "type": "number",
                            "description": "Relative humidity percentage (0-100)"
                        }
                    },
                    "required": ["temperature_f", "humidity"]
                }
            },
            {
                "name": "calculate_wind_chill",
                "handler": self._calculate_wind_chill,
                "description": "Calculate wind chill temperature",
                "schema": {
                    "type": "object",
                    "properties": {
                        "temperature_f": {
                            "type": "number",
                            "description": "Temperature in Fahrenheit"
                        },
                        "wind_speed_mph": {
                            "type": "number",
                            "description": "Wind speed in miles per hour"
                        }
                    },
                    "required": ["temperature_f", "wind_speed_mph"]
                }
            },
            {
                "name": "calculate_dew_point",
                "handler": self._calculate_dew_point,
                "description": "Calculate dew point from temperature and humidity",
                "schema": {
                    "type": "object",
                    "properties": {
                        "temperature_c": {
                            "type": "number",
                            "description": "Temperature in Celsius"
                        },
                        "humidity": {
                            "type": "number",
                            "description": "Relative humidity percentage (0-100)"
                        }
                    },
                    "required": ["temperature_c", "humidity"]
                }
            },
            {
                "name": "pressure_altitude_to_sea_level",
                "handler": self._pressure_altitude_to_sea_level,
                "description": "Convert pressure reading to sea level equivalent",
                "schema": {
                    "type": "object",
                    "properties": {
                        "pressure_hpa": {
                            "type": "number",
                            "description": "Pressure in hectopascals (hPa)"
                        },
                        "altitude_m": {
                            "type": "number",
                            "description": "Altitude in meters above sea level"
                        },
                        "temperature_c": {
                            "type": "number",
                            "description": "Temperature in Celsius"
                        }
                    },
                    "required": ["pressure_hpa", "altitude_m", "temperature_c"]
                }
            },
            {
                "name": "calculate_feels_like",
                "handler": self._calculate_feels_like,
                "description": "Calculate apparent temperature (feels like) considering wind and humidity",
                "schema": {
                    "type": "object",
                    "properties": {
                        "temperature_c": {
                            "type": "number",
                            "description": "Temperature in Celsius"
                        },
                        "humidity": {
                            "type": "number",
                            "description": "Relative humidity percentage (0-100)"
                        },
                        "wind_speed_kmh": {
                            "type": "number",
                            "description": "Wind speed in km/h"
                        }
                    },
                    "required": ["temperature_c", "humidity", "wind_speed_kmh"]
                }
            },
            {
                "name": "sunrise_sunset_times",
                "handler": self._sunrise_sunset_times,
                "description": "Calculate sunrise and sunset times for given coordinates and date",
                "schema": {
                    "type": "object",
                    "properties": {
                        "latitude": {
                            "type": "number",
                            "description": "Latitude in decimal degrees"
                        },
                        "longitude": {
                            "type": "number",
                            "description": "Longitude in decimal degrees"
                        },
                        "day_of_year": {
                            "type": "integer",
                            "description": "Day of year (1-365)"
                        }
                    },
                    "required": ["latitude", "longitude", "day_of_year"]
                }
            },
            {
                "name": "uv_index_from_solar_elevation",
                "handler": self._uv_index_from_solar_elevation,
                "description": "Calculate UV index from solar elevation angle",
                "schema": {
                    "type": "object",
                    "properties": {
                        "solar_elevation_degrees": {
                            "type": "number",
                            "description": "Solar elevation angle in degrees (0-90)"
                        },
                        "ozone_thickness": {
                            "type": "number",
                            "description": "Ozone layer thickness in Dobson units (default: 300)",
                            "default": 300
                        },
                        "cloud_cover": {
                            "type": "number",
                            "description": "Cloud cover percentage (0-100, default: 0)",
                            "default": 0
                        }
                    },
                    "required": ["solar_elevation_degrees"]
                }
            },
            {
                "name": "saturation_vapor_pressure",
                "handler": self._saturation_vapor_pressure,
                "description": "Calculate saturation vapor pressure at given temperature",
                "schema": {
                    "type": "object",
                    "properties": {
                        "temperature_c": {
                            "type": "number",
                            "description": "Temperature in Celsius"
                        }
                    },
                    "required": ["temperature_c"]
                }
            }
        ]
        
        # Register each tool
        for tool_def in weather_tools:
            self.register_tool(
                name=tool_def["name"],
                handler=tool_def["handler"],
                schema=tool_def["schema"],
                description=tool_def["description"]
            )
        
        logger.info(f"🛠️ Registered {len(weather_tools)} weather calculation tools")
    
    # Pure Weather Calculation Functions
    
    async def _celsius_to_fahrenheit(self, celsius: float) -> str:
        """Convert temperature from Celsius to Fahrenheit."""
        fahrenheit = (celsius * 9/5) + 32
        
        return json.dumps({
            "input": {
                "celsius": celsius
            },
            "result": {
                "fahrenheit": round(fahrenheit, 2)
            },
            "formula": "°F = (°C × 9/5) + 32"
        }, indent=2)
    
    async def _fahrenheit_to_celsius(self, fahrenheit: float) -> str:
        """Convert temperature from Fahrenheit to Celsius."""
        celsius = (fahrenheit - 32) * 5/9
        
        return json.dumps({
            "input": {
                "fahrenheit": fahrenheit
            },
            "result": {
                "celsius": round(celsius, 2)
            },
            "formula": "°C = (°F - 32) × 5/9"
        }, indent=2)
    
    async def _calculate_heat_index(self, temperature_f: float, humidity: float) -> str:
        """Calculate heat index using the Rothfusz regression."""
        T = temperature_f
        R = humidity
        
        # Rothfusz regression formula
        if T < 80:
            heat_index = T
        else:
            HI = (-42.379 + 
                  2.04901523 * T + 
                  10.14333127 * R - 
                  0.22475541 * T * R - 
                  6.83783e-3 * T**2 - 
                  5.481717e-2 * R**2 + 
                  1.22874e-3 * T**2 * R + 
                  8.5282e-4 * T * R**2 - 
                  1.99e-6 * T**2 * R**2)
            
            # Adjustments for low humidity
            if R < 13 and 80 <= T <= 112:
                adjustment = ((13 - R) / 4) * math.sqrt((17 - abs(T - 95)) / 17)
                HI -= adjustment
            # Adjustments for high humidity
            elif R > 85 and 80 <= T <= 87:
                adjustment = ((R - 85) / 10) * ((87 - T) / 5)
                HI += adjustment
            
            heat_index = HI
        
        # Determine risk level
        if heat_index < 80:
            risk_level = "No risk"
        elif heat_index < 90:
            risk_level = "Caution"
        elif heat_index < 105:
            risk_level = "Extreme caution"
        elif heat_index < 130:
            risk_level = "Danger"
        else:
            risk_level = "Extreme danger"
        
        return json.dumps({
            "input": {
                "temperature_f": temperature_f,
                "humidity_percent": humidity
            },
            "result": {
                "heat_index_f": round(heat_index, 1),
                "risk_level": risk_level
            },
            "formula": "Rothfusz regression (NWS standard)"
        }, indent=2)
    
    async def _calculate_wind_chill(self, temperature_f: float, wind_speed_mph: float) -> str:
        """Calculate wind chill temperature."""
        T = temperature_f
        V = wind_speed_mph
        
        if T > 50 or V < 3:
            wind_chill = T  # Wind chill not applicable
            applicable = False
        else:
            # NWS Wind Chill formula
            wind_chill = (35.74 + 
                         0.6215 * T - 
                         35.75 * (V ** 0.16) + 
                         0.4275 * T * (V ** 0.16))
            applicable = True
        
        # Determine risk level
        if not applicable:
            risk_level = "Not applicable"
        elif wind_chill > 16:
            risk_level = "No risk"
        elif wind_chill > -15:
            risk_level = "Uncomfortable"
        elif wind_chill > -35:
            risk_level = "Risk of frostbite"
        else:
            risk_level = "Extreme risk"
        
        return json.dumps({
            "input": {
                "temperature_f": temperature_f,
                "wind_speed_mph": wind_speed_mph
            },
            "result": {
                "wind_chill_f": round(wind_chill, 1),
                "applicable": applicable,
                "risk_level": risk_level
            },
            "formula": "NWS Wind Chill formula",
            "note": "Only applicable when T ≤ 50°F and wind ≥ 3 mph"
        }, indent=2)
    
    async def _calculate_dew_point(self, temperature_c: float, humidity: float) -> str:
        """Calculate dew point temperature using Magnus formula."""
        T = temperature_c
        RH = humidity
        
        # Magnus formula constants
        a = 17.27
        b = 237.7
        
        # Calculate dew point
        alpha = ((a * T) / (b + T)) + math.log(RH / 100.0)
        dew_point = (b * alpha) / (a - alpha)
        
        # Calculate comfort level
        dew_point_f = (dew_point * 9/5) + 32
        if dew_point_f < 50:
            comfort = "Very dry"
        elif dew_point_f < 55:
            comfort = "Comfortable"
        elif dew_point_f < 60:
            comfort = "Slightly humid"
        elif dew_point_f < 65:
            comfort = "Humid"
        elif dew_point_f < 70:
            comfort = "Very humid"
        else:
            comfort = "Oppressive"
        
        return json.dumps({
            "input": {
                "temperature_c": temperature_c,
                "humidity_percent": humidity
            },
            "result": {
                "dew_point_c": round(dew_point, 2),
                "dew_point_f": round(dew_point_f, 2),
                "comfort_level": comfort
            },
            "formula": "Magnus formula approximation"
        }, indent=2)
    
    async def _pressure_altitude_to_sea_level(self, pressure_hpa: float, altitude_m: float, temperature_c: float) -> str:
        """Convert station pressure to sea level pressure."""
        P = pressure_hpa
        h = altitude_m
        T = temperature_c + 273.15  # Convert to Kelvin
        
        # Barometric formula
        g = 9.80665  # Standard gravity
        M = 0.0289644  # Molar mass of Earth's air
        R = 8.31432  # Universal gas constant
        
        sea_level_pressure = P * math.exp((g * M * h) / (R * T))
        
        return json.dumps({
            "input": {
                "station_pressure_hpa": pressure_hpa,
                "altitude_m": altitude_m,
                "temperature_c": temperature_c
            },
            "result": {
                "sea_level_pressure_hpa": round(sea_level_pressure, 2),
                "pressure_difference_hpa": round(sea_level_pressure - pressure_hpa, 2)
            },
            "formula": "Barometric formula"
        }, indent=2)
    
    async def _calculate_feels_like(self, temperature_c: float, humidity: float, wind_speed_kmh: float) -> str:
        """Calculate apparent temperature (feels like) considering multiple factors."""
        T = temperature_c
        
        # Convert to Fahrenheit for heat index calculation
        T_f = (T * 9/5) + 32
        
        # Choose appropriate formula based on conditions
        if T_f >= 80:
            # Use heat index for hot conditions
            heat_index_result = await self._calculate_heat_index(T_f, humidity)
            heat_index_data = json.loads(heat_index_result)
            feels_like_f = heat_index_data["result"]["heat_index_f"]
            method = "Heat Index"
        elif T_f <= 50 and wind_speed_kmh >= 4.8:  # 3 mph = 4.8 kmh
            # Use wind chill for cold windy conditions
            wind_mph = wind_speed_kmh * 0.621371
            wind_chill_result = await self._calculate_wind_chill(T_f, wind_mph)
            wind_chill_data = json.loads(wind_chill_result)
            feels_like_f = wind_chill_data["result"]["wind_chill_f"]
            method = "Wind Chill"
        else:
            # Use simple apparent temperature formula
            feels_like_f = T_f + (0.33 * (humidity / 100.0) * 6.105 * math.exp(17.27 * T / (237.7 + T))) - 0.7 * (wind_speed_kmh / 3.6) - 4.0
            method = "Apparent Temperature"
        
        feels_like_c = (feels_like_f - 32) * 5/9
        
        return json.dumps({
            "input": {
                "temperature_c": temperature_c,
                "humidity_percent": humidity,
                "wind_speed_kmh": wind_speed_kmh
            },
            "result": {
                "feels_like_c": round(feels_like_c, 1),
                "feels_like_f": round(feels_like_f, 1),
                "method_used": method
            },
            "note": "Automatically selects appropriate calculation method based on conditions"
        }, indent=2)
    
    async def _sunrise_sunset_times(self, latitude: float, longitude: float, day_of_year: int) -> str:
        """Calculate sunrise and sunset times using solar position algorithms."""
        lat = math.radians(latitude)
        
        # Solar declination
        P = math.asin(0.39795 * math.cos(0.98563 * (day_of_year - 173) * math.pi / 180))
        
        # Hour angle
        argument = -math.tan(lat) * math.tan(P)
        
        # Check for polar day/night
        if argument < -1:
            condition = "polar_day"
            sunrise = "No sunset (polar day)"
            sunset = "No sunset (polar day)"
        elif argument > 1:
            condition = "polar_night"
            sunrise = "No sunrise (polar night)"
            sunset = "No sunrise (polar night)"
        else:
            condition = "normal"
            hour_angle = 24 * math.acos(argument) / (2 * math.pi)
            
            # Calculate times (in decimal hours)
            sunrise_decimal = 12 - hour_angle - longitude / 15
            sunset_decimal = 12 + hour_angle - longitude / 15
            
            # Convert to hours and minutes
            def decimal_to_time(decimal_hour):
                hours = int(decimal_hour) % 24
                minutes = int((decimal_hour - int(decimal_hour)) * 60)
                return f"{hours:02d}:{minutes:02d}"
            
            sunrise = decimal_to_time(sunrise_decimal)
            sunset = decimal_to_time(sunset_decimal)
        
        return json.dumps({
            "input": {
                "latitude": latitude,
                "longitude": longitude,
                "day_of_year": day_of_year
            },
            "result": {
                "sunrise_utc": sunrise,
                "sunset_utc": sunset,
                "condition": condition
            },
            "note": "Times are in UTC. Add timezone offset for local time."
        }, indent=2)
    
    async def _uv_index_from_solar_elevation(self, solar_elevation_degrees: float, ozone_thickness: float = 300, cloud_cover: float = 0) -> str:
        """Calculate UV index from solar elevation angle."""
        elevation = solar_elevation_degrees
        
        if elevation <= 0:
            uv_index = 0
        else:
            # Basic UV index calculation
            # Maximum UV at solar elevation of 90 degrees
            base_uv = 11 * math.sin(math.radians(elevation))
            
            # Ozone attenuation (more ozone = less UV)
            ozone_factor = 300 / max(ozone_thickness, 100)
            
            # Cloud attenuation
            cloud_factor = 1 - (cloud_cover / 100) * 0.8
            
            uv_index = base_uv * ozone_factor * cloud_factor
            uv_index = max(0, min(11, uv_index))  # Clamp between 0 and 11
        
        # Determine risk level
        if uv_index < 3:
            risk_level = "Low"
            protection = "Minimal protection required"
        elif uv_index < 6:
            risk_level = "Moderate"
            protection = "Seek shade during midday hours"
        elif uv_index < 8:
            risk_level = "High"
            protection = "Protection essential"
        elif uv_index < 11:
            risk_level = "Very High"
            protection = "Extra protection required"
        else:
            risk_level = "Extreme"
            protection = "Avoid outdoor activities"
        
        return json.dumps({
            "input": {
                "solar_elevation_degrees": solar_elevation_degrees,
                "ozone_thickness_du": ozone_thickness,
                "cloud_cover_percent": cloud_cover
            },
            "result": {
                "uv_index": round(uv_index, 1),
                "risk_level": risk_level,
                "protection_advice": protection
            },
            "note": "Simplified calculation for demonstration"
        }, indent=2)
    
    async def _saturation_vapor_pressure(self, temperature_c: float) -> str:
        """Calculate saturation vapor pressure using Tetens formula."""
        T = temperature_c
        
        # Tetens formula
        if T >= 0:
            # Over water
            es = 6.1078 * math.exp((17.27 * T) / (T + 237.3))
            phase = "water"
        else:
            # Over ice
            es = 6.1078 * math.exp((21.875 * T) / (T + 265.5))
            phase = "ice"
        
        # Convert to other units
        es_pa = es * 100  # hectopascals to pascals
        es_mmhg = es * 0.750062  # hectopascals to mmHg
        
        return json.dumps({
            "input": {
                "temperature_c": temperature_c
            },
            "result": {
                "saturation_vapor_pressure_hpa": round(es, 3),
                "saturation_vapor_pressure_pa": round(es_pa, 1),
                "saturation_vapor_pressure_mmhg": round(es_mmhg, 3),
                "phase": phase
            },
            "formula": "Tetens formula",
            "note": "Calculation over water for T ≥ 0°C, over ice for T < 0°C"
        }, indent=2)

# Configuration class for weather calculations server
class WeatherCalculationsServerConfig(ServerConfig):
    """Weather calculations server specific configuration."""
    
    def __init__(self, **kwargs):
        # Set weather-specific defaults
        kwargs.setdefault('server_name', 'weather-calculations-mcp-server')
        kwargs.setdefault('server_description', 'Pure weather calculation functions MCP server')
        kwargs.setdefault('enable_tools', True)
        kwargs.setdefault('enable_prompts', False)
        kwargs.setdefault('enable_resources', True)
        super().__init__(**kwargs)

def main_weather_calculations():
    """Main entry point for the weather calculations server."""
    main(
        server_class=WeatherCalculationsMCPServer,
        config_class=WeatherCalculationsServerConfig,
        prog_name="weather-calculations-mcp-server"
    )

if __name__ == "__main__":
    main_weather_calculations()