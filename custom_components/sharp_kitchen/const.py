"""Constants for the Sharp Kitchen (na-kitchen) integration.

This integration talks to the same backend the "Sharp Kitchen" Android app
(com.sharpusa.iotdrawer) uses. All endpoint/field names here were captured
directly from that app's own traffic (via a Frida hook on OkHttp), not from
any public Sharp documentation -- Sharp has not published this API.
"""

DOMAIN = "sharp_kitchen"

# --- Sharp / na-kitchen backend ---
API_BASE = "https://device.na-api.aiot.sharp.co.jp"
INITIALIZE_PATH = "/na-kitchen/api/account/initialize"
PAIRING_PATH = "/na-kitchen/api/device/pairing"
DEVICE_SETTING_PATH = "/na-kitchen/api/control/device/setting"
DEVICE_CACHE_PATH = "/na-kitchen/api/control/device/cache"
DEVICE_CONTROL_PATH = "/na-kitchen/api/control/device"

# --- AWS Cognito (used by the app to sign in before calling na-kitchen) ---
COGNITO_REGION = "us-east-1"
COGNITO_ENDPOINT = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
COGNITO_USER_POOL_ID = "us-east-1_afz8acV06"
COGNITO_CLIENT_ID = "3atehc0f8fp6013fo1dd6etlcl"
# Confirmed correct: this exact Client_Id/Client_Secret pair was seen
# again in the real login's own network traffic (the "Authorization:
# Basic ..." header on the /oauth2/token call below decodes to
# "<CLIENT_ID>:<CLIENT_SECRET>"), so this is no longer just a guess
# carried over from an unrelated API call.
COGNITO_CLIENT_SECRET = "5nghindckplg2fir1d5ahtgq5dl14ubema9om4veiq5ht3vechc"

# --- Cognito Hosted-UI login (this is how the real app actually logs in) ---
#
# The app does NOT call Cognito's InitiateAuth/USER_PASSWORD_AUTH API
# directly for the initial email+password login (an earlier version of
# this integration assumed it did -- that was wrong, and every
# account/initialize call failed with "fail to get user subject" as a
# result). Instead, the real login happens through a hosted web login
# page shown in an in-app WebView, using the standard OAuth2
# "authorization code" flow. This was captured directly off the real app
# using Chrome's remote-debugging on that WebView (chrome://inspect),
# during a genuinely fresh login (app data/cache cleared first) -- not
# guessed. The resulting access token has "version": 2 and
# scope "aws.cognito.signin.user.admin openid profile", matching the
# real app's token exactly, and account/initialize accepts it.
#
# Flow:
#   1. GET  OAUTH_LOGIN_URL (below)               -> Set-Cookie: XSRF-TOKEN
#   2. POST username/password/_csrf back to it    -> redirects to
#      OAUTH_REDIRECT_URI with a one-time ?code=... appended
#   3. POST that code to OAUTH_TOKEN_URL (HTTP Basic auth using the
#      client id/secret above) -> real access_token/refresh_token/id_token
OAUTH_HOST = "https://oauth-sharphomeuser.sharpusa.com"
OAUTH_TOKEN_URL = f"{OAUTH_HOST}/oauth2/token"
OAUTH_REDIRECT_URI = "https://sharphomeuser.sharpusa.com:8287/S1.html"
OAUTH_SCOPE = "openid profile aws.cognito.signin.user.admin"
# The real app's WebView sends this exact User-Agent on the login calls
# above; kept identical in case Sharp's login page is picky about it
# (na-kitchen's own API is already known to reject requests that don't
# look like they came from the real app -- see USER_AGENT below).
OAUTH_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; Android SDK built for x86_64 "
    "Build/TE1A.220922.034; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Version/4.0 Chrome/101.0.4951.61 Mobile Safari/537.36"
)

