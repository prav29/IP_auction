# Pravallika Vasireddy (pvasire2), Karthik Masineni (kmasine)

# Importing the required libraries
import socket
import sys
import os
import time
import numpy

# Configuring the server connection
SERVER_HOST = sys.argv[1]  # Server IP address passed as a command-line argument
SERVER_PORT = int(sys.argv[2])  # Server port passed as a command-line argument
UDP_PORT = int(sys.argv[3])  # UDP port for file transfer passed as a command-line argument
PACKET_LOSS_RATE = float(sys.argv[4])

CHUNK_SIZE = 2000
TIMEOUT = 2

def start_file_transfer_seller(winner_ip, udp_port):
    """
    Seller function for sending the file via Stop-and-Wait RDT.
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(TIMEOUT)
    print("UDP socket opened for RDT.\nStart sending file.")

    # Read the file to be sent
    file_path = "tosend.file"
    if not os.path.exists(file_path):
        print("Error: File tosend.file not found.")
        return

    with open(file_path, "rb") as file:
        file_data = file.read()

    total_size = len(file_data)
    total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE  # Calculate total chunks
    seq_num = 0

    # Send start control message
    start_msg = f"start {total_size}".encode()
    udp_socket.sendto(start_msg, (winner_ip, udp_port))
    print(f"Sending control seq {seq_num}: {start_msg.decode()}")

    try:
        ack, addr = udp_socket.recvfrom(1024)
        if ack.decode() == "ACK:0":
            print(f"Ack received: {seq_num}")
        else:
            print("Did not receive the correct ACK for start. Retrying.")
            udp_socket.sendto(start_msg, (winner_ip, udp_port))
    except socket.timeout:
        print("Timeout waiting for ACK. Retrying.")
        udp_socket.sendto(start_msg, (winner_ip, udp_port))

    # Send file chunks
    for i in range(total_chunks):
        chunk = file_data[i * CHUNK_SIZE: (i + 1) * CHUNK_SIZE]
        packet = f"{seq_num}:".encode() + chunk
        udp_socket.sendto(packet, (winner_ip, udp_port))
        print(f"Sending data seq {seq_num}: {len(chunk)}/{total_size}")

        try:
            ack, addr = udp_socket.recvfrom(1024)
            if ack.decode() == f"ACK:{seq_num}":
                print(f"Ack received: {seq_num}")
                seq_num = 1 - seq_num  # Toggle sequence number
            else:
                print(f"Received incorrect ACK: {ack.decode()}. Retrying.")
                udp_socket.sendto(packet, (winner_ip, udp_port))
        except socket.timeout:
            print("Timeout waiting for ACK. Retrying.")
            udp_socket.sendto(packet, (winner_ip, udp_port))

    # Send fin control message
    fin_msg = "fin".encode()
    udp_socket.sendto(fin_msg, (winner_ip, udp_port))
    print(f"Sending control seq {seq_num}: fin")

    try:
        ack, addr = udp_socket.recvfrom(1024)
        if ack.decode() == f"ACK:{seq_num}":
            print(f"Ack received: {seq_num}. File transfer complete.")
    except socket.timeout:
        print("Timeout waiting for ACK for fin. Exiting.")
    finally:
        udp_socket.close()


def start_file_transfer_buyer(seller_ip, udp_port):
    """
    Buyer function for receiving the file via Stop-and-Wait RDT.
    Calculates Transfer Completion Time (TCT) and Average Throughput (AT).
    """
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(("", udp_port))
    print("UDP socket opened for RDT.\nStart receiving file.")

    received_data = b""
    expected_seq_num = 0
    total_size = None

    # Start timing for Transfer Completion Time (TCT)
    start_time = time.time()

    while True:
        try:
            packet, addr = udp_socket.recvfrom(2048)

            # Simulate packet loss
            if numpy.random.binomial(1, PACKET_LOSS_RATE):
                print(f"Pkt dropped: {expected_seq_num}")
                continue

            if addr[0] != seller_ip:
                print(f"Msg received from unauthorized IP {addr[0]}. Discarding.")
                continue

            # Parse the message
            if packet.startswith(b"start"):
                total_size = int(packet.decode().split()[1])
                print(f"Msg received: start {total_size}")
                udp_socket.sendto(f"ACK:{expected_seq_num}".encode(), addr)
                print(f"Ack sent: {expected_seq_num}")

            elif packet.startswith(b"fin"):
                print("Msg received: fin")
                udp_socket.sendto(f"ACK:{expected_seq_num}".encode(), addr)
                print(f"Ack sent: {expected_seq_num}")
                break  # End the loop after correctly processing the "fin" message

            else:
                seq_num, chunk = packet.decode("latin1").split(":", 1)
                seq_num = int(seq_num)

                if seq_num == expected_seq_num:
                    received_data += chunk.encode("latin1")
                    print(f"Received data seq {seq_num}: {len(received_data)}/{total_size}")
                    udp_socket.sendto(f"ACK:{seq_num}".encode(), addr)
                    print(f"Ack sent: {seq_num}")
                    expected_seq_num = 1 - expected_seq_num  # Toggle sequence number
                else:
                    print(f"Msg received with mismatched sequence number {seq_num}. Expecting {expected_seq_num}")
                    udp_socket.sendto(f"ACK:{1 - expected_seq_num}".encode(), addr)

        except socket.timeout:
            print("Timeout waiting for packet. Retrying.")
            continue

    # Calculate TCT and AT
    end_time = time.time()
    transfer_completion_time = end_time - start_time  # Total time in seconds
    average_throughput = len(received_data) / transfer_completion_time  # Bytes per second

    # Save received file
    with open("recved.file", "wb") as file:
        file.write(received_data)

    print(f"File transfer complete. File saved as recved.file.")
    print(f"Transfer Completion Time (TCT): {transfer_completion_time:.6f} seconds")
    print(f"Average Throughput (AT): {average_throughput:.2f} bytes/second")
    udp_socket.close()


# def start_file_transfer_buyer(seller_ip, udp_port):
#     """
#     Buyer function for receiving the file via Stop-and-Wait RDT.
#     """
#     udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     udp_socket.bind(("", udp_port))
#     print("UDP socket opened for RDT.\nStart receiving file.")

