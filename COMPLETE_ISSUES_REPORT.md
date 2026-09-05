# Complete Issues Report - All Agent Findings

Generated: 2026-09-05

---

## ✅ FIXES APPLIED (4 issues)

### 1. AI Catalog Crash - TypeError
**Status**: ✅ **FIXED**

**Problem**: Page crashed when displaying draft preview after AI extraction

**Root Cause**: Backend returns `{price_amount_minor, currency}` but frontend expected `{price: {amount_minor, currency}}`

**Fix**: Added mapping in `handleGenerate()` to convert backend response format

**File**: `frontend/src/app/merchant/ai-catalog/page.tsx`

---

### 2. Buyer Input "No Typing Box"
**Status**: ✅ **FIXED**

**Problem**: Users thought there was no input box because it was disabled for 2-3 seconds during initialization

**Root Cause**: No visual feedback explaining why input was disabled

**Fix**: Added spinning Loader icon + "Initializing shopping assistant..." message + pulsing animation

**Files**:
- `frontend/src/components/buyer/buyer-composer.tsx`
- `frontend/src/components/buyer/buyer-chat-shell.tsx`

---

### 3. Export Downloads Empty Files
**Status**: ✅ **FIXED**

**Problem**: CSV/JSON downloads were empty

**Root Cause**: Download anchors weren't appended to DOM before `.click()` - modern browsers ignore detached elements

**Fix**: Added `document.body.appendChild(a)` before click, then `removeChild(a)` cleanup

**Files**:
- `frontend/src/app/merchant/transactions/page.tsx`
- `frontend/src/app/merchant/audit/page.tsx`

---

### 4. Billing Tab Resets Conversation
**Status**: ✅ **FIXED**

**Problem**: Clicking "Billing & Orders" tab destroyed entire conversation state

**Root Cause**: Conditional rendering (`tab === "chat" ? <A> : <B>`) **unmounts** inactive component

**Fix**: Changed to conditional **visibility** - both components stay mounted, only active one visible using Tailwind `hidden` class

**File**: `frontend/src/app/buyer/page.tsx`

---

## 🚫 MAJOR MISSING FEATURES

### 5. Image Upload Broken/Missing
**Status**: 🚫 **DESIGN ISSUE**

**Problem**: 
- New products: "Save the product first to add images" - NO image upload at all
- Existing products: Only accepts **URLs**, not file uploads

**Root Cause**: Product editor only has URL input field, not file picker

**What Users Expect**: File upload (like AI Catalog page has)

**What Exists**: URL input field only

**Impact**: Users cannot upload image files, must host images elsewhere and paste URLs

**Fix Needed**:
```tsx
// Replace URL input with file input
<Input type="file" accept="image/*" multiple />
// Convert File to blob and upload via existing API
```

**Files**:
- `frontend/src/components/merchant/product-editor.tsx` (lines 605-622)

---

### 6. Policy Save Button "Won't Click"
**Status**: ⚠️ **UX CONFUSION, NOT A BUG**

**Problem**: User says button won't click

**Reality**: Button IS working, but disabled when:
1. Nothing has changed (`!dirty`)
2. Currently saving (`saving`)
3. Invalid max amount entered (`maxAmountInvalid`)

**Feedback EXISTS**: Green "Policy saved" alert appears for 4 seconds after successful save

**Issue**: Disabled button doesn't explain WHY it's disabled

**Fix Needed**: Add tooltip or help text explaining why button is disabled:
```tsx
{!dirty && <p className="text-xs text-muted-foreground">No changes to save</p>}
{maxAmountInvalid && <p className="text-xs text-destructive">Enter a valid amount</p>}
```

**File**: `frontend/src/app/merchant/policy/page.tsx` (line 228)

---

### 7. Delete Functionality
**Status**: 🚫 **FRONTEND-ONLY, NO BACKEND API**

**Current State**:
- Delete button EXISTS but only for DRAFT products
- **Frontend-only** - just filters from local state, no backend API call
- Published products cannot be deleted at all

**Backend Missing**:
- ❌ No `DELETE /merchants/{id}/products/{productId}` endpoint
- ❌ No deletion logic in catalog service

**Fix Needed**:
1. Add backend `DELETE` endpoint
2. Wire frontend delete to actual API
3. Add delete capability for published products

**File**: `frontend/src/lib/services/store.ts` (lines 239-241)

---

### 8. No Multi-Select / Bulk Operations
**Status**: 🚫 **NOT IMPLEMENTED**

**Missing Everywhere**:
- ❌ No checkboxes in product tables
- ❌ No "Select All" functionality
- ❌ No bulk actions toolbar
- ❌ Cannot select specific items to export
- ❌ Cannot bulk delete
- ❌ All-or-nothing export only