# --- Client certificate (mutual TLS) for device.na-api.aiot.sharp.co.jp ---
#
# Sharp's device API edge requires every request -- including
# account/initialize itself -- to present this client certificate over
# TLS, on top of a valid Cognito access token. Without it, requests were
# seen to just get back a blank/non-error-looking rejection. This
# cert+key pair is baked into the Sharp Kitchen app itself (every install
# of the app ships the identical pair, from IoTDrawerPrdClient.pfx in its
# assets) -- it is not tied to any individual user account, so it's safe
# to bundle here the same way Sharp bundles it in their own app. It was
# extracted directly from the app's own (unlocked) Android KeyStore via a
# Frida hook, since the .pfx file itself is protected by a password
# containing raw NUL bytes that no available PKCS12 library could open
# directly.
CLIENT_CERT_B64 = (
    "MIIEITCCAwmgAwIBAgIJANpBRYtN3p6sMA0GCSqGSIb3DQEBCwUAMHoxCzAJBgNVBAYTAkpQMRIw"
    "EAYDVQQIDAlIaXJvc2hpbWExFDASBgNVBAoMC1NoYXJwIENvcnAuMSAwHgYDVQQDDBdkZXZpY2Uu"
    "YWlvdC5zaGFycC5jby5qcDEfMB0GCSqGSIb3DQEJARYQYWlvdEBzaGFycC5jby5qcDAgFw0xOTA2"
    "MDUwNzIzNDNaGA8yMDY5MDUyMzA3MjM0M1owgZExCzAJBgNVBAYTAkpQMRIwEAYDVQQIDAlIaXJv"
    "c2hpbWExGjAYBgNVBAcMEUhpZ2FzaGkgSGlyb3NoaW1hMRQwEgYDVQQKDAtTaGFycCBDb3JwLjEb"
    "MBkGA1UEAwwSSW9URHJhd2VyUHJkQ2xpZW50MR8wHQYJKoZIhvcNAQkBFhBhaW90QHNoYXJwLmNv"
    "LmpwMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuEcHvfJ9zHMrOb+vz5a8va7TGqrE"
    "TxfF4NejC8Gg3uNBbsxGyl6w+6G746qhsGQGuVZgWuMf7itxrEu2CN3+aZDZ7VNlJ4JdKdnUv9Z2"
    "erwf2FuWARsAEZauVe2cQDW2Z0R3qA8Hdt/bXLv5Uy4gv3+BcUH0sVr0UhLX3N7fgSYOUpYfys5A"
    "uoTaV5GLBrNt7XkpfmJHzUELJZvxvFVUktPPyDBF4FZ7iZ3REwF8PTuWUNeCeLEwg8aYxIZm6H+N"
    "tik0mTsUsmF9BGqhK5BSX70sFVjtI2M5KNVxaxGvMU8KW3uX80aNzmKMjK9HlRAJcOa985A7to7p"
    "4eHxPKu0TQIDAQABo4GPMIGMMAkGA1UdEwQCMAAwEQYJYIZIAYb4QgEBBAQDAgSwMCwGCWCGSAGG"
    "+EIBDQQfFh1PcGVuU1NMIEdlbmVyYXRlZCBDZXJ0aWZpY2F0ZTAdBgNVHQ4EFgQUKgW8JHCbjZi0"
    "axKgNHaEB3VxTPowHwYDVR0jBBgwFoAU4bKPCqkumoHUpIuhPPBM+2gFRQEwDQYJKoZIhvcNAQEL"
    "BQADggEBABLGpZEzIGBgyAbH/GiYxdqCjrsxO4CT8yOhWx7Zkjd6YcOl86COPfa6FirzoZWX+e8V"
    "AnnkhJysCoQeabEfBKLV3fAHJLqaD7Dd9RoPihoDkA2PtprRwrNJ2QiERb8Rlgs1kM0i03OxbBC4"
    "1sw82rx9dPHNJic2eQuy7LIdTbgcrLXRZi5Oy8z0S1wscApbhteel/T3gEFhTcbcy7n1nLyluEzt"
    "5g/M42nfCsrQWvLHTdQomR+O5c6xG1QO/IMTUFQlIzA4a/uFK6c4/jklz559tRyEnTDEAJTt02C1"
    "bvmCd3JOQaUAX+Ojp2nA+B625cvYwifs8OrVjnN0VHcLORI="
)
CLIENT_KEY_B64 = (
    "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC4Rwe98n3Mcys5v6/Plry9rtMa"
    "qsRPF8Xg16MLwaDe40FuzEbKXrD7obvjqqGwZAa5VmBa4x/uK3GsS7YI3f5pkNntU2Ungl0p2dS/"
    "1nZ6vB/YW5YBGwARlq5V7ZxANbZnRHeoDwd239tcu/lTLiC/f4FxQfSxWvRSEtfc3t+BJg5Slh/K"
    "zkC6hNpXkYsGs23teSl+YkfNQQslm/G8VVSS08/IMEXgVnuJndETAXw9O5ZQ14J4sTCDxpjEhmbo"
    "f422KTSZOxSyYX0EaqErkFJfvSwVWO0jYzko1XFrEa8xTwpbe5fzRo3OYoyMr0eVEAlw5r3zkDu2"
    "junh4fE8q7RNAgMBAAECggEBAJagMLrZeGxigyWcApgbLUGaoiG9DeNcmjkz6akVZ2potbZcMUz/"
    "Y4j7ZXotoiZtTHW4HeCMoC/swOjFphDPbEJbzVZJAXju/TnVPSplocim9xzBl/ZlXIQD95JzO3Hc"
    "tbDpbSkox8AqMMM3Pw/3t3rwPR0XfWxu3SAtGNcIMgb8cPLPsu1GgVEwXLCNAvjNXIeu4c1pLYMe"
    "MT8wIhFF9sCFNHCZqtJl3n7z/NwHqcgLOMATlvehNtmpIaDAN3BCko4wCOTjinqYjNAtVwXBBdz+"
    "y40Obnob1X/fW+Gkw/LijSPN2dNMTqnAAxxYs7hRehCv3TBsMxo3t/3fNseOmF0CgYEA7PRmPSMT"
    "60xyPg8BjwtWKl9d7SsPGbXZMgYnJ84JgnPGfVAxlWD3vBnf7LFTcvbinN31hYiRxwc1/RwC0m6C"
    "PQHuj/VsjsX08Qrm0/Fopv0cFfcaEcQyjZCpDYT3AV6/es3+mH1gq/oC8eEkwvr72s1gbs/YhlUK"
    "7fx4b9o7EqMCgYEAxxa9WeNxVpVI86WJe4bCChWDmqjERJWPXiVjx47+21PwrX44pBTpkypvo4gz"
    "LUQWTiEP11ncAiYLFHMrBYc9xhHb4duUOUnojBrhWiV8bzH1PDJufrxB4/Z3Wlw02aCeevVyuZ3P"
    "gfIfoUNi3z4roCQoftdJfZmMf7p2nFuOfE8CgYBPz3noObpp1JPeJzvFLHJXT0vZqFkrtb50RPJH"
    "S/SUBd7jMnGg+Mo4hxaPKKMM4+8sGu6pjXhcaydaG2cv7ZzcY5wwzN9Fr5Ny5NMeq/8tz674DwSu"
    "20CTwhfOv+xaf8lK2btZLVG0Wz9GrSiuq87MwcQrTsKFbHuD8Te3pO+ktQKBgCJ0bwS1dhHz+BIi"
    "ne6A3ef83S/Q8ValQ5CZi/EncDfpCQgdhhPvgpTzjSqSEblNxUZ0Nlegt5CvoM9DNzjXtPsocBNg"
    "ewCHJ/XHWSTOxABCdxyZ5cGNNyIKr5E1z/ex8nt5Kwewpg7pJkw0a1ITYl1upIt/Grrf7g7U6F4b"
    "AkfFAoGBAOO00gd7O1CaR4HB4LPDjmHykcK0np6OHMUDDhHTrXzF9h9NWo/422jnOutheLl0K8iq"
    "WG9kfTpfOSToeiOMw4B8m1MKFxa4kSTMd3sXett80FwWVctiPL3aPZCO/mWsfcMNNjx3MGQGhYN9"
    "7jWgNDVc5dal91IOi+Q16iepwAUm"
)