#     received_data = b""
#     expected_seq_num = 0
#     total_size = None

#     while True:
#         try:
#             packet, addr = udp_socket.recvfrom(2048)

#             # Simulate packet loss
#             if numpy.random.binomial(1, PACKET_LOSS_RATE):
#                 print(f"Pkt dropped: {expected_seq_num}")
#                 continue

#             if addr[0] != seller_ip:
#                 print(f"Msg received from unauthorized IP {addr[0]}. Discarding.")
#                 continue

#             # Parse the message
#             if packet.startswith(b"start"):
#                 total_size = int(packet.decode().split()[1])
#                 print(f"Msg received: start {total_size}")
#                 udp_socket.sendto(f"ACK:{expected_seq_num}".encode(), addr)
#                 print(f"Ack sent: {expected_seq_num}")

#             elif packet.startswith(b"fin"):
#                 print("Msg received: fin")
#                 udp_socket.sendto(f"ACK:{expected_seq_num}".encode(), addr)
#                 print(f"Ack sent: {expected_seq_num}")
#                 break

#             else:
#                 seq_num, chunk = packet.decode("latin1").split(":", 1)
#                 seq_num = int(seq_num)

#                 if seq_num == expected_seq_num:
#                     received_data += chunk.encode("latin1")
#                     print(f"Received data seq {seq_num}: {len(received_data)}/{total_size}")
#                     udp_socket.sendto(f"ACK:{seq_num}".encode(), addr)
#                     print(f"Ack sent: {seq_num}")
#                     expected_seq_num = 1 - expected_seq_num  # Toggle sequence number
#                 else:
#                     print(f"Msg received with mismatched sequence number {seq_num}. Expecting {expected_seq_num}")
#                     udp_socket.sendto(f"ACK:{1 - expected_seq_num}".encode(), addr)

#         except socket.timeout:
#             print("Timeout waiting for packet. Retrying.")
#             continue

#     # Save received file
#     with open("recved.file", "wb") as file:
#         file.write(received_data)
#     print(f"File transfer complete. File saved as recved.file.")
#     udp_socket.close()


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
                final_response = handle_server_response(seller_conn)  # Receive final auction start message
                break  # Exit the loop, auction has started
        except ValueError:
            print("Invalid input. Please provide auction details in the format: <type> <min_price> <number_of_bidders> <item_name>")
            continue
    
    if "Success!" in final_response:
        buyer_ip = final_response.split("Buyer IP:")[1].split()[0]
        print(f"Extracted Buyer IP: {buyer_ip}")
        start_file_transfer_seller(buyer_ip, int(UDP_PORT))



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
                        final_response = handle_server_response(buyer_conn)  # Receive final bid processing message

                        if "Success!" in final_response:
                            seller_ip = final_response.split("Seller IP:")[1].split()[0]
                            # print(f"Extracted Seller IP: {seller_ip}")
                            start_file_transfer_buyer(seller_ip, int(UDP_PORT))

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