**Fix Needed**:
1. Add checkbox UI component
2. Add multi-select state management
3. Add bulk actions toolbar:
   - "Delete selected" (with confirmation)
   - "Export selected"
4. Add backend bulk operation endpoints

**Files Affected**:
- `frontend/src/app/merchant/products/page.tsx`
- `frontend/src/app/merchant/transactions/page.tsx`

---

### 9. Transaction Visibility - No Real-Time Updates
**Status**: 🚫 **MISSING CRITICAL FEATURE**

**What EXISTS**:
- ✅ Transaction list with status badges
- ✅ Transaction detail page with full lifecycle
- ✅ Audit timeline per transaction
- ✅ Dashboard with metrics
- ✅ Review queue with countdown timers

**What's MISSING**:
- ❌ **No real-time updates** - must manually refresh page
- ❌ No polling mechanism
- ❌ No WebSocket or SSE for push updates
- ❌ No notification system for transaction changes
- ❌ No toast alerts when transactions change state
- ❌ No browser notifications
- ❌ No filtering/search (by state, date, amount)
- ❌ No "Active Transactions" monitoring view
- ❌ No badge counts on navigation items

**Fix Needed**:
1. Add polling (every 5-10 seconds) for active transactions
2. Or implement SSE endpoint for real-time updates
3. Add toast notification system
4. Add filtering UI (state, date range, search)
5. Add navigation badge counts ("Transactions (3)")

**Files**:
- `frontend/src/app/merchant/transactions/page.tsx`
- `frontend/src/app/merchant/page.tsx` (dashboard)

---

### 10. Review Page Purpose
**Status**: ✅ **FUNCTIONAL** (Not an issue)

**Purpose**: Merchant moderation queue for manual approval of purchase proposals

**What It Does**:
- Shows proposals requiring manual merchant decision (Gate 3 of multi-gate flow)
- Merchant can Approve or Deny with reason
- Part of: Buyer Auth → Auto Policy → **Manual Review** → Payment

**Status**: Fully functional and needed. Empty when no proposals need review.

---

### 11. LLM Visibility
**Status**: ⚠️ **PARTIAL** (Agent hit rate limit, manual investigation needed)

**Known from Logs**:
- ✅ LLM IS being called (qwen3p7-plus)
- ✅ AI responses are working

**Likely Missing**:
- ⚠️ No "AI is thinking..." indicator in buyer chat
- ⚠️ No loading state during AI catalog generation (might exist, needs verification)
- ⚠️ No visual feedback when AI is processing

**Manual Verification Needed**:
- Check if `isGenerating` state shows loading spinner in AI catalog
- Check if buyer chat shows typing indicator during AI response
- Check if error handling shows proper messages

---

## 📊 SUMMARY

### Fixed: 4
1. ✅ AI Catalog crash
2. ✅ Buyer input UX
3. ✅ Export downloads
4. ✅ Billing tab reset

### Broken: 7
1. 🚫 Image upload (URL-only, no file picker)
2. 🚫 Delete (frontend-only, no backend)
3. 🚫 Multi-select/bulk operations
4. 🚫 Real-time transaction updates
5. ⚠️ Policy save UX confusion
6. ⚠️ LLM visibility indicators
7. 🚫 Filtering/search capabilities

### Working: 1
- ✅ Review page (fully functional)

---

## 🎯 PRIORITY FIXES

### HIGH (Blocking Core Functionality):
1. **Image Upload** - Add file picker instead of URL-only
2. **Real-Time Updates** - Add polling or SSE for transaction monitoring
3. **Delete Backend** - Implement actual deletion API

### MEDIUM (UX Issues):
4. **Policy Save Feedback** - Add disabled state explanation
5. **LLM Indicators** - Add "thinking" states
6. **Multi-Select UI** - Add checkboxes and bulk actions

### LOW (Nice to Have):
7. **Filtering/Search** - Add transaction/product filters
8. **Navigation Badges** - Show counts on nav items

---

## 📁 FILES MODIFIED

### Already Fixed:
1. `frontend/src/app/merchant/ai-catalog/page.tsx`
2. `frontend/src/components/buyer/buyer-composer.tsx`
3. `frontend/src/components/buyer/buyer-chat-shell.tsx`
4. `frontend/src/app/merchant/transactions/page.tsx`
5. `frontend/src/app/merchant/audit/page.tsx`
6. `frontend/src/app/buyer/page.tsx`

### Need Modification:
7. `frontend/src/components/merchant/product-editor.tsx` (image upload)
8. `frontend/src/lib/services/store.ts` (delete API)
9. `frontend/src/app/merchant/policy/page.tsx` (disabled state feedback)
10. Backend: Need new DELETE endpoint and real-time update endpoints

---

**Next Steps**: Implement high-priority fixes (image upload, real-time updates, delete backend)
