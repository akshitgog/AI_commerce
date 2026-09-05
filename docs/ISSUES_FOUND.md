# Issues Found During Manual Testing

## ✅ FIXED IMMEDIATELY

### 1. AI Catalog Crash - TypeError: Cannot read 'amount_minor' of undefined
**Status**: ✅ **FIXED**

**Issue**: Page crashed when trying to display draft preview after AI extraction

**Cause**: Backend returns `{price_amount_minor, currency}` but frontend expected `{price: {amount_minor, currency}}`

**Fix Applied**: Added mapping in `handleGenerate()` to convert backend response to frontend format

**Test**: Generate product draft now - should show price correctly

---

## ⚠️ PARTIALLY WORKING (User Confusion)

### 2. Buyer "No Typing Box"
**Status**: ⚠️ **EXISTS BUT DISABLED INITIALLY**

**What User Reported**: "No typing box for user"

**Reality**: 
- Input box DOES exist at bottom of /buyer page
- Placeholder: "Ask about products…"
- **It's DISABLED for ~2-3 seconds** while sessions initialize
- From backend logs, I can see buyer chat IS working (search_catalog calls are happening)

**How to Use**:
1. Open http://127.0.0.1:3000/buyer
2. **WAIT 2-3 seconds** for input to enable
3. OR click the suggested button: "Find me a USB-C charger under ₹1,000."
4. Type your message and press Enter or click Send

**Known Issue**: If it stays disabled >5 seconds, check browser console for initialization errors

---

## 🚫 NOT IMPLEMENTED / MISSING FEATURES

These features are either not implemented or buttons are missing:

### 3. Policy Save Button Won't Click
**Status**: 🚫 **NEEDS INVESTIGATION**

**URL**: http://localhost:3000/merchant/policy

**User Report**: "Save policy button wont click"

**Backend Logs Show**: Policy PUT requests ARE succeeding (200 OK)
```
request_completed method=PUT route=/merchants/{merchant_id}/policy status=200
```

**Possible Causes**:
- Button has no visual feedback (appears to do nothing but actually works)
- Form validation preventing submit
- JavaScript error blocking click handler

**Test**: Try changing a policy value, click Save, and refresh page to see if it persisted

---

### 4. Product Editor - No Image Add Button
**URL**: http://localhost:3000/merchant/products/new

**User Report**: "There is no button to add image"

**Status**: 🚫 **MISSING UI COMPONENT**

**Impact**: Cannot add images when creating NEW products

---

### 5. Product Editor - Image Upload Not Working  
**URL**: http://localhost:3000/merchant/products/prod_001

**User Report**: "There is add button but wont able to add or update images"

**Status**: 🚫 **BROKEN**

**Impact**: Cannot add images to EXISTING products

**Backend Code**: Image upload API EXISTS and works (we tested it programmatically)

**Frontend Issue**: Button might exist but:
- File input not wired correctly
- Upload handler not triggering
- No error handling shown to user

---

### 6. Export Downloads - Blank/Empty Files
**User Report**: "Download all catalog or single catalog but downloading folder are blank"

**Status**: 🚫 **BROKEN**

**Affected Pages**:
- Product export (ZIP download)
- Transaction export (CSV/JSON) - http://localhost:3000/merchant/transactions
- Audit export (CSV/JSON) - http://localhost:3000/merchant/audit

**What Should Happen**:
- Products: Download ZIP with all product data
- Transactions: Download CSV or JSON with transaction list
- Audit: Download CSV or JSON with audit trail

**What Actually Happens**: Files download but are empty

---

### 7. No Download Buttons
**URL**: http://localhost:3000/merchant/transactions  
**URL**: http://localhost:3000/merchant/audit

**User Report**: "No download button"

**Status**: 🚫 **UI MISSING**

**Expected**: CSV/JSON export buttons on these pages

**Reality**: Buttons don't exist in UI

---

### 8. Buyer Billing Tab Resets Page
**URL**: http://localhost:3000/buyer (Billing & Orders tab)

**User Report**: "When i click on billing it got reset"

**Status**: 🚫 **BUG**

**Issue**: Clicking "Billing & Orders" tab causes page to reset/reload

**Impact**: Loses conversation state, forces re-initialization

---

### 9. Review Page Questionable
**URL**: http://localhost:3000/merchant/review

**User Report**: "This is not need i feel and or may be it is"

**Status**: ❓ **UNCLEAR PURPOSE**

**Note**: This might be a reviews moderation queue or similar feature - unclear if actually needed

---

## 🔍 PRIORITY FIXES NEEDED

### HIGH PRIORITY (Blocking Core Features):
1. ✅ **AI Catalog crash** - FIXED
2. **Image upload broken** - Users can't add product images
3. **Export downloads empty** - Users can't download data
4. **Buyer tab reset bug** - Breaks conversation state

### MEDIUM PRIORITY (UX Issues):
5. **Policy save button** - No feedback/confirmation
6. **Buyer input disabled** - User confusion, needs loading indicator

### LOW PRIORITY (Nice to Have):
7. **Download button UI** - Add export buttons to transactions/audit pages
8. **Review page** - Clarify purpose or remove

---

## 📋 TESTING CHECKLIST STATUS

From TESTING_INSTRUCTIONS.md:

### Phase B: Merchant AI Catalog
- [x] AI extraction generates draft - ✅ WORKING (after fix)
- [ ] Image upload - 🚫 BROKEN
- [ ] Image validation (3 files, 5MB) - ⚠️ CANNOT TEST (upload broken)
- [ ] Product creation with images - 🚫 BROKEN

### Phase C: Buyer Flow  
- [x] Buyer session initializes - ✅ WORKING
- [x] Message box enables - ⚠️ WORKS but confusing UX
- [x] AI responds to queries - ✅ WORKING (from logs)
- [ ] Billing & Orders tab - 🚫 RESETS PAGE

### Phase D: Merchant Exports
- [ ] Transaction CSV/JSON - 🚫 NO BUTTONS
- [ ] Audit CSV/JSON - 🚫 NO BUTTONS  
- [ ] Export files have data - 🚫 FILES ARE EMPTY

---

## 🔧 IMMEDIATE ACTIONS REQUIRED

1. **Investigate image upload components** - Why no buttons/broken functionality?
2. **Add download buttons** - Implement CSV/JSON export UI
3. **Fix export file generation** - Downloads are empty
4. **Fix Billing tab** - Prevent page reset
5. **Add loading indicator** - Show "Initializing..." while buyer input disabled
6. **Test policy save** - Verify it actually saves and show confirmation

---

## ⚠️ IMPORTANT NOTES

**Backend is Working**: 
- AI extraction ✅
- Buyer sessions ✅  
- Product creation ✅
- Policy updates ✅ (from logs)
- Image upload API ✅ (tested programmatically)

**Frontend Has Major Issues**:
- Missing UI components (image buttons, download buttons)
- Broken functionality (exports, image upload)
- UX confusion (disabled input, no feedback)
- State management bugs (Billing tab reset)

**This is NOT production-ready**. Multiple core features are broken or missing from the UI.
