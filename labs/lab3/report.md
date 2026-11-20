# Lab 3 Network Transport and Applications

TECH3498 IT Computers Security | November 19 2026

ARP resolves local hardware addresses, ICMP tests reachability, UDP carries the observed DNS queries, and TCP establishes the observed HTTPS connection. SSH and TLS protect application content; a service port alone does not prove that a session succeeded. This report answers the lab questions using a Windows Wi-Fi capture and protocol documentation.

## Method and evidence

A 40-second capture was collected with dumpcap and inspected using TShark 4.4.5, both part of Wireshark. The capture contained 165 packets with zero reported drops. Tests included four gateway pings, nslookup kean.edu, short TCP connection attempts to obi2.kean.edu on ports 23 and 22, and an HTTPS HEAD request. No credentials were entered and no email was sent. Frame numbers below refer to this capture. Selected packet fields and command results accompany this report. Unrelated traffic and local device identifiers are excluded from the public evidence summary.

| Test | Observed result |
| --- | --- |
| ARP | Frames 18 and 19 form a broadcast request and unicast reply. |
| Gateway ping | 4 requests and 4 replies; 0% loss; command reports 4-5 ms. |
| DNS | kean.edu returned 131.125.16.38; query/reply in frames 86 and 87. |
| Telnet and SSH | SYN attempts to ports 23 and 22; both timed out after 2500 ms. |
| HTTPS | TCP handshake and TLS 1.2 traffic; curl returned HTTP 403 Forbidden. |
| Netstat | 128 TCP rows and 68 UDP rows in one netstat -ano snapshot. |

## Scope of the completed work

The network observations above were performed off campus. Campus login, SFTP upload, the mail experiments, and the Gmail security review remain unperformed. Their protocol questions are answered below, with expected behavior distinguished from observed results. ICMP is an Internet-layer control protocol carried by IP, rather than a TCP/UDP transport-layer protocol [1].


<!-- pagebreak -->

# Lab 3 1 ARP and ICMP

## What packets are sent during ping

The capture shows ICMP Echo Request packets, type 8, and Echo Reply packets, type 0. Request/reply pairs are frames 52/53, 58/59, 64/65, and 78/79. An IPv4 host may first use ARP if it lacks the next-hop MAC address. In this run, an ARP exchange also occurred before ping, but it was initiated by the gateway and was not caused by clearing the client cache [1,2].

## What is the Ethernet broadcast address

The destination in the selected ARP request, frame 18, is ff:ff:ff:ff:ff:ff, or FF FF FF FF FF FF in the packet bytes. It addresses all stations in the local broadcast domain.

## Which address comes first in the Ethernet header

The six-byte destination MAC address comes first, followed by the six-byte source MAC address and the two-byte EtherType. Frame 18 has EtherType 0x0806, identifying ARP. Ethernet may also include VLAN tags; padding and a frame check sequence belong to frame formatting, although the FCS is often absent from host captures.

## What fields appear in ARP

The fields are hardware type, protocol type, hardware address length, protocol address length, operation, sender hardware address, sender protocol address, target hardware address, and target protocol address. Here the hardware type is Ethernet (1), protocol type is IPv4 (0x0800), hardware length is 6, and protocol length is 4 [2].

## Do all ARP fields have data

All fields are present. The target hardware field in a request need not contain a resolved target MAC. In frame 18 it contains ff:ff:ff:ff:ff:ff; many ARP implementations instead use 00:00:00:00:00:00. This placeholder is distinct from the Ethernet destination field, which is the broadcast address in this request.

## How do the request and reply differ

Frame 18 is operation 1, a gateway broadcast asking for the client hardware address. Frame 19 is operation 2, the client reply sent directly to the gateway. Sender and target protocol-address roles are reversed, and the reply identifies the answering host hardware address. A request and reply should be matched by their addresses and operation, rather than assuming the next captured row must be the reply.

## What protocol does Wireshark list for ping

Wireshark lists ICMP for both requests and replies. Ping uses neither TCP nor UDP ports. The arp display filter limits the view to ARP; clearing the display filter restores the packet list without changing the saved capture.


<!-- pagebreak -->

# Lab 3 1 UDP and TCP

## DNS source port destination port and checksum

The selected nslookup A query for kean.edu is frame 86: UDP source port 59372, destination port 53, checksum 0xe04d, and UDP length 34 bytes. Its response, frame 87, uses source port 53, destination port 59372, and checksum 0x0aeb. Frame 88 is a separate AAAA query using 59373 to 53 and checksum 0xe030; frame 89 is its reply with checksum 0x5fb0. Earlier DNS packets were background traffic, so the selected packets are the first relevant kean.edu query and response, rather than the first DNS packet in the entire capture [3].

