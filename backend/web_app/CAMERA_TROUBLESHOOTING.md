# Camera Troubleshooting Guide

## Common Issues and Solutions

### "Camera requires HTTPS or localhost"

**Problem**: Browsers require a secure connection to access camera.

**Solutions**:

1. **For local testing** - Access via localhost:
   ```
   ✅ http://localhost:5000
   ✅ http://127.0.0.1:5000
   ❌ http://192.168.1.100:5000  (won't work)
   ```

2. **For LAN access** - Enable HTTPS:
   ```bash
   # Quick self-signed certificate (testing only)
   openssl req -x509 -newkey rsa:4096 -nodes \
     -keyout key.pem -out cert.pem -days 365 \
     -subj "/CN=barcode-scanner"
   
   # Then in app.py, change the last line to:
   # app.run(host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem'))
   
   # Access at: https://192.168.1.100:5000
   ```

3. **For production** - Use reverse proxy with valid SSL:
   - nginx with Let's Encrypt certificate
   - Apache with SSL certificate
   - Cloud hosting with SSL (Heroku, AWS, etc.)

### "Camera permission denied"

**Problem**: Browser blocked camera access or user clicked "Deny".

**Solutions**:

1. **Chrome/Edge**: Click the camera icon in address bar → Allow
2. **Firefox**: Click the lock icon → Permissions → Camera → Allow
3. **Safari**: Safari menu → Settings → Websites → Camera → Allow
4. **Try incognito/private mode** to reset permissions
5. **Check OS permissions**:
   - Mac: System Settings → Privacy & Security → Camera → Allow browser
   - Windows: Settings → Privacy → Camera → Allow apps to access

### "Camera API not available"

**Problem**: Browser doesn't support camera API or it's disabled.

**Solutions**:

1. **Update browser** to latest version
2. **Try different browser**:
   - ✅ Chrome 53+
   - ✅ Edge 79+
   - ✅ Safari 11+
   - ✅ Firefox 36+
   - ❌ Internet Explorer (not supported)
3. **Check browser flags** (Chrome/Edge):
   - Go to `chrome://flags`
   - Search for "insecure origins"
   - Enable if needed (only for testing)

### "No cameras found"

**Problem**: No physical camera or camera not detected.

**Solutions**:

1. **Check camera connection** (external webcam)
2. **Test camera in other apps** (Zoom, Teams, etc.)
3. **Restart browser**
4. **Check Device Manager** (Windows) or System Report (Mac)
5. **Use manual entry** if camera not available

### "Camera is being used by another application"

**Problem**: Another app has exclusive access to camera.

**Solutions**:

1. **Close other apps** that might use camera:
   - Zoom, Teams, Skype
   - OBS, Streamlabs
   - Photo/camera apps
2. **Restart browser**
3. **Restart computer** if issue persists

## Testing Camera Access

### Quick Test

Open browser console (F12) and run:

```javascript
navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    console.log("✅ Camera works!");
    stream.getTracks().forEach(t => t.stop());
  })
  .catch(err => console.error("❌ Error:", err.name, err.message));
```

### Check Available Cameras

```javascript
navigator.mediaDevices.enumerateDevices()
  .then(devices => {
    const cameras = devices.filter(d => d.kind === 'videoinput');
    console.log("Cameras:", cameras);
  });
```

## Browser Console Debugging

The web app now logs detailed info to browser console:

1. **Open Developer Tools**: Press F12
2. **Go to Console tab**
3. **Click "Start Camera Scanner"**
4. **Look for**:
   - "Starting scanner..."
   - "Protocol: http: or https:"
   - "MediaDevices available: true/false"
   - "Camera permission granted, got stream"
   - "Cameras found: [array]"
   - "Scanner started successfully"

## Development vs Production

### Development (Localhost)
- ✅ Works with HTTP
- ✅ No SSL certificate needed
- ✅ Easy to test

### Production (LAN/Internet)
- ⚠️ HTTPS required
- ⚠️ Valid or self-signed certificate needed
- ⚠️ Users must accept certificate warning (self-signed)

## Still Not Working?

1. **Check Flask server logs** for errors
2. **Try manual entry** - It always works
3. **Use USB barcode scanner** - No camera needed
4. **Report issue** with:
   - Browser name and version
   - Operating system
   - URL you're accessing (http vs https)
   - Error message from console
   - Screenshot if possible

## Alternative: USB Barcode Scanner

If camera doesn't work, use USB barcode scanner:
- Plug in scanner
- Click in "Job ID" input field
- Scan barcode
- Scanner types Job ID automatically
- Press Enter or click Submit

No camera, no camera permissions, always works!
