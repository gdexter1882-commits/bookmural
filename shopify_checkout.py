"""
Storywalls – size-priced checkout.

Adds POST /api/checkout to the existing Flask app. The storefront cart sends
its murals (variant id + wall size); this module re-checks each one on the
server, works out the price (£24.00 per m², charged per 0.01 m²), and creates
a Shopify draft order in which every mural is quantity 1 at its exact price.
It returns the draft order's checkout link (invoiceUrl) for the browser to open.

Prices are never taken from the browser: they are recalculated here from the
wall size, and the mural must fit the wall under the same rules as the mural
calculator (eligible_texts.try_layout), using the product's page-size fields.

Environment variables (set in Render → Environment):
  SHOPIFY_SHOP           e.g. sj1vbt-c0.myshopify.com
  SHOPIFY_CLIENT_ID      from the Dev Dashboard app (Settings)
  SHOPIFY_CLIENT_SECRET  from the Dev Dashboard app (Settings)
  PRICE_PER_UNIT         optional, price of 0.01 m² in GBP (default 0.24)
  SHOP_CURRENCY          optional, default GBP

The Dev Dashboard app needs the scopes: write_draft_orders, read_products
"""
import json
import math
import os
import threading
import time
import traceback
import urllib.parse
import urllib.request
from decimal import Decimal, ROUND_HALF_UP

from flask import jsonify, request

from eligible_texts import try_layout

API_VERSION = "2026-07"
MAX_ITEMS = 20

_token_lock = threading.Lock()
_token = {"value": None, "expires": 0.0}


def _shop():
    shop = os.environ.get("SHOPIFY_SHOP", "").strip()
    if not shop:
        raise RuntimeError("SHOPIFY_SHOP is not set")
    return shop


def _access_token():
    """Client-credentials token for our own store; cached and renewed before it expires (24 h)."""
    with _token_lock:
        if _token["value"] and time.time() < _token["expires"] - 300:
            return _token["value"]
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": os.environ["SHOPIFY_CLIENT_ID"],
            "client_secret": os.environ["SHOPIFY_CLIENT_SECRET"],
        }).encode()
        req = urllib.request.Request(
            f"https://{_shop()}/admin/oauth/access_token", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        _token["value"] = data["access_token"]
        _token["expires"] = time.time() + int(data.get("expires_in", 86399))
        return _token["value"]


def _graphql(query, variables=None):
    req = urllib.request.Request(
        f"https://{_shop()}/admin/api/{API_VERSION}/graphql.json",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": _access_token()})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    if data.get("errors"):
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


VARIANTS_QUERY = """
query($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on ProductVariant {
      id
      product {
        title
        handle
        pw: metafield(namespace: "custom", key: "page_width_cm") { value }
        ph: metafield(namespace: "custom", key: "page_height_cm") { value }
        pages: metafield(namespace: "custom", key: "pages") { value }
      }
    }
  }
}
"""

DRAFT_ORDER_MUTATION = """
mutation($input: DraftOrderInput!) {
  draftOrderCreate(input: $input) {
    draftOrder { id name invoiceUrl totalPriceSet { presentmentMoney { amount currencyCode } } }
    userErrors { field message }
  }
}
"""


def _cm(value):
    """Whole centimetres, rounded the same way as the storefront (half up)."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def register(app):
    @app.route("/api/checkout", methods=["POST"])
    def create_checkout():
        try:
            data = request.get_json(silent=True) or {}
            items = data.get("items") or []
            if not isinstance(items, list) or not items:
                return jsonify({"error": "Your cart is empty."}), 400
            if len(items) > MAX_ITEMS:
                return jsonify({"error": "Too many murals in one order."}), 400

            unit_price = Decimal(os.environ.get("PRICE_PER_UNIT", "0.24"))
            currency = os.environ.get("SHOP_CURRENCY", "GBP")

            parsed = []
            for it in items:
                vid = str(it.get("variant_id", "")).strip()
                if not vid.isdigit():
                    return jsonify({"error": "Invalid item in cart."}), 400
                w, h = _cm(it.get("wall_width", 0)), _cm(it.get("wall_height", 0))
                if not (1 <= w <= 3000 and 1 <= h <= 1000):
                    return jsonify({"error": "Invalid wall size in cart."}), 400
                parsed.append({"vid": vid, "w": w, "h": h})

            ids = sorted({f"gid://shopify/ProductVariant/{p['vid']}" for p in parsed})
            nodes = {n["id"]: n for n in (_graphql(VARIANTS_QUERY, {"ids": ids})["nodes"] or []) if n}

            line_items = []
            for p in parsed:
                gid = f"gid://shopify/ProductVariant/{p['vid']}"
                node = nodes.get(gid)
                if not node:
                    return jsonify({"error": "A mural in your cart is no longer available."}), 400
                prod = node["product"]
                try:
                    pw = float(prod["pw"]["value"]); ph = float(prod["ph"]["value"]); pages = int(prod["pages"]["value"])
                except (TypeError, ValueError, KeyError):
                    return jsonify({"error": f"Missing size data for {prod['title']}."}), 400
                if not try_layout(p["w"], p["h"], pw, ph, pages).get("eligible"):
                    return jsonify({"error": f"{prod['title']} does not fit a {p['w']} × {p['h']} cm wall. "
                                             "Please remove it from your cart or check the mural calculator."}), 400
                units = math.ceil(p["w"] * p["h"] / 100)          # 100 cm² = 0.01 m²
                area = Decimal(units) / 100
                price = (unit_price * units).quantize(Decimal("0.01"))
                line_items.append({
                    "variantId": gid,
                    "quantity": 1,
                    "priceOverride": {"amount": str(price), "currencyCode": currency},
                    "customAttributes": [
                        {"key": "Wall width", "value": f"{p['w']} cm"},
                        {"key": "Wall height", "value": f"{p['h']} cm"},
                        {"key": "Mural area", "value": f"{area:.2f} m²"},
                    ],
                })

            result = _graphql(DRAFT_ORDER_MUTATION, {"input": {
                "lineItems": line_items,
                "presentmentCurrencyCode": currency,
                "tags": ["storywalls-web-checkout"],
            }})["draftOrderCreate"]
            if result["userErrors"]:
                print(f"❌ draftOrderCreate userErrors: {result['userErrors']}", flush=True)
                return jsonify({"error": "Could not start checkout. Please try again."}), 502
            draft = result["draftOrder"]
            print(f"🧾 Draft order {draft['name']} created: {draft['totalPriceSet']}", flush=True)
            return jsonify({"checkout_url": draft["invoiceUrl"], "draft": draft["name"]})

        except KeyError as e:
            print(f"❌ /api/checkout missing setting: {e}", flush=True)
            return jsonify({"error": "Checkout is not configured yet."}), 503
        except Exception as e:
            print(f"❌ Error in /api/checkout: {e}", flush=True)
            traceback.print_exc()
            return jsonify({"error": "Could not start checkout. Please try again."}), 500