# --- Config entry keys ---
CONF_REFRESH_TOKEN = "refresh_token"
CONF_PHONE_ID = "phone_id"
# The Cognito user's actual internal "username" (often a random UUID, NOT
# the email) -- required to correctly recompute SECRET_HASH on every token
# refresh. Captured once at login time by decoding the access token JWT.
CONF_COGNITO_USERNAME = "cognito_username"

DEFAULT_SCAN_INTERVAL = 30  # seconds; how often we poll device/cache

# The real Sharp Kitchen app is built on OkHttp and Sharp's edge servers
# appear to reject requests that don't look like they came from it (seen
# during research: a MITM-decrypting proxy got blocked outright; a plain
# HA/aiohttp request without this header got back a blank/non-JSON
# response instead of an error). Sending the same User-Agent the real app
# uses avoids that.
USER_AGENT = "okhttp/4.9.2"

# --- Device state / attribute keys (as returned by device/cache) ---
ATTR_COOK = "cook"
ATTR_DOOR = "door"
ATTR_REST_TIME = "rest_time"
ATTR_POWER = "power"
ATTR_TEMPERATURE = "temperature"
ATTR_MENU = "menu"
ATTR_MANUAL_MODE = "manual_mode"
ATTR_TMP_MANUAL_MODE = "tmp_manual_mode"

