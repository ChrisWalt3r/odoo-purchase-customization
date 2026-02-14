# Odoo 18 Purchase Customization – Multi-Vendor RFQ & Purchase Request

Custom Odoo 18 modules that extend the default Purchases application with multi-vendor RFQ management, bid comparison, and employee purchase request workflows.

## Overview

The standard Odoo Purchases module allows sending an RFQ to only one vendor at a time. These custom modules add the ability to assign **multiple vendors** to a single RFQ, receive and compare competitive bids, and award the winning bidder — all while integrating with an employee-driven purchase request workflow.

## Modules

### 1. Purchase Multi-Vendor RFQ (`purchase_rfq_multi_vendor`)

Extends the core `purchase` module to support assigning multiple vendors to a single Request for Quotation.

**Key Features:**
- **One-to-Many RFQ ↔ Vendors**: Assign multiple vendors to a single RFQ via a new "RFQ Vendors" tab on the Purchase Order form
- **Bulk RFQ Dispatch**: "Send RFQ to All Vendors" button sends the quotation request to every assigned vendor simultaneously
- **Bid Management**: Record bids from each vendor with detailed line-item pricing (One-to-Many relationship between RFQ and Bids)
- **Bid Comparison**: Compare all received bids side by side to evaluate pricing
- **Winner Selection Wizard**: Award the best bid through a guided wizard that automatically:
  - Creates a new Purchase Order with the winning vendor's pricing
  - Marks the winning bid as "Awarded"
  - Rejects all other competing bids
- **Smart Buttons**: Quick access to RFQ vendor count and received bids from the RFQ form

**Models:**
| Model | Description |
|-------|-------------|
| `purchase.rfq.vendor` | Links vendors to RFQs with status tracking (Draft → Sent → Bid Received → Awarded/Rejected) |
| `purchase.rfq.bid` | Stores vendor bids with line items, amounts, and validity dates |
| `purchase.rfq.bid.line` | Individual line items within a bid, linked to original RFQ lines |
| `select.winner.wizard` | Transient model for the bid award workflow |

### 2. Purchase Request (`purchase_request`)

Implements an employee purchase request workflow that feeds into the multi-vendor RFQ process.

**Key Features:**
- **Purchase Request Form**: Employees submit purchase requests with product lines, quantities, estimated prices, and justification
- **Approval Workflow**: State machine with transitions: Draft → Submitted → Approved → RFQ Created
- **Auto-RFQ Generation**: Approved requests automatically generate an RFQ with all requested product lines
- **Department Integration**: Requests are linked to the employee's department and manager for approval routing
- **Activity Notifications**: Automatic notifications to department managers when requests are submitted
- **Priority Levels**: Normal, Urgent, and Very Urgent priority classification
- **Full Traceability**: Each generated RFQ links back to its originating purchase request

**Models:**
| Model | Description |
|-------|-------------|
| `purchase.request` | Main request model with state machine, employee/department links, and RFQ generation |
| `purchase.request.line` | Product line items with quantities, UoM, estimated pricing |

## Module Structure

```
purchase_rfq_multi_vendor/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── purchase_order.py      # Extends purchase.order with vendor & bid relations
│   ├── rfq_vendor.py          # RFQ-Vendor assignment model
│   └── rfq_bid.py             # Bid and bid line models
├── wizard/
│   ├── __init__.py
│   ├── select_winner_wizard.py        # Bid award wizard
│   └── select_winner_wizard_views.xml
├── views/
│   ├── purchase_order_views.xml  # Extended PO form with vendor/bid tabs
│   ├── rfq_vendor_views.xml     # Vendor assignment views
│   └── rfq_bid_views.xml        # Bid form and list views
├── security/
│   └── ir.model.access.csv      # Access control rules
└── data/
    └── sequence_data.xml         # Bid reference sequences

purchase_request/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── purchase_request.py    # Request model with workflow
│   └── purchase_order.py      # Extends PO with request backlink
├── views/
│   ├── purchase_request_views.xml  # Form, list, kanban, search views + menus
│   └── purchase_order_views.xml    # Extended PO form showing request link
├── security/
│   ├── purchase_request_security.xml  # User groups
│   └── ir.model.access.csv           # Access control rules
└── data/
    └── sequence_data.xml              # Request reference sequences
```

## Installation

### Prerequisites
- Odoo 18.0 Community Edition
- Python 3.12+
- PostgreSQL
- Ubuntu 24.04 (recommended)

### Steps

1. Clone this repository into your Odoo addons directory:
   ```bash
   cd /path/to/odoo/addons
   git clone https://github.com/YOUR_USERNAME/odoo-purchase-customization.git
   cp -r odoo-purchase-customization/purchase_rfq_multi_vendor .
   cp -r odoo-purchase-customization/purchase_request .
   ```

2. Install the `purchase` module from Odoo Apps if not already installed.

3. Update the module list and install both modules:
   ```bash
   ./odoo-bin -d YOUR_DATABASE -i purchase_rfq_multi_vendor,purchase_request --stop-after-init
   ```

4. Restart the Odoo server:
   ```bash
   ./odoo-bin -d YOUR_DATABASE
   ```

## Usage Workflow

### Complete Procurement Cycle

```
Employee                    Procurement Officer              Vendor(s)
   |                              |                             |
   |  1. Create Purchase Request  |                             |
   |----------------------------->|                             |
   |                              |                             |
   |  2. Submit for Approval      |                             |
   |----------------------------->|                             |
   |                              |                             |
   |                 3. Approve   |                             |
   |                              |                             |
   |          4. Generate RFQ     |                             |
   |                              |                             |
   |          5. Assign Vendors   |                             |
   |                              |------ RFQ to Vendor A ----->|
   |                              |------ RFQ to Vendor B ----->|
   |                              |------ RFQ to Vendor C ----->|
   |                              |                             |
   |                              |<----- Bid from Vendor A ----|
   |                              |<----- Bid from Vendor B ----|
   |                              |<----- Bid from Vendor C ----|
   |                              |                             |
   |          6. Compare Bids     |                             |
   |                              |                             |
   |          7. Award Winner     |                             |
   |                              |--- Purchase Order --------->|
   |                              |                             |
```

### Step-by-Step

1. **Create a Purchase Request**: Navigate to *Purchase → Purchase Requests → New*
2. **Fill in the details**: Select employee, add product lines with quantities and estimated prices
3. **Submit**: Click "Submit Request" to send for managerial approval
4. **Approve**: Manager reviews and clicks "Approve"
5. **Generate RFQ**: Click "Create RFQ" to auto-generate an RFQ from the request
6. **Assign Vendors**: Go to the "RFQ Vendors" tab, add multiple vendors
7. **Send RFQ**: Click "Send RFQ to All Vendors" to dispatch to all assigned vendors
8. **Record Bids**: As vendors respond, record their bids with line-item pricing
9. **Compare & Award**: Use the bid comparison view, then award the best bid
10. **Purchase Order**: A new PO is auto-created with the winning vendor's pricing. Confirm it to finalize.

## Technical Details

- **Odoo Version**: 18.0 Community Edition
- **Python Version**: 3.12+
- **Dependencies**: `purchase`, `mail`, `hr` (for employee integration)
- **Design Patterns**: Model inheritance (`_inherit`), One2Many relationships, State machine workflows, Transient wizard models, Mail thread integration

## License

LGPL-3.0 – Same as Odoo Community Edition

## Author

Yiga Chris
