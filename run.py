from flask import Flask, request, jsonify, render_template_string, url_for
import pyotp
from logzero import logger
import http.client  # For making HTTP requests (if needed)
import json         # For parsing and generating JSON data

# -------------------------------------------------------------------------
# SMART API (Angel One)
# -------------------------------------------------------------------------
# Ensure you install the correct SmartAPI library:
# pip install smartapi-python
from SmartApi.smartConnect import SmartConnect

# Replace these with your actual credentials
api_key = 'y2gLEdxZ'
username = 'A62128571'
pwd = '0852'

# If you have a TOTP secret from Angel One, provide it here;
# otherwise, your `login_to_api()` might rely on a user-provided TOTP each time.
# totp_secret = 'YOUR_TOTP_SECRET'

smartApi = SmartConnect(api_key=api_key)

app = Flask(__name__)

# -------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------
def generate_totp(token):
    """
    Generate TOTP code using a provided token (i.e., the string/secret from your QR code).
    """
    try:
        totp = pyotp.TOTP(token).now()
        return totp
    except Exception as e:
        logger.error("Invalid Token: The provided token is not valid.")
        raise e

def login_to_api(username, password, token):
    """
    Log in to the Smart API using credentials and a TOTP.
    Returns (authToken, refreshToken) upon success, or None if fails.
    """
    try:
        # Generate the 6-digit TOTP from the secret
        totp_code = generate_totp(token)
        data = smartApi.generateSession(username, password, totp_code)
        
        if not data or data.get('status') == False:
            logger.error(data)
            return None
        
        # Extract tokens
        auth_token = data['data']['jwtToken']
        refresh_token = data['data']['refreshToken']
        return auth_token, refresh_token
    except Exception as e:
        logger.exception(f"Login failed: {e}")
        return None

def place_order(orderparams):
    """
    Place an order with given order parameters.
    Returns the order ID on success, or None on failure.
    """
    try:
        orderid = smartApi.placeOrder(orderparams)
        logger.info(f"Order placed successfully: {orderid}")
        return orderid
    except Exception as e:
        logger.exception(f"Order placement failed: {e}")
        return None

def create_gtt_rule(gttCreateParams):
    """
    Create a GTT rule with the given parameters.
    Returns the GTT rule ID on success, or None on failure.
    """
    try:
        rule_id = smartApi.gttCreateRule(gttCreateParams)
        logger.info(f"The GTT rule id is: {rule_id}")
        return rule_id
    except Exception as e:
        logger.exception(f"GTT Rule creation failed: {e}")
        return None

def list_gtt_rules():
    """
    List GTT rules. Returns the GTT list data, or None on failure.
    """
    try:
        status = ["FORALL"]
        page = 1
        count = 10
        gtt_list = smartApi.gttLists(status, page, count)
        return gtt_list
    except Exception as e:
        logger.exception(f"GTT Rule List failed: {e}")
        return None

# -------------------------------------------------------------------------
# FRONTEND TEMPLATE (HTML + JS)
# -------------------------------------------------------------------------
HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Angel One Trading Dashboard</title>
    <!-- Include Bootstrap for styling -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- TradingView Library for live charts -->
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>

    <style>
