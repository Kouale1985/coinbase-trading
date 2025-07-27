import logging

portfolio = {
    "USD": 100000,  # starting balance
    "positions": {}
}

def simulate_trade(action, product_id, price, quantity=0.0):
    global portfolio
    log = f"[SIMULATION] {action.upper()} {product_id} at ${price:.4f}"

    if action == "buy":
        cost = price * quantity
        if portfolio["USD"] >= cost:
            portfolio["USD"] -= cost
            portfolio["positions"][product_id] = portfolio["positions"].get(product_id, 0.0) + quantity
            logging.info(f"{log} — Bought {quantity:.2f}. New USD balance: ${portfolio['USD']:.2f}")
        else:
            logging.warning(f"{log} — Not enough USD to buy {quantity:.2f}")

    elif action == "sell":
        held_qty = portfolio["positions"].get(product_id, 0.0)
        if held_qty >= quantity:
            portfolio["USD"] += price * quantity
            portfolio["positions"][product_id] -= quantity
            logging.info(f"{log} — Sold {quantity:.2f}. New USD balance: ${portfolio['USD']:.2f}")
        else:
            logging.warning(f"{log} — Not enough {product_id} to sell {quantity:.2f}")

    else:
        logging.error(f"{log} — Unknown action.")

    return portfolio
