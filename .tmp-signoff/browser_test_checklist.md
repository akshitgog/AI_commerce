# Frontend Sign-Off: Browser Testing Checklist

## Phase B: Merchant AI Catalog & Image Flow
**URL**: http://127.0.0.1:3000/merchant/ai-catalog

### Test Steps:
1. [ ] Enter product text: "USB Cable, ₹10, 100 units"
2. [ ] Click "Generate" button
3. [ ] Verify Draft Preview appears with:
   - Title: USB Cable
   - Price: ₹10.00
   - Quantity: 100
4. [ ] Click image upload input
5. [ ] Select 1-3 images (< 5MB each)
6. [ ] Verify image previews appear
7. [ ] Verify remove buttons work
8. [ ] Test validation: Select > 3 files → Warning message
9. [ ] Test validation: Select file > 5MB → Rejection alert
10. [ ] Click "Create Draft" with valid images
11. [ ] Verify success message appears
12. [ ] Navigate to product editor
13. [ ] Verify uploaded images appear
14. [ ] Check image URL returns 200

## Phase C: Buyer Flow
**URL**: http://127.0.0.1:3000/buyer

### Desktop Width:
1. [ ] No buyer-login error in console
2. [ ] Chat interface renders
3. [ ] Search for existing product
4. [ ] Verify assistant response
5. [ ] Verify product card shows:
   - Product title
   - Price
   - Stock
   - Image (if available)
6. [ ] Create purchase proposal
7. [ ] Verify proposal card appears
8. [ ] Complete authorization flow
9. [ ] Verify merchant decision UI
10. [ ] Execute test payment (VERIFY TEST MODE ONLY)
11. [ ] Verify payment status updates
12. [ ] Check audit timeline
13. [ ] Open "Billing & Orders" tab
14. [ ] Verify order shows correct fields:
    - Product ID (camelCase)
    - Amount (amount.amount_minor/currency)
    - State (not "status")

### Mobile Width:
1. [ ] Repeat steps 1-14 at mobile viewport

## Phase D: Merchant Exports
**URL**: http://127.0.0.1:3000/merchant/transactions

### Test Steps:
1. [ ] Verify transaction list loads
2. [ ] Click CSV download button
3. [ ] Verify CSV file downloads with valid data
4. [ ] Click JSON download button
5. [ ] Verify JSON file downloads with valid data
6. [ ] Open http://127.0.0.1:3000/merchant/audit
7. [ ] Select a transaction
8. [ ] Verify audit timeline appears
9. [ ] Download audit CSV
10. [ ] Download audit JSON
11. [ ] Inspect both files for valid content

## Console Checks
- [ ] No frontend errors in browser console (merchant pages)
- [ ] No frontend errors in browser console (buyer pages)
- [ ] No unhandled promise rejections
- [ ] No network failures (except expected 404s)

## Results:
```
Date tested: __________
Tested by: __________

PASS / FAIL: __________

Issues found:
- 
- 
```
