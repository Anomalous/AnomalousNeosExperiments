import csv
from datetime import datetime
import os
from posixpath import split
import sys

# Koinly import formats: https://help.koinly.io/en/articles/3662999-how-to-create-a-custom-csv-file-with-your-data
# The simple format that doesn't support trades uses these fields:
# Koinly Date (required) - must be UTC time formatted as YYYY-MM-DD HH:mm:ss
# Amount (required) - NCR amount
# Currency (required) - "NCR"
# Net Worth Amount (optional) - value of transaction in fiat (USD); no NOT include fees here
# Net Worth Currency (optional) - "USD" or other fiat
# Label (optional) - 
#   outgoing: gift, loss, cost, margin fee, realized gain
#   incoming: airdrop, fork, mining, reward, income, loan interest, realized gain
# Description (optional) - description
# TxHash (optional) - N/A for Neos

# TokenTax manual CSV format is here: https://help.tokentax.co/en/articles/1707630-create-a-manual-csv-report-of-your-transactions
# Type - Trade / Deposit / Withdrawal / Income / Spend / Lost / Stolen / Mining / Gift
#   in Neos, receives would be Deposit or Income. Sends would be Withdrawal, Spend, or Gift
# BuyAmount, BuyCurrency - amount received or acquired and associated currency (leave blank if N/A)
# SellAmount, SellCurrency - amount traded/transferred/lost and associated currency (leave blank if N/A)
# FeeAmount, FeeCurrency - fortunately blank for Neos!
# Exchange - where the transaction too place; exchange name or wallet name
# Group - for flagging margin trades, leave blank
# Comment - self explanatory
# Date - must be formatted MM/DD/YY HH:MM (though the example CSV shows a 4-digit year)

# TaxBit format here: https://taxbit.com/help/csv-import
# "Date and Time" - ISO8601 like 2018-06-07T20:57:00
# "Transaction Type" - Buy / Sale / Trade / Transfer In / Transfer Out / Income / Expense
#   in Neos, receives would be Buy, Transfer In, or Income
#   in Neos, sends would be Sale, Transfer Out, or Expense
# "Sent Quantity" - NCR/KFC amount sent, blank if N/A. For "Buy" this should be fiat, for "Trade" or "Sale" it should be crypto
# "Sent Currency" - NCR/KFC, blank if N/A. For "Buy" this should be fiat, for "Trade" or "Sale" it should be crypto
# "Sending Source" - optional; exchange or wallet $ came from [that's what the doc says, but sample file uses this as a 'sent to' label]
# "Received Quantity" - NCR/KFC amount received, blank if N/A
# "Received Currency" - NCR/KFC; blank if N/A
# "Receiving Destination" - optional; exchange or wallet $ went to [that's what the doc says; but sample file uses this as a 'received from' label]
# "Fee" - transaction fee, added to cost basis
# "Fee Currency" - currency fee was paid in
# "Exchange Transaction ID" - optional
# "Blockchain Transaction Hash" - optional


DEPLOYER_TXNS_FILE = "NCR Deployer Transactions.csv"

class CalculatedMintValue:

    _batch_dates = []       # tuple (batch_num, date, ncr_val)

    def __init__(self, deployer_txns_fname):
        self._read_deployer_transactions(deployer_txns_fname)

    def has_data(self):
        return self._batch_dates

    # parse batch information from deployer transactions file, store in _batch_dates
    # note: input file HAS to be sorted by transaction date, oldest first
    def _read_deployer_transactions(self, deployer_txns_fname):

        if(False == os.path.exists(DEPLOYER_TXNS_FILE)):
            print(f"Deployer transactions file {DEPLOYER_TXNS_FILE} not found; calcualted mint values will not be available.")
            return

        # read deployer address transactions to calculate batch dates
        try:
            print(f"Reading batch information from deployer transaction file {deployer_txns_fname}")
            with open(deployer_txns_fname, newline='') as csvfile:
                self._batch_dates.clear()
                batch_num = 1
                batch_value = 0.06
                total_minted = 0
                mint_start = datetime.utcfromtimestamp(1549004400)
                self._batch_dates.append((batch_num, mint_start, batch_value))
                for row in csv.DictReader(csvfile):

                    # skip all non-NCR transactions
                    if(row["TokenSymbol"] != "NCR"):
                        continue
                    
                    # read time and value of transaction, calculate total minted and batch that this transaction falls into
                    tx_time = datetime.utcfromtimestamp(int(row["UnixTimestamp"]))
                    tx_value = float(row["Value"].replace(',', ''))
                    total_minted += tx_value
                    tx_batch = total_minted // 100000 + 1

                    # if this transaction completes one or more batches, save the information on those
                    while(batch_num < tx_batch):
                        batch_num += 1
                        batch_value *= 1.0125
                        self._batch_dates.append((batch_num, tx_time, batch_value))

            print(f"  Found {len(self._batch_dates)} minting batches")

        except AssertionError as e:
            print("Error reading deployer transactions file; calculated mint values will not be available.")
            print(e)

    def get_value_at_date(self, tx_date):

        # no value if file failed to read
        if len(self._batch_dates) == 0:
            return None

        # CoinMarketCap appears to have started tracking NCR price on 2021-10-31, so don't guess prices after that date
        cmc_data_avail_date = datetime(2021, 11, 1, 0, 0, 0)
        if(tx_date > cmc_data_avail_date): 
            return None

        # otherwise scan through batch list to find the batch this Tx belongs to and return the value
        prev_batch_val = 0
        for batch_num, batch_date, batch_ncr_val in self._batch_dates:
            if tx_date > batch_date:
                prev_batch_val = batch_ncr_val
            else:
                return prev_batch_val

        return None

        
                    
