# Release Notes - v1.0.2

## 🎉 What's New

### Real-Time Credit Balance Display
- **Live Credit Metrics**: The main dashboard now displays real-time add-on credit balance information directly from the Windsurf API
  - **Add-on Credits Remaining**: Shows available credits with total pool size
  - **Add-on Credits Used**: Displays consumed credits with usage percentage
  - **Billing Cycle Information**: Shows current billing period dates

### API Integration
- Integrated new Windsurf `GetTeamCreditBalance` API endpoint
- Added `get_team_credit_balance()` function to fetch live credit data
- Proper error handling with fallback to analytics dashboard link

## 🔧 Improvements

- **Cleaner UI**: Simplified main page layout with 2-column metric display
- **Better Error Messages**: More informative error handling for API failures
- **Debug Mode**: Added collapsible debug view to inspect raw API responses

## 🐛 Bug Fixes

- Fixed type conversion issues when parsing API responses (string to integer conversion)
- Fixed exception chaining for proper error traceability
- Removed whitespace formatting issues

## 📝 Notes

- The credit balance updates each time you refresh the page
- Requires Windsurf API service key with "Billing Read" permissions
- Previous workaround of linking to web dashboard is now replaced with live data

---

**Installation**: 
```bash
pip install windsurf-throttle==1.0.2
# or
uvx windsurf-throttle@1.0.2
```

**Full Changelog**: https://github.com/rappdw/windsurf-throttle/compare/v1.0.1...v1.0.2
