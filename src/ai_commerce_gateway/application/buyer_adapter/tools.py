# Reusable JSON tool schemas for Reference Buyer Chat and MCP

SEARCH_CATALOG_SCHEMA = {
    "name": "search_catalog",
    "description": "Search for published products available from the merchant.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "merchant_id": {
                "type": "string",
                "description": "The ID of the merchant to search within.",
            },
            "query": {
                "type": "string",
                "description": "Optional search term for product title or description.",
            },
            "category": {"type": "string", "description": "Optional category filter."},
            "min_price_minor": {
                "type": "integer",
                "description": "Optional minimum price (in minor units).",
            },
            "max_price_minor": {
                "type": "integer",
                "description": "Optional maximum price (in minor units).",
            },
            "currency": {"type": "string", "description": "Optional currency filter (e.g. INR)."},
        },
        "required": ["merchant_id"],
    },
}

GET_PRODUCT_SCHEMA = {
    "name": "get_product",
    "description": "Retrieve full details of a specific published product.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "merchant_id": {
                "type": "string",
                "description": "The merchant ID from the search result (tenant scope).",
            },
            "product_id": {"type": "string", "description": "The ID of the product."},
        },
        "required": ["merchant_id", "product_id"],
    },
}

CREATE_PURCHASE_PROPOSAL_SCHEMA = {
    "name": "create_purchase_proposal",
    "description": (
        "Create an immutable purchase proposal for a product. "
        "AI is NOT responsible for deriving total price."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "merchant_id": {"type": "string", "description": "The ID of the merchant."},
            "product_id": {"type": "string", "description": "The ID of the product to purchase."},
            "quantity": {
                "type": "integer",
                "description": "The quantity to purchase.",
                "minimum": 1,
            },
        },
        "required": ["merchant_id", "product_id", "quantity"],
    },
}

REQUEST_AUTHORIZATION_SCHEMA = {
    "name": "request_authorization",
    "description": (
        "Request human buyer authorization for a proposal. "
        "This DOES NOT approve the proposal; it requests approval from the buyer."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "proposal_id": {"type": "string", "description": "The ID of the proposal to authorize."}
        },
        "required": ["proposal_id"],
    },
}

EXECUTE_TRANSACTION_SCHEMA = {
    "name": "execute_transaction",
    "description": (
        "Execute a transaction for an authorized proposal. "
        "This initiates checkout with the payment provider."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "proposal_id": {
                "type": "string",
                "description": "The ID of the ready proposal to transact.",
            }
        },
        "required": ["proposal_id"],
    },
}

GET_TRANSACTION_STATUS_SCHEMA = {
    "name": "get_transaction_status",
    "description": "Check the status of a transaction.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "transaction_id": {"type": "string", "description": "The ID of the transaction."}
        },
        "required": ["transaction_id"],
    },
}

GET_TRANSACTION_AUDIT_SCHEMA = {
    "name": "get_transaction_audit",
    "description": "Retrieve the audit log events for a transaction.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "transaction_id": {"type": "string", "description": "The ID of the transaction."},
            "cursor": {"type": "string", "description": "Optional cursor for pagination."},
        },
        "required": ["transaction_id"],
    },
}

ALL_TOOLS = [
    SEARCH_CATALOG_SCHEMA,
    GET_PRODUCT_SCHEMA,
    CREATE_PURCHASE_PROPOSAL_SCHEMA,
    REQUEST_AUTHORIZATION_SCHEMA,
    EXECUTE_TRANSACTION_SCHEMA,
    GET_TRANSACTION_STATUS_SCHEMA,
    GET_TRANSACTION_AUDIT_SCHEMA,
]
