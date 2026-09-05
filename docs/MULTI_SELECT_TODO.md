# Multi-Select and Bulk Operations - Implementation Guide

## Current State
- No checkboxes in product or transaction tables
- No "Select All" functionality
- No bulk actions toolbar
- Only individual row actions via dropdown menus
- Export is all-or-nothing only

## Implementation Plan

### 1. Add Checkbox Component
File: `frontend/src/components/ui/checkbox.tsx`

Use shadcn/ui checkbox:
```bash
npx shadcn@latest add checkbox
```

### 2. Add Multi-Select State to Products Page
File: `frontend/src/app/merchant/products/page.tsx`

```typescript
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

const toggleSelect = (id: string) => {
  setSelectedIds(prev => {
    const next = new Set(prev);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    return next;
  });
};

const toggleSelectAll = () => {
  if (selectedIds.size === products.length) {
    setSelectedIds(new Set());
  } else {
    setSelectedIds(new Set(products.map(p => p.id)));
  }
};

const bulkDelete = async () => {
  if (confirm(`Delete ${selectedIds.size} products?`)) {
    for (const id of selectedIds) {
      await actions.deleteDraft(id);
    }
    setSelectedIds(new Set());
  }
};

const bulkExport = () => {
  const selected = products.filter(p => selectedIds.has(p.id));
  // Export only selected products
  exportProductsCSV(selected);
};
```

### 3. Add Table Checkboxes
```tsx
<TableHeader>
  <TableRow>
    <TableHead className="w-12">
      <Checkbox
        checked={selectedIds.size === products.length && products.length > 0}
        onCheckedChange={toggleSelectAll}
        aria-label="Select all"
      />
    </TableHead>
    <TableHead>Product</TableHead>
    {/* ... other headers */}
  </TableRow>
</TableHeader>

<TableBody>
  {products.map(product => (
    <TableRow key={product.id}>
      <TableCell>
        <Checkbox
          checked={selectedIds.has(product.id)}
          onCheckedChange={() => toggleSelect(product.id)}
          aria-label={`Select ${product.title}`}
        />
      </TableCell>
      {/* ... other cells */}
    </TableRow>
  ))}
</TableBody>
```

### 4. Add Bulk Actions Toolbar
```tsx
{selectedIds.size > 0 && (
  <div className="flex items-center gap-2 p-3 bg-muted rounded-md">
    <p className="text-sm font-medium">{selectedIds.size} selected</p>
    <div className="flex-1" />
    <Button
      variant="outline"
      size="sm"
      onClick={() => setSelectedIds(new Set())}
    >
      Clear
    </Button>
    <Button
      variant="outline"
      size="sm"
      onClick={bulkExport}
    >
      <Download className="h-4 w-4 mr-2" />
      Export Selected
    </Button>
    <Button
      variant="destructive"
      size="sm"
      onClick={bulkDelete}
    >
      <Trash className="h-4 w-4 mr-2" />
      Delete Selected
    </Button>
  </div>
)}
```

### 5. Add Similar UI to Transactions Page
File: `frontend/src/app/merchant/transactions/page.tsx`

Same pattern:
- Add `selectedIds` state
- Add checkboxes to table
- Add bulk export for selected transactions only
- Update CSV/JSON export functions to accept filtered list

### 6. Keyboard Shortcuts (Optional Enhancement)
- Shift+Click to select range
- Ctrl/Cmd+A to select all
- Delete key to bulk delete selected

## Benefits
- Users can select specific products/transactions to export
- Bulk delete multiple drafts at once
- Better UX for managing large catalogs
- Faster operations on multiple items

## Current Workaround
- Users must export all items, then filter manually
- Users must delete items one by one
- No way to perform operations on subset of items
