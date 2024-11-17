# Pravallika Vasireddy (pvasire2), Karthik Masineni (kmasine)

# Import all the required libraries
import socket
import threading
import sys

class AuctionManager:
    """
    The AuctionManager class handles seller and bidder connections, manages auction states, 
    and processes bids in a multi-threaded server environment.
    """

    def __init__(self): 
        """
        Initialize the auction manager with essential variables, 
        states, and server configuration.
        """

        # List to store the connected bidders
        self.bidder_list = []

        # Dictionary to store auction details sent by the seller
        self.auction_data = {'auction_mode': 0, 'minimum_price': 0, 'bidder_count': 0, 'product_name': ""}

        # Dictionary to store bids placed by each bidder
        self.bid_records = {}

        # Auction manager states. Set to 0 when waiting for a seller and 1 when waiting for bidders.
        self.AWAITING_SELLER = 0
        self.AWAITING_BIDDER = 1

        # Initialize current state to wait for seller connection
        self.current_state = self.AWAITING_SELLER

        # List to store the payment details of the final auction
        self.final_payment = []

        # Server configuration, host is localhost, port number passed through the command line
        self.HOST = 'localhost'
        self.PORT = int(sys.argv[1])

        # Create the server socket for the auctioneer and bind to host and port
        self.manager_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.manager_socket.bind((self.HOST, self.PORT))
        self.manager_socket.listen()

        # Indicate that the auctioneer is ready to host auctions
        print("Auctioneer is ready for hosting auctions!")

        # Start listening for connections from sellers and buyers
        self.wait_for_connections()

    def wait_for_connections(self):
        """
        Wait for incoming connections, handle the connections based on the auction state,
        and create new threads for sellers and buyers.
        """
        while True:
            # Accept a connection from either a seller or bidder
            client_socket, client_address = self.manager_socket.accept()

            # Notify the connected client
            client_socket.send("Connected to the Auctioneer server\n".encode())

            # Handle connection based on the current state (waiting for seller or buyer)
            if self.current_state == self.AWAITING_SELLER:
                self.seller_socket, self.seller_address = client_socket, client_address
                print('Seller connected from ' + str(self.seller_address))

                # Create a new thread to handle seller actions
                threading.Thread(target=self.process_seller, args=(self.seller_socket,)).start()
                print(">> New seller thread spawned")

                # Move to the next state, awaiting bidders
                self.current_state = self.AWAITING_BIDDER
            
            elif self.current_state == self.AWAITING_BIDDER:
                # Append connected buyer to the bidder list
                self.bidder_list.append(client_socket)

                # Notify buyer about their role and waiting status
                if len(self.bidder_list) < self.auction_data['bidder_count']:
                    client_socket.send("Your role is: [Buyer]\n".encode())
                    client_socket.send('The auctioneer is still waiting for other buyers to connect...'.encode())
                    print(f'Buyer {len(self.bidder_list)} is connected from ' + str(client_address[0]) + ":" + str(client_address[1]))

                # When all required buyers are connected, start the auction
                elif len(self.bidder_list) == self.auction_data['bidder_count']:
                    client_socket.send("Your role is: [Buyer]\n".encode())
                    print(f'Buyer {len(self.bidder_list)} is connected from ' + str(client_address[0]) + ":" + str(client_address[1]))
                    print('Requested number of bidders arrived. Let\'s start bidding!')

                    # Start the auction on a new thread
                    threading.Thread(target=self.start_auction).start()
                    print(">> New bidding thread spawned")
                else:
                    # If too many bidders try to connect, notify them the server is busy
                    client_socket.send("Server is busy. Try to connect again later.\n".encode())
                    client_socket.close()
                    self.bidder_list.pop()
                    continue

    def process_seller(self, client_socket):
        """
        Process auction request from the seller, including the auction mode, minimum price, number of bidders, 
        and product name. Raise errors for invalid inputs.
        """
        client_socket.send("Your role is: [Seller]".encode())
        
        while True:
            # Request auction details from the seller
            client_socket.send("Please submit an auction request: ".encode())

            try:
                # Receive and parse the auction details
                auction_request = client_socket.recv(1024).decode()
                auction_mode, minimum_price, bidder_count, product_name = auction_request.split()
                auction_mode = int(auction_mode)
                minimum_price = int(minimum_price)
                bidder_count = int(bidder_count)

                # Validate auction details
                if auction_mode not in [1, 2]:
                    raise ValueError("Invalid auction mode.")
                if minimum_price < 1:
                    raise ValueError("Invalid minimum price.")
                if bidder_count < 1 or bidder_count > 10:
                    raise ValueError("Invalid number of bidders.")
                if len(product_name) > 255:
                    raise ValueError("Product name too long.")

                # Store the auction data
                self.auction_data = {'auction_mode': auction_mode, 'minimum_price': minimum_price, 'bidder_count': bidder_count, 'product_name': product_name}

                # Notify the seller that the auction has started
                client_socket.send("Server: Auction Start".encode())
                print("Auction request received. Now waiting for buyers...")
                self.current_state = self.AWAITING_BIDDER
                return

            except Exception as e:
                client_socket.send(f'Invalid auction request: {e}'.encode())

    def process_bidder(self, client_socket):
        """
        Process each bidder's bid, ensuring valid positive integers, and store the bids in the bid_records dictionary.
        """
        client_socket.send('The bidding has started!\nPlease submit your bid:'.encode())
        
        while True:
            try:
                # Receive bid and ensure it's a valid positive integer
                bid = int(client_socket.recv(1024).decode())
                if bid < 1:
                    raise ValueError("Bid must be positive.")
                break
            except:
                client_socket.send('Server: Invalid bid. Please submit a positive integer!'.encode())

        # Identify the bidder and store the bid
        bidder_index = self.bidder_list.index(client_socket)
        print(f"Buyer {bidder_index + 1} bid: {bid}")
        client_socket.send('Server: Bid received. Please wait...'.encode())
        self.bid_records[client_socket] = bid


    def start_auction(self):
        """
        Start the auction by collecting bids from all the buyers, processing the bids, and declaring the auction result.
        """
        # Start threads to process each bidder's bid
        for buyer in self.bidder_list:
            threading.Thread(target=self.process_bidder, args=(buyer,)).start()

        while True:
            # Once all bids are received, find the highest bid
            if len(self.bid_records) == self.auction_data['bidder_count']:
                highest_bidder = max(self.bid_records, key=self.bid_records.get)
                highest_bid = self.bid_records[highest_bidder]

                # Handle an unsuccessful auction
                if highest_bid < self.auction_data['minimum_price']:
                    self.seller_socket.send('Unfortunately the item was not sold.'.encode())
                    for buyer in self.bidder_list:
                        buyer.send('Unfortunately you have not won the auction.'.encode())
                        buyer.close()
                    print("Auction failed as the minimum price was not reached!")
                    self.reset_auction()
                else:
                    # Process a successful auction (based on the auction mode)
                    self.handle_auction_success(highest_bidder, highest_bid)
                return

    def handle_auction_success(self, highest_bidder, highest_bid):
        """
        Handle the result of a successful auction, notifying both the seller and the winning bidder, 
        and closing connections.
        """
        if self.auction_data['auction_mode'] == 1:
            # Notify seller and winner in a first-price auction
            self.seller_socket.send(f'Auction Finished!\nSuccess! Your item {self.auction_data["product_name"]} has been sold for ${highest_bid}. Buyer IP: {highest_bidder.getpeername()[0]}\nDisconnecting from the Auctioneer server. Auction is Over!'.encode())
            
            highest_bidder.send(f'Auction Finished!\nSuccess! You won the item {self.auction_data["product_name"]}. Your payment due is ${highest_bid}. Seller IP: {self.seller_socket.getpeername()[0]}\nDisconnecting from the Auctioneer server. Auction is Over!'.encode())
            
        elif self.auction_data['auction_mode'] == 2:
            # For second-price auction, find second-highest bid
            del self.bid_records[highest_bidder]
            second_highest_bidder = max(self.bid_records, key=self.bid_records.get)
            second_highest_bid = self.bid_records[second_highest_bidder]
            
            # Notify seller and winner
            self.seller_socket.send(f'Auction Finished!\nSuccess! Your item {self.auction_data["product_name"]} has been sold for ${second_highest_bid}. Buyer IP: {highest_bidder.getpeername()[0]}\nDisconnecting from the Auctioneer server. Auction is Over!'.encode())
            
            highest_bidder.send(f'Auction Finished!\nSuccess! You won the item {self.auction_data["product_name"]}. Your payment due is ${second_highest_bid}. Seller IP: {self.seller_socket.getpeername()[0]}\nDisconnecting from the Auctioneer server. Auction is Over!'.encode())
        
        # Notify all losing bidders
        for buyer in self.bidder_list:
            if buyer != highest_bidder:
                buyer.send(f'Auction Finished!\nUnfortunately you did not win the last round.\nDisconnecting from the Auctioneer server. Auction is Over!'.encode())
                buyer.close()
        
        # Log auction result
        print(f"Item Sold! The highest bid is ${highest_bid}.")
        self.seller_socket.close()
        highest_bidder.close()

        # Reset auction for the next round
        self.reset_auction()

    def reset_auction(self):
        """
        Reset the auction state and data for the next round.
        """
        self.bidder_list = []
        self.bid_records = {}
        self.auction_data = {'auction_mode': 0, 'minimum_price': 0, 'bidder_count': 0, 'product_name': ""}
        self.final_payment = []
        self.current_state = self.AWAITING_SELLER
        print("Auctioneer is ready for hosting auctions!")


if __name__ == '__main__':
    AuctionManager()
