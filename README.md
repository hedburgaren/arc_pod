# ARC POD - Print on Demand

ARC POD is an app for Odoo 18 Community Edition, in which it's possible to connect to different, popular 
print on demand-services.

## Features

### Sprint 1 & 2: Provider Configuration
- Configure API connections to POD providers
- Manage provider settings from Odoo
- Test API connections
- Error logging and monitoring

### Sprint 3: Product Mapping
- Map Odoo products to POD provider products
- Browse product catalogs from providers
- Sync product data from providers
- Manage product mappings per provider

## Supported Providers

### Printify
API for Printify: https://developers.printify.com/#overview

**Configuration Requirements:**
- API Key
- Shop ID

### Gelato
API för Gelato: https://dashboard.gelato.com/docs/

**Configuration Requirements:**
- API Key

### Printful
API for Printful: https://developers.printful.com/docs/

**Configuration Requirements:**
- API Key

## Usage

1. **Configure Provider Settings**
   - Go to Settings > ARC POD
   - Select a provider
   - Enter API credentials (API Key, Shop ID if required)
   - Test the connection

2. **Map Products**
   - Go to Products > Products
   - Open a product
   - Navigate to "POD Mappings" tab
   - Click "Add POD Mapping"
   - Select provider and fetch catalog
   - Select product from catalog
   - Create mapping

3. **Manage Mappings**
   - Go to Settings > Product Mappings
   - View all product mappings
   - Filter by provider
   - Refresh product data from provider