/* General Body Styles */
body {
    background: radial-gradient(circle, #ffffff 30%, #f9f9f9 100%);
    color: #333333;
    font-family: "Arial", sans-serif;
    margin: 0;
    padding: 0;
}

/* Container */
.container {
    margin-top: 30px;
    padding: 0 20px;
}

/* Navbar */
.navbar {
    background: linear-gradient(to bottom, #ffffff, #f0f0f0);
    padding: 20px 30px;
    box-shadow: 0 4px 10px rgba(255, 253, 255, 0.4);
    border-bottom: 2px solid #007bff;
    position: relative;
}

.navbar-brand {
    font-size: 2rem;
    font-weight: bold;
    color: #007bff;
    text-shadow: 0 0 10px rgba(0, 123, 255, 0.8);
}

.navbar-brand:hover {
    color: #0056b3;
    text-shadow: 0 0 15px rgba(0, 86, 179, 0.8);
}

/* Logo Glow */
.logo-container img {
    max-width: 150px;
    height: auto;
    filter: drop-shadow(0 0 10px rgba(0, 123, 255, 1));
}

/* Custom Card Styles */
.custom-card {
    background: linear-gradient(145deg, #ffffff, #f9f9f9);
    border: 1px solid #007bff;
    border-radius: 12px;
    box-shadow: 0 8px 20px rgba(0, 123, 255, 0.3);
    transition: all 0.3s ease;
    overflow: hidden;
}

.custom-card:hover {
    transform: scale(1.02);
    box-shadow: 0 12px 30px rgba(0, 123, 255, 0.6);
}

.custom-card h5 {
    margin-bottom: 1rem;
    color: #007bff;
    text-shadow: 0 0 10px rgba(0, 123, 255, 0.8);
}

/* Buttons */
.btn-primary {
    background: linear-gradient(to right, #007bff, #0056b3);
    border: none;
    color: #fff;
    font-weight: bold;
    text-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
    box-shadow: 0 4px 10px rgba(0, 123, 255, 0.6);
    transition: all 0.3s ease;
}

.btn-primary:hover {
    background: linear-gradient(to right, #0056b3, #007bff);
    box-shadow: 0 6px 15px rgba(0, 123, 255, 0.8);
    transform: scale(1.05);
}

/* Form Elements */
input.form-control, select.form-select {
    background: #fff;
    color: #FF2C2C;
    border: 1px solid #008000;
    border-radius: 8px;
    box-shadow: 0 2px 5px rgba(255, 215, 0, 0.3);
    padding: 10px;
}

input.form-control:focus, select.form-select:focus {
    border-color: #FFD700;
    box-shadow: 0 4px 10px rgba(255, 215, 0, 0.6);
}

/* Response Box */
.response-box {
    background: #fff;
    color: #008000;
    border: 1px solid #008000;
    border-radius: 8px;
    padding: 15px;
    margin-top: 20px;
    box-shadow: 0 4px 10px rgba(255, 215, 0, 0.4);
}

/* Footer */
footer {
    background: #fff;
    color: #000;
    padding: 20px;
    text-align: center;
    border-top: 2px solid #FF2C2C;
    box-shadow: 0 0 10px rgba(255, 215, 0, 0.4);
}

/* Live Chart Section */
#tradingview-widget-container {
    border: 1px solid #008000;
    box-shadow: 0 0 15px rgba(255, 215, 0, 0.5);
    border-radius: 10px;
}

/* Button customizations */
.btn-primary, .btn-success, .btn-warning, .btn-info, .btn-secondary {
    border: 1px solid #008000 !important;
}

.btn-primary:hover, .btn-success:hover, .btn-warning:hover, .btn-info:hover, .btn-secondary:hover {
    background-color: #008000 !important;
    color: #fff !important;
}

/* Form Label */
.form-label {
    color: #008000;
}

/* Card Title */
.card-title {
    text-shadow: 1px 1px 2px rgba(255, 215, 0, 0.6);
}

/* Steps Navigation Buttons */
.btn-nav {
    margin-right: 5px;
    margin-bottom: 5px;
    background: linear-gradient(90deg, #228B22, #FF0000);
    background-size: 200% 200%;
    color: #FFFFFF;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    box-shadow: 0 0 10px rgba(34, 139, 34, 0.7);
    transition: all 0.3s ease;
    animation: gradient-flow 4s infinite, button-glow 2s infinite alternate;
}

.btn-nav:hover {
    background: linear-gradient(90deg, #006400, #CC0000);
    box-shadow: 0 0 20px rgba(255, 0, 0, 0.8);
}

/* Gradient Flow Animation */
@keyframes gradient-flow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Button Glow Animation */
@keyframes button-glow {
    0% { box-shadow: 0 0 10px rgba(34, 139, 34, 0.7); }
    100% { box-shadow: 0 0 20px rgba(255, 0, 0, 0.8); }
}

/* Smooth Scroll Helper */
html {
  scroll-behavior: smooth;
}
    </style>
</head>
<body>
<nav class="navbar navbar-expand-lg">
    <div class="container-fluid d-flex justify-content-between align-items-center">
        <!-- Left Logo -->
        <div class="logo-container">
            <img src="{{ url_for('static', filename='Angel.png') }}" alt="Angel One Logo">
        </div>

        <!-- Navbar Brand -->
        <span class="navbar-brand">Angel One Trading Dashboard</span>

        <!-- Right Logo -->
        <div class="logo-container">
            <img src="{{ url_for('static', filename='ramdoot.jpg') }}" alt="Ramdoot Logo">
        </div>
    </div>
</nav>

<!-- STEPS NAVIGATION -->
<div class="container mt-3">
    <!-- Clicking these buttons calls showSection() to reveal the relevant part -->
    <button class="btn-nav" onclick="showSection('section1')">Login</button>
    <button class="btn-nav" onclick="showSection('section2')">Place Order</button>
    <button class="btn-nav" onclick="showSection('section3')">Create GTT</button>
    <button class="btn-nav" onclick="showSection('section4')">List GTT</button>
    <button class="btn-nav" onclick="showSection('section5')">Call/Put</button>
    <button class="btn-nav" onclick="showSection('section6')">Auto/Manual</button>
    <button class="btn-nav" onclick="showSection('sectionProfile')">Profile</button>
    <button class="btn-nav" onclick="showSection('sectionWallet')">Wallet</button>
    <button class="btn-nav" onclick="showSection('sectionTradeHistory')">Trade History</button>
    <button class="btn-nav" onclick="showSection('sectionStopLossSettings')">Stop Loss</button>
    <button class="btn-nav" onclick="showSection('sectionIndicatorSettings')">Indicators</button>
    <button class="btn-nav" onclick="showSection('sectionErrorAlerts')">Error Alerts</button>
    <button class="btn-nav" onclick="showSection('sectionChart')">Live Chart</button>
</div>

<!-- MAIN CONTENT CONTAINER -->
<div class="container py-4">

    <!-- 1. LOGIN -->
    <div class="row mb-4" id="section1" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">1. Login</h5>
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input id="username" type="text" class="form-control" placeholder="Username">
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input id="password" type="password" class="form-control" placeholder="Password">
                    </div>
                    <div class="mb-3">
                        <label for="totp" class="form-label">TOTP Secret (from QR Code)</label>
                        <input id="totp" type="text" class="form-control" placeholder="TOTP secret">
                    </div>
                    <button class="btn btn-primary" onclick="login()">Login</button>
                    <div id="login-response" class="response-box"></div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 2. PLACE ORDER -->
    <div class="row mb-4" id="section2" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">2. Place Order</h5>
                    <p class="small text-muted" style="color:#000000 !important;">
                        Example parameters for demonstration. Adjust as needed.
                    </p>
                    
                    <!-- Variety Dropdown -->
                    <div class="mb-2">
                        <label for="order-variety" class="form-label">Variety</label>
                        <select id="order-variety" class="form-select">
                            <option value="NORMAL">Normal Order (Regular)</option>
                            <option value="STOPLOSS">Stop Loss Order</option>
                            <option value="AMO">After Market Order</option>
                            <option value="ROBO">ROBO (Bracket Order)</option>
                        </select>
                    </div>
                    
                    <!-- Trading Symbol -->
                    <div class="mb-2">
                        <label for="order-tradingsymbol" class="form-label">Trading Symbol</label>
                        <input id="order-tradingsymbol" type="text" class="form-control" value="SBIN-EQ">
                    </div>
                    
                    <!-- Symbol Token -->
                    <div class="mb-2">
                        <label for="order-symboltoken" class="form-label">Symbol Token</label>
                        <input id="order-symboltoken" type="text" class="form-control" value="3045">
                    </div>
                    
                    <!-- Transaction Type Dropdown -->
                    <div class="mb-2">
                        <label for="order-transactiontype" class="form-label">Transaction Type</label>
                        <select id="order-transactiontype" class="form-select">
                            <option value="BUY">Buy</option>
                            <option value="SELL">Sell</option>
                        </select>
                    </div>
                    
                    <!-- Exchange Dropdown -->
                    <div class="mb-2">
                        <label for="order-exchange" class="form-label">Exchange</label>
                        <select id="order-exchange" class="form-select">
                            <option value="NSE">NSE (Equity)</option>
                            <option value="BSE">BSE (Equity)</option>
                            <option value="NFO">NSE Futures and Options</option>
                            <option value="MCX">MCX Commodity</option>
                            <option value="BFO">BSE Futures and Options</option>
                            <option value="CDS">Currency Derivative Segment</option>
                        </select>
                    </div>
                    
                    <!-- Order Type Dropdown -->
                    <div class="mb-2">
                        <label for="order-ordertype" class="form-label">Order Type</label>
                        <select id="order-ordertype" class="form-select">
                            <option value="MARKET">Market Order (MKT)</option>
                            <option value="LIMIT">Limit Order (L)</option>
                            <option value="STOPLOSS_LIMIT">Stop Loss Limit Order (SL)</option>
                            <option value="STOPLOSS_MARKET">Stop Loss Market Order (SL-M)</option>
                        </select>
                    </div>
                    
                    <!-- Product Type Dropdown -->
                    <div class="mb-2">
                        <label for="order-producttype" class="form-label">Product Type</label>
                        <select id="order-producttype" class="form-select">
                            <option value="DELIVERY">Cash & Carry (CNC)</option>
                            <option value="CARRYFORWARD">Normal for Futures and Options (NRML)</option>
                            <option value="MARGIN">Margin Delivery</option>
                            <option value="INTRADAY">Margin Intraday Squareoff (MIS)</option>
                            <option value="BO">Bracket Order (BO)</option>
                        </select>
                    </div>
                    
                    <!-- Duration Dropdown -->
                    <div class="mb-2">
                        <label for="order-duration" class="form-label">Duration</label>
                        <select id="order-duration" class="form-select">
                            <option value="DAY">Regular Order (DAY)</option>
                            <option value="IOC">Immediate or Cancel (IOC)</option>
                        </select>
                    </div>
                    
                    <!-- Price -->
                    <div class="mb-2">
                        <label for="order-price" class="form-label">Price</label>
                        <input id="order-price" type="text" class="form-control" value="19500">
                    </div>
                    
                    <!-- Quantity -->
                    <div class="mb-2">
                        <label for="order-quantity" class="form-label">Quantity</label>
                        <input id="order-quantity" type="text" class="form-control" value="1">
                    </div>
                    
                    <!-- Place Order Button -->
                    <button class="btn btn-success" onclick="placeOrder()">Place Order</button>
                    <div id="order-response" class="response-box"></div>
                </div>
            </div>
        </div>
    </div>


    <!-- 3. CREATE GTT RULE -->
    <div class="row mb-4" id="section3" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">3. Create GTT Rule</h5>
                    <p class="small text-muted" style="color:#000000 !important;">
                        Example parameters for demonstration. Adjust as needed.
                    </p>
                    <div class="mb-2">
                        <label for="gtt-tradingsymbol" class="form-label">Trading Symbol</label>
                        <input id="gtt-tradingsymbol" type="text" class="form-control" value="SBIN-EQ">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-symboltoken" class="form-label">Symbol Token</label>
                        <input id="gtt-symboltoken" type="text" class="form-control" value="3045">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-exchange" class="form-label">Exchange</label>
                        <input id="gtt-exchange" type="text" class="form-control" value="NSE">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-producttype" class="form-label">Product Type</label>
                        <input id="gtt-producttype" type="text" class="form-control" value="MARGIN">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-transactiontype" class="form-label">Transaction Type (BUY/SELL)</label>
                        <input id="gtt-transactiontype" type="text" class="form-control" value="BUY">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-price" class="form-label">Price</label>
                        <input id="gtt-price" type="number" class="form-control" value="100000">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-qty" class="form-label">Quantity</label>
                        <input id="gtt-qty" type="number" class="form-control" value="10">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-disclosedqty" class="form-label">Disclosed Quantity</label>
                        <input id="gtt-disclosedqty" type="number" class="form-control" value="10">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-triggerprice" class="form-label">Trigger Price</label>
                        <input id="gtt-triggerprice" type="number" class="form-control" value="200000">
                    </div>
                    <div class="mb-2">
                        <label for="gtt-timeperiod" class="form-label">Time Period</label>
                        <input id="gtt-timeperiod" type="number" class="form-control" value="365">
                    </div>

                    <button class="btn btn-warning" onclick="createGttRule()">Create GTT Rule</button>
                    <div id="gtt-create-response" class="response-box"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 4. LIST GTT RULES -->
    <div class="row mb-4" id="section4" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">4. List GTT Rules</h5>
                    <button class="btn btn-info" onclick="listGttRules()">List GTT Rules</button>
                    <div id="gtt-list-response" class="response-box"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 5. Call/Put Section -->
    <div class="row mb-4" id="section5" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">5. Call/Put Options</h5>
                    <p class="small text-muted" style="color:#000000 !important;">
                        Choose your Option type and Strike Price. Set "AUTO" trade mode to immediately place an order.
                    </p>
                    <div class="mb-3">
                        <label for="option-type" class="form-label">Option Type</label>
                        <select id="option-type" class="form-select">
                            <option value="CALL">Call</option>
                            <option value="PUT">Put</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label for="strike-price" class="form-label">Strike Price</label>
                        <input id="strike-price" type="number" class="form-control" placeholder="Enter Strike Price">
                    </div>
                    <button class="btn btn-primary" onclick="selectOption()">Submit</button>
                    <div id="option-response" class="response-box"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 6. Auto/Manual Buy/Sell -->
    <div class="row mb-4" id="section6" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">6. Auto/Manual Buy/Sell</h5>
                    <p class="small text-muted" style="color:#000000 !important;">
                        Auto: Orders are placed instantly on "Submit" (above). 
                        Manual: You can confirm before placing.
                    </p>
                    <div class="mb-3">
                        <label for="trade-mode" class="form-label">Trade Mode</label>
                        <select id="trade-mode" class="form-select">
                            <option value="AUTO">Auto</option>
                            <option value="MANUAL" selected>Manual</option>
                        </select>
                    </div>
                    <button class="btn btn-warning" onclick="setTradeMode()">Set Mode</button>
                    <div id="trade-mode-response" class="response-box"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 7. Profile -->
    <div class="row mb-4" id="sectionProfile" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">Profile</h5>
                    <button class="btn btn-info" onclick="fetchProfile()">Fetch Profile</button>
                    <div id="profile-response" class="response-box" style="overflow-x: auto;"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 8. Wallet -->
    <div class="row mb-4" id="sectionWallet" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">Wallet</h5>
                    <p>Here you can see your wallet summary, account balance, and recent deposits/withdrawals.</p>
                    <!-- Example placeholder content -->
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Currency</th>
                                <th>Balance</th>
                                <th>Last Deposit</th>
                                <th>Last Withdrawal</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>INR</td>
                                <td>50000</td>
                                <td>2023-12-15</td>
                                <td>2023-12-10</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- 9. Trade History -->
    <div class="row mb-4" id="sectionTradeHistory" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">Trade History</h5>
                    <p>Your complete trading history.</p>
                    <!-- Example placeholder content -->
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Symbol</th>
                                <th>Buy/Sell</th>
                                <th>Price</th>
                                <th>Quantity</th>
                                <th>PNL</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>2023-12-15</td>
                                <td>SBIN-EQ</td>
                                <td>BUY</td>
                                <td>19500</td>
                                <td>1</td>
                                <td>+250</td>
                            </tr>
                            <tr>
                                <td>2023-12-14</td>
                                <td>SBIN-EQ</td>
                                <td>SELL</td>
                                <td>19300</td>
                                <td>1</td>
                                <td>-200</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- 10. Stop Loss Settings -->
    <div class="row mb-4" id="sectionStopLossSettings" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">Stop Loss Settings</h5>
                    <p>Automatically place stop loss orders with certain offsets.</p>
                    <!-- Example placeholder content -->
                    <div class="mb-3">
                        <label class="form-label" for="stoploss-offset">Stop Loss Offset (in %)</label>
                        <input id="stoploss-offset" type="number" class="form-control" value="2">
                    </div>
                    <button class="btn btn-primary">Update Stop Loss Settings</button>
                </div>
            </div>
        </div>
    </div>

    <!-- 11. Indicator Settings -->
    <div class="row mb-4" id="sectionIndicatorSettings" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">Indicator Settings</h5>
                    <p>Configure your preferred technical indicators here.</p>
                    <!-- Example placeholder content -->
                    <div class="mb-3">
                        <label class="form-label" for="indicator-rsi">RSI Period</label>
                        <input id="indicator-rsi" type="number" class="form-control" value="14">
                    </div>
                    <div class="mb-3">
                        <label class="form-label" for="indicator-macd">MACD Fast/Slow</label>
                        <input id="indicator-macd" type="text" class="form-control" value="12,26">
                    </div>
                    <button class="btn btn-primary">Save Indicator Settings</button>
                </div>
            </div>
        </div>
    </div>

    <!-- 12. Error Alerts -->
    <div class="row mb-4" id="sectionErrorAlerts" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">Error Alerts</h5>
                    <p>View recent errors or system alerts here.</p>
                    <!-- Example placeholder content -->
                    <ul>
                        <li>No recent errors</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <!-- 13. LIVE CHART -->
    <div class="row mb-4" id="sectionChart" style="display:none;">
        <div class="col-lg-12">
            <div class="card custom-card">
                <div class="card-body">
                    <h5 class="card-title">13. Live Chart</h5>
                    <p class="small text-muted" style="color:#000000 !important;">NIFTY Index Real-time Chart (TradingView)</p>
                    <div id="tradingview-widget-container" style="height: 500px;"></div>
                </div>
            </div>
        </div>
    </div>

</div>

<!-- FOOTER -->
<footer>
    <div class="container">
        <p class="mb-0">
            Angel One Trading Dashboard &mdash; Powered by <strong>Flask</strong> and <strong>Bootstrap</strong>
        </p>
    </div>
</footer>

<!-- Bootstrap JS + Dependencies (Popper) -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<script>
    // Helper function to show a specific section and hide all others
    function showSection(sectionId) {
        // Hide all sections
        const sections = document.querySelectorAll('.row.mb-4');
        sections.forEach(section => {
            section.style.display = 'none';
        });

        // Show only the clicked section
        const target = document.getElementById(sectionId);
        if (target) {
            target.style.display = 'block';
            // Scroll to the section if desired
            target.scrollIntoView({ behavior: 'smooth' });
        } else {
            console.warn(`Section with ID ${sectionId} not found.`);
        }
    }

    // Global variables for TOTP-based login, tokens, etc.
    let authToken = null;
    let refreshToken = null;
    let selectedOptionParams = null;

    // 1. LOGIN
    function login() {
        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;
        const totp = document.getElementById("totp").value;

        // Call our Flask endpoint to handle login
        fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, totp })
        })
        .then(res => res.json())
        .then(data => {
            const resp = document.getElementById("login-response");
            if (data.success) {
                resp.textContent = "Login Successfully";
                resp.style.color = "#00ff00"; // success in green
                authToken = data.authToken;
                refreshToken = data.refreshToken;
            } else {
                resp.textContent = data.message || "Login Failed!";
                resp.style.color = "red";
            }
        })
        .catch(err => {
            const resp = document.getElementById("login-response");
            resp.textContent = "Error: " + err;
            resp.style.color = "red";
        });
    }

    // 2. PLACE ORDER
    function placeOrder() {
        const orderParams = {
            variety: document.getElementById("order-variety").value,
            tradingsymbol: document.getElementById("order-tradingsymbol").value,
            symboltoken: document.getElementById("order-symboltoken").value,
            transactiontype: document.getElementById("order-transactiontype").value,
            exchange: document.getElementById("order-exchange").value,
            ordertype: document.getElementById("order-ordertype").value,
            producttype: document.getElementById("order-producttype").value,
            duration: document.getElementById("order-duration").value,
            price: document.getElementById("order-price").value,
            squareoff: "0",
            stoploss: "0",
            quantity: document.getElementById("order-quantity").value
        };

        fetch('/api/place_order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ orderParams, authToken, refreshToken })
        })
        .then(res => res.json())
        .then(data => {
            const resp = document.getElementById("order-response");
            if (data.success) {
                resp.textContent = "Order placed! ID: " + data.orderid;
                resp.style.color = "#008000";
            } else {
                resp.textContent = "Order failed!\n" + JSON.stringify(data);
                resp.style.color = "red";
            }
        })
        .catch(err => {
            document.getElementById("order-response").textContent = "Error: " + err;
        });
    }

    // 3. CREATE GTT RULE
    function createGttRule() {
        const gttParams = {
            tradingsymbol: document.getElementById("gtt-tradingsymbol").value,
            symboltoken: document.getElementById("gtt-symboltoken").value,
            exchange: document.getElementById("gtt-exchange").value,
            producttype: document.getElementById("gtt-producttype").value,
            transactiontype: document.getElementById("gtt-transactiontype").value,
            price: parseFloat(document.getElementById("gtt-price").value),
            qty: parseInt(document.getElementById("gtt-qty").value),
            disclosedqty: parseInt(document.getElementById("gtt-disclosedqty").value),
            triggerprice: parseFloat(document.getElementById("gtt-triggerprice").value),
            timeperiod: parseInt(document.getElementById("gtt-timeperiod").value),
        };

        fetch('/api/create_gtt_rule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gttParams, authToken, refreshToken })
        })
        .then(res => res.json())
        .then(data => {
            const resp = document.getElementById("gtt-create-response");
            if (data.success) {
                resp.textContent = "GTT Rule created! ID: " + data.rule_id;
                resp.style.color = "#008000";
            } else {
                resp.textContent = "GTT creation failed!\n" + JSON.stringify(data);
                resp.style.color = "red";
            }
        })
        .catch(err => {
            document.getElementById("gtt-create-response").textContent = "Error: " + err;
        });
    }

    // 4. LIST GTT RULES
    function listGttRules() {
        fetch('/api/list_gtt_rules', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ authToken, refreshToken })
        })
        .then(res => res.json())
        .then(data => {
            const resp = document.getElementById("gtt-list-response");
            if (data.success) {
                resp.textContent = "GTT Rules:\n" + JSON.stringify(data.gtt_list, null, 2);
                resp.style.color = "#008000";
            } else {
                resp.textContent = "Failed to list GTT rules!\n" + JSON.stringify(data);
                resp.style.color = "red";
            }
        })
        .catch(err => {
            document.getElementById("gtt-list-response").textContent = "Error: " + err;
        });
    }

    // 5. SELECT OPTION (CALL/PUT)
    function selectOption() {
        const optionType = document.getElementById("option-type").value;  // CALL or PUT
        const strikePrice = parseFloat(document.getElementById("strike-price").value);
        const resp = document.getElementById("option-response");

        if (isNaN(strikePrice)) {
            resp.textContent = "Please enter a valid numeric Strike Price.";
            resp.style.color = "red";
            return;
        }
        
        const symbol = "NIFTY" + strikePrice + (optionType === 'CALL' ? "CE" : "PE");
        selectedOptionParams = {
            variety: "NORMAL",
            tradingsymbol: symbol,
            symboltoken: "9999999", // placeholder, you'd get actual token from your broker
            transactiontype: "BUY",
            exchange: "NFO",        // typically options are in NFO
            ordertype: "MARKET",
            producttype: "INTRADAY",
            duration: "DAY",
            price: "0",            
            squareoff: "0",
            stoploss: "0",
            quantity: "75"         
        };
        resp.textContent = `Selected Option: ${symbol}, stored internally.`;
        resp.style.color = "#FFD700";

        // If in AUTO mode, place the order automatically
        if (document.getElementById("trade-mode").value === "AUTO") {
            autoPlaceSelectedOption();
        }
    }

    // 6. AUTO / MANUAL TRADE MODE
    function setTradeMode() {
        const mode = document.getElementById("trade-mode").value;
        const resp = document.getElementById("trade-mode-response");
        
        resp.textContent = `Trade mode set to ${mode}`;
        resp.style.color = "#FFD700";
        
        // If mode is AUTO and an option is already selected, place immediately
        if (mode === "AUTO" && selectedOptionParams) {
            autoPlaceSelectedOption();
        }
    }

    function autoPlaceSelectedOption() {
        const resp = document.getElementById("option-response");
        if (!selectedOptionParams) {
            resp.textContent = "No option data selected! Please choose Call/Put first.";
            resp.style.color = "red";
            return;
        }

        fetch('/api/place_order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ orderParams: selectedOptionParams, authToken, refreshToken })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                resp.textContent = "AUTO mode: Order placed! ID: " + data.orderid;
                resp.style.color = "#00ff00";
            } else {
                resp.textContent = "AUTO order failed!\n" + JSON.stringify(data);
                resp.style.color = "red";
            }
        })
        .catch(err => {
            resp.textContent = "Error (AUTO): " + err;
            resp.style.color = "red";
        });
    }

    // 7. FETCH PROFILE
    function fetchProfile() {
        if (!refreshToken) {
            const resp = document.getElementById("profile-response");
            resp.textContent = "You need to log in first!";
            resp.style.color = "red";
            return;
        }

        fetch('/api/get_profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refreshToken })
        })
        .then(res => res.json())
        .then(data => {
            const resp = document.getElementById("profile-response");
            if (data.success) {
                const profile = data.profile;
                let tableHTML = `
                    <table class="table table-bordered table-striped" style="color:#000;">
                        <tr><th>Field</th><th>Value</th></tr>
                        <tr><td>Client Code</td><td>${profile.clientcode}</td></tr>
                        <tr><td>Name</td><td>${profile.name}</td></tr>
                        <tr><td>Email</td><td>${profile.email}</td></tr>
                        <tr><td>Mobile Number</td><td>${profile.mobileno}</td></tr>
                        <tr><td>Exchanges</td><td>${profile.exchanges}</td></tr>
                        <tr><td>Products</td><td>${profile.products}</td></tr>
                        <tr><td>Last Login Time</td><td>${profile.lastlogintime || "N/A"}</td></tr>
                        <tr><td>Broker ID</td><td>${profile.brokerid}</td></tr>
                    </table>
                `;
                resp.innerHTML = tableHTML;
                resp.style.color = "black"; 
            } else {
                resp.textContent = `Failed to fetch profile: ${data.error}`;
                resp.style.color = "red";
            }
        })
        .catch(err => {
            const resp = document.getElementById("profile-response");
            resp.textContent = "Error: " + err;
            resp.style.color = "red";
        });
    }

    // 8. TRADINGVIEW LIVE CHART (NIFTY)
    new TradingView.widget({
        "width": "100%",
        "height": 500,
        "symbol": "NSE:NIFTY",
        "interval": "5",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "container_id": "tradingview-widget-container"
    });
