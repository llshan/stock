
import csv
from stock_analysis.data.storage import create_storage
from stock_analysis.trading import TransactionService
from stock_analysis.trading.config import DEFAULT_TRADING_CONFIG

from datetime import datetime

def load_transactions(file_path, db_path="database/stock_data.db"):
    storage = create_storage('sqlite', db_path=db_path)
    config = DEFAULT_TRADING_CONFIG
    svc = TransactionService(storage, config)

    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        for row in reader:
            symbol, action, date_str, unit_cost, quantity = [field.strip() for field in row]
            if action.lower() == 'buy':
                try:
                    # Convert date format
                    date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                    formatted_date = date_obj.strftime('%Y-%m-%d')

                    svc.record_buy_transaction(
                        symbol=symbol.strip(),
                        quantity=float(quantity),
                        price=float(unit_cost),
                        transaction_date=formatted_date,
                    )
                    print(f"Loaded transaction: {symbol}, {quantity}, {unit_cost}")
                except Exception as e:
                    print(f"Error loading transaction {symbol}: {e}")
            else:
                print(f"Skipping non-buy transaction: {row}, action: {action}")

    storage.close()

if __name__ == "__main__":
    load_transactions("transactions.txt")
