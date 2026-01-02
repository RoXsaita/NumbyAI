#!/usr/bin/env python3
"""Quick script to update user currency to PLN"""
import asyncio
from app.tools.fetch_preferences import fetch_preferences_handler
from app.tools.save_preferences import save_preferences_handler

async def main():
    user_id = '1adaf75e-2b54-4b31-9999-806182b0a124'
    
    # Fetch current settings
    print('Fetching current settings...')
    result = await fetch_preferences_handler(
        preference_type='settings',
        user_id=user_id
    )
    current_settings = result.get('structuredContent', {}).get('settings', {})
    print(f'Current currency: {current_settings.get("functional_currency", "Not set")}')
    
    # Save currency to PLN
    print('\nUpdating currency to PLN...')
    save_result = await save_preferences_handler(
        preferences=[{'functional_currency': 'PLN'}],
        preference_type='settings',
        user_id=user_id
    )
    
    response_text = save_result.get('content', [{}])[0].get('text', '')
    print(f'\n{response_text}')
    
    # Verify the change
    print('\nVerifying update...')
    verify_result = await fetch_preferences_handler(
        preference_type='settings',
        user_id=user_id
    )
    updated_settings = verify_result.get('structuredContent', {}).get('settings', {})
    print(f'Updated currency: {updated_settings.get("functional_currency", "Not set")}')

if __name__ == '__main__':
    asyncio.run(main())