# Observed values of "cook" -- there are almost certainly more than these
# three (this list was built from a short manual test session, not from
# Sharp documentation), but these are the ones actually seen on the wire.
COOK_STATE_NOT_CONNECTED = "not connected"
COOK_STATE_INIT_RUNNABLE = "init_runnable"
COOK_STATE_RUNNING = "running"

DOOR_STATE_CLOSE = "close"
DOOR_STATE_OPEN = "open"  # not directly observed, but the natural counterpart

# Boolean-ish settings toggled via {"command":"oven_setting","items":{...}}.
# Confirmed working for all three; others may exist per-model.
SETTING_KEYS = ["forget_take", "short_tone", "easy_wave"]

# --- Smart Cook presets ({"command":"cook_smart","auto_number":...,
# "auto_weight":...}) ---
#
# Sharp's real app has ~30 of these across 12 categories (Beverage/Hot
# Cereal, Defrost, Fish/Seafood, Frozen Entree, Ground Meat, Melt,
# Popcorn, Potatoes, Reheat, Rice, Soft/Warm, Vegetables). Only these 3
# have actually been captured and named so far (confirmed directly by
# the user, matching what they selected in the real app when this was
# captured) -- the rest of the catalog is unknown until more are
# captured the same way. min/max/unit below come from the real app's own
# screen for each of these three (e.g. "0.5 LB TO 2.0 LBS").
SMART_COOK_PRESETS = {
    "D7001": {
        "name": "Defrost Ground Meat",
        "unit": "lb",
        "min_weight": 0.5,
        "max_weight": 2.0,
        "default_weight": 1.2,
    },
    "M8007": {
        "name": "Beverage Reheat",
        "unit": "cup",
        "min_weight": 0.5,
        "max_weight": 2.0,
        "default_weight": 0.5,
    },
    "M8008": {
        "name": "Hot Water",
        "unit": "cup",
        "min_weight": 1.0,
        "max_weight": 6.0,
        "default_weight": 1.0,
    },
}
