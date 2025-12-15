# Common Issues & Solutions

## Login Doesn't Redirect to Products Page

**Problem**: After successful login, the page doesn't redirect automatically or stays on login page

**Solution**:
The app now uses AWS Amplify Hub to listen for authentication events. After the latest update:

1. **Save all files** and the dev server should auto-reload
2. **Try logging in again** - it should now redirect automatically
3. **Check browser console** for "Auth event: signedIn" message
4. If still not working, **hard refresh** (Cmd+Shift+R or Ctrl+Shift+R)

**What was fixed**: Added Hub listener to detect sign-in events and automatically update the user state, which triggers the redirect to `/products`.

---

## "Auth UserPool not configured" Error

**Problem**: Environment variables not loading

**Solution**:
1. Make sure `.env.local` exists in the `frontend/` directory (not root)
2. Restart the dev server completely:
   ```bash
   # Stop the server (Ctrl+C)
   cd frontend
   npm run dev
   ```
3. Clear browser cache and hard reload (Cmd+Shift+R or Ctrl+Shift+R)

**Verify environment variables are loading**:
Open browser console and type:
```javascript
console.log(import.meta.env)
```

You should see:
```javascript
{
  VITE_AWS_REGION: "ap-southeast-1",
  VITE_API_GATEWAY_ENDPOINT: "https://...",
  VITE_COGNITO_USER_POOL_ID: "ap-southeast-1_...",
  VITE_COGNITO_APP_CLIENT_ID: "..."
}
```

If values are `undefined`, the `.env.local` file is not in the right place or server needs restart.

## Other Common Issues

### Port Already in Use
Vite will automatically use the next available port. Check the terminal output for the actual URL.

### CORS Errors
- Check API Gateway has CORS enabled
- Verify the API endpoint URL is correct
- Check backend Lambda functions are deployed

### Authentication Errors
- Verify Cognito User Pool ID and Client ID are correct
- Check AWS region matches
- Clear cookies and try again

### Build Errors
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Need More Help?

1. Check browser console for detailed errors
2. Check terminal for backend errors
3. Verify all backend services are deployed
4. Review the QUICKSTART.md guide
