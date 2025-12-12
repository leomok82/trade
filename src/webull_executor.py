from config import Config
# import webull # Placeholder for actual webull library

class WebullExecutor():
    def __init__(self):
        self.user = Config.WEBULL_USERNAME
        self.password = Config.WEBULL_PASSWORD
        # self.wb = webull.paper_login(self.user, self.password) 

    def submit_order(self, symbol, qty, side, order_type='market', price=None):
        print(f"Webull: Submitting {side} order for {qty} shares of {symbol} at {order_type}")
        # return self.wb.place_order(...)
        return "mock_order_id"

    def cancel_order(self, order_id):
        print(f"Webull: Cancelling order {order_id}")
        # return self.wb.cancel_order(order_id)

    def get_positions(self):
        print("Webull: Fetching positions")
        # return self.wb.get_positions()
        return []
