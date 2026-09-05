# Manual Testing Instructions

## Start the Servers

### Terminal 1: Backend
```bash
# Double-click start-backend.bat
# OR run manually:
cd C:\Users\Galactus\OneDrive\Desktop\commerce-integrated
.venv\Scripts\python.exe -m uvicorn ai_commerce_gateway.api.app:app --host 127.0.0.1 --port 8001 --reload
```

Expected output:
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Terminal 2: Frontend
```bash
# Double-click start-frontend.bat
# OR run manually:
cd C:\Users\Galactus\OneDrive\Desktop\commerce-integrated\frontend
npm run dev
```

Expected output:
```
▲ Next.js 16.3.4
- Local:        http://localhost:3000
Ready in 2.3s
```

---

## Test Phase B: Merchant AI Catalog & Images

**URL**: http://127.0.0.1:3000/merchant/ai-catalog

### Steps:
1. Enter text: `USB Cable, ₹10, 100 units`
2. Click **Generate** button
3. **Verify**: Draft Preview appears with:
   - Title: "USB Cable"
   - Price: ₹10.00
   - Quantity: 100
4. Click image upload input (or drag & drop)
5. Select 1-3 images (PNG/JPEG < 5MB each)
6. **Verify**: Image previews appear with remove buttons
7. **Test validation**: Select >3 files
   - **Expected**: Warning message "Only the first 3 images were selected."
8. **Test validation**: Select a file >5MB
   - **Expected**: Red alert "Each image must be 5MB or smaller."
9. Click **Create Draft** with valid images
10. **Verify**: Success message with product ID
11. Navigate to product editor
12. **Verify**: Uploaded images appear in editor
13. Check image URL returns 200 (open in new tab)

---

## Test Phase C: Buyer Flow

**URL**: http://127.0.0.1:3000/buyer

### Desktop Width:

1. **Verify**: Page loads, no errors in console (F12)
2. Wait 2-3 seconds for message box to enable
3. **Verify**: Input box at bottom is enabled (not greyed out)
4. Type: `Find me coffee maker`
5. Click Send or press Enter
6. **Verify**: Assistant response appears
7. **Verify**: Product card appears with:
   - Product image
   - Title
   - Price
   - Stock
   - "Buy" button
8. Click **Buy** button
9. **Verify**: Proposal card appears
10. Click **Approve**
11. **Verify**: Authorization success message
12. **Verify**: "Continue to Payment" button appears
13. Click **Continue to Payment**
14. **IMPORTANT**: Verify "Test Mode" badge is visible
15. Click **Pay Now** button
16. **Verify**: Payment status updates (SUCCEEDED)
17. **Verify**: Transaction timeline appears

### Test Billing & Orders Tab:

18. Click **Billing & Orders** tab (top right)
19. **Verify**: Order appears with CORRECT field names:
    - **Product ID**: Shows `prod_xxx` (camelCase `productId`, NOT `product_id`)
    - **Amount**: Shows ₹xxx (from `amount.amount_minor` and `amount.currency`, NOT `price_minor`)
    - **Badge**: Shows "SUCCEEDED" or current state (from `state`, NOT `status`)

### Mobile Width:
20. Resize browser to ~375px width
21. Repeat steps 1-19
22. **Verify**: All elements are readable and buttons are clickable

---

## Test Phase D: Merchant Exports

**URL**: http://127.0.0.1:3000/merchant/transactions

### Transaction Export:
1. **Verify**: Transaction list appears
2. Look for CSV download button (usually top right or bottom)
3. Click **Download CSV**
4. **Verify**: File downloads (check Downloads folder)
5. Open CSV file
6. **Verify**: Valid comma-separated data with headers
7. Click **Download JSON**
8. **Verify**: File downloads
9. Open JSON file
10. **Verify**: Valid JSON structure `[{...}, {...}]`

### Audit Export:
11. Navigate to http://127.0.0.1:3000/merchant/audit
12. Select a transaction from the list
13. **Verify**: Audit timeline appears on right panel
14. Click **Download CSV** for audit
15. **Verify**: Audit CSV downloads with timeline events
16. Click **Download JSON** for audit
17. **Verify**: Audit JSON downloads with valid structure

---

## Browser Console Checks

### For Each Page:
1. Open DevTools Console (F12)
2. Navigate to page
3. **Check for**:
   - ❌ Red errors
   - ❌ Unhandled promise rejections
   - ⚠️ Unexpected network 4xx/5xx errors
   - ✅ Some warnings are OK (e.g., React dev mode warnings)

### Pages to Check:
- http://127.0.0.1:3000/merchant/ai-catalog
- http://127.0.0.1:3000/merchant/products
- http://127.0.0.1:3000/merchant/transactions
- http://127.0.0.1:3000/merchant/audit
- http://127.0.0.1:3000/buyer (Chat tab)
- http://127.0.0.1:3000/buyer (Billing & Orders tab)

---

## Known Issues (Expected):

### ⚠️ Buyer Transactions Backend Error
When clicking "Billing & Orders" tab, you may see:
- Empty list OR
- Console error: `500 Internal Server Error`

**Cause**: Backend missing `transaction_query_service` attribute

**Impact**: May prevent Billing & Orders tab from showing transactions

**Workaround**: 
- If tab shows "No orders found" but you completed a purchase, this is the backend bug
- The frontend field mapping changes (productId, amount, state) are still correct
- You can verify field mapping by inspecting the frontend React components in DevTools

---

## Critical Verification Checklist

- [ ] AI extraction generates draft with new Fireworks model
- [ ] Image upload accepts 1-3 files
- [ ] Image preview shows selected files
- [ ] Warning appears when selecting >3 files
- [ ] Alert appears when selecting file >5MB
- [ ] Product creation with images succeeds
- [ ] Buyer message box enables after 2-3 seconds
- [ ] Buyer can search and see product results
- [ ] Buyer can create proposal and authorize
- [ ] Test Mode payment executes successfully
- [ ] Billing & Orders shows **productId** (not product_id)
- [ ] Billing & Orders shows **amount.amount_minor** (not price_minor)
- [ ] Billing & Orders shows **state** badge (not status)
- [ ] Transaction CSV/JSON downloads work
- [ ] Audit CSV/JSON downloads work
- [ ] No critical errors in browser console
- [ ] Mobile width renders correctly

---

## If Something Breaks

### Frontend won't start:
```bash
cd frontend
npm install
npm run dev
```

### Backend won't start:
```bash
# Check .env has correct model
# Should be: LLM_MODEL=fireworks_ai/accounts/fireworks/models/qwen3p7-plus

.venv\Scripts\python.exe -m uvicorn ai_commerce_gateway.api.app:app --host 127.0.0.1 --port 8001
```

### Message box stays disabled:
1. Open browser console (F12)
2. Look for errors:
   - "Failed to login buyer"
   - "Failed to login merchant"
3. Check backend logs for 500 errors
4. Verify `frontend/.env.local` has:
   ```
   BACKEND_ORIGIN=http://127.0.0.1:8001
   BUYER_SESSIONS_ISSUER_KEY=dev-issuer-key
   ```

### Images won't upload:
1. Check file size < 5MB
2. Check file type is PNG/JPEG/WebP/GIF
3. Check backend logs for errors
4. Verify product was created first (need product ID)

---

## Report Results

After testing, update **SIGNOFF_REPORT.md** with:
- ✅ PASS or ❌ FAIL for each phase
- Screenshot any errors
- Note any blockers

Then run:
```bash
cd frontend
npm run lint
```

Fix lint errors if time permits, or document as "deferred to post-functional pass" per handoff doc.
