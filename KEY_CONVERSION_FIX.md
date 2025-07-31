# Coinbase API Key Conversion Fix

## Problem
The bot was failing with a "MalformedFraming" error when trying to load the PEM file for the Coinbase API private key. This occurred because:

1. The Coinbase Advanced Python SDK expects private keys in PEM format
2. Coinbase Cloud provides private keys in base64-encoded format
3. The cryptography library was trying to parse the base64 key as if it were a PEM file

## Solution
Added a `convert_base64_to_pem()` function in `bot.py` that:

1. Removes the "ed25519:" prefix if present
2. Adds base64 padding if needed
3. Decodes the base64 string to raw bytes
4. Takes the first 32 bytes for Ed25519 private key
5. Converts to proper PEM format with headers

## Key Changes
- Modified `bot.py` to convert the base64-encoded private key to PEM format
- Added proper error handling for key conversion
- Removed unused `key_loader.py` file

## Testing
The fix ensures that:
- Base64 keys from Coinbase Cloud are properly converted to PEM format
- The Coinbase REST client can successfully load the private key
- Proper error messages are displayed if conversion fails

## Environment Variables
Make sure your Render environment has:
- `COINBASE_API_KEY_ID`: Your Coinbase API key
- `COINBASE_API_PRIVATE_KEY`: Your base64-encoded private key from Coinbase Cloud

The bot will automatically convert the private key to the correct format for the SDK.