import json
import logging

import requests

from homeassistant import exceptions

from functools import wraps

_LOGGER = logging.getLogger(__name__)

_LoginURL = "https://www.semsportal.com/api/v2/Common/CrossLogin"
_PowerStationURLPart = "/v2/PowerStation/GetMonitorDetailByPowerstationId"
_WallboxURL = "https://www.semsportal.com/api/v3/EvCharger/GetCurrentChargeinfo"
_SetChargeModeURL = "https://www.semsportal.com/api/v3/EvCharger/SetChargeMode"
_PowerControlURL = "https://www.semsportal.com/api/v3/EvCharger/Charging"

_RequestTimeout = 30  # seconds

_DefaultHeaders = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "token": '{"version":"","client":"ios","language":"en"}',
}


class SemsApi:
    """Interface to the SEMS API."""

    def __init__(self, hass, username, password):
        """Init dummy hub."""
        self._hass = hass
        self._username = username
        self._password = password
        self._token = None

    def test_authentication(self) -> bool:
        """Test if we can authenticate with the host."""
        try:
            self._token = self.getLoginToken(self._username, self._password)
            return self._token is not None
        except Exception as exception:
            _LOGGER.exception("SEMS Authentication exception " + exception)
            return False

    def getLoginToken(self, userName, password):
        """Get the login token for the SEMS API"""
        try:
            # Get our Authentication Token from SEMS Portal API
            _LOGGER.debug("SEMS - Getting API token")

            # Prepare Login Data to retrieve Authentication Token
            # Dict won't work here somehow, so this magic string creation must do.
            login_data = '{"account":"' + userName + '","pwd":"' + password + '" }'

            # Make POST request to retrieve Authentication Token from SEMS API
            login_response = requests.post(
                _LoginURL,
                headers=_DefaultHeaders,
                data=login_data,
                timeout=_RequestTimeout,
            )
            _LOGGER.debug("Login Response: %s", login_response)
            # _LOGGER.debug("Login Response text: %s", login_response.text)

            login_response.raise_for_status()

            # Process response as JSON
            jsonResponse = login_response.json()  # json.loads(login_response.text)
            _LOGGER.debug("Login JSON response %s", jsonResponse)
            # Get all the details from our response, needed to make the next POST request (the one that really fetches the data)
            # Also store the api url send with the authentication request for later use
            tokenDict = jsonResponse["data"]
            tokenDict["api"] = jsonResponse["api"]

            _LOGGER.debug("SEMS - API Token received: %s", tokenDict)
            return tokenDict
        except Exception as exception:
            _LOGGER.error("Unable to fetch login token from SEMS API. %s", exception)
            return None

    def getData(self, powerStationId, renewToken=False, maxTokenRetries=20):
        """Get the latest data from the SEMS API and updates the state."""
        try:
            # Get the status of our SEMS Power Station
            _LOGGER.debug("SEMS - Making EV Charger Status API Call")
            if maxTokenRetries <= 0:
                _LOGGER.info(
                    "SEMS - Maximum token fetch tries reached, aborting for now"
                )
                raise OutOfRetries
            if self._token is None or renewToken:
                _LOGGER.debug(
                    "API token not set (%s) or new token requested (%s), fetching",
                    self._token,
                    renewToken,
                )
                self._token = self.getLoginToken(self._username, self._password)

            # Prepare Power Station status Headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "token": json.dumps(self._token),
            }

            # powerStationURL = self._token["api"] + _PowerStationURLPart
            # _LOGGER.debug(
            #     "Querying SEMS API (%s) for power station id: %s",
            #     powerStationURL,
            #     powerStationId,
            # )

            # data = '{"powerStationId":"' + powerStationId + '"}'

            # response = requests.post(
            #     powerStationURL, headers=headers, data=data, timeout=_RequestTimeout
            # )
            _LOGGER.debug(
                "Querying SEMS API (%s) for EV Charger Serial No: %s",
                _WallboxURL,
                powerStationId
            )

            data = '{"sn":"' + powerStationId + '"}'

            response = requests.post(
                _WallboxURL, headers=headers, data=data, timeout=_RequestTimeout
            )

            jsonResponse = response.json()
            # try again and renew token is unsuccessful
            if jsonResponse["msg"] != "success" or jsonResponse["data"] is None:
                _LOGGER.debug(
                    "Query not successful (%s), retrying with new token, %s retries remaining",
                    jsonResponse["msg"],
                    maxTokenRetries,
                )
                return self.getData(
                    powerStationId, True, maxTokenRetries=maxTokenRetries - 1
                )

            return jsonResponse["data"]
        except Exception as exception:
            _LOGGER.error("Unable to fetch data from SEMS. %s", exception)

    def change_status(self, inverterSn, status, renewToken=False, maxTokenRetries=2):
        """Schedule the downtime of the station"""
        try:
            # Get the status of our SEMS Power Station
            _LOGGER.debug("SEMS - Making Wallbox Status API Call")
            if maxTokenRetries <= 0:
                _LOGGER.info(
                    "SEMS - Maximum token fetch tries reached, aborting for now"
                )
                raise OutOfRetries
            if self._token is None or renewToken:
                _LOGGER.debug(
                    "API token not set (%s) or new token requested (%s), fetching",
                    self._token,
                    renewToken,
                )
                self._token = self.getLoginToken(self._username, self._password)

            # Prepare Power Station status Headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "token": json.dumps(self._token),
            }

            powerControlURL = _PowerControlURL
            _LOGGER.debug(
                "Sending power control command (%s) for power station id: %s",
                powerControlURL,
                inverterSn,
            )

            data = {
                "sn": inverterSn,
                "status": str(status)
            }

            response = requests.post(
                powerControlURL, headers=headers, json=data, timeout=_RequestTimeout
            )
            if (response.status_code != 200):
                # try again and renew token is unsuccessful
                _LOGGER.warn(
                    "Power control command not successful, retrying with new token, %s retries remaining",
                    maxTokenRetries,
                )
                return

            return
        except Exception as exception:
            _LOGGER.error("Unable to execute Power control command. %s", exception)

    def set_charge_mode(self, wallboxSn, mode, chargePower=None, renewToken=False, maxTokenRetries=20):
        """Schedule the downtime of the station"""
        try:
            # Get the status of our SEMS Power Station
            _LOGGER.debug("SEMS - Making EV Charger SetChargeMode API Call")
            if maxTokenRetries <= 0:
                _LOGGER.info(
                    "SEMS - Maximum token fetch tries reached, aborting for now"
                )
                raise OutOfRetries
            if self._token is None or renewToken:
                _LOGGER.debug(
                    "API token not set (%s) or new token requested (%s), fetching",
                    self._token,
                    renewToken,
                )
                self._token = self.getLoginToken(self._username, self._password)

            # Prepare Power Station status Headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "token": json.dumps(self._token),
                # "token": '{"uid": "d828fb31-508a-4e84-bfcc-b7ba66164092", "timestamp": 1718757570161, "token": "6578cf439e60fc9d4ba9717cc916992e", "client": "ios", "version": "", "language": "en", "api": "https://eu.semsportal.com/api/"}'
            }

            setChargeModeURL = _SetChargeModeURL

            _LOGGER.debug(
                "Sending SetChargeMode command (%s) for wallbox SN: %s mode: %s chargepower: %s",
                setChargeModeURL,
                wallboxSn,
                mode,
                chargePower
            )

            if chargePower:
                data = {
                    "sn": wallboxSn,
                    "type": mode,
                    "charge_power": chargePower
                }
            else:
                data = {
                    "sn": wallboxSn,
                    "type": mode
                }

            # request = requests.Request("POST", setChargeModeURL, headers=headers, json=data)
            #
            # request = request.prepare()
            # output = f"{request.method} {request.path_url} HTTP/1.1\r\n"
            # output += '\r\n'.join(f'{k}: {v}' for k, v in request.headers.items())
            # output += "\r\n\r\n"
            # if request.body is not None:
            #     output += request.body.decode() if isinstance(request.body, bytes) else request.body
            # _LOGGER.debug(f"Request: {output}")

            response = requests.post(
                setChargeModeURL, headers=headers, json=data, timeout=_RequestTimeout
            )
            # _LOGGER.debug(f"Response: {response.json()}")

            if response.status_code != 200:
                # try again and renew token is unsuccessful
                _LOGGER.debug(
                    "SetChargeMode command not successful, retrying with new token, %s retries remaining",
                    maxTokenRetries,
                )
                return

            return
        except Exception as exception:
            _LOGGER.error("Unable to execute SetChargeMode command. %s", exception)


class OutOfRetries(exceptions.HomeAssistantError):
    """Error to indicate too many error attempts."""