## Telnet source port destination port and checksum

The first TCP SYN for the Telnet test is frame 90, with source port 60474, destination port 23, and checksum 0x795f. Frame 93 is a retransmission. No SYN-ACK was captured for this flow, and the connection attempt timed out after 2500 ms. Thus this is an observed attempt, not an established Telnet login or a demonstration of cleartext credentials.

## What differs between the TCP and UDP headers

UDP has four fields: source port, destination port, length, and checksum; its header is 8 bytes. TCP includes source/destination ports, sequence and acknowledgment numbers, data offset, reserved bits, control flags, receive window, checksum, urgent pointer, and optional fields. Its base header is 20 bytes; the observed Telnet SYN has a 32-byte header because it includes options. TCP supports ordered byte delivery, acknowledgments, retransmission, flow control, and congestion control. UDP has no built-in connection handshake, ordering, or retransmission guarantee [3,4].

## How should checksum values be interpreted

The values above are the actual fields displayed for selected packets, not universal protocol constants. TShark reports these fields as unverified under the default checksum-validation settings; that does not establish validity or corruption. Transmit checksum offloading can also make outgoing host captures look incomplete or invalid before hardware finishes processing. Record the field and validation status separately [5].

## What does netstat add

netstat -ano reports local endpoints, remote endpoints and connection states for TCP, along with process IDs. UDP rows list bound endpoints without TCP connection states. The observed row counts are a transient system snapshot, not a count of lab connections. Packet bytes and checksums must be inspected in Wireshark; netstat does not provide them.


<!-- pagebreak -->

# Lab 3 2 File Transfer and Web Applications

## What does cat /etc/passwd return

It displays account records, typically one per line, with seven colon-separated fields: login name, password marker, user ID, primary group ID, user information, home directory, and login shell. An x commonly means that password hashes are held separately in /etc/shadow; it is not a plaintext password. System service accounts can have a shell that disables interactive login. This describes the file format; no obi2 account listing was retrieved [6].

## What web page was prepared

The accompanying index.html contains the requested heading, "This page is under construction.", and paragraph, "More computer security information will be posted here." It includes a complete head section, a UTF-8 declaration, and a valid HTML document structure. The file is ready for transfer; it has not been uploaded to obi2.

## Are FTP packets expected during SSH Secure File Transfer

SSH Secure File Transfer uses SFTP inside SSH, rather than ordinary FTP. The expected visible traffic includes TCP and SSH; DNS or ARP may also appear during name/address resolution. SFTP file content is encrypted, so a normal passive capture cannot read its commands or uploaded page. Ordinary FTP normally uses a separate FTP control connection on TCP 21 and separate data connections. No SFTP session occurred here, so the list of protocols in an actual transfer remains unverified [7,8].

## What are the SSH ports

The observed SSH connection attempt begins in frame 105 with client source port 60477 and server destination port 22, checksum 0xf606. Frame 108 repeats the SYN. The connection timed out after 2500 ms, so there is no first SSH protocol packet from an authenticated file-transfer session. For an established conventional SSH session, the reply direction would use source port 22 and the client ephemeral destination port [7].

## Are HTTP packets visible for the HTTPS URL

The HTTPS test shows TCP and TLS 1.2, including a client hello, server handshake, and encrypted application data. Without TLS secrets, the HTTP request and response content are not readable as plain HTTP in this capture. The curl endpoint did decrypt its own response and reported HTTP/1.1 403 Forbidden. This proves the web endpoint responded, but does not establish access to a personal public_html page [9].

## What are the HTTPS ports and checksum

The first HTTPS SYN, frame 117, uses source port 60479, destination port 443, and checksum 0x44f2. Frame 118 replies from 443 to 60479, checksum 0xe75d. Frame 119 completes the three-way handshake. These values describe TCP beneath TLS, even when Wireshark labels later packets TLS.


<!-- pagebreak -->

# Lab 3 2 Email and Account Security

## What message did the mail server return

No mail command was executed on obi2 because SSH access timed out. There is no observed server response or delivery result to report. A local mail utility may return silently after queueing a message; a direct SMTP exchange may provide a success reply such as code 250. Neither local acceptance nor SMTP acceptance alone proves final delivery to the inbox [10].

## How could this process be exploited

A sender can attempt to present a misleading sender address when the mail system permits it. This can support impersonation or phishing. A visible From address alone is insufficient evidence of identity. Sender authentication, relay restrictions, filtering, and recipient verification reduce this risk. The lab mail utility hands work to the server mail system; it is not itself a transcript of raw SMTP commands [10].