# check if line contains a comment
def is_comment_line(line):
    return line.startswith("Comment: ")

# parse comment from line
def parse_comment_line(line):
    return line[len("Comment: "):].strip()

# check if line contains a 'SEND' transaction
def is_send_line(line):
    return line.startswith('[') and line.split()[1] == "SEND"

# parse 'SEND' line into dictionary
def parse_send_line(line):
    parsed_line = {}
    parsed_line["Txn ID"] = int(line[1:line.index(']')])
    parsed_line["Txn Type"] = "SEND"
    parsed_line["Amount"] = float(str.split(line)[2])
    parsed_line["Currency"] = str.split(line)[3]
    parsed_line["User"] = line[line.index(" to ") + len(" to ") : line.index(". Balance:")]
    parsed_line["Balance"] = float(line[line.index(". Balance:") + len(". Balance:") : line.index(". Timestamp:")])
    timestamp_str = line[line.index(". Timestamp: ") + len(". Timestamp: ") : len(line) - 2]
    parsed_line["Timestamp"] = datetime.strptime(timestamp_str, "%A, %d %B %Y %H:%M:%S")
    parsed_line["Comment"] = None
    return parsed_line

# check if line contains a 'RECEIVE' transaction
def is_receive_line(line):
    return line.startswith('[') and line.split()[1] == "RECEIVE"

# parse 'RECEIVE' line into dictionary
def parse_receive_line(line):
    parsed_line = {}
    parsed_line["Txn ID"] = int(line[1:line.index(']')])
    parsed_line["Txn Type"] = "RECEIVE"
    parsed_line["Amount"] = float(str.split(line)[2])
    parsed_line["Currency"] = str.split(line)[3]
    parsed_line["User"] = line[line.index(" from ") + len(" from ") : line.index(". Balance:")]
    parsed_line["Balance"] = float(line[line.index(". Balance:") + len(". Balance:") : line.index(". Timestamp:")])
    timestamp_str = line[line.index(". Timestamp: ") + len(". Timestamp: ") : len(line) - 2]
    parsed_line["Timestamp"] = datetime.strptime(timestamp_str, "%A, %d %B %Y %H:%M:%S")
    parsed_line["Comment"] = None
    return parsed_line