</script>

</body>
</html>
"""

# -------------------------------------------------------------------------
# FLASK ROUTES
# -------------------------------------------------------------------------
@app.route('/', methods=['GET'])
def index():
    """
    Serves the main HTML page with embedded JavaScript and Bootstrap.
    """
    return render_template_string(HTML_PAGE)


# 1. LOGIN
@app.route('/api/login', methods=['POST'])
def api_login():
    """
    API endpoint for logging in using provided credentials and TOTP token.
    """
    data = request.get_json()
    username_input = data.get('username')
    password_input = data.get('password')
    totp_input = data.get('totp')

    auth_tokens = login_to_api(username_input, password_input, totp_input)
    if auth_tokens:
        return jsonify({
            "success": True,
            "message": "Login Successfully",
            "authToken": auth_tokens[0],
            "refreshToken": auth_tokens[1]
        })
    else:
        return jsonify({"success": False, "message": "Login Failed"})


# 2. PLACE ORDER
@app.route('/api/place_order', methods=['POST'])
def api_place_order():
    """
    API endpoint to place an order.
    """
    data = request.get_json()
    order_params = data.get('orderParams', {})
    # Typically you'd re-auth or ensure the session is valid. 
    order_id = place_order(order_params)
    if order_id:
        return jsonify({"success": True, "orderid": order_id})
    else:
        return jsonify({"success": False, "error": "Order placement failed."})


# 3. CREATE GTT RULE
@app.route('/api/create_gtt_rule', methods=['POST'])
def api_create_gtt_rule():
    """
    API endpoint to create a GTT rule.
    """
    data = request.get_json()
    gtt_params = data.get('gttParams', {})

    rule_id = create_gtt_rule(gtt_params)
    if rule_id:
        return jsonify({"success": True, "rule_id": rule_id})
    else:
        return jsonify({"success": False, "error": "GTT Rule creation failed."})


# 4. LIST GTT RULES
@app.route('/api/list_gtt_rules', methods=['POST'])
def api_list_gtt_rules():
    """
    API endpoint to list GTT rules.
    """
    gtt_list_data = list_gtt_rules()
    if gtt_list_data:
        return jsonify({"success": True, "gtt_list": gtt_list_data})
    else:
        return jsonify({"success": False, "error": "GTT listing failed."})


# 7. GET PROFILE
@app.route('/api/get_profile', methods=['POST'])
def api_get_profile():
    """
    API endpoint to fetch user profile using SmartAPI's getProfile() method.
    """
    data = request.get_json()
    refresh_token_input = data.get("refreshToken")

    if not refresh_token_input:
        return jsonify({"success": False, "error": "Missing refreshToken"})

    try:
        # Attempt to fetch user profile
        profile_data = smartApi.getProfile(refresh_token_input)
        if not profile_data or not profile_data.get('status'):
            raise Exception(profile_data.get('message', 'Unknown error fetching profile'))

        profile = profile_data.get('data', {})
        return jsonify({"success": True, "profile": profile})
    except Exception as e:
        logger.error(f"Failed to fetch profile: {e}")
        return jsonify({"success": False, "error": str(e)})


# -------------------------------------------------------------------------
# RUN FLASK (Development Only)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # In production, use a production-ready WSGI server like gunicorn.
    app.run(debug=True)