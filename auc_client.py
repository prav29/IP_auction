# Pravallika Vasireddy (pvasire2), Karthik Masineni (kmasine)

# Importing the required libraries
import socket
import sys

# Configuring the server connection
SERVER_HOST = sys.argv[1]  # Server IP address passed as a command-line argument
SERVER_PORT = int(sys.argv[2])  # Server port passed as a command-line argument


def handle_server_response(connection):
    """
    Helper function to receive and print messages from the auctioneer server.
    """
    server_response = connection.recv(1024).decode()  # Receive and decode server response
    print(server_response)  # Print the server response
    return server_response


def handle_seller_actions(seller_conn):
    """
    Function to manage the seller's interaction with the auctioneer server.
    The seller provides auction details, and this function handles the auction start process.
    """
    # Receive the initial connection response from the auctioneer
    handle_server_response(seller_conn)
    
    # Loop to send auction details until the auction starts
    while True:
        # Collecting auction details from the seller input in the format "1 20 2 shoes"
        try:
            auction_input = input("Enter auction details <auction_type> <min_price> <number_of_bidders> <item_name>: ")
            auction_mode, min_price, num_bidders, item_name = auction_input.split()

            # Format the auction details into a single string to send to the server
            auction_details = f"{auction_mode} {min_price} {num_bidders} {item_name}"

            # Sending the auction details to the server
            seller_conn.send(auction_details.encode())

            # Receiving and printing the auctioneer's response
            auctioneer_reply = handle_server_response(seller_conn)

            # If auction starts, exit the loop
            if "Server: Auction Start" in auctioneer_reply:
                handle_server_response(seller_conn)  # Receive final auction start message
                break  # Exit the loop, auction has started
        except ValueError:
            print("Invalid input. Please provide auction details in the format: <type> <min_price> <number_of_bidders> <item_name>")
            continue


def handle_buyer_actions(buyer_conn):
    """
    Function to manage the buyer's interaction with the auctioneer server.
    The buyer waits for the bidding to start and submits their bid when prompted.
    """
    # Loop to handle server responses related to the bidding process
    while True:
        auctioneer_reply = handle_server_response(buyer_conn)  # Receive initial response from the auctioneer
        
        if "The bidding has started!" in auctioneer_reply:
            # Loop to handle bid submission and response validation
            while True:
                try:
                    # Taking bid input from the buyer
                    bid_value = int(input("Enter your bid: "))
                    
                    # Sending the bid to the server
                    buyer_conn.send(str(bid_value).encode())

                    # Receiving and printing the auctioneer's response
                    auctioneer_reply = handle_server_response(buyer_conn)

                    # If bid is successfully received, proceed
                    if "Server: Bid received. Please wait..." in auctioneer_reply:
                        handle_server_response(buyer_conn)  # Receive final bid processing message
                        return  # Exit the loop after the bid is processed
                except ValueError:
                    print("Please enter a valid integer bid.")
                    continue


def initialize_client():
    """
    Main function to set up the client connection to the auctioneer server.
    It determines whether the user is a seller or a buyer based on server response.
    """
    # Creating a client socket to connect to the auctioneer server
    client_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_conn.connect((SERVER_HOST, SERVER_PORT))  # Connect to the server using the host and port

    # Receive and print the server response after connection
    handle_server_response(client_conn)  # Initial connection message
    role_response = handle_server_response(client_conn)  # Role (seller/buyer) message

    # Check if the client is a seller or a buyer and invoke the corresponding function
    if 'Seller' in role_response:
        handle_seller_actions(client_conn)  # Call seller function if the role is seller
    elif 'Buyer' in role_response:
        handle_buyer_actions(client_conn)  # Call buyer function if the role is buyer


if __name__ == '__main__':
    """
    Entry point of the client program. The client connects to the auctioneer server,
    and based on the role (seller or buyer), it follows appropriate actions.
    """
    initialize_client()  # Start the client program