def main():

    if(len(sys.argv) != 2):
        print("Usage: parse-neos-transactions [transaction_file]")
        exit()

    in_file_name = sys.argv[1]
    if(False == os.path.exists(in_file_name)):
        print(f"Invalid file {in_file_name}")
        exit()

    # read mint values first
    mint_values = CalculatedMintValue(DEPLOYER_TXNS_FILE)

    # read all lines from input file
    print(f"Reading Neos transaction file {in_file_name}")
    try:
        with open(in_file_name, 'r') as in_file:
            lines = in_file.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        exit()

    # parse transactions
    print("Parsing transactions")
    neos_txns = []
    last_txn = None
    for line in lines:

        # check for comments and add to the last transaction
        # note: only supports one comment line per transaction, multi-line comments may be lost
        if(is_comment_line(line) and last_txn != None):
            last_txn["Comment"] = parse_comment_line(line)
            last_txn = None
        
        # check for send line, if found parse and add to list
        if(is_send_line(line)):
            last_txn = parse_send_line(line)
            neos_txns.append(last_txn)

        # check for receive line, if found parse and add to list
        if(is_receive_line(line)):
            last_txn = parse_receive_line(line)
            neos_txns.append(last_txn)

    print(f"  Parsed {len(neos_txns)} transactions from file")

    # insert prices calcualted from mint deployer transaction history
    if mint_values.has_data():
        print("Calculating prices from deployer transactions")
        num_vals_found = 0
        for txn in neos_txns:
            txn["CalculatedMintValue"] = mint_values.get_value_at_date(txn["Timestamp"])
            if txn["CalculatedMintValue"] is not None:
                num_vals_found += 1
        print(f"  Calculated {num_vals_found} prices based on NCR deployer transactions")
        print("  ***WARNING*** -- these prices are just an estimate any may not be a correct cost basis")

    print("Saving converted files")
    # output as generic CSV
    out_fname_csv = os.path.splitext(in_file_name)[0] + ".csv"
    with open(out_fname_csv, 'w', newline='') as csvfile:
        fieldnames = ["Txn ID", "Timestamp", "Txn Type", "Amount", "Currency", "User", "Balance", "Comment", "CalculatedMintValue"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for txn in neos_txns:
            writer.writerow(txn)
    print("  Saved", out_fname_csv)

    # Koinly compatible file
    out_fname_koinly = os.path.splitext(in_file_name)[0] + "-Koinly.csv"
    with open(out_fname_koinly, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Koinly Date", "Amount", "Currency", "Net Worth Amount", "Net Worth Currency", "Description"])
        for txn in neos_txns:
            koinly_date = txn["Timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            koinly_amount = txn["Amount"] * (1 if txn["Txn Type"] == "RECEIVE" else -1)
            estimated_value = koinly_amount * txn["CalculatedMintValue"] if txn["CalculatedMintValue"] else ""
            estimated_currency = "USD" if txn["CalculatedMintValue"] else ""
            writer.writerow([koinly_date, koinly_amount, txn["Currency"], estimated_value, estimated_currency, txn["Comment"]])
    print("  Saved", out_fname_koinly)
    
    exit()
    
    # TokenTax compatible file
    # Note: since Type is mandatory the file will need to be manually edited to select
    out_fname_tokentax = os.path.splitext(in_file_name)[0] + "-TokenTax.csv"
    with open(out_fname_tokentax, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Type", "BuyAmount", "BuyCurrency", "SellAmount", "SellCurrency", "FeeAmount", "FeeCurrency", "Exchange", "Group", "Comment", "Date"])
        for txn in neos_txns:
            tx_type = "Deposit / Income" if txn["Txn Type"] == "RECEIVE" else "Withdrawal / Spend / Gift"
            buy_amount = txn["Amount"] if txn["Txn Type"] == "RECEIVE" else ""
            buy_currency = txn["Currency"] if txn["Txn Type"] == "RECEIVE" else ""
            sell_amount = txn["Amount"] if txn["Txn Type"] == "SEND" else ""
            sell_currency = txn["Currency"] if txn["Txn Type"] == "SEND" else ""
            tx_date = txn["Timestamp"].strftime("%m/%d/%Y %H:%M")
            writer.writerow([tx_type, buy_amount, buy_currency, sell_amount, sell_currency, "", "", "Neos", "", txn["Comment"], tx_date])
    print("  Saved", out_fname_tokentax)
    print("    ***NOTE*** -- The 'Type' column must be manually edited to select the correct type for each transaction")

    # TaxBit compatible file
    # Note: since "Transaction Type" is mandatory the file will need to be manually edired to select
    out_fname_taxbit = os.path.splitext(in_file_name)[0] + "-TaxBit.csv"
    with open(out_fname_taxbit, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Date and Time", "Transaction Type", "Sent Quantity", "Sent Currency", "Sending Source", 
                         "Received Quantity", "Received Currency", "Receiving Destination", "Fee", "Fee Currency", 
                         "Exchange Transaction ID", "Blockchain Transaction Hash"])
        for txn in neos_txns:
            tx_date = txn["Timestamp"].strftime("%Y-%m-%dT%H:%M:%S")
            tx_type = "Transfer In / Income" if txn["Txn Type"] == "RECEIVE" else "Transfer Out / Expense"
            sent_qty = txn["Amount"] if txn["Txn Type"] == "SEND" else ""
            sent_cur = txn["Currency"] if txn["Txn Type"] == "SEND" else ""
            sending_src = txn["User"] if txn["Txn Type"] == "SEND" else ""
            received_qty = txn["Amount"] if txn["Txn Type"] == "RECEIVE" else ""
            received_cur = txn["Currency"] if txn["Txn Type"] == "RECEIVE" else ""
            receiving_dest = txn["User"] if txn["Txn Type"] == "RECEIVE" else ""
            writer.writerow([tx_date, tx_type, sent_qty, sent_cur, sending_src, received_qty, received_cur, receiving_dest, "", "", "", ""])
    print("  Saved", out_fname_taxbit)
    print("    ***NOTE*** -- The 'Transaction Type' column must be manually edited to select the correct type for each transaction")

if __name__ == '__main__':
    main()