## What changes with the mail sender override option

The expected effect of mail -r spoofing@obi2.kean.edu is a changed sender identity, often the From header and possibly the SMTP envelope sender. Exact behavior depends on the installed mail implementation and server policy; a server may reject or rewrite it. Compare From, Sender if present, Reply-To, Return-Path, Received, and trusted Authentication-Results in the two received messages. No pair of messages was sent here, so no actual header difference is claimed.

## Can the true sender be identified

Headers from trusted receiving infrastructure can help trace a message. Examine the Received chain starting at the trusted receiving side and review SPF, DKIM, and DMARC results added by that infrastructure. An aligned authentication result supports authorized use of a domain; it does not identify the human who composed the email. Definitive attribution can require server submission logs and account records. DMARC evaluates alignment with the visible author domain [11].

## How do SMTP POP3 and IMAP relate

SMTP transfers outgoing email, conventionally using TCP 25 between servers. POP3 retrieves messages, conventionally on TCP 110; IMAP synchronizes and manages server mailboxes on TCP 143. TLS-protected variants commonly use POP3 995 and IMAP 993; submission commonly uses 587 with STARTTLS or 465 with implicit TLS. Plain ports alone do not guarantee cleartext because some services upgrade with STARTTLS. No POP3 or IMAP session was captured in this run [8,12].

## Are other Gmail sessions or third party grants present

The Kean Gmail account was not inspected. Other sessions: not assessed. Third-party access: not assessed. To complete the review, open Gmail on a computer and select Details at the bottom right; then review Google Account security, Manage all devices, and third-party connections. Record whether every session and grant is recognized. Multiple sessions can legitimately belong to the same device. Sign out or revoke access only after reviewing the particular entry [13,14].


<!-- pagebreak -->

# Issues Resolution and Remaining Evidence

## Off campus service access

Both obi2 TCP 23 and TCP 22 attempts timed out. A short timeout cannot distinguish a firewall rule from routing or service availability, and does not prove a port is closed. HTTPS reached the host but received 403. Retry SSH/SFTP from the campus network or a university-supported VPN if available, then record the actual outcome. The successful DNS lookup and HTTPS connection narrow the failure to specific service paths rather than establishing that the host is generally unreachable.

## ARP cache and capture differences

The Windows session lacked administrator privileges, and the ARP cache was left unchanged. A naturally occurring gateway-to-client ARP request and its reply were used for the ARP questions. This supports the ARP analysis without claiming that the prescribed cache-reset step was completed. No Windows features, passwords, account grants, or server permissions were changed.

## Evidence still required before submission

Complete an obi2 login and record the account-file interpretation against the actual output; upload index.html through SFTP and verify the personal web URL and permissions; record the first SSH packet ports; perform the two instructor-directed mail tests to your own mailbox and compare received headers; record the exact mail response; review Gmail sessions and third-party grants. Capture screenshots if required by the instructor. Keep passwords, mailbox contents, and other people's account information out of a public repository.

## Permissions and restoration

The handout requests 0755 for directories and referenced files. For directories, this grants owner read/write/search and others read/search; a static HTML file usually needs read permission rather than execute permission. Follow the lab server policy and record the permissions actually used. No campus changes were made in this run, so there is no server state to restore.

## References

[1] [ICMP](https://www.rfc-editor.org/rfc/rfc792)  
[2] [ARP](https://www.rfc-editor.org/rfc/rfc826)  
[3] [UDP](https://www.rfc-editor.org/rfc/rfc768)  
[4] [TCP](https://www.rfc-editor.org/rfc/rfc9293)  
[5] [Wireshark checksums](https://www.wireshark.org/docs/wsug_html_chunked/ChAdvChecksums.html)  
[6] [Linux passwd file format](https://man7.org/linux/man-pages/man5/passwd.5.html)  
[7] [SSH transport](https://www.rfc-editor.org/rfc/rfc4253)  
[8] [IANA service port registry](https://www.iana.org/assignments/service-names-port-numbers/)  
[9] [HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110)  
[10] [SMTP](https://www.rfc-editor.org/rfc/rfc5321)  
[11] [DMARC](https://www.rfc-editor.org/rfc/rfc9989)  
[12] [TLS for email](https://www.rfc-editor.org/rfc/rfc8314)  
[13] [Gmail account activity](https://support.google.com/mail/answer/45938?hl=en)  
- [14] [Google account devices](https://support.google.com/accounts/answer/3067630?hl=en)