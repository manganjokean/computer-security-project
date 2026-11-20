# Lab 3 Network Transport and Applications

TECH3498 IT Computers Security

**Status: written answers and local network observations are prepared; campus and account-specific tasks remain pending. This is not a fully completed lab submission.**

- [Report PDF](Lab3-Network-Transport-and-Applications.pdf)
- [Editable report text](report.md)
- [Requested sample web page](index.html)
- [Selected observed packet fields](evidence/packet-summary.csv)
- [Command results and evidence notes](evidence/observations.txt)

The report covers every question in the supplied lab procedure. It distinguishes actual packet observations from expected protocol behavior and unperformed account actions. Sources are linked in the report. No original instructor document, credentials, raw capture, mailbox contents, or account security details are published.

## Remaining work

1. Reach obi2 from the campus network or university-supported VPN and log in using your own account. Record the outcome of the account-file inspection.
2. Upload `index.html` using SFTP, apply the permissions required by the course/server, and verify your personal web URL. Capture the actual SSH session fields.
3. Perform the two lab mail tests to your own mailbox. Record the exact utility/server response and compare the received headers.
4. Review Kean Gmail sessions and third-party connections. Record only the required summary; keep sensitive evidence private.
5. Add the resulting evidence to the report and have it reviewed before submission.

## Reproducing the network observations

Use `dumpcap -D` to find your active interface, then capture in Wireshark while running `ping -n 4 <gateway>`, `nslookup kean.edu`, and the instructor-directed service tests. Interface numbers, source ports, checksums, timings and frame numbers will vary. Relevant display filters include `arp`, `icmp`, `dns.qry.name == "kean.edu"`, `tcp.port == 23`, `tcp.port == 22`, and `tcp.port == 443`.

Do not infer that a TCP connection succeeded from an outgoing SYN alone. Inspect the handshake. The observed SSH and Telnet attempts timed out; HTTPS responded with 403. A timeout is not proof that a port is closed. See the report for the ARP cache and checksum-validation limitations.
