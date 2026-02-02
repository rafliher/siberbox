# UI Not Updating? Quick Fix Guide

## Changes Made

✅ Route changed from `/changepassword` to `/settings`  
✅ Navigation bar updated with new settings icon  
✅ Settings page completely redesigned with new design system  
✅ All components now use the modern dark red theme  

## If UI Doesn't Update

### Method 1: Hard Refresh Browser
**Chrome/Edge/Firefox (Windows/Linux):**
- Press `Ctrl + Shift + R` or `Ctrl + F5`

**Chrome/Edge/Firefox (Mac):**
- Press `Cmd + Shift + R`

**Safari (Mac):**
- Press `Cmd + Option + R`

### Method 2: Clear Browser Cache
1. Open DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Method 3: Restart Dev Server
```bash
# Stop the server (Ctrl+C)
cd machine-lab-platform-ui

# Clear any build cache
rm -rf node_modules/.cache
rm -rf dist

# Restart
npm run serve
```

### Method 4: Clear All Caches
```bash
cd machine-lab-platform-ui

# Clear everything
rm -rf node_modules/.cache
rm -rf dist
rm -rf .cache

# Reinstall (if needed)
npm install

# Start fresh
npm run serve
```

## What Changed in Settings Page

### Before
- Old gaming-style dark theme
- Indonesian labels ("Autentikasi Admin", "Password Saat Ini")
- Gradient backgrounds
- Animated effects

### After
- Modern enterprise design
- Clean card-based layout
- English labels
- Professional icons
- Form validation
- Copy-to-clipboard functionality
- Success/error messages
- Responsive design

## New Features in Settings

1. **Admin API Key Section**
   - Display current JWT token
   - Copy to clipboard button
   - Rotate key with confirmation
   - Warning about invalidating current token

2. **Change Password Section**
   - Current password field
   - New password field (min 8 chars)
   - Confirm password field
   - Client-side validation
   - Clear error messages

3. **Visual Feedback**
   - Success messages
   - Error boxes
   - Info boxes with icons
   - Loading states on buttons

## Testing the New Route

1. Start the dev server: `npm run serve`
2. Login to the application
3. Click "Settings" in the navigation (was "Authentication")
4. You should see the new modern Settings page
5. Test API key copy button
6. Test password change form

## Troubleshooting

### Still Seeing Old Design?
1. Check browser console for errors (F12)
2. Verify `src/assets/main.css` exists
3. Check `src/App.vue` has `@import './assets/main.css';`
4. Clear service worker cache (if any)
5. Try incognito/private window

### Route Not Working?
1. Check router console for 404 errors
2. Verify `src/router/index.js` has `/settings` route
3. Check NavigationBar links to `/settings`
4. Restart dev server

### Styles Not Applied?
1. Check browser DevTools > Network tab
2. Verify `main.css` loaded successfully (200 status)
3. Check for CSS syntax errors in console
4. Try disabling browser extensions

## Quick Verification

Open browser DevTools (F12) and run:
```javascript
// Check if main.css variables are loaded
console.log(getComputedStyle(document.documentElement).getPropertyValue('--color-primary'));
// Should output: #dc2626
```

If you see `#dc2626`, the new design system is loaded! 🎉

---

**Still having issues?** Clear everything and start fresh:
```bash
# Kill all node processes
pkill -9 node

# Fresh start
cd machine-lab-platform-ui
rm -rf node_modules
npm install
npm run serve
```

Then hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R).
